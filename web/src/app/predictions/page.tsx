"use client";

import { useMemo } from "react";
import { motion } from "framer-motion";
import { LineChart, TrendingUp, Clock, Eye, RefreshCw, AlertTriangle } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import GlassCard from "@/components/GlassCard";
import PredictionChart from "@/components/PredictionChart";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorDisplay from "@/components/ErrorDisplay";
import { usePredictionsList } from "@/lib/hooks/usePrices";
import { useModelsStatus } from "@/lib/hooks/useModels";
import { useHolidaysList } from "@/lib/hooks/useHolidays";
import { ar, MODEL_AR_NAMES } from "@/lib/ar";

const catalysts = [
  { color: "bg-emerald-400", title: "زيادة الطلب قبل رمضان", desc: "من المتوقع زيادة الطلب على البيض والكتاكيت بنسبة 15-20% قبل شهر رمضان." },
  { color: "bg-gold-400", title: "تقلبات أسعار الأعلاف", desc: "ارتفاع أسعار الذرة والصويا عالمياً قد يؤثر على تكاليف الإنتاج." },
  { color: "bg-blue-400", title: "تغيرات السياسة التجارية", desc: "قرارات فتح وإغلاق الاستيراد تؤثر بشكل مباشر على أسعار السوق المحلي." },
  { color: "bg-red-400", title: "الأمراض والأوبئة", desc: "أي ظهور لأنفلونزا الطيور يؤدي إلى تذبذب حاد في الأسعار." },
];

export default function PredictionsPage() {
  const { data: predictions, isLoading, isError, refetch } = usePredictionsList({ product_type: "fertilized_eggs" });
  const { data: modelsStatus } = useModelsStatus("fertilized_eggs");
  const { data: holidays } = useHolidaysList({ from_date: new Date().toISOString().split("T")[0], limit: 20 });

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
      horizon: m.forecast_horizon ? `${m.forecast_horizon} يوم` : "---",
      lastTrained: m.last_trained_at,
    }));
  }, [modelsStatus]);

  const upcomingEvents = useMemo(() => {
    if (!holidays?.length) return [];
    return holidays.slice(0, 6).map((h) => ({
      event: h.name_ar,
      expectedDate: new Date(h.start_date).toLocaleDateString("ar-EG", { month: "long", year: "numeric" }),
      estimatedImpact: `${h.impact_description} ${h.impact_percentage != null ? Math.abs(h.impact_percentage) + "%" : ""}`,
      confidence: Math.min(1, Math.max(0.5, ((h.impact_percentage || 0) + 20) / 40)),
    }));
  }, [holidays]);

  const chartData = (predictions || []).map((p) => ({
    date: p.predicted_date,
    predicted: p.predicted_price,
    lower: p.confidence_lower ?? p.predicted_price * 0.9,
    upper: p.confidence_upper ?? p.predicted_price * 1.1,
  }));

  return (
    <div>
      <PageHeader
        title={ar.predictions.title}
        subtitle={ar.predictions.subtitle}
        badge="AI"
      />

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-8">
        {modelCards.map((model, i) => (
          <GlassCard key={model.name} glow={model.isTrained ? "emerald" : "none"} delay={0.1 + i * 0.1}>
            <div className="flex items-center gap-3 mb-3">
              <LineChart className={`w-5 h-5 ${model.isTrained ? "text-emerald-400" : "text-gray-500"}`} />
              <span className="text-sm font-semibold text-white">{model.name}</span>
            </div>
            {model.isTrained ? (
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">{ar.aiInsights.accuracy}</span>
                  {model.mape != null ? (
                    <span className="text-emerald-400 font-medium">{(100 - model.mape).toFixed(0)}%</span>
                  ) : (
                    <span className="text-yellow-400 font-medium">مدرب</span>
                  )}
                </div>
                {model.mape != null && (
                  <div className="h-1.5 rounded-full bg-white/5 overflow-hidden">
                    <motion.div
                      className="h-full rounded-full bg-gradient-to-l from-emerald-500 to-emerald-400"
                      initial={{ width: 0 }}
                      animate={{ width: `${100 - model.mape}%` }}
                      transition={{ duration: 1, delay: 0.3 + i * 0.1 }}
                    />
                  </div>
                )}
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">{ar.aiInsights.mape}</span>
                  <span className="text-gray-300">{model.mape != null ? `${model.mape.toFixed(1)}%` : "---"}</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-500">الأفق</span>
                  <span className="text-gray-300">{model.horizon}</span>
                </div>
              </div>
            ) : model.canTrain ? (
              <div className="text-xs text-yellow-400/70 flex items-center gap-2">
                <Clock className="w-3 h-3 shrink-0" />
                <span>جاهز للتدريب — {model.availableDays} يوم</span>
              </div>
            ) : (
              <div className="text-xs text-red-400/70">
                <div className="flex items-center gap-2 mb-1">
                  <AlertTriangle className="w-3 h-3 shrink-0" />
                  <span>غير متاح بعد</span>
                </div>
                <span className="text-[10px] block pr-5">يتطلب {model.requiredDays} يوم بيانات ({model.availableDays} يوم متاح)</span>
              </div>
            )}
          </GlassCard>
        ))}
      </div>

      <GlassCard glow="emerald" className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <TrendingUp className="w-5 h-5 text-emerald-400" />
            <h2 className="text-lg font-semibold text-white">{ar.predictions.forecast}</h2>
          </div>
          <div className="flex items-center gap-2">
            <span className="badge-green">{modelsStatus?.models.find((m) => m.model_name === "Prophet")?.model_is_trained ? "التوقع الموسمي" : "التوقعات"}</span>
            <button onClick={() => refetch()} className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>
        <p className="text-xs text-gray-500 mb-6">التوقعات مع نطاق ثقة 85%</p>

        {isLoading ? (
          <LoadingSpinner size="sm" text={ar.common.loading} />
        ) : isError ? (
          <ErrorDisplay onRetry={() => refetch()} />
        ) : chartData.length > 0 ? (
          <PredictionChart data={chartData} />
        ) : (
          <div className="h-[320px] flex items-center justify-center text-gray-500 text-sm">
            {ar.common.noData}
          </div>
        )}
      </GlassCard>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GlassCard glow="gold">
          <div className="flex items-center gap-3 mb-6">
            <Clock className="w-5 h-5 text-gold-400" />
            <h2 className="text-lg font-semibold text-white">{ar.predictions.upcomingEvents}</h2>
          </div>
          {upcomingEvents.length > 0 ? (
            <div className="space-y-3">
              {upcomingEvents.map((evt, i) => (
                <motion.div
                  key={evt.event}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: 0.1 + i * 0.08 }}
                  className="glass-sm rounded-xl p-4"
                >
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-sm font-semibold text-white">{evt.event}</h3>
                    <span className="text-[10px] text-gray-500">{evt.expectedDate}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-gray-400">التأثير المتوقع:</span>
                    <span className="text-xs font-medium text-emerald-400">{evt.estimatedImpact}</span>
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-[10px] text-gray-500">{ar.predictions.confidence}:</span>
                    <div className="flex-1 h-1.5 rounded-full bg-white/5 overflow-hidden">
                      <motion.div
                        className="h-full rounded-full bg-gradient-to-l from-emerald-500 to-emerald-400"
                        initial={{ width: 0 }}
                        animate={{ width: `${evt.confidence * 100}%` }}
                        transition={{ duration: 0.8, delay: 0.3 + i * 0.08 }}
                      />
                    </div>
                    <span className="text-[10px] text-emerald-400 font-medium">
                      {(evt.confidence * 100).toFixed(0)}%
                    </span>
                  </div>
                </motion.div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-gray-500 text-center py-8">لا توجد أحداث قادمة متاحة</div>
          )}
        </GlassCard>

        <GlassCard glow="blue">
          <div className="flex items-center gap-3 mb-6">
            <Eye className="w-5 h-5 text-blue-400" />
            <h2 className="text-lg font-semibold text-white">{ar.predictions.marketCatalysts}</h2>
          </div>
          <div className="space-y-4">
            {catalysts.map((c, i) => (
              <motion.div
                key={c.title}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: 0.1 + i * 0.08 }}
                className="glass-sm rounded-xl p-4"
              >
                <div className="flex items-center gap-2 mb-1">
                  <div className={`w-1.5 h-1.5 rounded-full ${c.color}`} />
                  <span className="text-sm font-medium text-white">{c.title}</span>
                </div>
                <p className="text-xs text-gray-400 pr-4">{c.desc}</p>
              </motion.div>
            ))}
          </div>
        </GlassCard>
      </div>
    </div>
  );
}
