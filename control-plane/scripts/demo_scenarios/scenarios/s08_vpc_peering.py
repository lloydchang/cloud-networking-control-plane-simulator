from ..common import *

def run_s08_vpc_peering():
    s8_name = "8. VPC Peering"
    create_scenario(
        title=s8_name,
        description="Simple VPC-to-VPC connectivity within the same region.",
        resource_order=[
            {"type": "vpc", "label": "Frontend VPC"},
            {"type": "vpc", "label": "Backend VPC"}
        ]
    )
    frontend_vpc_id = create_vpc("Frontend VPC", "10.50.0.0/16", region="us-east-1", scenario=s8_name)
    backend_vpc_id = create_vpc("Backend VPC", "10.51.0.0/16", region="us-east-1", scenario=s8_name)
    
    if frontend_vpc_id and backend_vpc_id:
        create_subnet(frontend_vpc_id, "Web Subnet", "10.50.1.0/24", cdc="CDC-1")
        create_subnet(frontend_vpc_id, "Web Server", "10.50.1.10/32", cdc="CDC-1")
        create_subnet(backend_vpc_id, "App Subnet", "10.51.1.0/24", cdc="CDC-1")
        create_subnet(backend_vpc_id, "App Server", "10.51.1.20/32", cdc="CDC-1")
        
        # Create bidirectional peering routes
        create_route(frontend_vpc_id, "10.51.0.0/16", backend_vpc_id, "vpc_peering")
        create_route(backend_vpc_id, "10.50.0.0/16", frontend_vpc_id, "vpc_peering")

