/*
 * CyberRiskIQ / Executive Overview reference build
 */
import { useMemo, useState, useEffect } from "react";
import {
  Activity, ArrowDownRight, ArrowUpRight, BarChart3, Bell, Check, ChevronDown, ChevronRight,
  CircleAlert, Clock3, Download, FileBarChart2, FileText, Gauge, Grid2X2, Landmark, LineChart,
  LockKeyhole, Menu, Plus, Search, Settings2, Shield, SlidersHorizontal, Sparkles, Target,
  Users, X, Zap, Sun, Moon
} from "lucide-react";
import { toast } from "sonner";
import { useCountUp } from "../hooks/useCountUp";
import { useInView } from "../hooks/useInView";
import { useTheme } from "../contexts/ThemeContext";

import RemediationBacklog from "../components/sections/RemediationBacklog";
import ComplianceMapping from "../components/sections/ComplianceMapping";
import InvestmentOptimizer from "../components/sections/InvestmentOptimizer";
import ScenarioSimulator from "../components/sections/ScenarioSimulator";
import AICopilot from "../components/sections/AICopilot";
import RiskQuantification from "../components/sections/RiskQuantification";

type RiskTone = "green" | "gold" | "red" | "slate";

const navGroups = [
  { label: "Command center", items: [{ label: "Executive Overview", icon: Grid2X2 }, { label: "Risk Quantification", icon: Activity }, { label: "AI Copilot", icon: Sparkles }, { label: "Scenario Simulator", icon: Clock3 }, { label: "Investment Optimizer", icon: BarChart3 }] },
  { label: "Governance", items: [{ label: "Compliance Mapping", icon: Shield }, { label: "Remediation Backlog", icon: FileText }] },
];

const contributors = [
  { name: "Core Banking DB Cluster", unit: "Core Banking", value: "₹1.12 Cr", amount: 112, tone: "gold" as RiskTone },
  { name: "Payments Gateway", unit: "Payments", value: "₹0.91 Cr", amount: 91, tone: "gold" as RiskTone },
  { name: "Corporate File Share", unit: "Corporate IT", value: "₹0.64 Cr", amount: 64, tone: "gold" as RiskTone },
  { name: "Cards API (legacy)", unit: "Cards & Lending", value: "₹0.48 Cr", amount: 48, tone: "gold" as RiskTone },
  { name: "IAM / SSO Platform", unit: "Corporate IT", value: "₹0.39 Cr", amount: 39, tone: "gold" as RiskTone },
];

const compliance = [
  { name: "ISO 27001", score: 82 },
  { name: "NIST CSF", score: 76 },
  { name: "CIS Controls", score: 88 },
];

function StatusPill({ tone = "green", children }: { tone?: RiskTone; children: React.ReactNode }) {
  return <span className={`status-pill status-pill--${tone}`}><span className="status-pill__dot" />{children}</span>;
}

function AnimatedNumber({ value, prefix = "", suffix = "" }: { value: string, prefix?: string, suffix?: string }) {
  const isCurrency = value.includes("₹");
  const parsedValue = parseFloat(value.replace(/[^0-9.]/g, ''));
  const isFloat = value.includes(".");
  const count = useCountUp(parsedValue || 0, 1500);
  
  if (isNaN(parsedValue)) return <>{value}</>;
  
  const displayValue = isFloat ? count.toFixed(2) : Math.round(count);
  return <>{prefix}{displayValue}{suffix}</>;
}

function MetricCard({ label, value, suffix, delta, deltaTone, note, icon: Icon, isLoading }: { label: string; value: string; suffix?: string; delta: string; deltaTone: RiskTone; note: string; icon: React.ComponentType<{ size?: number; strokeWidth?: number }>; isLoading?: boolean }) {
  if (isLoading) {
    return (
      <article className="metric-card">
        <div className="skeleton skeleton-text" style={{ width: '40%' }} />
        <div className="skeleton skeleton-title" style={{ marginTop: 14 }} />
        <div className="skeleton skeleton-text" style={{ width: '60%', marginTop: 22 }} />
      </article>
    );
  }

  const prefix = value.startsWith("₹") ? "₹" : "";
  const numSuffix = value.includes(" Cr") ? " Cr" : "";
  
  return <article className="metric-card"><div className="metric-card__label"><span>{label}</span><Icon size={15} strokeWidth={1.6} /></div><div className="metric-card__value"><AnimatedNumber value={value} prefix={prefix} suffix={numSuffix} /><small>{suffix}</small></div><div className="metric-card__foot"><span className={`metric-delta metric-delta--${deltaTone}`}>{deltaTone === "red" ? <ArrowUpRight size={12} /> : <ArrowDownRight size={12} />}{delta}</span><span>{note}</span></div></article>;
}

function TrendChart() {
  const [hoverX, setHoverX] = useState<number | null>(null);
  
  return <div className="trend-chart" onMouseLeave={() => setHoverX(null)} onMouseMove={(e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left - 47; 
    if (x >= 0 && x <= 644) setHoverX(x);
  }}><div className="chart-y-labels"><span>₹6.4Cr</span><span>₹6.0Cr</span><span>₹5.4Cr</span><span>₹4.8Cr</span></div><svg viewBox="0 0 700 270" role="img" aria-label="Trailing twelve month expected annual loss trending down"><defs><linearGradient id="ealFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#c99b48" stopOpacity=".48" /><stop offset="100%" stopColor="#c99b48" stopOpacity="0" /></linearGradient><linearGradient id="ealStroke" x1="0" x2="1"><stop offset="0%" stopColor="#d4ad61" /><stop offset="100%" stopColor="#b98c3c" /></linearGradient></defs><g className="chart-grid"><line x1="36" y1="25" x2="680" y2="25" /><line x1="36" y1="79" x2="680" y2="79" /><line x1="36" y1="133" x2="680" y2="133" /><line x1="36" y1="187" x2="680" y2="187" /><line x1="36" y1="241" x2="680" y2="241" /></g><path className="chart-fill" d="M36 62 C68 48 80 22 108 20 S132 95 163 113 S213 137 242 109 S279 63 305 72 S345 128 374 149 S423 188 452 195 S492 233 514 207 S550 163 574 195 S612 236 680 254 L680 260 L36 260 Z" fill="url(#ealFill)" /><path className="chart-stroke" d="M36 62 C68 48 80 22 108 20 S132 95 163 113 S213 137 242 109 S279 63 305 72 S345 128 374 149 S423 188 452 195 S492 233 514 207 S550 163 574 195 S612 236 680 254" stroke="url(#ealStroke)" /><g className="chart-months"><text x="36" y="278">Sep</text><text x="89" y="278">Oct</text><text x="143" y="278">Nov</text><text x="196" y="278">Dec</text><text x="252" y="278">Jan</text><text x="306" y="278">Feb</text><text x="362" y="278">Mar</text><text x="416" y="278">Apr</text><text x="471" y="278">May</text><text x="526" y="278">Jun</text><text x="582" y="278">Jul</text><text x="640" y="278">Aug</text></g></svg>
  {hoverX !== null && (
    <>
      <div className={`chart-tooltip-line ${hoverX !== null ? 'visible' : ''}`} style={{ left: hoverX + 47 }} />
      <div className={`chart-tooltip ${hoverX !== null ? 'visible' : ''}`} style={{ left: hoverX + 47, top: 120 }}>
        EAL: ₹5.1Cr<br/>Confidence: 89%
      </div>
    </>
  )}
  </div>;
}

function InvestmentCurve({ budget, setBudget }: { budget: number; setBudget: (value: number) => void }) {
  const reduction = useMemo(() => Math.round(11 + budget * 17), [budget]);
  return <article className="terminal-card investment-card stagger-enter stagger-4"><div className="card-head"><div><h2>Investment vs. Risk-Reduction curve</h2><span>DRAG TO SET BUDGET · BUNDLE RE-OPTIMIZES LIVE</span></div></div><div className="investment-summary"><div><span>₹{budget.toFixed(2)}</span><small> Crore annual security budget</small></div><div className="investment-result"><span>Projected reduction</span><strong>{reduction}%</strong></div></div><div className="curve-chart"><svg viewBox="0 0 720 200" role="img" aria-label="Investment budget and projected risk reduction curve"><g className="chart-grid"><line x1="28" y1="28" x2="700" y2="28" /><line x1="28" y1="82" x2="700" y2="82" /><line x1="28" y1="136" x2="700" y2="136" /></g><path d="M30 154 C120 107 178 82 248 63 S350 41 413 35 S523 28 698 24" className="curve-line" /><circle cx={30 + (budget / 12) * 668} cy={154 - (budget / 12) * 130} r="6" className="curve-point" /></svg><div className="curve-axis"><span>₹0Cr</span><span>₹6Cr</span><span>₹12Cr</span></div></div><input aria-label="Annual security budget" className="budget-slider" type="range" min="0" max="12" step=".25" value={budget} onChange={(event) => setBudget(Number(event.target.value))} /><div className="investment-foot"><span>Marginal gain flattens after the recommended allocation.</span><button className="ghost-button" onClick={() => toast.success("Bundle recommendation ready", { description: `₹${budget.toFixed(2)}Cr scenario includes 5 control moves.` })}>Review bundle <ArrowUpRight size={13} /></button></div></article>;
}

function EvidenceDrawer({ contributor, onClose }: { contributor: typeof contributors[number]; onClose: () => void }) {
  return <><div className="drawer-scrim" onClick={onClose} /><aside className="evidence-drawer"><div className="drawer-head"><div><span className="eyebrow">Selected risk contributor</span><h2>{contributor.name}</h2></div><button className="icon-button" onClick={onClose} aria-label="Close evidence drawer"><X size={17} /></button></div><StatusPill tone="gold">Top contributor</StatusPill><div className="drawer-value"><span>Expected annual loss</span><strong>{contributor.value}</strong><small>{contributor.unit}</small></div><div className="drawer-section"><span className="eyebrow">Monte Carlo context</span><p>This business surface contributes to the org-wide EAL through asset value, threat likelihood, control efficacy, and evidence freshness.</p></div><div className="drawer-stats"><div><span className="eyebrow">Share of EAL</span><strong>{Math.round(contributor.amount / 4.82 * 100)}%</strong></div><div><span className="eyebrow">Evidence confidence</span><strong>91.8%</strong></div></div><div className="drawer-section drawer-section--last"><span className="eyebrow">Recommended next move</span><strong>Segment access paths and verify gateway controls</strong><p>Potential reduction: <b>₹0.34 Cr</b> · confidence 0.88</p></div><button className="primary-button primary-button--full" onClick={() => toast.success("Finding added to backlog", { description: `${contributor.name} is ready for remediation planning.` })}>Add to remediation backlog <ArrowUpRight size={14} /></button></aside></>;
}

export default function Home() {
  const [activeNav, setActiveNav] = useState("Executive Overview");
  const [role, setRole] = useState("Executive");
  const [budget, setBudget] = useState(1);
  const [selected, setSelected] = useState<typeof contributors[number] | null>(null);
  const [mobileNav, setMobileNav] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { theme, toggleTheme } = useTheme();
  
  const [complianceRef, complianceInView] = useInView();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.metaKey && e.key === 'k') {
        e.preventDefault();
        toast("Global Search", { description: "Command Palette opened." });
      } else if (e.key === 'e' && e.ctrlKey) {
        e.preventDefault();
        toast("Export", { description: "Export triggered." });
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const selectNav = (label: string) => { setActiveNav(label); setMobileNav(false); };

  return (
    <div className="terminal-shell">
      <div className={`mobile-scrim ${mobileNav ? "is-open" : ""}`} onClick={() => setMobileNav(false)} />
      <div className={`mobile-rail ${mobileNav ? "is-open" : ""}`}>
        <Rail activeNav={activeNav} onSelect={selectNav} mobile />
      </div>
      <div className="desktop-rail">
        <Rail activeNav={activeNav} onSelect={selectNav} />
      </div>
      <div className="terminal-main">
        <header className="terminal-topbar">
          <button className="mobile-menu icon-button" onClick={() => setMobileNav(true)} aria-label="Open navigation">
            <Menu size={18} />
          </button>
          <button className="org-switcher" onClick={() => toast("Organization switcher", { description: "Acme Corp · BFSI demo instance" })}>
            <span className="org-avatar">AC</span>
            <span><b>Acme Corp</b><small>BFSI demo instance</small></span>
            <ChevronDown size={13} />
          </button>
          <div className="breadcrumb">
            <span>CyberRiskIQ</span>
            <ChevronRight size={13} />
            <strong>Executive Overview</strong>
          </div>
          <div className="topbar-actions">
            <div className="role-switcher">
              {["Executive", "CISO", "Analyst"].map((item) => (
                <button key={item} className={role === item ? "active" : ""} onClick={() => setRole(item)}>{item}</button>
              ))}
            </div>
            <button className="live-pill" onClick={() => toast("Monte Carlo engine live", { description: "4 sources · 18,421 evidence points synced." })}>
              <span />LIVE · MONTE CARLO ACTIVE
            </button>
            <button className="icon-button topbar-alert" onClick={() => toast("No new alerts", { description: "All critical findings are acknowledged." })}>
              <Bell size={16} />
            </button>
            <button className="icon-button" onClick={toggleTheme}>
              {theme === 'dark' ? <Sun size={16} /> : <Moon size={16} />}
            </button>
            <button className="user-initials" onClick={() => toast(`${role} view`, { description: "Acme Corp · BFSI demo instance" })}>AK</button>
          </div>
        </header>

        <main className="terminal-content">
          {activeNav === "Executive Overview" && (
            <>
              <section className={`executive-head ${!isLoading ? 'stagger-enter stagger-1' : ''}`}>
                <div>
                  <span className="eyebrow eyebrow--gold">Executive dashboard</span>
                  <h1>Enterprise cyber risk, priced in rupees</h1>
                  <p>Continuous rollup of Expected Annual Loss and Value-at-Risk across 4 business units and 86 assets. Every figure below traces to a Monte Carlo simulation, not a heat-map.</p>
                </div>
                <div className="executive-actions">
                  <button className="secondary-button" onClick={() => toast("Business unit flow", { description: "Add a new business unit to the portfolio model." })}>
                    <Plus size={14} />Add Business Unit
                  </button>
                  <button className="primary-button" onClick={() => toast.success("Board deck export queued", { description: "Your executive overview is being prepared." })}>
                    <Download size={14} />Export Board Deck (Ctrl+E)
                  </button>
                </div>
              </section>

              <section className={`metrics-grid ${!isLoading ? 'stagger-enter stagger-2' : ''}`}>
                <MetricCard label="Enterprise Risk Score" value="73" suffix="/100" delta="12%" deltaTone="green" note="vs last quarter" icon={Gauge} isLoading={isLoading} />
                <MetricCard label="Total Annual Loss Exposure (EAL)" value="₹4.82 Cr" delta="₹68L" deltaTone="green" note="since last recompute" icon={CircleAlert} isLoading={isLoading} />
                <MetricCard label="Value at Risk (95th pct)" value="₹9.15 Cr" delta="3%" deltaTone="red" note="tail risk widening" icon={Target} isLoading={isLoading} />
                <MetricCard label="Open Critical Findings" value="17" delta="4" deltaTone="red" note="new this week" icon={FileBarChart2} isLoading={isLoading} />
              </section>

              {!isLoading && (
                <section className="dashboard-grid">
                  <article className="terminal-card trend-card stagger-enter stagger-3">
                    <div className="card-head">
                      <div>
                        <h2>Risk exposure trend — org-wide EAL</h2>
                        <span>TRAILING 12 MONTHS · MONTE CARLO RECOMPUTE, DAILY</span>
                      </div>
                    </div>
                    <TrendChart />
                  </article>
                  <article className="terminal-card contributors-card stagger-enter stagger-3">
                    <div className="card-head">
                      <div>
                        <h2>Top 5 risk contributors</h2>
                        <span>SHARE OF ORG-WIDE EAL</span>
                      </div>
                      <button className="icon-button" onClick={() => toast("Contributor filters", { description: "Filter by business unit, asset type, or control family." })}>
                        <SlidersHorizontal size={15} />
                      </button>
                    </div>
                    <div className="contributors-list">
                      {contributors.length === 0 ? (
                        <div className="empty-state" style={{ textAlign: 'center', padding: '40px 0', color: '#687483', fontSize: 11 }}>
                          <Shield size={32} style={{ margin: '0 auto 12px', opacity: 0.2 }} />
                          <p>No major risk contributors found.</p>
                        </div>
                      ) : (
                        contributors.map((item) => (
                          <button key={item.name} className="contributor-row" onClick={() => setSelected(item)}>
                            <span className="contributor-copy"><b>{item.name}</b><small>{item.unit}</small></span>
                            <strong>{item.value}</strong>
                            <span className="contributor-bar"><i style={{ width: `${item.amount / 112 * 100}%` }} /></span>
                            <ChevronRight size={13} />
                          </button>
                        ))
                      )}
                    </div>
                  </article>
                  <InvestmentCurve budget={budget} setBudget={setBudget} />
                  <article className="terminal-card compliance-card stagger-enter stagger-4" ref={complianceRef as any}>
                    <div className="card-head">
                      <div>
                        <h2>Framework compliance snapshot</h2>
                        <span>AUTO-MAPPED CONTROL COVERAGE</span>
                      </div>
                      <button className="icon-button" onClick={() => toast("Compliance mapping", { description: "Control coverage is mapped against the latest evidence set." })}>
                        <Shield size={15} />
                      </button>
                    </div>
                    <div className="compliance-list">
                      {compliance.map((item) => (
                        <div className="compliance-row" key={item.name}>
                          <div><b>{item.name}</b><span>{item.score}%</span></div>
                          <div className="compliance-track"><i style={{ width: complianceInView ? `${item.score}%` : '0%' }} /></div>
                        </div>
                      ))}
                    </div>
                    <div className="compliance-foot">
                      <span><LockKeyhole size={12} />Evidence-backed coverage</span>
                      <button className="ghost-button" onClick={() => toast("Compliance report", { description: "Board-ready framework coverage summary requested." })}>
                        View mapping <ArrowUpRight size={13} />
                      </button>
                    </div>
                  </article>
                </section>
              )}
            </>
          )}

          {activeNav === "Risk Quantification" && <RiskQuantification />}
          {activeNav === "AI Copilot" && <AICopilot />}
          {activeNav === "Scenario Simulator" && <ScenarioSimulator />}
          {activeNav === "Investment Optimizer" && <InvestmentOptimizer />}
          {activeNav === "Compliance Mapping" && <ComplianceMapping />}
          {activeNav === "Remediation Backlog" && <RemediationBacklog />}

          <footer className="terminal-footer">
            <span><span className="footer-live" />Synthetic feed · Acme Corp</span>
            <span>Refreshed 4 min ago · {role} view (Press ⌘K to search)</span>
          </footer>
        </main>
      </div>
    </div>
  )
}

function Rail({ activeNav, onSelect, mobile = false }: { activeNav: string; onSelect: (label: string) => void; mobile?: boolean }) {
  return <aside className={`rail ${mobile ? "rail--mobile" : ""}`}><div className="rail-brand"><div className="rail-brand__mark">₹Q</div><div><b>CyberRiskIQ</b><span>SIH26105 · PROTOTYPE</span></div><button className="icon-button rail-close" onClick={() => onSelect(activeNav)} aria-label="Close navigation"><X size={15} /></button></div><div className="rail-org"><span className="org-avatar">AC</span><div><b>Acme Corp</b><small>BFSI demo instance</small></div><ChevronDown size={13} /></div>{navGroups.map((group) => <div className="rail-group" key={group.label}><span className="rail-label">{group.label}</span>{group.items.map(({ label, icon: Icon }) => <button key={label} className={`rail-item ${activeNav === label ? "is-active" : ""}`} onClick={() => onSelect(label)}><Icon size={15} strokeWidth={1.7} /><span>{label}</span>{label === "Investment Optimizer" && <i className="rail-count">3</i>}</button>)}</div>)}<div className="rail-foot"><span><span className="footer-live" />Synthetic feed · Acme Corp</span><small>Refreshed 4 min ago</small></div></aside>;
}
