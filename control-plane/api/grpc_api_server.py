import grpc
import logging
import asyncio
import os
import sys

# Workaround for absolute imports in generated gRPC stubs
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from concurrent import futures
from sqlalchemy.orm import Session
import cloud_networking_control_plane_simulator_pb2
import cloud_networking_control_plane_simulator_pb2_grpc
from .rest_api_server import SessionLocal
from . import shared_api_logic as services
from .models import (
    VPC as VPCModel,
    Subnet as SubnetModel,
    Route as RouteModel,
    SecurityGroup as SGModel,
    NATGateway as NATModel,
    InternetGateway as InternetGatewayModel,
)

import threading
import asyncio


class BackgroundLoop:
    def __init__(self):
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def run_task(self, coro):
        return asyncio.run_coroutine_threadsafe(coro, self.loop)


bg_loop = BackgroundLoop()


class NetworkService(cloud_networking_control_plane_simulator_pb2_grpc.NetworkServiceServicer):
    """
    gRPC implementation of the Network Service.
    Demonstrates "Polyglot" capability by providing a high-performance
    interface alongside the REST API.
    """

    def GetDB(self):
        """Helper to get a database session."""
        return SessionLocal()

    def ListVPCs(self, request, context):
        """
        List VPCs from the same SQLite Source of Truth used by the REST API.
        """
        db = self.GetDB()
        try:
            # Query the exact same SQLAlchemy models as FastAPI
            vpcs = (
                db.query(VPCModel)
                .limit(request.limit if request.limit > 0 else 100)
                .all()
            )

            response = cloud_networking_control_plane_simulator_pb2.ListVPCsResponse()
            for vpc in vpcs:
                pb_vpc = response.vpcs.add()
                pb_vpc.id = vpc.id
                pb_vpc.name = vpc.name
                pb_vpc.cidr = vpc.cidr
                pb_vpc.vni = vpc.vni
                pb_vpc.vrf = vpc.vrf
                pb_vpc.status = vpc.status
                # Todo: Add created_at timestamp conversion

            response.total = len(vpcs)
            return response
        finally:
            db.close()

    # Implemented CreateVPC using the shared service layer
    def CreateVPC(self, request, context):
        """
        Create a VPC using the shared logic.
        """
        db = self.GetDB()
        try:
            # Call the shared service logic
            new_vpc = services.create_vpc_logic(
                db,
                request.name,
                request.cidr,
                request.region if request.region else "us-east-1",
            )

            # Use the dedicated background loop
            bg_loop.run_task(services.provision_vpc_task(SessionLocal, new_vpc.id))

            # Construct proto response
            pb_vpc = cloud_networking_control_plane_simulator_pb2.VPC()
            pb_vpc.id = new_vpc.id
            pb_vpc.name = new_vpc.name
            pb_vpc.cidr = new_vpc.cidr
            pb_vpc.vni = new_vpc.vni
            pb_vpc.vrf = new_vpc.vrf
            pb_vpc.status = new_vpc.status

            return pb_vpc
        except Exception as e:
            context.abort(grpc.StatusCode.INTERNAL, f"Failed to create VPC: {str(e)}")
        finally:
            db.close()

    def DeleteVPC(self, request, context):
        db = self.GetDB()
        try:
            vpc = services.delete_vpc_logic(db, request.id)
            if not vpc:
                context.abort(grpc.StatusCode.NOT_FOUND, "VPC not found")

            bg_loop.run_task(services.deprovision_vpc_task(SessionLocal, request.id))
            return cloud_networking_control_plane_simulator_pb2.DeleteResponse(
                success=True, message="VPC deletion initiated"
            )
        finally:
            db.close()

    # Subnet Operations
    def CreateSubnet(self, request, context):
        db = self.GetDB()
        try:
            vpc = db.query(VPCModel).filter(VPCModel.id == request.vpc_id).first()
            if not vpc:
                context.abort(grpc.StatusCode.NOT_FOUND, "VPC not found")

            s = services.create_subnet_logic(
                db,
                request.vpc_id,
                request.name,
                request.cidr,
                request.availability_zone,
            )
            bg_loop.run_task(services.provision_subnet_task(SessionLocal, s.id))

            return cloud_networking_control_plane_simulator_pb2.Subnet(
                id=s.id,
                vpc_id=s.vpc_id,
                name=s.name,
                cidr=s.cidr,
                gateway=s.gateway,
                availability_zone=s.az,
                status="provisioning",
            )
        finally:
            db.close()

    def ListSubnets(self, request, context):
        db = self.GetDB()
        try:
            subnets = (
                db.query(SubnetModel).filter(SubnetModel.vpc_id == request.vpc_id).all()
            )
            response = cloud_networking_control_plane_simulator_pb2.ListSubnetsResponse()
            for s in subnets:
                sub = response.subnets.add()
                sub.id = s.id
                sub.vpc_id = s.vpc_id
                sub.name = s.name
                sub.cidr = s.cidr
                sub.gateway = s.gateway
                sub.availability_zone = s.az
                sub.status = "available"
            return response
        finally:
            db.close()

    # Route Operations
    def CreateRoute(self, request, context):
        db = self.GetDB()
        try:
            r = services.create_route_logic(
                db,
                request.vpc_id,
                request.destination,
                request.next_hop,
                request.next_hop_type,
            )
            return cloud_networking_control_plane_simulator_pb2.Route(
                id=r.id,
                vpc_id=r.vpc_id,
                destination=r.destination,
                next_hop=r.next_hop,
                next_hop_type=r.next_hop_type,
                priority=r.priority,
            )
        finally:
            db.close()

    # Security Group Operations
    def CreateSecurityGroup(self, request, context):
        db = self.GetDB()
        try:
            rules = [
                {
                    "direction": r.direction,
                    "protocol": r.protocol,
                    "port_from": r.port_from,
                    "port_to": r.port_to,
                    "cidr": r.cidr,
                }
                for r in request.rules
            ]
            sg = services.create_sg_logic(db, request.name, request.description, rules)
            pb_sg = cloud_networking_control_plane_simulator_pb2.SecurityGroup(
                id=sg.id, name=sg.name, description=sg.description
            )
            for r in sg.rules:
                rule = pb_sg.rules.add()
                rule.direction = r["direction"]
                rule.protocol = r["protocol"]
                rule.port_from = r["port_from"]
                rule.port_to = r["port_to"]
                rule.cidr = r["cidr"]
            return pb_sg
        finally:
            db.close()

    # NAT Gateway
    def CreateNATGateway(self, request, context):
        db = self.GetDB()
        try:
            nat = services.create_nat_logic(db, request.vpc_id, request.subnet_id)
            return cloud_networking_control_plane_simulator_pb2.NATGateway(
                id=nat.id,
                vpc_id=nat.vpc_id,
                subnet_id=nat.subnet_id,
                public_ip=nat.public_ip,
                status="provisioning",
            )
        finally:
            db.close()


def serve(port=50051):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    cloud_networking_control_plane_simulator_pb2_grpc.add_NetworkServiceServicer_to_server(
        NetworkService(), server
    )
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"gRPC Server started on port {port}")
    server.wait_for_termination()
