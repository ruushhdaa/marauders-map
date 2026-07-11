from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class IssueType(str, Enum):
    CONGESTION = "CONGESTION"
    BGP_FLAP = "BGP_FLAP"
    TUNNEL_DEGRADATION = "TUNNEL_DEGRADATION"
    MPLS_FAILURE = "MPLS_FAILURE"
    POLICY_DRIFT = "POLICY_DRIFT"
    LATENCY_DRIFT = "LATENCY_DRIFT"
    LINK_DOWN = "LINK_DOWN"
    ROUTE_INSTABILITY = "ROUTE_INSTABILITY"
    PACKET_LOSS = "PACKET_LOSS"


class ActionType(str, Enum):
    REROUTE_TRAFFIC = "REROUTE_TRAFFIC"
    RESTART_TUNNEL = "RESTART_TUNNEL"
    CLEAR_BGP_SESSION = "CLEAR_BGP_SESSION"
    APPLY_RATE_LIMIT = "APPLY_RATE_LIMIT"
    FAILOVER_TO_BACKUP = "FAILOVER_TO_BACKUP"
    RESET_MPLS_PATH = "RESET_MPLS_PATH"
    INCREASE_QOS_PRIORITY = "INCREASE_QOS_PRIORITY"
    CHANGE_ROUTING_PREFERENCE = "CHANGE_ROUTING_PREFERENCE"
    DO_NOTHING = "DO_NOTHING"


class NodeStatus(str, Enum):
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    DOWN = "DOWN"


class RiskLevel(str, Enum):
    HEALTHY = "HEALTHY"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ScenarioType(str, Enum):
    HUB_CONGESTION = "HUB_CONGESTION"
    BGP_ROUTE_FLAP = "BGP_ROUTE_FLAP"
    TUNNEL_DEGRADATION = "TUNNEL_DEGRADATION"
    MPLS_FAILURE = "MPLS_FAILURE"
    POLICY_DRIFT = "POLICY_DRIFT"


class NodeType(str, Enum):
    ROUTER = "ROUTER"
    HUB = "HUB"
    SPOKE = "SPOKE"
    PE = "PE"
    P = "P"
    CE = "CE"
    CONTROLLER = "CONTROLLER"
    SERVICE = "SERVICE"
    SDWAN_CTRL = "SDWAN_CTRL"
    BGP_PEER = "BGP_PEER"


class LinkType(str, Enum):
    MPLS = "MPLS"
    IPSEC = "IPSEC"
    BGP = "BGP"
    OSPF = "OSPF"
    SDWAN = "SDWAN"
    PHYSICAL = "PHYSICAL"
    ETHERNET = "ETHERNET"
    FIBER = "FIBER"
    LOGICAL = "LOGICAL"


class TopologyNode(BaseModel):
    node_id: str
    label: str
    node_type: NodeType = NodeType.ROUTER
    site: Optional[str] = None
    ip_address: Optional[str] = None
    vendor: Optional[str] = None
    position_x: float = 0.0
    position_y: float = 0.0
    risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.HEALTHY
    metrics: Dict[str, Any] = {}
    services: List[str] = []
    is_critical: bool = False


class TopologyLink(BaseModel):
    link_id: str
    source: str
    target: str
    link_type: LinkType = LinkType.PHYSICAL
    bandwidth_mbps: Optional[float] = None
    utilization: float = 0.0
    latency_ms: float = 0.0
    packet_loss: float = 0.0
    status: str = "UP"
    is_mpls: bool = False
    tunnel_id: Optional[str] = None


class NetworkTopology(BaseModel):
    nodes: List[TopologyNode]
    links: List[TopologyLink]
    last_updated: datetime


class RiskScore(BaseModel):
    node_id: str
    risk_score: float
    severity_score: float
    escalation_level: int
    urgency_level: RiskLevel
    risk_factors: Dict[str, float] = {}
    trend: str
    calculated_at: datetime = datetime.utcnow()


class SystemRiskSummary(BaseModel):
    overall_risk: float
    highest_risk_node: str
    active_predictions: int
    critical_nodes: List[str] = []
    risk_scores: List[RiskScore] = []
    calculated_at: datetime = datetime.utcnow()


class Prediction(BaseModel):
    prediction_id: str
    node_id: str
    issue_type: IssueType
    confidence_score: float
    risk_score: float
    time_to_impact_minutes: float
    affected_scope: List[str] = []
    model_source: str
    features_used: Dict[str, float] = {}
    timestamp: datetime = datetime.utcnow()
    explanation: str


class BlastRadiusResult(BaseModel):
    trigger_node: str
    affected_nodes: List[str] = []
    affected_services: List[str] = []
    impact_score: float = 0.0


class SimulationAction(BaseModel):
    action_type: ActionType
    target_node: str


class SimulationOutcome(BaseModel):
    action: SimulationAction
    projected_risk: float
    risk_reduction_pct: float
    estimated_recovery_minutes: float
    side_effects: List[str] = []
    confidence: float
    description: str


class SimulationResult(BaseModel):
    trigger_node: str
    failure_type: IssueType
    current_risk: float
    do_nothing_outcome: SimulationOutcome
    action_outcomes: List[SimulationOutcome]
    recommended_action: SimulationAction
    future_state_projection: Dict[str, Any]
    simulated_at: datetime = datetime.utcnow()


class CopilotQuery(BaseModel):
    question: str
    context_node: Optional[str] = None
    include_rag: bool = True


class CopilotResponse(BaseModel):
    answer: str
    referenced_nodes: List[str] = []
    referenced_runbooks: List[str] = []
    confidence: float = 0.0
    model_used: str = "unknown"
    rag_sources: List[Dict[str, Any]] = []
    timestamp: datetime = datetime.utcnow()


class RankedAction(BaseModel):
    rank: int
    action_type: ActionType
    target_node: str
    description: str
    risk_reduction_pct: float
    estimated_recovery_minutes: float
    operational_cost: str
    confidence: float
    runbook_reference: Optional[str] = None
    steps: List[str] = []


class ActionPlan(BaseModel):
    trigger_node: str
    issue_type: IssueType
    ranked_actions: List[RankedAction]
    generated_at: datetime = datetime.utcnow()


class Alert(BaseModel):
    id: str
    node_id: str
    issue_type: IssueType
    severity: str
    message: str
    confidence: float
    created_at: datetime = datetime.utcnow()
    resolved: bool = False


class TelemetryPoint(BaseModel):
    node_id: str
    metric: str
    value: float
    timestamp: datetime = datetime.utcnow()


class ScenarioRequest(BaseModel):
    scenario_id: str
    severity: str = "progressive"


class NetworkImportRequest(BaseModel):
    network_name: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    fault_scenarios: List[str] = []