"""
PS13 — Fake Network Importer
Allows importing custom network topologies as JSON
for testing backend logic against different networks.
"""
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
import structlog

logger = structlog.get_logger(__name__)

# Sample network topology format
SAMPLE_TOPOLOGY = {
    "network_name": "custom-test-network",
    "nodes": [
        {
            "id": "HUB-RTR-01",
            "type": "hub",
            "role": "hub_router",
            "interfaces": ["Gi0/0", "Gi0/1"],
            "services": ["MPLS", "BGP"]
        },
        {
            "id": "SPOKE-RTR-A",
            "type": "spoke",
            "role": "branch_router",
            "interfaces": ["Gi0/0"],
            "services": ["IPSec"]
        }
    ],
    "edges": [
        {
            "source": "SPOKE-RTR-A",
            "target": "HUB-RTR-01",
            "protocol": "BGP",
            "bandwidth_mbps": 100,
            "tunnel": "IPSec"
        }
    ],
    "fault_scenarios": [
        "HUB_CONGESTION",
        "BGP_ROUTE_FLAP"
    ]
}


class NetworkImporter:
    """
    Imports fake network topologies for testing.
    Connects imported topology to digital twin backend.
    """

    def __init__(self):
        self._current_topology: Optional[Dict] = None
        import os
        if os.path.exists("/app/data"):
            self._import_dir = Path("/app/data/imported_networks")
        else:
            self._import_dir = Path(__file__).resolve().parents[2] / "data" / "imported_networks"
        self._import_dir.mkdir(parents=True, exist_ok=True)

    def import_from_json(self, topology: Dict[str, Any]) -> Dict[str, Any]:
        """
        Import a network topology from a JSON dict.
        Validates structure and connects to digital twin.
        """
        # Validate required fields
        required = ["network_name", "nodes", "edges"]
        missing = [f for f in required if f not in topology]
        if missing:
            return {
                "success": False,
                "error": f"Missing required fields: {missing}",
                "required_format": SAMPLE_TOPOLOGY
            }

        # Validate nodes
        for node in topology["nodes"]:
            if "id" not in node or "type" not in node:
                return {
                    "success": False,
                    "error": "Each node must have 'id' and 'type' fields"
                }

        # Store topology
        self._current_topology = topology

        # Save to file
        save_path = self._import_dir / f"{topology['network_name']}.json"
        with open(save_path, "w") as f:
            json.dump(topology, f, indent=2)

        # Extract node IDs and edges for digital twin
        node_ids = [n["id"] for n in topology["nodes"]]
        edges = [(e["source"], e["target"]) for e in topology["edges"]]

        logger.info(
            "Network imported",
            name=topology["network_name"],
            nodes=len(node_ids),
            edges=len(edges)
        )

        return {
            "success": True,
            "network_name": topology["network_name"],
            "nodes_imported": len(node_ids),
            "edges_imported": len(edges),
            "node_ids": node_ids,
            "save_path": str(save_path),
            "message": f"Network '{topology['network_name']}' imported successfully"
        }

    def import_from_file(self, filepath: str) -> Dict[str, Any]:
        """Import topology from a JSON file path."""
        try:
            with open(filepath, "r") as f:
                topology = json.load(f)
            return self.import_from_json(topology)
        except FileNotFoundError:
            return {"success": False, "error": f"File not found: {filepath}"}
        except json.JSONDecodeError as e:
            return {"success": False, "error": f"Invalid JSON: {str(e)}"}

    def list_imported_networks(self) -> List[str]:
        """List all previously imported networks."""
        return [f.stem for f in self._import_dir.glob("*.json")]

    def load_network(self, network_name: str) -> Optional[Dict]:
        """Load a previously imported network by name."""
        path = self._import_dir / f"{network_name}.json"
        if not path.exists():
            return None
        with open(path, "r") as f:
            return json.load(f)

    def get_sample_topology(self) -> Dict:
        """Return sample topology format for reference."""
        return SAMPLE_TOPOLOGY

    def get_current_topology(self) -> Optional[Dict]:
        """Return currently active imported topology."""
        return self._current_topology


# Singleton
_importer: Optional[NetworkImporter] = None


def get_importer() -> NetworkImporter:
    global _importer
    if _importer is None:
        _importer = NetworkImporter()
    return _importer