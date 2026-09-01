import { useEffect, useMemo, useState } from "react";

type FundedControl = {
  id: number;
  name: string;
  cost_lakh: number;
  cost_cr: number;
  risk_saved_lakh: number;
  risk_saved_cr: number;
  roi_multiplier: number;
};

type UnfundedControl = {
  id: number;
  name: string;
  cost_lakh: number;
  risk_saved_lakh: number;
  reason: string;
};

type CurvePoint = {
  spend_cr: number;
  risk_reduction_cr: number;
};

type OptimizerResult = {
  budget_cr: number;
  allocated_spend_cr: number;
  unspent_lakh: number;
  total_risk_reduced_cr: number;
  overall_rosi: number;
  funded_controls: FundedControl[];
  unfunded_controls: UnfundedControl[];
  curve_points: CurvePoint[];
  sweet_spot_cr: number;
  executive_summary: string;
  recommended_action_ids: number[];
  total_cost_lakhs: number;
  total_reduction_lakhs: number;
  remaining_budget_lakhs: number;
  expected_eal_after_lakhs: number;
  rationale: string[];
};

const presets = [
  { label: "Regulatory Minimum", value: 0.45 },
  { label: "Balanced / Max ROI", value: 1.2 },
  { label: "Full Protection", value: 2.8 },
];

const fmtINR = (value: number, digits = 2) => `₹${value.toFixed(digits)}`;

export default function InvestmentOptimizer() {
  const [budget, setBudget] = useState<number>(1.2);
  const [optimizer, setOptimizer] = useState<OptimizerResult | null>(null);
  const [loading, setLoading] = useState(false);

  const maxBudget = 5;

  useEffect(() => {
    const timer = window.setTimeout(async () => {
      setLoading(true);
      try {
        const response = await fetch("/api/v1/optimizer/optimize", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ budget_cr: Number(budget.toFixed(2)) }),
        });

        if (!response.ok) {
          throw new Error("Optimizer request failed");
        }

        const data = (await response.json()) as OptimizerResult;
        setOptimizer(data);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    }, 250);

    return () => window.clearTimeout(timer);
  }, [budget]);

  const chartData = optimizer?.curve_points ?? [];

  const chartPath = useMemo(() => {
    if (chartData.length === 0) {
      return "M 0 300 C 100 200, 180 160, 300 90 S 520 40, 760 10";
    }

    const maxX = Math.max(5, ...chartData.map((point) => point.spend_cr), 1);
    const maxY = Math.max(5, ...chartData.map((point) => point.risk_reduction_cr), 1);

    const points = chartData.map((point, index) => {
      const x = (point.spend_cr / maxX) * 760;
      const y = 300 - (point.risk_reduction_cr / maxY) * 230;
      return `${index === 0 ? "M" : "L"} ${x} ${y}`;
    });

    return points.join(" ");
  }, [chartData]);

  const activePoint = optimizer
    ? {
        x: (optimizer.allocated_spend_cr / Math.max(5, optimizer.budget_cr || 5)) * 760,
        y: 300 - (optimizer.total_risk_reduced_cr / Math.max(3, optimizer.total_risk_reduced_cr || 3)) * 230,
      }
    : null;

  const summary = optimizer?.executive_summary ?? "Loading optimizer recommendation…";

  return (
    <section className="section-container stagger-enter stagger-1">
      <div className="section-header">
        <div>
          <span className="eyebrow eyebrow--gold">INVESTMENT OPTIMIZATION MODULE</span>
          <h1>Best risk reduction, per rupee</h1>
          <p>0/1 knapsack over the mitigation catalog: maximize total risk reduction while respecting the annual security budget.</p>
        </div>
      </div>

      <div className="terminal-card large-investment-card stagger-enter stagger-2">
        <div className="investment-header-row">
          <div className="investment-header">
            <div>
              <h3>Set your annual security budget</h3>
              <span>RECOMMENDED BUNDLE RE-SOLVES INSTANTLY</span>
            </div>
          </div>
          <div className="optimizer-zone-badge">Optimal Zone (₹1.10 - ₹1.40 Cr)</div>
        </div>

        <div className="optimizer-preset-row">
          {presets.map((preset) => (
            <button
              key={preset.label}
              type="button"
              className={`optimizer-preset ${Math.abs(budget - preset.value) < 0.05 ? "is-active" : ""}`}
              onClick={() => setBudget(preset.value)}
            >
              {preset.label} (₹{preset.value.toFixed(2)} Cr)
            </button>
          ))}
        </div>

        <div className="budget-display">
          <span className="budget-value">₹{budget.toFixed(2)}</span>
          <span className="budget-unit">Crore</span>
        </div>

        <div className="slider-container">
          <input
            type="range"
            className="budget-slider large-slider"
            min="0"
            max={maxBudget}
            step="0.05"
            value={budget}
            onChange={(event) => setBudget(Number(event.target.value))}
            aria-label="Annual security budget"
          />
          <div className="slider-axis">
            <span>₹0</span>
            <span>₹1.25 Cr</span>
            <span>₹2.5 Cr</span>
            <span>₹3.75 Cr</span>
            <span>₹5 Cr</span>
          </div>
        </div>

        <div className="optimizer-overview-grid">
          <div className="optimizer-stat-box">
            <span className="stat-label">Allocated spend</span>
            <strong>{optimizer ? fmtINR(optimizer.allocated_spend_cr, 2) + " Cr" : "—"}</strong>
          </div>
          <div className="optimizer-stat-box">
            <span className="stat-label">Risk reduced</span>
            <strong>{optimizer ? fmtINR(optimizer.total_risk_reduced_cr, 2) + " Cr" : "—"}</strong>
          </div>
          <div className="optimizer-stat-box">
            <span className="stat-label">ROSI</span>
            <strong>{optimizer ? `${optimizer.overall_rosi.toFixed(2)}x` : "—"}</strong>
          </div>
          <div className="optimizer-stat-box accent">
            <span className="stat-label">Sweet spot</span>
            <strong>{optimizer ? `₹${optimizer.sweet_spot_cr.toFixed(2)} Cr` : "—"}</strong>
          </div>
        </div>

        <div className="optimizer-chart-card">
          <div className="large-curve-chart">
            <div className="chart-y-axis">
              <span>₹4.0 Cr</span>
              <span>₹3.0 Cr</span>
              <span>₹2.0 Cr</span>
              <span>₹1.0 Cr</span>
              <span>₹0.0 Cr</span>
            </div>
            <svg viewBox="0 0 760 300" preserveAspectRatio="none" aria-label="Risk reduction efficiency frontier">
              <defs>
                <linearGradient id="curveGradient" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#6376c9" stopOpacity="0.35" />
                  <stop offset="100%" stopColor="#6376c9" stopOpacity="0" />
                </linearGradient>
              </defs>
              <g className="chart-grid">
                {[0, 60, 120, 180, 240, 300].map((y) => (
                  <line key={y} x1="0" y1={y} x2="760" y2={y} stroke="rgba(148,163,184,0.15)" />
                ))}
                {[0, 120, 240, 360, 480, 600, 760].map((x) => (
                  <line key={x} x1={x} y1="0" x2={x} y2="300" stroke="rgba(148,163,184,0.08)" />
                ))}
              </g>
              <path d={`${chartPath} L 760 300 L 0 300 Z`} fill="url(#curveGradient)" opacity={0.9} />
              <path d={chartPath} fill="none" stroke="#8ba1fb" strokeWidth="3" strokeLinecap="round" />
              {activePoint && (
                <g>
                  <circle cx={activePoint.x} cy={activePoint.y} r="10" fill="rgba(217,173,90,0.25)" />
                  <circle cx={activePoint.x} cy={activePoint.y} r="5" fill="#f0c76d" stroke="#fff" strokeWidth="2" className="chart-dot" />
                </g>
              )}
            </svg>
          </div>
          <div className="chart-legend-row">
            <span>Current spend: {optimizer ? fmtINR(optimizer.allocated_spend_cr, 2) + " Cr" : "—"}</span>
            <span>Risk reduction: {optimizer ? fmtINR(optimizer.total_risk_reduced_cr, 2) + " Cr" : "—"}</span>
          </div>
        </div>

        {optimizer && (
          <div className="optimizer-analysis-grid">
            <div className="decision-card decision-card--summary">
              <div className="decision-header">
                <span className="decision-kicker">Why this curve?</span>
                <h4>Decision breakdown</h4>
              </div>
              <p>{summary}</p>
              <div className="decision-bullets">
                <div className="bulb-pill">Steep ROI zone: low cost, fast reduction</div>
                <div className="bulb-pill muted">Diminishing returns: incremental spend buys less risk reduction</div>
              </div>
            </div>

            <div className="decision-card decision-card--quicklook">
              <div className="decision-header">
                <span className="decision-kicker">Bundle status</span>
                <h4>Current recommendation</h4>
              </div>
              <ul>
                <li>Funded controls: {optimizer.funded_controls.length}</li>
                <li>Unfunded next-in-line: {optimizer.unfunded_controls.length}</li>
                <li>Unspent: {fmtINR(optimizer.unspent_lakh, 0)}L</li>
                <li>Expected post-investment EAL: ₹{(optimizer.expected_eal_after_lakhs / 100).toFixed(2)} Cr</li>
              </ul>
            </div>
          </div>
        )}

        {optimizer && (
          <div className="optimizer-funding-grid">
            <div className="funding-card">
              <div className="funding-header">
                <h4>Funded Initiatives</h4>
                <span>{optimizer.funded_controls.length} controls</span>
              </div>
              <div className="funding-list">
                {optimizer.funded_controls.length === 0 ? (
                  <div className="empty-state">No controls fit within the current budget.</div>
                ) : (
                  optimizer.funded_controls.map((control) => (
                    <div key={control.id} className="funding-row funded-row">
                      <div className="funding-meta">
                        <span className="funding-check">✓</span>
                        <div>
                          <strong>{control.name}</strong>
                          <small>{fmtINR(control.cost_cr, 2)} Cr / {fmtINR(control.risk_saved_cr, 2)} Cr risk saved</small>
                        </div>
                      </div>
                      <div className="funding-amounts">
                        <span>{control.roi_multiplier.toFixed(2)}x ROI</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div className="funding-card unfunded-card">
              <div className="funding-header">
                <h4>Unfunded / Next in Line</h4>
                <span>{optimizer.unfunded_controls.length} items</span>
              </div>
              <div className="funding-list">
                {optimizer.unfunded_controls.length === 0 ? (
                  <div className="empty-state">All high-priority controls fit within the selected budget.</div>
                ) : (
                  optimizer.unfunded_controls.map((control) => (
                    <div key={control.id} className="funding-row unfunded-row">
                      <div className="funding-meta">
                        <span className="funding-tag">!</span>
                        <div>
                          <strong>{control.name}</strong>
                          <small>{fmtINR(control.cost_lakh / 100, 2)} Cr / {fmtINR(control.risk_saved_lakh / 100, 2)} Cr risk saved</small>
                        </div>
                      </div>
                      <div className="funding-reason">{control.reason}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
