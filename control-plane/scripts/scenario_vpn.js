/**
 * Scenario: Managed VPN (WireGuard)
 * Standard flex layout.
 */
function renderScenarioVPN(scenario, scenarioResources, vpcs, hubs, data, formatVpcHtml, formatHubHtml, formatConnectionsHtml) {
    const resourceIds = scenarioResources.map(r => r.id);

    const scenarioBody = `
        <div class="scenario-content">
            ${scenarioResources.map(r => {
        if (r.type === 'vpc') return formatVpcHtml(r);
        if (r.type === 'hub') return formatHubHtml(r);
        return '';
    }).join('')}
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
