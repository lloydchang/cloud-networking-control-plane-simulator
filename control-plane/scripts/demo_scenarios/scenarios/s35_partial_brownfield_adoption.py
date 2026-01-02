# control-plane/scripts/demo_scenarios/scenarios/s35_partial_brownfield_adoption.py

"""
Scenario 35: Partial Brownfield Adoption

This scenario validates control plane behavior and VPC View UI semantics when only a subset of
pre-existing workloads can be safely adopted into a new VPC.

Preconditions:
- Endpoints exist on the fabric as containers.
- Some endpoints fall within the declared VPC CIDR.
- Conflicts exist that prevent unambiguous ownership.

Behavior Under Test:
- Discovery of existing endpoints prior to VPC creation.
- Selective adoption of endpoints that meet ownership criteria.
- Rejection of endpoints that violate isolation or routing rules.
- Continued reconciliation without rollback of successfully adopted endpoints.
- VPC View accurately displays adopted endpoints and clearly shows excluded/conflicting endpoints.

Success Criteria:
- Eligible endpoints appear in the VPC View within the new VPC and correct subnet.
- Conflicting endpoints remain outside the VPC boundary in the UI.
- Control plane reconciliation completes without global failure.
- Logical boundaries and isolation guarantees are correctly represented in the VPC View.

Failure Semantics:
- The scenario fails only if no eligible endpoints exist.
- Rejected endpoints are expected and do not constitute failure.
- Partial convergence with correct VPC View mapping is the intended outcome.

This scenario models real-world brownfield environments where legacy constraints, overlapping
address space, or topology limitations prevent full ownership transfer into a single VPC while
ensuring the UI accurately represents logical network state.
"""

from ..common import *

def run_s35_partial_brownfield_adoption():
    s35_name = "35. Partial Brownfield Adoption"
    create_scenario(
        title=s35_name,
        description="Adopt a subset of existing workloads while rejecting conflicting endpoints, with VPC View reflecting accurate endpoint placement.",
        resource_order=[{"type": "vpc", "label": "Partial Brownfield VPC"}]
    )

    # Check that brownfield endpoints exist within the intended CIDR
    assert_brownfield_endpoints_exist("10.2.0.0/16", s35_name)

    # Create the VPC for partial adoption
    vpc_id = create_vpc("Partial Brownfield VPC", "10.2.0.0/16", scenario=s35_name)
    if vpc_id:
        # Add both adoptable and conflicting subnets
        create_subnet(vpc_id, "Adoptable Subnet", "10.2.1.0/24", cdc="CDC-1")  # server-3: 10.1.3.10
        create_subnet(vpc_id, "Conflicting Subnet", "10.2.2.0/24", cdc="CDC-2")  # server-4: 10.2.1.10

        # Attach a default route via Internet Gateway
        create_route(vpc_id, "0.0.0.0/0", "igw-auto", "internet_gateway")

        # Evaluate endpoints for adoption or conflict
        endpoints = list_brownfield_endpoints("10.2.0.0/16")

        for ep in endpoints:
            if is_endpoint_conflicting(ep, vpc_id):
                log_scenario(s35_name, f"[CONFLICT] Endpoint {ep['name']} ({ep['ip']}) cannot be adopted into Partial Brownfield VPC")
            else:
                attach_endpoint_to_vpc(ep['name'], vpc_id, select_subnet_for_endpoint(ep, vpc_id))
                log_scenario(s35_name, f"[ADOPTED] Endpoint {ep['name']} ({ep['ip']}) added to Partial Brownfield VPC")

        # Trigger reconciliation to ensure VPC View reflects adopted and conflicting endpoints
        reconcile_scenario(s35_name)
