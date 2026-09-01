import { useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { toast } from "sonner";

interface Control {
  key: string;
  label: string;
  desc: string;
  defaultOn: boolean;
}

const controlsList: Control[] = [
  { key: "mfa_privileged", label: "Enforce MFA on all privileged accounts", desc: "Applies to 340 privileged identities across 4 business units", defaultOn: true },
  { key: "patch_cve", label: "Patch critical CVEs within 7 days", desc: "SLA tightened from 30 days on internet-facing assets", defaultOn: true },
  { key: "upgrade_edr", label: "Upgrade EDR coverage to 100%", desc: "Currently 82% of endpoints covered", defaultOn: false },
  { key: "segment_network", label: "Segment OT / payments network", desc: "Isolate payment switch VLAN from corporate LAN", defaultOn: false },
  { key: "encrypt_backups", label: "Encrypt data at rest, all backups", desc: "Closes 3 unencrypted backup findings", defaultOn: true },
  { key: "delay_remediation", label: "Push non-critical remediation by 30 days", desc: "Deprioritizes 22 low-severity findings", defaultOn: false },
];

interface BuComparisonItem {
  name: string;
  before: number;
  after: number;
}

interface ScenarioSummary {
  current_eal_cr: number;
  projected_eal_cr: number;
  reduction_lakh: number;
  reduction_pct: number;
  rollout_cost_lakh: number;
  payback_months: number;
  bu_comparison: BuComparisonItem[];
  active_controls: string[];
}

export default function ScenarioSimulator() {
  const [activeControls, setActiveControls] = useState<string[]>([
    "mfa_privileged",
    "patch_cve",
    "encrypt_backups",
  ]);
  const [scenario, setScenario] = useState<ScenarioSummary | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const toggleControl = (controlKey: string) => {
    setActiveControls((prev) => {
      const exists = prev.includes(controlKey);
      const next = exists ? prev.filter((key) => key !== controlKey) : [...prev, controlKey];
      return next;
    });
  };

  const simulateScenario = async (nextControls: string[]) => {
    setIsRunning(true);
    try {
      const response = await fetch("/api/v1/scenario/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ active_controls: nextControls }),
      });

      if (!response.ok) {
        throw new Error("Scenario simulation request failed");
      }

      const data = (await response.json()) as ScenarioSummary;
      setScenario(data);
      toast.success("Simulation complete", {
        description: `Projected EAL: ₹${data.projected_eal_cr.toFixed(2)}Cr`,
      });
    } catch (error) {
      console.error(error);
      toast.error("Scenario simulation failed");
    } finally {
      setIsRunning(false);
    }
  };

  useEffect(() => {
    void simulateScenario(activeControls);
  }, []);

  useEffect(() => {
    if (activeControls.length > 0) {
      void simulateScenario(activeControls);
    }
  }, [activeControls]);

  const enabledCount = activeControls.length;
  const baselineEal = scenario?.current_eal_cr ?? 4.44;
  const projectedEal = scenario?.projected_eal_cr ?? 4.44;
  const reductionLakh = scenario?.reduction_lakh ?? 0;
  const totalCost = scenario?.rollout_cost_lakh ?? 0;
  const paybackMonths = scenario?.payback_months ?? 0;
  const reductionPct = scenario?.reduction_pct ?? 0;
  const buData = scenario?.bu_comparison ?? [
    { name: "Core Banking", before: 1.12, after: 1.12 },
    { name: "Payments", before: 1.1, after: 1.1 },
    { name: "Corporate IT", before: 1.1, after: 1.1 },
    { name: "Cards & Lending", before: 1.12, after: 1.12 },
  ];
  const maxBuValue = Math.max(...buData.map((item) => item.before), ...buData.map((item) => item.after), 1.3);

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
          onClick={() => void simulateScenario(activeControls)}
          disabled={isRunning}
          style={{ minWidth: 150, gap: 8 }}
        >
          <RefreshCw size={13} className={isRunning ? "spin" : ""} />
          {isRunning ? "Simulating…" : "Re-run simulation"}
        </button>
      </div>

      <div className="scenario-grid">
        <div className="terminal-card candidate-controls stagger-enter stagger-2">
          <div className="card-head mb-4">
            <div>
              <h2>Candidate controls</h2>
              <span>{enabledCount} of {controlsList.length} enabled</span>
            </div>
          </div>
          <div className="controls-list">
            {controlsList.map((control) => {
              const isActive = activeControls.includes(control.key);
              return (
                <div key={control.key} className="control-row">
                  <div className="control-info">
                    <strong>{control.label}</strong>
                    <span>{control.desc}</span>
                  </div>
                  <div
                    className={`toggle-switch ${isActive ? "active" : ""}`}
                    onClick={() => toggleControl(control.key)}
                    role="switch"
                    aria-checked={isActive}
                    tabIndex={0}
                    onKeyDown={(e) => {
                      if (e.key === " ") {
                        e.preventDefault();
                        toggleControl(control.key);
                      }
                    }}
                  >
                    <div className="toggle-thumb" />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="terminal-card simulated-impact stagger-enter stagger-3">
          <div className="card-head mb-4">
            <div>
              <h2>Simulated impact</h2>
              <span>{enabledCount} CONTROLS ENABLED</span>
            </div>
          </div>

          <div className="impact-overview">
            <div className="impact-stat">
              <span className="text-muted text-xs uppercase tracking-wider">CURRENT EAL</span>
              <strong className="text-light text-3xl">₹{baselineEal.toFixed(2)}Cr</strong>
            </div>
            <div className="impact-arrow">→</div>
            <div className="impact-stat">
              <span className="text-muted text-xs uppercase tracking-wider">PROJECTED EAL</span>
              <strong
                className={projectedEal < baselineEal ? "text-green text-3xl" : "text-red text-3xl"}
                style={{ transition: "all 0.4s ease" }}
              >
                ₹{projectedEal.toFixed(2)}Cr
              </strong>
            </div>
          </div>

          <div className="impact-chart">
            <div className="chart-legend">
              <span className="legend-item"><span className="legend-color bg-slate" /> Before</span>
              <span className="legend-item"><span className="legend-color bg-green" /> After</span>
            </div>
            <div className="chart-y-axis" style={{ width: 40 }}>
              {[1.6, 1.2, 0.8, 0.4, 0].map((value) => (
                <span key={value}>₹{value}Cr</span>
              ))}
            </div>
            <div className="bar-chart-area">
              {buData.map((group) => {
                const beforeHeight = Math.max(14, (group.before / maxBuValue) * 100);
                const afterHeight = Math.max(14, (group.after / maxBuValue) * 100);
                return (
                  <div key={group.name} className="bar-group">
                    <div className="bar before" style={{ height: `${beforeHeight}%` }} />
                    <div className="bar after bg-green" style={{ height: `${afterHeight}%`, transition: "height 0.5s ease" }} />
                    <span className="bar-label">{group.name}</span>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="impact-footer">
            <div className="footer-stat">
              <span className="text-muted text-xs">REDUCTION</span>
              <strong className={`text-lg ${reductionLakh > 0 ? "text-green" : "text-red"}`} style={{ transition: "all 0.3s" }}>
                {reductionLakh >= 0 ? "-" : "+"}₹{Math.abs(reductionLakh).toFixed(0)}L / {Math.abs(reductionPct).toFixed(0)}%
              </strong>
            </div>
            <div className="footer-stat">
              <span className="text-muted text-xs">ROLLOUT COST</span>
              <strong className="text-light text-lg" style={{ transition: "all 0.3s" }}>
                ₹{totalCost.toFixed(0)}L
              </strong>
            </div>
            <div className="footer-stat">
              <span className="text-muted text-xs">PAYBACK</span>
              <strong className="text-light text-lg" style={{ transition: "all 0.3s" }}>
                {paybackMonths === 0 ? "N/A" : `${paybackMonths.toFixed(1)} mo`}
              </strong>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
