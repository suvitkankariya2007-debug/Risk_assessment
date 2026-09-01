import { useState } from "react";

export default function InvestmentOptimizer() {
  const [budget, setBudget] = useState(1.2);

  // Calculate curve points for the SVG based on the budget
  // y = 1 - e^(-x) curve approximation
  const maxBudget = 5;
  const pathData = `M0 290 Q200 ${290 - (budget * 40)} 800 50`;

  return (
    <section className="section-container stagger-enter stagger-1">
      <div className="section-header">
        <div>
          <span className="eyebrow eyebrow--gold">INVESTMENT OPTIMIZATION MODULE</span>
          <h1>Best risk reduction, per rupee</h1>
          <p>0/1 knapsack over candidate controls: maximize Σ risk reduction subject to Σ cost ≤ budget.</p>
        </div>
      </div>

      <div className="terminal-card large-investment-card stagger-enter stagger-2">
        <div className="investment-header">
          <div>
            <h3>Set your annual security budget</h3>
            <span>RECOMMENDED BUNDLE RE-SOLVES INSTANTLY</span>
          </div>
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
            onChange={(e) => setBudget(Number(e.target.value))} 
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

        <div className="large-curve-chart">
          <div className="chart-y-axis">
            <span>₹3.6Cr</span>
            <span>₹3Cr</span>
            <span>₹2.5Cr</span>
            <span>₹2Cr</span>
            <span>₹1.5Cr</span>
            <span>₹1Cr</span>
            <span>₹0.6Cr</span>
          </div>
          <svg viewBox="0 0 800 300" preserveAspectRatio="none">
            <defs>
              <linearGradient id="curveGradient" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor="#6376c9" stopOpacity="0.4" />
                <stop offset="100%" stopColor="#6376c9" stopOpacity="0" />
              </linearGradient>
            </defs>
            <g className="chart-grid">
              <line x1="0" y1="20" x2="800" y2="20" />
              <line x1="0" y1="65" x2="800" y2="65" />
              <line x1="0" y1="110" x2="800" y2="110" />
              <line x1="0" y1="155" x2="800" y2="155" />
              <line x1="0" y1="200" x2="800" y2="200" />
              <line x1="0" y1="245" x2="800" y2="245" />
              <line x1="0" y1="290" x2="800" y2="290" />
            </g>
            <path 
              d="M0 290 C 200 150, 400 80, 800 60 L 800 300 L 0 300 Z" 
              fill="url(#curveGradient)" 
              className="chart-fill"
            />
            <path 
              d="M0 290 C 200 150, 400 80, 800 60" 
              fill="none" 
              stroke="#8ba1fb" 
              strokeWidth="3" 
              className="chart-stroke"
            />
          </svg>
        </div>
      </div>
    </section>
  );
}
