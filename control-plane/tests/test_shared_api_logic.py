import sys
import os
import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the control-plane directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# Mock metrics before importing api.shared_api_logic
class MockMetric:
    def set(self, val):
        pass

    def inc(self, val=1):
        pass

    def labels(self, *args, **kwargs):
        return self

    def observe(self, val):
        pass


mock_metrics = {
    "vpcs_total": MockMetric(),
    "reconciliation_latency": MockMetric(),
    "api_requests": MockMetric(),
    "reconciliation_actions": MockMetric(),
}

import metrics

metrics.METRICS = mock_metrics

from api.models import Base
from api import shared_api_logic as services

# Setup in-memory database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def setup_module(module):
    Base.metadata.create_all(bind=engine)


def teardown_module(module):
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    database = TestingSessionLocal()
    try:
        yield database
    finally:
        database.close()


def test_create_vpc(db):
    vpc = services.create_vpc_logic(db, "test-vpc", "10.0.0.0/16")
    assert vpc.id.startswith("vpc-")
    assert vpc.name == "test-vpc"
    assert vpc.vni >= 1000
    assert vpc.status == "provisioning"


@pytest.mark.asyncio
async def test_provision_subnet_task():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    vpc = services.create_vpc_logic(db, "prov-sub-vpc", "10.0.0.0/16")
    sub = services.create_subnet_logic(db, vpc.id, "prov-sub", "10.0.1.0/24")
    db_id = sub.id
    db.close()

    await services.provision_subnet_task(TestingSessionLocal, db_id)

    db = TestingSessionLocal()
    s = db.query(services.SubnetModel).filter(services.SubnetModel.id == db_id).first()
    assert s.status == "available"
    db.close()


@pytest.mark.asyncio
async def test_delete_vpc_flow():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    vpc = services.create_vpc_logic(db, "del-flow-vpc", "10.0.0.0/16")
    db_id = vpc.id
    db.close()

    # Test logic
    db = TestingSessionLocal()
    services.delete_vpc_logic(db, db_id)
    vpc = db.query(services.VPCModel).filter(services.VPCModel.id == db_id).first()
    assert vpc.status == "deleting"
    db.close()

    # Test task
    await services.deprovision_vpc_task(TestingSessionLocal, db_id)

    db = TestingSessionLocal()
    vpc = db.query(services.VPCModel).filter(services.VPCModel.id == db_id).first()
    assert vpc is None
    db.close()


@pytest.mark.asyncio
async def test_deprovision_subnet_task():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    vpc = services.create_vpc_logic(db, "sub-deprov", "10.0.0.0/16")
    sub = services.create_subnet_logic(db, vpc.id, "sub-del", "10.0.1.0/24")
    db_id = sub.id
    db.close()

    await services.deprovision_subnet_task(TestingSessionLocal, db_id)

    db = TestingSessionLocal()
    s = db.query(services.SubnetModel).filter(services.SubnetModel.id == db_id).first()
    assert s is None
    db.close()


def test_vni_increment(db):
    v1 = services.get_next_vni()
    v2 = services.get_next_vni()
    assert v2 == v1 + 1


def test_create_subnet(db):
    vpc = services.create_vpc_logic(db, "vpc-sub", "10.0.0.0/16")
    subnet = services.create_subnet_logic(db, vpc.id, "subnet-1", "10.0.1.0/24")
    assert subnet.id.startswith("subnet-")
    assert subnet.gateway == "10.0.1.1"


def test_create_route(db):
    vpc = services.create_vpc_logic(db, "vpc-route", "10.0.0.0/16")
    route = services.create_route_logic(db, vpc.id, "0.0.0.0/0", "igw-1", "gateway")
    assert route.id.startswith("rtb-")
    assert route.next_hop == "igw-1"


def test_create_sg(db):
    rules = [
        {
            "direction": "ingress",
            "protocol": "tcp",
            "port_from": 80,
            "port_to": 80,
            "cidr": "0.0.0.0/0",
        }
    ]
    sg = services.create_sg_logic(db, "web-sg", "Allow HTTP", rules)
    assert sg.id.startswith("sg-")
    assert sg.rules[0]["port_from"] == 80


def test_create_nat(db):
    vpc = services.create_vpc_logic(db, "vpc-nat", "10.0.0.0/16")
    subnet = services.create_subnet_logic(db, vpc.id, "subnet-nat", "10.0.1.0/24")
    nat = services.create_nat_logic(db, vpc.id, subnet.id)
    assert nat.id.startswith("nat-")
    assert nat.public_ip.startswith("203.0.113.")


def test_create_igw(db):
    vpc = services.create_vpc_logic(db, "vpc-igw", "10.0.0.0/16")
    igw = services.create_igw_logic(db, vpc.id)
    assert igw.id.startswith("igw-")
    assert igw.vpc_id == vpc.id


@pytest.mark.asyncio
async def test_provision_vpc_task():
    # We need a fresh DB for async task to avoid session conflicts in this simple test
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    vpc = services.create_vpc_logic(db, "async-vpc", "10.0.0.0/16")
    db_id = vpc.id
    db.close()

    await services.provision_vpc_task(TestingSessionLocal, db_id)


@pytest.mark.asyncio
async def test_provision_route_task():
    # Setup
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    vpc = services.create_vpc_logic(db, "async-vpc-rt", "10.0.0.0/16")
    route = services.create_route_logic(db, vpc.id, "0.0.0.0/0", "igw-1", "gateway")
    db_id = route.id
    db.close()

    # Task (provisioning logic is just a print/sleep for route currently, but we test execution)
    await services.provision_route_task(TestingSessionLocal, db_id)

    # Deprovision
    await services.deprovision_route_task(TestingSessionLocal, db_id)

    # Verify deletion
    db = TestingSessionLocal()
    r = db.query(services.RouteModel).filter(services.RouteModel.id == db_id).first()
    assert r is None
    db.close()


@pytest.mark.asyncio
async def test_provision_nat_task():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    vpc = services.create_vpc_logic(db, "async-vpc-nat", "10.0.0.0/16")
    subnet = services.create_subnet_logic(db, vpc.id, "async-sub-nat", "10.0.1.0/24")
    nat = services.create_nat_logic(db, vpc.id, subnet.id)
    db_id = nat.id
    db.close()

    await services.provision_nat_gateway_task(TestingSessionLocal, db_id)
    await services.deprovision_nat_gateway_task(TestingSessionLocal, db_id)

    db = TestingSessionLocal()
    n = db.query(services.NATModel).filter(services.NATModel.id == db_id).first()
    assert n is None
    db.close()


@pytest.mark.asyncio
async def test_provision_igw_task():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    vpc = services.create_vpc_logic(db, "async-vpc-igw", "10.0.0.0/16")
    igw = services.create_igw_logic(db, vpc.id)
    db_id = igw.id
    db.close()

    await services.provision_internet_gateway_task(TestingSessionLocal, db_id)
    # Note: IGW deprovisioning task isn't in shared logic explicitly yet?
    # Checking shared_api_logic.py... it seems we only have provision_internet_gateway_task.
    # Let's double check the file.
