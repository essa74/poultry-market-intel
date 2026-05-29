"use client";

import { motion } from "framer-motion";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  badge?: string;
}

export default function PageHeader({ title, subtitle, badge }: PageHeaderProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.25, 0, 1] }}
      className="mb-8"
    >
      <div className="flex items-center gap-3 mb-1">
        <h1 className="text-2xl md:text-3xl font-bold text-white">{title}</h1>
        {badge && (
          <span className="badge-green text-[10px]">{badge}</span>
        )}
      </div>
      {subtitle && (
        <p className="text-sm text-gray-500 mt-1">{subtitle}</p>
      )}
      <div className="glow-line mt-4" />
    </motion.div>
  );
}
