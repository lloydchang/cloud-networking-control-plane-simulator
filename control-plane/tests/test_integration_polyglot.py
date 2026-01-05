import pytest
import time
import os
import sys
import uuid

# Add the api directory to sys.path for gRPC generated stubs
# And the root directory for 'api' package imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "api")))

# Ensure DB writes to local dir BEFORE importing rest_api_server
os.environ["DB_DIR"] = "."
os.environ["DB_PATH"] = "./network_test.db"

from fastapi.testclient import TestClient
from api.rest_api_server import app, get_db, SessionLocal
from api.grpc_api_server import NetworkService
from api import cloud_networking_control_plane_simulator_pb2

# Use the same SessionLocal as rest_api_server (configured via env vars)
TestingSessionLocal = SessionLocal

# Patch gRPC to use the same SessionLocal
import api.grpc_api_server

api.grpc_api_server.SessionLocal = TestingSessionLocal


# Override get_db for consistency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


class MockContext:
    def abort(self, code, details):
        raise RuntimeError(f"gRPC Abort: {code} - {details}")


@pytest.fixture
def grpc_service():
    return NetworkService()


def test_polyglot_flow(grpc_service):
    # Use unique identifiers to avoid conflicts
    unique_id = uuid.uuid4().hex[:6]
    vpc_name = f"poly-vpc-{unique_id}"
    vpc_cidr = f"10.{hash(unique_id) % 200 + 50}.0.0/16"

    # 1. Create VPC via REST
    resp = client.post("/vpcs", json={"name": vpc_name, "cidr": vpc_cidr})
    assert resp.status_code == 201, f"Failed to create VPC: {resp.text}"
    vpc_id = resp.json()["id"]

    # 2. Verify via gRPC
    # Note: ListVPCs takes a request object
    list_req = cloud_networking_control_plane_simulator_pb2.ListVPCsRequest(limit=1000)
    list_resp = grpc_service.ListVPCs(list_req, MockContext())

    found = False
    for v in list_resp.vpcs:
        if v.id == vpc_id:
            assert v.name == vpc_name
            assert v.cidr == vpc_cidr
            found = True
            break
    assert found, f"VPC {vpc_id} created via REST not visible via gRPC"

    # 3. Create Subnet via REST
    resp = client.post(
        f"/vpcs/{vpc_id}/subnets", json={"name": "poly-sub", "cidr": "10.50.1.0/24"}
    )
    assert resp.status_code == 201
    sub_id = resp.json()["id"]

    # 4. Verify Subnet via gRPC
    sub_req = cloud_networking_control_plane_simulator_pb2.ListSubnetsRequest(vpc_id=vpc_id)
    sub_resp = grpc_service.ListSubnets(sub_req, MockContext())
    assert len(sub_resp.subnets) >= 1
    assert sub_resp.subnets[0].id == sub_id
    assert sub_resp.subnets[0].cidr == "10.50.1.0/24"

    # 5. Delete VPC via gRPC (Cross-control!)
    # Wait, can we? Yes, if implemented.
    del_req = cloud_networking_control_plane_simulator_pb2.DeleteVPCRequest(id=vpc_id)
    del_resp = grpc_service.DeleteVPC(del_req, MockContext())
    assert del_resp.success is True

    # 6. Verify Deletion in REST (should be 404 or deleting)
    # The task runs in background, give it a moment?
    # REST TestClient might NOT run grpc background loop.
    # We might need to manually run the task if we want to verify "gone".
    # But checking status via REST immediately:
    resp = client.get(f"/vpcs/{vpc_id}")
    if resp.status_code == 200:
        assert resp.json()["status"] == "deleting"
    else:
        assert resp.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__])
