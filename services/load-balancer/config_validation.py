#!/usr/bin/env python3
"""
Configuration Validation for Load Balancer Controller

Provides functions to sanitize and validate load balancer configuration data
to prevent configuration injection vulnerabilities.
"""

import re
from typing import Dict, List, Any

# Stricter regex for names to prevent injection of newlines or other commands
# Allows alphanumeric, dash, and underscore
SAFE_NAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]+$")

def is_safe_name(name: str) -> bool:
    """Check if a name is safe for use in HAProxy config."""
    return SAFE_NAME_REGEX.match(name) is not None

def validate_port(port: Any) -> bool:
    """Validate that a port is an integer between 1 and 65535."""
    return isinstance(port, int) and 0 < port <= 65535

def validate_ip_address(ip: str) -> bool:
    """Basic validation for IPv4 addresses."""
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    return all(part.isdigit() and 0 <= int(part) <= 255 for part in parts)

def validate_server(server: Dict[str, Any]) -> List[str]:
    """Validate a single server configuration."""
    errors = []
    if not is_safe_name(server.get("name", "")):
        errors.append(f"Invalid server name: {server.get('name')}")
    if not validate_ip_address(server.get("address", "")):
        errors.append(f"Invalid IP address for server {server.get('name')}: {server.get('address')}")
    if not validate_port(server.get("port")):
        errors.append(f"Invalid port for server {server.get('name')}: {server.get('port')}")
    return errors

def validate_backend(backend: Dict[str, Any]) -> List[str]:
    """Validate a backend configuration."""
    errors = []
    if not is_safe_name(backend.get("name", "")):
        errors.append(f"Invalid backend name: {backend.get('name')}")

    servers = backend.get("servers", [])
    if not isinstance(servers, list):
        errors.append(f"Servers for backend {backend.get('name')} must be a list.")
    else:
        for server in servers:
            errors.extend(validate_server(server))
    return errors

def validate_frontend(frontend: Dict[str, Any]) -> List[str]:
    """Validate a frontend configuration."""
    errors = []
    if not is_safe_name(frontend.get("name", "")):
        errors.append(f"Invalid frontend name: {frontend.get('name')}")
    if not validate_port(frontend.get("port")):
        errors.append(f"Invalid port for frontend {frontend.get('name')}: {frontend.get('port')}")
    if not is_safe_name(frontend.get("backend", "")):
        errors.append(f"Invalid backend name for frontend {frontend.get('name')}: {frontend.get('backend')}")
    return errors

def validate_config_data(config: Dict[str, Any]) -> List[str]:
    """Validate the entire load balancer configuration."""
    errors = []

    frontends = config.get("frontends", [])
    if not isinstance(frontends, list):
        errors.append("Frontends must be a list.")
    else:
        for frontend in frontends:
            errors.extend(validate_frontend(frontend))

    backends = config.get("backends", [])
    if not isinstance(backends, list):
        errors.append("Backends must be a list.")
    else:
        for backend in backends:
            errors.extend(validate_backend(backend))

    return errors
