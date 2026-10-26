import { useState } from "react";
import { getMeta } from "./api.js";
import { useApi } from "./hooks.js";
import { fmtTime } from "./utils.js";
import DayAheadPanel from "./components/DayAheadPanel.jsx";
import ExplorePanel from "./components/ExplorePanel.jsx";
import Glossary from "./components/Glossary.jsx";

const TABS = [
  { id: "dayahead", label: "Day-ahead decision" },
  { id: "explore", label: "Forecast accuracy explorer" },
];

export default function App() {
  const [tab, setTab] = useState("dayahead");
  const meta = useApi((signal) => getMeta(signal), []);

  return (
    <div className="page">
      <header className="header">
        <div>
          <h1>Wind Forecast Monitor</h1>
          <p>GB national wind generation: Elexon forecasts vs actuals, January 2026</p>
        </div>
        {meta.data && (
          <div className="header-meta">
            <div>Latest forecast in data set: {fmtTime(meta.data.last_publish_time)} UTC</div>
            <div>All times UTC (= UK local time in January)</div>
          </div>
        )}
      </header>

      {meta.data?.source === "synthetic" && (
        <div className="banner banner-warn">
          <strong>Demo data.</strong> This server is using randomly generated numbers, not real Elexon data.
          Run <code>python -m scripts.fetch_data</code> in the backend to load the real data.
        </div>
      )}

      {meta.error && (
        <div className="banner banner-error">
          <strong>Cannot load data.</strong> {meta.error}
        </div>
      )}

      {meta.data && (
        <>
          <nav className="tabs">
            {TABS.map((item) => (
              <button
                key={item.id}
                className={item.id === tab ? "tab active" : "tab"}
                onClick={() => setTab(item.id)}
              >
                {item.label}
              </button>
            ))}
          </nav>
          {tab === "dayahead" ? <DayAheadPanel meta={meta.data} /> : <ExplorePanel meta={meta.data} />}
          <Glossary />
        </>
      )}

      {meta.loading && !meta.data && !meta.error && <p className="muted">Loading…</p>}
    </div>
  );
}
