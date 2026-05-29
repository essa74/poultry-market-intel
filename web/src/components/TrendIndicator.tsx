"use client";

import { motion } from "framer-motion";
import GlassCard from "./GlassCard";
import { TrendingUp, TrendingDown } from "lucide-react";

interface TrendIndicatorProps {
  label: string;
  value: string;
  change: number;
  changeLabel: string;
  icon?: React.ReactNode;
  delay?: number;
}

export default function TrendIndicator({
  label,
  value,
  change,
  changeLabel,
  icon,
  delay = 0,
}: TrendIndicatorProps) {
  const isUp = change > 0;
  const isDown = change < 0;

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.4, delay, ease: [0.25, 0.25, 0, 1] }}
      className="glass-sm rounded-xl p-4 flex items-center justify-between"
    >
      <div className="flex items-center gap-3">
        {icon && (
          <div className={`p-2 rounded-lg ${
            isUp ? "bg-emerald-500/10" : isDown ? "bg-red-500/10" : "bg-white/5"
          }`}>
            {icon}
          </div>
        )}
        <div>
          <p className="text-xs text-gray-500">{label}</p>
          <p className="text-sm font-semibold text-white mt-0.5">{value}</p>
        </div>
      </div>
      <div className={`flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-lg ${
        isUp ? "text-emerald-400 bg-emerald-500/10" : isDown ? "text-red-400 bg-red-500/10" : "text-gray-400 bg-white/5"
      }`}>
        {isUp ? <TrendingUp className="w-3.5 h-3.5" /> : <TrendingDown className="w-3.5 h-3.5" />}
        <span>{isUp ? "+" : ""}{change.toFixed(1)}%</span>
        <span className="text-[10px] opacity-70">{changeLabel}</span>
      </div>
    </motion.div>
  );
}
