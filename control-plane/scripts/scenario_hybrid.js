/**
 * Scenario: Kubernetes Hybrid Network
 * Uses automatic hub centering from main vpc.html.
 */
function renderScenarioHybrid(scenario, scenarioResources, vpcs, hubs, standaloneDCs, data, formatVpcHtml, formatHubHtml, formatStandaloneDCHtml, formatConnectionsHtml, displayCounter, vpcCount, hubCount, dcCount) {
    const resourceIds = scenarioResources.map(r => r.id);

    // Use standard layout - automatic hub centering will position CRHs in the middle
    const scenarioBody = `
        <div class="scenario-content">
            ${scenarioResources.map(r => {
        if (r.type === 'vpc') return formatVpcHtml(r);
        if (r.type === 'hub') return formatHubHtml(r);
        if (r.type === 'standalone_dc') return formatStandaloneDCHtml(r);
        return '';
    }).join('')}
        </div>
    `;

    return `
        <div class="scenario-group">
            <div class="scenario-title">${scenario.title} <span style="font-size: 11px; color: #666; font-weight: normal;">(${vpcCount} VPC${vpcCount !== 1 ? 's' : ''}${hubCount > 0 ? `, ${hubCount} CRH${hubCount !== 1 ? 's' : ''}` : ''}${dcCount > 0 ? `, ${dcCount} ODC${dcCount !== 1 ? 's' : ''}` : ''})</span></div>
            <div class="scenario-desc">${scenario.description}</div>
            <div class="scenario-connections">
                ${formatConnectionsHtml(resourceIds)}
            </div>
            ${scenarioBody}
        </div>
    `;
}
