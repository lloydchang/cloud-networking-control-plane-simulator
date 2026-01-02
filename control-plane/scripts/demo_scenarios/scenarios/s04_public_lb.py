from ..common import *

def run_s04_public_lb():
    s4_name = "4. Public Load Balancer & Private Backend"
    create_scenario(
        title=s4_name,
        description="Ingress traffic management with a public listener and private workers.",
        resource_order=[{"type": "vpc", "label": "Application Service"}]
    )
    lb_vpc_id = create_vpc("Application Service", "10.30.0.0/16", region="us-east-1", scenario=s4_name)
    if lb_vpc_id:
        create_subnet(lb_vpc_id, "Frontend Entry", "10.30.1.0/24", cdc="CDC-1")
        create_subnet(lb_vpc_id, "Load Balancer Server", "10.30.1.5/32", cdc="CDC-1")
        create_subnet(lb_vpc_id, "Backend Pool", "10.30.2.0/24", cdc="CDC-1")
        create_subnet(lb_vpc_id, "App Server 1", "10.30.2.11/32", cdc="CDC-1")
        create_subnet(lb_vpc_id, "App Server 2", "10.30.2.12/32", cdc="CDC-1")
        run_request("POST", f"/vpcs/{lb_vpc_id}/internet-gateways")
        create_route(lb_vpc_id, "0.0.0.0/0", "igw-auto", "internet_gateway")
