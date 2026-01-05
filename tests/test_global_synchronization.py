import os
import re
import json
import yaml
import pytest
import glob

class ProjectPaths:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    COMPOSE_PATH = os.path.join(BASE_DIR, "docker-compose.yml")
    TOPOLOGY_PATH = os.path.join(BASE_DIR, "configs", "topology.json")
    ARCH_PATH = os.path.join(BASE_DIR, "docs", "ARCHITECTURE.md")
    INDEX_HTML_PATH = os.path.join(BASE_DIR, "docs", "index.html")
    SCENARIOS_DIR = os.path.join(BASE_DIR, "control-plane", "scripts", "demo_scenarios")

class TestContractConsistency:
    @pytest.fixture(scope="class")
    def compose_data(self):
        with open(ProjectPaths.COMPOSE_PATH, "r") as f:
            return yaml.safe_load(f)

    @pytest.fixture(scope="class")
    def topology_data(self):
        with open(ProjectPaths.TOPOLOGY_PATH, "r") as f:
            return json.load(f)

    @pytest.fixture(scope="class")
    def arch_content(self):
        with open(ProjectPaths.ARCH_PATH, "r") as f:
            return f.read()

    @pytest.fixture(scope="class")
    def static_vpc_data(self):
        """Extract the JSON object from window.STATIC_VPC_DATA in index.html"""
        with open(ProjectPaths.INDEX_HTML_PATH, "r") as f:
            content = f.read()
        
        # Regex to capture the JSON object after window.STATIC_VPC_DATA = 
        match = re.search(r'window\.STATIC_VPC_DATA\s*=\s*({.*?});', content, re.DOTALL)
        if not match:
            pytest.fail("Could not find window.STATIC_VPC_DATA in index.html")
        
        json_str = match.group(1)
        return json.loads(json_str)

    def test_topology_vs_compose_switches(self, topology_data, compose_data):
        """
        Contract: Every switch defined in topology.json must exist as a service in docker-compose.yml
        and share the same IP address.
        """
        services = compose_data.get("services", {})
        topo_switches = topology_data.get("switches", {})

        for switch_name, switch_conf in topo_switches.items():
            # Check existence
            assert switch_name in services, f"Switch {switch_name} from topology.json not found in docker-compose.yml"
            
            # Check IP (Router ID usually matches Loopback/Management IP)
            compose_networks = services[switch_name].get("networks", {})
            # Assuming 'fabric' network for management/router-id or checking loopback if defined
            # In this project's compose, leaf IPs are often on the 'fabric' network
            
            fabric_conf = compose_networks.get("fabric", {})
            if fabric_conf:
                compose_ip = fabric_conf.get("ipv4_address")
                # Note: Topology Router ID might differ from Fabric IP, but let's check basic alignment if possible
                # In this specific repo, router_id 10.0.0.11 corresponds to leaf-1 fabric IP commonly found in lab setups
                # If they strictly match, assert. If logic differs, we relax carefully.
                # Looking at topology.json: leaf-1 router_id is 10.0.0.11.
                # Looking at common docker-compose practices here: leaf-1 is 10.0.0.11.
                assert compose_ip == switch_conf["router_id"], \
                    f"IP Mismatch for {switch_name}: Topology({switch_conf['router_id']}) vs Compose({compose_ip})"

    def test_arch_doc_contains_critical_ips(self, arch_content, compose_data):
        """
        Contract: Key Infrastructure IPs defined in docker-compose.yml must be documented in ARCHITECTURE.md.
        """
        services = compose_data.get("services", {})
        
        # 1. Load Balancer
        lb = services.get("load-balancer", {})
        lb_ip = lb.get("networks", {}).get("fabric", {}).get("ipv4_address")
        if lb_ip:
            assert lb_ip in arch_content, f"Load Balancer IP {lb_ip} missing from ARCHITECTURE.md"

        # 2. Internet Gateway / NAT
        igw = services.get("internet-gateway", {})
        igw_ip = igw.get("networks", {}).get("internet", {}).get("ipv4_address")
        if igw_ip:
            assert igw_ip in arch_content, f"Internet Gateway IP {igw_ip} missing from ARCHITECTURE.md"

    def test_html_dashboard_data_consistency(self, static_vpc_data, topology_data):
        """
        Contract: The static dashboard data (used for visualization) should reflect valid
        structures compliant with the topology (where overlapping).
        
        Note: The dashboard visualizes 'Logical' VPCs (10.0.0.0/16 etc) which are 
        defined in the database/scenarios, while topology.json defines 'Underlay' resources.
        Here we check specifically for any Hardcoded Underlay references if they exist.
        """
        nodes = static_vpc_data.get("nodes", [])
        
        # Check Leaf Switch labels exist in HTML data
        leaf_ids = [n["id"] for n in nodes if n["type"] == "leaf"]
        # Only check 'leaf' switches from topology, assuming spines are not always visualized
        topo_leafs = [s for s in topology_data.get("switches", {}).keys() if "leaf" in s]
        
        for leaf in topo_leafs:
            # Dashboard uses specific IDs like 'leaf-1', 'leaf-2'
            # We enforce that the topology switches are represented in the UI
            assert leaf in leaf_ids, f"Topology switch {leaf} not found in Dashboard static data"

    def test_demo_scenario_files_exist(self):
        """
        Contract: Ensure that all basic/intermediate/advanced scenarios are physically present.
        """
        files = glob.glob(os.path.join(ProjectPaths.SCENARIOS_DIR, "scenarios", "*.py"))
        assert len(files) > 0, "No scenario python scripts found in control-plane/scripts/demo_scenarios/scenarios"

    def test_verify_networking_md_glossary_link(self):
        """
        Contract: NETWORKING.md must link to ARCHITECTURE.md glossary to avoid duplicating definitions.
        """
        nw_path = os.path.join(ProjectPaths.BASE_DIR, "docs", "NETWORKING.md")
        assert os.path.exists(nw_path)
        with open(nw_path, "r") as f:
            content = f.read()
        
        assert "ARCHITECTURE.md#glossary-of-acronyms" in content, \
            "NETWORKING.md is missing the link to the central Glossary in ARCHITECTURE.md"

if __name__ == "__main__":
    pytest.main([__file__])
