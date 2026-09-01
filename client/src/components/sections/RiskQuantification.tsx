import { useState, useMemo, useRef, useEffect, Fragment } from "react";
import { ChevronUp, ChevronDown, ChevronsUpDown } from "lucide-react";

interface Asset {
  id: number;
  name: string;
  business_unit: string;
  criticality: "Critical" | "High" | "Medium" | "Low";
  eal_lakhs: number;
  var_95_lakhs: number;
  control_efficiency: number;
}

interface MonteCarloResult {
  asset_id: number;
  asset_name: string;
  business_unit: string;
  criticality: string;
  mean_loss_lakhs: number;
  p95_loss_lakhs: number;
  p99_loss_lakhs: number;
  trials: number;
  distribution: number[];
  control_efficiency: number;
}

const BUSINESS_UNIT_FILTERS = [
  { key: "ALL", label: "ALL BUSINESS UNITS" },
  { key: "CORE BANKING", label: "CORE BANKING" },
  { key: "PAYMENTS", label: "PAYMENTS" },
  { key: "CARDS & LENDING", label: "CARDS & LENDING" },
  { key: "CORPORATE IT", label: "CORPORATE IT" },
] as const;

const VIEW_MODES = ["ORG", "BUSINESS UNIT", "ASSET"] as const;
type ViewMode = (typeof VIEW_MODES)[number];
type SortKey = "name" | "eal" | "var95" | "eff";
type SortDir = "asc" | "desc";

const fmtCurrencyLakh = (value: number) => {
  if (!Number.isFinite(value)) return "₹0.00L";
  if (value >= 100) return `₹${(value / 100).toFixed(2)}Cr`;
  return `₹${value.toFixed(1)}L`;
};

const fmtCr = (value: number) => `₹${(value || 0).toFixed(2)}Cr`;
const critColor: Record<string, string> = { Critical: "#ef858d", High: "var(--gold)", Medium: "#f2c86f", Low: "#51d1a1" };

const buildSyntheticHistogram = (items: Asset[]) => {
  const bins = Array.from({ length: 30 }, () => 0);
  if (!items.length) return bins;

  items.forEach((asset) => {
    const avg = Math.max(asset.eal_lakhs / 100, 0.25);
    const var95 = Math.max(asset.var_95_lakhs / 100, 0.5);
    const controlWeight = 1 + asset.control_efficiency / 100;

    bins.forEach((_, index) => {
      const x = (index / bins.length) * Math.max(var95 * 3, 2.5);
      const spread = Math.max(0.25, var95 / 4.5);
      const density = Math.exp(-((x - avg) ** 2) / (2 * spread ** 2));
      bins[index] += density * controlWeight;
    });
  });

  const maxValue = Math.max(...bins, 1);
  return bins.map((value) => value / maxValue);
};

export default function RiskQuantification() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [viewMode, setViewMode] = useState<ViewMode>("ASSET");
  const [activeBuFilter, setActiveBuFilter] = useState<string>("ALL");
  const [selectedAssetId, setSelectedAssetId] = useState<string>("core-pay-db-01");
  const [sortKey, setSortKey] = useState<SortKey>("eal");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [mc, setMc] = useState<MonteCarloResult | null>(null);
  const barsRef = useRef<HTMLDivElement>(null);
  const [barsVisible, setBarsVisible] = useState(false);

  useEffect(() => {
    const fetchAssets = async () => {
      const response = await fetch("/api/v1/quant/assets");
      const data = (await response.json()) as Asset[];
      setAssets(data);
      if (data[0]) setSelectedAssetId(String(data[0].name));
    };

    fetchAssets();
  }, []);

  useEffect(() => {
    if (!selectedAssetId || viewMode !== "ASSET") return;

    const fetchMonteCarlo = async () => {
      try {
        const response = await fetch(`/api/v1/quant/monte-carlo/${selectedAssetId}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ trials: 50000 }),
        });

        if (!response.ok) throw new Error(`Monte Carlo fetch failed: ${response.status}`);
        const data = (await response.json()) as MonteCarloResult;
        setMc(data);
      } catch {
        setMc(null);
      }
    };

    fetchMonteCarlo();
  }, [selectedAssetId, viewMode]);

  useEffect(() => {
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) setBarsVisible(true);
    }, { threshold: 0.1 });

    if (barsRef.current) obs.observe(barsRef.current);
    return () => obs.disconnect();
  }, [mc, viewMode]);

  const filteredAssets = useMemo(() => {
    const list = activeBuFilter === "ALL"
      ? assets
      : assets.filter((asset) => asset.business_unit.toUpperCase() === activeBuFilter);

    return [...list].sort((a, b) => {
      let comparison = 0;
      if (sortKey === "name") comparison = a.name.localeCompare(b.name);
      else if (sortKey === "eal") comparison = a.eal_lakhs - b.eal_lakhs;
      else if (sortKey === "var95") comparison = a.var_95_lakhs - b.var_95_lakhs;
      else comparison = a.control_efficiency - b.control_efficiency;
      return sortDir === "asc" ? comparison : -comparison;
    });
  }, [assets, activeBuFilter, sortKey, sortDir]);

  const selectedAsset = useMemo(
    () => assets.find((asset) => asset.name === selectedAssetId || String(asset.id) === selectedAssetId) ?? assets[0],
    [assets, selectedAssetId]
  );

  const businessUnitSummaries = useMemo(() => {
    const groups = new Map<string, Asset[]>();

    filteredAssets.forEach((asset) => {
      const bucket = asset.business_unit;
      groups.set(bucket, [...(groups.get(bucket) ?? []), asset]);
    });

    return Array.from(groups.entries()).map(([businessUnit, items]) => {
      const totalEal = items.reduce((sum, asset) => sum + asset.eal_lakhs, 0);
      const totalVar95 = items.reduce((sum, asset) => sum + asset.var_95_lakhs, 0);
      const averageControl = items.reduce((sum, asset) => sum + asset.control_efficiency, 0) / items.length;

      return {
        businessUnit,
        assetCount: items.length,
        totalEal,
        totalVar95,
        averageControl,
      };
    });
  }, [filteredAssets]);

  const orgSummary = useMemo(() => {
    const totalEal = assets.reduce((sum, asset) => sum + asset.eal_lakhs, 0);
    const totalVar95 = assets.reduce((sum, asset) => sum + asset.var_95_lakhs, 0);
    const averageControl = assets.reduce((sum, asset) => sum + asset.control_efficiency, 0) / (assets.length || 1);
    return {
      name: "Acme Corp Org-wide Rollup",
      assetCount: assets.length,
      totalEal,
      totalVar95,
      averageControl,
    };
  }, [assets]);

  const dataRows = useMemo(() => {
    if (viewMode === "ASSET") return filteredAssets;
    if (viewMode === "BUSINESS UNIT") return businessUnitSummaries;
    return [orgSummary];
  }, [businessUnitSummaries, filteredAssets, orgSummary, viewMode]);

  const chartData = useMemo(() => {
    if (viewMode === "ASSET") {
      const selected = assets.find((asset) => asset.name === selectedAssetId || String(asset.id) === selectedAssetId);
      if (selected) return buildSyntheticHistogram([selected]);
      return buildSyntheticHistogram(filteredAssets);
    }

    if (viewMode === "BUSINESS UNIT") {
      const groupAssets = activeBuFilter === "ALL" ? assets : assets.filter((asset) => asset.business_unit.toUpperCase() === activeBuFilter);
      return buildSyntheticHistogram(groupAssets);
    }

    return buildSyntheticHistogram(assets);
  }, [activeBuFilter, assets, filteredAssets, selectedAssetId, viewMode]);

  const histogramMax = Math.max(0.0001, ...chartData);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((prev) => (prev === "asc" ? "desc" : "asc"));
    else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const SortIcon = ({ keyName }: { keyName: SortKey }) =>
    sortKey === keyName ? (sortDir === "asc" ? <ChevronUp size={10} /> : <ChevronDown size={10} />) : <ChevronsUpDown size={10} style={{ opacity: 0.4 }} />;

  if (!assets.length) {
    return <section className="section-container"><div className="terminal-card">Loading asset risk data...</div></section>;
  }

  const meanLossCr = (mc?.mean_loss_lakhs ?? selectedAsset?.eal_lakhs ?? 0) / 100;
  const p95VarCr = (mc?.p95_loss_lakhs ?? selectedAsset?.var_95_lakhs ?? 0) / 100;
  const p99LossCr = (mc?.p99_loss_lakhs ?? (selectedAsset?.var_95_lakhs ?? 0) * 1.2 ?? 0) / 100;

  return (
    <section className="section-container stagger-enter stagger-1">
      <div className="section-header">
        <div>
          <span className="eyebrow eyebrow--gold">RISK QUANTIFICATION ENGINE</span>
          <h1>EAL &amp; VaR, from asset to org</h1>
          <p>FAIR-style Monte Carlo over loss-event frequency × vulnerability × impact magnitude, rolled up by asset, business unit and org.</p>
        </div>
      </div>

      <div className="view-toggles">
        <div className="segmented-control">
          {VIEW_MODES.map((mode) => (
            <button key={mode} className={`segment ${viewMode === mode ? "active" : ""}`} onClick={() => setViewMode(mode)}>
              {mode}
            </button>
          ))}
        </div>
        <span className="text-muted text-xs" style={{ marginLeft: 16, lineHeight: "34px" }}>
          {viewMode === "ORG" ? "Organisation-wide rollup" : viewMode === "BUSINESS UNIT" ? "Grouped by business unit" : "Individual asset view"}
        </span>
      </div>

      <div className="filter-tags">
        {BUSINESS_UNIT_FILTERS.map((filter) => (
          <button
            key={filter.key}
            className={`filter-tag ${activeBuFilter === filter.key ? "active" : ""}`}
            onClick={() => setActiveBuFilter(filter.key)}
          >
            {filter.label}
            {filter.key !== "ALL" && (
              <span style={{ marginLeft: 6, opacity: 0.6 }}>
                ({assets.filter((asset) => asset.business_unit.toUpperCase() === filter.key).length})
              </span>
            )}
          </button>
        ))}
      </div>

      <div className="quantification-grid">
        <div className="terminal-card asset-register stagger-enter stagger-2">
          <div className="card-head mb-4">
            <div>
              <h2>Asset risk register</h2>
              <span>
                {viewMode === "ASSET" && `${filteredAssets.length} ASSETS`}
                {viewMode === "BUSINESS UNIT" && `${businessUnitSummaries.length} BUSINESS UNITS`}
                {viewMode === "ORG" && "ORG-WIDE SUMMARY"}
                {' • CLICK ROW TO INSPECT'}
              </span>
            </div>
          </div>

          <table className="data-table compact-table">
            <thead>
              {viewMode === "ASSET" ? (
                <tr>
                  <th style={{ cursor: "pointer" }} onClick={() => handleSort("name")}>
                    <span className="th-sort">ASSET <SortIcon keyName="name" /></span>
                  </th>
                  <th>BU</th>
                  <th>CRITICALITY</th>
                  <th style={{ cursor: "pointer" }} onClick={() => handleSort("eal")}>
                    <span className="th-sort">EAL <SortIcon keyName="eal" /></span>
                  </th>
                  <th style={{ cursor: "pointer" }} onClick={() => handleSort("var95")}>
                    <span className="th-sort">VAR 95% <SortIcon keyName="var95" /></span>
                  </th>
                  <th style={{ cursor: "pointer" }} onClick={() => handleSort("eff")}>
                    <span className="th-sort">CTRL EFF. <SortIcon keyName="eff" /></span>
                  </th>
                </tr>
              ) : viewMode === "BUSINESS UNIT" ? (
                <tr>
                  <th>BUSINESS UNIT</th>
                  <th>ASSET COUNT</th>
                  <th>TOTAL EAL</th>
                  <th>TOTAL VAR 95%</th>
                  <th>AVG CONTROL</th>
                </tr>
              ) : (
                <tr>
                  <th>ORG</th>
                  <th>ASSET COUNT</th>
                  <th>EAL</th>
                  <th>VAR 95%</th>
                  <th>AVG CONTROL</th>
                </tr>
              )}
            </thead>
            <tbody>
              {viewMode === "ASSET" && filteredAssets.map((item) => {
                const isSelected = String(item.name) === String(selectedAssetId) || String(item.id) === String(selectedAssetId);
                return (
                  <tr
                    key={item.id}
                    style={{ cursor: "pointer", background: isSelected ? "rgba(56, 138, 255, 0.12)" : undefined }}
                    onClick={() => { setSelectedAssetId(String(item.name)); setViewMode("ASSET"); }}
                  >
                    <td className="font-medium text-light">
                      {isSelected && <span style={{ color: "#5ea0ff", marginRight: 8 }}>▶</span>}
                      {item.name}
                    </td>
                    <td className="text-muted">{item.business_unit}</td>
                    <td>
                      <span className="priority-dot" style={{ display: "inline-block", background: critColor[item.criticality], width: 7, height: 7, borderRadius: "50%", marginRight: 6 }} />
                      <span className="text-light" style={{ fontSize: 11 }}>{item.criticality}</span>
                    </td>
                    <td className="font-medium text-light">{fmtCurrencyLakh(item.eal_lakhs)}</td>
                    <td className="font-medium text-light">{fmtCurrencyLakh(item.var_95_lakhs)}</td>
                    <td>
                      <div className="control-eff-cell">
                        <span className="eff-bar">
                          <i className={`bg-${item.control_efficiency >= 70 ? "green" : item.control_efficiency >= 55 ? "gold" : "red"}`} style={{ width: `${item.control_efficiency}%` }} />
                        </span>
                        <span className="text-light">{item.control_efficiency}%</span>
                      </div>
                    </td>
                  </tr>
                );
              })}

              {viewMode === "BUSINESS UNIT" && businessUnitSummaries.map((row) => (
                <tr key={row.businessUnit}>
                  <td className="font-medium text-light">{row.businessUnit}</td>
                  <td className="text-light">{row.assetCount}</td>
                  <td className="text-light">{fmtCurrencyLakh(row.totalEal)}</td>
                  <td className="text-light">{fmtCurrencyLakh(row.totalVar95)}</td>
                  <td className="text-light">{Math.round(row.averageControl)}%</td>
                </tr>
              ))}

              {viewMode === "ORG" && (
                <tr>
                  <td className="font-medium text-light">{orgSummary.name}</td>
                  <td className="text-light">{orgSummary.assetCount}</td>
                  <td className="text-light">{fmtCurrencyLakh(orgSummary.totalEal)}</td>
                  <td className="text-light">{fmtCurrencyLakh(orgSummary.totalVar95)}</td>
                  <td className="text-light">{Math.round(orgSummary.averageControl)}%</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="terminal-card monte-carlo-chart stagger-enter stagger-3">
          <div className="card-head mb-4">
            <div>
              <h2>Monte Carlo distribution</h2>
              <span style={{ textTransform: "uppercase" }}>
                {viewMode === "ASSET" ? (selectedAsset?.name ?? "Asset") : viewMode === "BUSINESS UNIT" ? `${(activeBuFilter === "ALL" ? "ALL" : activeBuFilter)} BUSINESS UNIT` : "ACME CORP ORG"} · {mc?.trials ?? 50000} TRIALS
              </span>
            </div>
          </div>

          <div className="histogram-container">
            <div className="histogram-bars" ref={barsRef}>
              {chartData.map((height, index) => {
                let toneColor = "#2a3442";
                if (index >= Math.floor(chartData.length * 0.7)) toneColor = "#8b5cf6";
                if (index >= Math.floor(chartData.length * 0.9)) toneColor = "#ef858d";

                const normalized = Math.max(4, (height / histogramMax) * 100);
                return (
                  <div
                    key={index}
                    style={{
                      flex: 1,
                      height: barsVisible ? `${normalized}%` : "0%",
                      background: toneColor,
                      borderRadius: "2px 2px 0 0",
                      transition: `height 0.4s ease ${index * 0.012}s`,
                    }}
                  />
                );
              })}
            </div>
            <div className="histogram-labels">
              <span style={{ fontSize: 9, color: "#687483" }}>Min</span>
              <span style={{ fontSize: 9, color: "#687483" }}>Mean</span>
              <span style={{ fontSize: 9, color: "#687483", marginLeft: "auto" }}>P95</span>
              <span style={{ fontSize: 9, color: "#687483" }}>P99</span>
            </div>
            <div className="histogram-axis">
              <span className="text-muted">Mean loss <strong className="text-light">{fmtCr(meanLossCr)}</strong></span>
              <span className="text-muted">P95 (VaR) <strong className="text-gold">{fmtCr(p95VarCr)}</strong></span>
              <span className="text-muted">P99 <strong className="text-red">{fmtCr(p99LossCr)}</strong></span>
            </div>
          </div>

          <div className="asset-summary-footer">
            <div>
              <span className="eyebrow">CONTROL EFFECTIVENESS</span>
              <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 8, maxWidth: 210, minWidth: 0 }}>
                <div style={{ flex: "1 1 auto", minWidth: 0, height: 6, background: "#1c2431", borderRadius: 3, overflow: "hidden" }}>
                  <div style={{ height: "100%", width: `${selectedAsset?.control_efficiency ?? Math.round(orgSummary.averageControl)}%`, background: (selectedAsset?.control_efficiency ?? Math.round(orgSummary.averageControl)) >= 70 ? "#51d1a1" : (selectedAsset?.control_efficiency ?? Math.round(orgSummary.averageControl)) >= 55 ? "var(--gold)" : "#ef858d", borderRadius: 3, transition: "width 0.6s ease" }} />
                </div>
                <span className="text-light" style={{ fontSize: 12, fontWeight: 600, flexShrink: 0, whiteSpace: "nowrap" }}>{selectedAsset?.control_efficiency ?? Math.round(orgSummary.averageControl)}%</span>
              </div>
            </div>
            <div style={{ display: "flex", gap: 20, marginTop: 16 }}>
              <div>
                <span className="eyebrow">CRITICALITY</span>
                <div style={{ marginTop: 6, color: critColor[selectedAsset?.criticality ?? "High"], fontWeight: 700, fontSize: 13 }}>{selectedAsset?.criticality ?? "-"}</div>
              </div>
              <div>
                <span className="eyebrow">BUSINESS UNIT</span>
                <div style={{ marginTop: 6, color: "#dce3e9", fontSize: 12 }}>{selectedAsset?.business_unit ?? "-"}</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
