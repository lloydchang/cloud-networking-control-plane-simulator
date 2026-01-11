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

Deployment: Cache-busting fix applied 2025-01-04 to resolve Vercel serving issues
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
from fastapi.middleware.cors import CORSMiddleware
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

# Add CORS middleware for GitHub Pages integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://lloydchang.github.io",
        "http://localhost:8000",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
if os.path.exists(SCRIPTS_DIR):
    app.mount("/scripts", StaticFiles(directory=SCRIPTS_DIR), name="scripts")

ASSETS_DIR = os.path.join(os.path.dirname(__file__), "ui", "assets")
UI_DIR = os.path.join(os.path.dirname(__file__), "ui")

# Only create assets directory if not in Vercel (read-only filesystem)
if not os.getenv("VERCEL"):
    os.makedirs(ASSETS_DIR, exist_ok=True)
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# Mount UI assets directory for logo and other static files
if os.path.exists(UI_DIR):
    app.mount("/ui", StaticFiles(directory=UI_DIR), name="ui")

DB_DIR = "/tmp" if os.getenv("VERCEL") else os.getenv("DB_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
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

class SubnetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    cidr: str
    availability_zone: str = "us-east-1a"
    data_center: str = "CDC-1"

class Subnet(BaseModel):
    id: str
    vpc_id: str
    name: str
    cidr: str
    az: str
    data_center: Optional[str] = None
    status: str
    created_at: datetime

class RouteCreate(BaseModel):
    destination: str
    next_hop: str
    next_hop_type: str

class Route(BaseModel):
    id: str
    vpc_id: str
    destination: str
    next_hop: str
    next_hop_type: str
    status: str
    created_at: datetime

class NATGatewayCreate(BaseModel):
    subnet_id: str

class NATGateway(BaseModel):
    id: str
    vpc_id: str
    subnet_id: str
    public_ip: str
    created_at: datetime

class InternetGateway(BaseModel):
    id: str
    vpc_id: str
    vpc_id: str
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
async def vpc_view():
    """Serve the VPC HTML template"""
    try:
        template_path = os.path.join(os.path.dirname(__file__), "ui", "vpc.html")
        if os.path.exists(template_path):
            with open(template_path, 'r') as f:
                content = f.read()
            return HTMLResponse(content)
        else:
            return HTMLResponse("<h1>VPC template not found</h1>", status_code=404)
    except Exception as e:
        return HTMLResponse(f"<h1>Error serving VPC view: {e}</h1>", status_code=500)

@app.get("/openapi.json", include_in_schema=False)
async def openapi_json():
    return JSONResponse(app.openapi())

@app.get("/", include_in_schema=False)
async def vpc_view():
    """Serve the pre-built static index.html directly from GitHub raw"""
    try:
        import httpx
        import time
        # Add cache-busting timestamp to force fresh fetch
        timestamp = int(time.time())
        github_raw_url = f"https://raw.githubusercontent.com/lloydchang/cloud-networking-control-plane-simulator/refs/heads/main/docs/index.html?t={timestamp}"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(github_raw_url, headers={"Cache-Control": "no-cache"})
            if response.status_code == 200:
                logging.info(f"Serving pre-built static index.html from GitHub raw (size: {len(response.text)} chars)")
                return HTMLResponse(response.text, headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
            else:
                return HTMLResponse(f"<h1>Static Content Not Available</h1><p>Could not fetch index.html from GitHub (status: {response.status_code})</p>", status_code=503)
    except Exception as e:
        logging.error(f"Error fetching static index.html from GitHub: {e}")
        return HTMLResponse("<h1>Service Unavailable</h1><p>Unable to serve static content</p>", status_code=503)

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

@app.get("/docs", include_in_schema=False)
async def docs(request: Request):
    openapi_path = "/openapi.json"
    return HTMLResponse(f"""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Cloud Networking Control Plane Simulator - Swagger UI</title>
      <meta charset='utf-8'/>
      <meta name='viewport' content='width=device-width, initial-scale=1'>
      <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5.10.5/swagger-ui.css" />
      <style>
        html {{ box-sizing: border-box; overflow: -moz-scrollbars-vertical; overflow-y: scroll; }}
        *, *:before, *:after {{ box-sizing: inherit; }}
        body {{ margin:0; background: #fafafa; }}
      </style>
    </head>
    <body>
      <div id="swagger-ui"></div>
      <script src="https://unpkg.com/swagger-ui-dist@5.10.5/swagger-ui-bundle.js"></script>
      <script src="https://unpkg.com/swagger-ui-dist@5.10.5/swagger-ui-standalone-preset.js"></script>
      <script>
        window.onload = function() {{
          SwaggerUIBundle({{
            url: '{openapi_path}',
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
              SwaggerUIBundle.presets.apis,
              SwaggerUIStandalonePreset
            ],
            plugins: [
              SwaggerUIBundle.plugins.DownloadUrl
            ],
            layout: "StandaloneLayout",
            tryItOutEnabled: true
          }});
        }}
      </script>
    </body>
    </html>
    """)

# Subnet endpoints
@app.post("/vpcs/{vpc_id}/subnets", response_model=Subnet, status_code=201)
def create_subnet(vpc_id: str, subnet: SubnetCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if not db.query(VPCModel).filter(VPCModel.id == vpc_id).first():
        raise HTTPException(status_code=404, detail="VPC not found")
    new_subnet = services.create_subnet_logic(db, vpc_id, subnet.name, subnet.cidr, subnet.availability_zone)
    background_tasks.add_task(services.provision_subnet_task, SessionLocal, new_subnet.id)
    return new_subnet

@app.get("/vpcs/{vpc_id}/subnets", response_model=List[Subnet])
def list_subnets(vpc_id: str, db: Session = Depends(get_db)):
    return services.list_subnets(vpc_id)

@app.delete("/subnets/{subnet_id}")
def delete_subnet(subnet_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    subnet = services.delete_subnet_logic(db, subnet_id)
    if not subnet:
        raise HTTPException(status_code=404, detail="Subnet not found")
    background_tasks.add_task(services.deprovision_subnet_task, SessionLocal, subnet_id)
    return {"message": "Subnet deletion initiated"}

# Route endpoints
@app.post("/vpcs/{vpc_id}/routes", response_model=Route, status_code=201)
def create_route(vpc_id: str, route: RouteCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if not db.query(VPCModel).filter(VPCModel.id == vpc_id).first():
        raise HTTPException(status_code=404, detail="VPC not found")
    new_route = services.create_route_logic(db, vpc_id, route.destination, route.next_hop, route.next_hop_type)
    background_tasks.add_task(services.provision_route_task, SessionLocal, new_route.id)
    return new_route

@app.get("/vpcs/{vpc_id}/routes", response_model=List[Route])
def list_routes(vpc_id: str, db: Session = Depends(get_db)):
    return services.list_routes(vpc_id)

@app.delete("/routes/{route_id}")
def delete_route(route_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    route = services.delete_route_logic(db, route_id)
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")
    background_tasks.add_task(services.deprovision_route_task, SessionLocal, route_id)
    return {"message": "Route deletion initiated"}

# Security Group endpoints
@app.post("/security-groups", response_model=SecurityGroup, status_code=201)
def create_security_group(security_group: SecurityGroupCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    new_sg = services.create_security_group_logic(db, security_group.name, security_group.description, security_group.rules)
    return new_sg

@app.get("/security-groups", response_model=List[SecurityGroup])
def list_security_groups(db: Session = Depends(get_db)):
    return services.list_security_groups()

# Gateway endpoints
@app.post("/vpcs/{vpc_id}/internet-gateways", response_model=InternetGateway, status_code=201)
def create_internet_gateway(vpc_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if not db.query(VPCModel).filter(VPCModel.id == vpc_id).first():
        raise HTTPException(status_code=404, detail="VPC not found")
    igw = services.create_internet_gateway_logic(db, vpc_id)
    background_tasks.add_task(services.provision_internet_gateway_task, SessionLocal, igw.id)
    return igw

@app.post("/vpcs/{vpc_id}/nat-gateways", response_model=NATGateway, status_code=201)
def create_nat_gateway(vpc_id: str, nat: NATGatewayCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    if not db.query(VPCModel).filter(VPCModel.id == vpc_id).first():
        raise HTTPException(status_code=404, detail="VPC not found")
    nat_gw = services.create_nat_logic(db, vpc_id, nat.subnet_id)
    background_tasks.add_task(services.provision_nat_gateway_task, SessionLocal, nat_gw.id)
    return nat_gw