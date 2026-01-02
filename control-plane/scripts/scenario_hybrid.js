/**
 * Scenario: Kubernetes Hybrid Network
 * High-fidelity 3-column grid layout with propagation arrows.
 */
function renderScenarioHybrid(scenario, scenarioResources, vpcs, hubs, standaloneDCs, data, formatVpcHtml, formatHubHtml, formatStandaloneDCHtml, formatConnectionsHtml) {
    const resourceIds = scenarioResources.map(r => r.id);

    // 2x3 Grid Layout:
    // Row 1: K8s Cluster 1 | NAT Hub | Shared Services
    // Row 2: K8s Cluster 2 | Non-NAT Hub | On-Premise DC

    const k8s1 = scenarioResources.find(r => r.label.includes('Cluster 1'));
    const k8s2 = scenarioResources.find(r => r.label.includes('Cluster 2'));
    const natHub = scenarioResources.find(r => r.type === 'hub' && r.label.includes('NAT Flows'));
    const nonNatHub = scenarioResources.find(r => r.type === 'hub' && r.label.includes('Non-NAT Flows'));
    const sharedServices = scenarioResources.find(r => r.label.includes('Shared Services'));
    const onPremDC = scenarioResources.find(r => r.label.includes('On-Premise Data Center'));

    const scenarioBody = `
        <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 40px; width: 100%;">
            ${k8s1 ? formatVpcHtml(k8s1) : ''}
            ${natHub ? formatHubHtml(natHub) : ''}
            ${sharedServices ? formatVpcHtml(sharedServices) : ''}
            ${k8s2 ? formatVpcHtml(k8s2) : ''}
            ${nonNatHub ? formatHubHtml(nonNatHub) : ''}
            ${onPremDC ? formatStandaloneDCHtml(onPremDC) : ''}
        </div>
    `;

    return `
        <div class="scenario-group">
            <div class="scenario-title">${scenario.title}</div>
            <div class="scenario-desc">${scenario.description}</div>
            <div class="scenario-connections">
                ${formatConnectionsHtml(resourceIds)}
            </div>
            ${scenarioBody}
        </div>
    `;
}
