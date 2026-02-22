import { useState } from "react";
import AnalyticsPage from "./pages/AnalyticsPage";
import NavigationPage from "./pages/NavigationPage";

type Tab = "navigation" | "analytics";

export default function App() {
  const [tab, setTab] = useState<Tab>("navigation");

  return (
    <div className="app-shell">
      <header className="topbar glass">
        <div className="brand-wrap" aria-label="CityScope branding">
          <div className="brand-dot" />
          <div>
            <h1>CityScope</h1>
            <p>Location-aware route recommendations and urban incident analytics</p>
          </div>
        </div>
        <nav className="tab-nav segmented" aria-label="Primary tabs">
          <button
            className={tab === "navigation" ? "active" : ""}
            onClick={() => setTab("navigation")}
            type="button"
            aria-pressed={tab === "navigation"}
          >
            Navigation
          </button>
          <button
            className={tab === "analytics" ? "active" : ""}
            onClick={() => setTab("analytics")}
            type="button"
            aria-pressed={tab === "analytics"}
          >
            Analytics
          </button>
        </nav>
        <div className="header-actions" aria-label="User actions">
          <button className="icon-btn" type="button" aria-label="Settings">
            ⚙
          </button>
          <button className="icon-btn" type="button" aria-label="User profile">
            ◉
          </button>
        </div>
      </header>

      {tab === "navigation" ? <NavigationPage /> : <AnalyticsPage />}

      <footer className="footer-note">
        Reported incidents are not complete ground truth and may reflect reporting and geocoding bias.
      </footer>
    </div>
  );
}
