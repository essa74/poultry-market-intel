"use client";

import { motion } from "framer-motion";

type Variant = "hero" | "footer";

interface BrandCreditProps {
  variant?: Variant;
  className?: string;
}

const TEXT = "تم تطويره بواسطة عيسى العفيفي بمساعدة أدوات الذكاء الاصطناعي";

const variantStyles: Record<Variant, {
  container: string;
  text: string;
  dot: string;
}> = {
  hero: {
    container:
      "glass-sm rounded-2xl border border-emerald-500/30 shadow-lg shadow-emerald-500/15 backdrop-blur-2xl px-6 py-4 inline-flex items-center gap-3",
    text:
      "text-sm md:text-base font-semibold text-gray-100",
    dot:
      "w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-sm shadow-emerald-400/50",
  },
  footer: {
    container:
      "glass-sm rounded-2xl border border-emerald-500/25 shadow-md shadow-emerald-500/10 backdrop-blur-2xl px-5 py-3 inline-flex items-center gap-2.5",
    text:
      "text-xs md:text-sm font-medium text-gray-200",
    dot:
      "w-1.5 h-1.5 rounded-full bg-emerald-400/70",
  },

};

export default function BrandCredit({ variant = "footer", className = "" }: BrandCreditProps) {
  const styles = variantStyles[variant];

  const content = (
    <span className={`${styles.text} ${className}`}>
      {TEXT}
    </span>
  );

  if (variant === "hero") {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.8, ease: [0.25, 0.25, 0, 1] }}
        className={styles.container}
        dir="rtl"
      >
        <span className={styles.dot} />
        {content}
      </motion.div>
    );
  }

  // footer
  return (
    <div className={styles.container} dir="rtl">
      <span className={styles.dot} />
      {content}
    </div>
  );
}
