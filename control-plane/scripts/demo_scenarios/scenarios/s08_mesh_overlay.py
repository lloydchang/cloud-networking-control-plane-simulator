from ..common import *

def run_s08_mesh_overlay():
    s8_name = "8. Private Mesh Overlay"
    create_scenario(
        title=s8_name,
        description="Zero-trust mesh overlay networking.",
        resource_order=[
            {"type": "vpc", "label": "Mesh Node West"},
            {"type": "vpc", "label": "Mesh Node East"}
        ]
    )
    mesh_west_id = create_vpc("Mesh Node West", "192.168.200.0/24", region="us-west", scenario=s8_name)
    mesh_east_id = create_vpc("Mesh Node East", "192.168.100.0/24", region="us-east", scenario=s8_name)
    
    if mesh_west_id: create_subnet(mesh_west_id, "Main", "192.168.200.0/24", cdc="CDC-11")
    if mesh_east_id: create_subnet(mesh_east_id, "Main", "192.168.100.0/24", cdc="CDC-1")
    
    if mesh_west_id and mesh_east_id:
        create_mesh_node(mesh_west_id, "mkey:west-node-01")
        create_mesh_node(mesh_east_id, "mkey:east-node-01")
        create_route(mesh_west_id, "192.168.100.0/24", mesh_east_id, "mesh_vpn")
        create_route(mesh_east_id, "192.168.200.0/24", mesh_west_id, "mesh_vpn")
