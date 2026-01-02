from ..common import *

def run_s21_subnet_level_peering():
    s21_name = "21. Subnet-Level Peering"
    create_scenario(
        title=s21_name,
        description="Restrict peering connectivity to specific subnets.",
        resource_order=[
            {"type": "vpc", "label": "Producer Service VPC"},
            {"type": "vpc", "label": "Consumer Client VPC"}
        ]
    )
    prod_vpc_id = create_vpc("Producer Service VPC", "10.221.0.0/16", scenario=s21_name)
    cons_vpc_id = create_vpc("Consumer Client VPC", "10.231.0.0/16", scenario=s21_name)
    if prod_vpc_id and cons_vpc_id:
        create_subnet(prod_vpc_id, "Exposed API Subnet", "10.221.1.0/24", cdc="CDC-1")
        create_subnet(prod_vpc_id, "Internal Data Subnet", "10.221.2.0/24", cdc="CDC-1")
        create_subnet(cons_vpc_id, "Client App Subnet", "10.231.1.0/24", cdc="CDC-1")
        create_route(cons_vpc_id, "10.221.1.0/24", prod_vpc_id, "vpc_peering")
        create_route(prod_vpc_id, "10.231.1.0/24", cons_vpc_id, "vpc_peering")
