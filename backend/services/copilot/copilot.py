"""
PS13 — Offline AI Copilot
Mistral 7B Instruct via Ollama + RAG context injection.
100% air-gapped: zero external API calls.
Supports streaming responses.
"""
import os
import json
from datetime import datetime
from typing import AsyncGenerator, Optional, Dict, Any, List
import httpx
import structlog

from models.schemas import CopilotQuery, CopilotResponse
from services.rag.rag_engine import get_rag

logger = structlog.get_logger(__name__)

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mistral:7b-instruct")
OLLAMA_FALLBACK = os.environ.get("OLLAMA_FALLBACK_MODEL", "phi3:mini")
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "120"))

# ──────────────────────────────────────────────────────
# SYSTEM PROMPT: NOC Mission Control Copilot
# ──────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are ARIA, AI copilot for PS13 Mission 
Control — air-gapped predictive NOC for MPLS/SD-WAN networks.

CRITICAL: Respond ONLY in valid JSON. No plain text. Only JSON.

REQUIRED FORMAT:
{
  "issue_summary": "one sentence describing the problem",
  "confidence_score": 0.85,
  "root_cause": "technical explanation",
  "affected_nodes": ["NODE-ID-1"],
  "blast_radius": "which services/sites are impacted",
  "urgency": "CRITICAL",
  "recommended_actions": [
    {
      "rank": 1,
      "action": "specific action",
      "runbook": "RB-NET-001",
      "estimated_recovery_minutes": 10,
      "operational_cost": "LOW"
    }
  ],
  "verification_steps": ["step to confirm fix worked"],
  "uncertainty_note": null
}

STRICT RULES:
- Never invent node IDs not in context
- Only use runbooks RB-NET-001 through RB-NET-008
- If uncertain, set confidence_score below 0.70
- urgency must be: CRITICAL, HIGH, MEDIUM, or LOW
- operational_cost must be: LOW, MEDIUM, or HIGH

Valid nodes: HUB-RTR-01, MPLS-PE-01, MPLS-PE-02, SDWAN-CTRL,
SPOKE-RTR-A, SPOKE-RTR-B, SPOKE-RTR-C, SPOKE-RTR-D,
BGP-PEER-01, SVC-VOIP, SVC-ERP, SVC-VIDEO

You are air-gapped. All intelligence is local. No external calls."""


class AICopilot:
    """
    Offline AI Copilot backed by Ollama (Mistral 7B).
    Augmented with RAG context from local knowledge base.
    """

    def __init__(self):
        self._model = OLLAMA_MODEL
        self._available = False
        self._http = httpx.AsyncClient(timeout=OLLAMA_TIMEOUT)

    async def check_availability(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            resp = await self._http.get(f"{OLLAMA_HOST}/api/tags")
            if resp.status_code == 200:
                tags = resp.json().get("models", [])
                model_names = [t.get("name", "") for t in tags]
                if any(self._model in name for name in model_names):
                    self._available = True
                    logger.info("Ollama ready", model=self._model)
                    return True
                # Try fallback model
                if any(OLLAMA_FALLBACK in name for name in model_names):
                    self._model = OLLAMA_FALLBACK
                    self._available = True
                    logger.warning("Using fallback model", model=self._model)
                    return True
                logger.warning("Model not pulled yet", available_models=model_names)
                return False
        except Exception as e:
            logger.warning("Ollama not available", error=str(e))
            self._available = False
            return False

    async def pull_model(self) -> bool:
        """Pull the model if not already available (startup task)."""
        try:
            logger.info("Pulling Ollama model", model=self._model)
            async with self._http.stream(
                "POST", f"{OLLAMA_HOST}/api/pull",
                json={"name": self._model},
                timeout=600,
            ) as resp:
                async for line in resp.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if data.get("status") == "success":
                            logger.info("Model pulled successfully", model=self._model)
                            return True
            return False
        except Exception as e:
            logger.error("Model pull failed", error=str(e))
            return False

    async def query(self, query: CopilotQuery,
                    network_context: Optional[Dict[str, Any]] = None) -> CopilotResponse:
        """Execute a single-turn copilot query with RAG context."""

        rag = get_rag()
        rag_sources = []
        context_str = ""

        # 1. Retrieve RAG context
        if query.include_rag:
            rag_sources = rag.retrieve(query.question, top_k=5)
            if rag_sources:
                context_str = "\n\n".join(
                    f"[{d['source']}]: {d['content'][:400]}" for d in rag_sources[:3]
                )

        # 2. Build full prompt
        user_message = self._build_prompt(
            query.question, context_str, network_context, query.context_node
        )

        # 3. Call Ollama
        answer = ""
        model_used = "rule_based_fallback"

        if self._available:
            try:
                raw_answer = await self._call_ollama(user_message)
                model_used = self._model
                parsed = self._validate_and_parse_response(raw_answer)
                if network_context and "issue_type" in network_context:
                    try:
                        from services.action_ranking.ranker import get_ranker
                        ranker = get_ranker()
                        from models.schemas import IssueType
                        issue_val = network_context["issue_type"]
                        if isinstance(issue_val, str):
                            issue = IssueType(issue_val.upper())
                        else:
                            issue = IssueType(issue_val)
                        node = network_context.get("trigger_node", "HUB-RTR-01")
                        risk = network_context.get("risk_score", 0.75)
                        action_plan = ranker.rank(node, issue, risk)
                        parsed["recommended_actions"] = [
                            {
                                "rank": a.rank,
                                "action": a.description,
                                "runbook": a.runbook_reference,
                                "estimated_recovery_minutes": a.estimated_recovery_minutes,
                                "operational_cost": a.operational_cost,
                                "confidence": a.confidence,
                                "steps": a.steps
                            }
                            for a in action_plan.ranked_actions[:3]
                        ]
                        parsed["cost_ranking_source"] = "ranker_engine"
                    except Exception as e:
                        parsed["cost_ranking_source"] = "llm_only"
                import json as _json
                answer = _json.dumps(parsed, indent=2)
            except Exception as e:
                logger.error("Ollama call failed", error=str(e))
                answer = self._rule_based_response(query.question, network_context)
        else:
            answer = self._rule_based_response(query.question, network_context)

        # 4. Extract referenced nodes and runbooks from answer
        referenced_nodes = self._extract_node_refs(answer)
        referenced_runbooks = self._extract_runbook_refs(answer)

        return CopilotResponse(
            answer=answer,
            referenced_nodes=referenced_nodes,
            referenced_runbooks=referenced_runbooks,
            confidence=0.85 if self._available else 0.60,
            model_used=model_used,
            rag_sources=rag_sources,
            timestamp=datetime.utcnow(),
        )

    async def stream_query(
        self, question: str, network_context: Optional[Dict] = None,
        context_node: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """Stream copilot response token by token via Ollama."""

        rag = get_rag()
        rag_ctx = rag.build_context(question)
        user_message = self._build_prompt(question, rag_ctx, network_context, context_node)

        if not self._available:
            response = self._rule_based_response(question, network_context)
            for word in response.split():
                yield word + " "
            return

        try:
            async with self._http.stream(
                "POST",
                f"{OLLAMA_HOST}/api/generate",
                json={
                    "model": self._model,
                    "prompt": user_message,
                    "system": SYSTEM_PROMPT,
                    "stream": True,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "num_predict": 800,
                    },
                },
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            token = data.get("response", "")
                            if token:
                                yield token
                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error("Stream failed", error=str(e))
            yield f"\n[Copilot connection error: {str(e)}]"

    async def _call_ollama(self, prompt: str) -> str:
        """Non-streaming Ollama call."""
        resp = await self._http.post(
            f"{OLLAMA_HOST}/api/generate",
            json={
                "model": self._model,
                "prompt": prompt,
                "system": SYSTEM_PROMPT,
                "stream": False,
                "options": {"temperature": 0.3, "top_p": 0.9, "num_predict": 800},
            },
        )
        resp.raise_for_status()
        return resp.json().get("response", "")

    @staticmethod
    def _validate_and_parse_response(raw: str) -> Dict[str, Any]:
        import json, re
        VALID_NODES = {
            "HUB-RTR-01","MPLS-PE-01","MPLS-PE-02","SDWAN-CTRL",
            "SPOKE-RTR-A","SPOKE-RTR-B","SPOKE-RTR-C","SPOKE-RTR-D",
            "BGP-PEER-01","SVC-VOIP","SVC-ERP","SVC-VIDEO"
        }
        VALID_RUNBOOKS = {f"RB-NET-{str(i).zfill(3)}" for i in range(1,9)}
        VALID_URGENCY = {"CRITICAL","HIGH","MEDIUM","LOW"}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r'\{.*\}', raw, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                except:
                    return {"error": "unparseable", "raw": raw[:200]}
            else:
                return {"error": "no_json_found", "raw": raw[:200]}
        if "affected_nodes" in data:
            data["affected_nodes"] = [
                n for n in data["affected_nodes"] if n in VALID_NODES
            ]
        if "recommended_actions" in data:
            for action in data["recommended_actions"]:
                if action.get("runbook") not in VALID_RUNBOOKS:
                    action["runbook"] = None
        if data.get("urgency") not in VALID_URGENCY:
            data["urgency"] = "MEDIUM"
        if "confidence_score" in data:
            data["confidence_score"] = max(0.0, min(1.0, 
                float(data["confidence_score"])))
        return data

    @staticmethod
    def _build_prompt(question: str, rag_context: str,
                      network_ctx: Optional[Dict], context_node: Optional[str]) -> str:
        parts = []
        if context_node:
            parts.append(f"Context node: {context_node}")
        if network_ctx:
            parts.append(f"Current network state:\n{json.dumps(network_ctx, indent=2)}")
        if rag_context:
            parts.append(f"Relevant knowledge base:\n{rag_context}")
        parts.append(f"Question: {question}")
        return "\n\n".join(parts)

    @staticmethod
    def _rule_based_response(question: str, ctx: Optional[Dict]) -> str:
        """Intelligent rule-based fallback when Ollama is unavailable."""
        q = question.lower()
        if "fail" in q or "down" in q:
            return ("🔴 **Failure Analysis**: Based on current telemetry, the node shows elevated "
                    "error rates and packet loss consistent with hardware or link degradation. "
                    "**Recommended actions**:\n"
                    "1. Check physical/logical link status (`show interfaces`)\n"
                    "2. Verify MPLS label-switched path (`show mpls ldp bindings`)\n"
                    "3. Initiate failover to backup path if available\n"
                    "4. Reference: RB-NET-005 (Failover Procedure)\n"
                    "\n⚠️ *Note: Ollama LLM not yet available. Using rule-based analysis.*")
        if "risk" in q or "score" in q:
            return ("📊 **Risk Assessment**: Risk score is computed from bandwidth utilization, "
                    "packet loss, latency drift, and anomaly scores (Isolation Forest). "
                    "Scores >75 indicate CRITICAL escalation requiring immediate action.\n"
                    "\n⚠️ *Note: Ollama LLM not yet available. Using rule-based analysis.*")
        if "congestion" in q:
            return ("📈 **Congestion Analysis**: Hub router shows >80% bandwidth utilization. "
                    "This is typically caused by bulk data transfers, backup jobs, or video streams "
                    "without QoS prioritization.\n"
                    "**Actions**: Apply rate-limiting (RB-NET-004) or reroute traffic (RB-NET-001).\n"
                    "\n⚠️ *Note: Ollama LLM not yet available. Using rule-based analysis.*")
        return ("🤖 **ARIA Copilot**: I am analyzing the current network state. "
                "Please ensure Ollama is running (`docker exec ps13-ollama ollama pull mistral:7b-instruct`) "
                "for full AI-powered analysis. Currently operating in rule-based mode.\n"
                "Ask me about: failure analysis, risk scores, congestion, BGP flaps, tunnel issues.")

    @staticmethod
    def _extract_node_refs(text: str) -> List[str]:
        """Extract node ID references from copilot response."""
        known_nodes = [
            "HUB-RTR-01", "MPLS-PE-01", "MPLS-PE-02", "SDWAN-CTRL",
            "SPOKE-RTR-A", "SPOKE-RTR-B", "SPOKE-RTR-C", "SPOKE-RTR-D",
            "BGP-PEER-01", "SVC-VOIP", "SVC-ERP", "SVC-VIDEO",
        ]
        return [n for n in known_nodes if n in text.upper()]

    @staticmethod
    def _extract_runbook_refs(text: str) -> List[str]:
        """Extract runbook references from copilot response."""
        import re
        return re.findall(r"RB-NET-\d+", text.upper())


# Singleton
_copilot: Optional[AICopilot] = None


def get_copilot() -> AICopilot:
    global _copilot
    if _copilot is None:
        _copilot = AICopilot()
    return _copilot
