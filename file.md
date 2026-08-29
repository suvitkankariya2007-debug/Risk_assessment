# CyberRiskIQ - Repository Directory & File Map

This document serves as a complete blueprint for any AI coding assistant to understand, build, and extend the **CyberRiskIQ Command Center** prototype. 

---

## 1. Project Overview & Architecture
**CyberRiskIQ** is a BFSI-focused Cyber Risk Quantification and Optimization dashboard. 
- **Frontend**: React + TypeScript + Vite + TailwindCSS.
- **Backend**: A minimal Node/Express server serving compiled static assets.
- **Routing**: Pure client-side routing using the lightweight `wouter` library.
- **State & Theme**: Managed via React contexts (`ThemeContext.tsx`).
- **Core Invariants**: Expected Annual Loss (EAL) and Value-at-Risk (VaR) quantification using client-side simulations.

---

## 2. Directory Structure Tree
```text
cyber-risk-optimizer/
├── client/                      # Frontend Application Root
│   ├── index.html               # Main entry HTML template
│   ├── public/                  # Public assets (icons, images)
│   └── src/                     # React/TypeScript source code
│       ├── App.tsx              # Root component & Wouter client router
│       ├── main.tsx             # DOM mounting entrypoint
│       ├── index.css            # CSS variables & utility classes
│       ├── sections.css         # Page section styling (glassmorphism/terminal aesthetics)
│       ├── const.ts             # Client constants
│       ├── components/          # React components
│       │   ├── ErrorBoundary.tsx# Catches runtime React UI render errors
│       │   ├── ManusDialog.tsx  # Dialog orchestration
│       │   ├── Map.tsx          # SVG-based network topology mapping of risk nodes
│       │   ├── sections/        # Main feature modules of the command center
│       │   │   ├── AICopilot.tsx          # Conversational assistant for risk analysis
│       │   │   ├── ComplianceMapping.tsx  # Interactive coverage of NIST/ISO frameworks
│       │   │   ├── InvestmentOptimizer.tsx# Live control budget vs. EAL optimization curve
│       │   │   ├── RemediationBacklog.tsx # Acknowledged vulnerabilities tracker
│       │   │   ├── RiskQuantification.tsx # Detailed EAL, VaR, & Monte Carlo statistics
│       │   │   └── ScenarioSimulator.tsx  # Threat & vulnerability simulator
│       │   └── ui/              # Shadcn components (Button, Card, Table, Tooltip, etc.)
│       ├── contexts/            # React global contexts
│       │   └── ThemeContext.tsx # System/Light/Dark mode state management
│       └── hooks/               # Custom reusable React hooks
│           ├── useComposition.ts# Composition inputs helper
│           ├── useCountUp.ts    # Rolling text numbers animation
│           ├── useInView.ts     # Viewport intersection tracker
│           ├── useMobile.tsx    # Mobile screen layout detection
│           └── usePersistFn.ts  # Cached callback persistence
├── server/                      # Node/Express Backend Root
│   └── index.ts                 # Production asset server & SPA router fallback
├── shared/                      # Shared assets between Frontend and Backend
│   └── const.ts                 # Common constants (session ID keys, session lengths)
├── dist/                        # Build output directory (created after npm run build)
│   ├── index.js                 # Compiled Express server
│   └── public/                  # Bundled React application
├── package.json                 # Dependency config and run scripts
├── tsconfig.json                # TypeScript compilation config
├── components.json              # Shadcn-UI configuration
└── vite.config.ts               # Vite bundler config with logging and storage proxy plugins
```

---


---

## 3. Core Files & Their Purposes

### Configuration & Tooling
*   **`vite.config.ts`**: Configures the dev server (port `3000`), TypeScript path aliases (`@/` for client, `@shared/` for shared files), and sets up two custom plugins:
    *   `vitePluginManusDebugCollector`: Creates local JSON log files in `.manus-logs/` capturing browser console logs, network activity, and session replays.
    *   `vitePluginStorageProxy`
## 3. Core Files & Their Purposes

### Configuration & Tooling
*   **`vite.config.ts`**: Config

---

## 3. Core Files & Their Purposes

### Configuration & Tooling
*   **`vite.config.ts`**: Configures the dev server (port `3000`), TypeScript path aliases (`@/` for client, `@shared/` for shared files), and sets up two custom plugins:
    *   `vitePluginManusDebugCollector`: Creates local JSON log files in `.manus-logs/` capturing browser console logs, network activity, and session replays.
    *   `vitePluginStorageProxy`ures the dev server (port `3000`), TypeScript path aliases (`@/` for client, `@shared/` for shared files), and sets up two custom plugins:
    *   `vitePluginManusDebugCollector`: Creates local JSON log files in `.manus-logs/` capturing browser console logs, network activity, and session replays.
    *   `vitePluginStorageProxy`: Proxies cloud assets from storage APIs.
*   **`package.json`**: Specifies scripts (`dev`, `build`, `start`, `preview`) and core packages.

### Backend
*   **`server/index.ts`**: Express backend entrypoint. In production (`NODE_ENV=production`), serves compiled assets out of `dist/public` and directs all unmatched requests (`*`) to `index.html` to support client-side SPA routing.

### Frontend Routing & Stylingd
*   **`client/src/App.tsx`**: Sets up global wrapper contexts (`ThemeProvider`, `TooltipProvider`, `Toaster`) and defines client-side routes via `<Switch>` (`wouter`).
*   **`client/src/index.css` & `client/src/sections.css`**: Central UI theme definitions. Implements dark-mode variables, glowing terminal borders, typography, custom layouts, and animations.

### Dashboard Sections (`client/src/components/sections/`)
*   **`AICopilot.tsx`**: Chat workspace featuring a simulated AI system providing insights on assets (e.g., *Core Banking DB*, *IAM SSO*). Uses a hardcoded conversational script.
*   **`RiskQuantification.tsx`**: Shows detailed Monte Carlo distribution curves, asset hazard levels, and threat tables.
*   **`ScenarioSimulator.tsx`**: Allows users to dynamically change threat frequency and impact sliders to calculate real-time expected financial loss.
*   **`InvestmentOptimizer.tsx`**: Models control choices (e.g., *Multi-Factor Authentication*, *DLP*) against a given budget, calculating risk-reduction returns.
*   **`ComplianceMapping.tsx`**: Maps framework compliance (ISO 27001, NIST, CIS) with live progress bars and control coverage tables.
*   **`RemediationBacklog.tsx`**: Interactive backlog table showing CVE status, business impact (rupees), ownership, and quick remediation actions.

---

## 4. Key Dependencies & Package Requirements

The following packages are specified in `package.json` and must be resolved:

### Production / Core Dependencies
*   **`react`** & **`react-dom`** (`^19.2.1`): Main frontend framework.
*   **`wouter`** (`^3.3.5`): Simple routing library for SPAs.
*   **`express`** (`^4.21.2`): Minimal backend to serve built artifacts.
*   **`framer-motion`** (`^12.23.22`): Fluid page entries and state change animations.
*   **`recharts`** (`^2.15.2`): Render risk graphs and Monte Carlo distribution visuals.
*   **`lucide-react`** (`^0.453.0`): Icon library.
*   **`zod`** (`^4.1.12`): Schema validation for settings or parameters.
*   **`sonner`** (`^2.0.7`): Toast notifications.
*   **`radix-ui` suite**: Headless primitives for modals, sliders, tooltips, select inputs, dropdowns, and checkboxes.

### Dev & Compilation Dependencies
*   **`vite`** (`^7.1.7`) & **`@tailwindcss/vite`** (`^4.1.3`): Asset bundling and CSS injection.
*   **`esbuild`** (`^0.25.0`): Compiles backend TypeScript (`server/index.ts`) for deployment.
*   **`tsx`** (`^4.19.1`): Directly execute typescript files during testing/running.
*   **`typescript`** (`5.6.3`): Enforces static typing contracts.

---

## 5. Development & Run Guide

### Step 1: Install Dependencies
Run the command below (use `--legacy-peer-deps` due to peer conflicts between newer Vite bundler versions and legacy UI components):
```bash
npm install --legacy-peer-deps
```

### Step 2: Running the Dev Server
Launches the Vite dev server with hot module replacement (HMR). By default, it runs on port `3000` (or `3001` if `3000` is busy):
```bash
npm run dev
```

### Step 3: Compiling for Production
Builds the frontend production bundles into `dist/public` and compiles the backend server file into `dist/index.js`:
```bash
npm run build
```

### Step 4: Running Production Build
Launches the Express server pointing to the built production bundle:
```bash
npm run start
```
