"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import {
  Newspaper, ExternalLink, Calendar, RefreshCw, AlertTriangle,
  TrendingUp, TrendingDown, Minus, BarChart3, Layers,
} from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import PageHeader from "@/components/PageHeader";
import GlassCard from "@/components/GlassCard";
import LoadingSpinner from "@/components/LoadingSpinner";
import ErrorDisplay from "@/components/ErrorDisplay";

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

interface NewsArticle {
  id: number;
  title: string;
  summary: string | null;
  url: string;
  source_name: string;
  published_at: string | null;
  image_url: string | null;
  category: string | null;
  keywords: string | null;
  relevance_score: number | null;
  sentiment: string | null;
  created_at: string;
}

interface MarketIndicators {
  today_count: number;
  dominant_category: string | null;
  market_sentiment: string;
  category_distribution: Record<string, number>;
  sentiment_distribution: Record<string, number>;
}

async function fetchJson<T>(url: string, opts?: RequestInit): Promise<T> {
  const res = await fetch(url, opts);
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const body = await res.clone().json();
      if (body.detail) {
        msg = typeof body.detail === "string" ? body.detail : (body.detail.ar || body.detail.en || msg);
      }
    } catch { /* ignore */ }
    throw new Error(msg);
  }
  return res.json();
}

function formatDate(d: string | null) {
  if (!d) return "---";
  return new Date(d).toLocaleDateString("ar-EG", {
    year: "numeric", month: "long", day: "numeric",
  });
}

const CATEGORY_COLORS: Record<string, string> = {
  "أسعار الكتاكيت": "bg-emerald-500/10 text-emerald-400",
  "بيض مخصب": "bg-amber-500/10 text-amber-400",
  أعلاف: "bg-lime-500/10 text-lime-400",
  "بورصة ومؤشرات": "bg-blue-500/10 text-blue-400",
  "شركات وإنتاج": "bg-violet-500/10 text-violet-400",
};

const CATEGORIES = [
  { key: "", label: "الكل" },
  { key: "أسعار الكتاكيت", label: "أسعار الكتاكيت" },
  { key: "بيض مخصب", label: "بيض مخصب" },
  { key: "أعلاف", label: "أعلاف" },
  { key: "بورصة ومؤشرات", label: "بورصة ومؤشرات" },
  { key: "شركات وإنتاج", label: "شركات وإنتاج" },
];

const SENTIMENT_ICONS: Record<string, React.ReactNode> = {
  إيجابي: <TrendingUp className="w-4 h-4 text-emerald-400" />,
  محايد: <Minus className="w-4 h-4 text-gray-400" />,
  سلبي: <TrendingDown className="w-4 h-4 text-red-400" />,
};

const SENTIMENT_COLORS: Record<string, string> = {
  إيجابي: "text-emerald-400 bg-emerald-500/10",
  محايد: "text-gray-400 bg-white/5",
  سلبي: "text-red-400 bg-red-500/10",
};

function IndicatorsWidget({ data }: { data: MarketIndicators }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
      <GlassCard glow="none" hover={false} delay={0}>
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-emerald-500/10">
            <Newspaper className="w-5 h-5 text-emerald-400" />
          </div>
          <div>
            <p className="text-[10px] text-gray-500 uppercase tracking-wider">أخبار اليوم</p>
            <p className="text-xl font-bold text-white">{data.today_count}</p>
          </div>
        </div>
      </GlassCard>
      <GlassCard glow="none" hover={false} delay={0}>
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-blue-500/10">
            <Layers className="w-5 h-5 text-blue-400" />
          </div>
          <div>
            <p className="text-[10px] text-gray-500 uppercase tracking-wider">التصنيف السائد</p>
            <p className="text-xl font-bold text-white">{data.dominant_category || "---"}</p>
          </div>
        </div>
      </GlassCard>
      <GlassCard glow="none" hover={false} delay={0}>
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-amber-500/10">
            <BarChart3 className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <p className="text-[10px] text-gray-500 uppercase tracking-wider">مؤشر السوق</p>
            <div className="flex items-center gap-1.5">
              {SENTIMENT_ICONS[data.market_sentiment] || <Minus className="w-4 h-4 text-gray-400" />}
              <span className={`text-sm font-bold ${SENTIMENT_COLORS[data.market_sentiment]?.split(" ")[0] || "text-gray-400"}`}>
                {data.market_sentiment}
              </span>
            </div>
          </div>
        </div>
      </GlassCard>
    </div>
  );
}

export default function NewsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(0);
  const [categoryFilter, setCategoryFilter] = useState("");
  const limit = 20;

  const { data, isLoading, isError, refetch } = useQuery<NewsArticle[]>({
    queryKey: ["news", "list", page, categoryFilter],
    queryFn: () => fetchJson(
      `${getApiBase()}/news/?limit=${limit}&offset=${page * limit}${categoryFilter ? `&category=${categoryFilter}` : ""}`
    ),
    refetchInterval: 300_000,
  });

  const { data: indicators } = useQuery<MarketIndicators>({
    queryKey: ["news", "indicators"],
    queryFn: () => fetchJson(`${getApiBase()}/news/indicators`),
    refetchInterval: 300_000,
  });

  const refreshMutation = useMutation({
    mutationFn: () => fetchJson<{ message: string }>(`${getApiBase()}/news/refresh`, {
      method: "POST",
    } as RequestInit),
    onSuccess: (res) => {
      toast.success(res.message);
      queryClient.invalidateQueries({ queryKey: ["news"] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  return (
    <div>
      <PageHeader
        title="الأخبار"
        subtitle="آخر أخبار أسواق الدواجن والبيض في مصر"
        badge="أخبار"
      />

      {indicators && <IndicatorsWidget data={indicators} />}

      <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-2">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.key}
            onClick={() => { setCategoryFilter(cat.key); setPage(0); }}
            className={`shrink-0 px-3 py-1.5 rounded-xl text-xs font-medium transition-colors ${
              categoryFilter === cat.key
                ? "bg-emerald-500/15 text-emerald-400"
                : "text-gray-500 bg-white/5 hover:bg-white/10 hover:text-gray-300"
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      <div className="flex items-center justify-between mb-6">
        <p className="text-xs text-gray-500">
          {data?.length ? `عدد المقالات: ${data.length}` : ""}
        </p>
        <button
          onClick={() => refreshMutation.mutate()}
          disabled={refreshMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-medium text-emerald-400 hover:text-emerald-300 bg-emerald-500/5 hover:bg-emerald-500/10 transition-colors disabled:opacity-40"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${refreshMutation.isPending ? "animate-spin" : ""}`} />
          {refreshMutation.isPending ? "جاري التحديث..." : "تحديث الأخبار"}
        </button>
      </div>

      {isLoading ? (
        <LoadingSpinner text="جاري تحميل الأخبار..." />
      ) : isError ? (
        <ErrorDisplay onRetry={() => refetch()} />
      ) : (
        <>
          {!data || data.length === 0 ? (
            <div className="text-center py-16">
              <Newspaper className="w-12 h-12 text-gray-600 mx-auto mb-4" />
              <p className="text-sm text-gray-500">لا توجد أخبار متاحة حالياً</p>
              <p className="text-xs text-gray-600 mt-1">حاول تحديث الأخبار لاحقاً</p>
              <button
                onClick={() => refreshMutation.mutate()}
                disabled={refreshMutation.isPending}
                className="mt-4 px-4 py-2 rounded-xl text-xs font-medium text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 transition-colors disabled:opacity-40"
              >
                تحديث الأخبار
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {data.map((article, i) => (
                <motion.div
                  key={article.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.4, delay: i * 0.03 }}
                >
                  <GlassCard glow="none" hover={false} delay={0}>
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                          {article.category && (
                            <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${CATEGORY_COLORS[article.category] || "bg-white/5 text-gray-400"}`}>
                              {article.category}
                            </span>
                          )}
                          {article.sentiment && (
                            <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full flex items-center gap-1 ${
                              SENTIMENT_COLORS[article.sentiment] || "bg-white/5 text-gray-400"
                            }`}>
                              {SENTIMENT_ICONS[article.sentiment]}
                              {article.sentiment}
                            </span>
                          )}
                          {article.relevance_score != null && (
                            <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${
                              article.relevance_score >= 80 ? "text-emerald-400 bg-emerald-500/10" :
                              article.relevance_score >= 70 ? "text-blue-400 bg-blue-500/10" :
                              "text-gray-400 bg-white/5"
                            }`}>
                              {article.relevance_score}%
                            </span>
                          )}
                          <span className="text-[10px] text-gray-500">{article.source_name}</span>
                          <span className="text-[10px] text-gray-600">{article.published_at ? formatDate(article.published_at) : formatDate(article.created_at)}</span>
                        </div>
                        <h3 className="text-sm font-semibold text-white leading-relaxed mb-1.5 line-clamp-2">
                          {article.title}
                        </h3>
                        {article.summary && (
                          <p className="text-xs text-gray-400 leading-relaxed line-clamp-2 mb-2">
                            {article.summary}
                          </p>
                        )}
                        {article.keywords && (
                          <div className="flex items-center gap-1.5 flex-wrap">
                            {article.keywords.split(", ").slice(0, 4).map((kw) => (
                              <span key={kw} className="text-[9px] text-gray-600 bg-white/5 px-1.5 py-0.5 rounded-full">
                                {kw}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      <a
                        href={article.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="shrink-0 p-2 rounded-xl text-gray-500 hover:text-emerald-400 hover:bg-emerald-500/10 transition-colors"
                      >
                        <ExternalLink className="w-4 h-4" />
                      </a>
                    </div>
                  </GlassCard>
                </motion.div>
              ))}
            </div>
          )}

          {data && data.length >= limit && (
            <div className="flex items-center justify-center gap-3 mt-8">
              <button
                onClick={() => setPage(Math.max(0, page - 1))}
                disabled={page === 0}
                className="px-4 py-2 rounded-xl text-xs font-medium text-gray-400 bg-white/5 hover:bg-white/10 transition-colors disabled:opacity-30"
              >
                السابق
              </button>
              <span className="text-xs text-gray-500">الصفحة {page + 1}</span>
              <button
                onClick={() => setPage(page + 1)}
                disabled={!data || data.length < limit}
                className="px-4 py-2 rounded-xl text-xs font-medium text-gray-400 bg-white/5 hover:bg-white/10 transition-colors disabled:opacity-30"
              >
                التالي
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
