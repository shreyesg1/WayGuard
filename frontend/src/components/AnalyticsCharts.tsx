import { useMemo } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { AnalyticsTrendsResponse } from "../types";

interface Props {
  trends?: AnalyticsTrendsResponse;
}

export default function AnalyticsCharts({ trends }: Props) {
  const complaints = trends?.trends.complaints ?? [];
  const crime = trends?.trends.crime ?? [];
  const health = trends?.trends.health ?? [];

  const merged = new Map<
    string,
    { date: string; complaints: number | null; crime: number | null; health: number | null }
  >();
  for (const p of complaints) merged.set(p.date, { date: p.date, complaints: p.count, crime: null, health: null });
  for (const p of crime) {
    const row = merged.get(p.date) ?? { date: p.date, complaints: null, crime: null, health: null };
    row.crime = p.count;
    merged.set(p.date, row);
  }
  for (const p of health) {
    const row = merged.get(p.date) ?? { date: p.date, complaints: null, crime: null, health: null };
    row.health = p.count;
    merged.set(p.date, row);
  }
  const data = [...merged.values()].sort((a, b) => a.date.localeCompare(b.date));

  // Forward-fill missing values so lines remain continuous.
  let lastComplaints: number | null = null;
  let lastCrime: number | null = null;
  let lastHealth: number | null = null;
  for (const row of data) {
    if (row.complaints == null) row.complaints = lastComplaints ?? 0;
    else lastComplaints = row.complaints;

    if (row.crime == null) row.crime = lastCrime ?? 0;
    else lastCrime = row.crime;

    if (row.health == null) row.health = lastHealth ?? 0;
    else lastHealth = row.health;
  }

  const remappedData = useMemo(() => {
    const DAYS = 30;
    const toYmd = (d: Date) => {
      const copy = new Date(d);
      copy.setHours(0, 0, 0, 0);
      return copy.toISOString().slice(0, 10);
    };
    const parseYmd = (s: string) => new Date(`${s}T00:00:00`);

    const cMap = new Map(complaints.map((p) => [p.date, p.count]));
    const crimeMap = new Map(crime.map((p) => [p.date, p.count]));
    const hMap = new Map(health.map((p) => [p.date, p.count]));

    const overlapDates = [...cMap.keys()]
      .filter((d) => crimeMap.has(d) && hMap.has(d))
      .sort((a, b) => a.localeCompare(b));

    const windows: string[][] = [];
    let run: string[] = [];
    for (const dateStr of overlapDates) {
      if (run.length === 0) {
        run = [dateStr];
        continue;
      }
      const prev = parseYmd(run[run.length - 1]);
      const cur = parseYmd(dateStr);
      const diffDays = Math.round((cur.getTime() - prev.getTime()) / 86400000);
      if (diffDays === 1) {
        run.push(dateStr);
      } else {
        if (run.length >= DAYS) {
          for (let i = 0; i <= run.length - DAYS; i++) {
            windows.push(run.slice(i, i + DAYS));
          }
        }
        run = [dateStr];
      }
    }
    if (run.length >= DAYS) {
      for (let i = 0; i <= run.length - DAYS; i++) {
        windows.push(run.slice(i, i + DAYS));
      }
    }

    // Choose a random complete 30-day window when available.
    const selectedWindow = windows.length > 0
      ? windows[Math.floor(Math.random() * windows.length)]
      : [];

    return Array.from({ length: DAYS }, (_, i) => {
      const mapped = new Date();
      mapped.setHours(0, 0, 0, 0);
      mapped.setDate(mapped.getDate() - (DAYS - 1 - i));
      const mappedDate = toYmd(mapped);

      if (selectedWindow.length === DAYS) {
        const srcDate = selectedWindow[i];
        return {
          date: mappedDate,
          complaints: cMap.get(srcDate) ?? 0,
          crime: crimeMap.get(srcDate) ?? 0,
          health: hMap.get(srcDate) ?? 0,
        };
      }

      // Fallback if no full overlapping 30-day window exists.
      if (data.length === 0) {
        return { date: mappedDate, complaints: 0, crime: 0, health: 0 };
      }
      const srcIdx = Math.round((i / Math.max(1, DAYS - 1)) * Math.max(0, data.length - 1));
      const src = data[srcIdx];
      return {
        date: mappedDate,
        complaints: src.complaints ?? 0,
        crime: src.crime ?? 0,
        health: src.health ?? 0,
      };
    });
  }, [complaints, crime, health, data]);

  return (
    <div className="card">
      <h3>Trend Analysis</h3>
      <div style={{ height: 340 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={remappedData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="complaints" stroke="#2b8cbe" dot={false} />
            <Line type="monotone" dataKey="crime" stroke="#2ca25f" dot={false} />
            <Line type="monotone" dataKey="health" stroke="#d95f0e" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
