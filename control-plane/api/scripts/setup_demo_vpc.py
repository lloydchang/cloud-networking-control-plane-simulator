#!/usr/bin/env python3
import json
import urllib.request
import urllib.parse
import time

API_URL = "http://localhost:8000"

def run_request(method, path, data=None):
    url = f"{API_URL}{path}"
    req = urllib.request.Request(url, method=method)
    if data:
        json_data = json.dumps(data).encode('utf-8')
        req.add_header('Content-Type', 'application/json')
        req.data = json_data
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = response.read().decode('utf-8')
            return json.loads(res_data) if res_data else {}
    except Exception as e:
        print(f"Request failed: {url} {e}")
        return None

def create_demo_architecture():
    print("=== Provisioning HA Comparison Architecture ===")
    
    # --- PATTERN 1: REGIONAL PEERING (Connecting isolated Silos) ---
    # Goal: Connect 1 -> 2, 2 -> 3, 3 -> 1
    vpc_configs = [
        {"name": "single-dc-vpc-1", "cidr": "10.1.0.0/16", "dc": "CDC-1"},
        {"name": "single-dc-vpc-2", "cidr": "10.2.0.0/16", "dc": "CDC-2"},
        {"name": "single-dc-vpc-3", "cidr": "10.3.0.0/16", "dc": "CDC-3"},
    ]
    
    vpcs = {}
    for cfg in vpc_configs:
        res = run_request("POST", "/vpcs", data={"name": cfg['name'], "cidr": cfg['cidr']})
        if res:
            v_id = res['id']
            vpcs[cfg['name']] = v_id
            run_request("POST", f"/vpcs/{v_id}/subnets", data={"name": "Workload", "cidr": cfg['cidr'].replace(".0.0/16", ".1.0/24"), "data_center": cfg['dc']})
            print(f"  + Created {cfg['name']} in {cfg['dc']}")

    # Create Peering Routes (1->2, 2->3, 3->1)
    if all(name in vpcs for name in ["single-dc-vpc-1", "single-dc-vpc-2", "single-dc-vpc-3"]):
        # 1 -> 2
        run_request("POST", f"/vpcs/{vpcs['single-dc-vpc-1']}/routes", data={"destination": "10.2.0.0/16", "next_hop": vpcs['single-dc-vpc-2'], "next_hop_type": "vpc_peering"})
        # 2 -> 3
        run_request("POST", f"/vpcs/{vpcs['single-dc-vpc-2']}/routes", data={"destination": "10.3.0.0/16", "next_hop": vpcs['single-dc-vpc-3'], "next_hop_type": "vpc_peering"})
        # 3 -> 1
        run_request("POST", f"/vpcs/{vpcs['single-dc-vpc-3']}/routes", data={"destination": "10.1.0.0/16", "next_hop": vpcs['single-dc-vpc-1'], "next_hop_type": "vpc_peering"})
        print("  -> Established Triangular Peering mesh between Single-DC VPCs.")

    # --- PATTERN 2: NATIVE HA (Distributed VPC spanning sites) ---
    # Goal: Spans DC-11, DC-12, DC-13 within a single 192.168.0.0/16 container.
    print("\n[Pattern 2] Provisioning 'multi-dc-vpc' (Distributed 192.168.0.0/16)...")
    res = run_request("POST", "/vpcs", data={"name": "multi-dc-vpc", "cidr": "192.168.0.0/16"})
    if res:
        v_id = res['id']
        subnets = [
            {"name": "Public-11", "cidr": "192.168.0.0/19", "data_center": "CDC-11"},
            {"name": "Public-12", "cidr": "192.168.32.0/19", "data_center": "CDC-12"},
            {"name": "Public-13", "cidr": "192.168.64.0/19", "data_center": "CDC-13"},
            {"name": "Private-11", "cidr": "192.168.96.0/19", "data_center": "CDC-11"},
            {"name": "Private-12", "cidr": "192.168.128.0/19", "data_center": "CDC-12"},
        ]
        active_subnets = []
        for s in subnets:
            res_s = run_request("POST", f"/vpcs/{v_id}/subnets", data=s)
            if res_s: 
                active_subnets.append(res_s)
                print(f"  + Subnet: {s['name']} -> {s['data_center']}")
        
        # Internals connection demonstration (Logical mesh handled by underlay)
        print("  -> Inter-CDC traffic (11 <-> 12 <-> 13) is natively routed within this logical boundary.")

    print("\n=== Provisioning Complete ===")

if __name__ == "__main__":
    create_demo_architecture()
