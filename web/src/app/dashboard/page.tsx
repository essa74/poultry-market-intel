"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import {
  Egg, Bird, BarChart3,
  BrainCircuit, Eye, RefreshCw,
} from "lucide-react";
import PageHeader from "@/components/PageHeader";
import StatCard from "@/components/StatCard";
import GlassCard from "@/components/GlassCard";
import PriceChart from "@/components/PriceChart";
import TrendIndicator from "@/components/TrendIndicator";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorDisplay from "@/components/ErrorDisplay";
import { usePricesList, useLatestPrices } from "@/lib/hooks/usePrices";
import { PriceRecord } from "@/lib/api";
import { ar } from "@/lib/ar";

const FERTILIZED_EGG_CATEGORIES = [
  "white", "sasso", "baladi", "local", "duck", "quail", "turkey", "ostrich",
];

const CATEGORY_LABELS: Record<string, string> = {
  white: "أبيض",
  sasso: "ساسو",
  baladi: "بلدي",
  local: "محلي / فيومي وجميزة",
  duck: "بط",
  quail: "سمان",
  turkey: "رومي",
  ostrich: "نعام",
};

export default function DashboardPage() {
  const { data: eggRecords, isLoading: eggLoading, isError: eggError, refetch: refetchEgg } = usePricesList({
    product_type: "fertilized_eggs",
    limit: 50,
  });

  const { data: chickRecords, isLoading: chickLoading, isError: chickError, refetch: refetchChick } = usePricesList({
    product_type: "day_old_chicks",
    limit: 50,
  });

  const { data: latestEggs } = useLatestPrices({ product_type: "fertilized_eggs", limit: 50 });
  const { data: latestChicks } = useLatestPrices({ product_type: "day_old_chicks", limit: 50 });
  const { data: latestAll } = useLatestPrices({ limit: 50 });

  const latestByCategory = useMemo(() => {
    const map: Record<string, PriceRecord> = {};
    (latestEggs || []).forEach((r) => {
      if (!map[r.category]) map[r.category] = r;
    });
    return map;
  }, [latestEggs]);

  const eggCards = useMemo(() => {
    return FERTILIZED_EGG_CATEGORIES.map((cat) => ({
      category: cat,
      label: CATEGORY_LABELS[cat] || cat,
      record: latestByCategory[cat] as PriceRecord | undefined,
    }));
  }, [latestByCategory]);

  const weeklyTrend = useMemo(() => {
    const allEggs = eggRecords || [];
    const allChicks = chickRecords || [];

    const grouped: Record<string, { eggs: number[]; chicks: number[] }> = {};
    allEggs.forEach((r) => {
      const date = r.recorded_date;
      if (!grouped[date]) grouped[date] = { eggs: [], chicks: [] };
      grouped[date].eggs.push(r.price);
    });
    allChicks.forEach((r) => {
      const date = r.recorded_date;
      if (!grouped[date]) grouped[date] = { eggs: [], chicks: [] };
      grouped[date].chicks.push(r.price);
    });

    return Object.entries(grouped)
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-12)
      .map(([date, vals]) => ({
        date: date.slice(5),
        eggs: vals.eggs.length ? Number((vals.eggs.reduce((s, p) => s + p, 0) / vals.eggs.length).toFixed(1)) : 0,
        chicks: vals.chicks.length ? Number((vals.chicks.reduce((s, p) => s + p, 0) / vals.chicks.length).toFixed(1)) : 0,
      }));
  }, [eggRecords, chickRecords]);

  const hasData = (latestAll || []).length > 0;
  const isLoading = eggLoading || chickLoading;
  const isError = eggError || chickError;

  if (isError) {
    return (
      <div>
        <PageHeader title={ar.dashboard.title} subtitle={ar.dashboard.subtitle} badge="مباشر" />
        <ErrorDisplay onRetry={() => { refetchEgg(); refetchChick(); }} />
      </div>
    );
  }

  if (!hasData && !isLoading) {
    return (
      <div>
        <PageHeader title={ar.dashboard.title} subtitle={ar.dashboard.subtitle} badge="مباشر" />
        <GlassCard>
          <div className="text-center py-12">
            <Egg className="w-10 h-10 mx-auto text-gray-600 mb-3" />
            <p className="text-sm text-gray-500">{ar.common.noRealData}</p>
            <p className="text-xs text-gray-600 mt-1">{ar.common.awaitingFirstCollection}</p>
          </div>
        </GlassCard>
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title={ar.dashboard.title}
        subtitle={ar.dashboard.subtitle}
        badge="مباشر"
      />

      {isLoading ? (
        <LoadingSpinner text={ar.common.loading} />
      ) : (
        <>
          <div className="mb-6">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-white">أسعار البيض المخصب — آخر التحديثات</h2>
              <button onClick={() => { refetchEgg(); refetchChick(); }} className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors">
                <RefreshCw className="w-4 h-4" />
              </button>
            </div>
            {eggCards.filter(c => c.record).length > 0 ? (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-8 gap-3">
                {eggCards.filter(c => c.record).map(({ category, label, record }, i) => (
                  <StatCard
                    key={category}
                    title={record?.raw_product_name || label}
                    value={record ? `${record.price} ج.م` : "---"}
                    subtitle={`${label} · ${record?.source || ""}${record?.recorded_date ? ` · ${record.recorded_date}` : ""}`}
                    change={0}
                    icon={<Egg className="w-4 h-4" />}
                    delay={0.05 * i}
                  />
                ))}
              </div>
            ) : (
              <GlassCard glow="none" hover={false}>
                <div className="text-center py-8">
                  <p className="text-sm text-gray-500">{ar.common.noRealData}</p>
                  <p className="text-xs text-gray-600 mt-1">{ar.common.awaitingFirstCollection}</p>
                </div>
              </GlassCard>
            )}
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            <GlassCard className="lg:col-span-2" glow="emerald">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-lg font-semibold text-white">{ar.dashboard.weeklyTrend}</h2>
                  <p className="text-xs text-gray-500 mt-0.5">آخر {weeklyTrend.length} سجل</p>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <div className="flex items-center gap-1.5">
                    <div className="w-3 h-0.5 rounded bg-emerald-500" />
                    <span className="text-gray-400">{ar.dashboard.eggTrend}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className="w-3 h-0.5 rounded bg-gold-500" />
                    <span className="text-gray-400">{ar.dashboard.chickTrend}</span>
                  </div>
                </div>
              </div>
              {weeklyTrend.length > 0 ? (
                <PriceChart data={weeklyTrend} />
              ) : (
                <div className="h-[300px] flex flex-col items-center justify-center text-gray-500 text-sm">
                  <span className="mb-1">{ar.common.noRealData}</span>
                  <span className="text-xs text-gray-600">{ar.common.awaitingFirstCollection}</span>
                </div>
              )}
            </GlassCard>

            <GlassCard glow="blue">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-lg font-semibold text-white">{ar.dashboard.recentTrend}</h2>
                  <p className="text-xs text-gray-500 mt-0.5">مؤشرات سريعة</p>
                </div>
                <Eye className="w-5 h-5 text-blue-400" />
              </div>
              {(latestChicks ?? []).length > 0 ? (
              <div className="space-y-3">
                {(latestChicks ?? []).slice(0, 4).map((record, i) => (
                  <TrendIndicator
                    key={record.id}
                    label={record.raw_product_name || `كتاكيت ${record.category}`}
                    value={`${record.price} ج.م`}
                    change={0}
                    changeLabel={ar.dashboard.changeFromLastWeek}
                    icon={<Bird className="w-4 h-4" />}
                    delay={0.2 + i * 0.1}
                  />
                ))}
                <div className="flex items-center gap-2 text-xs text-gray-500 glass-sm rounded-xl p-3">
                  <BarChart3 className="w-4 h-4 text-emerald-400" />
                  <span>عدد السجلات: <span className="text-white font-medium">{(eggRecords?.length || 0) + (chickRecords?.length || 0)}</span></span>
                </div>
              </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-sm text-gray-500">{ar.common.noRealData}</p>
                  <p className="text-xs text-gray-600 mt-1">{ar.common.awaitingFirstCollection}</p>
                </div>
              )}
              {(latestAll || []).length > 0 ? (
              <div className="space-y-3">
                {(latestAll || []).slice(0, 8).map((record, i) => (
                  <motion.div
                    key={record.id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3, delay: 0.1 + i * 0.05 }}
                    className="flex items-center justify-between py-2 border-b border-white/5 last:border-0"
                  >
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-sm text-gray-300 truncate">
                          {record.raw_product_name || (record.product_type === "fertilized_eggs" ? "بيض مخصب" : record.product_type === "day_old_chicks" ? "كتاكيت" : "أعلاف")}
                        </span>
                        {record.category && (
                          <span className="badge-green text-[9px] shrink-0">{CATEGORY_LABELS[record.category] || record.category}</span>
                        )}
                      </div>
                      <p className="text-xs text-gray-600">
                        {record.source} · {record.recorded_date}
                      </p>
                    </div>
                    <span className="text-sm font-semibold text-emerald-400 pr-3 shrink-0">
                      {record.price.toFixed(1)} ج.م
                    </span>
                  </motion.div>
                ))}
              </div>
              ) : (
                <div className="text-center py-8">
                  <p className="text-sm text-gray-500">{ar.common.noRealData}</p>
                  <p className="text-xs text-gray-600 mt-1">{ar.common.awaitingFirstCollection}</p>
                </div>
              )}

              <div className="glow-line mt-4 mb-4" />
              <div className="text-center">
                <span className="text-xs text-gray-500">
                  آخر تحديث: {new Date().toLocaleDateString("ar-EG")}
                </span>
              </div>
            </GlassCard>
          </div>
        </>
      )}
    </div>
  );
}