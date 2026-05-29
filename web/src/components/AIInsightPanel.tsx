"use client";

import { motion } from "framer-motion";
import { BrainCircuit, TrendingUp, TrendingDown, Minus, Sparkles } from "lucide-react";

interface AIInsight {
  title: string;
  description: string;
  confidence: number;
  type: "positive" | "negative" | "neutral";
}

interface AIInsightPanelProps {
  insights: AIInsight[];
  delay?: number;
}

export default function AIInsightPanel({ insights, delay = 0 }: AIInsightPanelProps) {
  const typeConfig = {
    positive: {
      icon: TrendingUp,
      color: "text-emerald-400",
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/20",
      badge: "إيجابي",
    },
    negative: {
      icon: TrendingDown,
      color: "text-red-400",
      bg: "bg-red-500/10",
      border: "border-red-500/20",
      badge: "سلبي",
    },
    neutral: {
      icon: Minus,
      color: "text-blue-400",
      bg: "bg-blue-500/10",
      border: "border-blue-500/20",
      badge: "محايد",
    },
  };

  function getConfidenceLevel(score: number) {
    if (score >= 0.85) return { label: "ثقة عالية", color: "text-emerald-400" };
    if (score >= 0.7) return { label: "ثقة متوسطة", color: "text-gold-400" };
    return { label: "ثقة منخفضة", color: "text-red-400" };
  }

  return (
    <div className="space-y-4">
      {insights.map((insight, i) => {
        const config = typeConfig[insight.type];
        const Icon = config.icon;
        const confidence = getConfidenceLevel(insight.confidence);

        return (
          <motion.div
            key={insight.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: delay + i * 0.1, ease: [0.25, 0.25, 0, 1] }}
            className={`glass-sm rounded-xl p-5 border ${config.border} hover:bg-white/[0.03] transition-colors`}
          >
            <div className="flex items-start gap-4">
              <div className={`p-2.5 rounded-xl ${config.bg} shrink-0`}>
                <Icon className={`w-5 h-5 ${config.color}`} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                  <h3 className="text-sm font-semibold text-white">{insight.title}</h3>
                  <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${config.bg} ${config.color}`}>
                    {config.badge}
                  </span>
                </div>
                <p className="text-xs text-gray-400 leading-relaxed mb-3">{insight.description}</p>
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-1.5">
                    <Sparkles className="w-3 h-3 text-emerald-400" />
                    <span className="text-[10px] text-gray-500">AI</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="h-1.5 w-16 rounded-full bg-white/5 overflow-hidden">
                      <motion.div
                        className="h-full rounded-full bg-gradient-to-l from-emerald-500 to-emerald-400"
                        initial={{ width: 0 }}
                        animate={{ width: `${insight.confidence * 100}%` }}
                        transition={{ duration: 1, delay: delay + i * 0.1 + 0.3 }}
                      />
                    </div>
                    <span className={`text-[10px] font-medium ${confidence.color}`}>
                      {confidence.label}
                    </span>
                  </div>
                </div>
              </div>
              <div className="text-right shrink-0">
                <span className="text-lg font-bold text-white">
                  {(insight.confidence * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
}
