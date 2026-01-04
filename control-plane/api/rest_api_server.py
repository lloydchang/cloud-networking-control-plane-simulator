# File: control-plane/api/rest_api_server.py
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
import json
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, Response, HTMLResponse
from pydantic import BaseModel, Field

from sqlalchemy import create_engine, text, Table, MetaData, select, insert, update
from sqlalchemy.orm import sessionmaker, Session

import logging
logging.basicConfig(level=logging.INFO)

try:
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

try:
    from metrics import METRICS
except ImportError:
    METRICS = {}
    PROMETHEUS_AVAILABLE = False

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
    VniCounter as VniCounterModel
)
from . import shared_api_logic as services

app = FastAPI(
    title="Cloud Networking Control Plane Simulator - Control Plane API",
    description="Cloud Networking Control Plane Simulator - Control Plane API",
    version="1.0.0",
    redoc_url=None,  # Disable built-in ReDoc
)

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
if os.path.exists(SCRIPTS_DIR):
    app.mount("/scripts", StaticFiles(directory=SCRIPTS_DIR), name="scripts")

ASSETS_DIR = "/app/assets"
UI_DIR = os.path.join(os.path.dirname(__file__), "ui")

# Only create assets directory if not in Vercel (read-only filesystem)
if not os.getenv("VERCEL"):
    os.makedirs(ASSETS_DIR, exist_ok=True)
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# Mount UI assets directory for logo and other static files
if os.path.exists(UI_DIR):
    app.mount("/ui", StaticFiles(directory=UI_DIR), name="ui")

DB_DIR = "/tmp" if os.getenv("VERCEL") else os.getenv("DB_DIR", "/app/data")
DB_PATH = os.getenv("DB_PATH", f"{DB_DIR}/network.db")
if not DB_PATH.startswith(":memory:"):
    os.makedirs(DB_DIR, exist_ok=True)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

@app.on_event("startup")
def initialize_database_and_metrics():
    db = SessionLocal()
    try:
        # Initialize vni_counter table if it doesn't exist
        try:
            db.execute(text("CREATE TABLE IF NOT EXISTS vni_counter (id INTEGER PRIMARY KEY, current INTEGER NOT NULL);"))
            db.commit()
        except Exception as e:
            logging.warning(f"Could not create vni_counter table: {e}")

        # Initialize vni_counter row if it doesn't exist
        try:
            metadata = MetaData()
            vni_counter = Table("vni_counter", metadata, autoload_with=engine)
            row = db.execute(select(vni_counter).where(vni_counter.c.id == 1)).fetchone()
            if not row:
                db.execute(insert(vni_counter).values(id=1, current=1003))
                db.commit()
                logging.info("Inserted initial vni_counter row with id=1 and current=1003")
            else:
                logging.info(f"vni_counter exists with current={row['current']}")
        except Exception as e:
            logging.warning(f"Could not initialize vni_counter: {e}")

        # Initialize metrics if available
        if PROMETHEUS_AVAILABLE:
            try:
                METRICS["vpcs_total"].set(db.query(VPCModel).count())
                METRICS["subnets_total"].set(db.query(SubnetModel).count())
                METRICS["routes_total"].set(db.query(RouteModel).count())
                METRICS["security_groups_total"].set(db.query(SGModel).count())
                METRICS["nat_gateways_total"].set(db.query(NATModel).count())
                METRICS["internet_gateways_total"].set(db.query(InternetGatewayModel).count())
            except Exception as e:
                logging.warning(f"Could not initialize metrics: {e}")

        # Generate OpenAPI spec
        try:
            if not os.getenv("VERCEL"):
                openapi_path = os.path.join(ASSETS_DIR, "openapi.json")
                with open(openapi_path, "w") as f:
                    json.dump(app.openapi(), f)
        except Exception as e:
            logging.warning(f"Could not generate OpenAPI spec: {e}")
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/metrics")
def metrics():
    if not PROMETHEUS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Prometheus client not installed")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    if PROMETHEUS_AVAILABLE:
        METRICS["api_requests"].labels(method=request.method, endpoint=request.url.path).inc()
    start = time.time()
    response = await call_next(request)
    _ = (time.time() - start) * 1000
    return response

@app.post("/vpcs", response_model=VPC, status_code=201)
def create_vpc(vpc: VPCCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    new_vpc = services.create_vpc_logic(db, vpc.name, vpc.cidr, vpc.region, vpc.secondary_cidrs, vpc.scenario)
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

@app.get("/vpc", include_in_schema=False)
async def get_vpc_data():
    """Get all VPC data for the VPC view"""
    db = SessionLocal()
    try:
        vpcs = db.query(VPCModel).all()
        
        # Transform VPCs into nodes format
        nodes = []
        edges = []
        
        for vpc in vpcs:
            nodes.append({
                "id": vpc.id,
                "type": "vpc",
                "label": vpc.name,
                "cidr": vpc.cidr,
                "region": vpc.region,
                "secondary_cidrs": vpc.secondary_cidrs or [],
                "scenario": vpc.scenario,
                "status": vpc.status,
                "created_at": vpc.created_at.isoformat() if vpc.created_at else None
            })
        
        return {
            "nodes": nodes,
            "edges": edges,
            "scenarios": []
        }
    finally:
        db.close()

@app.get("/openapi.json", include_in_schema=False)
async def openapi_json():
    return JSONResponse(app.openapi())

@app.get("/", include_in_schema=False)
async def vpc_view():
    """Serve the VPC view HTML page"""
    vpc_html_path = os.path.join(os.path.dirname(__file__), "ui", "vpc.html")
    try:
        with open(vpc_html_path, "r") as f:
            return HTMLResponse(f.read())
    except FileNotFoundError:
        return HTMLResponse("<h1>VPC View Not Found</h1><p>The VPC view HTML file could not be found.</p>", status_code=404)

@app.get("/redoc", include_in_schema=False)
async def redoc(request: Request):
    openapi_path = "/openapi.json"
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Cloud Networking Control Plane Simulator - ReDoc</title>
      <meta charset='utf-8'/>
      <meta name='viewport' content='width=device-width, initial-scale=1'>
      <link href='https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700' rel='stylesheet'>
      <style>
        body {{ margin: 0; padding: 0; }}
        redoc {{ height: 100vh; }}
      </style>
    </head>
    <body>
      <redoc spec-url='{openapi_path}'></redoc>
      <script src='https://cdn.jsdelivr.net/npm/redoc@2.0.0/bundles/redoc.standalone.js'></script>
    </body>
    </html>
    """)