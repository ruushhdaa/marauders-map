import { usePS13Store, scoreToLevel, getRiskColor } from "@/store";
import { SCENARIO_CATALOG, scenarioById } from "@/lib/scenarios";

export async function generateAndPrintReport() {
  const state = usePS13Store.getState();
  const nodes = state.nodes ?? [];
  const links = state.links ?? [];
  const copilotMessages = state.copilotMessages ?? [];
  const appliedRemediations = state.appliedRemediations ?? [];
  const activeScenarios = state.activeScenarios ?? [];
  const predictions = state.predictions ?? [];
  const alerts = state.alerts ?? [];
  const blastRadius = state.blastRadius;
  const nodeRiskScores = state.nodeRiskScores ?? {};
  const systemRisk = state.systemRisk ?? 0;
  const highestRiskNode = state.highestRiskNode ?? "";
  const criticalNodes = state.criticalNodes ?? [];

  const generatedAt = new Date().toLocaleString();
  const riskLevel = scoreToLevel(systemRisk);

  // ── Derived analytics ────────────────────────────────────────────────────
  const totalNodes = nodes.length;
  const totalLinks = links.length;
  const linksDown = links.filter((l: any) => l.status === "DOWN").length;
  const linksDegraded = links.filter((l: any) => l.status === "DEGRADED").length;
  const linksUp = totalLinks - linksDown - linksDegraded;
  const criticalNodeList = nodes.filter((n: any) => n.is_critical);
  const highRiskNodes = nodes.filter((n: any) => n.risk_score >= 70);
  const mediumRiskNodes = nodes.filter((n: any) => n.risk_score >= 40 && n.risk_score < 70);
  const healthyNodes = nodes.filter((n: any) => n.risk_score < 20);

  const avgCpu = totalNodes > 0 ? nodes.reduce((s: number, n: any) => s + (n.metrics?.cpu_utilization ?? 0), 0) / totalNodes : 0;
  const avgMem = totalNodes > 0 ? nodes.reduce((s: number, n: any) => s + (n.metrics?.memory_utilization ?? 0), 0) / totalNodes : 0;
  const avgBw = totalNodes > 0 ? nodes.reduce((s: number, n: any) => s + (n.metrics?.bandwidth_utilization ?? 0), 0) / totalNodes : 0;
  const avgPktLoss = totalNodes > 0 ? nodes.reduce((s: number, n: any) => s + (n.metrics?.packet_loss ?? 0), 0) / totalNodes : 0;
  const avgLatency = totalNodes > 0 ? nodes.reduce((s: number, n: any) => s + (n.metrics?.latency_ms ?? 0), 0) / totalNodes : 0;
  const avgJitter = totalNodes > 0 ? nodes.reduce((s: number, n: any) => s + (n.metrics?.jitter_ms ?? 0), 0) / totalNodes : 0;
  const avgErrorRate = totalNodes > 0 ? nodes.reduce((s: number, n: any) => s + (n.metrics?.error_rate ?? 0), 0) / totalNodes : 0;

  const maxLatencyNode = nodes.reduce((best: any, n: any) => (!best || (n.metrics?.latency_ms ?? 0) > (best.metrics?.latency_ms ?? 0)) ? n : best, null as any);
  const maxPktLossNode = nodes.reduce((best: any, n: any) => (!best || (n.metrics?.packet_loss ?? 0) > (best.metrics?.packet_loss ?? 0)) ? n : best, null as any);
  const maxCpuNode = nodes.reduce((best: any, n: any) => (!best || (n.metrics?.cpu_utilization ?? 0) > (best.metrics?.cpu_utilization ?? 0)) ? n : best, null as any);

  // MPLS vs non-MPLS links
  const mplsLinks = links.filter((l: any) => l.is_mpls);
  const nonMplsLinks = links.filter((l: any) => !l.is_mpls);
  const tunnelLinks = links.filter((l: any) => l.tunnel_id);

  // Unique sites
  const sites = [...new Set(nodes.map((n: any) => n.site).filter(Boolean))];

  // Unacknowledged alerts
  const unackedAlerts = alerts.filter((a: any) => !a.acknowledged);

  // ── Vulnerability Assessment ─────────────────────────────────────────────
  function buildVulnerabilities(): string[] {
    const vulns: string[] = [];
    nodes.forEach((n: any) => {
      const m = n.metrics;
      if (!m) return;
      if (m.cpu_utilization > 85) vulns.push("CRITICAL: " + n.node_id + " (" + n.label + ") — CPU at " + m.cpu_utilization.toFixed(1) + "% (threshold: 85%). Risk of process starvation, routing daemon crashes, and packet drops.");
      else if (m.cpu_utilization > 70) vulns.push("HIGH: " + n.node_id + " — CPU at " + m.cpu_utilization.toFixed(1) + "%. Approaching saturation. Schedule capacity review.");
      if (m.bandwidth_utilization > 85) vulns.push("CRITICAL: " + n.node_id + " — Bandwidth at " + m.bandwidth_utilization.toFixed(1) + "% utilization. QoS policies may fail to guarantee SLAs.");
      else if (m.bandwidth_utilization > 70) vulns.push("HIGH: " + n.node_id + " — Bandwidth at " + m.bandwidth_utilization.toFixed(1) + "%. Approaching congestion threshold.");
      if (m.packet_loss > 2) vulns.push("CRITICAL: " + n.node_id + " — Packet loss at " + m.packet_loss.toFixed(3) + "%. Voice and real-time applications severely impacted.");
      else if (m.packet_loss > 0.5) vulns.push("HIGH: " + n.node_id + " — Packet loss at " + m.packet_loss.toFixed(3) + "%. VoIP MOS score degrading.");
      if (m.latency_ms > 100) vulns.push("CRITICAL: " + n.node_id + " — Latency at " + m.latency_ms.toFixed(1) + " ms. Exceeds SLA threshold (100ms). Potential timeout failures.");
      else if (m.latency_ms > 50) vulns.push("HIGH: " + n.node_id + " — Latency at " + m.latency_ms.toFixed(1) + " ms. Approaching SLA limits.");
      if (m.jitter_ms > 15) vulns.push("HIGH: " + n.node_id + " — Jitter at " + m.jitter_ms.toFixed(1) + " ms. VoIP and video conferencing quality degraded.");
      if (m.error_rate > 2) vulns.push("HIGH: " + n.node_id + " — Interface error rate at " + m.error_rate.toFixed(2) + "%. Check for CRC errors, duplex mismatch.");
      if (m.qos_drop_rate > 10) vulns.push("HIGH: " + n.node_id + " — QoS drop rate at " + m.qos_drop_rate.toFixed(1) + "%. Priority queues overflowing.");
    });
    links.forEach((l: any) => {
      if (l.status === "DOWN") vulns.push("CRITICAL: Link " + l.source + " → " + l.target + " is DOWN. Traffic rerouting required.");
      if (l.status === "DEGRADED") vulns.push("HIGH: Link " + l.source + " → " + l.target + " is DEGRADED. Monitor for further deterioration.");
      if (l.utilization > 85) vulns.push("HIGH: Link " + l.source + " → " + l.target + " utilization at " + l.utilization.toFixed(1) + "%. Congestion imminent.");
    });
    if (vulns.length === 0) vulns.push("No critical vulnerabilities detected. All metrics within operational thresholds.");
    return vulns;
  }

  // ── Root Cause Analysis ──────────────────────────────────────────────────
  function buildRootCause(): string {
    if (activeScenarios.length === 0 && highRiskNodes.length === 0) {
      return "<p>No active faults detected. The network is operating within normal parameters. All nodes report healthy metrics and no intrusion scenarios are currently running.</p>";
    }
    let html = "";
    activeScenarios.forEach((sc: any) => {
      const def = scenarioById(sc.type);
      const elapsedMin = ((Date.now() - sc.started_at) / 60000).toFixed(1);
      html += '<div class="rca-block">';
      html += "<strong>Scenario: " + (def ? def.title : sc.type.replace(/_/g, " ")) + "</strong>";
      html += "<br>Trigger Node: <code>" + sc.trigger_node + "</code>";
      html += "<br>Issue Type: <code>" + sc.issue_type + "</code>";
      html += "<br>Current Severity: <span class=\"sev-" + sc.severity.toLowerCase() + "\">" + sc.severity + " (Step " + sc.step + "/4)</span>";
      html += "<br>Duration Active: " + elapsedMin + " minutes";
      if (def) {
        html += "<br><em>Root Cause: " + def.description + "</em>";
      }
      html += "</div>";
    });
    if (highRiskNodes.length > 0 && activeScenarios.length === 0) {
      html += "<p>High-risk conditions detected on " + highRiskNodes.length + " node(s) without an active scenario. Investigate external factors such as traffic surges, DDoS, or hardware degradation.</p>";
    }
    return html;
  }

  // ── Suggestions ──────────────────────────────────────────────────────────
  function buildSuggestions(): string[] {
    const suggestions: string[] = [];
    activeScenarios.forEach((sc: any) => {
      const def = scenarioById(sc.type);
      if (sc.type === "HUB_CONGESTION") {
        suggestions.push("IMMEDIATE: Implement QoS shaping on HUB-RTR-01 WAN interface. Rate-limit bulk backup traffic to 30% of available bandwidth.");
        suggestions.push("SHORT-TERM: Enable WRED (Weighted Random Early Detection) on HUB-RTR-01 to proactively drop low-priority packets before queue saturation.");
        suggestions.push("LONG-TERM: Schedule backup jobs during off-peak hours (02:00–05:00 UTC) using cron-based traffic engineering.");
      } else if (sc.type === "BGP_ROUTE_FLAP") {
        suggestions.push("IMMEDIATE: Apply route dampening on BGP-PEER-01 (half-life 15 min, suppress 2000, reuse 750, max-suppress 60 min).");
        suggestions.push("SHORT-TERM: Contact ISP NOC to investigate keepalive violations on the transit peering session.");
        suggestions.push("LONG-TERM: Establish secondary BGP transit peer for redundancy. Implement BFD for sub-second failure detection.");
      } else if (sc.type === "TUNNEL_DEGRADATION") {
        suggestions.push("IMMEDIATE: Force IPSec SA renegotiation on SPOKE-RTR-A. Clear crypto session and re-establish with fresh keys.");
        suggestions.push("SHORT-TERM: Run WAN circuit diagnostics (BER test) to identify physical layer corruption causing renegotiation loops.");
        suggestions.push("LONG-TERM: Upgrade to AES-256-GCM with hardware acceleration to reduce crypto overhead during renegotiation.");
      } else if (sc.type === "MPLS_FAILURE") {
        suggestions.push("IMMEDIATE: Restart LDP process on MPLS-PE-01. Flush stale FIB entries to free label space.");
        suggestions.push("SHORT-TERM: Audit MPLS label allocation policy. Current label count may exceed FIB capacity. Consider label compression.");
        suggestions.push("LONG-TERM: Upgrade PE router line cards to support 128K+ label entries. Implement Segment Routing to reduce LDP dependency.");
      } else if (sc.type === "POLICY_DRIFT") {
        suggestions.push("IMMEDIATE: Rollback SD-WAN controller to previous firmware configuration snapshot. Restore QoS templates from backup.");
        suggestions.push("SHORT-TERM: Enable configuration change auditing on SDWAN-CTRL. Set up pre/post-upgrade diff checks.");
        suggestions.push("LONG-TERM: Implement Infrastructure-as-Code (IaC) for SD-WAN policy management. Version control all QoS templates.");
      } else {
        suggestions.push("Investigate " + sc.type.replace(/_/g, " ") + " on " + sc.trigger_node + ". Run detailed diagnostics.");
      }
    });
    // General suggestions based on metrics
    if (avgCpu > 60) suggestions.push("CAPACITY: Network-wide average CPU is " + avgCpu.toFixed(1) + "%. Consider horizontal scaling or load distribution.");
    if (avgPktLoss > 0.3) suggestions.push("QUALITY: Average packet loss across the network is " + avgPktLoss.toFixed(3) + "%. Audit optical transceivers and cable plant.");
    if (linksDown > 0) suggestions.push("REDUNDANCY: " + linksDown + " link(s) are currently DOWN. Verify failover paths are operational and traffic is re-converged.");
    if (unackedAlerts.length > 5) suggestions.push("OPERATIONS: " + unackedAlerts.length + " unacknowledged alerts. Assign on-call engineer to triage and acknowledge.");
    if (criticalNodes.length > 2) suggestions.push("ARCHITECTURE: " + criticalNodes.length + " critical nodes in degraded state simultaneously. Review network redundancy design.");
    if (suggestions.length === 0) suggestions.push("No immediate action required. Continue monitoring baseline metrics for anomaly detection.");
    return suggestions;
  }

  // ── Build all sections ─────────────────────────────────────────────────
  const vulns = buildVulnerabilities();
  const rcaHtml = buildRootCause();
  const suggestions = buildSuggestions();

  // ── Topology Nodes Table ────────────────────────────────────────────────
  const topoRows = nodes
    .sort((a: any, b: any) => (b.risk_score ?? 0) - (a.risk_score ?? 0))
    .map((n: any) => {
      const m = n.metrics || {};
      const riskColor = n.risk_score >= 80 ? "#e26370" : n.risk_score >= 60 ? "#dd8a4a" : n.risk_score >= 40 ? "#d8b062" : n.risk_score >= 20 ? "#7fb0d6" : "#57b6a6";
      return "<tr>" +
        "<td><strong>" + n.node_id + "</strong></td>" +
        "<td>" + (n.label || n.node_id) + "</td>" +
        "<td><code>" + n.node_type + "</code></td>" +
        "<td>" + (n.site || "—") + "</td>" +
        "<td>" + (n.ip_address || "—") + "</td>" +
        "<td>" + (n.is_critical ? '<span class="badge-crit">CRITICAL</span>' : "Standard") + "</td>" +
        '<td style="color:' + riskColor + ';font-weight:700;">' + (n.risk_score ?? 0).toFixed(1) + "</td>" +
        "<td>" + (m.cpu_utilization ?? 0).toFixed(1) + "%</td>" +
        "<td>" + (m.memory_utilization ?? 0).toFixed(1) + "%</td>" +
        "<td>" + (m.bandwidth_utilization ?? 0).toFixed(1) + "%</td>" +
        "<td>" + (m.latency_ms ?? 0).toFixed(1) + " ms</td>" +
        "<td>" + (m.packet_loss ?? 0).toFixed(3) + "%</td>" +
        "<td>" + (m.jitter_ms ?? 0).toFixed(1) + " ms</td>" +
        "<td>" + (m.error_rate ?? 0).toFixed(2) + "%</td>" +
        "<td>" + (n.services || []).join(", ") + "</td>" +
        "</tr>";
    }).join("");

  // ── Links Table ─────────────────────────────────────────────────────────
  const linkRows = links
    .sort((a: any, b: any) => {
      const order: any = { DOWN: 0, DEGRADED: 1, UP: 2 };
      return (order[a.status] ?? 2) - (order[b.status] ?? 2);
    })
    .map((l: any) => {
      const statusColor = l.status === "DOWN" ? "#e26370" : l.status === "DEGRADED" ? "#dd8a4a" : "#57b6a6";
      return "<tr>" +
        "<td>" + l.link_id + "</td>" +
        "<td>" + l.source + "</td>" +
        "<td>" + l.target + "</td>" +
        "<td><code>" + l.link_type + "</code></td>" +
        '<td style="color:' + statusColor + ';font-weight:700;">' + l.status + "</td>" +
        "<td>" + (l.bandwidth_mbps ?? "—") + " Mbps</td>" +
        "<td>" + (l.utilization ?? 0).toFixed(1) + "%</td>" +
        "<td>" + (l.latency_ms ?? 0).toFixed(1) + " ms</td>" +
        "<td>" + (l.packet_loss ?? 0).toFixed(3) + "%</td>" +
        "<td>" + (l.is_mpls ? "Yes" : "No") + "</td>" +
        "<td>" + (l.tunnel_id || "—") + "</td>" +
        "</tr>";
    }).join("");

  // ── Predictions Table ───────────────────────────────────────────────────
  let predictionsSection: string;
  if (predictions.length === 0) {
    predictionsSection = "<p>No predictive analytics generated. The system has not detected any escalating trends warranting forward-looking projections.</p>";
  } else {
    const predRows = predictions.map((p: any) => {
      const confColor = p.confidence_score > 0.8 ? "#e26370" : p.confidence_score > 0.6 ? "#dd8a4a" : "#d8b062";
      return "<tr>" +
        "<td><strong>" + p.node_id + "</strong></td>" +
        "<td>" + p.issue_type.replace(/_/g, " ") + "</td>" +
        '<td style="color:' + confColor + ';font-weight:700;">' + (p.confidence_score * 100).toFixed(1) + "%</td>" +
        "<td>" + p.risk_score.toFixed(1) + "</td>" +
        "<td>" + p.time_to_impact_minutes + " min</td>" +
        "<td>" + (p.affected_scope || []).join(", ") + "</td>" +
        "<td><em>" + p.explanation + "</em></td>" +
        "</tr>";
    }).join("");
    predictionsSection =
      "<table><thead><tr><th>Node</th><th>Issue Type</th><th>Confidence</th><th>Risk</th><th>Time to Impact</th><th>Affected Scope</th><th>Explanation</th></tr></thead><tbody>" +
      predRows + "</tbody></table>";
  }

  // ── Alerts Table ────────────────────────────────────────────────────────
  let alertsSection: string;
  if (alerts.length === 0) {
    alertsSection = "<p>No alerts generated during this monitoring session.</p>";
  } else {
    const alertRows = alerts.slice(0, 30).map((a: any) => {
      const urgColor = a.urgency === "CRITICAL" ? "#e26370" : a.urgency === "HIGH" ? "#dd8a4a" : "#d8b062";
      return "<tr>" +
        "<td>" + new Date(a.timestamp).toLocaleTimeString() + "</td>" +
        "<td>" + a.node_id + "</td>" +
        '<td style="color:' + urgColor + ';font-weight:700;">' + a.urgency + "</td>" +
        "<td>" + a.risk_score.toFixed(1) + "</td>" +
        "<td>" + a.message + "</td>" +
        "<td>" + (a.acknowledged ? "✓ Acknowledged" : '<span style="color:#e26370;">⚠ Pending</span>') + "</td>" +
        "</tr>";
    }).join("");
    alertsSection =
      "<p>Total alerts: <strong>" + alerts.length + "</strong> | Unacknowledged: <strong style='color:#e26370;'>" + unackedAlerts.length + "</strong></p>" +
      "<table><thead><tr><th>Time</th><th>Node</th><th>Urgency</th><th>Risk</th><th>Message</th><th>Status</th></tr></thead><tbody>" +
      alertRows + "</tbody></table>";
  }

  // ── Blast Radius ────────────────────────────────────────────────────────
  let blastSection: string;
  if (!blastRadius) {
    blastSection = "<p>No blast radius analysis has been computed for this session. Trigger a fault simulation to generate impact analysis.</p>";
  } else {
    blastSection = '<div class="blast-card">' +
      "<p><strong>Trigger Node:</strong> " + blastRadius.trigger_node + "</p>" +
      "<p><strong>Failure Type:</strong> " + blastRadius.failure_type + "</p>" +
      "<p><strong>Impact Score:</strong> <span style='color:#e26370;font-weight:700;'>" + blastRadius.impact_score.toFixed(1) + "/100</span></p>" +
      "<p><strong>Propagation Depth:</strong> " + blastRadius.propagation_depth + " hops</p>" +
      "<p><strong>Estimated Users Impacted:</strong> " + blastRadius.estimated_users_impacted.toLocaleString() + "</p>" +
      "<p><strong>Affected Nodes:</strong> " + blastRadius.affected_nodes.join(", ") + "</p>" +
      "<p><strong>Affected Sites:</strong> " + blastRadius.affected_sites.join(", ") + "</p>" +
      "<p><strong>Affected Services:</strong> " + blastRadius.affected_services.join(", ") + "</p>" +
      "</div>";
  }

  // ── Applied Remediations ────────────────────────────────────────────────
  let appliedSection: string;
  if (appliedRemediations.length === 0) {
    appliedSection = "<p>No remediation actions have been executed during this session. All recommended actions remain pending operator review.</p>";
  } else {
    const appRows = appliedRemediations.map((r: any, i: number) => {
      return "<tr>" +
        "<td>" + (i + 1) + "</td>" +
        "<td>" + new Date(r.timestamp).toLocaleTimeString() + "</td>" +
        "<td><strong>" + r.node_id + "</strong></td>" +
        "<td>" + r.action_type.replace(/_/g, " ") + "</td>" +
        "</tr>";
    }).join("");
    appliedSection =
      "<table><thead><tr><th>#</th><th>Time</th><th>Target Node</th><th>Action Applied</th></tr></thead><tbody>" +
      appRows + "</tbody></table>";
  }

  // ── Copilot Chat ────────────────────────────────────────────────────────
  let chatSection: string;
  if (copilotMessages.length === 0) {
    chatSection = "<p>No AI Copilot interactions recorded. The copilot can be used to query runbooks, explain anomalies, and receive context-aware remediation guidance.</p>";
  } else {
    chatSection = copilotMessages.map((m: any) => {
      const isUser = m.role === "user";
      const label = isUser ? "👤 Operator" : "🤖 VIKRAM Copilot";
      const cls = isUser ? "chat-user" : "chat-ai";
      const ts = m.timestamp
        ? ' <span style="font-weight:normal;font-size:10px;color:#999;">(' + new Date(m.timestamp).toLocaleTimeString() + ")</span>"
        : "";
      return '<div class="' + cls + '">' + label + ts + "</div>" +
        '<div class="chat-msg">' + escapeHtml(m.content) + "</div>";
    }).join("");
  }

  // ── Risk Score Details ──────────────────────────────────────────────────
  let riskDetailSection: string;
  const riskEntries = Object.values(nodeRiskScores);
  if (riskEntries.length === 0) {
    riskDetailSection = "<p>No individual node risk assessments available. Risk scoring is generated once simulation data is available.</p>";
  } else {
    const riskRows = (riskEntries as any[])
      .sort((a, b) => b.risk_score - a.risk_score)
      .map((rs) => {
        const trendIcon = rs.trend === "INCREASING" ? "📈" : rs.trend === "DECREASING" ? "📉" : "➡️";
        const urgColor = rs.urgency_level === "CRITICAL" ? "#e26370" : rs.urgency_level === "HIGH" ? "#dd8a4a" : rs.urgency_level === "MEDIUM" ? "#d8b062" : "#57b6a6";
        return "<tr>" +
          "<td><strong>" + rs.node_id + "</strong></td>" +
          "<td>" + rs.risk_score.toFixed(1) + "</td>" +
          "<td>" + rs.severity_score.toFixed(1) + "</td>" +
          '<td style="color:' + urgColor + ';font-weight:700;">' + rs.urgency_level + "</td>" +
          "<td>" + rs.escalation_level + "</td>" +
          "<td>" + trendIcon + " " + rs.trend + "</td>" +
          "<td>" + new Date(rs.calculated_at).toLocaleTimeString() + "</td>" +
          "</tr>";
      }).join("");
    riskDetailSection =
      "<table><thead><tr><th>Node</th><th>Risk Score</th><th>Severity</th><th>Urgency</th><th>Escalation Lvl</th><th>Trend</th><th>Calculated At</th></tr></thead><tbody>" +
      riskRows + "</tbody></table>";
  }

  // ── Conclusion ──────────────────────────────────────────────────────────
  function buildConclusion(): string {
    let c = "";
    if (systemRisk < 20) {
      c = "<p>The MPLS/SD-WAN network is currently operating in a <strong style='color:#57b6a6;'>HEALTHY</strong> state. All monitored metrics are within acceptable SLA thresholds. No immediate operator action is required. Continue baseline monitoring and review predictive analytics daily.</p>";
    } else if (systemRisk < 40) {
      c = "<p>The network is in a <strong style='color:#7fb0d6;'>LOW RISK</strong> state. Minor deviations have been detected but remain within operational tolerance. Monitor the identified nodes closely over the next 30 minutes for trend changes.</p>";
    } else if (systemRisk < 60) {
      c = "<p>The network is in a <strong style='color:#d8b062;'>MEDIUM RISK</strong> state. Several metrics are approaching threshold limits. Operator review of the identified vulnerabilities and suggested remediations is <em>recommended within the next 15 minutes</em> to prevent escalation.</p>";
    } else if (systemRisk < 80) {
      c = "<p>The network is in a <strong style='color:#dd8a4a;'>HIGH RISK</strong> state. Active fault conditions are degrading service quality. <em>Immediate operator intervention is required.</em> Implement the recommended remediations in priority order to prevent SLA breaches and potential cascading failures.</p>";
    } else {
      c = "<p>⚠️ The network is in a <strong style='color:#e26370;'>CRITICAL</strong> state. Active service disruptions are occurring. <em>Emergency response protocol should be activated immediately.</em> Escalate to Tier-3 engineering and implement all recommended remediations without delay. Post-incident review required once stabilized.</p>";
    }
    if (activeScenarios.length > 0) {
      c += "<p><strong>Active Threat Count:</strong> " + activeScenarios.length + " concurrent intrusion scenario(s) detected. Each requires independent remediation tracking.</p>";
    }
    if (appliedRemediations.length > 0) {
      c += "<p><strong>Remediation Progress:</strong> " + appliedRemediations.length + " action(s) have been executed during this session. Verify post-action metrics convergence before closing the incident.</p>";
    }
    if (predictions.length > 0) {
      const urgent = predictions.filter((p: any) => p.time_to_impact_minutes <= 10);
      if (urgent.length > 0) {
        c += "<p style='color:#e26370;'><strong>⏰ Urgent:</strong> " + urgent.length + " prediction(s) indicate impact within 10 minutes. Prioritize action on these nodes.</p>";
      }
    }
    return c;
  }

  // ── SLA Timeout Analysis ────────────────────────────────────────────────
  function buildTimeoutAnalysis(): string {
    let html = "";
    const slaBreachNodes = nodes.filter((n: any) => n.metrics && n.metrics.latency_ms > 100);
    const nearBreachNodes = nodes.filter((n: any) => n.metrics && n.metrics.latency_ms > 50 && n.metrics.latency_ms <= 100);
    if (slaBreachNodes.length === 0 && nearBreachNodes.length === 0) {
      return "<p>All nodes are within SLA latency thresholds (&lt;100ms). No timeout risks detected.</p>";
    }
    if (slaBreachNodes.length > 0) {
      html += '<div class="timeout-alert"><strong>⚠️ SLA BREACH — ' + slaBreachNodes.length + " node(s) exceeding 100ms latency threshold:</strong><ul>";
      slaBreachNodes.forEach((n: any) => {
        html += "<li><strong>" + n.node_id + "</strong> — " + n.metrics.latency_ms.toFixed(1) + " ms (exceeded by " + (n.metrics.latency_ms - 100).toFixed(1) + " ms). ";
        html += "Affected services: " + (n.services || []).join(", ") + ". ";
        html += "Risk of application timeouts, TCP retransmissions, and user-facing errors.</li>";
      });
      html += "</ul></div>";
    }
    if (nearBreachNodes.length > 0) {
      html += "<p><strong>Warning:</strong> " + nearBreachNodes.length + " node(s) approaching SLA limits (50–100ms): ";
      html += nearBreachNodes.map((n: any) => n.node_id + " (" + n.metrics.latency_ms.toFixed(1) + "ms)").join(", ");
      html += ". Monitor closely.</p>";
    }
    return html;
  }

  // ── Assemble full HTML ────────────────────────────────────────────────
  const scenarioLine = activeScenarios.length > 0
    ? activeScenarios.map((sc: any) => {
        const def = scenarioById(sc.type);
        return '<span class="scenario-tag">' + (def ? def.icon + " " : "") + (def ? def.title : sc.type.replace(/_/g, " ")) + " — " + sc.severity + "</span>";
      }).join(" ")
    : '<span style="color:#57b6a6;">None active (Baseline operations)</span>';

  const html = [
    "<!DOCTYPE html>",
    '<html lang="en"><head><meta charset="UTF-8">',
    "<title>VIKRAM — MPLS Network State Analysis Report</title>",
    "<style>",
    "  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&family=JetBrains+Mono:wght@400;600&display=swap');",
    "  * { box-sizing: border-box; margin: 0; padding: 0; }",
    "  body { font-family: 'Inter', sans-serif; color: #1a1a2e; padding: 40px 50px; background: #fff; line-height: 1.6; font-size: 12px; }",
    "  .cover { text-align: center; margin-bottom: 36px; padding-bottom: 24px; border-bottom: 3px solid #0a0a23; }",
    "  .cover h1 { font-size: 36px; letter-spacing: 8px; font-weight: 900; color: #0a0a23; margin-bottom: 4px; }",
    "  .cover h2 { font-size: 14px; font-weight: 400; color: #4a4a6a; text-transform: uppercase; letter-spacing: 3px; margin-bottom: 6px; }",
    "  .cover .subtitle { font-size: 11px; color: #888; font-family: 'JetBrains Mono', monospace; }",
    "  .cover .classification { display: inline-block; padding: 3px 14px; margin-top: 10px; font-size: 10px; font-weight: 700; letter-spacing: 2px; border: 1px solid #e26370; color: #e26370; border-radius: 3px; }",

    "  .summary-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 20px 0 30px; }",
    "  .stat-card { background: #f8f8fc; border: 1px solid #e0e0ea; border-radius: 8px; padding: 14px; text-align: center; }",
    "  .stat-card .val { font-size: 28px; font-weight: 900; color: #0a0a23; }",
    "  .stat-card .lbl { font-size: 9px; text-transform: uppercase; letter-spacing: 1.5px; color: #888; margin-top: 3px; font-weight: 600; }",

    "  h3 { font-size: 13px; color: #0a0a23; border-left: 4px solid #0a0a23; padding: 6px 0 6px 12px; margin-top: 30px; margin-bottom: 10px; letter-spacing: 1.5px; text-transform: uppercase; background: #f8f8fc; }",
    "  h4 { font-size: 12px; color: #2a2a4a; margin-top: 16px; margin-bottom: 6px; }",

    "  table { width: 100%; border-collapse: collapse; margin: 8px 0 20px; font-size: 10px; }",
    "  th, td { border: 1px solid #e0e0ea; padding: 6px 8px; text-align: left; }",
    "  th { background: #f0f0f8; font-weight: 700; font-size: 9px; text-transform: uppercase; letter-spacing: 0.5px; color: #555; }",
    "  tr:nth-child(even) td { background: #fafafa; }",
    "  code { font-family: 'JetBrains Mono', monospace; background: #f0f0f8; padding: 1px 5px; border-radius: 3px; font-size: 10px; }",

    "  .badge-crit { background: #fde8ea; color: #c0392b; padding: 2px 6px; border-radius: 3px; font-size: 9px; font-weight: 700; }",
    "  .scenario-tag { display: inline-block; background: #fff3e0; color: #e65100; padding: 3px 10px; border-radius: 4px; font-size: 10px; font-weight: 600; margin-right: 8px; }",
    "  .sev-critical { color: #e26370; font-weight: 700; }",
    "  .sev-high { color: #dd8a4a; font-weight: 700; }",
    "  .sev-medium { color: #d8b062; font-weight: 700; }",
    "  .sev-low { color: #7fb0d6; font-weight: 700; }",
    "  .sev-healthy { color: #57b6a6; font-weight: 700; }",

    "  .vuln-list { list-style: none; padding: 0; }",
    "  .vuln-list li { padding: 6px 10px; margin: 4px 0; border-radius: 4px; font-size: 11px; }",
    "  .vuln-list li.v-crit { background: #fde8ea; border-left: 4px solid #e26370; }",
    "  .vuln-list li.v-high { background: #fff3e0; border-left: 4px solid #dd8a4a; }",
    "  .vuln-list li.v-normal { background: #f0f8f4; border-left: 4px solid #57b6a6; }",

    "  .suggest-list { list-style: none; padding: 0; counter-reset: suggest; }",
    "  .suggest-list li { padding: 8px 10px 8px 36px; margin: 4px 0; background: #f0f4ff; border-radius: 4px; font-size: 11px; position: relative; border-left: 4px solid #3f51b5; }",
    "  .suggest-list li::before { counter-increment: suggest; content: counter(suggest); position: absolute; left: 10px; font-weight: 700; color: #3f51b5; }",

    "  .rca-block { background: #f8f4ff; border: 1px solid #d1c4e9; border-radius: 8px; padding: 14px; margin: 8px 0; }",
    "  .blast-card { background: #fde8ea; border: 1px solid #ef9a9a; border-radius: 8px; padding: 14px; margin: 8px 0; }",
    "  .timeout-alert { background: #fff3e0; border: 1px solid #ffcc02; border-radius: 8px; padding: 14px; margin: 8px 0; }",

    "  .chat-user { font-weight: 700; color: #1a5fb4; margin-top: 14px; font-size: 12px; }",
    "  .chat-ai { font-weight: 700; color: #9141ac; margin-top: 14px; font-size: 12px; }",
    "  .chat-msg { background: #f5f5fa; padding: 10px 14px; border-left: 3px solid #bbb; margin: 4px 0 12px; font-family: 'JetBrains Mono', monospace; white-space: pre-wrap; font-size: 10px; line-height: 1.6; }",

    "  .conclusion { background: #f0f8ff; border: 2px solid #3f51b5; border-radius: 8px; padding: 20px; margin-top: 24px; }",
    "  .footer { margin-top: 40px; text-align: center; font-size: 9px; color: #aaa; border-top: 1px solid #eee; padding-top: 12px; }",
    "  .footer .conf { font-weight: 700; color: #e26370; letter-spacing: 2px; }",
    "  .toc { background: #f8f8fc; border: 1px solid #e0e0ea; border-radius: 8px; padding: 16px 24px; margin-bottom: 24px; }",
    "  .toc-title { font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px; }",
    "  .toc ol { padding-left: 20px; font-size: 11px; line-height: 2; }",
    "  p { margin: 4px 0 8px; }",
    "  @media print { body { padding: 20px 30px; font-size: 10px; } .summary-grid { grid-template-columns: repeat(4, 1fr); } h3 { break-after: avoid; } table { break-inside: auto; } tr { break-inside: avoid; } }",
    "</style></head><body>",

    // ── Cover ────────────────────────────────────────────────────────────
    '<div class="cover">',
    "  <h1>VIKRAM</h1>",
    "  <h2>MPLS / SD-WAN Network State Analysis Report</h2>",
    '  <div class="subtitle">Report ID: RPT-' + Date.now().toString(36).toUpperCase() + " | Generated: " + generatedAt + "</div>",
    '  <div class="classification">CONFIDENTIAL — INTERNAL USE ONLY</div>',
    "</div>",

    // ── Table of Contents ────────────────────────────────────────────────
    '<div class="toc">',
    '  <div class="toc-title">Table of Contents</div>',
    "  <ol>",
    "    <li>Executive Summary</li>",
    "    <li>Network Topology — Nodes</li>",
    "    <li>Network Topology — Links &amp; Tunnels</li>",
    "    <li>Root Cause Analysis</li>",
    "    <li>Vulnerability Assessment</li>",
    "    <li>SLA &amp; Timeout Analysis</li>",
    "    <li>Active High-Risk Faults</li>",
    "    <li>Predictive Analytics &amp; Time-to-Impact</li>",
    "    <li>Risk Scoring — Per-Node Breakdown</li>",
    "    <li>Alerts &amp; Event Log</li>",
    "    <li>Blast Radius Impact Analysis</li>",
    "    <li>Remediations Applied</li>",
    "    <li>Recommendations &amp; Suggested Actions</li>",
    "    <li>AI Copilot Interaction Log</li>",
    "    <li>Conclusion &amp; Next Steps</li>",
    "  </ol>",
    "</div>",

    // ── 1. Executive Summary ─────────────────────────────────────────────
    "<h3>1. Executive Summary</h3>",
    '<div class="summary-grid">',
    '  <div class="stat-card"><div class="val">' + totalNodes + '</div><div class="lbl">Total Nodes</div></div>',
    '  <div class="stat-card"><div class="val">' + totalLinks + '</div><div class="lbl">Total Links</div></div>',
    '  <div class="stat-card"><div class="val" style="color:' + (systemRisk >= 60 ? "#e26370" : systemRisk >= 40 ? "#dd8a4a" : "#57b6a6") + ';">' + systemRisk.toFixed(1) + '</div><div class="lbl">System Risk Score</div></div>',
    '  <div class="stat-card"><div class="val" style="color:' + (highRiskNodes.length > 0 ? "#e26370" : "#57b6a6") + ';">' + highRiskNodes.length + '</div><div class="lbl">High-Risk Nodes</div></div>',
    '  <div class="stat-card"><div class="val">' + linksUp + '</div><div class="lbl">Links UP</div></div>',
    '  <div class="stat-card"><div class="val" style="color:#e26370;">' + linksDown + '</div><div class="lbl">Links DOWN</div></div>',
    '  <div class="stat-card"><div class="val">' + appliedRemediations.length + '</div><div class="lbl">Actions Applied</div></div>',
    '  <div class="stat-card"><div class="val">' + alerts.length + '</div><div class="lbl">Total Alerts</div></div>',
    "</div>",
    '<p><strong>System Risk Level:</strong> <span class="sev-' + riskLevel.toLowerCase() + '">' + riskLevel + "</span></p>",
    highestRiskNode ? "<p><strong>Highest Risk Node:</strong> <code>" + highestRiskNode + "</code></p>" : "",
    "<p><strong>Active Scenarios:</strong> " + scenarioLine + "</p>",
    "<p><strong>Sites Covered:</strong> " + sites.join(", ") + " (" + sites.length + " sites)</p>",
    "<p><strong>Critical Infrastructure:</strong> " + criticalNodeList.length + " critical nodes | " + mplsLinks.length + " MPLS links | " + tunnelLinks.length + " IPSec tunnels</p>",
    "<h4>Network Health Summary</h4>",
    "<table><thead><tr><th>Metric</th><th>Network Average</th><th>Worst Node</th><th>Worst Value</th><th>Threshold</th><th>Status</th></tr></thead><tbody>",
    "<tr><td>CPU Utilization</td><td>" + avgCpu.toFixed(1) + "%</td><td>" + (maxCpuNode?.node_id ?? "—") + "</td><td>" + (maxCpuNode?.metrics?.cpu_utilization ?? 0).toFixed(1) + "%</td><td>85%</td><td>" + ((maxCpuNode?.metrics?.cpu_utilization ?? 0) > 85 ? '<span style="color:#e26370;">BREACH</span>' : '<span style="color:#57b6a6;">OK</span>') + "</td></tr>",
    "<tr><td>Latency</td><td>" + avgLatency.toFixed(1) + " ms</td><td>" + (maxLatencyNode?.node_id ?? "—") + "</td><td>" + (maxLatencyNode?.metrics?.latency_ms ?? 0).toFixed(1) + " ms</td><td>100 ms</td><td>" + ((maxLatencyNode?.metrics?.latency_ms ?? 0) > 100 ? '<span style="color:#e26370;">BREACH</span>' : '<span style="color:#57b6a6;">OK</span>') + "</td></tr>",
    "<tr><td>Packet Loss</td><td>" + avgPktLoss.toFixed(3) + "%</td><td>" + (maxPktLossNode?.node_id ?? "—") + "</td><td>" + (maxPktLossNode?.metrics?.packet_loss ?? 0).toFixed(3) + "%</td><td>1.0%</td><td>" + ((maxPktLossNode?.metrics?.packet_loss ?? 0) > 1 ? '<span style="color:#e26370;">BREACH</span>' : '<span style="color:#57b6a6;">OK</span>') + "</td></tr>",
    "<tr><td>Jitter</td><td>" + avgJitter.toFixed(1) + " ms</td><td>—</td><td>—</td><td>30 ms</td><td>" + (avgJitter > 30 ? '<span style="color:#e26370;">BREACH</span>' : '<span style="color:#57b6a6;">OK</span>') + "</td></tr>",
    "<tr><td>Error Rate</td><td>" + avgErrorRate.toFixed(2) + "%</td><td>—</td><td>—</td><td>2.0%</td><td>" + (avgErrorRate > 2 ? '<span style="color:#dd8a4a;">WARNING</span>' : '<span style="color:#57b6a6;">OK</span>') + "</td></tr>",
    "</tbody></table>",

    // ── 2. Nodes ─────────────────────────────────────────────────────────
    "<h3>2. Network Topology — Nodes (" + totalNodes + ")</h3>",
    "<p>Complete inventory of all monitored nodes sorted by risk score (highest first). Metrics reflect real-time state at report generation time.</p>",
    "<table><thead><tr><th>Node ID</th><th>Label</th><th>Type</th><th>Site</th><th>IP</th><th>Criticality</th><th>Risk</th><th>CPU</th><th>Mem</th><th>BW</th><th>Latency</th><th>Pkt Loss</th><th>Jitter</th><th>Errors</th><th>Services</th></tr></thead><tbody>",
    topoRows,
    "</tbody></table>",

    // ── 3. Links ─────────────────────────────────────────────────────────
    "<h3>3. Network Topology — Links &amp; Tunnels (" + totalLinks + ")</h3>",
    "<p>All inter-node connections including MPLS LSPs, IPSec tunnels, BGP sessions, and physical links. Sorted by status (DOWN first).</p>",
    "<table><thead><tr><th>Link</th><th>Source</th><th>Target</th><th>Type</th><th>Status</th><th>Bandwidth</th><th>Utilization</th><th>Latency</th><th>Pkt Loss</th><th>MPLS</th><th>Tunnel ID</th></tr></thead><tbody>",
    linkRows,
    "</tbody></table>",

    // ── 4. Root Cause ────────────────────────────────────────────────────
    "<h3>4. Root Cause Analysis</h3>",
    "<p>Analysis of active fault conditions, their origin, and underlying technical causes.</p>",
    rcaHtml,

    // ── 5. Vulnerabilities ───────────────────────────────────────────────
    "<h3>5. Vulnerability Assessment</h3>",
    "<p>Automatically generated assessment of all metric threshold violations and potential failure points across the network.</p>",
    '<ul class="vuln-list">',
    vulns.map((v) => {
      const cls = v.startsWith("CRITICAL") ? "v-crit" : v.startsWith("HIGH") ? "v-high" : "v-normal";
      return '<li class="' + cls + '">' + v + "</li>";
    }).join(""),
    "</ul>",

    // ── 6. SLA & Timeout ─────────────────────────────────────────────────
    "<h3>6. SLA &amp; Timeout Analysis</h3>",
    "<p>Evaluation of latency-sensitive SLA thresholds. Nodes exceeding 100ms are flagged as breach; nodes between 50–100ms are warnings.</p>",
    buildTimeoutAnalysis(),

    // ── 7. High-Risk Faults ──────────────────────────────────────────────
    "<h3>7. Active High-Risk Faults (" + highRiskNodes.length + ")</h3>",
    highRiskNodes.length === 0
      ? "<p>No nodes currently in high-risk state (risk ≥ 70). All assets are within acceptable operational parameters.</p>"
      : "<p>" + highRiskNodes.length + " node(s) have risk scores ≥ 70, indicating active fault conditions requiring intervention.</p>" +
        "<table><thead><tr><th>Node</th><th>Label</th><th>Risk</th><th>CPU %</th><th>Latency</th><th>Packet Loss</th><th>Jitter</th><th>QoS Drops</th></tr></thead><tbody>" +
        highRiskNodes.map((n: any) => {
          const m = n.metrics || {};
          return "<tr><td><strong>" + n.node_id + "</strong></td><td>" + n.label + "</td><td style='color:#e26370;font-weight:700;'>" + (n.risk_score ?? 0).toFixed(1) + "</td><td>" + (m.cpu_utilization ?? 0).toFixed(1) + "%</td><td>" + (m.latency_ms ?? 0).toFixed(1) + " ms</td><td>" + (m.packet_loss ?? 0).toFixed(3) + "%</td><td>" + (m.jitter_ms ?? 0).toFixed(1) + " ms</td><td>" + (m.qos_drop_rate ?? 0).toFixed(1) + "%</td></tr>";
        }).join("") + "</tbody></table>",

    // ── 8. Predictions ───────────────────────────────────────────────────
    "<h3>8. Predictive Analytics &amp; Time-to-Impact</h3>",
    "<p>AI-generated forward-looking predictions showing the estimated time before fault conditions reach critical thresholds.</p>",
    predictionsSection,

    // ── 9. Risk Scoring ──────────────────────────────────────────────────
    "<h3>9. Risk Scoring — Per-Node Breakdown</h3>",
    "<p>Detailed risk assessment per node including severity scoring, escalation levels, and trend direction (increasing/stable/decreasing).</p>",
    riskDetailSection,

    // ── 10. Alerts ───────────────────────────────────────────────────────
    "<h3>10. Alerts &amp; Event Log</h3>",
    "<p>Chronological log of all alerts generated during this monitoring session, including acknowledgment status.</p>",
    alertsSection,

    // ── 11. Blast Radius ─────────────────────────────────────────────────
    "<h3>11. Blast Radius Impact Analysis</h3>",
    "<p>Failure propagation analysis showing the cascading impact of node failures on downstream services, sites, and users.</p>",
    blastSection,

    // ── 12. Remediations ─────────────────────────────────────────────────
    "<h3>12. Remediations Applied This Session</h3>",
    "<p>Step-by-step log of all remediation actions executed by operators during this session.</p>",
    appliedSection,

    // ── 13. Suggestions ──────────────────────────────────────────────────
    "<h3>13. Recommendations &amp; Suggested Actions</h3>",
    "<p>Context-aware recommendations generated from active scenarios, vulnerability assessment, and network health analysis. Prioritized by urgency.</p>",
    '<ol class="suggest-list">',
    suggestions.map((s) => "<li>" + s + "</li>").join(""),
    "</ol>",

    // ── 14. Copilot Chat ─────────────────────────────────────────────────
    "<h3>14. AI Copilot Interaction Log</h3>",
    "<p>Complete transcript of operator queries and VIKRAM Copilot responses during this session.</p>",
    chatSection,

    // ── 15. Conclusion ───────────────────────────────────────────────────
    "<h3>15. Conclusion &amp; Next Steps</h3>",
    '<div class="conclusion">',
    buildConclusion(),
    "</div>",

    // ── Footer ───────────────────────────────────────────────────────────
    '<div class="footer">',
    '  <div class="conf">CONFIDENTIAL</div>',
    "  <div>VIKRAM MPLS/SD-WAN Predictive Copilot — Air-Gapped Network Intelligence Platform</div>",
    "  <div>Report generated automatically. Verify all findings against live telemetry before executing critical actions.</div>",
    "  <div>© " + new Date().getFullYear() + " VIKRAM Systems. All rights reserved.</div>",
    "</div>",
    "<script>window.onload=function(){setTimeout(function(){window.print();},800);}</script>",
    "</body></html>",
  ].join("\n");

  // Open in new tab and trigger print dialog
  const printWindow = window.open("", "_blank");
  if (printWindow) {
    printWindow.document.open();
    printWindow.document.write(html);
    printWindow.document.close();
  } else {
    alert("Please allow popups to generate the report.");
  }
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
