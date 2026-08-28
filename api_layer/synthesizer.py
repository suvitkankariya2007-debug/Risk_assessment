import json
from typing import Any, Optional
from schemas.data_models import (
    DeterministicContextPayload,
    PersonaType,
    AssetNode,
    FAIROutput,
    MILPROSIOutput,
    EPSSOutput,
    XAIOutput,
)


class DeterministicExecutionAggregator:
    def aggregate(
        self,
        session_id: str,
        persona: PersonaType,
        slots: Any,
        asset: Optional[AssetNode] = None,
        epss: Optional[EPSSOutput] = None,
        fair: Optional[FAIROutput] = None,
        xai: Optional[XAIOutput] = None,
        milprosi: Optional[MILPROSIOutput] = None,
        compliance_controls: Optional[list] = None,
    ) -> DeterministicContextPayload:
        payload = DeterministicContextPayload(
            session_id=session_id,
            persona=persona,
            timestamp=__import__("datetime").datetime.utcnow().isoformat() + "Z",
            slots=slots,
            asset=asset,
            epss=epss,
            fair=fair,
            xai=xai,
            milprosi=milprosi,
            compliance_controls=compliance_controls or [],
            guardrail_passed=True,
            guardrail_errors=[],
        )
        return payload


class ExecutivePromptFormatter:
    def format(self, payload: DeterministicContextPayload) -> str:
        fair = payload.fair
        milprosi = payload.milprosi
        asset = payload.asset
        epss = payload.epss

        lines = [
            "EXECUTIVE RISK BRIEF",
            f"Asset: {asset.name if asset else 'N/A'}",
        ]
        if epss:
            lines.append(f"Exploit Likelihood: {epss.p_exploit:.1%}")
        if fair:
            lines.append(f"Expected Annual Loss: ₹{fair.eal_inr_cr:.2f} Cr")
            lines.append(f"95% Value-at-Risk: ₹{fair.var_95_inr_cr:.2f} Cr")
            lines.append(f"Primary Loss: ₹{fair.primary_loss_inr_cr:.2f} Cr")
            lines.append(f"Secondary Loss: ₹{fair.secondary_loss_inr_cr:.2f} Cr")
        if milprosi:
            lines.append(f"Risk Reduced: ₹{milprosi.risk_reduced_inr_cr:.2f} Cr")
            lines.append(f"ROSI: {milprosi.rosi_pct:.1f}%")
            lines.append(f"Net Capital Saved: ₹{milprosi.net_capital_saved_inr_cr:.2f} Cr")
            lines.append(f"Control Cost: ₹{milprosi.control_cost_inr_cr:.2f} Cr")
            lines.append(f"Gordon-Loeb Ceiling: ₹{milprosi.gordon_loeb_ceiling_inr_cr:.2f} Cr")
            lines.append(f"Economically Viable: {'Yes' if milprosi.is_economically_viable else 'No'}")
        if fair and milprosi:
            lines.append(
                f"Why Risk is Critical: Downtime exposure of ₹{fair.primary_loss_inr_cr:.2f} Cr "
                f"combined with regulatory fines amplifying secondary losses to ₹{fair.secondary_loss_inr_cr:.2f} Cr."
            )
        return "\n".join(lines)


class TechnicalDiagnosticFormatter:
    def format(self, payload: DeterministicContextPayload) -> str:
        fair = payload.fair
        milprosi = payload.milprosi
        epss = payload.epss
        xai = payload.xai
        asset = payload.asset

        lines = [
            "TECHNICAL DIAGNOSTIC REPORT",
            f"Asset ID: {asset.asset_id if asset else 'N/A'}",
        ]
        if epss:
            lines.append(f"CVE: {epss.cve_id}")
            lines.append(f"EPSS P(Exploit): {epss.p_exploit:.6f}")
            lines.append(f"Z-Score: {epss.z_score:.4f}")
            lines.append(f"Feature Contributions: {json.dumps(epss.feature_contributions)}")
        if fair:
            lines.append(f"LEF: {fair.lef:.6f}")
            lines.append(f"EAL: ₹{fair.eal_inr_cr:.4f} Cr")
            lines.append(f"VaR 95%: ₹{fair.var_95_inr_cr:.4f} Cr")
            lines.append(f"Primary Loss: ₹{fair.primary_loss_inr_cr:.4f} Cr")
            lines.append(f"Secondary Loss: ₹{fair.secondary_loss_inr_cr:.4f} Cr")
        if xai:
            lines.append(f"XAI Trust Score: {xai.trust_score_pct:.1f}%")
            lines.append(f"IQR Threshold: {xai.iqr_threshold:.4f}")
            lines.append(f"Flags: {xai.flags_status}")
            lines.append(f"Misaligned Tokens: {json.dumps(xai.misaligned_tokens)}")
        if milprosi:
            lines.append(f"Risk Reduced: ₹{milprosi.risk_reduced_inr_cr:.4f} Cr")
            lines.append(f"ROSI: {milprosi.rosi_pct:.2f}%")
            lines.append(f"Net Capital Saved: ₹{milprosi.net_capital_saved_inr_cr:.4f} Cr")
            lines.append(f"Control Cost: ₹{milprosi.control_cost_inr_cr:.4f} Cr")
            lines.append(f"Gordon-Loeb Ceiling: ₹{milprosi.gordon_loeb_ceiling_inr_cr:.4f} Cr")
            lines.append(f"Economically Viable: {milprosi.is_economically_viable}")
        lines.append("WAF Rule: drop tcp any any -> any any (msg:\"EXPLOIT BLOCK\")")
        lines.append("Jira: { \"project\": \"SEC\", \"issuetype\": \"Task\", \"priority\": \"High\" }")
        return "\n".join(lines)


class PromptSynthesizers:
    def __init__(self) -> None:
        self.aggregator = DeterministicExecutionAggregator()
        self.exec_formatter = ExecutivePromptFormatter()
        self.tech_formatter = TechnicalDiagnosticFormatter()

    def synthesize(self, payload: DeterministicContextPayload) -> str:
        if payload.persona == PersonaType.BUSINESS:
            return self.exec_formatter.format(payload)
        return self.tech_formatter.format(payload)
