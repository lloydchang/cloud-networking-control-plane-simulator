from ..common import *

def run_s14_network_lifecycle():
    s14_name = "14. Network Lifecycle: Automated vs Manual"
    create_scenario(
        title=s14_name,
        description="Contrast automated regional coverage with manual precision.",
        resource_order=[
            {"type": "vpc", "label": "Automated Regional VPC"},
            {"type": "vpc", "label": "Manual Controlled VPC"}
        ]
    )
    auto_vpc_id = create_vpc("Automated Regional VPC", "10.128.0.0/9", scenario=s14_name)
    cust_vpc_id = create_vpc("Manual Controlled VPC", "10.13.0.0/16", scenario=s14_name)
    if auto_vpc_id:
        create_subnet(auto_vpc_id, "Auto Subnet us-east1", "10.128.0.0/20", cdc="CDC-1")
        create_subnet(auto_vpc_id, "Auto Subnet us-west1", "10.136.0.0/20", cdc="CDC-11")
        create_subnet(auto_vpc_id, "Auto Subnet europe-west1", "10.144.0.0/20", cdc="CDC-2")
    if cust_vpc_id:
        create_subnet(cust_vpc_id, "Manual Subnet A", "10.13.1.0/24", cdc="CDC-1")
        create_subnet(cust_vpc_id, "Manual Subnet B", "10.13.2.0/24", cdc="CDC-1")
