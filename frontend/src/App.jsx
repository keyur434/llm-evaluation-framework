import { useCallback, useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const API = "";

async function api(path, options) {
  const res = await fetch(`${API}${path}`, options);
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json();
}

function fmtPct(n) {
  if (n == null || Number.isNaN(n)) return "—";
  return `${(n * 100).toFixed(1)}%`;
}

function categoryAverages(results) {
  const map = {};
  for (const r of results || []) {
    if (!map[r.category]) map[r.category] = { sum: 0, n: 0 };
    map[r.category].sum += r.score;
    map[r.category].n += 1;
  }
  return Object.entries(map)
    .map(([category, { sum, n }]) => ({
      category,
      mean: sum / n,
      count: n,
    }))
    .sort((a, b) => a.category.localeCompare(b.category));
}

export default function App() {
  const [summary, setSummary] = useState(null);
  const [runs, setRuns] = useState([]);
  const [drift, setDrift] = useState(null);
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    const [s, r, d] = await Promise.all([
      api("/api/eval/summary"),
      api("/api/eval/runs?limit=60"),
      api("/api/eval/drift"),
    ]);
    setSummary(s);
    setRuns([...r].reverse());
    setDrift(d);
    if (s.latest_run_id) {
      const det = await api(`/api/eval/runs/${s.latest_run_id}`);
      setDetail(det);
    }
  }, []);

  useEffect(() => {
    setLoading(true);
    load()
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [load]);

  const chartData = useMemo(
    () =>
      runs
        .filter((r) => r.finished_at && r.mean_score != null)
        .map((r) => ({
          id: r.id,
          date: new Date(r.finished_at).toLocaleDateString(),
          score: Number((r.mean_score * 100).toFixed(2)),
        })),
    [runs]
  );

  const cats = useMemo(() => categoryAverages(detail?.results), [detail]);
  const threshold = summary?.threshold ?? 0.8;

  async function onRun() {
    setRunning(true);
    setError("");
    try {
      await api("/api/eval/run", { method: "POST" });
      await load();
    } catch (e) {
      setError(e.message);
    } finally {
      setRunning(false);
    }
  }

  if (loading) return <p className="muted">Loading dashboard…</p>;

  return (
    <div>
      <h1>LLM Evaluation Framework</h1>
      <p className="sub">Golden dataset scores over time · LLM-as-a-judge · drift gate</p>

      {error ? <div className="banner alert">{error}</div> : null}

      {drift ? (
        <div className={`banner ${drift.alert ? "alert" : "ok"}`}>{drift.message}</div>
      ) : null}

      <div className="row">
        <button onClick={onRun} disabled={running}>
          {running ? "Running eval…" : "Run eval"}
        </button>
        <button className="secondary" onClick={() => load().catch((e) => setError(e.message))}>
          Refresh
        </button>
        <span className="muted">
          candidate={summary?.candidate ?? "—"} · judge={summary?.judge ?? "—"}
        </span>
      </div>

      <div className="grid">
        <div className="card">
          <div className="label">Latest mean</div>
          <div className="value">{fmtPct(summary?.mean_score)}</div>
        </div>
        <div className="card">
          <div className="label">Gate ({fmtPct(threshold)})</div>
          <div className={`value ${summary?.passed ? "pass" : "fail"}`}>
            {summary?.passed == null ? "—" : summary.passed ? "PASS" : "FAIL"}
          </div>
        </div>
        <div className="card">
          <div className="label">7d mean</div>
          <div className="value">{fmtPct(drift?.current_7d_mean)}</div>
        </div>
        <div className="card">
          <div className="label">Prior 7d</div>
          <div className="value">{fmtPct(drift?.previous_7d_mean)}</div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: "1rem" }}>
        <div className="label" style={{ marginBottom: "0.75rem" }}>
          Score history (%)
        </div>
        <div className="chart-wrap">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid stroke="#243556" strokeDasharray="3 3" />
              <XAxis dataKey="date" stroke="#8fa3c4" tick={{ fontSize: 11 }} />
              <YAxis domain={[60, 100]} stroke="#8fa3c4" tick={{ fontSize: 11 }} />
              <Tooltip
                contentStyle={{ background: "#121c30", border: "1px solid #243556" }}
              />
              <Legend />
              <ReferenceLine
                y={threshold * 100}
                stroke="#f59e0b"
                strokeDasharray="4 4"
                label={{ value: "threshold", fill: "#f59e0b", fontSize: 11 }}
              />
              <Line
                type="monotone"
                dataKey="score"
                name="mean score"
                stroke="#3b82f6"
                strokeWidth={2}
                dot={{ r: 3 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card">
        <div className="label" style={{ marginBottom: "0.75rem" }}>
          Latest run by category {detail ? `(#${detail.id})` : ""}
        </div>
        {cats.length === 0 ? (
          <p className="muted">No per-case results yet. Run an eval.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Category</th>
                <th>Cases</th>
                <th>Mean score</th>
              </tr>
            </thead>
            <tbody>
              {cats.map((c) => (
                <tr key={c.category}>
                  <td>{c.category}</td>
                  <td>{c.count}</td>
                  <td className={c.mean >= threshold ? "pass" : "fail"}>{fmtPct(c.mean)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
