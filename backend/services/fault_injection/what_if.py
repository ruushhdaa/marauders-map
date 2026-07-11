"""
PS13 - What-If Simulation Engine Placeholder
"""
from typing import Dict, Any
import structlog
import copy
from services.digital_twin.twin import get_twin

logger = structlog.get_logger(__name__)

class WhatIfSimulationEngine:
    """
    Manages interactive 'What-If' simulations on the topology map.
    """
    def __init__(self):
        pass

    async def create_simulation(self, target_node: str, fault_type: str) -> Dict[str, Any]:
        """
        Creates a new What-If simulation state for the topology.
        """
        logger.info("Creating what-if simulation", target_node=target_node, fault_type=fault_type)
        
        # We need a separate Twin instance or a copy of the topology.
        # But we can just use the real twin's get_topology and override values manually.
        twin = get_twin()
        if target_node not in twin.graph.nodes:
            return {"status": "error", "message": f"Node {target_node} not found"}
            
        topo = twin.get_topology()
        what_if_topo = topo.model_dump()
        
        # Find node and apply theoretical risk
        for node in what_if_topo["nodes"]:
            if node["id"] == target_node:
                node["metadata"]["risk_score"] = 99.0
                node["metadata"]["status"] = "CRITICAL"
                node["metadata"]["metrics"]["cpu_util"] = 100.0
                node["metadata"]["metrics"]["error_rate"] = 0.95
                
            # Simulate a blast radius impact on neighbors
            elif target_node in [l["source"] for l in what_if_topo["links"] if l["target"] == node["id"]] or \
                 target_node in [l["target"] for l in what_if_topo["links"] if l["source"] == node["id"]]:
                 node["metadata"]["risk_score"] = min(node["metadata"].get("risk_score", 0) + 40, 100)
                 if node["metadata"]["risk_score"] > 70:
                     node["metadata"]["status"] = "DEGRADED"

        return {
            "simulation_id": f"sim_whatif_{target_node}_{fault_type}",
            "target_node": target_node,
            "fault_type": fault_type,
            "simulation_active": True,
            "differentiating_factor": "SIMULATION_MODE_ENABLED",
            "what_if_topology": what_if_topo
        }

def get_what_if_engine() -> WhatIfSimulationEngine:
    return WhatIfSimulationEngine()
