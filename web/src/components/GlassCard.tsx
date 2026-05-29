"use client";

import { motion } from "framer-motion";

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  glow?: "emerald" | "gold" | "blue" | "none";
  hover?: boolean;
  delay?: number;
  onClick?: (e: React.MouseEvent) => void;
}

export default function GlassCard({
  children,
  className = "",
  glow = "none",
  hover = true,
  delay = 0,
  onClick,
}: GlassCardProps) {
  const glowStyles = {
    emerald: "hover:shadow-glow hover:border-emerald-500/20",
    gold: "hover:shadow-glow-gold hover:border-gold-500/20",
    blue: "hover:shadow-[0_0_20px_rgba(59,130,246,0.15)] hover:border-blue-500/20",
    none: "",
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: [0.25, 0.25, 0, 1] }}
      whileHover={hover ? { y: -2, transition: { duration: 0.2 } } : undefined}
      onClick={onClick}
      className={`glass rounded-2xl p-6 ${glowStyles[glow]} ${
        onClick || hover ? "glass-hover cursor-pointer" : ""
      } ${className}`}
    >
      {children}
    </motion.div>
  );
}
