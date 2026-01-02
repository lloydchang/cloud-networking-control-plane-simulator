from ..common import *

def run_s02_multi_tier_vpc():
    s2_name = "2. Multi-tier VPC"
    create_scenario(
        title=s2_name,
        description="Professional VPC with public/private segmentation.",
        resource_order=[{"type": "vpc", "label": "Production VPC"}]
    )
    prod_vpc_id = create_vpc("Production VPC", "10.10.0.0/16", region="us-east-1", scenario=s2_name)
    if prod_vpc_id:
        create_subnet(prod_vpc_id, "Public Subnet", "10.10.1.0/24", cdc="CDC-1")
        create_subnet(prod_vpc_id, "Private Subnet", "10.10.2.0/24", cdc="CDC-1")
        create_subnet(prod_vpc_id, "Web Server", "10.10.1.10/32", cdc="CDC-1")
        create_subnet(prod_vpc_id, "Database Server", "10.10.2.50/32", cdc="CDC-1")
        run_request("POST", f"/vpcs/{prod_vpc_id}/internet-gateways")
        create_route(prod_vpc_id, "0.0.0.0/0", "igw-auto", "internet_gateway")
