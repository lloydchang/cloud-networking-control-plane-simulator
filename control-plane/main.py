#!/usr/bin/env python3
"""
Cloud Networking Control Plane - Main Entry Point

This is the central control plane for the Cloud Networking Control Plane Simulator.
It manages:
- REST API for network operations
- gRPC server for high-performance operations  
- Intent reconciliation engine
- Linux datapath management
- Switch configuration
"""

import os
import asyncio
import threading
import uvicorn
from api.rest_api_server import app, SessionLocal
from reconciler.reconciler import ReconciliationEngine
from device.config_generator import ConfigGenerator
from metrics import METRICS
from api.models import (
    VPC as VPCModel,
    Subnet as SubnetModel,
    Route as RouteModel,
    SecurityGroup as SGModel,
    NATGateway as NATModel,
    InternetGateway as InternetGatewayModel,
    VPNGateway as VPNGatewayModel,
    MeshNode as MeshNodeModel,
)


def start_rest_api():
    """Start the FastAPI REST API server."""
    port = int(os.getenv("REST_PORT", 8000))
    print(f"Starting REST API on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


def start_grpc_server():
    """Start the gRPC server."""
    port = int(os.getenv("GRPC_PORT", 50051))
    print(f"Starting gRPC server on port {port}...")
    from api import grpc_api_server as grpc_server

    # Run gRPC in a separate thread so it doesn't block REST
    grpc_thread = threading.Thread(target=grpc_server.serve, args=(port,), daemon=True)
    grpc_thread.start()


def initialize_metrics():
    """Initialize Prometheus metrics from the database."""
    if not METRICS:
        print("  ! Metrics not enabled, skipping initialization.")
        return

    db = SessionLocal()
    try:
        print("  Initializing metrics from database...")
        METRICS["vpcs_total"].set(db.query(VPCModel).count())
        METRICS["subnets_total"].set(db.query(SubnetModel).count())
        METRICS["routes_total"].set(db.query(RouteModel).count())
        METRICS["security_groups_total"].set(db.query(SGModel).count())
        METRICS["nat_gateways_total"].set(db.query(NATModel).count())
        METRICS["internet_gateways_total"].set(db.query(InternetGatewayModel).count())
        METRICS["vpn_gateways_total"].set(db.query(VPNGatewayModel).count())
        METRICS["mesh_nodes_total"].set(db.query(MeshNodeModel).count())
        print("  ✓ Metrics initialized")
    except Exception as e:
        print(f"  ! Error initializing metrics: {e}")
    finally:
        db.close()


def main():
    print("=" * 60)
    print("  Cloud Networking Control Plane")
    print("  Network Automation Simulator")
    print("=" * 60)

    # Initialize components
    print("\nInitializing components...")

    # Initialize metrics from database
    initialize_metrics()

    # Start reconciliation engine in background
    try:
        reconciler = ReconciliationEngine()
        reconciler_thread = threading.Thread(target=reconciler.run, daemon=True)
        reconciler_thread.start()
        print("  ✓ Reconciliation Engine started")
    except Exception as e:
        print(f"  ! Reconciliation Engine failed to start (Docker missing?): {e}")
        print("    Continuing without reconciliation...")

    # Config generator
    config_gen = ConfigGenerator()
    print("  ✓ Config Generator initialized")

    print("\nStarting API servers...")

    # Start gRPC API (background)
    start_grpc_server()

    # Start REST API (blocking)
    start_rest_api()


if __name__ == "__main__":
    main()
