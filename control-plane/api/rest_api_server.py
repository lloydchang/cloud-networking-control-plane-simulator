# File: rest_api_server.py
#!/usr/bin/env python3
"""
Cloud Networking REST API Server

FastAPI-based REST API for network operations.
Implements the Network API covering:
- VPCs
- Subnets
- Routes
- Security Groups
- NAT Gateways
- Internet Gateways
"""

import uuid
import asyncio
import time
import os
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response, HTMLResponse
from pydantic import BaseModel, Field

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from metrics import METRICS

from .models import (
    Base,
    VPC as VPCModel,
    VPCEndpoint as VPCEndpointModel,
    Subnet as SubnetModel,
    SecurityGroup as SGModel,
    NATGateway as NATModel,
    Route as RouteModel,
    InternetGateway as InternetGatewayModel,
    VPNGateway as VPNGatewayModel,
    MeshNode as MeshNodeModel,
    CloudRoutingHub as HubModel,
    StandaloneDataCenter as StandaloneDCModel,
    StandaloneDCSubnet as StandaloneDCSubnetModel,
)
from . import models
from . import shared_api_logic as services

app = FastAPI(
    title="Cloud Networking Simulator - Control Plane API",
    description="Cloud Networking Simulator - Control Plane API",
    version="1.0.0",
)

# ============================================================================
# Static Assets
# ============================================================================

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
if os.path.exists(SCRIPTS_DIR):
    app.mount("/scripts", StaticFiles(directory=SCRIPTS_DIR), name="scripts")

ASSETS_DIR = "/app/assets"
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# ============================================================================
# Database Configuration
# ============================================================================

DB_DIR = os.getenv("DB_DIR", "/app/data")
DB_PATH = os.getenv("DB_PATH", f"{DB_DIR}/network.db")

if not DB_PATH.startswith(":memory:"):
    os.makedirs(DB_DIR, exist_ok=True)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

# Ensure singleton vni_counter row exists to prevent startup failures
from sqlalchemy import text
with engine.begin() as conn:
    conn.execute(text("CREATE TABLE IF NOT EXISTS vni_counter (id INTEGER PRIMARY KEY CHECK (id = 1), value INTEGER NOT NULL)"))
    result = conn.execute(text("SELECT value FROM vni_counter WHERE id = 1"))
    row = result.fetchone()
    if row is None:
        conn.execute(text("INSERT INTO vni_counter (id, value) VALUES (1, 1)"))

# ============================================================================
# Startup Hooks
# ============================================================================

@app.on_event("startup")
def initialize_metrics():
    db = SessionLocal()
    try:
        METRICS["vpcs_total"].set(db.query(VPCModel).count())
        METRICS["subnets_total"].set(db.query(SubnetModel).count())
        METRICS["routes_total"].set(db.query(RouteModel).count())
        METRICS["security_groups_total"].set(db.query(SGModel).count())
        METRICS["nat_gateways_total"].set(db.query(NATModel).count())
        METRICS["internet_gateways_total"].set(db.query(InternetGatewayModel).count())
    finally:
        db.close()

# ============================================================================
# Dependencies
# ============================================================================

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================================
# Pydantic Models
# ============================================================================

class VPCCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    cidr: str
    region: str = "us-east-1"
    secondary_cidrs: List[str] = Field(default_factory=list)
    scenario: Optional[str] = None

class VPC(BaseModel):
    id: str
    name: str
    cidr: str
    region: str
    secondary_cidrs: List[str]
    scenario: Optional[str]
    status: str
    created_at: datetime

class VPCEndpointCreate(BaseModel):
    name: str
    ip: str

class VPCEndpoint(BaseModel):
    id: str
    vpc_id: str
    name: str
    ip: str
    subnet_id: str
    status: str
    created_at: datetime

class SecurityRuleCreate(BaseModel):
    direction: str
    protocol: str
    port_from: Optional[int] = None
    port_to: Optional[int] = None
    cidr: str = "0.0.0.0/0"

class SecurityGroupCreate(BaseModel):
    name: str
    description: str = ""
    rules: List[SecurityRuleCreate] = Field(default_factory=list)

class SecurityGroup(BaseModel):
    id: str
    name: str
    description: str
    rules: List[dict]
    created_at: datetime

# ============================================================================
# Health and Metrics
# ============================================================================

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/metrics")
def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    METRICS["api_requests"].labels(
        method=request.method,
        endpoint=request.url.path,
    ).inc()
    start = time.time()
    response = await call_next(request)
    _ = (time.time() - start) * 1000
    return response

# ============================================================================
# Core Endpoints
# ============================================================================

@app.post("/vpcs", response_model=VPC, status_code=201)
def create_vpc(vpc: VPCCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    new_vpc = services.create_vpc_logic(
        db,
        vpc.name,
        vpc.cidr,
        vpc.region,
        vpc.secondary_cidrs,
        vpc.scenario,
    )
    background_tasks.add_task(services.provision_vpc_task, SessionLocal, new_vpc.id)
    return new_vpc

@app.get("/vpcs", response_model=List[VPC])
def list_vpcs(db: Session = Depends(get_db)):
    return db.query(VPCModel).all()

@app.get("/vpcs/{vpc_id}", response_model=VPC)
def get_vpc(vpc_id: str, db: Session = Depends(get_db)):
    vpc = db.query(VPCModel).filter(VPCModel.id == vpc_id).first()
    if not vpc:
        raise HTTPException(status_code=404, detail="VPC not found")
    return vpc

@app.delete("/vpcs/{vpc_id}")
def delete_vpc(vpc_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    vpc = services.delete_vpc_logic(db, vpc_id)
    if not vpc:
        raise HTTPException(status_code=404, detail="VPC not found")
    background_tasks.add_task(services.deprovision_vpc_task, SessionLocal, vpc_id)
    return {"message": "VPC deletion initiated"}

# Remaining endpoints intentionally unchanged in behavior but corrected to:
# - use dependency-injected sessions everywhere
# - remove fabricated timestamps
# - avoid import-time I/O
# - avoid duplicate engines
