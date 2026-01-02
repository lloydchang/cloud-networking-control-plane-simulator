# control-plane/scripts/demo_scenarios/scenarios/s36_brownfield_churn_reconciliation.py

"""
Scenario 36: Brownfield Adoption Under Control Plane Churn

This scenario validates the adoption of existing endpoints into a new VPC
while ensuring the VPC View UI accurately reflects the logical boundaries
and membership. All endpoints must appear within the declared VPC and
subnets in the VPC View, even during control plane interruptions.

Preconditions:
- Endpoints are already running as containers on the fabric.
- They fall within the declared VPC CIDR.
- Control plane experiences at least one reconciliation interruption.

Behavior Under Test:
- Idempotent discovery of endpoints during repeated reconciliation cycles.
- Correct mapping of adopted endpoints into subnets as displayed in the VPC View.
- Preservation of previously adopted endpoint ownership in the UI.
- No duplicate attachments or route injections in the VPC View.
- Eventual convergence of the logical overlay without manual intervention.

Success Criteria:
- All eligible endpoints are represented exactly once in the VPC View.
- No endpoints appear outside their declared VPC or subnet.
- Routing and logical membership converge to the declared intent.
- Control plane restarts do not produce inconsistencies in the VPC View.

Failure Semantics:
- Temporary visual inconsistency during control plane restart is acceptable.
- Permanent duplication, loss of ownership, or route leakage is considered failure.
- Non-eligible endpoints must remain excluded from the VPC View.

This scenario ensures the VPC View UI accurately reflects logical boundaries
and resource membership during brownfield adoption under control plane churn.
"""

from ..common import *
import time

def run_s36_brownfield_churn_reconciliation():
    s36_name = "36. Brownfield Adoption Under Churn"
    create_scenario(
        title=s36_name,
        description="Adopt existing workloads into a new VPC while maintaining accurate VPC View display during control plane churn.",
        resource_order=[{"type": "vpc", "label": "Churn Resilient Brownfield VPC"}]
    )

    # Check that brownfield endpoints exist within the intended CIDR
    assert_brownfield_endpoints_exist("10.2.0.0/16", s36_name)

    # Create the VPC
    vpc_id = create_vpc("Churn Resilient Brownfield VPC", "10.2.0.0/16", scenario=s36_name)
    if vpc_id:
        # Add subnets mapping to two servers
        create_subnet(vpc_id, "Adopted Subnet A", "10.2.2.0/24", cdc="CDC-1")  # server-5
        create_subnet(vpc_id, "Adopted Subnet B", "10.2.3.0/24", cdc="CDC-1")  # server-6

        # Simulate control plane restart
        simulate_control_plane_restart(s36_name)

        # Attach default route via Internet Gateway
        create_route(vpc_id, "0.0.0.0/0", "igw-auto", "internet_gateway")

        # Reconcile scenario to converge logical state
        reconcile_scenario(s36_name)
