from fastapi import APIRouter
from datetime import datetime
from services.digital_twin.twin import get_twin
from services.prediction.predictor import get_predictor
from services.action_ranking.ranker import get_ranker
from models.schemas import IssueType

report_router = APIRouter(prefix="/api/report", tags=["Report"])

@report_router.get("")
async def generate_report_data():
    """
    Gather current network state, active faults, and recommendations for the report.
    """
    twin = get_twin()
    topo = twin.get_topology()
    
    # 1. Identify active faults / predictions
    predictor = get_predictor()
    faults = []
    for node_id in twin.graph.nodes:
        metrics = twin.node_metrics.get(node_id, {})
        affected = list(twin.get_downstream_nodes(node_id, depth=3))
        pred = predictor.predict(node_id, metrics, affected)
        if pred and pred.risk_score >= 20.0:
            faults.append(pred.model_dump())
            
    # Sort faults by risk score
    faults.sort(key=lambda x: x["risk_score"], reverse=True)
    
    # 2. Get cost-aware remediation recommendations for high-risk nodes
    remediations = {}
    ranker = get_ranker()
    for f in faults:
        node_id = f["node_id"]
        # Default issue type or try to infer from prediction. We'll use CONGESTION as a fallback.
        plan = ranker.rank(node_id, IssueType.CONGESTION, f["risk_score"])
        remediations[node_id] = plan.model_dump()

    # 3. Compile full report payload
    return {
        "generated_at": datetime.utcnow().isoformat(),
        "topology": {
            "node_count": len(topo.nodes),
            "link_count": len(topo.links),
            "nodes": [n.model_dump() for n in topo.nodes],
            "links": [l.model_dump() for l in topo.links]
        },
        "active_faults": faults,
        "remediations": remediations,
    }
