import { Download, ShieldCheck, TriangleAlert, XCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useCountUp } from "../../hooks/useCountUp";

type FrameworkScore = {
  name: string;
  subtitle: string;
  score: number;
};

type ControlItem = {
  id: string;
  name: string;
  iso_27001: string;
  nist_csf: string;
  cis_v8: string;
  rbi_csf: string;
  sebi_cscrf: string;
  status: "EVIDENCED" | "PARTIAL" | "GAP";
  coverage_pct: number;
  penalty_risk_cr: number;
  recommended_action: string;
  policy_template_title: string;
};

const frameworkMeta: Record<string, string> = {
  "ISO 27001": "Annex A controls",
  "NIST CSF": "Core functions",
  "CIS Controls": "Safeguards",
  "RBI CSF": "Cyber security framework",
  "SEBI CSCRF": "Cyber & resilience framework",
  "Overall": "Weighted average",
};

function AnimatedPercent({ value }: { value: number }) {
  const animated = useCountUp(value, 1000);
  return <strong>{animated.toFixed(0)}%</strong>;
}

function formatCurrencyLakh(value: number) {
  return `₹${value.toFixed(2)}L`;
}

export default function ComplianceMapping() {
  const [frameworks, setFrameworks] = useState<FrameworkScore[]>([]);
  const [controls, setControls] = useState<ControlItem[]>([]);
  const [selectedControl, setSelectedControl] = useState<ControlItem | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadComplianceData = async () => {
      try {
        const [frameworkResponse, matrixResponse] = await Promise.all([
          fetch("/api/v1/compliance/frameworks"),
          fetch("/api/v1/compliance/matrix"),
        ]);

        if (!frameworkResponse.ok || !matrixResponse.ok) {
          throw new Error("Compliance data request failed");
        }

        const frameworkPayload = (await frameworkResponse.json()) as Record<string, number>;
        const matrixPayload = (await matrixResponse.json()) as { controls?: ControlItem[] };

        const nextFrameworks = Object.entries(frameworkPayload).map(([name, score]) => ({
          name,
          subtitle: frameworkMeta[name] ?? "Control coverage",
          score: Number(score),
        }));

        setFrameworks(nextFrameworks);
        setControls(matrixPayload.controls ?? []);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    };

    loadComplianceData();
  }, []);

  const statusMap = useMemo(
    () => ({
      EVIDENCED: { className: "status-badge--evidenced", icon: "🟢", label: "EVIDENCED" },
      PARTIAL: { className: "status-badge--partial", icon: "🟡", label: "PARTIAL" },
      GAP: { className: "status-badge--gap", icon: "🔴", label: "GAP" },
    }),
    [],
  );

  const handleExportAuditReport = async () => {
    try {
      const response = await fetch("/api/v1/compliance/export-report");
      if (!response.ok) {
        throw new Error("Failed to export report");
      }
      const payload = (await response.json()) as { file_name?: string; report?: string };
      const fileName = payload.file_name ?? "compliance-readiness-report.txt";
      const reportText = payload.report ?? JSON.stringify(payload, null, 2);
      const blob = new Blob([reportText], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = fileName;
      anchor.click();
      URL.revokeObjectURL(url);
      window.print();
    } catch (error) {
      console.error(error);
      window.print();
    }
  };

  const handleTemplateDownload = (control: ControlItem) => {
    const reportText = [
      `Compliance SOP Template: ${control.policy_template_title}`,
      `Control: ${control.name}`,
      `Status: ${control.status}`,
      `Coverage: ${control.coverage_pct}%`,
      "",
      "Required remediation:",
      control.recommended_action,
    ].join("\n");

    const blob = new Blob([reportText], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = control.policy_template_title;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="section-container stagger-enter stagger-1">
      <div className="section-header">
        <div>
          <span className="eyebrow eyebrow--gold">COMPLIANCE MAPPING</span>
          <h1>One control, five frameworks</h1>
          <p>Every control maps automatically to the clauses it satisfies — the same dashboard doubles as an audit artifact.</p>
        </div>
        <button className="primary-button" onClick={handleExportAuditReport} type="button">
          <Download size={14} /> Export audit report
        </button>
      </div>

      <div className="framework-grid">
        {frameworks.map((framework, index) => (
          <div key={framework.name} className={`terminal-card framework-card stagger-enter stagger-${index + 2}`}>
            <b>{framework.name}</b>
            <span>{framework.subtitle}</span>
            <div className="framework-score">
              <AnimatedPercent value={framework.score} />
              <small>mapped & evidenced</small>
            </div>
            <div className="progress-bar">
              <span style={{ width: `${framework.score}%` }} />
            </div>
          </div>
        ))}
      </div>

      <div className="table-header stagger-enter stagger-5">
        <h2>Control → clause mapping</h2>
        <span>{loading ? "LOADING CONTROLS" : `${controls.length} MAPPED CONTROLS`}</span>
      </div>

      <div className="terminal-card table-card stagger-enter stagger-5">
        <table className="data-table">
          <thead>
            <tr>
              <th>CONTROL</th>
              <th>ISO 27001</th>
              <th>NIST CSF</th>
              <th>CIS V8</th>
              <th>RBI CSF</th>
              <th>SEBI CSCRF</th>
              <th>STATUS</th>
            </tr>
          </thead>
          <tbody>
            {controls.map((item) => {
              const status = statusMap[item.status];
              return (
                <tr key={item.id} className="compliance-row" onClick={() => setSelectedControl(item)}>
                  <td className="font-medium text-light">{item.name}</td>
                  <td className="text-muted">{item.iso_27001}</td>
                  <td className="text-muted">{item.nist_csf}</td>
                  <td className="text-muted">{item.cis_v8}</td>
                  <td className="text-muted">{item.rbi_csf}</td>
                  <td className="text-muted">{item.sebi_cscrf}</td>
                  <td>
                    <span className={`status-badge ${status.className}`}>
                      <span className="status-icon">{status.icon}</span>
                      {status.label}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {selectedControl && (
        <div className="compliance-drawer-backdrop" onClick={() => setSelectedControl(null)}>
          <aside className="compliance-drawer" onClick={(event) => event.stopPropagation()}>
            <div className="compliance-drawer-header">
              <div>
                <span className="decision-kicker">Control detail</span>
                <h3>{selectedControl.name}</h3>
              </div>
              <button type="button" className="close-button" onClick={() => setSelectedControl(null)}>
                ×
              </button>
            </div>

            <div className="drawer-grid">
              <div className="drawer-block">
                <h4>Clause mapping</h4>
                <ul>
                  <li><strong>ISO 27001:</strong> {selectedControl.iso_27001}</li>
                  <li><strong>NIST CSF:</strong> {selectedControl.nist_csf}</li>
                  <li><strong>CIS v8:</strong> {selectedControl.cis_v8}</li>
                  <li><strong>RBI CSF:</strong> {selectedControl.rbi_csf}</li>
                  <li><strong>SEBI CSCRF:</strong> {selectedControl.sebi_cscrf}</li>
                </ul>
              </div>

              <div className="drawer-block">
                <h4>Evidence status</h4>
                <div className="status-strip">
                  <span className={`status-badge ${statusMap[selectedControl.status].className}`}>
                    <span className="status-icon">{statusMap[selectedControl.status].icon}</span>
                    {statusMap[selectedControl.status].label}
                  </span>
                  <span className="coverage-pill">Coverage: {selectedControl.coverage_pct}%</span>
                </div>
                <p className="risk-value">Regulatory penalty risk: {formatCurrencyLakh(selectedControl.penalty_risk_cr * 100)}</p>
              </div>
            </div>

            <div className="drawer-block">
              <h4>Actionable remediation plan</h4>
              <ol>
                {selectedControl.recommended_action.split(/(?<=\.\s)/).map((step, index) => (
                  <li key={`${selectedControl.id}-${index}`}>{step.trim()}</li>
                ))}
              </ol>
            </div>

            <div className="drawer-actions">
              <button type="button" className="primary-button" onClick={() => handleTemplateDownload(selectedControl)}>
                <Download size={14} /> Download standing audit SOP
              </button>
            </div>
          </aside>
        </div>
      )}
    </section>
  );
}
