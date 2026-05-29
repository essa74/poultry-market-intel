"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface DataPoint {
  date: string;
  eggs?: number;
  chicks?: number;
  [key: string]: string | number | undefined;
}

interface PriceChartProps {
  data: DataPoint[];
  lines?: { key: string; color: string; name: string }[];
  height?: number;
  showGrid?: boolean;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <p className="text-gray-400 text-xs mb-2">{label}</p>
      {payload.map((entry: any, i: number) => (
        <div key={i} className="flex items-center justify-between gap-6 text-sm">
          <span className="text-gray-300">{entry.name}</span>
          <span className="font-semibold text-white" style={{ color: entry.color }}>
            {Number(entry.value).toFixed(1)} ج.م
          </span>
        </div>
      ))}
    </div>
  );
};

export default function PriceChart({
  data,
  lines = [
    { key: "eggs", color: "#10b981", name: "البيض المخصب" },
    { key: "chicks", color: "#f59e0b", name: "الكتاكيت" },
  ],
  height = 300,
  showGrid = true,
}: PriceChartProps) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
        {showGrid && (
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
        )}
        <XAxis
          dataKey="date"
          tick={{ fill: "#6b7280", fontSize: 11, fontFamily: "Cairo, sans-serif" }}
          axisLine={false}
          tickLine={false}
          dy={10}
        />
        <YAxis
          tick={{ fill: "#6b7280", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          dx={-10}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ stroke: "rgba(255,255,255,0.1)", strokeWidth: 1 }} />
        {lines.map((line) => (
          <defs key={line.key}>
            <linearGradient id={`gradient-${line.key}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={line.color} stopOpacity={0.3} />
              <stop offset="95%" stopColor={line.color} stopOpacity={0} />
            </linearGradient>
          </defs>
        ))}
        {lines.map((line) => (
          <Area
            key={line.key}
            type="monotone"
            dataKey={line.key}
            stroke={line.color}
            strokeWidth={2}
            fill={`url(#gradient-${line.key})`}
            name={line.name}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 2, stroke: line.color, fill: "#0a0a0f" }}
          />
        ))}
      </AreaChart>
    </ResponsiveContainer>
  );
}
