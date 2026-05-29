"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { BarChart3, TrendingUp, MapPin, CalendarRange, ArrowUpDown, RefreshCw, Bird, Egg, Wheat } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import GlassCard from "@/components/GlassCard";
import PriceChart from "@/components/PriceChart";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorDisplay from "@/components/ErrorDisplay";
import { usePricesList } from "@/lib/hooks/usePrices";
import { ar } from "@/lib/ar";

export default function MarketTrendsPage() {
  const threeYearsAgo = new Date();
  threeYearsAgo.setFullYear(threeYearsAgo.getFullYear() - 3);

  const { data: eggPrices, isLoading: eggLoading, isError: eggError, refetch: refetchEgg } = usePricesList({
    product_type: "fertilized_eggs",
    start_date: threeYearsAgo.toISOString().split("T")[0],
    limit: 1000,
  });

  const { data: chickPrices, isLoading: chickLoading } = usePricesList({
    product_type: "day_old_chicks",
    start_date: threeYearsAgo.toISOString().split("T")[0],
    limit: 1000,
  });

  const chickTrend = useMemo(() => {
    if (!chickPrices?.length) return [];
    const byMonth: Record<string, number[]> = {};
    chickPrices.forEach((r) => {
      const d = new Date(r.recorded_date);
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
      if (!byMonth[key]) byMonth[key] = [];
      byMonth[key].push(r.price);
    });
    return Object.entries(byMonth)
      .sort(([a], [b]) => a.localeCompare(b))
      .slice(-18)
      .map(([date, vals]) => ({
        date: date.slice(5),
        price: Number((vals.reduce((s, p) => s + p, 0) / vals.length).toFixed(1)),
      }));
  }, [chickPrices]);

  const yearOverYearData = useMemo(() => {
    if (!eggPrices?.length) return [];
    const byYearMonth: Record<string, Record<number, number[]>> = {};

    eggPrices.forEach((r) => {
      const d = new Date(r.recorded_date);
      const year = d.getFullYear();
      const month = d.getMonth();
      if (!byYearMonth[year]) byYearMonth[year] = {};
      if (!byYearMonth[year][month]) byYearMonth[year][month] = [];
      byYearMonth[year][month].push(r.price);
    });

    const monthNames = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"];
    const years = Object.keys(byYearMonth).sort();

    return monthNames.map((month, mi) => {
      const point: { date: string; [key: string]: number | string | undefined } = { date: month };
      years.forEach((y) => {
        const prices = byYearMonth[Number(y)]?.[mi];
        point[y] = prices?.length ? Number((prices.reduce((s, p) => s + p, 0) / prices.length).toFixed(1)) : undefined;
      });
      return point;
    });
  }, [eggPrices]);

  const yearLabels = useMemo(() => {
    if (!eggPrices?.length) return [];
    return [...new Set(eggPrices.map((r) => new Date(r.recorded_date).getFullYear()))].sort().map(String);
  }, [eggPrices]);

  const regionData = useMemo(() => {
    if (!eggPrices?.length && !chickPrices?.length) return [];
    const byRegion: Record<string, { eggs: number[]; chicks: number[] }> = {};

    (eggPrices || []).forEach((r) => {
      const region = r.region || "أخرى";
      if (!byRegion[region]) byRegion[region] = { eggs: [], chicks: [] };
      byRegion[region].eggs.push(r.price);
    });
    (chickPrices || []).forEach((r) => {
      const region = r.region || "أخرى";
      if (!byRegion[region]) byRegion[region] = { eggs: [], chicks: [] };
      byRegion[region].chicks.push(r.price);
    });

    return Object.entries(byRegion)
      .map(([name, vals]) => ({
        name,
        eggsPrice: vals.eggs.length ? Number((vals.eggs.reduce((s, p) => s + p, 0) / vals.eggs.length).toFixed(1)) : 0,
        chicksPrice: vals.chicks.length ? Number((vals.chicks.reduce((s, p) => s + p, 0) / vals.chicks.length).toFixed(1)) : 0,
      }))
      .filter((r) => r.eggsPrice > 0 || r.chicksPrice > 0)
      .sort((a, b) => b.eggsPrice - a.eggsPrice);
  }, [eggPrices, chickPrices]);

  const stats = useMemo(() => {
    if (!eggPrices?.length) return null;
    const prices = eggPrices.map((r) => r.price);
    const sorted = [...prices].sort((a, b) => a - b);
    const oldest = new Date(eggPrices[eggPrices.length - 1]?.recorded_date || "");
    const newest = new Date(eggPrices[0]?.recorded_date || "");
    const yearDiff = (newest.getTime() - oldest.getTime()) / (365.25 * 24 * 60 * 60 * 1000);
    const growth = yearDiff > 0 ? ((prices[0] - sorted[0]) / sorted[0]) * 100 : 0;

    // volatility: coefficient of variation
    const mean = prices.reduce((s, p) => s + p, 0) / prices.length;
    const variance = prices.reduce((s, p) => s + (p - mean) ** 2, 0) / prices.length;
    const volatility = mean > 0 ? (Math.sqrt(variance) / mean) * 100 : 0;

    // peak month: find month with highest average price
    const byMonth: Record<number, number[]> = {};
    eggPrices.forEach((r) => {
      const m = new Date(r.recorded_date).getMonth();
      if (!byMonth[m]) byMonth[m] = [];
      byMonth[m].push(r.price);
    });
    const monthNames = ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو", "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"];
    let peakMonth = "---";
    let peakAvg = 0;
    Object.entries(byMonth).forEach(([m, vals]) => {
      const avg = vals.reduce((s, p) => s + p, 0) / vals.length;
      if (avg > peakAvg) {
        peakAvg = avg;
        peakMonth = monthNames[parseInt(m)] || monthNames[0];
      }
    });

    return { growth, volatility, peakMonth };
  }, [eggPrices]);

  const isLoading = eggLoading || chickLoading;
  const isError = eggError;

  if (isLoading) return <div><PageHeader title={ar.trends.title} subtitle={ar.trends.subtitle} badge="3 سنوات" /><LoadingSpinner text={ar.common.loading} /></div>;
  if (isError) return <div><PageHeader title={ar.trends.title} subtitle={ar.trends.subtitle} badge="3 سنوات" /><ErrorDisplay onRetry={() => refetchEgg()} /></div>;

  return (
    <div>
      <PageHeader
        title={ar.trends.title}
        subtitle={ar.trends.subtitle}
        badge="3 سنوات"
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <GlassCard glow="emerald" delay={0.1}>
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <span className="text-xs text-gray-500">{ar.trends.growthRate}</span>
          </div>
          <p className="text-2xl font-bold text-white">{stats ? `${stats.growth > 0 ? "+" : ""}${stats.growth.toFixed(1)}%` : "---"}</p>
          <p className="text-[10px] text-gray-500 mt-0.5">البيض المخصب على مدى الفترة المتاحة</p>
        </GlassCard>
        <GlassCard glow="gold" delay={0.15}>
          <div className="flex items-center gap-2 mb-1">
            <ArrowUpDown className="w-4 h-4 text-gold-400" />
            <span className="text-xs text-gray-500">{ar.trends.volatility}</span>
          </div>
          <p className="text-2xl font-bold text-white">{stats ? `±${stats.volatility.toFixed(1)}%` : "---"}</p>
          <p className="text-[10px] text-gray-500 mt-0.5">التقلب الموسمي للأسعار</p>
        </GlassCard>
        <GlassCard glow="blue" delay={0.2}>
          <div className="flex items-center gap-2 mb-1">
            <CalendarRange className="w-4 h-4 text-blue-400" />
            <span className="text-xs text-gray-500">{ar.trends.peakMonth}</span>
          </div>
          <p className="text-2xl font-bold text-white">{stats?.peakMonth || "---"}</p>
          <p className="text-[10px] text-gray-500 mt-0.5">شهر ذروة الأسعار</p>
        </GlassCard>
      </div>

      <GlassCard glow="emerald" className="mb-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Bird className="w-5 h-5 text-emerald-400" />
            <h2 className="text-lg font-semibold text-white">{ar.trends.chickTrend}</h2>
          </div>
          <button onClick={() => refetchEgg()} className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
        {chickTrend.length > 0 ? (
          <PriceChart
            data={chickTrend}
            lines={[{ key: "price", color: "#10b981", name: "أسعار الكتاكيت" }]}
            height={250}
          />
        ) : (
          <div className="h-[250px] flex flex-col items-center justify-center text-gray-500 text-sm">
            <span className="mb-1">{ar.common.noMarketData}</span>
            <span className="text-xs text-gray-600">{ar.common.awaitingFirstCollection}</span>
          </div>
        )}
      </GlassCard>

      <GlassCard glow="gold" className="mb-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Egg className="w-5 h-5 text-gold-400" />
            <h2 className="text-lg font-semibold text-white">{ar.trends.eggTrend}</h2>
          </div>
          <div className="flex items-center gap-3 text-xs">
            {yearLabels.map((y, i) => {
              const colors = ["#10b981", "#f59e0b", "#3b82f6"];
              return (
                <div key={y} className="flex items-center gap-1.5">
                  <div className="w-3 h-0.5 rounded" style={{ backgroundColor: colors[i] || "#10b981" }} />
                  <span className="text-gray-400">{y}</span>
                </div>
              );
            })}
          </div>
        </div>
        {yearOverYearData.length > 0 ? (
          <PriceChart
            data={yearOverYearData}
            lines={yearLabels.map((y, i) => ({
              key: y,
              color: ["#10b981", "#f59e0b", "#3b82f6"][i] || "#10b981",
              name: y,
            }))}
            height={300}
          />
        ) : (
          <div className="h-[300px] flex flex-col items-center justify-center text-gray-500 text-sm">
            <span className="mb-1">{ar.common.noMarketData}</span>
            <span className="text-xs text-gray-600">{ar.common.awaitingFirstCollection}</span>
          </div>
        )}
      </GlassCard>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <GlassCard glow="gold">
          <div className="flex items-center gap-3 mb-6">
            <MapPin className="w-5 h-5 text-gold-400" />
            <h2 className="text-lg font-semibold text-white">{ar.trends.regionComparison}</h2>
          </div>
          {regionData.length > 0 ? (
            <div className="space-y-3">
              {regionData.map((region, i) => (
                <motion.div
                  key={region.name}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: 0.1 + i * 0.05 }}
                  className="glass-sm rounded-xl p-4"
                >
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm font-medium text-white">{region.name}</span>
                    <span className="text-xs text-gray-500">
                      البيض: {region.eggsPrice} ج.م
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-emerald-400 w-16">البيض</span>
                    <div className="flex-1 h-2 rounded-full bg-white/5 overflow-hidden">
                      <motion.div
                        className="h-full rounded-full bg-gradient-to-l from-emerald-500 to-emerald-400"
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.min((region.eggsPrice / (Math.max(...regionData.map((r) => r.eggsPrice)) || 1)) * 100, 100)}%` }}
                        transition={{ duration: 0.8, delay: 0.2 + i * 0.05 }}
                      />
                    </div>
                    <span className="text-[10px] text-gray-400 w-10 text-left">{region.eggsPrice}</span>
                  </div>
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-sm text-gray-500">{ar.common.noMarketData}</p>
              <p className="text-xs text-gray-600 mt-1">{ar.common.awaitingFirstCollection}</p>
            </div>
          )}
        </GlassCard>

        <GlassCard glow="blue">
          <div className="flex items-center gap-3 mb-6">
            <BarChart3 className="w-5 h-5 text-blue-400" />
            <h2 className="text-lg font-semibold text-white">{ar.trends.priceHistory}</h2>
          </div>
          {eggPrices && eggPrices.length > 0 ? (
            <PriceChart
              data={eggPrices.slice(-30).reverse().map((d) => ({ date: d.recorded_date.slice(5), price: d.price }))}
              lines={[{ key: "price", color: "#3b82f6", name: "البيض المخصب" }]}
              height={250}
            />
          ) : (
            <div className="h-[250px] flex flex-col items-center justify-center text-gray-500 text-sm">
              <span className="mb-1">{ar.common.noMarketData}</span>
              <span className="text-xs text-gray-600">{ar.common.awaitingFirstCollection}</span>
            </div>
          )}
          <div className="mt-4 grid grid-cols-3 gap-3">
            {regionData.slice(0, 6).map((region, i) => (
              <motion.div
                key={region.name}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 + i * 0.05 }}
                className="glass-sm rounded-xl p-2 text-center"
              >
                <p className="text-[10px] text-gray-500 truncate">{region.name}</p>
                <p className="text-xs font-semibold text-white">{region.eggsPrice} <span className="text-[8px] text-gray-500">ج.م</span></p>
              </motion.div>
            ))}
          </div>
        </GlassCard>
      </div>

      {eggPrices && eggPrices.length > 0 && (
        <GlassCard>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-white">تحليلات السوق</h2>
          </div>
          <div className="grid md:grid-cols-2 gap-4">
            <div className="glass-sm rounded-xl p-4">
              <h3 className="text-sm font-semibold text-white mb-2">ملخص البيانات</h3>
              <p className="text-xs text-gray-400 leading-relaxed">
                إجمالي {eggPrices.length} سجل سعري للبيض المخصب على مدى {
                  eggPrices.length > 1
                    ? Math.ceil(
                        (new Date(eggPrices[0].recorded_date).getTime() -
                          new Date(eggPrices[eggPrices.length - 1].recorded_date).getTime()) /
                          (365.25 * 24 * 60 * 60 * 1000),
                      )
                    : 0
                } سنوات. متوسط السعر: {(eggPrices.reduce((s, r) => s + r.price, 0) / eggPrices.length).toFixed(1)} ج.م
              </p>
            </div>
            <div className="glass-sm rounded-xl p-4">
              <h3 className="text-sm font-semibold text-white mb-2">توزيع المحافظات</h3>
              <p className="text-xs text-gray-400 leading-relaxed">
                البيانات تغطي {regionData.length} محافظة/منطقة. أعلى سعر في {regionData[0]?.name || "---"} ({regionData[0]?.eggsPrice.toFixed(1)} ج.م)
                وأقل سعر في {regionData[regionData.length - 1]?.name || "---"} ({regionData[regionData.length - 1]?.eggsPrice.toFixed(1)} ج.م)
              </p>
            </div>
          </div>
        </GlassCard>
      )}
    </div>
  );
}
