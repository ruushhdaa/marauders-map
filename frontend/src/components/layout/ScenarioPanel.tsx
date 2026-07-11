"use client";

import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, RotateCcw, ChevronRight, X, Layers, Zap } from "lucide-react";
import { usePS13Store, LEVELS, getRiskColor } from "@/store";
import { SCENARIO_CATALOG } from "@/lib/scenarios";
import { buildAdjacency } from "@/lib/demoTopology";

import { ingestFault, healFault, injectScenario as apiInjectScenario, injectFullScenario as apiInjectFullScenario, resetScenarios } from "@/lib/api";

// Static "top action" per issue type (client-side, no backend needed).
const TOP_ACTION: Record<string, string> = {
  CONGESTION: "Apply QoS shaping on HUB WAN uplink",
  BGP_FLAP: "Dampen flapping prefixes · fail over to backup peer",
  TUNNEL_DEGRADATION: "Rekey IPSec SA · reroute over MPLS path",
  MPLS_FAILURE: "Rebuild LDP sessions · shift to PE-02 label paths",
  POLICY_DRIFT: "Re-push QoS templates from golden config",
  SOFTWARE_BUG: "Run application self-healing sequence",
  API_FAILURE: "Run API gateway self-healing sequence",
};

export default function ScenarioPanel() {
  const {
    activeScenarios, injectScenario, escalateScenario,
    clearScenario, clearAllScenarios, links,
    isHealing, healingSteps
  } = usePS13Store();

  const adjacency = buildAdjacency(links);
  const activeMap = new Map(activeScenarios.map((s) => [s.type, s]));

  async function handleInject(id: string) {
    const def = SCENARIO_CATALOG.find((s) => s.id === id);
    if (!def) return;
    
    // For our new application-level faults, call the real backend
    if (def.id === "SOFTWARE_BUG" || def.id === "API_FAILURE") {
      // Optimistically register locally so UI knows it's active
      if (!activeMap.has(id)) {
         injectScenario({
          type: def.id,
          trigger_node: def.trigger_node,
          issue_type: def.issue_type,
          step: 4, // fully degraded instantly
          severity: "CRITICAL",
          started_at: Date.now(),
        });
      }

      try {
        await ingestFault(def.trigger_node, def.issue_type);
      } catch (err) {
        console.error("Failed to ingest fault", err);
      }
      return;
    }

    const existing = activeMap.get(id);
    if (existing) {
      escalateScenario(id); // active → escalate one step
      try {
        await apiInjectScenario(def.id, existing.step + 1);
      } catch (err) {
        console.error("Failed to inject scenario on backend", err);
      }
      return;
    }
    
    injectScenario({
      type: def.id,
      trigger_node: def.trigger_node,
      issue_type: def.issue_type,
      step: 1,
      severity: LEVELS[1],
      started_at: Date.now(),
    });

    try {
      await apiInjectScenario(def.id, 1);
    } catch (err) {
      console.error("Failed to inject scenario on backend", err);
    }
  }

  async function handleFull(id: string) {
    const def = SCENARIO_CATALOG.find((s) => s.id === id);
    if (!def) return;
    
    // If it's one of the application faults, trigger Self-Healing instead of "Full"
    if (def.id === "SOFTWARE_BUG" || def.id === "API_FAILURE") {
      try {
        await healFault(def.trigger_node, def.issue_type);
      } catch (err) {
        console.error("Failed to heal fault", err);
        // Fallback: clear the scenario if backend is unreachable
        clearScenario(id);
      }
      return;
    }
    
    clearScenario(id);
    injectScenario({
      type: def.id,
      trigger_node: def.trigger_node,
      issue_type: def.issue_type,
      step: 4,
      severity: LEVELS[4],
      started_at: Date.now(),
    });

    try {
      await apiInjectFullScenario(def.id);
    } catch (err) {
      console.error("Failed to fully inject scenario on backend", err);
    }
  }

  async function handleResetAll() {
    clearAllScenarios();
    try {
      await resetScenarios();
    } catch (err) {
      console.error("Failed to reset scenarios on backend", err);
    }
  }

  async function handleClearScenario(id: string) {
    clearScenario(id);
    // Since backend does not support clearing a single legacy scenario, 
    // we reset all if there are no more active scenarios.
    if (activeScenarios.length <= 1) {
      try {
        await resetScenarios();
      } catch (err) {
        console.error("Failed to reset scenarios on backend", err);
      }
    }
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-white/5 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-red-500/15 border border-red-500/30 flex items-center justify-center">
              <AlertTriangle size={14} className="text-red-400" />
            </div>
            <div>
              <div className="text-sm font-display font-bold text-white">Intrusions</div>
              <div className="text-[10px] text-white/30 font-mono">
                run several at once
              </div>
            </div>
          </div>
          <motion.button
            onClick={handleResetAll}
            disabled={activeScenarios.length === 0}
            whileTap={{ scale: 0.95 }}
            className="flex items-center gap-1 text-[10px] font-mono text-white/30 hover:text-white/60 transition-colors px-2 py-1 rounded border border-white/10 hover:border-white/20 disabled:opacity-40"
          >
            <RotateCcw size={10} />
            Reset all
          </motion.button>
        </div>

        {/* Aggregate indicator */}
        <div className="mt-3 flex items-center gap-2 rounded-lg p-2.5"
          style={{
            background: activeScenarios.length ? "rgba(221,138,74,0.08)" : "rgba(180,196,224,0.04)",
            border: `1px solid ${activeScenarios.length ? "rgba(221,138,74,0.25)" : "rgba(180,196,224,0.08)"}`,
          }}
        >
          <Layers size={12} className={activeScenarios.length ? "text-ember" : "text-white/30"} />
          <span className="text-[10px] font-mono text-white/60">
            {activeScenarios.length === 0
              ? "No active intrusions"
              : `${activeScenarios.length} intrusion${activeScenarios.length > 1 ? "s" : ""} active`}
          </span>
        </div>
      </div>

      {/* Scenario list */}
      <div className="flex-1 overflow-y-auto p-3">
        <div className="space-y-2">
          {SCENARIO_CATALOG.map((sc) => {
            const active = activeMap.get(sc.id);
            const isActive = !!active;
            const neighbours = adjacency[sc.trigger_node] ?? [];

            return (
              <motion.div
                key={sc.id}
                layout
                className="rounded-xl overflow-hidden border transition-all"
                style={{
                  borderColor: isActive ? `${sc.color}45` : "rgba(255,255,255,0.06)",
                  background: isActive ? `${sc.color}0c` : "rgba(255,255,255,0.02)",
                }}
              >
                <div className="p-3">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">{sc.icon}</span>
                      <div>
                        <div className="text-xs font-display font-bold text-white">{sc.title}</div>
                        <div className="text-[10px] text-white/40 font-mono">{sc.subtitle}</div>
                      </div>
                    </div>
                    {isActive && (
                      <button
                        onClick={() => handleClearScenario(sc.id)}
                        title="Clear this intrusion"
                        className="flex-shrink-0 w-5 h-5 rounded flex items-center justify-center text-white/40 hover:text-white hover:bg-white/10 transition-colors"
                      >
                        <X size={12} />
                      </button>
                    )}
                  </div>

                  <p className="text-[10px] text-white/40 font-mono mb-2 leading-relaxed">
                    {sc.description}
                  </p>

                  <div className="flex items-center gap-2 mb-3 text-[9px] font-mono text-white/35">
                    <span>trigger: <span className="text-white/60">{sc.trigger_node}</span></span>
                    <span>·</span>
                    <span>{neighbours.length} adjacent</span>
                  </div>

                  {/* Severity progress (only when active) */}
                  <AnimatePresence>
                    {isActive && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mb-3"
                      >
                        <div className="flex gap-1 mb-1">
                          {[0, 1, 2, 3, 4].map((s) => (
                            <div
                              key={s}
                              className="flex-1 h-1 rounded-full transition-all"
                              style={{ background: s <= active!.step ? sc.color : "rgba(255,255,255,0.1)" }}
                            />
                          ))}
                        </div>
                        <div className="flex items-center justify-between text-[9px] font-mono">
                          <span style={{ color: getRiskColor(active!.severity) }}>
                            {active!.severity} · step {active!.step + 1}/5
                          </span>
                          <span className="text-white/40 flex items-center gap-1">
                            <Zap size={8} /> {TOP_ACTION[sc.issue_type]}
                          </span>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Actions */}
                  <div className="flex gap-1.5">
                    <motion.button
                      onClick={() => handleInject(sc.id)}
                      whileTap={{ scale: 0.95 }}
                      className="flex-1 py-1.5 rounded-md text-[10px] font-mono transition-all flex items-center justify-center gap-1"
                      style={{ background: `${sc.color}14`, border: `1px solid ${sc.color}30`, color: sc.color }}
                    >
                      <ChevronRight size={9} />
                      {isActive ? "Escalate" : "Inject"}
                    </motion.button>
                    <motion.button
                      onClick={() => handleFull(sc.id)}
                      whileTap={{ scale: 0.95 }}
                      className="py-1.5 px-2.5 rounded-md text-[10px] font-mono transition-all"
                      style={{ background: "rgba(226,99,112,0.1)", border: "1px solid rgba(226,99,112,0.25)", color: "#e26370" }}
                    >
                      {sc.id === "SOFTWARE_BUG" || sc.id === "API_FAILURE" ? "Self-Heal" : "Full"}
                    </motion.button>
                  </div>
                  
                  {/* Real-time Healing Steps */}
                  <AnimatePresence>
                    {(sc.id === "SOFTWARE_BUG" || sc.id === "API_FAILURE") && isHealing && isActive && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mt-3 bg-black/20 border border-white/5 rounded p-2"
                      >
                        <div className="text-[10px] font-display text-white/70 mb-1 flex items-center gap-1">
                          <Zap size={10} className="text-blue-400" /> Auto-Recovery in progress...
                        </div>
                        <div className="space-y-1">
                          {healingSteps.map((step, idx) => (
                            <motion.div 
                              key={idx}
                              initial={{ opacity: 0, x: -10 }}
                              animate={{ opacity: 1, x: 0 }}
                              className="text-[9px] font-mono text-white/50 pl-2 border-l border-blue-500/30 py-0.5"
                            >
                              {step}
                            </motion.div>
                          ))}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
