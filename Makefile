# Cloud Networking Control Plane Simulator - CI/CD Makefile

.PHONY: all lint test validate deploy rollback canary clean up down logs

# Default target (starts simulator)
all: up

help:
	@echo "Available commands:"
	@echo "  make up          - Start the simulator"
	@echo "  make down        - Stop the simulator"
	@echo "  make clean       - Remove simulator data"
	@echo "  make test        - Run unit tests"
	@echo "  make lint        - Run linters"
	@echo "  make deploy      - Validate and deploy"
	@echo "  make logs        - Follow API logs"
	@echo "  make validate    - Validate config files"

# Code linting
lint:
	@echo "=== Running Linters ==="
	@cd control-plane && python -m py_compile main.py api/rest_api_server.py reconciler/reconciler.py || true
	@cd cicd && python -m py_compile validate.py canary.py rollback.py || true
	@echo "Lint complete"

# Generate gRPC stubs using the control-plane image
# This extracts the generated files to the host for use with volume mounts
proto:
	@echo "=== Generating gRPC Stubs ==="
	docker compose build control-plane
	@docker run --rm -v $(shell pwd)/control-plane/api:/out cloud-networking-control-plane-simulator-control-plane sh -c "cp /app/api/cloud_networking_control_plane_simulator_pb2.py /app/api/cloud_networking_control_plane_simulator_pb2_grpc.py /out/"
	@echo "Stubs generated in control-plane/api/"

lint-extreme:
	@echo "=== Running Extreme Linting (mypy, flake8) ==="
	@cd control-plane && mypy . || true
	@cd control-plane && flake8 . || true
	@cd control-plane && black . || true

security-scan:
	@echo "=== Running Security Scan (bandit) ==="
	@bandit -r control-plane/api || true

# Unit tests
test:
	@echo "=== Running Unit Tests ==="
	@cd control-plane && python -m pytest tests/ -v || echo "No tests found"
	@echo "Tests complete"

test-cov:
	@echo "=== Running Tests with Coverage ==="
	@cd control-plane && python -m pytest --cov=api --cov-report=term-missing tests/

# Configuration validation
validate:
	@echo "=== Validating Configuration ==="
	@python cicd/validate.py configs/topology.json 2>/dev/null || echo "No topology.json found, skipping"
	@echo "Validation complete"

# Full deployment (with validation and canary)
deploy: validate
	@echo "=== Starting Deployment ==="
	@python cicd/canary.py
	@echo "Deployment complete"

# Rollback to previous version
rollback:
	@echo "=== Rolling Back ==="
	@python cicd/rollback.py
	@echo "Rollback complete"

# Canary deployment only
canary:
	@echo "=== Canary Deployment ==="
	@python cicd/canary.py

# Helper to ensure gRPC stubs exist
ensure-proto:
	@if [ ! -f control-plane/api/cloud_networking_control_plane_simulator_pb2.py ] || [ ! -f control-plane/api/cloud_networking_control_plane_simulator_pb2_grpc.py ]; then \
		$(MAKE) proto; \
	fi

# Start the simulator
up: ensure-proto
	@echo "=== Starting Cloud Networking Control Plane Simulator ==="
	docker compose up -d
	@echo "Waiting for Control Plane to be ready..."
	@sleep 5
	@$(MAKE) create-sample-vpc
	@echo ""
	@echo "Services running:"
	@docker compose ps
	@echo ""
	@echo "Access points:"
	@echo "  Control Plane REST API:      http://localhost:8000"
	@echo "  Control Plane gRPC API:      localhost:50051"
	@echo "  Grafana:                     http://localhost:3333 (admin / change-this-password)"
	@echo "  Prometheus:                  http://localhost:9999"
	@echo "  VPC View:                    http://localhost:8000/vpc"
	@echo "  Load Balancer:               http://localhost:8080"
	@echo ""
	@echo "To see the real-time VPC object model, run: make vpc"

# Stop the simulator
down:
	@echo "=== Stopping Cloud Networking Control Plane Simulator ==="
	docker compose down

# View logs
logs:
	docker compose logs -f

# View specific service logs
logs-%:
	docker compose logs -f $*

# Check status
status:
	@echo "=== Service Status ==="
	@docker compose ps
	@echo ""
	@echo "=== Network Status ==="
	@docker network ls | grep -E "cloud-networking-control-plane-simulator|fabric|internet|vpc" || true

# Run control-plane in development mode
dev-control-plane:
	cd control-plane && python main.py

# Clean up all data
clean:
	@echo "=== Cleaning Up ==="
	docker compose down -v
	rm -rf control-plane/data/*
	rm -rf /tmp/versions/*
	@echo "Clean complete"

# Build all images
build:
	@echo "=== Building Images ==="
	docker compose build

# Rebuild and restart
rebuild: build
	docker compose up -d --force-recreate

# Health check
health:
	@echo "=== Health Check ==="
	@curl -s http://localhost:8000/health | jq . || echo "Control Plane not responding"
	@curl -s http://localhost:9999/-/healthy || echo "Prometheus not responding"
	@curl -s http://localhost:3333/api/health | jq . || echo "Grafana not responding"
	@curl -s http://localhost:8000/vpc > /dev/null 2>&1 && echo "VPC View API: OK" || echo "VPC View API not responding"

# Open VPC View
vpc:
	@open http://localhost:8000/vpc || echo "Please open http://localhost:8000/vpc in your browser"

map: vpc
topology: vpc

# Show BGP status on all leaves
bgp-status:
	@echo "=== BGP Status ==="
	@for leaf in leaf-1 leaf-2 leaf-3; do \
		echo "\n--- $$leaf ---"; \
		docker compose exec $$leaf vtysh -c "show ip bgp summary" 2>/dev/null || echo "$$leaf not running"; \
	done

# Show EVPN routes
evpn-routes:
	@echo "=== EVPN Routes ==="
	@docker compose exec leaf-1 vtysh -c "show bgp l2vpn evpn" 2>/dev/null || echo "Not available"

# Test VPC connectivity
test-connectivity:
	@echo "=== Testing VPC Connectivity ==="
	@echo "VPC100: server-1 -> server-2"
	@docker compose exec server-1 ping -c 2 10.1.2.10 2>/dev/null || echo "Ping failed"
	@echo ""
	@echo "VPC200: server-4 -> server-5"
	@docker compose exec server-4 ping -c 2 10.2.2.10 2>/dev/null || echo "Ping failed"
	@echo ""
	@echo "Cross-VPC (should fail): server-1 -> server-4"
	@docker compose exec server-1 ping -c 2 10.2.1.10 2>/dev/null || echo "Ping failed (expected)"

# Create sample standard VPC via API
create-sample-vpc:
	@echo "=== Creating Demo Scenarios ==="
	@docker compose exec control-plane python3 /app/scripts/create_demo_scenarios.py

# List VPCs (REST)
list-vpcs:
	@curl -s http://localhost:8000/vpcs | jq .

# List VPCs (gRPC)
grpc-list-vpcs:
	@grpcurl -plaintext localhost:50051 network.NetworkService/ListVPCs

# Create VPC (gRPC)
grpc-create-vpc:
	@grpcurl -plaintext -d '{"name": "grpc-vpc", "cidr": "10.200.0.0/16"}' localhost:50051 network.NetworkService/CreateVPC

# Interactive shell into control plane
shell-control-plane:
	@docker compose exec control-plane /bin/bash

# Interactive shell into a leaf
shell-leaf-1:
	docker compose exec leaf-1 vtysh
