from ..common import *

def run_s12_k8s_hybrid():
    s12_name = "12. Kubernetes Hybrid Network"
    create_scenario(
        title=s12_name,
        description="Complex enterprise connectivity with secondary addressing.",
        resource_order=[
            {"type": "vpc", "label": "Kubernetes Cluster 1"},
            {"type": "vpc", "label": "Kubernetes Cluster 2"},
            {"type": "hub", "label": "Cloud Routing Hub (NAT Flows)"},
            {"type": "hub", "label": "Cloud Routing Hub (Non-NAT Flows)"},
            {"type": "vpc", "label": "Shared Services"},
            {"type": "standalone_dc", "label": "On-Premise Data Center"}
        ]
    )
    
    nat_hub_id = create_hub("Cloud Routing Hub (NAT Flows)", region="global", scenario=s12_name)
    internal_hub_id = create_hub("Cloud Routing Hub (Non-NAT Flows)", region="global", scenario=s12_name)
    
    k8s1_id = create_vpc("Kubernetes Cluster 1", "10.1.0.0/16 & 100.64.0.0/16", secondary_cidrs=["100.64.0.0/16"], region="us-east", scenario=s12_name) 
    create_subnet(k8s1_id, "Public Subnet", "10.1.1.0/24", cdc="CDC-1")
    create_subnet(k8s1_id, "Private Subnet", "10.1.3.0/24", cdc="CDC-1")
    create_subnet(k8s1_id, "CGNAT Subnet", "100.64.0.0/19", cdc="CDC-1") 
    create_subnet(k8s1_id, "Public Subnet", "10.1.2.0/24", cdc="CDC-2")
    create_subnet(k8s1_id, "Private Subnet", "10.1.4.0/24", cdc="CDC-2")
    create_subnet(k8s1_id, "CGNAT Subnet", "100.64.32.0/19", cdc="CDC-2")

    k8s2_id = create_vpc("Kubernetes Cluster 2", "10.2.0.0/16 & 100.65.0.0/16", secondary_cidrs=["100.65.0.0/16"], region="us-west", scenario=s12_name)
    create_subnet(k8s2_id, "Public Subnet", "10.2.1.0/24", cdc="CDC-1") 
    create_subnet(k8s2_id, "Private Subnet", "10.2.3.0/24", cdc="CDC-1")
    create_subnet(k8s2_id, "CGNAT Subnet", "100.65.0.0/19", cdc="CDC-1")
    create_subnet(k8s2_id, "Public Subnet", "10.2.2.0/24", cdc="CDC-2") 
    create_subnet(k8s2_id, "Private Subnet", "10.2.4.0/24", cdc="CDC-2")
    create_subnet(k8s2_id, "CGNAT Subnet", "100.65.32.0/19", cdc="CDC-2")
    
    shared_id = create_vpc("Shared Services", "10.100.0.0/24", scenario=s12_name)
    create_subnet(shared_id, "Public Subnet", "10.100.0.64/27", cdc="CDC-1")
    create_subnet(shared_id, "NGW-DC Subnet", "10.100.0.32/27", cdc="CDC-1")
    create_subnet(shared_id, "Private Subnet", "10.100.0.128/26", cdc="CDC-1")
    create_subnet(shared_id, "Public Subnet", "10.100.0.96/27", cdc="CDC-2")
    create_subnet(shared_id, "NGW-DC Subnet", "10.100.0.0/27", cdc="CDC-2")
    create_subnet(shared_id, "Private Subnet", "10.100.0.192/26", cdc="CDC-2")

    corp_id = create_standalone_dc("On-Premise Data Center", "10.250.0.0/16", region="on-prem", scenario=s12_name)
    if corp_id:
        create_standalone_dc_subnet(corp_id, "Test Server", "10.0.1.117/32", odc="ODC-1")

    if nat_hub_id and internal_hub_id and k8s1_id and k8s2_id and shared_id and corp_id:
        for vpc_id in [k8s1_id, k8s2_id, shared_id]:
            create_route(vpc_id, "0.0.0.0/0", nat_hub_id, "cloud_routing_hub")
            create_route(vpc_id, "10.0.0.0/8", internal_hub_id, "cloud_routing_hub")
        create_route(corp_id, "10.1.0.0/16", internal_hub_id, "vpn_gateway")
        create_route(corp_id, "10.2.0.0/16", internal_hub_id, "vpn_gateway")
        create_hub_route(internal_hub_id, "10.1.0.0/16", k8s1_id, "cloud_routing_hub")
        create_hub_route(internal_hub_id, "10.2.0.0/16", k8s2_id, "cloud_routing_hub")
        create_hub_route(internal_hub_id, "10.100.0.0/24", shared_id, "cloud_routing_hub")
        create_hub_route(internal_hub_id, "100.64.0.0/16", k8s1_id, "cloud_routing_hub")
        create_hub_route(internal_hub_id, "100.65.0.0/16", k8s2_id, "cloud_routing_hub")
        create_hub_route(nat_hub_id, "0.0.0.0/0", shared_id, "nat_gateway")
        for vpc_id, cidr in [(k8s1_id, "10.1.0.0/16"), (k8s2_id, "10.2.0.0/16"), (k8s1_id, "100.64.0.0/16"), (k8s2_id, "100.65.0.0/16")]:
            create_hub_route(nat_hub_id, cidr, vpc_id, "cloud_routing_hub")
