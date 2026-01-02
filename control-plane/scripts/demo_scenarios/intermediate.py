from .scenarios import (
    s11_collaborative_shared,
    s12_k8s_hybrid,
    s13_app_service_mesh,
    s14_network_lifecycle,
    s15_policy_enforcement,
    s16_hybrid_connectivity,
    s17_enterprise_hub_spoke
)

def run_intermediate_scenarios():
    print("\n=== Running Intermediate Scenarios (11-17) ===")
    s11_collaborative_shared.run_s11_collaborative_shared()
    s12_k8s_hybrid.run_s12_k8s_hybrid()
    s13_app_service_mesh.run_s13_app_service_mesh()
    s14_network_lifecycle.run_s14_network_lifecycle()
    s15_policy_enforcement.run_s15_policy_enforcement()
    s16_hybrid_connectivity.run_s16_hybrid_connectivity()
    s17_enterprise_hub_spoke.run_s17_enterprise_hub_spoke()
