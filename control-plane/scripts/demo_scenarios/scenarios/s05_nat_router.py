from ..common import *

def run_s05_nat_router():
    s5_name = "5. NAT Router for Private Subnets"
    create_scenario(
        title=s5_name,
        description="Controlled internet access for isolated instances.",
        resource_order=[{"type": "vpc", "label": "Egress Gateway VPC"}]
    )
    nat_vpc_id = create_vpc("Egress Gateway VPC", "10.40.0.0/16", region="us-east-1", scenario=s5_name)
    if nat_vpc_id:
        create_subnet(nat_vpc_id, "Public Gateway", "10.40.1.0/24", cdc="CDC-1")
        create_subnet(nat_vpc_id, "NAT Router Server", "10.40.1.100/32", cdc="CDC-1")
        create_subnet(nat_vpc_id, "Isolated Compute", "10.40.2.0/24", cdc="CDC-1")
        create_subnet(nat_vpc_id, "Worker Node Server", "10.40.2.10/32", cdc="CDC-1")
        run_request("POST", f"/vpcs/{nat_vpc_id}/internet-gateways")
        create_route(nat_vpc_id, "0.0.0.0/0", "igw-auto", "internet_gateway")
