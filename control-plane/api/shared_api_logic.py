# services/shared_api_logic.py
import uuid
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from .models import (
    VPC as VPCModel,
    VPCEndpoint as VPCEndpointModel,
    Subnet as SubnetModel,
    Route as RouteModel,
    SecurityGroup as SGModel,
    NATGateway as NATModel,
    InternetGateway as InternetGatewayModel,
    CloudRoutingHub as HubModel,
    Scenario as ScenarioModel,
    StandaloneDataCenter as StandaloneDCModel,
    StandaloneDCSubnet as StandaloneDCSubnetModel,
    VPNGateway as VPNGatewayModel,
    MeshNode as MeshNodeModel,
)
from metrics import METRICS

from sqlalchemy.orm import Session
from api.models import VniCounter

def get_next_vni(db: Session) -> int:
    """
    Get the next available VNI and increment the counter in the database.
    Ensures the increment is persisted and returns a unique VNI each call.
    """
    # Try to get the counter row (assumes only one row exists)
    counter = db.query(VniCounter).first()

    if counter is None:
        # First time: initialize the counter
        counter = VniCounter(current=1003)  # or your starting VNI
        db.add(counter)
        db.commit()
        db.refresh(counter)
        return counter.current

    # Increment the counter
    counter.current += 1
    db.commit()
    db.refresh(counter)
    return counter.current


# VPC Services
def create_vpc_logic(db: Session, name: str, cidr: str, region: str = "us-east-1", secondary_cidrs: list = None, scenario: str = None):
    vpc_id = f"vpc-{uuid.uuid4().hex[:8]}"
    new_vpc = VPCModel(
        id=vpc_id,
        name=name,
        cidr=cidr,
        vni=get_next_vni(db),
        vrf=f"VRF-{vpc_id}",
        region=region,
        secondary_cidrs=secondary_cidrs or [],
        scenario=scenario,
        status="provisioning",
    )
    db.add(new_vpc)
    db.commit()
    db.refresh(new_vpc)
    if METRICS:
        METRICS["vpcs_total"].set(db.query(VPCModel).count())
    return new_vpc


def delete_vpc_logic(db: Session, vpc_id: str):
    vpc = db.query(VPCModel).filter(VPCModel.id == vpc_id).first()
    if vpc:
        vpc.status = "deleting"
        db.commit()
    return vpc


def _get_db_session():
    """Helper to get a database session, avoiding circular imports."""
    # Lazy import to avoid circular dependency
    import sys
    if 'rest_api_server' in sys.modules:
        from . import rest_api_server
        return rest_api_server.SessionLocal()
    # Fallback: create engine directly if rest_api_server not loaded
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import os
    DB_DIR = os.getenv("DB_DIR", "/app/data")
    DB_PATH = os.getenv("DB_PATH", f"{DB_DIR}/network.db")
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
    engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def get_vpc(vpc_id: str):
    """Get a VPC by ID. Creates a new session for the query."""
    db = _get_db_session()
    try:
        vpc = db.query(VPCModel).filter(VPCModel.id == vpc_id).first()
        return vpc
    finally:
        db.close()


# Subnet Services
def create_subnet_logic(
    db: Session, vpc_id: str, name: str, cidr: str, az: str = "us-east-1a"
):
    subnet_id = f"subnet-{uuid.uuid4().hex[:8]}"
    gateway = cidr.rsplit(".", 1)[0] + ".1"
    new_subnet = SubnetModel(
        id=subnet_id,
        vpc_id=vpc_id,
        name=name,
        cidr=cidr,
        gateway=gateway,
        az=az,
        status="provisioning",
    )
    db.add(new_subnet)
    db.commit()
    db.refresh(new_subnet)
    if METRICS:
        METRICS["subnets_total"].set(db.query(SubnetModel).count())
    return new_subnet


# Route Services
def create_route_logic(
    db: Session, vpc_id: str, destination: str, next_hop: str, next_hop_type: str
):
    # Resolve igw-auto placeholder to actual IGW ID
    if next_hop == "igw-auto" and next_hop_type == "internet_gateway":
        actual_igw = db.query(InternetGatewayModel).filter(InternetGatewayModel.vpc_id == vpc_id).first()
        if actual_igw:
            next_hop = actual_igw.id
        else:
            # If no IGW exists, create one first
            new_igw = create_igw_logic(db, vpc_id)
            next_hop = new_igw.id
    
    # Resolve vpn-auto placeholder to actual VPN Gateway ID
    if next_hop == "vpn-auto" and next_hop_type == "vpn_gateway":
        actual_vpn = db.query(VPNGatewayModel).filter(VPNGatewayModel.vpc_id == vpc_id).first()
        if actual_vpn:
            next_hop = actual_vpn.id
    
    route_id = f"rtb-{uuid.uuid4().hex[:8]}"
    new_route = RouteModel(
        id=route_id,
        vpc_id=vpc_id,
        destination=destination,
        next_hop=next_hop,
        next_hop_type=next_hop_type,
        status="provisioning",
    )
    db.add(new_route)
    db.commit()
    db.refresh(new_route)
    if METRICS:
        METRICS["routes_total"].set(db.query(RouteModel).count())
    return new_route


# Security Group Services
def create_sg_logic(db: Session, name: str, description: str, rules: list):
    sg_id = f"sg-{uuid.uuid4().hex[:8]}"
    new_sg = SGModel(id=sg_id, name=name, description=description, rules=rules)
    db.add(new_sg)
    db.commit()
    db.refresh(new_sg)
    if METRICS:
        METRICS["security_groups_total"].set(db.query(SGModel).count())
    return new_sg


# Gateway Services
def create_nat_logic(db: Session, vpc_id: str, subnet_id: str):
    nat_id = f"nat-{uuid.uuid4().hex[:8]}"
    count = db.query(NATModel).count()
    public_ip = f"203.0.113.{count + 10}"
    new_nat = NATModel(
        id=nat_id, vpc_id=vpc_id, subnet_id=subnet_id, public_ip=public_ip
    )
    db.add(new_nat)
    db.commit()
    db.refresh(new_nat)
    if METRICS:
        METRICS["nat_gateways_total"].set(db.query(NATModel).count())
    return new_nat


def create_igw_logic(db: Session, vpc_id: str):
    igw_id = f"igw-{uuid.uuid4().hex[:8]}"
    new_igw = InternetGatewayModel(id=igw_id, vpc_id=vpc_id)
    db.add(new_igw)
    db.commit()
    db.refresh(new_igw)
    if METRICS:
        METRICS["internet_gateways_total"].set(db.query(InternetGatewayModel).count())
    return new_igw


# VPN Gateway Services
def create_vpn_gateway_logic(vpc_id: str, endpoint: str, public_key: str, allowed_ips: str):
    """Create a VPN gateway. Creates a new session for the operation."""
    db = _get_db_session()
    try:
        vpn_id = f"vpn-{uuid.uuid4().hex[:8]}"
        new_vpn = VPNGatewayModel(
            id=vpn_id,
            vpc_id=vpc_id,
            endpoint=endpoint,
            public_key=public_key,
            allowed_ips=allowed_ips,
            status="provisioning"
        )
        db.add(new_vpn)
        db.commit()
        db.refresh(new_vpn)
        if METRICS:
            METRICS["vpn_gateways_total"].set(db.query(VPNGatewayModel).count())
        return new_vpn
    finally:
        db.close()


def delete_vpn_gateway_logic(db: Session, vpn_id: str):
    vpn = db.query(VPNGatewayModel).filter(VPNGatewayModel.id == vpn_id).first()
    if vpn:
        db.delete(vpn)
        db.commit()
        if METRICS:
            METRICS["vpn_gateways_total"].set(db.query(VPNGatewayModel).count())
    return vpn


def list_vpn_gateways(vpc_id: str):
    """List VPN gateways for a VPC. Creates a new session for the query."""
    db = _get_db_session()
    try:
        gateways = db.query(VPNGatewayModel).filter(VPNGatewayModel.vpc_id == vpc_id).all()
        # Convert to dict format matching VPNGateway Pydantic model
        return [
            {
                "id": gw.id,
                "vpc_id": gw.vpc_id,
                "endpoint": gw.endpoint,
                "public_key": gw.public_key,
                "allowed_ips": gw.allowed_ips,
            }
            for gw in gateways
        ]
    finally:
        db.close()


# Mesh Node Services
def create_mesh_node_logic(vpc_id: str, node_key: str, tailnet: str):
    """Create a mesh node. Creates a new session for the operation."""
    db = _get_db_session()
    try:
        node_id = f"mesh-{uuid.uuid4().hex[:8]}"
        new_node = MeshNodeModel(
            id=node_id,
            vpc_id=vpc_id,
            node_key=node_key,
            tailnet=tailnet,
            status="provisioning"
        )
        db.add(new_node)
        db.commit()
        db.refresh(new_node)
        if METRICS:
            METRICS["mesh_nodes_total"].set(db.query(MeshNodeModel).count())
        return new_node
    finally:
        db.close()


def delete_mesh_node_logic(db: Session, node_id: str):
    node = db.query(MeshNodeModel).filter(MeshNodeModel.id == node_id).first()
    if node:
        db.delete(node)
        db.commit()
        if METRICS:
            METRICS["mesh_nodes_total"].set(db.query(MeshNodeModel).count())
    return node


def list_mesh_nodes(vpc_id: str):
    """List mesh nodes for a VPC. Creates a new session for the query."""
    db = _get_db_session()
    try:
        nodes = db.query(MeshNodeModel).filter(MeshNodeModel.vpc_id == vpc_id).all()
        # Convert to dict format matching MeshNode Pydantic model
        return [
            {
                "id": node.id,
                "vpc_id": node.vpc_id,
                "node_key": node.node_key,
                "tailnet": node.tailnet,
            }
            for node in nodes
        ]
    finally:
        db.close()


# Async Provisioning Tasks
async def provision_vpn_gateway_task(vpn_id: str):
    """Provision a VPN gateway. Creates a new session for the operation."""
    await asyncio.sleep(0.5)
    db = _get_db_session()
    try:
        vpn = db.query(VPNGatewayModel).filter(VPNGatewayModel.id == vpn_id).first()
        if vpn:
            vpn.status = "available"
            db.commit()
            if METRICS:
                METRICS["vpn_gateways_total"].set(db.query(VPNGatewayModel).count())
    finally:
        db.close()
    print(f"VPN Gateway {vpn_id} provisioned")


async def deprovision_vpn_gateway_task(db_factory, vpn_id: str):
    await asyncio.sleep(0.5)
    db = db_factory()
    try:
        vpn = db.query(VPNGatewayModel).filter(VPNGatewayModel.id == vpn_id).first()
        if vpn:
            db.delete(vpn)
            db.commit()
            if METRICS:
                METRICS["vpn_gateways_total"].set(db.query(VPNGatewayModel).count())
    finally:
        db.close()


async def provision_mesh_node_task(node_id: str):
    """Provision a mesh node. Creates a new session for the operation."""
    await asyncio.sleep(0.5)
    db = _get_db_session()
    try:
        node = db.query(MeshNodeModel).filter(MeshNodeModel.id == node_id).first()
        if node:
            node.status = "available"
            db.commit()
            if METRICS:
                METRICS["mesh_nodes_total"].set(db.query(MeshNodeModel).count())
    finally:
        db.close()
    print(f"Mesh Node {node_id} provisioned")


async def deprovision_mesh_node_task(db_factory, node_id: str):
    await asyncio.sleep(0.5)
    db = db_factory()
    try:
        node = db.query(MeshNodeModel).filter(MeshNodeModel.id == node_id).first()
        if node:
            db.delete(node)
            db.commit()
            if METRICS:
                METRICS["mesh_nodes_total"].set(db.query(MeshNodeModel).count())
    finally:
        db.close()


def create_hub_logic(db: Session, name: str, region: str = "global", scenario: str = None):
    hub_id = f"hub-{uuid.uuid4().hex[:8]}"
    new_hub = HubModel(id=hub_id, name=name, region=region, scenario=scenario)
    db.add(new_hub)
    db.commit()
    db.refresh(new_hub)
    return new_hub


def list_vpc_endpoints(db: Session, vpc_id: str):
    return db.query(VPCEndpointModel).filter(VPCEndpointModel.vpc_id == vpc_id).all()


def create_vpc_endpoint(db: Session, vpc_id: str, name: str, ip: str):
    # Find the subnet this IP belongs to
    subnets = db.query(SubnetModel).filter(SubnetModel.vpc_id == vpc_id).all()
    import ipaddress
    target_subnet_id = None
    for s in subnets:
        if ipaddress.ip_address(ip) in ipaddress.ip_network(s.cidr):
            target_subnet_id = s.id
            break

    if not target_subnet_id:
        raise ValueError(f"IP {ip} does not belong to any subnet in VPC {vpc_id}")

    endpoint_id = f"vpe-{uuid.uuid4().hex[:8]}"
    new_endpoint = VPCEndpointModel(
        id=endpoint_id,
        vpc_id=vpc_id,
        subnet_id=target_subnet_id,
        name=name,
        ip=ip,
        status="active"
    )
    db.add(new_endpoint)
    db.commit()
    db.refresh(new_endpoint)
    return new_endpoint


def delete_vpc_endpoint(db: Session, vpc_id: str, endpoint_id: str):
    endpoint = db.query(VPCEndpointModel).filter(
        VPCEndpointModel.vpc_id == vpc_id, 
        VPCEndpointModel.id == endpoint_id
    ).first()
    if endpoint:
        db.delete(endpoint)
        db.commit()
        return True
    return False


def delete_hub_logic(db: Session, hub_id: str):
    hub = db.query(HubModel).filter(HubModel.id == hub_id).first()
    if hub:
        # Delete associated routes first
        db.query(RouteModel).filter(RouteModel.hub_id == hub_id).delete()
        db.delete(hub)
        db.commit()
    return hub


def create_scenario_logic(db: Session, title: str, description: str = None, resource_order: list = None):
    # Idempotent creation: check if exists first
    existing = db.query(ScenarioModel).filter(ScenarioModel.title == title).first()
    if existing:
        existing.description = description
        existing.resource_order = resource_order or []
        db.commit()
        db.refresh(existing)
        return existing

    scenario_id = f"scenario-{uuid.uuid4().hex[:8]}"
    new_scenario = ScenarioModel(
        id=scenario_id,
        title=title,
        description=description,
        resource_order=resource_order or []
    )
    db.add(new_scenario)
    db.commit()
    db.refresh(new_scenario)
    return new_scenario


# Standalone Data Center Services
def create_standalone_dc_logic(db: Session, name: str, cidr: str, region: str = "on-prem", scenario: str = None):
    dc_id = f"dc-{uuid.uuid4().hex[:8]}"
    new_dc = StandaloneDCModel(
        id=dc_id,
        name=name,
        cidr=cidr,
        region=region,
        scenario=scenario
    )
    db.add(new_dc)
    db.commit()
    db.refresh(new_dc)
    return new_dc


def delete_standalone_dc_logic(db: Session, dc_id: str):
    dc = db.query(StandaloneDCModel).filter(StandaloneDCModel.id == dc_id).first()
    if dc:
        # Delete associated subnets and routes
        db.query(StandaloneDCSubnetModel).filter(StandaloneDCSubnetModel.dc_id == dc_id).delete()
        db.query(RouteModel).filter(RouteModel.dc_id == dc_id).delete()
        db.delete(dc)
        db.commit()
    return dc


def create_standalone_dc_subnet_logic(db: Session, dc_id: str, name: str, cidr: str, az: str = "DC-1"):
    subnet_id = f"dc-subnet-{uuid.uuid4().hex[:8]}"
    gateway = cidr.rsplit(".", 1)[0] + ".1"
    new_subnet = StandaloneDCSubnetModel(
        id=subnet_id,
        dc_id=dc_id,
        name=name,
        cidr=cidr,
        gateway=gateway,
        az=az,
        status="active"
    )
    db.add(new_subnet)
    db.commit()
    db.refresh(new_subnet)
    return new_subnet


def create_standalone_dc_route_logic(
    db: Session, dc_id: str, destination: str, next_hop: str, next_hop_type: str
):
    route_id = f"rtb-dc-{uuid.uuid4().hex[:8]}"
    new_route = RouteModel(
        id=route_id,
        dc_id=dc_id,
        destination=destination,
        next_hop=next_hop,
        next_hop_type=next_hop_type,
        status="active",
    )
    db.add(new_route)
    db.commit()
    db.refresh(new_route)
    if METRICS:
        METRICS["routes_total"].set(db.query(RouteModel).count())
    return new_route



# Provisioning Tasks (Simplified for shared use)
async def provision_vpc_task(db_factory, vpc_id: str):
    await asyncio.sleep(0.5)
    db = db_factory()
    try:
        vpc = db.query(VPCModel).filter(VPCModel.id == vpc_id).first()
        if vpc:
            vpc.status = "available"
            db.commit()
            if METRICS:
                METRICS["vpcs_total"].set(db.query(VPCModel).count())
    finally:
        db.close()


async def provision_subnet_task(db_factory, subnet_id: str):
    await asyncio.sleep(0.5)
    db = db_factory()
    try:
        subnet = db.query(SubnetModel).filter(SubnetModel.id == subnet_id).first()
        if subnet:
            subnet.status = "available"
            db.commit()
            if METRICS:
                METRICS["subnets_total"].set(db.query(SubnetModel).count())
    finally:
        db.close()


async def deprovision_vpc_task(db_factory, vpc_id: str):
    await asyncio.sleep(0.5)
    db = db_factory()
    try:
        vpc = db.query(VPCModel).filter(VPCModel.id == vpc_id).first()
        if vpc:
            db.delete(vpc)
            db.commit()
            if METRICS:
                METRICS["vpcs_total"].set(db.query(VPCModel).count())
    finally:
        db.close()


async def deprovision_subnet_task(db_factory, subnet_id):
    await asyncio.sleep(0.5)
    db = db_factory()
    try:
        subnet = db.query(SubnetModel).filter(SubnetModel.id == subnet_id).first()
        if subnet:
            db.delete(subnet)
            db.commit()
            if METRICS:
                METRICS["subnets_total"].set(db.query(SubnetModel).count())
    finally:
        db.close()


async def provision_route_task(db_factory, route_id):
    await asyncio.sleep(0.5)
    db = db_factory()
    try:
        route = db.query(RouteModel).filter(RouteModel.id == route_id).first()
        if route:
            route.status = "available"
            db.commit()
            if METRICS:
                METRICS["routes_total"].set(db.query(RouteModel).count())
    finally:
        db.close()
    print(f"Route {route_id} provisioned")


async def deprovision_route_task(db_factory, route_id):
    db = db_factory()
    try:
        route = db.query(RouteModel).filter(RouteModel.id == route_id).first()
        if route:
            db.delete(route)
            db.commit()
            if METRICS:
                METRICS["routes_total"].set(db.query(RouteModel).count())
    finally:
        db.close()


async def provision_nat_gateway_task(db_factory, nat_id):
    await asyncio.sleep(0.5)
    db = db_factory()
    try:
        nat = db.query(NATModel).filter(NATModel.id == nat_id).first()
        if nat:
            # Note: models.py doesn't have status for NAT, but we can update metric
            if METRICS:
                METRICS["nat_gateways_total"].set(db.query(NATModel).count())
    finally:
        db.close()
    print(f"NAT Gateway {nat_id} provisioned")


async def deprovision_nat_gateway_task(db_factory, nat_id):
    await asyncio.sleep(0.5)
    db = db_factory()
    try:
        nat = db.query(NATModel).filter(NATModel.id == nat_id).first()
        if nat:
            db.delete(nat)
            db.commit()
            if METRICS:
                METRICS["nat_gateways_total"].set(db.query(NATModel).count())
    finally:
        db.close()


async def provision_internet_gateway_task(db_factory, igw_id):
    await asyncio.sleep(0.5)
    db = db_factory()
    try:
        if METRICS:
            METRICS["internet_gateways_total"].set(db.query(InternetGatewayModel).count())
    finally:
        db.close()
    print(f"Internet Gateway {igw_id} provisioned")
