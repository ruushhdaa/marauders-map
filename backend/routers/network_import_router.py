"""
PS13 — Network Import Router
Endpoints for importing fake network topologies.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File
from typing import Dict, Any, List
import json

from services.network_import.importer import get_importer

router = APIRouter(prefix="/api/networks", tags=["Network Import"])


@router.get("/sample")
async def get_sample_topology() -> Dict:
    """
    Returns a sample topology JSON you can edit
    and re-import for testing.
    """
    importer = get_importer()
    return importer.get_sample_topology()


@router.post("/import")
async def import_network(topology: Dict[str, Any]) -> Dict:
    """
    Import a custom network topology JSON.

    Required format:
    {
        "network_name": "my-test-network",
        "nodes": [
            {"id": "HUB-01", "type": "hub", ...}
        ],
        "edges": [
            {"source": "SPOKE-A", "target": "HUB-01", ...}
        ]
    }
    """
    importer = get_importer()
    result = importer.import_from_json(topology)

    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result["error"]
        )
    return result


@router.post("/import/file")
async def import_network_from_file(
    file: UploadFile = File(...)
) -> Dict:
    """
    Upload a .json topology file directly.
    """
    if not file.filename.endswith(".json"):
        raise HTTPException(
            status_code=400,
            detail="Only .json files are accepted"
        )

    try:
        contents = await file.read()
        topology = json.loads(contents)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid JSON file: {str(e)}"
        )

    importer = get_importer()
    result = importer.import_from_json(topology)

    if not result["success"]:
        raise HTTPException(
            status_code=400,
            detail=result["error"]
        )
    return result


@router.get("/list")
async def list_imported_networks() -> Dict:
    """
    List all previously imported networks.
    """
    importer = get_importer()
    networks = importer.list_imported_networks()
    return {
        "imported_networks": networks,
        "count": len(networks)
    }


@router.get("/current")
async def get_current_network() -> Dict:
    """
    Get the currently active imported topology.
    """
    importer = get_importer()
    topology = importer.get_current_topology()

    if topology is None:
        return {
            "active": False,
            "message": "No custom network imported yet",
            "hint": "POST to /api/networks/import to load one"
        }

    return {
        "active": True,
        "topology": topology
    }


@router.get("/load/{network_name}")
async def load_network(network_name: str) -> Dict:
    """
    Load a previously imported network by name.
    """
    importer = get_importer()
    topology = importer.load_network(network_name)

    if topology is None:
        raise HTTPException(
            status_code=404,
            detail=f"Network '{network_name}' not found"
        )

    # Set as current
    importer._current_topology = topology
    return {
        "success": True,
        "loaded": network_name,
        "topology": topology
    }


@router.delete("/current")
async def clear_current_network() -> Dict:
    """
    Clear the currently active imported topology.
    Reverts to default network.
    """
    importer = get_importer()
    importer._current_topology = None
    return {
        "success": True,
        "message": "Custom topology cleared. Default network active."
    }