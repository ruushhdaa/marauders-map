/**
 * VIKRAM — intrusion / fault scenario catalog.
 * Trigger nodes + issue types mirror the backend fault injector so the
 * client simulation behaves like the real thing.
 */
export interface ScenarioDef {
  id: string;
  title: string;
  subtitle: string;
  icon: string;
  color: string;
  trigger_node: string;
  issue_type: string;
  description: string;
}

export const SCENARIO_CATALOG: ScenarioDef[] = [
  {
    id: "HUB_CONGESTION",
    title: "Hub Congestion",
    subtitle: "Progressive bandwidth saturation",
    icon: "📈",
    color: "#dd8a4a",
    trigger_node: "HUB-RTR-01",
    issue_type: "CONGESTION",
    description:
      "Bulk backup jobs consume HUB-RTR-01 WAN bandwidth without QoS, triggering cascading latency across all spoke sites.",
  },
  {
    id: "BGP_ROUTE_FLAP",
    title: "BGP Route Flap",
    subtitle: "Transit peer session instability",
    icon: "🔄",
    color: "#e26370",
    trigger_node: "BGP-PEER-01",
    issue_type: "BGP_FLAP",
    description:
      "ISP transit BGP session experiencing keepalive violations, causing route table churn and internet loss.",
  },
  {
    id: "TUNNEL_DEGRADATION",
    title: "Tunnel Degradation",
    subtitle: "IPSec tunnel quality degrading",
    icon: "🔗",
    color: "#d8b062",
    trigger_node: "SPOKE-RTR-A",
    issue_type: "TUNNEL_DEGRADATION",
    description:
      "WAN packet corruption causing IPSec SA renegotiation loops on SPOKE-RTR-A, degrading VoIP and ERP.",
  },
  {
    id: "MPLS_FAILURE",
    title: "MPLS Failure",
    subtitle: "Label-switched path collapse",
    icon: "💀",
    color: "#e26370",
    trigger_node: "MPLS-PE-01",
    issue_type: "MPLS_FAILURE",
    description:
      "MPLS-PE-01 FIB table exhaustion causing LDP session flap, collapsing label-switched paths network-wide.",
  },
  {
    id: "POLICY_DRIFT",
    title: "Policy Drift",
    subtitle: "SD-WAN QoS configuration drift",
    icon: "⚙️",
    color: "#9b8cff",
    trigger_node: "SDWAN-CTRL",
    issue_type: "POLICY_DRIFT",
    description:
      "SD-WAN controller firmware upgrade reset QoS templates, demoting VoIP to best-effort class across all tunnels.",
  },
  {
    id: "SOFTWARE_BUG",
    title: "Software Bug",
    subtitle: "Application crashes unexpectedly",
    icon: "🐛",
    color: "#ffaa00",
    trigger_node: "APP-SRV-01",
    issue_type: "SOFTWARE_BUG",
    description: "An unhandled exception in the core application service is causing 100% CPU utilization and dropping requests.",
  },
  {
    id: "API_FAILURE",
    title: "API Failure",
    subtitle: "Gateway timeout and latency",
    icon: "🔌",
    color: "#ff4444",
    trigger_node: "API-GW-01",
    issue_type: "API_FAILURE",
    description: "The API gateway is experiencing 5000ms latency and 90% error rate due to a bad deployment.",
  },
];

export function scenarioById(id: string): ScenarioDef | undefined {
  return SCENARIO_CATALOG.find((s) => s.id === id);
}

/** Risk the trigger node reaches at each severity step (0..4). */
export const STEP_RISK = [12, 42, 64, 83, 97];
