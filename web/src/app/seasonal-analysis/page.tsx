"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { CalendarDays, TrendingUp, TrendingDown, Info, RefreshCw, Egg, Bird, Wheat } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import GlassCard from "@/components/GlassCard";
import SeasonalEventCard from "@/components/SeasonalEventCard";
import PriceChart from "@/components/PriceChart";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorDisplay from "@/components/ErrorDisplay";
import { usePricesList } from "@/lib/hooks/usePrices";
import { useHolidaysList } from "@/lib/hooks/useHolidays";
import { ar } from "@/lib/ar";

const EVENT_TYPE_ICONS: Record<string, string> = {
  ramadan: "moon",
  eid_fitr: "star",
  eid_adha: "star",
  coptic_christmas: "cross",
  easter: "cross",
  sham_el_nessim: "flower",
  winter: "snow",
  school: "book",
  summer_heat: "sun",
};

const EVENT_TYPE_LABELS: Record<string, string> = {
  ramadan: "رمضان",
  eid_fitr: "أعياد",
  eid_adha: "أعياد",
  coptic_christmas: "مسيحي",
  easter: "مسيحي",
  sham_el_nessim: "موسمي",
  winter: "فصلي",
  school: "موسمي",
  summer_heat: "فصلي",
};

function formatDate(d: string) {
  const date = new Date(d);
  return date.toLocaleDateString("ar-EG", { month: "short", day: "numeric" });
}

export default function SeasonalAnalysisPage() {
  const today = new Date();
  const threeYearsAgo = new Date();
  threeYearsAgo.setFullYear(threeYearsAgo.getFullYear() - 3);

  const { data: eggData, isLoading, isError, refetch } = usePricesList({
    product_type: "fertilized_eggs",
    start_date: threeYearsAgo.toISOString().split("T")[0],
    limit: 500,
  });

  const { data: holidays } = useHolidaysList({
    from_date: today.toISOString().split("T")[0],
    limit: 50,
  });

  const seasonalEvents = useMemo(() => {
    if (!holidays?.length) return [];
    return holidays.map((h) => ({
      name: h.name_ar,
      type: EVENT_TYPE_LABELS[h.event_type] || h.event_type,
      impact: h.impact_description || "---",
      impactValue: h.impact_percentage || 0,
      icon: EVENT_TYPE_ICONS[h.event_type] || "star",
      startDate: formatDate(h.start_date),
      endDate: formatDate(h.end_date),
    }));
  }, [holidays]);

  const monthlyData = useMemo(() => {
    if (!eggData?.length) return [];
    const byMonth: Record<string, number[]> = {};
    eggData.forEach((r) => {
      const date = new Date(r.recorded_date);
      const monthKey = date.getMonth();
      if (!byMonth[monthKey]) byMonth[monthKey] = [];
      byMonth[monthKey].push(r.price);
    });

    const monthNames = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"];

    return monthNames.map((month, i) => {
      const prices = byMonth[i] || [];
      return {
        month,
        eggs: prices.length ? Number((prices.reduce((s, p) => s + p, 0) / prices.length).toFixed(1)) : 0,
        count: prices.length,
      };
    });
  }, [eggData]);

  if (isLoading) return <div><PageHeader title={ar.seasonal.title} subtitle={ar.seasonal.subtitle} badge="تحليل" /><LoadingSpinner text={ar.common.loading} /></div>;
  if (isError) return <div><PageHeader title={ar.seasonal.title} subtitle={ar.seasonal.subtitle} badge="تحليل" /><ErrorDisplay onRetry={() => refetch()} /></div>;

  return (
    <div>
      <PageHeader
        title={ar.seasonal.title}
        subtitle={ar.seasonal.subtitle}
        badge="تحليل"
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <GlassCard glow="emerald">
          <div className="flex items-center gap-3 mb-6">
            <CalendarDays className="w-5 h-5 text-emerald-400" />
            <h2 className="text-lg font-semibold text-white">{ar.seasonal.effectOnPrices}</h2>
          </div>
          <SeasonalEventCard events={seasonalEvents} delay={0.2} />
        </GlassCard>

        <GlassCard glow="none">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <TrendingUp className="w-5 h-5 text-emerald-400" />
              <h2 className="text-lg font-semibold text-white">{ar.seasonal.monthlyAverages}</h2>
            </div>
            <button onClick={() => refetch()} className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/5">
                  <th className="text-right py-2 px-3 text-xs font-medium text-gray-500">الشهر</th>
                  <th className="text-right py-2 px-3 text-xs font-medium text-gray-500">متوسط السعر</th>
                  <th className="text-right py-2 px-3 text-xs font-medium text-gray-500">عدد السجلات</th>
                </tr>
              </thead>
              <tbody>
                {monthlyData.map((row, i) => (
                  <motion.tr
                    key={row.month}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3, delay: i * 0.04 }}
                    className="border-b border-white/5 last:border-0"
                  >
                    <td className="py-2.5 px-3 text-gray-300 font-medium">{row.month}</td>
                    <td className="py-2.5 px-3">
                      {row.eggs > 0 ? (
                        <>
                          <span className="text-white font-medium">{row.eggs.toFixed(1)}</span>
                          <span className="text-[10px] text-gray-500 mr-1">ج.م</span>
                        </>
                      ) : (
                        <span className="text-gray-500">---</span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-xs text-gray-400">{row.count || "---"}</td>
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </GlassCard>
      </div>

      <GlassCard glow="emerald" className="mb-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-white">{ar.seasonal.impactPercentage}</h2>
          <div className="flex items-center gap-3 text-xs">
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="text-gray-400">تأثير إيجابي</span>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-red-500" />
              <span className="text-gray-400">تأثير سلبي</span>
            </div>
          </div>
        </div>
        <div className="space-y-3">
          {seasonalEvents.map((event, i) => {
            const isPositive = event.impactValue > 0;
            return (
              <motion.div
                key={event.name}
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: "100%" }}
                transition={{ duration: 0.5, delay: i * 0.08 }}
                className="flex items-center gap-4"
              >
                <span className="text-xs text-gray-300 w-28 shrink-0 text-left">{event.name}</span>
                <div className="flex-1 h-7 rounded-lg bg-white/5 overflow-hidden relative">
                  <motion.div
                    className={`h-full rounded-lg ${
                      isPositive
                        ? "bg-gradient-to-l from-emerald-500/30 to-emerald-500/10"
                        : "bg-gradient-to-l from-red-500/30 to-red-500/10"
                    }`}
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.abs(event.impactValue) * 5}%` }}
                    transition={{ duration: 0.8, delay: 0.2 + i * 0.08, ease: [0.25, 0.25, 0, 1] }}
                  />
                  <span className={`absolute top-1/2 -translate-y-1/2 text-xs font-semibold ${
                    isPositive ? "text-emerald-400 right-2" : "text-red-400 right-2"
                  }`}>
                    {isPositive ? "+" : ""}{event.impactValue}%
                  </span>
                </div>
                <span className={`text-[10px] w-14 text-center ${
                  isPositive ? "text-emerald-400" : "text-red-400"
                }`}>
                  {event.impact}
                </span>
              </motion.div>
            );
          })}
        </div>
      </GlassCard>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <GlassCard glow="gold" className="lg:col-span-2">
          <h2 className="text-lg font-semibold text-white mb-4">متوسط الأسعار الشهرية (آخر 3 سنوات)</h2>
          <PriceChart
            data={monthlyData.map((d) => ({ date: d.month, eggs: d.eggs }))}
            lines={[{ key: "eggs", color: "#10b981", name: "البيض المخصب" }]}
            height={250}
          />
        </GlassCard>

        <GlassCard glow="blue">
          <div className="flex items-center gap-3 mb-4">
            <Info className="w-5 h-5 text-blue-400" />
            <h2 className="text-lg font-semibold text-white">{ar.seasonal.seasonalSummary}</h2>
          </div>
          <div className="text-xs text-gray-400 leading-relaxed space-y-3">
            <p><strong className="text-white">مواسم التفريخ:</strong> ذروة الطلب على الكتاكيت عمر يوم في فصلي الربيع والخريف مع زيادة نشاط المفرخات.</p>
            <p><strong className="text-white">رمضان:</strong> زيادة الطلب على البيض المخصب وكتاكيت التسمين مع ارتفاع الأسعار بنسبة 15-20% قبل وأثناء الشهر.</p>
            <p><strong className="text-white">الصيف:</strong> انخفاض الإنتاج بسبب الحرارة مع زيادة تكلفة التبريد في المزارع والمفرخات.</p>
            <p><strong className="text-white">تكلفة الأعلاف:</strong> تتأثر أسعار الذرة وفول الصويا بالأسواق العالمية وسعر الدولار مما ينعكس على تكلفة الإنتاج.</p>
            <p><strong className="text-white">عيد الأضحى:</strong> زيادة الطلب على كتاكيت التسمين والأمهات مع ارتفاع أسعار الإنتاج بنسبة 8-10%.</p>
            <div className="glow-line my-3" />
            <p className="text-gray-500">* التحليل مبني على بيانات الأسعار لآخر 3 سنوات ونماذج الذكاء الاصطناعي الموسمية.</p>
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
