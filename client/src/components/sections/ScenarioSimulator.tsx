import { useState, useMemo } from "react";
import { RefreshCw } from "lucide-react";
import { toast } from "sonner";

interface Control {
  id: number;
  name: string;
  desc: string;
  defaultOn: boolean;
  ealReduction: number; // in Lakhs
  cost: number; // rollout cost in Lakhs
  buImpact: Record<string, number>; // % reduction per BU (0-100 relative)
}

const controlsList: Control[] = [
  { id: 1, name: "Enforce MFA on all privileged accounts",  desc: "Applies to 340 privileged identities across 4 business units", defaultOn: true,  ealReduction: 68,  cost: 12, buImpact: { "Core Banking": 20, Payments: 25, "Corp IT": 30, "Cards & Lending": 15 } },
  { id: 2, name: "Patch critical CVEs within 7 days",        desc: "SLA tightened from 30 days on internet-facing assets",         defaultOn: true,  ealReduction: 54,  cost: 8,  buImpact: { "Core Banking": 15, Payments: 30, "Corp IT": 10, "Cards & Lending": 20 } },
  { id: 3, name: "Upgrade EDR coverage to 100%",            desc: "Currently 82% of endpoints covered",                           defaultOn: false, ealReduction: 31,  cost: 18, buImpact: { "Core Banking": 5,  Payments: 8,  "Corp IT": 28, "Cards & Lending": 12 } },
  { id: 4, name: "Segment OT / payments network",           desc: "Isolate payment switch VLAN from corporate LAN",               defaultOn: false, ealReduction: 47,  cost: 22, buImpact: { "Core Banking": 10, Payments: 45, "Corp IT": 5,  "Cards & Lending": 18 } },
  { id: 5, name: "Encrypt data at rest, all backups",       desc: "Closes 3 unencrypted backup findings",                        defaultOn: true,  ealReduction: 22,  cost: 6,  buImpact: { "Core Banking": 8,  Payments: 5,  "Corp IT": 35, "Cards & Lending": 5 }  },
  { id: 6, name: "Push non-critical remediation by 30 days", desc: "Deprioritizes 22 low-severity findings",                    defaultOn: false, ealReduction: -8,  cost: 0,  buImpact: { "Core Banking": -5, Payments: -5, "Corp IT": -8, "Cards & Lending": -3 } },
];

const BASE_EAL = 482; // in Lakhs (₹4.82 Cr)
const BU_BASE: Record<string, number> = {
  "Core Banking": 112, Payments: 91, "Corp IT": 103, "Cards & Lending": 76,
};
const BU_MAX = Math.max(...Object.values(BU_BASE));

export default function ScenarioSimulator() {
  const [activeToggles, setActiveToggles] = useState<Record<number, boolean>>(
    controlsList.reduce((acc, c) => ({ ...acc, [c.id]: c.defaultOn }), {})
  );
  const [isRunning, setIsRunning] = useState(false);
  const [pendingToggles, setPendingToggles] = useState<Record<number, boolean> | null>(null);

  const toggleControl = (id: number) => {
    setActiveToggles(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const metrics = useMemo(() => {
    const enabledControls = controlsList.filter(c => activeToggles[c.id]);
    const totalReduction = enabledControls.reduce((s, c) => s + c.ealReduction, 0);
    const totalCost = enabledControls.reduce((s, c) => s + c.cost, 0);
    const projectedEAL = Math.max(BASE_EAL - totalReduction, 50);
    const reductionPct = Math.round((totalReduction / BASE_EAL) * 100);
    const paybackMonths = totalCost > 0 ? (totalCost / (totalReduction / 12)).toFixed(1) : "0";

    // Per-BU projected reduction
    const buAfter: Record<string, number> = {};
    Object.keys(BU_BASE).forEach(bu => {
      const buReduction = enabledControls.reduce((s, c) => s + (c.buImpact[bu] ?? 0) * (BU_BASE[bu] / 100), 0);
      buAfter[bu] = Math.max(BU_BASE[bu] - buReduction, 5);
    });

    return { projectedEAL, totalReduction, totalCost, reductionPct, paybackMonths, buAfter, enabledCount: enabledControls.length };
  }, [activeToggles]);

  const handleRerun = () => {
    setIsRunning(true);
    const snapshot = { ...activeToggles };
    toast("Running Monte Carlo simulation…", { description: "50,000 trials · modified control baseline" });
    setTimeout(() => {
      setPendingToggles(snapshot);
      setIsRunning(false);
      toast.success("Simulation complete", { description: `Projected EAL: ₹${(metrics.projectedEAL / 100).toFixed(2)}Cr` });
    }, 1800);
  };

  const bus = Object.keys(BU_BASE);

  return (
    <section className="section-container stagger-enter stagger-1">
      <div className="section-header">
        <div>
          <span className="eyebrow eyebrow--gold">WHAT-IF ENGINE</span>
          <h1>Toggle a control. Watch EAL move.</h1>
          <p>Each toggle re-runs the Monte Carlo model against a modified control-effectiveness baseline.</p>
        </div>
        <button
          className="primary-button"
          onClick={handleRerun}
          disabled={isRunning}
          style={{ minWidth: 150, gap: 8 }}
        >
          <RefreshCw size={13} className={isRunning ? "spin" : ""} />
          {isRunning ? "Simulating…" : "Re-run simulation"}
        </button>
      </div>

      <div className="scenario-grid">
        {/* Controls panel */}
        <div className="terminal-card candidate-controls stagger-enter stagger-2">
          <div className="card-head mb-4">
            <div>
              <h2>Candidate controls</h2>
              <span>{metrics.enabledCount} of {controlsList.length} enabled</span>
            </div>
          </div>
          <div className="controls-list">
            {controlsList.map(control => (
              <div key={control.id} className="control-row">
                <div className="control-info">
                  <strong>{control.name}</strong>
                  <span>{control.desc}</span>
                  <div className="control-meta">
                    <span className={`control-impact ${control.ealReduction < 0 ? "text-red" : "text-green"}`}>
                      {control.ealReduction < 0 ? "+" : "−"}₹{Math.abs(control.ealReduction)}L EAL
                    </span>
                    {control.cost > 0 && <span className="text-muted"> · ₹{control.cost}L cost</span>}
                  </div>
                </div>
                <div
                  className={`toggle-switch ${activeToggles[control.id] ? "active" : ""}`}
                  onClick={() => toggleControl(control.id)}
                  role="switch"
                  aria-checked={activeToggles[control.id]}
                  tabIndex={0}
                  onKeyDown={(e) => e.key === " " && toggleControl(control.id)}
                >
                  <div className="toggle-thumb" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Impact panel */}
        <div className="terminal-card simulated-impact stagger-enter stagger-3">
          <div className="card-head mb-4">
            <div>
              <h2>Simulated impact</h2>
              <span>{metrics.enabledCount} CONTROLS ENABLED</span>
            </div>
          </div>

          <div className="impact-overview">
            <div className="impact-stat">
              <span className="text-muted text-xs uppercase tracking-wider">CURRENT EAL</span>
              <strong className="text-light text-3xl">₹4.82Cr</strong>
            </div>
            <div className="impact-arrow">→</div>
            <div className="impact-stat">
              <span className="text-muted text-xs uppercase tracking-wider">PROJECTED EAL</span>
              <strong
                className={metrics.projectedEAL < BASE_EAL ? "text-green text-3xl" : "text-red text-3xl"}
                style={{ transition: "all 0.4s ease" }}
              >
                ₹{(metrics.projectedEAL / 100).toFixed(2)}Cr
              </strong>
            </div>
          </div>

          {/* Bar chart */}
          <div className="impact-chart">
            <div className="chart-legend">
              <span className="legend-item"><span className="legend-color bg-slate" /> Before</span>
              <span className="legend-item"><span className="legend-color bg-green" /> After</span>
            </div>
            <div className="chart-y-axis" style={{ width: 40 }}>
              {[1.6, 1.2, 0.8, 0.4, 0].map(v => (
                <span key={v}>₹{v}Cr</span>
              ))}
            </div>
            <div className="bar-chart-area">
              {bus.map(bu => {
                const beforeH = Math.round((BU_BASE[bu] / BU_MAX) * 90);
                const afterH = Math.round((metrics.buAfter[bu] / BU_MAX) * 90);
                return (
                  <div key={bu} className="bar-group">
                    <div className="bar before" style={{ height: `${beforeH}%` }} />
                    <div className="bar after bg-green" style={{ height: `${afterH}%`, transition: "height 0.5s ease" }} />
                    <span className="bar-label">{bu}</span>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Footer stats */}
          <div className="impact-footer">
            <div className="footer-stat">
              <span className="text-muted text-xs">REDUCTION</span>
              <strong className={`text-lg ${metrics.totalReduction > 0 ? "text-green" : "text-red"}`}
                style={{ transition: "all 0.3s" }}>
                {metrics.totalReduction >= 0 ? "−" : "+"}₹{Math.abs(metrics.totalReduction)}L ({Math.abs(metrics.reductionPct)}%)
              </strong>
            </div>
            <div className="footer-stat">
              <span className="text-muted text-xs">ROLLOUT COST</span>
              <strong className="text-light text-lg" style={{ transition: "all 0.3s" }}>
                ₹{metrics.totalCost}L
              </strong>
            </div>
            <div className="footer-stat">
              <span className="text-muted text-xs">PAYBACK</span>
              <strong className="text-light text-lg" style={{ transition: "all 0.3s" }}>
                {metrics.paybackMonths === "0" ? "N/A" : `${metrics.paybackMonths} mo`}
              </strong>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
