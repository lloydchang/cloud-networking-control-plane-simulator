from fastapi.testclient import TestClient
import pytest
import os

# Ensure we don't try to write to /app/data during tests
os.environ["DB_DIR"] = os.getcwd()
from api.rest_api_server import app, get_db
from api import shared_api_logic as services
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Local test DB setup to avoid importing conftest internals
SQLALCHEMY_DATABASE_URL = "sqlite:///./network_test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_create_vpc_rest():
    response = client.post(
        "/vpcs", json={"name": "rest-vpc", "cidr": "10.0.0.0/16", "region": "us-west-2"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "rest-vpc"
    assert data["region"] == "us-west-2"
    assert "id" in data


def test_list_vpcs_rest():
    client.post("/vpcs", json={"name": "list-vpc", "cidr": "10.1.0.0/16"})
    response = client.get("/vpcs")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_get_vpc_not_found():
    response = client.get("/vpcs/vpc-nonexistent")
    assert response.status_code == 404


def test_create_subnet_rest():
    vpc_resp = client.post("/vpcs", json={"name": "subnet-vpc", "cidr": "10.2.0.0/16"})
    vpc_id = vpc_resp.json()["id"]

    response = client.post(
        f"/vpcs/{vpc_id}/subnets", json={"name": "rest-sub", "cidr": "10.2.1.0/24"}
    )
    assert response.status_code == 201
    assert response.json()["cidr"] == "10.2.1.0/24"


def test_delete_vpc_rest():
    vpc_resp = client.post("/vpcs", json={"name": "delete-vpc", "cidr": "10.3.0.0/16"})
    vpc_id = vpc_resp.json()["id"]

    response = client.delete(f"/vpcs/{vpc_id}")
    assert response.status_code == 200
    assert "initiated" in response.json()["message"]


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "endpoints" in response.json()


def test_create_route_rest():
    vpc_resp = client.post("/vpcs", json={"name": "route-vpc", "cidr": "10.4.0.0/16"})
    vpc_id = vpc_resp.json()["id"]

    response = client.post(
        f"/vpcs/{vpc_id}/routes",
        json={
            "destination": "0.0.0.0/0",
            "next_hop": "igw-xx",
            "next_hop_type": "gateway",
        },
    )
    assert response.status_code == 201
    assert response.json()["destination"] == "0.0.0.0/0"


def test_list_routes_rest():
    vpc_resp = client.post(
        "/vpcs", json={"name": "list-route-vpc", "cidr": "10.5.0.0/16"}
    )
    vpc_id = vpc_resp.json()["id"]
    client.post(
        f"/vpcs/{vpc_id}/routes",
        json={
            "destination": "1.1.1.1/32",
            "next_hop": "10.5.0.1",
            "next_hop_type": "instance",
        },
    )

    response = client.get(f"/vpcs/{vpc_id}/routes")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_delete_route_rest():
    vpc_resp = client.post(
        "/vpcs", json={"name": "del-route-vpc", "cidr": "10.6.0.0/16"}
    )
    vpc_id = vpc_resp.json()["id"]
    route_resp = client.post(
        f"/vpcs/{vpc_id}/routes",
        json={
            "destination": "8.8.8.8/32",
            "next_hop": "10.6.0.1",
            "next_hop_type": "instance",
        },
    )
    route_id = route_resp.json()["id"]

    response = client.delete(f"/routes/{route_id}")
    assert response.status_code == 200

    # Test 404
    response = client.delete(f"/routes/{route_id}")
    assert response.status_code == 404


def test_security_groups_rest():
    # Create
    response = client.post(
        "/security-groups",
        json={
            "name": "web-sg",
            "description": "Web traffic",
            "rules": [
                {
                    "direction": "ingress",
                    "protocol": "tcp",
                    "port_from": 80,
                    "port_to": 80,
                    "cidr": "0.0.0.0/0",
                }
            ],
        },
    )
    assert response.status_code == 201
    sg_id = response.json()["id"]

    # List
    response = client.get("/security-groups")
    assert response.status_code == 200
    assert len(response.json()) >= 1

    # Get
    response = client.get(f"/security-groups/{sg_id}")
    assert response.status_code == 200
    assert response.json()["id"] == sg_id

    # Get 404
    response = client.get("/security-groups/sg-nonexistent")
    assert response.status_code == 404

    # Attach (Stub)
    response = client.post(f"/security-groups/{sg_id}/attach?instance_id=i-12345")
    # Note: Attach logic in rest_api_server.py checks a global DB dict,
    # which might not be populated in our test session the same way.
    # Let's see if it errors. It likely will fail if DB dict isn't mocked or used.
    # Looking at code: `if sg_id not in DB["security_groups"]:` -> Wait, rest_api_server.py uses SQLalchemy?
    # Ah, the attach endpoint in rest_api_server.py (lines 384-390) refers to `DB["security_groups"]`!
    # This is a BUG in the server code (legacy artifact?).
    # We should fix the server code first, but let's run this test to confirm failure.


def test_nat_gateway_rest():
    vpc_resp = client.post("/vpcs", json={"name": "nat-vpc", "cidr": "10.7.0.0/16"})
    vpc_id = vpc_resp.json()["id"]
    sub_resp = client.post(
        f"/vpcs/{vpc_id}/subnets", json={"name": "nat-sub", "cidr": "10.7.1.0/24"}
    )
    sub_id = sub_resp.json()["id"]

    # Create
    response = client.post(f"/vpcs/{vpc_id}/nat-gateways", json={"subnet_id": sub_id})
    assert response.status_code == 201
    nat_id = response.json()["id"]

    # List
    response = client.get(f"/vpcs/{vpc_id}/nat-gateways")
    assert response.status_code == 200
    assert len(response.json()) >= 1

    # Delete
    response = client.delete(f"/nat-gateways/{nat_id}")
    assert response.status_code == 200

    # Delete 404
    response = client.delete(f"/nat-gateways/{nat_id}")
    assert response.status_code == 404


def test_internet_gateway_rest():
    vpc_resp = client.post("/vpcs", json={"name": "igw-vpc", "cidr": "10.8.0.0/16"})
    vpc_id = vpc_resp.json()["id"]

    # Create
    response = client.post(f"/vpcs/{vpc_id}/internet-gateways")
    assert response.status_code == 201
    # Note: The server code returns InternetGateway object.

    # List
    response = client.get(f"/vpcs/{vpc_id}/internet-gateways")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_delete_vpc_not_found():
    response = client.delete("/vpcs/vpc-nonexistent")
    assert response.status_code == 404


def test_delete_subnet_rest():
    vpc_resp = client.post("/vpcs", json={"name": "sub-del-vpc", "cidr": "10.9.0.0/16"})
    vpc_id = vpc_resp.json()["id"]
    sub_resp = client.post(
        f"/vpcs/{vpc_id}/subnets", json={"name": "del-sub", "cidr": "10.9.1.0/24"}
    )
    sub_id = sub_resp.json()["id"]

    response = client.delete(f"/subnets/{sub_id}")
    assert response.status_code == 200

    # 404 check
    response = client.delete(f"/subnets/{sub_id}")
    assert response.status_code == 404


def test_create_subnet_vpc_not_found():
    response = client.post(
        "/vpcs/vpc-nonexistent/subnets", json={"name": "fail", "cidr": "1.1.1.1/24"}
    )
    assert response.status_code == 404


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "control_plane_api_requests_total" in response.text


def test_get_vpc_not_found():
    response = client.get("/vpcs/vpc-missing")
    assert response.status_code == 404


def test_create_route_vpc_not_found():
    response = client.post(
        "/vpcs/vpc-missing/routes",
        json={
            "destination": "0.0.0.0/0",
            "next_hop": "igw-xx",
            "next_hop_type": "gateway",
        },
    )
    assert response.status_code == 404


def test_delete_route_not_found():
    response = client.delete("/routes/rtb-missing")
    assert response.status_code == 404


def test_sg_attach_not_found():
    response = client.post("/security-groups/sg-missing/attach?instance_id=i-1")
    assert response.status_code == 404


def test_create_nat_vpc_not_found():
    response = client.post(
        "/vpcs/vpc-missing/nat-gateways", json={"subnet_id": "sub-1"}
    )
    assert response.status_code == 404


def test_create_igw_vpc_not_found():
    response = client.post("/vpcs/vpc-missing/internet-gateways")
    assert response.status_code == 404
