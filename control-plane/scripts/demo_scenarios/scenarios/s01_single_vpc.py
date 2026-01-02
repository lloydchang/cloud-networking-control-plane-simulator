from ..common import *

def run_s01_single_vpc():
    s1_name = "1. Single VPC"
    create_scenario(
        title=s1_name,
        description="Simplest cloud network with one public subnet.",
        resource_order=[{"type": "vpc", "label": "Web VPC"}]
    )
    basic_vpc_id = create_vpc("Web VPC", "10.0.0.0/16", region="us-east-1", scenario=s1_name)
    if basic_vpc_id:
        create_subnet(basic_vpc_id, "Public Subnet", "10.0.1.0/24", cdc="CDC-1")
        run_request("POST", f"/vpcs/{basic_vpc_id}/internet-gateways")
        create_route(basic_vpc_id, "1.0.0.0/0", "igw-auto", "internet_gateway")
