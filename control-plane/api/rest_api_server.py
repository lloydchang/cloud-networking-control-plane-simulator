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
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Request
from pydantic import BaseModel, Field
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
from fastapi.staticfiles import StaticFiles
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from metrics import METRICS
from starlette.responses import Response, HTMLResponse

app = FastAPI(
    title="Cloud Networking Simulator - Control Plane API",
    description="Cloud Networking Simulator - Control Plane API",
    version="1.0.0",
)

# Expose scripts for scenario-specific UI logic
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
if os.path.exists(SCRIPTS_DIR):
    app.mount("/scripts", StaticFiles(directory=SCRIPTS_DIR), name="scripts")

# Serve static assets (images, CSS, JS)
ASSETS_DIR = "/app/assets"
if os.path.exists(ASSETS_DIR):
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")

# ============================================================================
# Database Configuration (SQLite for Persistence)
# ============================================================================

DB_DIR = os.getenv("DB_DIR", "/app/data")
DB_PATH = os.getenv("DB_PATH", f"{DB_DIR}/network.db")

# Ensure data directory exists if it's not a special sqlite path
if not os.path.exists(DB_DIR) and not DB_PATH.startswith(":memory:"):
    try:
        os.makedirs(DB_DIR, exist_ok=True)
    except OSError:
        # Fallback for read-only environments during testing if needed
        pass

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# Quick runtime check of DB
from sqlalchemy import create_engine, inspect
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})

inspector = inspect(engine)
print("SQLite tables:", inspector.get_table_names())

# Optional: test a simple query
try:
    with engine.connect() as conn:
        result = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        print("Tables in DB:", [row[0] for row in result])
except Exception as e:
    print("DB check error:", e)


engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


@app.on_event("startup")
def initialize_metrics():
    """Initialize Prometheus metrics from current database state."""
    db = SessionLocal()
    try:
        # Resource counts
        METRICS["vpcs_total"].set(db.query(VPCModel).count())
        METRICS["subnets_total"].set(db.query(SubnetModel).count())
        METRICS["routes_total"].set(db.query(RouteModel).count())
        METRICS["security_groups_total"].set(db.query(SGModel).count())
        METRICS["nat_gateways_total"].set(db.query(NATModel).count())
        METRICS["internet_gateways_total"].set(db.query(InternetGatewayModel).count())
        # TODO: Add metrics for gateways
        
        print("Initialized all resource metrics.")
    finally:
        db.close()


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Metrics are imported from metrics.py

# ============================================================================
# Pydantic Models
# ============================================================================


class VPCCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    cidr: str = Field(..., pattern=r"^[a-fA-F0-9\.:/ ]+( & [a-fA-F0-9\.:/ ]+)*$")
    region: str = "us-east-1"
    secondary_cidrs: List[str] = [] # For Kubernetes/Pod subnets
    scenario: Optional[str] = None


class VPC(BaseModel):
    id: str
    name: str
    cidr: str
    region: str
    secondary_cidrs: List[str] # For Kubernetes/Pod subnets
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

class CloudRoutingHubCreate(BaseModel):
    name: str
    region: str = "global"
    scenario: Optional[str] = None

class CloudRoutingHub(BaseModel):
    id: str
    name: str
    region: str
    scenario: Optional[str] = None
    created_at: datetime


class ScenarioResource(BaseModel):
    type: str # 'vpc' or 'hub'
    label: str

class ScenarioCreate(BaseModel):
    title: str
    description: Optional[str] = None
    resource_order: Optional[List[ScenarioResource]] = None

class Scenario(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    resource_order: List[ScenarioResource]
    created_at: datetime


class StandaloneDCCreate(BaseModel):
    name: str
    cidr: str
    region: str = "on-prem"
    scenario: Optional[str] = None


class StandaloneDC(BaseModel):
    id: str
    name: str
    cidr: str
    region: str
    scenario: Optional[str]
    created_at: datetime


class StandaloneDCSubnetCreate(BaseModel):
    name: str
    cidr: str
    data_center: str = "DC-1"


class SubnetCreate(BaseModel):
    name: str
    cidr: str
    data_center: str = "DC-NORTH"


class Subnet(BaseModel):
    id: str
    vpc_id: str
    name: str
    cidr: str
    gateway: str
    data_center: str
    status: str
    created_at: datetime


class RouteCreate(BaseModel):
    destination: str
    next_hop: str
    next_hop_type: str = Field(..., pattern=r"^(gateway|nat|instance|vpc_peering|vpn_gateway|mesh_vpn|cloud_routing_hub|internet_gateway|nat_gateway|hub_peer|service_endpoint|service_mesh|private_link)$")


class Route(BaseModel):
    id: str
    vpc_id: Optional[str] = None
    hub_id: Optional[str] = None
    dc_id: Optional[str] = None
    destination: str
    next_hop: str
    next_hop_type: str
    priority: int
    status: str


class SecurityRuleCreate(BaseModel):
    direction: str = Field(..., pattern=r"^(ingress|egress)$")
    protocol: str = Field(..., pattern=r"^(tcp|udp|icmp|all)$")
    port_from: Optional[int] = None
    port_to: Optional[int] = None
    cidr: str = "0.0.0.0/0"


class SecurityGroupCreate(BaseModel):
    name: str
    description: str = ""
    rules: List[SecurityRuleCreate] = []


class SecurityGroup(BaseModel):
    id: str
    name: str
    description: str
    rules: List[dict]
    created_at: datetime


class NATGatewayCreate(BaseModel):
    subnet_id: str


class NATGateway(BaseModel):
    id: str
    vpc_id: str
    subnet_id: str
    public_ip: str
    status: str
    created_at: datetime


class InternetGatewayCreate(BaseModel):
    pass


class InternetGateway(BaseModel):
    id: str
    vpc_id: str
    status: str
    created_at: datetime


class VPNGatewayCreate(BaseModel):
    endpoint: str
    public_key: str
    allowed_ips: str


class VPNGateway(BaseModel):
    id: str
    vpc_id: str
    endpoint: str
    public_key: str
    allowed_ips: str


class MeshNodeCreate(BaseModel):
    node_key: str
    tailnet: str


class MeshNode(BaseModel):
    id: str
    vpc_id: str
    node_key: str
    tailnet: str

# ============================================================================
# Favicon handler to prevent 500 errors if favicon is missing
# ============================================================================

@app.get("/favicon.png")
@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)

# ============================================================================
# Health Check
# ============================================================================


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "cloud-networking-controller"}


@app.get("/metrics")
async def metrics():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.middleware("http")
async def prometheus_middleware(request, call_next):
    method = request.method
    path = request.url.path

    # Track request count
    METRICS["api_requests"].labels(method=method, endpoint=path).inc()

    start_time = time.time()
    response = await call_next(request)
    process_time = (time.time() - start_time) * 1000

    # We could track latency per endpoint here if needed
    return response




@app.get("/vpc", response_class=Response)
def get_vpc_view(request: Request, db: Session = Depends(get_db)):
    """
    Returns the VPC View.
    - If Accept header contains 'text/html', serves the interactive VPC-centric UI.
    - Otherwise, returns a JSON representation of the VPC object model.
    """
    accept = request.headers.get("accept", "")
    
    # 1. Serve HTML UI if requested by a browser
    if "text/html" in accept:
        ui_path = os.path.join(os.path.dirname(__file__), "ui", "vpc.html")
        if not os.path.exists(ui_path):
            return HTMLResponse("VPC View UI not found. Run 'make build' to ensure UI files are present.", status_code=404)
        
        with open(ui_path, "r") as f:
            return HTMLResponse(content=f.read())

    # 2. Return JSON for API/Script usage
    print("DEBUG: Executing /vpc JSON response logic")
    nodes = []
    edges = []

    # Underlay (Physical Ground - The Site Gateways)
    # We maintain a consistent set of physical landing points for our logical VPCs
    known_dcs = ["CDC-1", "CDC-2", "CDC-3", "CDC-11", "CDC-12", "CDC-13", "ODC-1", "DC-NORTH", "DC-SOUTH"]
    
    hubs = db.query(models.CloudRoutingHub).all()
    for hub in hubs:
        hub_routes = db.query(RouteModel).filter(RouteModel.hub_id == hub.id).all()
        nodes.append({
            "id": f"hub-{hub.id}",
            "label": hub.name,
            "type": "hub",
            "region": hub.region,
            "scenario": hub.scenario,
            "routes": [
                {
                    "destination": r.destination,
                    "next_hop": r.next_hop,
                    "next_hop_type": r.next_hop_type
                } for r in hub_routes
            ]
        })
    leaves = []
    for dc in known_dcs:
        leaf_id = f"leaf-{dc.lower().replace('cdc-', '').replace('odc-', '').replace('dc-', '')}"
        leaves.append(leaf_id)
        # Use CDC for cloud-like DCs, keep DC/ODC for generic sites
        site_label = f"Site Switch ({dc})"
        nodes.append({"id": leaf_id, "label": site_label, "type": "leaf"})

    # Overlay: VPCs and their managed resources
    vpcs = db.query(VPCModel).all()
    for vpc in vpcs:
        vpc_node_id = f"vpc-{vpc.id}"
        nodes.append({
            "id": vpc_node_id, 
            "label": vpc.name, 
            "type": "vpc", 
            "cidr": vpc.cidr,
            "scenario": vpc.scenario
        })
        
        # Subnets & DC Grouping
        subnets = db.query(SubnetModel).filter(SubnetModel.vpc_id == vpc.id).all()
        dc_parents = {} # Track DC nodes per VPC
        active_dcs = set()
        
        for subnet in subnets:
            dc_name = subnet.az 
            dc_id = f"vpc-{vpc.id}-dc-{dc_name}"
            active_dcs.add(dc_name)
            
            # Create DC parent node if it doesn't exist
            if dc_id not in dc_parents:
                nodes.append({
                    "id": dc_id,
                    "label": f"Cloud Data Center: {dc_name}",
                    "type": "dc",
                    "parent": vpc_node_id
                })
                dc_parents[dc_id] = dc_name

            subnet_node_id = f"subnet-{subnet.id}"
            subnet_type = "server" if "Server" in subnet.name else "subnet"
            subnet_cidr = subnet.cidr.replace("/32", "") if subnet_type == "server" else subnet.cidr
            
            nodes.append({
                "id": subnet_node_id, 
                "label": f"{subnet.name} ({subnet_cidr})", 
                "type": subnet_type, 
                "cidr": subnet_cidr,
                "parent": dc_id
            })

        # Physical Placement (Overlay link to Leaves)
        # Show where the VPC 'lands' based on its subnets
        for dc_name in active_dcs:
            # Connect the VPC to the Leaf switch representing that DC
            # (In this simulator, we'll map DC-1 to leaf-1, DC-11 to leaf-1, etc or just use DC-NORTH)
            leaf_id = f"leaf-{dc_name.lower().replace('cdc-', '').replace('odc-', '').replace('dc-', '')}"
            if leaf_id in leaves:
                edges.append({
                    "source": leaf_id, 
                    "target": vpc_node_id, 
                    "type": "overlay",
                    "label": "Logical Membership"
                })

        # Gateways (Inside VPC container)
        nats = db.query(NATModel).filter(NATModel.vpc_id == vpc.id).all()
        for nat in nats:
            nat_node_id = f"nat-{nat.id}"
            # Find the subnet's DC to place the NAT GW correctly
            parent_id = vpc_node_id # Default
            for s in subnets:
                if s.id == nat.subnet_id:
                    parent_id = f"vpc-{vpc.id}-dc-{s.az}"
                    break

            nodes.append({
                "id": nat_node_id, 
                "label": "NAT GW", 
                "type": "nat", 
                "parent": parent_id
            })

        igws = db.query(InternetGatewayModel).filter(InternetGatewayModel.vpc_id == vpc.id).all()
        for igw in igws:
            igw_node_id = f"igw-{igw.id}"
            nodes.append({
                "id": igw_node_id, 
                "label": "Internet GW", 
                "type": "igw", 
                "parent": vpc_node_id # IGW is VPC-wide/Regional
            })

        # VPN Gateways
        vpn_gateways = db.query(VPNGatewayModel).filter(VPNGatewayModel.vpc_id == vpc.id).all()
        for vpn_gw in vpn_gateways:
            vpn_node_id = f"vpn-gateway-{vpn_gw.id}"
            nodes.append({
                "id": vpn_node_id,
                "label": f"VPN Gateway\n{vpn_gw.endpoint}",
                "type": "vpn_gateway",
                "parent": vpc_node_id
            })

        # Mesh Nodes
        mesh_nodes = db.query(MeshNodeModel).filter(MeshNodeModel.vpc_id == vpc.id).all()
        for mesh_node in mesh_nodes:
            mesh_node_id = f"mesh-node-{mesh_node.id}"
            nodes.append({
                "id": mesh_node_id,
                "label": f"Mesh Node\n{mesh_node.node_key[:8]}...",
                "type": "mesh_node",
                "parent": vpc_node_id
            })

        # Inter-VPC Connections (Multiple Types)
        routes = db.query(RouteModel).filter(RouteModel.vpc_id == vpc.id).all()
        for route in routes:
            # Map next_hop_type to visual edge type
            edge_type_map = {
                "vpc_peering": ("peering", "VPC Peering"),
                "vpn_gateway": ("vpn", "VPN Gateway"),
                "mesh_vpn": ("mesh", "Mesh VPN"),
                "cloud_routing_hub": ("cloud_routing_hub", "Cloud Routing Hub"),
                "internet_gateway": ("internet", "Internet"),
                "nat_gateway": ("nat_route", "NAT Gateway"),
            }
            
            if route.next_hop_type in edge_type_map:
                edge_type, edge_label = edge_type_map[route.next_hop_type]
                # Determine target - could be another VPC, a hub, or a gateway
                if str(route.next_hop).startswith("hub-"):
                    target_id = f"hub-{route.next_hop}"
                elif route.next_hop_type in ["vpc_peering", "mesh_vpn"]:
                    target_id = f"vpc-{route.next_hop}"
                elif route.next_hop_type == "vpn_gateway":
                    # Handle VPN gateway targets - could be VPC or standalone DC
                    if str(route.next_hop).startswith("dc-"):
                        target_id = f"standalone-dc-{route.next_hop}"
                    else:
                        target_id = f"vpc-{route.next_hop}"
                else:
                    target_id = route.next_hop
                
                edges.append({
                    "source": vpc_node_id,
                    "target": target_id,
                    "type": edge_type,
                    "label": edge_label,
                    "destination": route.destination
                })

    # Standalone Data Centers
    standalone_dcs = db.query(StandaloneDCModel).all()
    for sdc in standalone_dcs:
        sdc_node_id = f"standalone-dc-{sdc.id}"
        nodes.append({
            "id": sdc_node_id,
            "label": sdc.name,
            "type": "standalone_dc",
            "cidr": sdc.cidr,
            "region": sdc.region,
            "scenario": sdc.scenario
        })
        
        # Standalone DC Subnets
        sdc_subnets = db.query(StandaloneDCSubnetModel).filter(StandaloneDCSubnetModel.dc_id == sdc.id).all()
        for subnet in sdc_subnets:
            subnet_node_id = f"dc-subnet-{subnet.id}"
            subnet_type = "server" if "Server" in subnet.name else "subnet"
            subnet_cidr = subnet.cidr.replace("/32", "") if subnet_type == "server" else subnet.cidr
            
            nodes.append({
                "id": subnet_node_id,
                "label": f"{subnet.name} ({subnet_cidr})",
                "type": subnet_type,
                "cidr": subnet_cidr,
                "parent": sdc_node_id
            })

        # Standalone DC Routes
        sdc_routes = db.query(RouteModel).filter(RouteModel.dc_id == sdc.id).all()
        for route in sdc_routes:
            edge_type_map = {
                "vpc_peering": ("peering", "VPC Peering"),
                "vpn_gateway": ("vpn", "VPN Gateway"),
                "mesh_vpn": ("mesh", "Mesh VPN"),
                "cloud_routing_hub": ("cloud_routing_hub", "Cloud Routing Hub"),
            }
            if route.next_hop_type in edge_type_map:
                edge_type, edge_label = edge_type_map[route.next_hop_type]
                # Handle VPN gateway targets - could be VPC or standalone DC
                if str(route.next_hop).startswith("hub-"):
                    target_id = f"hub-{route.next_hop}"
                elif route.next_hop_type == "vpn_gateway":
                    if str(route.next_hop).startswith("vpc-"):
                        target_id = f"vpc-{route.next_hop}"
                    else:
                        target_id = f"standalone-dc-{route.next_hop}"
                else:
                    target_id = route.next_hop
                edges.append({
                    "source": sdc_node_id,
                    "target": target_id,
                    "type": edge_type,
                    "label": edge_label,
                    "destination": route.destination
                })

    # Global Scenarios
    scenarios = db.query(models.Scenario).all()
    
    # Sort scenarios by a preferred order
    # Sort scenarios dynamically based on the numeric prefix in the title
    # Format expected: "X. Title"
    import re
    
    def get_scenario_number(title):
        match = re.match(r"^(\d+)\.", title)
        if match:
            n = int(match.group(1))
            # Return large number for 0 so it sorts last
            return n if n > 0 else 999
        return 999 # Put non-numbered scenarios at the end

    sorted_scenarios = sorted(
        scenarios, 
        key=lambda s: get_scenario_number(s.title)
    )
    
    scenario_list = []
    for s in sorted_scenarios:
        scenario_list.append({
            "title": s.title,
            "description": s.description,
            "resources": s.resource_order
        })

    import json
    response_data = {
        "nodes": nodes, 
        "edges": edges,
        "scenarios": scenario_list
    }
    return Response(content=json.dumps(response_data), media_type="application/json")

# File: rest_api_server.py
#!/usr/bin/env python3
"""
Full Cloud Networking REST API Server
Includes VPC, Subnet, Route, Security Groups, NAT, IGW, VPN, Mesh, Cloud Routing Hub, Standalone DC, and VPC Endpoints.
"""

@app.get("/vpcs/{vpc_id}/endpoints", response_model=List[VPCEndpoint])
def list_vpc_endpoints(vpc_id: str, db: Session = Depends(get_db)):
    print(f"DEBUG: Querying VPC with ID {vpc_id}")
    vpc = db.query(VPCModel).filter(VPCModel.id == vpc_id).first()
    print(f"DEBUG: VPC found: {vpc}")
    if not vpc:
        raise HTTPException(status_code=404, detail="VPC not found")
    return services.list_vpc_endpoints(db, vpc_id)

@app.post("/vpcs/{vpc_id}/endpoints", response_model=VPCEndpoint, status_code=201)
def create_vpc_endpoint(vpc_id: str, payload: VPCEndpointCreate, db: Session = Depends(get_db)):
    print(f"DEBUG: create_vpc_endpoint called for vpc_id: {vpc_id}")
    vpc = db.query(VPCModel).filter(VPCModel.id == vpc_id).first()
    if not vpc:
        print(f"DEBUG: VPC {vpc_id} NOT FOUND in database")
        raise HTTPException(status_code=404, detail="VPC not found")
    print(f"DEBUG: Found VPC: {vpc.name}. Attempting to create endpoint: {payload.name} ({payload.ip})")
    try:
        endpoint = services.create_vpc_endpoint(db, vpc_id, payload.name, payload.ip)
        return endpoint
    except ValueError as e:
        # Handle conflict detection errors with proper HTTP status
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        # Handle other unexpected errors
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.delete("/vpcs/{vpc_id}/endpoints/{endpoint_id}")
def delete_vpc_endpoint(vpc_id: str, endpoint_id: str, db: Session = Depends(get_db)):
    success = services.delete_vpc_endpoint(db, vpc_id, endpoint_id)
    if not success:
        raise HTTPException(status_code=404, detail="Endpoint not found")
    return {"message": f"Endpoint {endpoint_id} deleted from VPC {vpc_id}"}

@app.delete("/hubs/{hub_id}")
def delete_hub(hub_id: str, db: Session = Depends(get_db)):
    hub = services.delete_hub_logic(db, hub_id)
    if not hub:
        raise HTTPException(status_code=404, detail="Hub not found")
    return {"message": "Hub deleted successfully"}


@app.post("/hubs", response_model=CloudRoutingHub, status_code=201)
def create_hub(hub: CloudRoutingHubCreate, db: Session = Depends(get_db)):
    return services.create_hub_logic(db, hub.name, hub.region, hub.scenario)

@app.post("/hubs/{hub_id}/routes", response_model=Route)
def create_hub_route(hub_id: str, route: RouteCreate, db: Session = Depends(get_db)):
    db_hub = db.query(models.CloudRoutingHub).filter(models.CloudRoutingHub.id == hub_id).first()
    if not db_hub:
        raise HTTPException(status_code=404, detail="Hub not found")
        
    route_id = f"route-hub-{uuid.uuid4().hex[:8]}"
    db_route = models.Route(
        id=route_id,
        hub_id=hub_id,
        destination=route.destination,
        next_hop=route.next_hop,
        next_hop_type=route.next_hop_type
    )
    db.add(db_route)
    db.commit()
    db.refresh(db_route)
    return db_route


@app.post("/scenarios", response_model=Scenario, status_code=201)
def create_scenario(scenario: ScenarioCreate, db: Session = Depends(get_db)):
    # Convert resource_order to dict for storage if it's a list of ScenarioResource
    resource_order_data = [r.dict() for r in scenario.resource_order] if scenario.resource_order else []
    return services.create_scenario_logic(db, scenario.title, scenario.description, resource_order_data)


@app.get("/scenarios", response_model=List[Scenario])
def list_scenarios(db: Session = Depends(get_db)):
    return db.query(models.Scenario).all()


@app.post("/standalone-dcs", response_model=StandaloneDC, status_code=201)
def create_standalone_dc(dc: StandaloneDCCreate, db: Session = Depends(get_db)):
    return services.create_standalone_dc_logic(db, dc.name, dc.cidr, dc.region, dc.scenario)


@app.delete("/standalone-dcs/{dc_id}")
def delete_standalone_dc(dc_id: str, db: Session = Depends(get_db)):
    dc = services.delete_standalone_dc_logic(db, dc_id)
    if not dc:
        raise HTTPException(status_code=404, detail="Standalone DC not found")
    return {"message": "Standalone DC deleted successfully"}


@app.post("/standalone-dcs/{dc_id}/subnets", status_code=201)
def create_standalone_dc_subnet(dc_id: str, subnet: StandaloneDCSubnetCreate, db: Session = Depends(get_db)):
    dc = db.query(StandaloneDCModel).filter(StandaloneDCModel.id == dc_id).first()
    if not dc:
        raise HTTPException(status_code=404, detail="Standalone DC not found")
    
    return services.create_standalone_dc_subnet_logic(db, dc_id, subnet.name, subnet.cidr, subnet.data_center)


@app.post("/standalone-dcs/{dc_id}/routes", response_model=Route, status_code=201)
def create_standalone_dc_route(dc_id: str, route: RouteCreate, db: Session = Depends(get_db)):
    dc = db.query(StandaloneDCModel).filter(StandaloneDCModel.id == dc_id).first()
    if not dc:
        raise HTTPException(status_code=404, detail="Standalone DC not found")
        
    return services.create_standalone_dc_route_logic(db, dc_id, route.destination, route.next_hop, route.next_hop_type)


@app.get("/")
async def root():
    return {
        "service": "Cloud Networking Simulator - Control Plane API",
        "version": "1.0.0",
        "endpoints": [
            "/vpcs",
            "/vpcs/{vpc_id}/subnets",
            "/vpcs/{vpc_id}/routes",
            "/vpcs/{vpc_id}/nat-gateways",
            "/vpcs/{vpc_id}/internet-gateways",
            "/security-groups",
        ],
    }


# ============================================================================
# VPC Endpoints
# ============================================================================


@app.post("/vpcs", response_model=VPC, status_code=201)
def create_vpc(
    vpc: VPCCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    new_vpc = services.create_vpc_logic(db, vpc.name, vpc.cidr, vpc.region, vpc.secondary_cidrs, vpc.scenario)

    # Trigger background provisioning
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
def delete_vpc(
    vpc_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    vpc = services.delete_vpc_logic(db, vpc_id)
    if not vpc:
        raise HTTPException(status_code=404, detail="VPC not found")

    background_tasks.add_task(services.deprovision_vpc_task, SessionLocal, vpc_id)

    return {"message": "VPC deletion initiated"}


# ============================================================================
# Subnet Endpoints
# ============================================================================


@app.post("/vpcs/{vpc_id}/subnets", response_model=Subnet, status_code=201)
def create_subnet(
    vpc_id: str,
    subnet: SubnetCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    vpc = db.query(VPCModel).filter(VPCModel.id == vpc_id).first()
    if not vpc:
        raise HTTPException(status_code=404, detail="VPC not found")

    new_subnet = services.create_subnet_logic(
        db, vpc_id, subnet.name, subnet.cidr, subnet.data_center
    )
    background_tasks.add_task(
        services.provision_subnet_task, SessionLocal, new_subnet.id
    )

    return Subnet(
        id=new_subnet.id,
        vpc_id=new_subnet.vpc_id,
        name=new_subnet.name,
        cidr=new_subnet.cidr,
        gateway=new_subnet.gateway,
        data_center=new_subnet.az,
        status="provisioning",
        created_at=datetime.utcnow(),
    )


@app.get("/vpcs/{vpc_id}/subnets", response_model=List[Subnet])
def list_subnets(vpc_id: str, db: Session = Depends(get_db)):
    subnets = db.query(SubnetModel).filter(SubnetModel.vpc_id == vpc_id).all()
    return [
        Subnet(
            id=s.id,
            vpc_id=s.vpc_id,
            name=s.name,
            cidr=s.cidr,
            gateway=s.gateway,
            data_center=s.az,
            status="available",
            created_at=datetime.utcnow(),
        )
        for s in subnets
    ]


@app.delete("/subnets/{subnet_id}")
def delete_subnet(
    subnet_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    subnet = db.query(SubnetModel).filter(SubnetModel.id == subnet_id).first()
    if not subnet:
        raise HTTPException(status_code=404, detail="Subnet not found")

    db.delete(subnet)
    db.commit()
    background_tasks.add_task(services.deprovision_subnet_task, SessionLocal, subnet_id)

    return {"message": "Subnet deletion initiated"}


# ============================================================================
# Route Endpoints
# ============================================================================


@app.post("/vpcs/{vpc_id}/routes", response_model=Route, status_code=201)
def create_route(
    vpc_id: str,
    route: RouteCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    vpc = db.query(VPCModel).filter(VPCModel.id == vpc_id).first()
    if not vpc:
        raise HTTPException(status_code=404, detail="VPC not found")

    new_route = services.create_route_logic(
        db, vpc_id, route.destination, route.next_hop, route.next_hop_type
    )
    background_tasks.add_task(services.provision_route_task, SessionLocal, new_route.id)

    return Route(
        id=new_route.id,
        vpc_id=new_route.vpc_id,
        destination=new_route.destination,
        next_hop=new_route.next_hop,
        next_hop_type=new_route.next_hop_type,
        priority=new_route.priority,
        status="provisioning",
    )


@app.get("/vpcs/{vpc_id}/routes", response_model=List[Route])
def list_routes(vpc_id: str, db: Session = Depends(get_db)):
    routes = db.query(RouteModel).filter(RouteModel.vpc_id == vpc_id).all()
    return [
        Route(
            id=r.id,
            vpc_id=r.vpc_id,
            destination=r.destination,
            next_hop=r.next_hop,
            next_hop_type=r.next_hop_type,
            priority=r.priority,
            status="active",
        )
        for r in routes
    ]


@app.delete("/routes/{route_id}")
def delete_route(
    route_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    route = db.query(RouteModel).filter(RouteModel.id == route_id).first()
    if not route:
        raise HTTPException(status_code=404, detail="Route not found")

    db.delete(route)
    db.commit()
    background_tasks.add_task(services.deprovision_route_task, SessionLocal, route_id)

    return {"message": "Route deletion initiated"}


# ============================================================================
# Security Group Endpoints
# ============================================================================


@app.post("/security-groups", response_model=SecurityGroup, status_code=201)
def create_security_group(sg: SecurityGroupCreate, db: Session = Depends(get_db)):
    rules = [r.model_dump() for r in sg.rules]
    new_sg = services.create_sg_logic(db, sg.name, sg.description, rules)

    return SecurityGroup(
        id=new_sg.id,
        name=new_sg.name,
        description=new_sg.description,
        rules=new_sg.rules,
        created_at=datetime.utcnow(),
    )


@app.get("/security-groups", response_model=List[SecurityGroup])
def list_security_groups(db: Session = Depends(get_db)):
    sgs = db.query(SGModel).all()
    return [
        SecurityGroup(
            id=sg.id,
            name=sg.name,
            description=sg.description,
            rules=sg.rules,
            created_at=datetime.utcnow(),
        )
        for sg in sgs
    ]


@app.get("/security-groups/{sg_id}", response_model=SecurityGroup)
def get_security_group(sg_id: str, db: Session = Depends(get_db)):
    sg = db.query(SGModel).filter(SGModel.id == sg_id).first()
    if not sg:
        raise HTTPException(status_code=404, detail="Security Group not found")
    return SecurityGroup(
        id=sg.id,
        name=sg.name,
        description=sg.description,
        rules=sg.rules,
        created_at=datetime.utcnow(),
    )


@app.post("/security-groups/{sg_id}/attach")
def attach_security_group(sg_id: str, instance_id: str, db: Session = Depends(get_db)):
    sg = db.query(SGModel).filter(SGModel.id == sg_id).first()
    if not sg:
        raise HTTPException(status_code=404, detail="Security Group not found")

    # In production, this would trigger firewall rule updates
    return {"message": f"Security Group {sg_id} attached to {instance_id}"}


# ============================================================================
# NAT Gateway Endpoints
# ============================================================================


@app.post("/vpcs/{vpc_id}/nat-gateways", response_model=NATGateway, status_code=201)
def create_nat_gateway(
    vpc_id: str,
    nat_gw: NATGatewayCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    vpc = db.query(VPCModel).filter(VPCModel.id == vpc_id).first()
    if not vpc:
        raise HTTPException(status_code=404, detail="VPC not found")

    new_nat = services.create_nat_logic(db, vpc_id, nat_gw.subnet_id)
    background_tasks.add_task(
        services.provision_nat_gateway_task, SessionLocal, new_nat.id
    )

    return NATGateway(
        id=new_nat.id,
        vpc_id=new_nat.vpc_id,
        subnet_id=new_nat.subnet_id,
        public_ip=new_nat.public_ip,
        status="provisioning",
        created_at=datetime.utcnow(),
    )


@app.get("/vpcs/{vpc_id}/nat-gateways", response_model=List[NATGateway])
def list_nat_gateways(vpc_id: str, db: Session = Depends(get_db)):
    nats = db.query(NATModel).filter(NATModel.vpc_id == vpc_id).all()
    return [
        NATGateway(
            id=n.id,
            vpc_id=n.vpc_id,
            subnet_id=n.subnet_id,
            public_ip=n.public_ip,
            status="available",
            created_at=datetime.utcnow(),
        )
        for n in nats
    ]


@app.delete("/nat-gateways/{nat_id}")
def delete_nat_gateway(
    nat_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    nat = db.query(NATModel).filter(NATModel.id == nat_id).first()
    if not nat:
        raise HTTPException(status_code=404, detail="NAT Gateway not found")

    db.delete(nat)
    db.commit()
    background_tasks.add_task(
        services.deprovision_nat_gateway_task, SessionLocal, nat_id
    )

    return {"message": "NAT Gateway deletion initiated"}


# ============================================================================
# Internet Gateway Endpoints
# ============================================================================


@app.post(
    "/vpcs/{vpc_id}/internet-gateways", response_model=InternetGateway, status_code=201
)
def create_internet_gateway(
    vpc_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    vpc = db.query(VPCModel).filter(VPCModel.id == vpc_id).first()
    if not vpc:
        raise HTTPException(status_code=404, detail="VPC not found")

    new_igw = services.create_igw_logic(db, vpc_id)
    background_tasks.add_task(
        services.provision_internet_gateway_task, SessionLocal, new_igw.id
    )
    return InternetGateway(
        id=new_igw.id,
        vpc_id=vpc_id,
        status="provisioning",
        created_at=datetime.utcnow(),
    )


@app.get("/vpcs/{vpc_id}/internet-gateways", response_model=List[InternetGateway])
def list_internet_gateways(vpc_id: str, db: Session = Depends(get_db)):
    igws = (
        db.query(InternetGatewayModel)
        .filter(InternetGatewayModel.vpc_id == vpc_id)
        .all()
    )
    return [
        InternetGateway(
            id=i.id, vpc_id=i.vpc_id, status="attached", created_at=datetime.utcnow()
        )
        for i in igws
    ]


# ============================================================================
# Managed VPN Gateways
# ============================================================================

@app.post(
    "/vpcs/{vpc_id}/vpn_gateways",
    response_model=VPNGateway,
    status_code=201
)
def create_vpn_gateway(
    vpc_id: str,
    payload: VPNGatewayCreate,
    background_tasks: BackgroundTasks,
):
    vpc = services.get_vpc(vpc_id)
    if not vpc:
        raise HTTPException(status_code=404, detail="VPC not found")

    gateway = services.create_vpn_gateway_logic(
        vpc_id=vpc_id,
        endpoint=payload.endpoint,
        public_key=payload.public_key,
        allowed_ips=payload.allowed_ips,
    )

    background_tasks.add_task(
        services.provision_vpn_gateway_task,
        gateway.id,
    )

    return VPNGateway(
        id=gateway.id,
        vpc_id=gateway.vpc_id,
        endpoint=gateway.endpoint,
        public_key=gateway.public_key,
        allowed_ips=gateway.allowed_ips,
    )

@app.get(
    "/vpcs/{vpc_id}/vpn_gateways",
    response_model=List[VPNGateway]
)
def list_vpn_gateways(vpc_id: str):
    vpc = services.get_vpc(vpc_id)
    if not vpc:
        raise HTTPException(status_code=404, detail="VPC not found")

    return services.list_vpn_gateways(vpc_id)

# ============================================================================
# Private Mesh Overlay Nodes
# ============================================================================

@app.post(
    "/vpcs/{vpc_id}/mesh-nodes",
    response_model=MeshNode,
    status_code=201
)
def create_mesh_node(
    vpc_id: str,
    payload: MeshNodeCreate,
    background_tasks: BackgroundTasks,
):
    vpc = services.get_vpc(vpc_id)
    if not vpc:
        raise HTTPException(status_code=404, detail="VPC not found")

    node = services.create_mesh_node_logic(
        vpc_id=vpc_id,
        node_key=payload.node_key,
        tailnet=payload.tailnet,
    )

    background_tasks.add_task(
        services.provision_mesh_node_task,
        node.id,
    )

    return MeshNode(
        id=node.id,
        vpc_id=node.vpc_id,
        node_key=node.node_key,
        tailnet=node.tailnet,
    )

@app.get(
    "/vpcs/{vpc_id}/mesh-nodes",
    response_model=List[MeshNode]
)
def list_mesh_nodes(vpc_id: str):
    vpc = services.get_vpc(vpc_id)
    if not vpc:
        raise HTTPException(status_code=404, detail="VPC not found")

    return services.list_mesh_nodes(vpc_id)


# ============================================================================
# VPC Graph Rendering Helpers
# ============================================================================

def render_vpn_gateway_node(gateway: VPNGatewayModel):
    return {
        "id": f"vpn-gateway-{gateway.id}",
        "type": "vpn_gateway",
        "label": f"VPN Gateway\n{gateway.endpoint}",
        "vpc_id": gateway.vpc_id,
    }

def render_mesh_node(node: MeshNodeModel):
    return {
        "id": f"mesh-node-{node.id}",
        "type": "mesh_node",
        "label": f"Mesh Node\n{node.node_key[:8]}...",
        "vpc_id": node.vpc_id,
    }


# ============================================================================
# Background Provisioning Tasks
# ============================================================================

# Provisioning tasks have been migrated to services.py for gRPC/REST interchangeability.
