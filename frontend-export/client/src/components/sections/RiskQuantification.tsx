import { useState, useMemo, useRef, useEffect } from "react";
import { ChevronUp, ChevronDown, ChevronsUpDown } from "lucide-react";

interface Asset {
  id: number;
  name: string;
  bu: string;
  crit: "Critical" | "High" | "Medium" | "Low";
  ealL: number; // EAL in Lakhs
  varL: number; // VaR in Lakhs
  eff: number;
  effTone: "green" | "gold" | "red";
}

const assets: Asset[] = [
  { id: 1, name: "core-pay-db-01",    bu: "Core Banking",    crit: "Critical", ealL: 112, varL: 194, eff: 41, effTone: "red" },
  { id: 2, name: "pay-gw-03",         bu: "Payments",        crit: "Critical", ealL: 91,  varL: 161, eff: 54, effTone: "gold" },
  { id: 3, name: "corp-fs-02",        bu: "Corporate IT",    crit: "High",     ealL: 64,  varL: 110, eff: 58, effTone: "gold" },
  { id: 4, name: "cards-api-legacy",  bu: "Cards & Lending", crit: "High",     ealL: 48,  varL: 82,  eff: 63, effTone: "gold" },
  { id: 5, name: "iam-sso-01",        bu: "Corporate IT",    crit: "Medium",   ealL: 39,  varL: 66,  eff: 71, effTone: "green" },
  { id: 6, name: "branch-pos-fleet",  bu: "Cards & Lending", crit: "Medium",   ealL: 28,  varL: 49,  eff: 69, effTone: "gold" },
  { id: 7, name: "hr-portal",         bu: "Corporate IT",    crit: "Low",      ealL: 9,   varL: 15,  eff: 88, effTone: "green" },
];

const mcData: Record<number, { mean: number; p95: number; p99: number; trials: string; dist: number[] }> = {
  1: { mean: 61.2, p95: 194, p99: 310, trials: "50,000", dist: [2,3,4,6,9,12,17,24,32,42,53,65,78,90,100,95,85,72,60,48,38,28,20,14,10,7,5,3,2,1] },
  2: { mean: 48.1, p95: 161, p99: 255, trials: "50,000", dist: [1,3,5,8,12,18,28,38,52,68,82,93,100,96,88,78,65,52,40,30,22,15,10,7,4,3,2,1,1,0] },
  3: { mean: 33.9, p95: 110, p99: 174, trials: "50,000", dist: [3,4,6,10,15,22,31,43,57,71,85,94,100,97,90,80,67,54,41,31,22,15,10,7,4,3,2,1,0,0] },
  4: { mean: 25.4, p95: 82,  p99: 130, trials: "50,000", dist: [4,5,8,12,18,27,38,51,65,79,91,98,100,96,89,78,64,50,38,27,19,12,8,5,3,2,1,1,0,0] },
  5: { mean: 20.7, p95: 66,  p99: 104, trials: "50,000", dist: [5,7,10,14,20,29,40,54,68,82,93,99,100,95,86,74,60,46,33,23,15,10,6,4,2,1,1,0,0,0] },
  6: { mean: 14.8, p95: 49,  p99: 78,  trials: "50,000", dist: [6,8,12,17,24,33,45,58,72,85,95,100,99,92,82,68,54,40,28,18,11,7,4,2,1,1,0,0,0,0] },
  7: { mean: 4.7,  p95: 15,  p99: 24,  trials: "50,000", dist: [8,12,17,24,33,44,57,70,83,93,99,100,96,88,76,62,47,34,22,14,8,5,3,1,1,0,0,0,0,0] },
};

const BUS = ["All business units", "Core Banking", "Payments", "Cards & Lending", "Corporate IT"];
const VIEWS = ["Org", "Business Unit", "Asset"];

type SortKey = "name" | "eal" | "eff";
type SortDir = "asc" | "desc";

const fmtL = (l: number) => l >= 100 ? `₹${(l / 100).toFixed(2)}Cr` : `₹${l}L`;

const critColor: Record<string, string> = { Critical: "#ef858d", High: "var(--gold)", Medium: "#f2c86f", Low: "#51d1a1" };

export default function RiskQuantification() {
  const [viewMode, setViewMode] = useState("Asset");
  const [activeFilter, setActiveFilter] = useState("All business units");
  const [selectedId, setSelectedId] = useState<number>(1);
  const [sortKey, setSortKey] = useState<SortKey>("eal");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const barsRef = useRef<HTMLDivElement>(null);
  const [barsVisible, setBarsVisible] = useState(false);

  useEffect(() => {
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) setBarsVisible(true); }, { threshold: 0.1 });
    if (barsRef.current) obs.observe(barsRef.current);
    return () => obs.disconnect();
  }, []);

  const filtered = useMemo(() => {
    let rows = activeFilter === "All business units" ? assets : assets.filter(a => a.bu === activeFilter);
    return [...rows].sort((a, b) => {
      const cmp = sortKey === "name" ? a.name.localeCompare(b.name)
        : sortKey === "eal" ? a.ealL - b.ealL
        : a.eff - b.eff;
      return sortDir === "asc" ? cmp : -cmp;
    });
  }, [activeFilter, sortKey, sortDir]);

  const selected = useMemo(() => assets.find(a => a.id === selectedId) ?? assets[0], [selectedId]);
  const mc = mcData[selected.id];

  const handleSort = (k: SortKey) => {
    if (sortKey === k) setSortDir(d => d === "asc" ? "desc" : "asc");
    else { setSortKey(k); setSortDir("desc"); }
  };

  const SortIcon = ({ k }: { k: SortKey }) =>
    sortKey === k ? (sortDir === "asc" ? <ChevronUp size={10} /> : <ChevronDown size={10} />) : <ChevronsUpDown size={10} style={{ opacity: 0.4 }} />;

  return (
    <section className="section-container stagger-enter stagger-1">
      <div className="section-header">
        <div>
          <span className="eyebrow eyebrow--gold">RISK QUANTIFICATION ENGINE</span>
          <h1>EAL &amp; VaR, from asset to org</h1>
          <p>FAIR-style Monte Carlo over loss-event frequency × vulnerability × impact magnitude, rolled up by asset, business unit and org.</p>
        </div>
      </div>

      {/* View toggle */}
      <div className="view-toggles">
        <div className="segmented-control">
          {VIEWS.map(mode => (
            <button key={mode} className={`segment ${viewMode === mode ? "active" : ""}`} onClick={() => setViewMode(mode)}>
              {mode}
            </button>
          ))}
        </div>
        <span className="text-muted text-xs" style={{ marginLeft: 16, lineHeight: "34px" }}>
          {viewMode === "Org" ? "Organisation-wide rollup" : viewMode === "Business Unit" ? "Grouped by business unit" : "Individual asset view"}
        </span>
      </div>

      {/* Filter tags */}
      <div className="filter-tags">
        {BUS.map(filter => (
          <button key={filter} className={`filter-tag ${activeFilter === filter ? "active" : ""}`} onClick={() => setActiveFilter(filter)}>
            {filter}
            {filter !== "All business units" && (
              <span style={{ marginLeft: 6, opacity: 0.6 }}>
                ({assets.filter(a => a.bu === filter).length})
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="quantification-grid">
        {/* Asset table */}
        <div className="terminal-card asset-register stagger-enter stagger-2">
          <div className="card-head mb-4">
            <div>
              <h2>Asset risk register</h2>
              <span>{filtered.length} ASSETS · CLICK ROW TO INSPECT</span>
            </div>
          </div>
          <table className="data-table compact-table">
            <thead>
              <tr>
                <th style={{ cursor: "pointer" }} onClick={() => handleSort("name")}>
                  <span className="th-sort">ASSET <SortIcon k="name" /></span>
                </th>
                <th>BU</th>
                <th>CRITICALITY</th>
                <th style={{ cursor: "pointer" }} onClick={() => handleSort("eal")}>
                  <span className="th-sort">EAL <SortIcon k="eal" /></span>
                </th>
                <th>VaR 95%</th>
                <th style={{ cursor: "pointer" }} onClick={() => handleSort("eff")}>
                  <span className="th-sort">CTRL EFF. <SortIcon k="eff" /></span>
                </th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(item => (
                <tr
                  key={item.id}
                  style={{ cursor: "pointer", background: item.id === selectedId ? "rgba(217,173,90,0.06)" : undefined }}
                  onClick={() => setSelectedId(item.id)}
                >
                  <td className="font-medium text-light">
                    {item.id === selectedId && <span style={{ color: "var(--gold)", marginRight: 6 }}>▶</span>}
                    {item.name}
                  </td>
                  <td className="text-muted">{item.bu}</td>
                  <td>
                    <span className="priority-dot" style={{ display: "inline-block", background: critColor[item.crit], width: 7, height: 7, borderRadius: "50%", marginRight: 6 }} />
                    <span className="text-light" style={{ fontSize: 11 }}>{item.crit}</span>
                  </td>
                  <td className="font-medium text-light">{fmtL(item.ealL)}</td>
                  <td className="font-medium text-light">{fmtL(item.varL)}</td>
                  <td>
                    <div className="control-eff-cell">
                      <span className="eff-bar">
                        <i className={`bg-${item.effTone}`} style={{ width: `${item.eff}%` }} />
                      </span>
                      <span className="text-light">{item.eff}%</span>
                    </div>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={6} style={{ textAlign: "center", padding: "28px 0", color: "var(--muted)" }}>No assets match this filter.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Monte Carlo panel */}
        <div className="terminal-card monte-carlo-chart stagger-enter stagger-3">
          <div className="card-head mb-4">
            <div>
              <h2>Monte Carlo distribution</h2>
              <span style={{ textTransform: "uppercase" }}>{selected.name} · {mc.trials} TRIALS</span>
            </div>
          </div>

          <div className="histogram-container">
            <div className="histogram-bars" ref={barsRef}>
              {mc.dist.map((height, i) => {
                const tone = i > 23 ? "red" : i >= 15 ? "gold" : "slate";
                return (
                  <div
                    key={i}
                    className={`hist-bar bg-${tone}`}
                    style={{
                      height: barsVisible ? `${height}%` : "0%",
                      transition: `height 0.5s ease ${i * 0.015}s`,
                    }}
                  />
                );
              })}
            </div>
            <div className="histogram-labels">
              <span style={{ fontSize: 9, color: "var(--muted)" }}>Min</span>
              <span style={{ fontSize: 9, color: "var(--muted)" }}>Mean</span>
              <span style={{ fontSize: 9, color: "var(--muted)", marginLeft: "auto" }}>P95</span>
              <span style={{ fontSize: 9, color: "var(--muted)" }}>P99</span>
            </div>
            <div className="histogram-axis">
              <span className="text-muted">Mean loss <strong className="text-light">₹{mc.mean}L</strong></span>
              <span className="text-muted">P95 (VaR) <strong className="text-gold">{fmtL(mc.p95)}</strong></span>
              <span className="text-muted">P99 <strong className="text-red">{fmtL(mc.p99)}</strong></span>
            </div>
          </div>

          {/* Asset summary */}
          <div className="asset-summary-footer">
            <div>
              <span className="eyebrow">CONTROL EFFECTIVENESS</span>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 8, maxWidth: 210, minWidth: 0 }}>
                <div style={{ flex: "1 1 auto", minWidth: 0, height: 6, background: "#1c2431", borderRadius: 3, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${selected.eff}%`, background: selected.effTone === "green" ? "#51d1a1" : selected.effTone === "gold" ? "var(--gold)" : "#ef858d", borderRadius: 3, transition: "width 0.6s ease" }} />
                </div>
                <span className="text-light" style={{ fontSize: 12, fontWeight: 600, flexShrink: 0, whiteSpace: "nowrap" }}>{selected.eff}%</span>
              </div>
            </div>
            <div style={{ display: "flex", gap: 20, marginTop: 16 }}>
              <div>
                <span className="eyebrow">CRITICALITY</span>
                <div style={{ marginTop: 6, color: critColor[selected.crit], fontWeight: 700, fontSize: 13 }}>{selected.crit}</div>
              </div>
              <div>
                <span className="eyebrow">BUSINESS UNIT</span>
                <div style={{ marginTop: 6, color: "var(--text)", fontSize: 12 }}>{selected.bu}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
