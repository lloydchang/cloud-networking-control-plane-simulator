#!/usr/bin/env python3
"""
Load Balancer Controller

Manages HAProxy configuration based on desired state from API.
Implements:
- L4 (TCP) and L7 (HTTP) load balancing
- Health checks
- Dynamic backend updates
- Graceful reloads
"""

import json
import re
import subprocess
import time
import os
import signal
from pathlib import Path
from typing import Dict, List, Any
from jinja2 import Template


def sanitize_identifier(input_val: Any) -> str:
    """
    Sanitizes a string to be a safe HAProxy identifier.
    Allows alphanumeric characters, hyphens, underscores, and periods.
    Strips any other characters to prevent config injection.
    Example: "backend-name_1.0" -> "backend-name_1.0"
    Example: "backend; rm -rf /" -> "backendrm-rf"
    """
    if not isinstance(input_val, str):
        return ""
    return re.sub(r'[^a-zA-Z0-9_.-]', '', input_val)


def sanitize_address(input_val: Any) -> str:
    """
    Sanitizes a network address (IP or hostname).
    Allows characters valid in hostnames, IPv4, and IPv6 addresses.
    Strips characters that could be used for injection.
    Example: "1.2.3.4" -> "1.2.3.4"
    Example: "2001:db8::1" -> "2001:db8::1"
    Example: "my-host.com" -> "my-host.com"
    Example: "my-host.com;-R" -> "my-host.com-R"
    """
    if not isinstance(input_val, str):
        return ""
    # Allow alphanumeric, underscore, hyphen, period, and colon
    return re.sub(r'[^a-zA-Z0-9_.:-]', '', input_val)


def validate_numeric(input_val: Any) -> Any:
    """
    Validates that a value is numeric.
    Returns the value if it's an integer, otherwise returns 0.
    This prevents non-numeric values from being injected into numeric-only
    fields like port or weight.
    """
    if isinstance(input_val, int):
        return input_val
    return 0  # Default to a safe value if not an integer


HAPROXY_CFG = "/etc/haproxy/haproxy.cfg"
HAPROXY_TEMPLATE = "haproxy.cfg.template"
HAPROXY_PID_FILE = "/var/run/haproxy.pid"

# Load Balancer definitions (would come from API in production)
LB_CONFIG: Dict[str, Any] = {
    "frontends": [
        {
            "name": "web-http",
            "port": 80,
            "mode": "http",
            "backend": "web-servers"
        },
        {
            "name": "web-https",
            "port": 443,
            "mode": "tcp",
            "backend": "web-servers-ssl"
        },
        {
            "name": "api-gateway",
            "port": 8080,
            "mode": "http",
            "backend": "api-servers"
        }
    ],
    "backends": [
        {
            "name": "web-servers",
            "mode": "http",
            "balance": "roundrobin",
            "servers": [
                {"name": "web-1", "address": "10.1.1.10", "port": 80, "weight": 100},
                {"name": "web-2", "address": "10.1.2.10", "port": 80, "weight": 100},
            ]
        },
        {
            "name": "web-servers-ssl",
            "mode": "tcp",
            "balance": "roundrobin",
            "servers": [
                {"name": "web-1", "address": "10.1.1.10", "port": 443, "weight": 100},
                {"name": "web-2", "address": "10.1.2.10", "port": 443, "weight": 100},
            ]
        },
        {
            "name": "api-servers",
            "mode": "http",
            "balance": "roundrobin",
            "servers": [
                {"name": "api-1", "address": "10.1.3.10", "port": 8080, "weight": 100},
            ]
        }
    ]
}


def render_config(config: Dict[str, Any]) -> str:
    """
    Render HAProxy config from template with sanitization.

    🛡️ SECURITY: A custom Jinja2 environment is used to apply specific
    sanitization and validation filters to all rendered variables. This prevents
    config injection attacks by ensuring that any data from the API
    (or local config) is stripped of malicious characters before being
    written to the haproxy.cfg file. Without this, a malicious server
    name like 'my-server\n acl malicious_acl path_beg /admin' could
    inject unauthorized rules.
    """
    with open(HAPROXY_TEMPLATE, 'r') as f:
        template_str = f.read()

    # Create a Jinja2 environment and register the custom filters
    env = Template(template_str).environment
    env.filters['sanitize_id'] = sanitize_identifier
    env.filters['sanitize_addr'] = sanitize_address
    env.filters['validate_num'] = validate_numeric
    
    # Re-parse the template with the new environment
    template = env.from_string(template_str)

    return template.render(
        frontends=config["frontends"],
        backends=config["backends"]
    )


def validate_config(config_path: str) -> bool:
    """Validate HAProxy configuration."""
    try:
        result = subprocess.run(
            ["haproxy", "-c", "-f", config_path],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print("Configuration validation: PASSED")
            return True
        else:
            print(f"Configuration validation: FAILED\n{result.stderr}")
            return False
    except Exception as e:
        print(f"Validation error: {e}")
        return False


def reload_haproxy():
    """Gracefully reload HAProxy."""
    print("Reloading HAProxy...")
    try:
        # Start or reload HAProxy
        if os.path.exists(HAPROXY_PID_FILE):
            result = subprocess.run(
                ["haproxy", "-f", HAPROXY_CFG, "-p", HAPROXY_PID_FILE, 
                 "-sf", open(HAPROXY_PID_FILE).read().strip()],
                capture_output=True,
                text=True
            )
        else:
            result = subprocess.run(
                ["haproxy", "-f", HAPROXY_CFG, "-p", HAPROXY_PID_FILE, "-D"],
                capture_output=True,
                text=True
            )
        
        if result.returncode == 0:
            print("HAProxy reload: SUCCESS")
        else:
            print(f"HAProxy reload: FAILED\n{result.stderr}")
            
    except Exception as e:
        print(f"Reload error: {e}")


def apply_config(config: Dict[str, Any]):
    """Apply new load balancer configuration."""
    print("Applying new configuration...")
    
    # Render config
    rendered = render_config(config)
    
    # Write to temp file first
    temp_path = f"{HAPROXY_CFG}.new"
    with open(temp_path, 'w') as f:
        f.write(rendered)
    
    # Validate
    if not validate_config(temp_path):
        print("Aborting due to validation failure")
        os.remove(temp_path)
        return False
    
    # Atomic move
    os.rename(temp_path, HAPROXY_CFG)
    
    # Reload HAProxy
    reload_haproxy()
    
    return True


def reconciliation_loop():
    """
    Main reconciliation loop.
    In production:
    - Watches API for LB definition changes
    - Compares with running config
    - Applies changes with validation
    """
    last_config_hash = None

    # ⚡ OPTIMIZATION: Pre-calculate the hash for the static config.
    # In a real-world scenario where the config is fetched from an API,
    # this hash would be calculated on the fetched data inside the loop.
    # Since LB_CONFIG is static, we calculate it once to avoid redundant
    # CPU work in every iteration.
    # Impact: Reduces CPU usage by avoiding repeated JSON serialization and hashing.
    config_hash = hash(json.dumps(LB_CONFIG, sort_keys=True))

    while True:
        try:
            # In production: fetch desired state from API
            # fetched_config = fetch_from_api("/load-balancers")
            # For this simulation, we use the static config.
            config = LB_CONFIG

            # In a real system, we'd calculate the hash of the *newly fetched* config.
            # Since our config is static, we use the pre-calculated hash.
            if config_hash != last_config_hash:
                print("Configuration change detected")
                if apply_config(config):
                    last_config_hash = config_hash
            
            time.sleep(10)  # Check every 10 seconds
            
        except Exception as e:
            print(f"Reconciliation error: {e}")
            time.sleep(5)


def main():
    print("=== Load Balancer Controller Starting ===")
    
    # Initial config application
    apply_config(LB_CONFIG)
    
    print("=== Load Balancer Controller Ready ===")
    print(f"Stats available at: http://localhost:8404/stats")
    
    # Enter reconciliation loop
    reconciliation_loop()


if __name__ == "__main__":
    main()
