import { Download } from "lucide-react";
import { useCountUp } from "../../hooks/useCountUp";

function AnimatedPercent({ value }: { value: number }) {
  const animated = useCountUp(value, 1000);
  return <strong>{animated.toFixed(0)}%</strong>;
}

const frameworks = [
  { name: "ISO 27001", subtitle: "Annex A controls", score: 82 },
  { name: "NIST CSF 2.0", subtitle: "Core functions", score: 76 },
  { name: "CIS Controls v8", subtitle: "Safeguards", score: 88 },
  { name: "RBI CSF", subtitle: "Cyber security framework", score: 69 },
  { name: "SEBI CSCRF", subtitle: "Cyber & resilience framework", score: 71 },
];

const controls = [
  { id: 1, name: "Privileged access MFA", iso: "A.9.4", nist: "PR.AC-7", cis: "6.5", rbi: "4.1", sebi: "5.3", status: "Evidenced", tone: "green" },
  { id: 2, name: "Critical patch SLA (7d)", iso: "A.12.6", nist: "ID.RA-1", cis: "7.3", rbi: "3.2", sebi: "6.1", status: "Evidenced", tone: "green" },
  { id: 3, name: "Backup encryption at rest", iso: "A.10.1", nist: "PR.DS-1", cis: "3.11", rbi: "4.2", sebi: "5.7", status: "Partial", tone: "gold" },
  { id: 4, name: "Network segmentation — payments", iso: "A.13.1", nist: "PR.AC-5", cis: "12.2", rbi: "5.4", sebi: "6.4", status: "Gap", tone: "red" },
];

export default function ComplianceMapping() {
  return (
    <section className="section-container stagger-enter stagger-1">
      <div className="section-header">
        <div>
          <span className="eyebrow eyebrow--gold">COMPLIANCE MAPPING</span>
          <h1>One control, five frameworks</h1>
          <p>Every control maps automatically to the clauses it satisfies — the same dashboard doubles as an audit artifact.</p>
        </div>
        <button className="primary-button"><Download size={14} /> Export audit report</button>
      </div>

      <div className="framework-grid">
        {frameworks.map((f, i) => (
          <div key={f.name} className={`terminal-card framework-card stagger-enter stagger-${i + 2}`}>
            <b>{f.name}</b>
            <span>{f.subtitle}</span>
            <div className="framework-score">
              <AnimatedPercent value={f.score} />
              <small>mapped & evidenced</small>
            </div>
          </div>
        ))}
        <div className="terminal-card framework-card framework-card--overall stagger-enter stagger-5">
          <b>Overall posture</b>
          <span>weighted average</span>
          <div className="framework-score">
            <strong className="text-green"><AnimatedPercent value={77} /></strong>
            <small>audit-ready</small>
          </div>
        </div>
      </div>

      <div className="table-header stagger-enter stagger-5">
        <h2>Control → clause mapping</h2>
        <span>SAMPLE OF 214 MAPPED CONTROLS</span>
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
            {controls.map((item) => (
              <tr key={item.id}>
                <td className="font-medium text-light">{item.name}</td>
                <td className="text-muted">{item.iso}</td>
                <td className="text-muted">{item.nist}</td>
                <td className="text-muted">{item.cis}</td>
                <td className="text-muted">{item.rbi}</td>
                <td className="text-muted">{item.sebi}</td>
                <td>
                  <span className={`status-badge status-badge--${item.status.toLowerCase()}`}>
                    <span className={`status-dot bg-${item.tone}`}></span>
                    {item.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
