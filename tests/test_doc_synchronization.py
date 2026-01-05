import os
import re
import yaml
import pytest

def test_synchronization():
    """Verify that ARCHITECTURE.md matches docker-compose.yml configuration."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    compose_path = os.path.join(base_dir, "docker-compose.yml")
    arch_path = os.path.join(base_dir, "docs", "ARCHITECTURE.md")

    with open(compose_path, "r") as f:
        compose = yaml.safe_load(f)
    
    with open(arch_path, "r") as f:
        arch_content = f.read()

    services = compose.get("services", {})

    # 1. Check Load Balancer IP
    lb_ip = services.get("load-balancer", {}).get("networks", {}).get("fabric", {}).get("ipv4_address")
    assert lb_ip == "10.0.0.103", f"Expected LB IP to be 10.0.0.103 in compose, found {lb_ip}"
    assert lb_ip in arch_content, f"LB IP {lb_ip} not found in ARCHITECTURE.md"

    # 2. Check NAT/Internet Gateway IP
    # In ARCHITECTURE.md Outbound diagram: Internet-GW (203.0.113.2)
    igw_ip = services.get("internet-gateway", {}).get("networks", {}).get("internet", {}).get("ipv4_address")
    assert igw_ip == "203.0.113.2", f"Expected IGW IP to be 203.0.113.2 in compose, found {igw_ip}"
    # ARCHITECTURE.md mentions Internet-GW (NAT/Router) in text/diagrams
    assert igw_ip in arch_content, f"Internet Gateway IP {igw_ip} not found in ARCHITECTURE.md"

    # 3. Check Server-1 IP (Primary example)
    s1_ip = services.get("server-1", {}).get("networks", {}).get("vpc-100-leaf-1", {}).get("ipv4_address")
    assert s1_ip == "10.1.1.10", f"Expected Server-1 IP to be 10.1.1.10, found {s1_ip}"
    assert s1_ip in arch_content, f"Server-1 IP {s1_ip} not found in ARCHITECTURE.md"

    # 4. Check Server-3 Port Consistency (should be 80)
    s3_cmd = services.get("server-3", {}).get("command", "")
    assert "python3 -m http.server 80" in s3_cmd, "Server-3 should be configured for port 80"

    # 5. Check Simulated User IP (Conflict prevention)
    # Ensure it's .250 as per latest implementation plan to avoid NAT NAT collisions (.10+)
    assert "203.0.113.250" in arch_content, "Simulated User IP 203.0.113.250 not found in ARCHITECTURE.md"

    # 6. Check Leaf VPC isolation (VRF consistency)
    # docker-compose.yml shows leaf-1 has both vpc-100 and vpc-200 networks
    l1_networks = services.get("leaf-1", {}).get("networks", {})
    assert "vpc-100-leaf-1" in l1_networks
    assert "vpc-200-leaf-1" in l1_networks
    
    # Check that ARCHITECTURE.md diagram shows VRF: 100/200 on leafs
    # Regex to find VRF: 100/200 inside Leaf-1/2 boxes
    assert "VRF: 100/200" in arch_content, "ARCHITECTURE.md should list both VRFs (100 and 200) on Leaf switches"

    # 7. Check NETWORKING.md presence and links
    nw_path = os.path.join(base_dir, "docs", "NETWORKING.md")
    assert os.path.exists(nw_path)
    with open(nw_path, "r") as f:
        nw_content = f.read()
    assert "[Architecture Overview](ARCHITECTURE.md)" in nw_content

if __name__ == "__main__":
    pytest.main([__file__])
