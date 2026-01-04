# file: models.py

from sqlalchemy import Column, String, Integer, ForeignKey, JSON, DateTime, func, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import os

Base = declarative_base()

class VniCounter(Base):
    __tablename__ = "vni_counter"
    id = Column(Integer, primary_key=True)
    current = Column(Integer, nullable=False)

class VPC(Base):
    __tablename__ = "vpcs"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    cidr = Column(String, nullable=False)
    vni = Column(Integer, unique=True, nullable=False)
    vrf = Column(String, unique=True, nullable=False)
    region = Column(String, default="us-east-1")
    secondary_cidrs = Column(JSON, default=list) # For K8s/Pod subnets
    scenario = Column(String, nullable=True)     # For UI grouping
    status = Column(String, default="active")
    created_at = Column(DateTime, server_default=func.now())

class VPCEndpoint(Base):
    __tablename__ = "vpc_endpoints"
    id = Column(String, primary_key=True, default=lambda: f"vpe-{uuid.uuid4().hex[:8]}")
    vpc_id = Column(String, ForeignKey("vpcs.id"), nullable=False)
    subnet_id = Column(String, ForeignKey("subnets.id"), nullable=False)
    name = Column(String, nullable=False)
    ip = Column(String, nullable=False)
    status = Column(String, default="active")
    created_at = Column(DateTime, server_default=func.now())

VPC.endpoints = relationship("VPCEndpoint", backref="vpc", cascade="all, delete-orphan")

class CloudRoutingHub(Base):
    __tablename__ = "cloud_routing_hubs"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    region = Column(String, default="global")
    scenario = Column(String, nullable=True)     # For UI grouping
    created_at = Column(DateTime, server_default=func.now())

class Scenario(Base):
    __tablename__ = "scenarios"
    id = Column(String, primary_key=True)
    title = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    resource_order = Column(JSON, nullable=True) # Optional: list of {type, label}
    created_at = Column(DateTime, server_default=func.now())

class Subnet(Base):
    __tablename__ = "subnets"
    id = Column(String, primary_key=True)
    vpc_id = Column(String, ForeignKey("vpcs.id"), nullable=False)
    name = Column(String, nullable=False)
    cidr = Column(String, nullable=False)
    gateway = Column(String, nullable=False)
    az = Column(String, nullable=False)
    status = Column(String, default="provisioning")
    created_at = Column(DateTime, server_default=func.now())

class SecurityGroup(Base):
    __tablename__ = "security_groups"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    rules = Column(JSON)  # Store list of rules as JSON
    created_at = Column(DateTime, server_default=func.now())

class NATGateway(Base):
    __tablename__ = "nat_gateways"
    id = Column(String, primary_key=True)
    vpc_id = Column(String, ForeignKey("vpcs.id"), nullable=False)
    subnet_id = Column(String, ForeignKey("subnets.id"), nullable=False)
    public_ip = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class InternetGateway(Base):
    __tablename__ = "internet_gateways"
    id = Column(String, primary_key=True)
    vpc_id = Column(String, ForeignKey("vpcs.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class VPNGateway(Base):
    __tablename__ = "vpn_gateways"
    id = Column(String, primary_key=True)
    vpc_id = Column(String, ForeignKey("vpcs.id"))
    endpoint = Column(String)
    public_key = Column(String)
    allowed_ips = Column(String)
    status = Column(String)

class MeshNode(Base):
    __tablename__ = "mesh_nodes"
    id = Column(String, primary_key=True)
    vpc_id = Column(String, ForeignKey("vpcs.id"))
    node_key = Column(String)
    tailnet = Column(String)
    status = Column(String)

class Route(Base):
    __tablename__ = "routes"
    id = Column(String, primary_key=True)
    vpc_id = Column(String, ForeignKey("vpcs.id"), nullable=True)
    hub_id = Column(String, ForeignKey("cloud_routing_hubs.id"), nullable=True)
    dc_id = Column(String, ForeignKey("standalone_data_centers.id"), nullable=True)
    destination = Column(String, nullable=False)
    next_hop = Column(String, nullable=False)
    next_hop_type = Column(String, nullable=False)
    priority = Column(Integer, default=100)
    status = Column(String, default="active")
    created_at = Column(DateTime, server_default=func.now())

class StandaloneDataCenter(Base):
    __tablename__ = "standalone_data_centers"
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    cidr = Column(String, nullable=False)
    region = Column(String, default="on-prem")
    scenario = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class StandaloneDCSubnet(Base):
    __tablename__ = "standalone_dc_subnets"
    id = Column(String, primary_key=True)
    dc_id = Column(String, ForeignKey("standalone_data_centers.id"), nullable=False)
    name = Column(String, nullable=False)
    cidr = Column(String, nullable=False)
    gateway = Column(String, nullable=False)
    az = Column(String, nullable=False)
    status = Column(String, default="active")
    created_at = Column(DateTime, server_default=func.now())

# ============================================================================
# Database Configuration (SQLite for Persistence)
# ============================================================================

# Default to /tmp for serverless environments if DB_DIR is not set
DB_DIR = os.getenv("DB_DIR", "/tmp")
DB_PATH = os.path.join(DB_DIR, "network.db")

# Ensure data directory exists if it's not a special sqlite path
if not os.path.exists(DB_DIR) and not DB_PATH.startswith(":memory:"):
    try:
        os.makedirs(DB_DIR, exist_ok=True)
    except OSError:
        # Fallback for read-only environments during testing if needed
        pass

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

# Create the engine pointing to your SQLite database
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=True,
    connect_args={"check_same_thread": False}  # Needed for SQLite in serverless
)

# Ensure /tmp is writable and create tables safely
try:
    if not DB_PATH.startswith(":memory:") and os.access(DB_DIR, os.W_OK):
        os.makedirs(DB_DIR, exist_ok=True)
        Base.metadata.create_all(bind=engine)
except Exception as e:
    print("Warning: could not create tables:", e)

# Optional: query existing tables safely for debugging
try:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        print("Existing tables:", [row[0] for row in result])
except Exception as e:
    print("SQLite query failed:", e)
