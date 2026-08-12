"use client";

import { useMemo, useState, type PointerEvent } from "react";

import type { HypotheticalAccountSnapshot } from "@/lib/site-types";

const WIDTH = 1200;
const HEIGHT = 440;
const TOP = 28;
const BOTTOM = 42;

const currency = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
  maximumFractionDigits: 0,
});

export default function HistoricalAccountChart({ snapshot }: { snapshot: HypotheticalAccountSnapshot }) {
  const [activeIndex, setActiveIndex] = useState(snapshot.points.length - 1);
  const chart = useMemo(() => buildChart(snapshot), [snapshot]);
  const active = snapshot.points[activeIndex];
  const activeX = chart.x(activeIndex);
  const activeY = chart.y(active.value);
  const alignRight = activeX > WIDTH * 0.74;

  function inspect(event: PointerEvent<SVGSVGElement>) {
    const bounds = event.currentTarget.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (event.clientX - bounds.left) / bounds.width));
    setActiveIndex(Math.round(ratio * (snapshot.points.length - 1)));
  }

  return (
    <div className="account-chart-shell">
      <svg
        className="account-chart"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={`Hypothetical account value from ${snapshot.period.start} to ${snapshot.period.end}, ending at ${currency.format(snapshot.ending_balance)}`}
        onPointerMove={inspect}
        onPointerLeave={() => setActiveIndex(snapshot.points.length - 1)}
      >
        <defs>
          <linearGradient id="account-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#42d98b" stopOpacity=".24" />
            <stop offset="100%" stopColor="#42d98b" stopOpacity="0" />
          </linearGradient>
          <filter id="account-glow" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {chart.gridValues.map((value) => (
          <g key={value}>
            <line x1="0" y1={chart.y(value)} x2={WIDTH} y2={chart.y(value)} className="account-grid-line" />
            <text x="0" y={chart.y(value) - 9} className="account-axis-value">{compactCurrency(value)}</text>
          </g>
        ))}

        {chart.yearMarkers.map((marker) => (
          <g key={marker.year}>
            <line x1={marker.x} y1={TOP} x2={marker.x} y2={HEIGHT - BOTTOM} className="account-year-line" />
            <text x={marker.x + 8} y={HEIGHT - 12} className="account-year-label">{marker.year}</text>
          </g>
        ))}

        <line x1="0" y1={chart.y(snapshot.starting_balance)} x2={WIDTH} y2={chart.y(snapshot.starting_balance)} className="account-start-line" />
        <path d={chart.areaPath} fill="url(#account-fill)" />
        <path d={chart.linePath} className="account-line-glow" filter="url(#account-glow)" />
        <path d={chart.linePath} className="account-line" />

        <line x1={activeX} y1={TOP} x2={activeX} y2={HEIGHT - BOTTOM} className="account-cursor" />
        <circle cx={activeX} cy={activeY} r="6" className="account-point" />
        <g transform={`translate(${alignRight ? activeX - 18 : activeX + 18} ${Math.max(48, activeY - 20)})`} textAnchor={alignRight ? "end" : "start"}>
          <text className="account-tooltip-value">{currency.format(active.value)}</text>
          <text y="21" className="account-tooltip-date">{formatDate(active.date)}</text>
        </g>
      </svg>
      <p className="account-chart-hint">MOVE ACROSS THE CURVE TO INSPECT</p>
    </div>
  );
}

function buildChart(snapshot: HypotheticalAccountSnapshot) {
  const values = [snapshot.starting_balance, ...snapshot.points.map((point) => point.value)];
  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const padding = (maximum - minimum) * 0.08;
  const floor = Math.max(0, minimum - padding);
  const ceiling = maximum + padding;
  const x = (index: number) => (index / (snapshot.points.length - 1)) * WIDTH;
  const y = (value: number) => TOP + ((ceiling - value) / (ceiling - floor)) * (HEIGHT - TOP - BOTTOM);
  const linePath = snapshot.points.map((point, index) => `${index ? "L" : "M"}${x(index).toFixed(2)} ${y(point.value).toFixed(2)}`).join(" ");
  const areaPath = `${linePath} L${WIDTH} ${HEIGHT - BOTTOM} L0 ${HEIGHT - BOTTOM} Z`;
  const years = new Map<string, number>();
  snapshot.points.forEach((point, index) => {
    const year = point.date.slice(0, 4);
    if (!years.has(year)) years.set(year, index);
  });
  const yearMarkers = [...years].map(([year, index]) => ({ year, x: x(index) }));
  const gridValues = [100000, 300000, 500000, 700000, 900000].filter((value) => value >= floor && value <= ceiling);
  return { x, y, linePath, areaPath, yearMarkers, gridValues };
}

function compactCurrency(value: number) {
  return `$${Math.round(value / 1000)}K`;
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("en-US", { month: "short", day: "numeric", year: "numeric", timeZone: "UTC" }).format(new Date(`${value}T00:00:00Z`));
}
