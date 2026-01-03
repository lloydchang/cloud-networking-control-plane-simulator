# control-plane/scripts/demo_scenarios/common.py
import json
import urllib.request
import urllib.parse
import time
import sys
import docker
import ipaddress

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
            status_code = response.getcode()
            if status_code >= 400:
                error_detail = ""
                try:
                    error_json = json.loads(res_data)
                    if 'detail' in error_json:
                        error_detail = f" - {error_json['detail']}"
                except:
                    pass
                print(f"Request failed: {url} HTTP Error {status_code}: {response.reason}{error_detail}")
                return None
            return json.loads(res_data) if res_data else {}
    except urllib.error.HTTPError as e:
        error_detail = ""
        try:
            error_data = e.read().decode('utf-8')
            error_json = json.loads(error_data)
            if 'detail' in error_json:
                error_detail = f" - {error_json['detail']}"
        except:
            pass
        print(f"Request failed: {url} HTTP Error {e.code}: {e.reason}{error_detail}")
        return None
    except Exception as e:
        print(f"Request failed: {url} {e}")
        return None

def create_vpc(name, cidr, region="us-east-1", secondary_cidrs=None, scenario=None):
    vpcs = run_request("GET", "/vpcs") or []
    for vpc in vpcs:
        if vpc.get("name") == name and vpc.get("scenario") == scenario:
            print(f"VPC already exists: {name}")
            return vpc.get("id")

    print(f"Creating VPC: {name} ({cidr})")
    payload = {
        "name": name,
        "cidr": cidr,
        "region": region,
        "secondary_cidrs": secondary_cidrs or [],
        "scenario": scenario
    }
    res = run_request("POST", "/vpcs", data=payload)
    time.sleep(0.5)
    if res and 'id' in res:
        return res['id']
    return None

def create_subnet(vpc_id, name, cidr, cdc="CDC-1"):
    subnets = run_request("GET", f"/vpcs/{vpc_id}/subnets") or []
    for s in subnets:
        if s.get("name") == name and s.get("data_center") == cdc:
            return
    print(f"  + Subnet: {name} ({cidr}) in {cdc}")
    run_request("POST", f"/vpcs/{vpc_id}/subnets", data={
        "name": name,
        "cidr": cidr,
        "data_center": cdc
    })

def create_route(vpc_id, destination, next_hop, next_hop_type):
    path = f"/vpcs/{vpc_id}/routes"
    if vpc_id.startswith("dc-"):
        path = f"/standalone-dcs/{vpc_id}/routes"
    run_request("POST", path, data={
        "destination": destination,
        "next_hop": next_hop,
        "next_hop_type": next_hop_type
    })

def create_hub(name, region="global", scenario=None):
    view = run_request("GET", "/vpc") or {}
    nodes = view.get("nodes", [])
    for n in nodes:
        if n.get("type") == "hub" and n.get("label") == name and n.get("scenario") == scenario:
            print(f"Hub already exists: {name}")
            return n.get("id").removeprefix("hub-")
    print(f"+ Routing Hub: {name} ({region})")
    resp = run_request("POST", "/hubs", data={
        "name": name,
        "region": region,
        "scenario": scenario
    })
    if resp:
        return resp.get("id")
    return None

def create_scenario(title, description, resource_order=None):
    print(f"+ Scenario Metadata: {title}")
    run_request("POST", "/scenarios", data={
        "title": title,
        "description": description,
        "resource_order": resource_order or []
    })

def create_hub_route(hub_id, destination, next_hop, next_hop_type):
    run_request("POST", f"/hubs/{hub_id}/routes", data={
        "destination": destination,
        "next_hop": next_hop,
        "next_hop_type": next_hop_type
    })

def create_vpn_gateway(vpc_id, endpoint, pubkey, allowed_ips):
    run_request("POST", f"/vpcs/{vpc_id}/vpn_gateways", data={
        "endpoint": endpoint,
        "public_key": pubkey,
        "allowed_ips": allowed_ips
    })

def create_mesh_node(vpc_id, key):
    run_request("POST", f"/vpcs/{vpc_id}/mesh-nodes", data={
        "node_key": key,
        "tailnet": "demo-mesh"
    })

def create_standalone_dc(name, cidr, region="on-prem", scenario=None):
    view = run_request("GET", "/vpc") or {}
    nodes = view.get("nodes", [])
    for n in nodes:
        if n.get("type") == "standalone_dc" and n.get("label") == name and n.get("scenario") == scenario:
            print(f"Standalone DC already exists: {name}")
            return n.get("id").removeprefix("standalone-dc-")
    print(f"Creating Standalone DC: {name} ({cidr})")
    payload = {
        "name": name,
        "cidr": cidr,
        "region": region,
        "scenario": scenario
    }
    res = run_request("POST", "/standalone-dcs", data=payload)
    time.sleep(0.5)
    if res and 'id' in res:
        return res['id']
    return None

def create_standalone_dc_subnet(dc_id, name, cidr, odc="ODC-1"):
    run_request("POST", f"/standalone-dcs/{dc_id}/subnets", data={
        "name": name,
        "cidr": cidr,
        "data_center": odc
    })

def discover_existing_endpoints():
    """
    Discover running containers that can be adopted as brownfield endpoints.
    Returns a list of dicts with at least 'name' and 'ip' keys.
    """
    client = docker.from_env()
    endpoints = []
    for container in client.containers.list():
        try:
            # Inspect network settings to find IP addresses
            for net_name, net_data in container.attrs['NetworkSettings']['Networks'].items():
                ip = net_data.get('IPAddress')
                if ip:
                    endpoints.append({'name': container.name, 'ip': ip})
        except Exception as e:
            print(f"Skipping container {container.name}: {e}")
    return endpoints

def ip_in_cidr(ip, cidr):
    if not ip:
        return False
    return ipaddress.ip_address(ip) in ipaddress.ip_network(cidr)

def assert_brownfield_endpoints_exist(cidr, scenario):
    """
    Fail the scenario if no existing endpoints are detected
    within the provided CIDR on the fabric.
    """

    endpoints = discover_existing_endpoints()

    matching = []
    for ep in endpoints:
        if ip_in_cidr(ep.get("ip"), cidr):
            matching.append(ep)

    if not matching:
        raise RuntimeError(
            f"[{scenario}] Brownfield adoption failed: "
            f"no existing endpoints found in CIDR {cidr}"
        )

# control-plane/scripts/demo_scenarios/common.py
def list_brownfield_endpoints(cidr):
    """
    Return all endpoints within the given CIDR.
    """
    endpoints = discover_existing_endpoints()
    matching = [ep for ep in endpoints if ip_in_cidr(ep.get("ip"), cidr)]
    return matching

def is_endpoint_conflicting(endpoint, vpc_id):
    """
    Returns True if the endpoint IP conflicts with any existing subnet in the VPC.
    Otherwise False (safe to adopt).
    """
    # Get all subnets in the VPC
    subnets = run_request("GET", f"/vpcs/{vpc_id}/subnets") or []
    ep_ip = endpoint.get("ip")
    for s in subnets:
        if ip_in_cidr(ep_ip, s.get("cidr", "")):
            # Endpoint IP is inside an existing subnet, adoptable
            return False
    # If not in any subnet, treat as conflict
    return True

def attach_endpoint_to_vpc(endpoint_name, vpc_id, subnet_name):
    """
    Attach a brownfield endpoint to the given VPC and subnet.
    """
    # Check if endpoint already exists in the VPC
    existing_endpoints = run_request("GET", f"/vpcs/{vpc_id}/endpoints") or []
    for existing_ep in existing_endpoints:
        if existing_ep.get("name") == endpoint_name:
            log_scenario("DEBUG", f"Endpoint {endpoint_name} already exists in VPC {vpc_id}, skipping creation")
            return
    
    # Get the endpoint IP from the existing endpoints
    endpoints = discover_existing_endpoints()
    endpoint_ip = None
    for ep in endpoints:
        if ep.get("name") == endpoint_name:
            endpoint_ip = ep.get("ip")
            break
    
    if not endpoint_ip:
        raise Exception(f"Endpoint {endpoint_name} not found in existing endpoints")
    
    payload = {
        "name": endpoint_name,
        "ip": endpoint_ip
    }
    run_request("POST", f"/vpcs/{vpc_id}/endpoints", data=payload)

def select_subnet_for_endpoint(endpoint, vpc_id):
    """
    Returns the name of the subnet in which the endpoint IP belongs.
    Returns None if no matching subnet is found.
    """
    ep_ip = endpoint.get("ip")
    subnets = run_request("GET", f"/vpcs/{vpc_id}/subnets") or []
    for s in subnets:
        if ip_in_cidr(ep_ip, s.get("cidr", "")):
            return s.get("name")
    return None

def log_scenario(scenario_name, message):
    """
    Log a message prefixed with the scenario name.
    """
    print(f"[{scenario_name}] {message}")

def simulate_control_plane_restart(scenario_name):
    """Simulate a restart by waiting to emulate reconciliation downtime."""
    print(f"Simulating control plane restart for scenario: {scenario_name}")
    time.sleep(1)  # simulate downtime
    print(f"Control plane restarted for scenario: {scenario_name}")

def reconcile_scenario(scenario_name):
    """Simulate a control plane reconciliation cycle."""
    print(f"Reconciling scenario: {scenario_name}")
    time.sleep(1)  # simulate reconciliation
    print(f"Reconciliation complete for scenario: {scenario_name}")

def wipe_demo_resources():
    print("--- Wiping existing demo resources to ensure clean state ---")
    view = run_request("GET", "/vpc") or {}
    nodes = view.get("nodes", [])
    for n in nodes:
        if n.get("type") == "vpc" and n.get("scenario"):
            vpc_id = n.get("id").removeprefix("vpc-")
            print(f"Deleting VPC: {n.get('label')} ({vpc_id})")
            run_request("DELETE", f"/vpcs/{vpc_id}")
            time.sleep(0.2)
    for n in nodes:
        if n.get("type") == "hub" and n.get("scenario"):
            hub_id = n.get("id").removeprefix("hub-")
            print(f"Deleting Hub: {n.get('label')} ({hub_id})")
            run_request("DELETE", f"/hubs/{hub_id}")
    for n in nodes:
        if n.get("type") == "standalone_dc" and n.get("scenario"):
            dc_id = n.get("id").removeprefix("standalone-dc-")
            print(f"Deleting Standalone DC: {n.get('label')} ({dc_id})")
            run_request("DELETE", f"/standalone-dcs/{dc_id}")
    print("Wipe complete. Waiting for async deprovisions...")
    time.sleep(2)
