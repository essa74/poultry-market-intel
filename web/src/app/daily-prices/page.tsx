"use client";

import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import { Filter, Search, RefreshCw, Egg, Bird } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import GlassCard from "@/components/GlassCard";
import PriceChart from "@/components/PriceChart";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorDisplay from "@/components/ErrorDisplay";
import { usePricesList } from "@/lib/hooks/usePrices";
import { PRODUCT_TYPES } from "@/lib/constants";
import { ar } from "@/lib/ar";
import { PriceRecord } from "@/lib/api";

function getApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (typeof window !== "undefined") {
    const host = window.location.hostname;
    if (host === "localhost" || host === "127.0.0.1") {
      return "http://127.0.0.1:8000/api/v1";
    }
  }
  return "/api/v1";
}

const UNIT_LABELS: Record<string, string> = {
  per_tray: "للطبق",
  per_egg: "للبيضة",
  per_unit: "للواحدة",
  per_ton: "للطن",
  per_carton: "للكرتونة",
};

function unitLabel(record: { product_type: string; unit: string }): string {
  if (record.unit === "per_unit") {
    if (record.product_type === "fertilized_eggs") return "للبيضة";
    if (record.product_type === "day_old_chicks") return "للكتكوت";
    return "للواحدة";
  }
  return UNIT_LABELS[record.unit] || record.unit;
}

const CATEGORY_LABELS: Record<string, string> = {
  white: "أبيض",
  sasso: "ساسو",
  baladi: "بلدي",
  local: "محلي / فيومي وجميزة",
  duck: "بط",
  quail: "سمان",
  turkey: "رومي",
  ostrich: "نعام",
  brown: "بني",
  feed_corn: "ذرة",
  feed_soy: "صويا",
};

const ALL_CATEGORIES = [
  "white", "sasso", "baladi", "local", "duck", "quail", "turkey", "ostrich", "brown",
];

export default function DailyPricesPage() {
  const [selectedProduct, setSelectedProduct] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedSource, setSelectedSource] = useState("");

  const { data: prices, isLoading, isError, refetch } = usePricesList({
    product_type: selectedProduct || undefined,
    category: selectedCategory || undefined,
    limit: 100,
  });

  const sources = useMemo(() => {
    if (!prices?.length) return [];
    const unique = new Set<string>();
    prices.forEach((r) => { if (r.source) unique.add(r.source); });
    return Array.from(unique).sort();
  }, [prices]);

  const chartData = useMemo(() => {
    const grouped: Record<string, { eggs: number[]; chicks: number[] }> = {};
    (prices || []).forEach((r) => {
      const date = r.recorded_date;
      if (!grouped[date]) grouped[date] = { eggs: [], chicks: [] };
      if (r.product_type === "fertilized_eggs") grouped[date].eggs.push(r.price);
      else grouped[date].chicks.push(r.price);
    });
    return Object.entries(grouped)
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-20)
      .map(([date, vals]) => ({
        date: date.slice(5),
        eggs: vals.eggs.length ? Number((vals.eggs.reduce((s, p) => s + p, 0) / vals.eggs.length).toFixed(1)) : 0,
        chicks: vals.chicks.length ? Number((vals.chicks.reduce((s, p) => s + p, 0) / vals.chicks.length).toFixed(1)) : 0,
      }));
  }, [prices]);

  const filteredPrices = useMemo(() => {
    if (!prices) return [];
    if (!selectedSource) return prices;
    return prices.filter((r) => r.source === selectedSource);
  }, [prices, selectedSource]);

  // Stats
  const eggPrices = useMemo(() => (prices || []).filter((r) => r.product_type === "fertilized_eggs"), [prices]);
  const chickPrices = useMemo(() => (prices || []).filter((r) => r.product_type === "day_old_chicks"), [prices]);
  const eggAvg = eggPrices.length ? (eggPrices.reduce((s, r) => s + r.price, 0) / eggPrices.length).toFixed(1) : null;
  const chickAvg = chickPrices.length ? (chickPrices.reduce((s, r) => s + r.price, 0) / chickPrices.length).toFixed(1) : null;

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <PageHeader
          title="أسعار السوق"
          subtitle="جميع أسعار السوق المسجلة — البيض المخصب والكتاكيت والأعلاف"
          badge="محدث"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
        <GlassCard glow="emerald">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-xl bg-emerald-500/10">
              <Egg className="w-5 h-5 text-emerald-400" />
            </div>
            <div>
              <p className="text-sm text-gray-400">متوسط السعر — البيض المخصب</p>
              <p className="text-2xl font-bold text-white">
                {eggAvg || "---"}
                <span className="text-sm font-medium text-gray-500 mr-1">ج.م</span>
              </p>
            </div>
          </div>
          <p className="text-xs text-gray-500">إجمالي {eggPrices.length} سجل</p>
        </GlassCard>
        <GlassCard glow="gold">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 rounded-xl bg-gold-500/10">
              <Bird className="w-5 h-5 text-gold-400" />
            </div>
            <div>
              <p className="text-sm text-gray-400">متوسط السعر — كتاكيت عمر يوم</p>
              <p className="text-2xl font-bold text-white">
                {chickAvg || "---"}
                <span className="text-sm font-medium text-gray-500 mr-1">ج.م</span>
              </p>
            </div>
          </div>
          <p className="text-xs text-gray-500">إجمالي {chickPrices.length} سجل</p>
        </GlassCard>
      </div>

      <GlassCard glow="emerald" className="mb-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-white">اتجاه الأسعار</h2>
          <div className="flex items-center gap-3 text-xs">
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-0.5 rounded bg-emerald-500" />
              <span className="text-gray-400">البيض</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-3 h-0.5 rounded bg-gold-500" />
              <span className="text-gray-400">الكتاكيت</span>
            </div>
          </div>
        </div>
        {chartData.length > 0 ? (
          <PriceChart data={chartData} height={280} />
        ) : (
          <div className="h-[280px] flex flex-col items-center justify-center text-gray-500 text-sm">
            <span className="mb-1">{ar.common.noMarketData}</span>
            <span className="text-xs text-gray-600">{ar.common.awaitingFirstCollection}</span>
          </div>
        )}
      </GlassCard>

      <GlassCard>
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <h2 className="text-lg font-semibold text-white">جدول الأسعار</h2>
          <div className="flex items-center gap-3 flex-wrap">
            <div className="flex items-center gap-2 glass-sm rounded-xl px-3 py-2">
              <Filter className="w-4 h-4 text-gray-400 shrink-0" />
              <select
                value={selectedProduct}
                onChange={(e) => setSelectedProduct(e.target.value)}
                className="bg-transparent text-xs text-gray-300 border-none outline-none focus:ring-0 cursor-pointer"
              >
                <option value="" className="bg-surface">جميع المنتجات</option>
                {PRODUCT_TYPES.map((pt) => (
                  <option key={pt.value} value={pt.value} className="bg-surface">{pt.label}</option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-2 glass-sm rounded-xl px-3 py-2">
              <Search className="w-4 h-4 text-gray-400 shrink-0" />
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="bg-transparent text-xs text-gray-300 border-none outline-none focus:ring-0 cursor-pointer"
              >
                <option value="" className="bg-surface">جميع التصنيفات</option>
                {ALL_CATEGORIES.map((c) => (
                  <option key={c} value={c} className="bg-surface">{CATEGORY_LABELS[c] || c}</option>
                ))}
              </select>
            </div>
            {sources.length > 0 && (
              <div className="flex items-center gap-2 glass-sm rounded-xl px-3 py-2">
                <Search className="w-4 h-4 text-gray-400 shrink-0" />
                <select
                  value={selectedSource}
                  onChange={(e) => setSelectedSource(e.target.value)}
                  className="bg-transparent text-xs text-gray-300 border-none outline-none focus:ring-0 cursor-pointer"
                >
                  <option value="" className="bg-surface">جميع المصادر</option>
                  {sources.map((s) => (
                    <option key={s} value={s} className="bg-surface">{s}</option>
                  ))}
                </select>
              </div>
            )}
            <button
              onClick={() => refetch()}
              className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white transition-colors glass-sm rounded-xl px-3 py-2"
            >
              <RefreshCw className="w-4 h-4" />
              {ar.common.refresh}
            </button>
          </div>
        </div>

        {isLoading ? (
          <LoadingSpinner size="sm" text={ar.common.loading} />
        ) : isError ? (
          <ErrorDisplay onRetry={() => refetch()} />
        ) : !filteredPrices.length ? (
          <div className="text-center py-12">
            <p className="text-sm text-gray-500">لا توجد أسعار مسجلة لهذه التصفية</p>
            <p className="text-xs text-gray-600 mt-1">{ar.common.awaitingFirstCollection}</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/5">
                  <th className="text-right py-3 px-3 text-xs font-medium text-gray-500">المنتج</th>
                  <th className="text-right py-3 px-3 text-xs font-medium text-gray-500">التصنيف</th>
                  <th className="text-right py-3 px-3 text-xs font-medium text-gray-500">الوصف</th>
                  <th className="text-right py-3 px-3 text-xs font-medium text-gray-500">السعر</th>
                  <th className="text-right py-3 px-3 text-xs font-medium text-gray-500">الوحدة</th>
                  <th className="text-right py-3 px-3 text-xs font-medium text-gray-500">المصدر</th>
                  <th className="text-right py-3 px-3 text-xs font-medium text-gray-500">التاريخ</th>
                </tr>
              </thead>
              <tbody>
                {filteredPrices.map((record, i) => (
                  <motion.tr
                    key={record.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2, delay: i * 0.02 }}
                    className="border-b border-white/5 hover:bg-white/[0.02] transition-colors"
                  >
                    <td className="py-3 px-3">
                      <span className="text-white font-medium">
                        {record.product_type === "fertilized_eggs" ? "بيض مخصب" :
                         record.product_type === "day_old_chicks" ? "كتاكيت" : "أعلاف"}
                      </span>
                    </td>
                    <td className="py-3 px-3 text-gray-400">{CATEGORY_LABELS[record.category] || record.category}</td>
                    <td className="py-3 px-3 text-gray-400 max-w-[200px] truncate" title={record.raw_product_name || ""}>
                      {record.raw_product_name || "-"}
                    </td>
                    <td className="py-3 px-3">
                      <span className="font-semibold text-white">{record.price.toFixed(1)}</span>
                      <span className="text-xs text-gray-500 mr-1">ج.م</span>
                    </td>
                    <td className="py-3 px-3 text-gray-400">{unitLabel(record)}</td>
                    <td className="py-3 px-3 text-gray-400">{record.source || "-"}</td>
                    <td className="py-3 px-3 text-xs text-gray-500">{record.recorded_date}</td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </GlassCard>
    </div>
  );
}