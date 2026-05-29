"use client";

import { motion } from "framer-motion";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import GlassCard from "./GlassCard";

interface StatCardProps {
  title: string;
  value: string;
  subtitle: string;
  change: number;
  icon: React.ReactNode;
  delay?: number;
  format?: "price" | "percent";
}

export default function StatCard({
  title,
  value,
  subtitle,
  change,
  icon,
  delay = 0,
  format = "price",
}: StatCardProps) {
  const isUp = change > 0;
  const isDown = change < 0;

  return (
    <GlassCard glow={isUp ? "emerald" : isDown ? "gold" : "blue"} delay={delay}>
      <div className="flex items-start justify-between mb-4">
        <span className="text-xs font-medium text-gray-500 uppercase tracking-wider">
          {title}
        </span>
        <div className={`p-2 rounded-xl ${
          isUp ? "bg-emerald-500/10 text-emerald-400" :
          isDown ? "bg-red-500/10 text-red-400" :
          "bg-blue-500/10 text-blue-400"
        }`}>
          {icon}
        </div>
      </div>
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: delay + 0.2, ease: [0.25, 0.25, 0, 1] }}
      >
        <div className="stat-value text-white">{value}</div>
      </motion.div>
      <div className="flex items-center gap-2 mt-2">
        <div className={`flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-md ${
          isUp ? "text-emerald-400 bg-emerald-500/10" :
          isDown ? "text-red-400 bg-red-500/10" :
          "text-gray-400 bg-white/5"
        }`}>
          {isUp ? <TrendingUp className="w-3 h-3" /> : isDown ? <TrendingDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
          {format === "percent" ? `${Math.abs(change).toFixed(1)}%` : `${isUp ? "+" : ""}${change.toFixed(1)}`}
        </div>
        <span className="text-xs text-gray-500">{subtitle}</span>
      </div>
    </GlassCard>
  );
}
