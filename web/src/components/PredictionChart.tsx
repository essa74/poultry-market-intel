"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import GlassCard from "./GlassCard";
import { motion } from "framer-motion";

interface PredictionPoint {
  date: string;
  predicted: number;
  lower: number;
  upper: number;
}

interface PredictionChartProps {
  data: PredictionPoint[];
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <p className="text-gray-400 text-xs mb-2">{label}</p>
      {payload.map((entry: any, i: number) => (
        <div key={i} className="flex items-center justify-between gap-6 text-sm">
          <span className="text-gray-300">{entry.name}</span>
          <span className="font-semibold" style={{ color: entry.color }}>
            {Number(entry.value).toFixed(1)} ج.م
          </span>
        </div>
      ))}
    </div>
  );
};

export default function PredictionChart({ data }: PredictionChartProps) {
  if (!data.length) return null;

  const latest = data[data.length - 1];

  return (
    <div>
      <div className="flex items-center gap-4 mb-6 flex-wrap">
        <div>
          <p className="text-xs text-gray-500 mb-1">آخر توقع</p>
          <motion.p
            initial={{ scale: 0.5, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.5, ease: [0.25, 0.25, 0, 1] }}
            className="text-2xl font-bold text-white"
          >
            {latest.predicted.toFixed(1)} <span className="text-sm font-medium text-gray-500">ج.م</span>
          </motion.p>
        </div>
        <div className="h-10 w-px bg-white/5" />
        <div>
          <p className="text-xs text-gray-500 mb-1">نطاق الثقة</p>
          <p className="text-sm font-semibold text-gray-300">
            {latest.lower.toFixed(1)} – {latest.upper.toFixed(1)} ج.م
          </p>
        </div>
        <div className="h-10 w-px bg-white/5" />
        <div>
          <p className="text-xs text-gray-500 mb-1">مستوى الثقة</p>
          <div className="flex items-center gap-2">
            <div className="h-2 w-20 rounded-full bg-white/5 overflow-hidden">
              <motion.div
                className="h-full rounded-full bg-gradient-to-l from-emerald-500 to-emerald-400"
                initial={{ width: 0 }}
                animate={{ width: "85%" }}
                transition={{ duration: 1, delay: 0.5 }}
              />
            </div>
            <span className="text-xs font-medium text-emerald-400">85%</span>
          </div>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={320}>
        <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.03)" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: "#6b7280", fontSize: 11, fontFamily: "Cairo, sans-serif" }}
            axisLine={false}
            tickLine={false}
            dy={10}
          />
          <YAxis tick={{ fill: "#6b7280", fontSize: 11 }} axisLine={false} tickLine={false} dx={-10} />
          <Tooltip content={<CustomTooltip />} cursor={{ stroke: "rgba(255,255,255,0.1)", strokeWidth: 1 }} />
          <defs>
            <linearGradient id="predictionGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.25} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="confidenceGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#10b981" stopOpacity={0.12} />
              <stop offset="95%" stopColor="#10b981" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <Area
            type="monotone"
            dataKey="upper"
            stroke="none"
            fill="url(#confidenceGradient)"
          />
          <Area
            type="monotone"
            dataKey="lower"
            stroke="none"
            fill="url(#confidenceGradient)"
          />
          <Area
            type="monotone"
            dataKey="predicted"
            stroke="#10b981"
            strokeWidth={2.5}
            fill="url(#predictionGradient)"
            name="السعر المتوقع"
            dot={false}
            activeDot={{ r: 5, strokeWidth: 2, stroke: "#10b981", fill: "#0a0a0f" }}
          />
          <ReferenceLine
            y={latest.predicted}
            stroke="rgba(16,185,129,0.2)"
            strokeDasharray="4 4"
          />
        </AreaChart>
      </ResponsiveContainer>

      <div className="flex items-center gap-4 mt-4 text-xs text-gray-500">
        <div className="flex items-center gap-2">
          <div className="w-4 h-0.5 rounded bg-emerald-500" />
          <span>السعر المتوقع</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-3 rounded bg-emerald-500/10 border border-emerald-500/30" />
          <span>نطاق الثقة 85%</span>
        </div>
      </div>
    </div>
  );
}
