"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  LayoutDashboard,
  BarChart3,
  CalendarDays,
  BrainCircuit,
  Newspaper,
  Egg,
  ChevronLeft,
  X,
  Shield,
  Home,
  PenLine,
  HardDrive,
} from "lucide-react";
import { useState } from "react";
import { ar } from "@/lib/ar";
import BrandCredit from "@/components/BrandCredit";

const navItems = [
  { href: "/", label: ar.nav.home, icon: Home },
  { href: "/dashboard", label: ar.nav.dashboard, icon: LayoutDashboard },
  { href: "/news", label: ar.nav.news, icon: Newspaper },
  { href: "/market-trends", label: ar.nav.trends, icon: BarChart3 },
  { href: "/seasonal-analysis", label: ar.nav.seasonal, icon: CalendarDays },
  { href: "/ai-insights", label: ar.nav.aiInsights, icon: BrainCircuit },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      <button
        onClick={() => setMobileOpen(true)}
        className="lg:hidden fixed top-4 right-4 z-50 glass-sm p-2.5 rounded-xl text-white"
        aria-label="فتح القائمة"
      >
        <ChevronLeft className="w-5 h-5" />
      </button>

      <AnimatePresence>
        {mobileOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm lg:hidden"
            onClick={() => setMobileOpen(false)}
          />
        )}
      </AnimatePresence>

      <aside
        className={`fixed top-0 right-0 z-50 h-full w-72 lg:w-64 xl:w-72 bg-surface/80 backdrop-blur-2xl border-l border-white/5 flex flex-col transition-transform duration-300 lg:translate-x-0 ${
          mobileOpen ? "translate-x-0" : "translate-x-full lg:translate-x-0"
        }`}
      >
        {mobileOpen && (
          <button
            onClick={() => setMobileOpen(false)}
            className="lg:hidden absolute top-4 left-4 p-2 rounded-xl text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        )}

        <div className="p-6 border-b border-white/5">
          <Link href="/" className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center shadow-lg shadow-emerald-500/20">
              <Egg className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-base font-bold text-white tracking-tight">
                توقعات سوق الدواجن
              </h1>
              <p className="text-[10px] text-gray-500 font-medium">
                منصة تحليل الأسواق
              </p>
            </div>
          </Link>
        </div>

        <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            const Icon = item.icon;
            return (
              <Link key={item.href} href={item.href} onClick={() => setMobileOpen(false)}>
                <motion.div
                  whileHover={{ x: -2 }}
                  whileTap={{ scale: 0.98 }}
                  className={`sidebar-link group ${isActive ? "active" : ""}`}
                >
                  <Icon className={`w-5 h-5 transition-colors ${isActive ? "text-emerald-400" : "text-gray-500 group-hover:text-gray-300"}`} />
                  <span className="flex-1">{item.label}</span>
                  {isActive && (
                    <motion.div
                      layoutId="activeNav"
                      className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400/50"
                    />
                  )}
                </motion.div>
              </Link>
            );
          })}

          <div className="my-4 glow-line" />

          <Link href="/admin/prices" onClick={() => setMobileOpen(false)}>
            <motion.div
              whileHover={{ x: -2 }}
              whileTap={{ scale: 0.98 }}
              className={`sidebar-link group ${pathname === "/admin/prices" ? "active" : ""}`}
            >
              <PenLine className={`w-5 h-5 transition-colors ${pathname === "/admin/prices" ? "text-emerald-400" : "text-gray-500 group-hover:text-gray-300"}`} />
              <span className="flex-1">{ar.nav.pricesEntry}</span>
              {pathname === "/admin/prices" && (
                <motion.div layoutId="activeNav" className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400/50" />
              )}
            </motion.div>
          </Link>

          <Link href="/admin/scraping" onClick={() => setMobileOpen(false)}>
            <motion.div
              whileHover={{ x: -2 }}
              whileTap={{ scale: 0.98 }}
              className={`sidebar-link group ${pathname === "/admin/scraping" ? "active" : ""}`}
            >
              <HardDrive className={`w-5 h-5 transition-colors ${pathname === "/admin/scraping" ? "text-emerald-400" : "text-gray-500 group-hover:text-gray-300"}`} />
              <span className="flex-1">إدارة المصادر</span>
              {pathname === "/admin/scraping" && (
                <motion.div layoutId="activeNav" className="w-1.5 h-1.5 rounded-full bg-emerald-400 shadow-sm shadow-emerald-400/50" />
              )}
            </motion.div>
          </Link>
        </nav>

        {/* BrandCredit — absolute bottom of sidebar = far bottom-right of viewport in RTL */}
        <div className="absolute bottom-3 left-0 right-0 flex justify-center pointer-events-none">
          <div className="pointer-events-auto">
            <BrandCredit variant="footer" />
          </div>
        </div>
      </aside>
    </>
  );
}
