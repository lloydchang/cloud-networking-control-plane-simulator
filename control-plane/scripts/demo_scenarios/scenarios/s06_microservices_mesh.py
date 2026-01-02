from ..common import *

def run_s06_microservices_mesh():
    s6_name = "6. Secure Microservices Mesh"
    create_scenario(
        title=s6_name,
        description="Secure service-to-service communication.",
        resource_order=[{"type": "vpc", "label": "Platform VPC"}]
    )
    ms_vpc_id = create_vpc("Platform VPC", "10.50.0.0/16", region="us-east-1", scenario=s6_name)
    if ms_vpc_id:
        create_subnet(ms_vpc_id, "Identity Service", "10.50.1.0/24", cdc="CDC-1")
        create_subnet(ms_vpc_id, "Identity Server", "10.50.1.5/32", cdc="CDC-1")
        create_subnet(ms_vpc_id, "Catalog Service", "10.50.2.0/24", cdc="CDC-1")
        create_subnet(ms_vpc_id, "Catalog Server", "10.50.2.10/32", cdc="CDC-1")
        create_subnet(ms_vpc_id, "Order Service", "10.50.3.0/24", cdc="CDC-1")
        create_subnet(ms_vpc_id, "Order Server", "10.50.3.15/32", cdc="CDC-1")
