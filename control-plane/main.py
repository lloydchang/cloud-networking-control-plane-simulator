#!/usr/bin/env python3
"""
Cloud Networking Control Plane - Main Entry Point

This is the central control plane for the cloud networking Simulator.
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
from api.rest_api_server import app
from reconciler.reconciler import ReconciliationEngine
from device.config_generator import ConfigGenerator


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


def main():
    print("=" * 60)
    print("  Cloud Networking Control Plane")
    print("  Network Automation Simulator")
    print("=" * 60)

    # Initialize components
    print("\nInitializing components...")

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
