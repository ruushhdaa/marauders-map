from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime

class IssueType(str, Enum):
    CONGESTION = "CONGESTION"
    LATENCY_DRIFT = "LATENCY_DRIFT"
    TUNNEL_DEGRADATION = "TUNNEL_DEGRADATION"
    MPLS_FAILURE = "MPLS_FAILURE"
    BGP_FLAP = "BGP_FLAP"
    POLICY_DRIFT = "POLICY_DRIFT"
    ROUTE_INSTABILITY = "ROUTE_INSTABILITY"
    LINK_DOWN = "LINK_DOWN"
    SOFTWARE_BUG = "SOFTWARE_BUG"
    API_FAILURE = "API_FAILURE"

class ActionType(str, Enum):
    CLEAR_BGP_SESSION = "CLEAR_BGP_SESSION"
    RESTART_TUNNEL = "RESTART_TUNNEL"
    APPLY_RATE_LIMIT = "APPLY_RATE_LIMIT"
    RESET_MPLS_PATH = "RESET_MPLS_PATH"
    INCREASE_QOS_PRIORITY = "INCREASE_QOS_PRIORITY"
    FAILOVER_TO_BACKUP = "FAILOVER_TO_BACKUP"
    REROUTE_TRAFFIC = "REROUTE_TRAFFIC"
    CHANGE_ROUTING_PREFERENCE = "CHANGE_ROUTING_PREFERENCE"

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
    SOFTWARE_BUG = "SOFTWARE_BUG"
    API_FAILURE = "API_FAILURE"

class CopilotQuery(BaseModel):
    query: str
    node_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

class CopilotResponse(BaseModel):
    response: str
    actions: List[str] = []

class Prediction(BaseModel):
    prediction_id: str
    node_id: str
    issue_type: str
    confidence_score: float
    risk_score: float
    time_to_impact_minutes: float
    affected_scope: List[str] = []
    explanation: str = ""
    timestamp: Any

class BlastRadiusResult(BaseModel):
    node_id: str
    issue_type: str
    affected_nodes: List[str]
    max_impact_score: float
    description: str

class SimulationAction(BaseModel):
    node_id: str
    action_type: str
    issue_type: str
    description: Optional[str] = None

class NodeType(str, Enum):
    ROUTER = "ROUTER"
    SWITCH = "SWITCH"
    FIREWALL = "FIREWALL"
    SERVER = "SERVER"
    GATEWAY = "GATEWAY"
    PE = "PE"
    SDWAN_CTRL = "SDWAN_CTRL"
    SERVICE = "SERVICE"

class LinkType(str, Enum):
    MPLS = "MPLS"
    FIBER = "FIBER"
    IPSEC = "IPSEC"
    COPPER = "COPPER"
    BGP = "BGP"
    SDWAN = "SDWAN"
    PHYSICAL = "PHYSICAL"

class TopologyNode(BaseModel):
    node_id: str
    label: str
    node_type: NodeType
    site: Optional[str] = None
    ip_address: Optional[str] = None
    vendor: Optional[str] = None
    position_x: float
    position_y: float
    risk_score: float = 0.0
    risk_level: RiskLevel = RiskLevel.HEALTHY
    metrics: Dict[str, Any] = {}
    services: List[str] = []
    is_critical: bool = False

class TopologyLink(BaseModel):
    link_id: str
    source: str
    target: str
    link_type: LinkType
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

class RiskScore(BaseModel):
    node_id: str
    risk_score: float
    severity_score: float
    escalation_level: Any
    urgency_level: str
    risk_factors: Dict[str, float]
    trend: str
    calculated_at: datetime

class RankedAction(BaseModel):
    rank: int
    action_type: str
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
    issue_type: str
    ranked_actions: List[RankedAction]
    generated_at: datetime = Field(default_factory=datetime.utcnow)

class SystemRiskSummary(BaseModel):
    overall_risk: float
    highest_risk_node: str
    active_predictions: int
    critical_nodes: List[str]
    risk_scores: List[RiskScore]
    calculated_at: datetime = Field(default_factory=datetime.utcnow)

class SimulationAction(BaseModel):
    action_type: ActionType
    target_node: str

class SimulationOutcome(BaseModel):
    action: SimulationAction
    projected_risk: float
    risk_reduction_pct: float
    estimated_recovery_minutes: float
    side_effects: List[str]
    confidence: float
    description: str

class SimulationResult(BaseModel):
    trigger_node: str
    failure_type: str
    current_risk: float
    do_nothing_outcome: SimulationOutcome
    action_outcomes: List[SimulationOutcome]
    recommended_action: SimulationAction
    future_state_projection: Dict[str, Any]
    simulated_at: datetime = Field(default_factory=datetime.utcnow)

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
