"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { BrainCircuit, Sparkles, Cpu, Database, BarChart4, Clock, CheckCircle2, AlertTriangle, Eye, TrendingUp, CalendarDays } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import GlassCard from "@/components/GlassCard";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorDisplay from "@/components/ErrorDisplay";
import { useModelsStatus } from "@/lib/hooks/useModels";
import { usePricesList } from "@/lib/hooks/usePrices";
import { DATA_SOURCES, INSIGHT_LEVELS } from "@/lib/constants";
import { ar, MODEL_AR_NAMES } from "@/lib/ar";

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

export default function AIInsightsPage() {
  const { data: modelsStatus, isLoading, isError, refetch } = useModelsStatus("fertilized_eggs");
  const { data: eggPrices } = usePricesList({ product_type: "fertilized_eggs", limit: 500 });

  const availableDays = modelsStatus?.models?.[0]?.available_days || 0;

  const insightLevel = useMemo(() => {
    let level = INSIGHT_LEVELS[0];
    for (const l of INSIGHT_LEVELS) {
      if (availableDays >= l.minDays) level = l;
    }
    return level;
  }, [availableDays]);

  const modelCards = useMemo(() => {
    if (!modelsStatus) return [];
    return modelsStatus.models.map((m) => ({
      name: MODEL_AR_NAMES[m.model_name] || m.model_name,
      isTrained: m.model_is_trained,
      canTrain: m.can_train,
      requiredDays: m.required_days,
      availableDays: m.available_days,
      mae: m.mae,
      rmse: m.rmse,
      mape: m.mape,
      forecastHorizon: m.forecast_horizon,
      lastTrained: m.last_trained_at,
    }));
  }, [modelsStatus]);

  const trainedCount = modelCards.filter((m) => m.isTrained).length;

  const avgPrice = useMemo(() => {
    if (!eggPrices?.length) return null;
    return (eggPrices.reduce((s, r) => s + r.price, 0) / eggPrices.length).toFixed(1);
  }, [eggPrices]);

  const isLoaded = modelsStatus && !isLoading;

  return (
    <div>
      <PageHeader
        title={ar.aiInsights.title}
        subtitle={ar.aiInsights.subtitle}
        badge={`${availableDays} يوم`}
      />

      {isLoading ? (
        <LoadingSpinner text={ar.common.loading} />
      ) : isError ? (
        <ErrorDisplay onRetry={() => refetch()} />
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <GlassCard glow={availableDays >= 3 ? "emerald" : "none"} delay={0.1}>
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs text-gray-500">مستوى التحليل</p>
                <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                  availableDays >= 3 ? "bg-emerald-500/20 text-emerald-400" : "bg-yellow-500/20 text-yellow-400"
                }`}>
                  {availableDays >= 3 ? "متاح" : "غير متاح"}
                </span>
              </div>
              <p className="text-lg font-bold text-white">{insightLevel.label}</p>
              <p className="text-[10px] text-gray-500 mt-1">{insightLevel.desc}</p>
            </GlassCard>
            <GlassCard glow={availableDays >= 7 ? "emerald" : "none"} delay={0.15}>
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs text-gray-500">أيام البيانات</p>
                <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400">{availableDays} يوم</span>
              </div>
              <div className="flex items-center gap-2">
                <p className="text-2xl font-bold text-white">{availableDays}</p>
                <div className="flex-1 h-1.5 rounded-full bg-white/5 overflow-hidden">
                  <motion.div
                    className="h-full rounded-full bg-gradient-to-l from-emerald-500 to-emerald-400"
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.min((availableDays / 90) * 100, 100)}%` }}
                    transition={{ duration: 1, delay: 0.3 }}
                  />
                </div>
              </div>
              <p className="text-[10px] text-gray-500 mt-1">من أصل 90 يوماً للنموذج الذكي</p>
            </GlassCard>
            <GlassCard glow={availableDays >= 30 ? "emerald" : "none"} delay={0.2}>
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs text-gray-500">النماذج المدربة</p>
              </div>
              <p className="text-2xl font-bold text-white">{trainedCount} / {modelCards.length}</p>
              <p className="text-[10px] text-gray-500 mt-1">
                {trainedCount === modelCards.length ? "جميع النماذج جاهزة" :
                 trainedCount > 0 ? `لديك ${trainedCount} نموذج مدرب` : "لا توجد نماذج مدربة بعد"}
              </p>
            </GlassCard>
            <GlassCard glow={avgPrice ? "emerald" : "none"} delay={0.25}>
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs text-gray-500">متوسط السعر</p>
              </div>
              <p className="text-2xl font-bold text-white">{avgPrice || "---"}</p>
              <p className="text-[10px] text-gray-500 mt-1">البيض المخصب — آخر {availableDays} يوم</p>
            </GlassCard>
          </div>

          <GlassCard glow="emerald" className="mb-8">
            <div className="flex items-center gap-3 mb-6">
              <BrainCircuit className="w-5 h-5 text-emerald-400" />
              <h2 className="text-lg font-semibold text-white">مراحل تطور التحليل</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
              {[
                { days: 3, label: "رؤى أولية", desc: "تحليل أولي للاتجاه العام", active: availableDays >= 3, icon: Eye },
                { days: 7, label: "اتجاه قصير", desc: "اتجاه السوق على المدى القصير", active: availableDays >= 7, icon: TrendingUp },
                { days: 30, label: "التوقع الإحصائي", desc: "نموذج ARIMA للتنبؤ الإحصائي", active: availableDays >= 30, icon: BarChart4 },
                { days: 45, label: "التوقع الموسمي", desc: "نموذج Prophet للتنبؤ الموسمي", active: availableDays >= 45, icon: CalendarDays },
                { days: 90, label: "التوقع الذكي", desc: "نموذج LSTM للتنبؤ المتقدم", active: availableDays >= 90, icon: Cpu },
              ].map((stage, i) => {
                const Icon = stage.icon;
                const isReached = stage.active;
                return (
                  <motion.div
                    key={stage.days}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.4, delay: 0.1 + i * 0.08 }}
                    className={`glass-sm rounded-xl p-4 text-center ${
                      isReached ? "border border-emerald-500/20" : "opacity-50"
                    }`}
                  >
                    <div className={`inline-flex p-2 rounded-xl mb-2 ${
                      isReached ? "bg-emerald-500/10 text-emerald-400" : "bg-white/5 text-gray-500"
                    }`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <p className="text-xs font-semibold text-white mb-0.5">{stage.label}</p>
                    <p className="text-[10px] text-gray-500">{stage.desc}</p>
                    {isReached ? (
                      <span className="text-[9px] text-emerald-400 mt-1 block">{stage.days} يوم ✓</span>
                    ) : (
                      <span className="text-[9px] text-gray-600 mt-1 block">يتطلب {stage.days} يوم</span>
                    )}
                  </motion.div>
                );
              })}
            </div>
          </GlassCard>

          <GlassCard glow="emerald" className="mb-8">
            <div className="flex items-center gap-3 mb-6">
              <BrainCircuit className="w-5 h-5 text-emerald-400" />
              <h2 className="text-lg font-semibold text-white">{ar.aiInsights.title}</h2>
              <Sparkles className="w-4 h-4 text-gold-400" />
            </div>
            {availableDays < 3 ? (
              <div className="text-center py-8">
                <div className="inline-flex p-3 rounded-xl bg-yellow-500/10 text-yellow-400 mb-4">
                  <Eye className="w-6 h-6" />
                </div>
                <p className="text-sm text-white font-medium mb-2">بانتظار بيانات كافية</p>
                <p className="text-xs text-gray-400 max-w-md mx-auto leading-relaxed">
                  تبدأ الرؤى الأولية بعد 3 أيام من جمع البيانات. حالياً: {availableDays} يوم
                </p>
              </div>
            ) : availableDays < 30 ? (
              <div className="text-center py-8">
                <div className="inline-flex p-3 rounded-xl bg-emerald-500/10 text-emerald-400 mb-4">
                  <Eye className="w-6 h-6" />
                </div>
                <p className="text-sm text-white font-medium mb-2">{insightLevel.label}</p>
                <p className="text-xs text-gray-400 max-w-md mx-auto leading-relaxed">
                  رؤى أولية بناءً على البيانات المتاحة. مع توفر المزيد من البيانات، ستتمكن النماذج من تقديم توقعات أكثر دقة.
                  حالياً: {availableDays} يوم بيانات من أصل 30 يوماً المطلوبة للنموذج الإحصائي.
                </p>
                <div className="mt-4 flex items-center justify-center gap-4 text-xs text-gray-500">
                  <div className="glass-sm rounded-lg px-3 py-2">
                    <p className="text-emerald-400 font-bold">{availableDays}</p>
                    <p>يوم بيانات</p>
                  </div>
                  <div className="glass-sm rounded-lg px-3 py-2">
                    <p className="text-yellow-400 font-bold">{Math.max(0, 30 - availableDays)}</p>
                    <p>يوم متبقي</p>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-center py-8">
                <p className="text-sm text-gray-400">✅ البيانات كافية — النماذج جاهزة للتدريب والتنبؤ</p>
                <p className="text-xs text-gray-500 mt-2">راجع جدول النماذج أدناه لعرض أداء كل نموذج</p>
              </div>
            )}
          </GlassCard>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <GlassCard glow="emerald">
              <div className="flex items-center gap-3 mb-6">
                <Cpu className="w-5 h-5 text-emerald-400" />
                <h2 className="text-lg font-semibold text-white">{ar.aiInsights.modelMetrics}</h2>
              </div>
              <div className="space-y-4">
                {modelCards.map((m, i) => (
                  <div key={m.name} className="glass-sm rounded-xl p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <BarChart4 className={`w-4 h-4 ${m.isTrained ? "text-emerald-400" : "text-gray-500"}`} />
                      <span className="text-sm font-medium text-white">{m.name}</span>
                      {m.isTrained && <span className="badge-green text-[10px]">مدرب</span>}
                      {!m.isTrained && m.canTrain && <span className="text-[10px] px-2 py-0.5 rounded bg-yellow-500/20 text-yellow-400">جاهز للتدريب</span>}
                      {!m.isTrained && !m.canTrain && <span className="text-[10px] px-2 py-0.5 rounded bg-red-500/20 text-red-400">غير متاح بعد</span>}
                    </div>
                    {m.isTrained ? (
                      <div className="grid grid-cols-2 gap-3 text-xs">
                        <div><span className="text-gray-500">{ar.aiInsights.mae}:</span> <span className="text-gray-300 mr-1">{m.mae?.toFixed(2) ?? "---"} ج.م</span></div>
                        <div><span className="text-gray-500">{ar.aiInsights.rmse}:</span> <span className="text-gray-300 mr-1">{m.rmse?.toFixed(2) ?? "---"} ج.م</span></div>
                        <div><span className="text-gray-500">{ar.aiInsights.mape}:</span> <span className="text-gray-300 mr-1">{m.mape?.toFixed(2) ?? "---"}%</span></div>
                        <div><span className="text-gray-500">الأفق:</span> <span className="text-gray-300 mr-1">{m.forecastHorizon ? `${m.forecastHorizon} يوم` : "---"}</span></div>
                      </div>
                    ) : !m.canTrain ? (
                      <div className="text-xs text-red-400/70 flex items-center gap-2">
                        <AlertTriangle className="w-3 h-3" />
                        <span>يتطلب {m.requiredDays} يوم بيانات ({m.availableDays} يوم متاح)</span>
                      </div>
                    ) : (
                      <div className="text-xs text-yellow-400/70 flex items-center gap-2">
                        <Clock className="w-3 h-3" />
                        <span>{m.availableDays} يوم بيانات متاح — جاهز للتدريب</span>
                      </div>
                    )}
                  </div>
                ))}

                <div className="glass-sm rounded-xl p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle2 className="w-4 h-4 text-blue-400" />
                    <span className="text-sm font-medium text-white">ملخص البيانات</span>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div><span className="text-gray-500">إجمالي الأيام:</span> <span className="text-gray-300 mr-1">{availableDays} يوم</span></div>
                    <div><span className="text-gray-500">من:</span> <span className="text-gray-300 mr-1">{modelsStatus?.data_start_date || "---"}</span></div>
                    <div><span className="text-gray-500">إلى:</span> <span className="text-gray-300 mr-1">{modelsStatus?.data_end_date || "---"}</span></div>
                    <div><span className="text-gray-500">النماذج المدربة:</span> <span className="text-gray-300 mr-1">{trainedCount}</span></div>
                  </div>
                </div>
              </div>
            </GlassCard>

            <GlassCard glow="blue">
              <div className="flex items-center gap-3 mb-6">
                <Database className="w-5 h-5 text-blue-400" />
                <h2 className="text-lg font-semibold text-white">{ar.aiInsights.dataSources}</h2>
              </div>
              <div className="space-y-3">
                {DATA_SOURCES.map((src, i) => (
                  <motion.div
                    key={src.name}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: 0.1 + i * 0.08 }}
                    className="flex items-center justify-between glass-sm rounded-xl p-3.5"
                  >
                    <div>
                      <p className="text-sm font-medium text-white">{src.name}</p>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 text-gray-400">{src.type}</span>
                        <span className="text-[10px] text-gray-500">تحديث: {src.update}</span>
                      </div>
                    </div>
                    <div className="text-left">
                      <span className="text-xs font-semibold text-emerald-400">{src.reliability}%</span>
                      <div className="h-1 w-12 rounded-full bg-white/5 mt-1 overflow-hidden">
                        <motion.div
                          className="h-full rounded-full bg-gradient-to-l from-emerald-500 to-emerald-400"
                          initial={{ width: 0 }}
                          animate={{ width: `${src.reliability}%` }}
                          transition={{ duration: 0.8, delay: 0.3 + i * 0.08 }}
                        />
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>
              <div className="mt-4 text-xs text-gray-500 glass-sm rounded-xl p-3 text-center">
                {ar.aiInsights.lastUpdated}: {new Date().toLocaleDateString("ar-EG")}
              </div>
            </GlassCard>
          </div>
        </>
      )}
    </div>
  );
}
