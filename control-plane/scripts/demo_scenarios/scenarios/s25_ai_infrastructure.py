from ..common import *

def run_s25_ai_infrastructure():
    s25_name = "25. AI Infrastructure: Accelerated RDMA Network"
    create_scenario(
        title=s25_name,
        description="Specialized high-performance networking for AI/ML training workloads",
        resource_order=[{"type": "vpc", "label": "AI Training VPC"}]
    )
    ai_vpc_id = create_vpc("AI Training VPC", "10.160.0.0/16", scenario=s25_name)
    if ai_vpc_id:
        create_subnet(ai_vpc_id, "GPU Cluster Subnet (RDMA)", "10.160.1.0/24", cdc="CDC-1")
        create_subnet(ai_vpc_id, "Accelerator Node 1", "10.160.1.10/32", cdc="CDC-1")
        create_subnet(ai_vpc_id, "Accelerator Node 2", "10.160.1.11/32", cdc="CDC-1")
        create_subnet(ai_vpc_id, "Parameter Server", "10.160.1.100/32", cdc="CDC-1")
