from ..common import *

def run_s23_cloud_native_service_hub():
    s23_name = "23. Cloud-Native Service Hub"
    create_scenario(
        title=s23_name,
        description="Identity-based service connectivity layer.",
        resource_order=[
            {"type": "hub", "label": "Service Mesh Hub"},
            {"type": "vpc", "label": "Checkout VPC"},
            {"type": "vpc", "label": "Inventory VPC"},
            {"type": "vpc", "label": "Client VPC"}
        ]
    )
    mesh_hub_id = create_hub("Service Mesh Hub", region="global", scenario=s23_name)
    check_id = create_vpc("Checkout VPC", "10.25.1.0/24", scenario=s23_name)
    inv_id = create_vpc("Inventory VPC", "10.25.2.0/24", scenario=s23_name)
    client_id = create_vpc("Client VPC", "10.26.0.0/16", scenario=s23_name)
    if mesh_hub_id and check_id and inv_id and client_id:
        create_subnet(check_id, "Checkout Backend", "10.25.1.5/32", cdc="CDC-1")
        create_subnet(inv_id, "Inventory Backend", "10.25.2.10/32", cdc="CDC-1")
        create_subnet(client_id, "Web App Client", "10.26.1.100/32", cdc="CDC-11")
        for vpc_id in [check_id, inv_id, client_id]:
            create_route(vpc_id, "10.0.0.0/8", mesh_hub_id, "service_mesh")
            create_hub_route(mesh_hub_id, f"svc.{vpc_id}.local", vpc_id, "service_mesh")
