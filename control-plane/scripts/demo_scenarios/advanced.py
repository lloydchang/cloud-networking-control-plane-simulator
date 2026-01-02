# control-plane/scripts/demo_scenarios/advanced.py

from .scenarios import (
    s18_virtual_appliance,
    s19_hub_gateway_transit,
    s20_data_scale_network,
    s21_subnet_level_peering,
    s22_shared_cluster,
    s23_cloud_native_service_hub,
    s24_hybrid_appliance_bridge,
    s25_ai_infrastructure,
    s26_global_hubs_gre,
    s27_dual_stack,
    s28_cloud_native_nat,
    s29_heterogeneous_lb,
    s30_standard_ipsec_vpn,
    s31_remote_access_vpn,
    s32_private_dns,
    s33_legacy_windows,
    s34_brownfield_adoption,
    s35_partial_brownfield_adoption,
    s36_brownfield_churn_reconciliation
)

def run_advanced_scenarios():
    print("\n=== Running Advanced Scenarios (18-36) ===")
    s18_virtual_appliance.run_s18_virtual_appliance()
    s19_hub_gateway_transit.run_s19_hub_gateway_transit()
    s20_data_scale_network.run_s20_data_scale_network()
    s21_subnet_level_peering.run_s21_subnet_level_peering()
    s22_shared_cluster.run_s22_shared_cluster()
    s23_cloud_native_service_hub.run_s23_cloud_native_service_hub()
    s24_hybrid_appliance_bridge.run_s24_hybrid_appliance_bridge()
    s25_ai_infrastructure.run_s25_ai_infrastructure()
    s26_global_hubs_gre.run_s26_global_hubs_gre()
    s27_dual_stack.run_s27_dual_stack()
    s28_cloud_native_nat.run_s28_cloud_native_nat()
    s29_heterogeneous_lb.run_s29_heterogeneous_lb()
    s30_standard_ipsec_vpn.run_s30_standard_ipsec_vpn()
    s31_remote_access_vpn.run_s31_remote_access_vpn()
    s32_private_dns.run_s32_private_dns()
    s33_legacy_windows.run_s33_legacy_windows()
    s34_brownfield_adoption.run_s34_brownfield_adoption()
    s35_partial_brownfield_adoption.run_s35_partial_brownfield_adoption()
    s36_brownfield_churn_reconciliation.run_s36_brownfield_churn_reconciliation()
