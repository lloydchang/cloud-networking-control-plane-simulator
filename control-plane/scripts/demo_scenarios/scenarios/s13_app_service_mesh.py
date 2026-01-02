from ..common import *

def run_s13_app_service_mesh():
    s13_name = "13. Secure Application Service Mesh"
    create_scenario(
        title=s13_name,
        description="High-level application-layer mesh across multiple tiers.",
        resource_order=[
            {"type": "vpc", "label": "Frontend Mesh VPC"},
            {"type": "vpc", "label": "Backend Mesh VPC"},
            {"type": "vpc", "label": "Data Mesh VPC"}
        ]
    )
    fe_vpc_id = create_vpc("Frontend Mesh VPC", "10.110.0.0/16", scenario=s13_name)
    be_vpc_id = create_vpc("Backend Mesh VPC", "10.120.0.0/16", scenario=s13_name)
    da_vpc_id = create_vpc("Data Mesh VPC", "10.130.0.0/16", scenario=s13_name)
    if fe_vpc_id and be_vpc_id and da_vpc_id:
        create_subnet(fe_vpc_id, "Mesh Ingress", "10.110.1.0/24", cdc="CDC-1")
        create_subnet(be_vpc_id, "Service Tier", "10.120.1.0/24", cdc="CDC-1")
        create_subnet(da_vpc_id, "Storage Tier", "10.130.1.0/24", cdc="CDC-1")
        create_route(fe_vpc_id, "10.120.0.0/16", be_vpc_id, "service_mesh")
        create_route(be_vpc_id, "10.130.0.0/16", da_vpc_id, "service_mesh")
