"""
api_layer/scan_ledger.py
=========================
In-memory ScanLedger for dynamic vulnerability scan ingestion.

Accepts JSON or CSV uploads from Qualys/Tenable/CrowdStrike scan exports,
parses findings, and caches them for real-time CVE + Asset lookup by the
chat routes.  Chat endpoints query the ledger FIRST; if no scan is loaded
they fall back to the static mock_kb baseline.
"""
import csv
import io
import json
import os
import re
import sqlite3
import threading
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


# ── Finding Schema ──────────────────────────────────────────────────────────
class ScanFinding(BaseModel):
    finding_id: str
    cve_id: str
    asset_name: str
    vendor: str = "unknown"
    cvss_score: float = 0.0
    cvss_vector: str = ""
    tags: List[str] = []
    exploit_weaponized: bool = False
    poc_published: bool = False
    reference_count: int = 0
    description: str = ""
    severity: str = "medium"
    ingested_at: str = ""


class ScanUploadResponse(BaseModel):
    status: str
    findings_ingested: int
    total_findings: int
    scan_id: str


# ── Ledger Singleton ────────────────────────────────────────────────────────
class ScanLedger:
    """Thread-safe scan-findings cache with SQLite write-through persistence.

    In-memory dicts remain the hot-path read source (no disk round-trip on
    the request path). Uploaded findings survive server restarts via the
    SQLite database, which is loaded once at process startup.
    """

    def __init__(self) -> None:
        self._findings: List[ScanFinding] = []
        self._by_cve: Dict[str, ScanFinding] = {}
        self._by_asset: Dict[str, List[ScanFinding]] = {}
        self.scan_count: int = 0
        self._lock = threading.RLock()
        # Phase 0c: persistence layer (SQLite file; path overridable via env)
        self._db_path = os.environ.get(
            "SCAN_LEDGER_DB",
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scan_ledger.db"),
        )
        self._init_db()
        self._load_from_db()

    # ── Persistence helpers ─────────────────────────────────────────────────
    def _init_db(self) -> None:
        try:
            con = sqlite3.connect(self._db_path)
            try:
                con.execute(
                    "CREATE TABLE IF NOT EXISTS scan_findings ("
                    " cve_id TEXT PRIMARY KEY, payload TEXT NOT NULL,"
                    " ingested_at TEXT NOT NULL)"
                )
                con.commit()
            finally:
                con.close()
        except Exception:
            # Persistence is best-effort; the in-memory ledger keeps working.
            pass

    def _load_from_db(self) -> None:
        try:
            con = sqlite3.connect(self._db_path)
            try:
                rows = con.execute(
                    "SELECT payload FROM scan_findings"
                ).fetchall()
            finally:
                con.close()
            for (payload_json,) in rows:
                try:
                    f = ScanFinding(**json.loads(payload_json))
                    self._findings.append(f)
                    self._by_cve[f.cve_id.upper()] = f
                    key = f.asset_name.lower().strip()
                    self._by_asset.setdefault(key, []).append(f)
                except Exception:
                    continue
        except Exception:
            pass

    def _persist(self, f: ScanFinding) -> None:
        try:
            con = sqlite3.connect(self._db_path)
            try:
                con.execute(
                    "INSERT OR REPLACE INTO scan_findings"
                    " (cve_id, payload, ingested_at) VALUES (?, ?, ?)",
                    (f.cve_id.upper(), f.model_dump_json(), f.ingested_at),
                )
                con.commit()
            finally:
                con.close()
        except Exception:
            pass

    # ── Query API ───────────────────────────────────────────────────────────
    @property
    def is_loaded(self) -> bool:
        return len(self._findings) > 0

    def lookup_cve(self, cve_id: str) -> Optional[Dict[str, Any]]:
        """Return mock_kb-compatible dict for a CVE, or None if not found."""
        f = self._by_cve.get(cve_id.upper())
        if not f:
            return None
        return {
            "vendor": f.vendor,
            "tags": f.tags,
            "exploit_weaponized": f.exploit_weaponized,
            "poc_published": f.poc_published,
            "reference_count": f.reference_count,
            "description": f.description,
            "cvss_score": f.cvss_score,
            "cvss_vector": f.cvss_vector,
        }

    def lookup_finding(self, cve_id: str) -> Optional[ScanFinding]:
        """Return the raw ScanFinding for a CVE, or None if not found."""
        return self._by_cve.get(cve_id.upper())

    def lookup_asset(self, asset_name: str) -> Optional[List[ScanFinding]]:
        """Return all findings for a given asset name."""
        key = asset_name.lower().strip()
        return self._by_asset.get(key)

    def list_findings(self) -> List[Dict[str, Any]]:
        return [f.model_dump() for f in self._findings[-50:]]

    def clear(self) -> None:
        self._findings.clear()
        self._by_cve.clear()
        self._by_asset.clear()
        self.scan_count = 0
        try:
            con = sqlite3.connect(self._db_path)
            try:
                con.execute("DELETE FROM scan_findings")
                con.commit()
            finally:
                con.close()
        except Exception:
            pass

    # ── Ingestion ───────────────────────────────────────────────────────────
    def ingest_json(self, raw: Any) -> int:
        """Parse JSON scan data. Accepts list of dicts or a dict with 'findings' key."""
        findings_list: List[dict] = []
        if isinstance(raw, list):
            findings_list = raw
        elif isinstance(raw, dict):
            findings_list = raw.get("findings") or raw.get("vulnerabilities") or raw.get("results") or [raw]
        else:
            return 0

        count = 0
        for item in findings_list:
            f = self._normalize_finding(item)
            if f:
                self._add(f)
                count += 1
        self.scan_count += 1
        return count

    def ingest_csv(self, csv_text: str) -> int:
        """Parse CSV scan data (Qualys/Tenable-style headers)."""
        reader = csv.DictReader(io.StringIO(csv_text))
        count = 0
        for row in reader:
            f = self._normalize_finding(row)
            if f:
                self._add(f)
                count += 1
        self.scan_count += 1
        return count

    def _add(self, f: ScanFinding) -> None:
        self._findings.append(f)
        self._by_cve[f.cve_id.upper()] = f
        key = f.asset_name.lower().strip()
        self._by_asset.setdefault(key, []).append(f)
        # Write-through persistence (memory stays the hot read path)
        self._persist(f)

    def _normalize_finding(self, item: dict) -> Optional[ScanFinding]:
        """Normalize heterogeneous scan export formats into ScanFinding."""
        cve_id = (
            item.get("cve_id")
            or item.get("cve")
            or item.get("CVE ID")
            or item.get("CVE")
            or item.get("vulnerability_id")
            or ""
        ).strip().upper()

        if not cve_id or not re.match(r"CVE-\d{4}-\d{4,7}", cve_id):
            return None

        asset = (
            item.get("asset_name")
            or item.get("asset")
            or item.get("host")
            or item.get("hostname")
            or item.get("Asset Name")
            or "Unknown Asset"
        )
        vendor = (
            item.get("vendor")
            or item.get("Vendor")
            or item.get("plugin_family")
            or "unknown"
        )
        tags_raw = item.get("tags") or item.get("Tags") or item.get("labels") or []
        if isinstance(tags_raw, str):
            tags_raw = [t.strip() for t in tags_raw.split(",")]

        cvss_vector = str(
            item.get("cvss_vector")
            or item.get("vector")
            or item.get("CVSS Vector")
            or item.get("V3 Vector")
            or ""
        ).strip()

        try:
            cvss = float(item.get("cvss_score") or item.get("cvss_base_score") or item.get("cvss") or item.get("CVSS Score") or 0)
        except (ValueError, TypeError):
            cvss = 0.0

        weaponized = _to_bool(item.get("exploit_weaponized") or item.get("weaponized") or False)
        poc = _to_bool(item.get("poc_published") or item.get("poc") or item.get("exploit_available") or False)

        try:
            ref_count = int(item.get("reference_count") or item.get("references") or 0)
        except (ValueError, TypeError):
            ref_count = 0

        description = str(item.get("description") or item.get("summary") or item.get("Synopsis") or "")
        severity = str(item.get("severity") or item.get("Severity") or "medium").lower()

        return ScanFinding(
            finding_id=str(uuid.uuid4())[:8],
            cve_id=cve_id,
            asset_name=asset,
            vendor=vendor,
            cvss_score=cvss,
            cvss_vector=cvss_vector,
            tags=tags_raw,
            exploit_weaponized=weaponized,
            poc_published=poc,
            reference_count=ref_count,
            description=description,
            severity=severity,
            ingested_at=datetime.utcnow().isoformat() + "Z",
        )


def _to_bool(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("true", "1", "yes", "y")
    return bool(val)


# ── Module-level singleton ──────────────────────────────────────────────────
scan_ledger = ScanLedger()
