"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowLeft,
  TrendingUp,
  CalendarDays,
  Newspaper,
  Sparkles,
  BarChart3,
  DollarSign,
  LineChart,
  Brain,
} from "lucide-react";
import BrandCredit from "@/components/BrandCredit";

export default function Home() {
  const [showSplash, setShowSplash] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => setShowSplash(false), 1800);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="min-h-screen bg-surface overflow-hidden relative">
      {/* Loading/intro splash — shows BrandCredit immediately, fades away */}
      <AnimatePresence>
        {showSplash && (
          <motion.div
            key="splash"
            initial={{ opacity: 1 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, transition: { duration: 0.6 } }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-surface pointer-events-none"
          >
            <motion.div
              initial={{ opacity: 0, scale: 0.92 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.96 }}
              transition={{ duration: 0.5, ease: [0.25, 0.25, 0, 1] }}
            >
              <BrandCredit variant="hero" />
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="absolute inset-0 bg-gradient-radial from-emerald-500/[0.04] via-transparent to-transparent pointer-events-none" />
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl" />
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-amber-500/5 rounded-full blur-3xl" />

      <div className="relative z-10 max-w-6xl mx-auto px-6 py-20">
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.25, 0.25, 0, 1], delay: 0.1 }}
          className="text-center mb-20"
        >
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.6, ease: [0.25, 0.25, 0, 1], delay: 0.2 }}
            className="inline-flex items-center gap-2 glass-sm rounded-full px-4 py-2 mb-8"
          >
            <Sparkles className="w-4 h-4 text-emerald-400" />
            <span className="text-xs text-emerald-400 font-medium">
              توقعات سوق الدواجن — مدعومة بالذكاء الاصطناعي
            </span>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.3 }}
            className="text-5xl md:text-7xl font-black text-white mb-6 leading-tight"
          >
            <span className="gradient-text">توقعات</span>
            <br />
            <span>سوق الدواجن</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="text-lg text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed"
          >
            منصة ذكية لتحليل سوق البيض المخصب والكتاكيت والأعلاف ومؤشرات بورصة الدواجن في مصر
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.5 }}
            className="flex items-center justify-center gap-4 flex-wrap"
          >
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 bg-gradient-to-l from-emerald-600 to-emerald-500 text-white px-8 py-3.5 rounded-2xl font-semibold shadow-lg shadow-emerald-500/20 hover:shadow-emerald-500/30 hover:from-emerald-500 hover:to-emerald-400 transition-all duration-300"
            >
              دخول لوحة التحكم
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <Link
              href="/news"
              className="inline-flex items-center gap-2 glass-sm text-gray-300 px-8 py-3.5 rounded-2xl font-medium hover:bg-white/5 hover:text-white transition-all duration-300"
            >
              الأخبار
              <Newspaper className="w-4 h-4" />
            </Link>
            <Link
              href="/daily-prices"
              className="inline-flex items-center gap-2 glass-sm text-gray-300 px-8 py-3.5 rounded-2xl font-medium hover:bg-white/5 hover:text-white transition-all duration-300"
            >
              الأسعار اليومية
              <TrendingUp className="w-4 h-4" />
            </Link>
          </motion.div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.6, ease: [0.25, 0.25, 0, 1] }}
          className="grid md:grid-cols-2 lg:grid-cols-3 gap-6"
        >
          {[
            { icon: DollarSign, title: "الأسعار اليومية", desc: "أسعار البيض المخصب والكتاكيت والأعلاف محدثة يومياً", href: "/daily-prices", glow: "emerald" as const },
            { icon: LineChart, title: "التوقعات السعرية", desc: "توقعات الأسعار باستخدام الذكاء الاصطناعي وتحليل السلاسل الزمنية", href: "/predictions", glow: "gold" as const },
            { icon: CalendarDays, title: "التحليل الموسمي", desc: "تحليل الموسمية وتأثير الأعياد والمواسم على أسعار السوق", href: "/seasonal-analysis", glow: "blue" as const },
            { icon: BarChart3, title: "اتجاهات السوق", desc: "اتجاهات الأسعار ومقارنات المناطق والمؤشرات السعرية", href: "/market-trends", glow: "emerald" as const },
            { icon: Brain, title: "رؤى الذكاء الاصطناعي", desc: "تحليلات ذكية وتوصيات مبنية على بيانات السوق التاريخية", href: "/ai-insights", glow: "gold" as const },
            { icon: Newspaper, title: "الأخبار", desc: "آخر أخبار قطاع الدواجن والأعلاف وأسواق المخصب والكتاكيت", href: "/news", glow: "blue" as const },
          ].map((feature, i) => (
            <Link key={feature.title} href={feature.href}>
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5, delay: 0.7 + i * 0.1 }}
                whileHover={{ y: -4 }}
                className="glass rounded-2xl p-6 glass-hover group h-full"
              >
                <div className={`p-3 rounded-xl w-fit mb-4 transition-colors ${
                  feature.glow === "emerald" ? "bg-emerald-500/10 text-emerald-400 group-hover:bg-emerald-500/20" :
                  feature.glow === "gold" ? "bg-gold-500/10 text-gold-400 group-hover:bg-gold-500/20" :
                  "bg-blue-500/10 text-blue-400 group-hover:bg-blue-500/20"
                }`}>
                  <feature.icon className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
                <p className="text-sm text-gray-400 leading-relaxed">{feature.desc}</p>
              </motion.div>
            </Link>
          ))}
        </motion.div>

        {/* Status bar */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 1.2 }}
          className="text-center mt-20"
        >
          <div className="glass-sm inline-flex items-center gap-6 rounded-2xl px-8 py-4">
            <div className="flex items-center gap-3">
              <Sparkles className="w-5 h-5 text-emerald-400" />
              <span className="text-sm text-gray-400">آخر تحديث:</span>
              <span className="text-sm font-medium text-white">{new Date().toLocaleDateString("ar-EG")}</span>
            </div>
            <div className="h-6 w-px bg-white/5" />
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-sm text-emerald-400 font-medium">النظام نشط</span>
            </div>
          </div>
        </motion.div>

        {/* Brand credit — below status bar */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.6, delay: 1.4 }}
          className="flex justify-center mt-6"
        >
          <BrandCredit variant="hero" />
        </motion.div>
      </div>
    </div>
  );
}
