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

type ContributorItem = {
  id: number;
  name: string;
  unit: string;
  value: string;
  amount: number;
  tone: RiskTone;
  businessUnit?: string;
  ealContributionCr?: number;
  var95Cr?: number;
  explanation?: string;
  telemetrySource?: string;
  lossBreakdown?: {
    downtime_pct?: number;
    breach_response_pct?: number;
    regulatory_fines_pct?: number;
    customer_remedy_pct?: number;
  };
  technicalDetails?: {
    cve?: string;
    cvss?: number;
    port?: number;
    mfa_enforced?: boolean;
  };
};

const navGroups = [
  { label: "Command center", items: [{ label: "Executive Overview", icon: Grid2X2 }, { label: "Risk Quantification", icon: Activity }, { label: "AI Copilot", icon: Sparkles }, { label: "Scenario Simulator", icon: Clock3 }, { label: "Investment Optimizer", icon: BarChart3 }] },
  { label: "Governance", items: [{ label: "Compliance Mapping", icon: Shield }, { label: "Remediation Backlog", icon: FileText }] },
];

const contributorSeed: ContributorItem[] = [
  { id: 1, name: "Core Banking DB Cluster", unit: "Core Banking", value: "₹1.12 Cr", amount: 112, tone: "gold" as RiskTone },
  { id: 2, name: "Payments Gateway", unit: "Payments", value: "₹0.91 Cr", amount: 91, tone: "gold" as RiskTone },
  { id: 3, name: "Corporate File Share", unit: "Corporate IT", value: "₹0.64 Cr", amount: 64, tone: "gold" as RiskTone },
  { id: 4, name: "Cards API (legacy)", unit: "Cards & Lending", value: "₹0.48 Cr", amount: 48, tone: "gold" as RiskTone },
  { id: 5, name: "IAM / SSO Platform", unit: "Corporate IT", value: "₹0.39 Cr", amount: 39, tone: "gold" as RiskTone },
];

const notificationAlerts = [
  { title: "Payment switch segmentation overdue", detail: "RBI control test failed on 2 of 4 network segments.", time: "12 min ago" },
  { title: "Privileged MFA drift detected", detail: "11 stale admin sessions remain unreviewed across Core Banking.", time: "27 min ago" },
  { title: "Legacy API patch SLA missed", detail: "Cards API cluster has 3 critical CVEs beyond the 7-day window.", time: "41 min ago" },
];

const dashboardPerspectives = {
  Executive: {
    headline: "Enterprise cyber risk, priced in rupees",
    subhead: "Continuous rollup of Expected Annual Loss and Value-at-Risk across 4 business units and 86 assets. Every figure below traces to a Monte Carlo simulation, not a heat-map.",
  },
  CISO: {
    headline: "Control coverage and governance posture",
    subhead: "Control efficacy, assurance gaps, and framework readiness across the enterprise. The focus is on resilience, evidence quality, and control drift reduction.",
  },
  Analyst: {
    headline: "Vulnerability backlog and remediation priority",
    subhead: "Exposure clustering, backlog pressure, and critical-finding remediation sequencing by business unit and asset criticality.",
  },
};

const metricsByPerspective: Record<string, Array<{ label: string; value: string; suffix?: string; delta: string; deltaTone: RiskTone; note: string; icon: React.ComponentType<{ size?: number; strokeWidth?: number }> }>> = {
  Executive: [
    { label: "Enterprise Risk Score", value: "73", suffix: "/100", delta: "12%", deltaTone: "green", note: "vs last quarter", icon: Gauge },
    { label: "Total Annual Loss Exposure (EAL)", value: "₹4.82 Cr", delta: "₹68L", deltaTone: "green", note: "since last recompute", icon: CircleAlert },
    { label: "Value at Risk (95th pct)", value: "₹9.15 Cr", delta: "3%", deltaTone: "red", note: "tail risk widening", icon: Target },
    { label: "Open Critical Findings", value: "17", delta: "4", deltaTone: "red", note: "new this week", icon: FileBarChart2 },
  ],
  CISO: [
    { label: "Control Assurance", value: "82%", suffix: "", delta: "9%", deltaTone: "green", note: "vs last quarter", icon: Shield },
    { label: "Framework Coverage", value: "76%", delta: "4%", deltaTone: "green", note: "from evidence review", icon: LockKeyhole },
    { label: "Critical Controls Gap", value: "11", delta: "3", deltaTone: "red", note: "requiring validation", icon: CircleAlert },
    { label: "Remediation SLA Health", value: "88%", delta: "5%", deltaTone: "green", note: "maintained", icon: Check },
  ],
  Analyst: [
    { label: "Critical Backlog", value: "29", delta: "6", deltaTone: "red", note: "this week", icon: FileText },
    { label: "High-Priority Assets", value: "8", delta: "2", deltaTone: "red", note: "under active review", icon: Zap },
    { label: "Median MTTR", value: "11d", delta: "-2d", deltaTone: "green", note: "improving trend", icon: Clock3 },
    { label: "IR Drill Readiness", value: "74%", delta: "7%", deltaTone: "green", note: "ready for restart", icon: Activity },
  ],
};

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

function InvestmentCurve({ budget, setBudget, onReviewBundle }: { budget: number; setBudget: (value: number) => void; onReviewBundle: () => void }) {
  const reduction = useMemo(() => Math.round(11 + budget * 17), [budget]);
  return <article className="terminal-card investment-card stagger-enter stagger-4"><div className="card-head"><div><h2>Investment vs. Risk-Reduction curve</h2><span>DRAG TO SET BUDGET · BUNDLE RE-OPTIMIZES LIVE</span></div></div><div className="investment-summary"><div><span>₹{budget.toFixed(2)}</span><small> Crore annual security budget</small></div><div className="investment-result"><span>Projected reduction</span><strong>{reduction}%</strong></div></div><div className="curve-chart"><svg viewBox="0 0 720 200" role="img" aria-label="Investment budget and projected risk reduction curve"><g className="chart-grid"><line x1="28" y1="28" x2="700" y2="28" /><line x1="28" y1="82" x2="700" y2="82" /><line x1="28" y1="136" x2="700" y2="136" /></g><path d="M30 154 C120 107 178 82 248 63 S350 41 413 35 S523 28 698 24" className="curve-line" /><circle cx={30 + (budget / 12) * 668} cy={154 - (budget / 12) * 130} r="6" className="curve-point" /></svg><div className="curve-axis"><span>₹0Cr</span><span>₹6Cr</span><span>₹12Cr</span></div></div><input aria-label="Annual security budget" className="budget-slider" type="range" min="0" max="12" step=".25" value={budget} onChange={(event) => setBudget(Number(event.target.value))} /><div className="investment-foot"><span>Marginal gain flattens after the recommended allocation.</span><button className="ghost-button" onClick={() => { toast.success("Bundle recommendation ready", { description: `₹${budget.toFixed(2)}Cr scenario includes 5 control moves.` }); onReviewBundle(); }}>Review bundle <ArrowUpRight size={13} /></button></div></article>;
}

function EvidenceDrawer({ contributor, onClose, persona }: { contributor: ContributorItem; onClose: () => void; persona: string }) {
  const ealValue = contributor.ealContributionCr ?? Number((contributor.amount / 100).toFixed(2));
  const var95Value = contributor.var95Cr ?? Number((contributor.amount * 1.68 / 100).toFixed(2));
  const explanation = contributor.explanation || 
    "This business surface contributes materially to enterprise expected loss because its value, interaction volume, and exposure to internet-facing traffic amplify both frequency and severity. The control posture is still uneven, with a few access and patching gaps creating a moderate to elevated tail-risk profile. Because the exposure sits in a high-value business unit, it remains a priority for near-term mitigation and monitoring.";
  const telemetrySource = contributor.telemetrySource || "Qualys Scanner & Okta";
  const lossBreakdown = contributor.lossBreakdown || { downtime_pct: 32, breach_response_pct: 28, regulatory_fines_pct: 24, customer_remedy_pct: 16 };
  const lossCategories = [
    { label: "Downtime", value: lossBreakdown.downtime_pct ?? 0, tone: "gold" },
    { label: "Breach Response", value: lossBreakdown.breach_response_pct ?? 0, tone: "red" },
    { label: "Regulatory Fines", value: lossBreakdown.regulatory_fines_pct ?? 0, tone: "green" },
    { label: "Customer Remedy", value: lossBreakdown.customer_remedy_pct ?? 0, tone: "slate" },
  ];
  const fairCam = {
    threatResistance: 58,
    lossMitigation: 74,
    threatCommunity: ["Ransomware Cartels", "Supply-Chain Attackers"],
    vendorDependency: "AWS Ingress / Cloud Provider",
    reserveCr: ealValue * 0.28,
  };
  const headerTitle = persona === "CISO"
    ? "CISO Governance & SLA Impact"
    : persona === "Analyst"
      ? "Analyst Telemetry Root-Cause"
      : "Executive Financial Briefing";
  const summaryLabel = persona === "CISO"
    ? "Director control and SLA assessment"
    : persona === "Analyst"
      ? "Telemetry-driven root-cause narrative"
      : "Board and CFO financial briefing";

  return <><div className="drawer-scrim" onClick={onClose} /><aside className="evidence-drawer"><div className="drawer-head"><div><span className="eyebrow">{summaryLabel}</span><h2>{headerTitle}</h2></div><button className="icon-button" onClick={onClose} aria-label="Close evidence drawer"><X size={17} /></button></div><StatusPill tone="gold">{contributor.unit}</StatusPill><div className="drawer-value"><span>Expected annual loss</span><strong>₹{ealValue.toFixed(2)} Cr</strong><small>{contributor.name}</small></div><div className="drawer-section"><span className="eyebrow">Asset details</span><p><b>{contributor.businessUnit || contributor.unit}</b> · EAL: <b>₹{ealValue.toFixed(2)} Cr</b> · VaR (95th pct): <b>₹{var95Value.toFixed(2)} Cr</b></p></div><div className="drawer-section"><span className="eyebrow">Why this ranks here</span><p>{explanation}</p></div><div className="drawer-section"><span className="eyebrow">Telemetry ingestion</span><div className="telemetry-badge">Ingested via {telemetrySource}</div></div>
      <div className="drawer-section"><span className="eyebrow">FAIR loss structure</span><div className="loss-breakdown">
        <div className="loss-breakdown__row"><div className="loss-breakdown__meta"><span>Primary Direct Losses</span><strong>{(lossBreakdown.downtime_pct ?? 32) + (lossBreakdown.breach_response_pct ?? 28)}%</strong></div><div className="loss-breakdown__track"><i className="loss-breakdown__fill loss-breakdown__fill--gold" style={{ width: `${(lossBreakdown.downtime_pct ?? 32) + (lossBreakdown.breach_response_pct ?? 28)}%` }} /></div></div>
        <div className="loss-breakdown__row"><div className="loss-breakdown__meta"><span>Downtime</span><strong>{lossBreakdown.downtime_pct ?? 32}%</strong></div><div className="loss-breakdown__track"><i className="loss-breakdown__fill loss-breakdown__fill--gold" style={{ width: `${lossBreakdown.downtime_pct ?? 32}%` }} /></div></div>
        <div className="loss-breakdown__row"><div className="loss-breakdown__meta"><span>Forensic / IR</span><strong>{lossBreakdown.breach_response_pct ?? 28}%</strong></div><div className="loss-breakdown__track"><i className="loss-breakdown__fill loss-breakdown__fill--red" style={{ width: `${lossBreakdown.breach_response_pct ?? 28}%` }} /></div></div>
        <div className="loss-breakdown__row"><div className="loss-breakdown__meta"><span>Secondary Losses</span><strong>{(lossBreakdown.regulatory_fines_pct ?? 24) + (lossBreakdown.customer_remedy_pct ?? 16)}%</strong></div><div className="loss-breakdown__track"><i className="loss-breakdown__fill loss-breakdown__fill--green" style={{ width: `${(lossBreakdown.regulatory_fines_pct ?? 24) + (lossBreakdown.customer_remedy_pct ?? 16)}%` }} /></div></div>
        <div className="loss-breakdown__row"><div className="loss-breakdown__meta"><span>Regulatory Fines</span><strong>{lossBreakdown.regulatory_fines_pct ?? 24}%</strong></div><div className="loss-breakdown__track"><i className="loss-breakdown__fill loss-breakdown__fill--green" style={{ width: `${lossBreakdown.regulatory_fines_pct ?? 24}%` }} /></div></div>
        <div className="loss-breakdown__row"><div className="loss-breakdown__meta"><span>Customer Remedy / Rep.</span><strong>{lossBreakdown.customer_remedy_pct ?? 16}%</strong></div><div className="loss-breakdown__track"><i className="loss-breakdown__fill loss-breakdown__fill--slate" style={{ width: `${lossBreakdown.customer_remedy_pct ?? 16}%` }} /></div></div>
      </div></div>
      <div className="drawer-section"><span className="eyebrow">Recommended incident reserve</span><div className="telemetry-badge" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, width: '100%' }}><span>Reserve fund</span><strong>₹{(fairCam.reserveCr || (ealValue * 0.28)).toFixed(2)} Cr</strong></div></div>
      <div className="drawer-section"><span className="eyebrow">FAIR-CAM & threat community</span><div className="loss-breakdown">
        <div className="loss-breakdown__row"><div className="loss-breakdown__meta"><span>Threat Resistance</span><strong>{fairCam.threatResistance}%</strong></div><div className="loss-breakdown__track"><i className="loss-breakdown__fill loss-breakdown__fill--green" style={{ width: `${fairCam.threatResistance}%` }} /></div></div>
        <div className="loss-breakdown__row"><div className="loss-breakdown__meta"><span>Loss Mitigation</span><strong>{fairCam.lossMitigation}%</strong></div><div className="loss-breakdown__track"><i className="loss-breakdown__fill loss-breakdown__fill--gold" style={{ width: `${fairCam.lossMitigation}%` }} /></div></div>
      </div><div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 12 }}>
        {fairCam.threatCommunity.map((item) => (<span key={item} className="telemetry-badge" style={{ margin: 0 }}>{item}</span>))}
        <span className="telemetry-badge" style={{ margin: 0 }}>{fairCam.vendorDependency}</span>
      </div></div><div className="drawer-stats"><div><span className="eyebrow">Share of EAL</span><strong>{Math.round((contributor.amount / 4.82) * 100)}%</strong></div><div><span className="eyebrow">Evidence confidence</span><strong>91.8%</strong></div></div><div className="drawer-section drawer-section--last"><span className="eyebrow">Recommended next move</span><strong>Segment access paths and verify gateway controls</strong><p>Potential reduction: <b>₹0.34 Cr</b> · confidence 0.88</p></div><button className="primary-button primary-button--full" onClick={() => toast.success("Finding added to backlog", { description: `${contributor.name} is ready for remediation planning.` })}>Add to remediation backlog <ArrowUpRight size={14} /></button></aside></>;
}

export default function Home() {
  const [activeNav, setActiveNav] = useState("Executive Overview");
  const [role, setRole] = useState("Executive");
  const [budget, setBudget] = useState(1);
  const [contributors, setContributors] = useState<ContributorItem[]>(contributorSeed);
  const [selected, setSelected] = useState<ContributorItem | null>(null);
  const [mobileNav, setMobileNav] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [showAlertDropdown, setShowAlertDropdown] = useState(false);
  const [showAddBusinessUnit, setShowAddBusinessUnit] = useState(false);
  const [showExportModal, setShowExportModal] = useState(false);
  const [buForm, setBuForm] = useState({ name: "", assetCount: "", initialBudget: "" });
  const [loadingExplanationId, setLoadingExplanationId] = useState<number | null>(null);
  const [telemetryEvents, setTelemetryEvents] = useState<Array<{ id: string; source: string; target_asset: string; event_type: string; severity: string; message: string; status: string; timestamp: string }>>([]);
  const [attackState, setAttackState] = useState<{ attack_active: boolean; attack_type: string | null; target_asset: string | null; eal_spike_cr?: number }>({ attack_active: false, attack_type: null, target_asset: null, eal_spike_cr: 0 });
  const { theme, toggleTheme } = useTheme();

  const [complianceRef, complianceInView] = useInView();
  const perspectiveMeta = dashboardPerspectives[role as keyof typeof dashboardPerspectives] || dashboardPerspectives.Executive;
  const metrics = metricsByPerspective[role] || metricsByPerspective.Executive;

  const handleExport = () => {
    setShowExportModal(true);
  };

  const handleSelectContributor = async (item: ContributorItem, preferredPersona = role) => {
    try {
      setLoadingExplanationId(item.id);
      const response = await fetch(`/api/v1/quant/assets/${item.id}/explain?persona=${encodeURIComponent((preferredPersona || "executive").toLowerCase())}`);
      if (response.ok) {
        const payload = await response.json();
        setSelected({
          ...item,
          businessUnit: payload.business_unit,
          ealContributionCr: payload.eal_contribution_cr,
          var95Cr: payload.var_95_cr,
          explanation: payload.explanation,
          telemetrySource: payload.telemetry_source,
          lossBreakdown: payload.loss_breakdown,
          technicalDetails: payload.technical_details,
        });
        return;
      }
    } catch {
      // fall back to local metadata
    } finally {
      setLoadingExplanationId(null);
    }

    setSelected(item);
  };

  useEffect(() => {
    if (!selected) return;
    void handleSelectContributor(selected, role);
  }, [role]);

  const loadLiveTelemetry = async () => {
    try {
      const response = await fetch('/api/v1/telemetry/live-feed');
      if (!response.ok) return;
      const payload = await response.json();
      setTelemetryEvents(Array.isArray(payload) ? payload : []);
    } catch {
      // live feed is best-effort and should degrade silently
    }
  };

  const triggerAttackDrill = async (attackType: 'ddos' | 'ransomware' | 'credential_stuffing' = 'ddos') => {
    try {
      const response = await fetch('/api/v1/telemetry/trigger-drill', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ attack_type: attackType }),
      });
      if (!response.ok) throw new Error('drill trigger failed');
      const payload = await response.json();
      setAttackState({
        attack_active: payload.attack_active,
        attack_type: payload.attack_type,
        target_asset: payload.target_asset,
        eal_spike_cr: payload.eal_spike_cr,
      });
      setTelemetryEvents(Array.isArray(payload.live_events) ? payload.live_events : telemetryEvents);
      toast.warning(`Attack drill active: ${payload.attack_type ?? 'ddos'}` , { description: `Target asset ${payload.target_asset ?? 'N/A'} is in emergency response mode.` });
      await loadLiveTelemetry();
    } catch {
      toast.error('Attack drill trigger failed', { description: 'The backend did not accept the drill request.' });
    }
  };

  const resetAttackDrill = async () => {
    try {
      const response = await fetch('/api/v1/telemetry/reset-drill', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({}) });
      if (!response.ok) throw new Error('drill reset failed');
      const payload = await response.json();
      setAttackState({ attack_active: false, attack_type: null, target_asset: null, eal_spike_cr: 0 });
      setTelemetryEvents(Array.isArray(payload.live_events) ? payload.live_events : telemetryEvents);
      toast.success('Threat posture restored', { description: 'The drill has been neutralized and baseline thresholds restored.' });
      await loadLiveTelemetry();
    } catch {
      toast.error('Reset failed', { description: 'The drill state could not be cleared.' });
    }
  };

  useEffect(() => {
    void loadLiveTelemetry();
    const timer = window.setInterval(() => {
      void loadLiveTelemetry();
    }, 6000);
    return () => window.clearInterval(timer);
  }, []);

  const handleHandleAddBusinessUnit = () => {
    if (!buForm.name.trim()) {
      toast.error("Business unit name is required.");
      return;
    }

    const assetCount = Number(buForm.assetCount) || 0;
    const initialBudget = Number(buForm.initialBudget) || 0;
    const newBU = {
      id: Date.now(),
      name: buForm.name.trim(),
      unit: buForm.name.trim(),
      value: `₹${(initialBudget / 100).toFixed(2)} Cr`,
      amount: Math.max(8, Math.round(initialBudget / 3)),
      tone: "gold" as RiskTone,
      businessUnit: buForm.name.trim(),
      ealContributionCr: Number((initialBudget / 100).toFixed(2)),
      var95Cr: Number(((initialBudget * 1.7) / 100).toFixed(2)),
      explanation: `${buForm.name.trim()} is emerging as a new contributor to the enterprise exposure profile because its asset base and business criticality create a meaningful concentration of expected loss. Control coverage is still in the ramp-up phase, and the current environment leaves a few access and patching gaps unresolved. At a projected VaR of ₹${((initialBudget * 1.7) / 100).toFixed(2)} Cr, it is a material watchlist item for the next review cycle.`,
    };

    setContributors((current) => [newBU, ...current].slice(0, 5));
    setBuForm({ name: "", assetCount: "", initialBudget: "" });
    setShowAddBusinessUnit(false);
    toast.success("Business unit added", { description: `${buForm.name.trim()} was appended to the local model.` });
  };

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.metaKey && e.key === 'k') {
        e.preventDefault();
        toast("Global Search", { description: "Command Palette opened." });
      } else if (e.key === 'e' && e.ctrlKey) {
        e.preventDefault();
        handleExport();
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
            <div className="alert-dropdown-wrap">
              <button className="icon-button topbar-alert" onClick={() => setShowAlertDropdown((open) => !open)} aria-label="Open security alerts">
                <Bell size={16} />
              </button>
              {showAlertDropdown && (
                <div className="alert-dropdown">
                  <div className="alert-dropdown__header">
                    <span className="eyebrow">Critical alerts</span>
                    <strong>3 recent</strong>
                  </div>
                  {notificationAlerts.map((alert) => (
                    <div key={alert.title} className="alert-item">
                      <span className="alert-item__dot" />
                      <div>
                        <b>{alert.title}</b>
                        <p>{alert.detail}</p>
                        <small>{alert.time}</small>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
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
                  <span className="eyebrow eyebrow--gold">{role} dashboard</span>
                  <h1>{perspectiveMeta.headline}</h1>
                  <p>{perspectiveMeta.subhead}</p>
                </div>
                <div className="executive-actions">
                  <button className="secondary-button" onClick={() => setShowAddBusinessUnit(true)}>
                    <Plus size={14} />Add Business Unit
                  </button>
                  <button className="primary-button" onClick={handleExport}>
                    <Download size={14} />Export Board Deck (Ctrl+E)
                  </button>
                </div>
              </section>

              <section className={`metrics-grid ${!isLoading ? 'stagger-enter stagger-2' : ''}`}>
                {metrics.map((metric) => (
                  <MetricCard key={metric.label} label={metric.label} value={metric.value} suffix={metric.suffix} delta={metric.delta} deltaTone={metric.deltaTone} note={metric.note} icon={metric.icon} isLoading={isLoading} />
                ))}
              </section>

              {!isLoading && (
                <section className="terminal-card telemetry-card stagger-enter stagger-3" style={{ marginTop: 18 }}>
                  <div className="card-head">
                    <div>
                      <h2>Live telemetry stream</h2>
                      <span>{attackState.attack_active ? 'ATTACK DRILL ACTIVE' : 'SYNTHETIC SECURITY FEED'} · {telemetryEvents.length} EVENTS</span>
                    </div>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                      <button className="live-pill" onClick={() => void loadLiveTelemetry()}>
                        <span />{attackState.attack_active ? 'Live response active' : 'Live feed stable'}
                      </button>
                      {attackState.attack_active ? (
                        <button className="secondary-button" onClick={() => void resetAttackDrill()}>Reset drill</button>
                      ) : (
                        <div style={{ display: 'flex', gap: 8 }}>
                          <button className="secondary-button" onClick={() => void triggerAttackDrill('ddos')}>DDOS drill</button>
                          <button className="secondary-button" onClick={() => void triggerAttackDrill('ransomware')}>Ransomware drill</button>
                          <button className="secondary-button" onClick={() => void triggerAttackDrill('credential_stuffing')}>Cred stuffing</button>
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="telemetry-feed" style={{ display: 'grid', gap: 10, marginTop: 12 }}>
                    {telemetryEvents.length === 0 ? (
                      <div className="empty-state" style={{ padding: '20px 0', color: '#687483', fontSize: 11 }}>No live signals currently tracked.</div>
                    ) : (
                      telemetryEvents.slice(0, 5).map((event) => (
                        <div key={event.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, padding: '10px 12px', border: '1px solid rgba(120,135,151,0.15)', borderRadius: 10, background: 'rgba(11,18,26,0.4)' }}>
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                              <span style={{ fontSize: 10, color: '#d4ad61', textTransform: 'uppercase', letterSpacing: '.08em' }}>{event.severity}</span>
                              <span style={{ fontSize: 10, color: '#7f8ea3' }}>{event.source}</span>
                            </div>
                            <div style={{ fontSize: 12, fontWeight: 600, color: '#e7eef7' }}>{event.message}</div>
                          </div>
                          <div style={{ textAlign: 'right', minWidth: 120 }}>
                            <div style={{ fontSize: 10, color: '#7f8ea3', textTransform: 'uppercase', letterSpacing: '.08em' }}>{event.event_type}</div>
                            <div style={{ fontSize: 10, color: '#9bb0c1', marginTop: 6 }}>{new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                  {attackState.attack_active && (
                    <div style={{ marginTop: 12, padding: '10px 12px', borderRadius: 10, background: 'rgba(255, 94, 94, 0.08)', border: '1px solid rgba(239,133,141,0.2)', color: '#f2b0b5' }}>
                      Attack drill in progress · {attackState.attack_type} targeting {attackState.target_asset} · EAL spike +₹{attackState.eal_spike_cr ?? 0} Cr
                    </div>
                  )}
                </section>
              )}

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
                        contributors.slice(0, 5).map((item) => (
                          <button key={item.id || item.name} className="contributor-row" onClick={() => handleSelectContributor(item)}>
                            <span className="contributor-copy"><b>{item.name}</b><small>{item.unit}</small></span>
                            <strong>{item.value}</strong>
                            <span className="contributor-bar"><i style={{ width: `${Math.min((item.amount / 112) * 100, 100)}%` }} /></span>
                            {loadingExplanationId === item.id ? <span className="loading-indicator">…</span> : <ChevronRight size={13} />}
                          </button>
                        ))
                      )}
                    </div>
                  </article>
                  <InvestmentCurve budget={budget} setBudget={setBudget} onReviewBundle={() => selectNav("Investment Optimizer")} />
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
                      <button className="ghost-button" onClick={() => selectNav("Compliance Mapping")}>
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

      {selected && <EvidenceDrawer contributor={selected} onClose={() => setSelected(null)} persona={role} />}

      {showAddBusinessUnit && (
        <div className="drawer-scrim" onClick={() => setShowAddBusinessUnit(false)}>
          <aside className="modal-panel" onClick={(event) => event.stopPropagation()}>
            <div className="drawer-head">
              <div>
                <span className="eyebrow">Portfolio update</span>
                <h2>Add business unit</h2>
              </div>
              <button className="icon-button" onClick={() => setShowAddBusinessUnit(false)} aria-label="Close add business unit modal"><X size={17} /></button>
            </div>
            <div className="modal-form">
              <label>
                <span>BU Name</span>
                <input value={buForm.name} onChange={(e) => setBuForm((current) => ({ ...current, name: e.target.value }))} placeholder="e.g. Digital Infrastructure" />
              </label>
              <label>
                <span>Asset Count</span>
                <input value={buForm.assetCount} type="number" min="0" onChange={(e) => setBuForm((current) => ({ ...current, assetCount: e.target.value }))} placeholder="18" />
              </label>
              <label>
                <span>Initial Budget</span>
                <input value={buForm.initialBudget} type="number" min="0" step="0.01" onChange={(e) => setBuForm((current) => ({ ...current, initialBudget: e.target.value }))} placeholder="120.00" />
              </label>
            </div>
            <button className="primary-button primary-button--full" onClick={handleHandleAddBusinessUnit}>Save temporary record</button>
          </aside>
        </div>
      )}

      {showExportModal && (
        <div className="drawer-scrim" onClick={() => setShowExportModal(false)}>
          <aside className="modal-panel export-panel" onClick={(event) => event.stopPropagation()}>
            <div className="drawer-head">
              <div>
                <span className="eyebrow">Board-ready summary</span>
                <h2>Executive overview</h2>
              </div>
              <button className="icon-button" onClick={() => setShowExportModal(false)} aria-label="Close export modal"><X size={17} /></button>
            </div>
            <div className="export-summary">
              <div>
                <span>Enterprise risk score</span>
                <strong>73 / 100</strong>
              </div>
              <div>
                <span>EAL</span>
                <strong>₹4.82 Cr</strong>
              </div>
              <div>
                <span>95th pct VaR</span>
                <strong>₹9.15 Cr</strong>
              </div>
              <div>
                <span>Critical findings</span>
                <strong>17</strong>
              </div>
            </div>
            <div className="export-note">Ready for board review and formatted for export to PDF or print.</div>
            <button className="primary-button primary-button--full" onClick={() => { window.print(); setShowExportModal(false); }}>Print / Export</button>
          </aside>
        </div>
      )}
    </div>
  )
}

function Rail({ activeNav, onSelect, mobile = false }: { activeNav: string; onSelect: (label: string) => void; mobile?: boolean }) {
  return <aside className={`rail ${mobile ? "rail--mobile" : ""}`}><div className="rail-brand"><div className="rail-brand__mark">₹Q</div><div><b>CyberRiskIQ</b><span>SIH26105 · PROTOTYPE</span></div><button className="icon-button rail-close" onClick={() => onSelect(activeNav)} aria-label="Close navigation"><X size={15} /></button></div><div className="rail-org"><span className="org-avatar">AC</span><div><b>Acme Corp</b><small>BFSI demo instance</small></div><ChevronDown size={13} /></div>{navGroups.map((group) => <div className="rail-group" key={group.label}><span className="rail-label">{group.label}</span>{group.items.map(({ label, icon: Icon }) => <button key={label} className={`rail-item ${activeNav === label ? "is-active" : ""}`} onClick={() => onSelect(label)}><Icon size={15} strokeWidth={1.7} /><span>{label}</span>{label === "Investment Optimizer" && <i className="rail-count">3</i>}</button>)}</div>)}<div className="rail-foot"><span><span className="footer-live" />Synthetic feed · Acme Corp</span><small>Refreshed 4 min ago</small></div></aside>;
}
