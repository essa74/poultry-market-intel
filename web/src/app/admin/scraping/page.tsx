"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import {
  Activity, RefreshCw, Play, AlertTriangle, CheckCircle2,
  XCircle, Clock, Database, Globe, MessageCircle, ExternalLink, Plus, Trash2, RotateCcw, Key,
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

interface Source {
  id: number; name: string; source_type: string; url: string;
  is_active: boolean; health_score: number; consecutive_failures: number;
  last_success_at: string | null; last_failure_at: string | null;
  config?: { post_urls?: string[]; auto_discover?: boolean; [key: string]: unknown };
  latest_log?: ScrapingLog | null;
}

interface ScrapingLog {
  id: number; source_id: number; status: string;
  records_collected: number; records_skipped: number;
  error_message: string | null; started_at: string;
  finished_at: string | null; duration_seconds: number | null;
  admin_warning: string | null;
  valid_saved: number;
  duplicates_skipped: number;
  invalid_skipped: number;
}

interface RawPrice {
  id: number; source_id: number; product_type: string | null;
  category: string | null; price: number | null; region: string | null;
  recorded_date: string | null; extraction_method: string;
  confidence: number; is_duplicate: boolean; created_at: string;
  raw_text?: string | null;
}

interface Status {
  total_sources: number; active_sources: number;
  healthy_sources: number; failed_sources: number;
  total_logs_today: number; total_collected_today: number;
  scheduler_running: boolean;
  auto_discover_active: boolean;
  auto_discover_interval_hours: number;
}

const sourceIcons: Record<string, React.ReactNode> = {
  website: <Globe className="w-4 h-4" />,
  facebook: <MessageCircle className="w-4 h-4" />,
  telegram: <Activity className="w-4 h-4" />,
  manual: <Database className="w-4 h-4" />,
};

const statusColors: Record<string, string> = {
  success: "text-emerald-400 bg-emerald-500/10",
  partial: "text-gold-400 bg-gold-500/10",
  failed: "text-red-400 bg-red-500/10",
  running: "text-blue-400 bg-blue-500/10",
  pending: "text-gray-400 bg-white/5",
};

function getAdminToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("admin_token") || "";
}

function setAdminToken(token: string) {
  localStorage.setItem("admin_token", token);
}

function clearAdminToken() {
  localStorage.removeItem("admin_token");
}

async function fetchJson<T>(url: string, opts?: RequestInit): Promise<T> {
  const token = getAdminToken();
  const headers: Record<string, string> = {
    ...(opts?.headers as Record<string, string> || {}),
  };
  if (token) {
    headers["X-Admin-Token"] = token;
  }
  const res = await fetch(url, { ...opts, headers });
  if (res.status === 401) {
    clearAdminToken();
    let msg = "هذه العملية تتطلب صلاحية مدير";
    try {
      const body = await res.clone().json();
      if (body.detail) {
        msg = typeof body.detail === "string" ? body.detail : (body.detail.ar || body.detail.en || msg);
      }
    } catch { /* ignore */ }
    throw new Error(msg);
  }
  if (!res.ok) {
    let msg = `HTTP ${res.status}`;
    try {
      const body = await res.clone().json();
      if (body.detail) {
        msg = typeof body.detail === "string" ? body.detail : (body.detail.ar || body.detail.en || msg);
      }
    } catch { /* ignore parse errors */ }
    throw new Error(msg);
  }
  return res.json();
}

export default function AdminScrapingPage() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<"sources" | "logs" | "raw">("sources");
  const [showAddForm, setShowAddForm] = useState(false);
  const [newSource, setNewSource] = useState({ name: "", url: "", source_type: "website", is_active: true });
  const [showManualPrice, setShowManualPrice] = useState(false);
  const [manualPrice, setManualPrice] = useState({
    product_type: "fertilized_eggs",
    category: "white",
    price: "",
    unit: "per_unit",
    source_name: "إدخال يدوي",
    raw_note: "",
    recorded_date: new Date().toISOString().slice(0, 10),
  });

  const { data: status, isLoading: statusLoading } = useQuery<Status>({
    queryKey: ["scraping", "status"],
    queryFn: () => fetchJson(`${getApiBase()}/scraping/status`),
    refetchInterval: 15_000,
  });

  const { data: sources, isLoading: srcLoading, isError: srcError, refetch: refetchSources } = useQuery<Source[]>({
    queryKey: ["scraping", "sources"],
    queryFn: () => fetchJson(`${getApiBase()}/scraping/sources`),
    refetchInterval: 30_000,
  });

  const { data: logs, isLoading: logsLoading } = useQuery<ScrapingLog[]>({
    queryKey: ["scraping", "logs"],
    queryFn: () => fetchJson(`${getApiBase()}/scraping/logs?limit=30`),
    refetchInterval: 15_000,
  });

  const { data: rawPrices, isLoading: rawLoading } = useQuery<RawPrice[]>({
    queryKey: ["scraping", "raw"],
    queryFn: () => fetchJson(`${getApiBase()}/scraping/raw-prices?limit=30`),
    refetchInterval: 15_000,
  });

  const runMutation = useMutation({
    mutationFn: () => fetchJson<{ message: string; status: string }>(`${getApiBase()}/scraping/run`, {
      method: "POST",
    } as RequestInit),
    onSuccess: (data) => {
      toast.success(data.message);
      queryClient.invalidateQueries({ queryKey: ["scraping"] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const runSourceMutation = useMutation({
    mutationFn: (id: number) => fetchJson(`${getApiBase()}/scraping/sources/${id}/run`, {
      method: "POST",
    } as RequestInit),
    onSuccess: () => {
      toast.success("تم تشغيل المصدر");
      queryClient.invalidateQueries({ queryKey: ["scraping", "sources"] });
      queryClient.invalidateQueries({ queryKey: ["scraping", "logs"] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const toggleMutation = useMutation({
    mutationFn: (id: number) => fetchJson(`${getApiBase()}/scraping/sources/${id}/toggle`, {
      method: "PATCH",
    } as RequestInit),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["scraping", "sources"] });
      toast.success("تم تحديث حالة المصدر");
    },
  });

  const createSourceMutation = useMutation({
    mutationFn: (s: typeof newSource) => fetchJson(`${getApiBase()}/scraping/sources`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(s),
    } as RequestInit),
    onSuccess: () => {
      toast.success("تمت إضافة المصدر بنجاح");
      queryClient.invalidateQueries({ queryKey: ["scraping", "sources"] });
      setShowAddForm(false);
      setNewSource({ name: "", url: "", source_type: "website", is_active: true });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const manualPriceMutation = useMutation({
    mutationFn: (data: typeof manualPrice) => fetchJson(`${getApiBase()}/prices/manual`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...data, price: parseFloat(data.price) }),
    } as RequestInit),
    onSuccess: () => {
      toast.success("تم حفظ السعر اليدوي بنجاح");
      queryClient.invalidateQueries({ queryKey: ["prices"] });
      setShowManualPrice(false);
      setManualPrice({
        product_type: "fertilized_eggs",
        category: "white",
        price: "",
        unit: "per_unit",
        source_name: "إدخال يدوي",
        raw_note: "",
        recorded_date: new Date().toISOString().slice(0, 10),
      });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const [selectedSourceId, setSelectedSourceId] = useState<number | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<{ source: Source; show: boolean }>({ source: null as unknown as Source, show: false });
  const [resetConfirm, setResetConfirm] = useState(false);
  const [editingPostUrls, setEditingPostUrls] = useState<{ sourceId: number; urls: string } | null>(null);
  const [expandedDebug, setExpandedDebug] = useState<number | null>(null);
  const [showTokenPrompt, setShowTokenPrompt] = useState(!getAdminToken());
  const [tokenInput, setTokenInput] = useState("");

  const { data: facebookDebug } = useQuery({
    queryKey: ["scraping", "facebook-debug", expandedDebug],
    queryFn: () => expandedDebug ? fetchJson<Record<string, unknown>>(`${getApiBase()}/scraping/sources/${expandedDebug}/facebook-debug`) : null,
    enabled: !!expandedDebug,
    staleTime: 60_000,
  });

  const updateConfigMutation = useMutation({
    mutationFn: ({ id, config }: { id: number; config: Record<string, unknown> }) =>
      fetchJson(`${getApiBase()}/scraping/sources/${id}/post-urls`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...config }),
      } as RequestInit),
    onSuccess: () => {
      toast.success("تم تحديث الإعدادات");
      queryClient.invalidateQueries({ queryKey: ["scraping", "sources"] });
      setEditingPostUrls(null);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const resetMutation = useMutation({
    mutationFn: () => fetchJson<{ message: string }>(`${getApiBase()}/scraping/reset`, {
      method: "POST",
    } as RequestInit),
    onSuccess: (res) => {
      toast.success(res.message);
      queryClient.invalidateQueries({ queryKey: ["scraping"] });
      queryClient.invalidateQueries({ queryKey: ["prices"] });
      setResetConfirm(false);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const deleteSourceMutation = useMutation({
    mutationFn: (id: number) => fetchJson<{ message: string }>(`${getApiBase()}/scraping/sources/${id}`, {
      method: "DELETE",
    } as RequestInit),
    onSuccess: (_, deletedId) => {
      toast.success("تم حذف المصدر بنجاح");
      queryClient.invalidateQueries({ queryKey: ["scraping", "sources"] });
      queryClient.invalidateQueries({ queryKey: ["scraping", "logs"] });
      queryClient.invalidateQueries({ queryKey: ["scraping", "raw"] });
      setDeleteConfirm({ source: null as unknown as Source, show: false });
      if (selectedSourceId === deletedId) {
        setSelectedSourceId(null);
      }
    },
    onError: (err: Error) => toast.error(err.message),
  });

  return (
    <div>
      <PageHeader
        title="إدارة جمع البيانات"
        subtitle="لوحة تحكم نظام جمع الأسعار الآلي — حالة المصادر، السجلات، والبيانات المستخرجة"
        badge="Admin"
      />

      <div className="mb-4 p-4 rounded-xl bg-gold-500/10 border border-gold-500/20">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-gold-400 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm text-gold-300 font-medium">جمع فيسبوك التلقائي غير مضمون على السيرفر المجاني</p>
            <p className="text-xs text-gray-400 mt-1">
              استخدم <Link href="/admin/prices" className="text-emerald-400 hover:underline">إدخال الأسعار اليدوي</Link> للتحديث اليومي — الطريقة المعتمدة حالياً لتحديث الأسعار.
            </p>
          </div>
        </div>
      </div>

      {showTokenPrompt && (
        <GlassCard glow="gold" hover={false} className="mb-4">
          <div className="flex items-center gap-3 flex-wrap">
            <Key className="w-5 h-5 text-gold-400 shrink-0" />
            <span className="text-sm text-gray-300">صلاحية المدير مطلوبة لبعض الإجراءات</span>
            <input
              type="text"
              value={tokenInput}
              onChange={(e) => setTokenInput(e.target.value)}
              placeholder="أدخل رمز المدير"
              className="flex-1 min-w-[120px] bg-white/5 border border-white/10 rounded-xl px-3 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500/50"
            />
            <button
              onClick={() => {
                if (tokenInput.trim()) {
                  setAdminToken(tokenInput.trim());
                  setShowTokenPrompt(false);
                  queryClient.invalidateQueries({ queryKey: ["scraping"] });
                  toast.success("تم حفظ رمز المدير");
                }
              }}
              disabled={!tokenInput.trim()}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white rounded-xl px-4 py-1.5 text-xs font-medium transition-colors"
            >
              حفظ
            </button>
            <button
              onClick={() => setShowTokenPrompt(false)}
              className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
            >
              تخطي
            </button>
          </div>
        </GlassCard>
      )}

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-3 mb-3">
        {[
          { label: "إجمالي المصادر", value: status?.total_sources ?? 0, color: "text-white" },
          { label: "نشط", value: status?.active_sources ?? 0, color: "text-emerald-400" },
          { label: "سليم", value: status?.healthy_sources ?? 0, color: "text-emerald-400" },
          { label: "فاشل", value: status?.failed_sources ?? 0, color: "text-red-400" },
          { label: "سجلات اليوم", value: status?.total_logs_today ?? 0, color: "text-blue-400" },
          { label: "تم الجمع", value: status?.total_collected_today ?? 0, color: "text-gold-400" },
          { label: "المجدول", value: status?.scheduler_running ? "نشط" : "متوقف", color: status?.scheduler_running ? "text-emerald-400" : "text-red-400" },
        ].map((s, i) => (
          <GlassCard key={s.label} glow="none" hover={false} delay={0.05 * i}>
            <p className="text-[10px] text-gray-500 mb-1">{s.label}</p>
            <p className={`text-lg font-bold ${s.color}`}>{s.value}</p>
          </GlassCard>
        ))}
        <GlassCard glow="none" hover={false} delay={0.4}>
          <button
            onClick={() => runMutation.mutate()}
            disabled={runMutation.isPending}
            className="w-full h-full flex items-center justify-center gap-2 text-xs text-emerald-400 hover:text-emerald-300 transition-colors disabled:opacity-50"
          >
            <Play className="w-4 h-4" />
            تشغيل الآن
          </button>
        </GlassCard>
      </div>

      {(() => {
        const lastAutoLog = (logs || []).sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime())[0];
        const totalCollected = (logs || []).reduce((s, l) => s + l.records_collected, 0);
        const totalDuplicates = (logs || []).reduce((s, l) => s + l.duplicates_skipped, 0);
        const totalInvalid = (logs || []).reduce((s, l) => s + l.invalid_skipped, 0);
        return (
      <GlassCard glow="none" hover={false} className="mb-8">
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-xs font-semibold text-white">تفاصيل المجدول</h3>
          <span className={`text-[10px] px-2 py-0.5 rounded-full ${status?.scheduler_running ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"}`}>
            {status?.scheduler_running ? "نشط" : "متوقف"}
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <div>
            <p className="text-[9px] text-gray-600">آخر تشغيل تلقائي</p>
            <p className="text-xs text-gray-300">
              {lastAutoLog ? new Date(lastAutoLog.started_at).toLocaleString("ar-EG") : "لم يتم بعد"}
            </p>
          </div>
          <div>
            <p className="text-[9px] text-gray-600">الحالة</p>
            <p className="text-xs text-gray-300">{status?.scheduler_running ? "المجدول يعمل" : "المجدول متوقف"}</p>
          </div>
          <div>
            <p className="text-[9px] text-gray-600">عدد السجلات</p>
            <p className="text-xs text-gray-300">{totalCollected}</p>
          </div>
          <div>
            <p className="text-[9px] text-gray-600">المكرر</p>
            <p className="text-xs text-gray-300">{totalDuplicates}</p>
          </div>
          <div>
            <p className="text-[9px] text-gray-600">غير الصالح</p>
            <p className="text-xs text-gray-300">{totalInvalid}</p>
          </div>
        </div>
        <div className="mt-3 pt-3 border-t border-white/5 grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <p className="text-[9px] text-gray-600">اكتشاف تلقائي (فيسبوك)</p>
            <p className="text-xs text-gray-300">
              {status?.auto_discover_active
                ? `كل ${status.auto_discover_interval_hours} ساعات`
                : "غير نشط"}
            </p>
          </div>
          <div>
            <p className="text-[9px] text-gray-600">جمع صباحي</p>
            <p className="text-xs text-gray-300">06:00 يومياً</p>
          </div>
          <div>
            <p className="text-[9px] text-gray-600">جمع مسائي</p>
            <p className="text-xs text-gray-300">18:00 يومياً</p>
          </div>
        </div>
      </GlassCard>
        )})()}

      <div className="flex items-center gap-2 mb-6">
        {(["sources", "logs", "raw"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${
              activeTab === tab
                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                : "text-gray-500 hover:text-white glass-sm"
            }`}
          >
            {tab === "sources" ? "المصادر" : tab === "logs" ? "السجلات" : "البيانات الخام"}
          </button>
        ))}
        <div className="flex-1" />
        <button
          onClick={() => queryClient.invalidateQueries({ queryKey: ["scraping"] })}
          className="p-2 rounded-xl text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {activeTab === "sources" && (
        <div className="space-y-3">
          <button
            onClick={() => setResetConfirm(true)}
            className="w-full glass-sm rounded-xl p-3 flex items-center justify-center gap-2 text-sm text-red-400 hover:text-red-300 border border-red-500/20 hover:border-red-500/30 transition-colors mb-2"
          >
            <RotateCcw className="w-4 h-4" />
            إعادة تهيئة البيانات — مسح كل الأسعار والسجلات
          </button>
          <button
            onClick={() => setShowManualPrice(true)}
            className="w-full glass-sm rounded-xl p-3 flex items-center justify-center gap-2 text-sm text-blue-400 hover:text-blue-300 border border-blue-500/20 hover:border-blue-500/30 transition-colors mb-2"
          >
            <Plus className="w-4 h-4" />
            إضافة سعر يدوي
          </button>
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="w-full glass-sm rounded-xl p-3 flex items-center justify-center gap-2 text-sm text-emerald-400 hover:text-emerald-300 transition-colors"
          >
            <Plus className="w-4 h-4" />
            {showAddForm ? "إغلاق" : "إضافة مصدر يدوي"}
          </button>
          {showAddForm && (
            <GlassCard glow="none" hover={false}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
                <input
                  type="text" placeholder="اسم المصدر"
                  value={newSource.name}
                  onChange={(e) => setNewSource({ ...newSource, name: e.target.value })}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500/50"
                />
                <input
                  type="url" placeholder="رابط الموقع"
                  value={newSource.url}
                  onChange={(e) => setNewSource({ ...newSource, url: e.target.value })}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500/50"
                />
                <select
                  value={newSource.source_type}
                  onChange={(e) => setNewSource({ ...newSource, source_type: e.target.value })}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500/50"
                >
                  <option value="website" className="bg-gray-900">موقع إلكتروني</option>
                  <option value="facebook" className="bg-gray-900">فيسبوك</option>
                  <option value="telegram" className="bg-gray-900">تيليجرام</option>
                </select>
                <label className="flex items-center gap-2 text-sm text-gray-400">
                  <input
                    type="checkbox" checked={newSource.is_active}
                    onChange={(e) => setNewSource({ ...newSource, is_active: e.target.checked })}
                    className="rounded bg-white/5 border-white/10"
                  />
                  نشط
                </label>
              </div>
              <button
                onClick={() => createSourceMutation.mutate(newSource)}
                disabled={!newSource.name || !newSource.url || createSourceMutation.isPending}
                className="w-full bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white rounded-xl py-2 text-sm font-medium transition-colors"
              >
                {createSourceMutation.isPending ? "جاري الإضافة..." : "إضافة المصدر"}
              </button>
            </GlassCard>
          )}
          {srcLoading ? <LoadingSpinner size="sm" /> : srcError ? <ErrorDisplay onRetry={() => refetchSources()} /> : null}
          {(sources || []).map((source, i) => (
            <div
              key={source.id}
              onClick={() => setSelectedSourceId(source.id)}
              className={`rounded-2xl transition-all duration-200 ${
                selectedSourceId === source.id ? "ring-1 ring-emerald-500/30" : ""
              }`}
            >
            <GlassCard glow={source.health_score >= 70 ? "emerald" : source.health_score >= 40 ? "gold" : "none"} hover={true} delay={0.05 * i}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className={`p-2 rounded-lg ${source.is_active ? "bg-emerald-500/10" : "bg-white/5"}`}>
                    {sourceIcons[source.source_type] || <Database className="w-4 h-4 text-gray-400" />}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-white">{source.name}</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded-full ${
                        source.is_active ? "bg-emerald-500/10 text-emerald-400" : "bg-white/5 text-gray-500"
                      }`}>
                        {source.is_active ? "نشط" : "متوقف"}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 mt-0.5">
                      <span className="text-[10px] text-gray-500">{source.source_type}</span>
                      <a href={source.url} target="_blank" rel="noopener noreferrer" className="text-[10px] text-blue-400 hover:text-blue-300 flex items-center gap-1">
                        {source.url.slice(0, 40)}… <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                    {source.source_type === "facebook" && (
                      <div className="mt-2">
                        {editingPostUrls?.sourceId === source.id ? (
                          <div className="space-y-2">
                            <textarea
                              value={editingPostUrls.urls}
                              onChange={(e) => setEditingPostUrls({ ...editingPostUrls, urls: e.target.value })}
                              rows={4}
                              className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-[10px] text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500/50 font-mono"
                              placeholder="https://facebook.com/post1&#10;https://facebook.com/post2"
                            />
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => updateConfigMutation.mutate({
                                  id: source.id,
                                  config: {
                                    post_urls: editingPostUrls.urls.split("\n").map(u => u.trim()).filter(Boolean),
                                  },
                                })}
                                disabled={updateConfigMutation.isPending}
                                className="flex-1 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white rounded-xl py-1.5 text-[10px] font-medium transition-colors"
                              >
                                {updateConfigMutation.isPending ? "جاري الحفظ..." : "حفظ"}
                              </button>
                              <button
                                onClick={() => setEditingPostUrls(null)}
                                className="flex-1 bg-white/5 hover:bg-white/10 text-gray-300 rounded-xl py-1.5 text-[10px] font-medium transition-colors"
                              >
                                إلغاء
                              </button>
                            </div>
                          </div>
                        ) : (
                          <button
                            onClick={() => setEditingPostUrls({
                              sourceId: source.id,
                              urls: (source.config?.post_urls || []).join("\n"),
                            })}
                            className="text-[10px] text-blue-400 hover:text-blue-300 flex items-center gap-1 transition-colors"
                          >
                            <Plus className="w-3 h-3" />
                            {source.config?.post_urls?.length
                              ? `روابط المنشورات (${source.config.post_urls.length})`
                              : "إضافة روابط منشورات"}
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
                {source.source_type === "facebook" && (
                  <div className="mt-2 space-y-2">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => updateConfigMutation.mutate({
                          id: source.id,
                          config: { auto_discover: !(source.config?.auto_discover !== false) },
                        })}
                        className={`text-[10px] px-2.5 py-1 rounded-full transition-colors ${
                          source.config?.auto_discover !== false
                            ? "bg-emerald-500/20 text-emerald-400"
                            : "bg-white/5 text-gray-500"
                        }`}
                      >
                        {source.config?.auto_discover !== false ? "✓" : "✗"} اكتشاف المنشورات تلقائيًا
                      </button>
                      {source.config?.auto_discover !== false && (
                        <span className="text-[9px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400">تلقائي</span>
                      )}
                    </div>
                    <p className="text-[9px] text-gray-600 leading-relaxed">
                      يتم فتح الصفحة والبحث عن أسعار البيض المخصب في أحدث المنشورات. روابط المنشورات المباشرة اختيارية.
                    </p>
                  </div>
                )}
                <div className="flex items-center gap-4">
                  <div className="text-left">
                    <div className="flex items-center gap-1.5 mb-1">
                      <div className="h-1.5 w-16 rounded-full bg-white/5 overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            source.health_score >= 70 ? "bg-emerald-500" : source.health_score >= 40 ? "bg-gold-500" : "bg-red-500"
                          }`}
                          style={{ width: `${source.health_score}%` }}
                        />
                      </div>
                      <span className="text-[10px] font-medium text-gray-400">{source.health_score.toFixed(0)}%</span>
                    </div>
                    {source.latest_log && (
                      <p className="text-[9px] text-gray-500">
                        جمع: {source.latest_log.records_collected}
                        {source.latest_log.duplicates_skipped > 0 && ` · مكرر: ${source.latest_log.duplicates_skipped}`}
                        {source.latest_log.invalid_skipped > 0 && ` · غيرصالح: ${source.latest_log.invalid_skipped}`}
                      </p>
                    )}
                    {source.latest_log?.admin_warning && (
                      <p className="text-[9px] text-gold-400 max-w-[200px]" title={source.latest_log.admin_warning}>
                        ⚠ {source.latest_log.admin_warning}
                      </p>
                    )}
                    {source.source_type === "facebook" && source.latest_log?.records_collected === 0 && (
                      <div className="mt-1.5">
                        <button
                          onClick={() => setExpandedDebug(expandedDebug === source.id ? null : source.id)}
                          className="text-[9px] text-blue-400 hover:text-blue-300 transition-colors"
                        >
                          {expandedDebug === source.id ? "إخفاء التفاصيل" : "عرض تفاصيل التصحيح"}
                        </button>
                        {expandedDebug === source.id && facebookDebug && (
                          <div className="mt-1.5 space-y-0.5 text-[9px] text-gray-500">
                            <p>عدد المنشورات المكتشفة: {String(facebookDebug.posts_found ?? facebookDebug.posts_used ?? "?")}</p>
                            <p>عدد منشورات الأسعار: {String(facebookDebug.accepted_posts ?? "?")}</p>
                            <p>عدد أسطر الأسعار: {String(facebookDebug.parsed_price_lines_count ?? facebookDebug.accepted_ocr_lines ?? "?")}</p>
                            {!!facebookDebug.admin_warning && (
                              <p className="text-gold-400">{String(facebookDebug.admin_warning)}</p>
                            )}
                            {!!facebookDebug.facebook_blocked && (
                              <p className="text-red-400">فيسبوك قام بحظر الطلب</p>
                            )}
                            {!!facebookDebug.image_only_detected && (
                              <p className="text-gold-400">محتوى الصور فقط — OCR يحتاج تفعيل</p>
                            )}
                            {!!facebookDebug.sample_post_texts && Array.isArray(facebookDebug.sample_post_texts) && (facebookDebug.sample_post_texts as string[]).length > 0 && (
                              <div className="mt-1">
                                <p className="text-gray-600">نص المنشور:</p>
                                <p className="text-gray-500 line-clamp-2">{(facebookDebug.sample_post_texts as string[])[0]}</p>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                    {source.latest_log?.valid_saved !== undefined && (
                      <p className="text-[9px] text-gray-600 mt-0.5">
                        محفوظ: {source.latest_log.valid_saved} · مكرر: {source.latest_log.duplicates_skipped} · غير صالح: {source.latest_log.invalid_skipped}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => runSourceMutation.mutate(source.id)}
                    disabled={runSourceMutation.isPending}
                    className="p-2 rounded-xl text-emerald-500 hover:text-emerald-400 hover:bg-emerald-500/10 transition-colors disabled:opacity-40"
                    title="تشغيل المصدر"
                  >
                    <Play className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => toggleMutation.mutate(source.id)}
                    className={`p-2 rounded-xl transition-colors ${
                      source.is_active ? "text-gray-500 hover:text-red-400" : "text-gray-600 hover:text-emerald-400"
                    }`}
                  >
                    {source.is_active ? <XCircle className="w-4 h-4" /> : <CheckCircle2 className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => setDeleteConfirm({ source, show: true })}
                    className="p-2 rounded-xl text-gray-600 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </GlassCard>
            </div>
          ))}
        </div>
      )}

      {activeTab === "logs" && (
        <div className="space-y-2">
          {logsLoading ? <LoadingSpinner size="sm" /> : null}
          {(logs || []).map((log) => (
            <div key={log.id}>
              <div className="glass-sm rounded-xl p-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${statusColors[log.status] || "text-gray-400 bg-white/5"}`}>
                    {log.status}
                  </span>
                  <div>
                    <p className="text-xs text-gray-300">المصدر #{log.source_id}</p>
                    <p className="text-[10px] text-gray-500">
                      {log.records_collected} تم الجمع · {log.records_skipped} تم التخطي
                      {log.duration_seconds ? ` · ${log.duration_seconds.toFixed(1)}ث` : ""}
                    </p>
                    {(log.valid_saved > 0 || log.duplicates_skipped > 0 || log.invalid_skipped > 0) && (
                      <p className="text-[9px] text-gray-600 mt-0.5">
                        محفوظ: {log.valid_saved} · مكرر: {log.duplicates_skipped} · غير صالح: {log.invalid_skipped}
                      </p>
                    )}
                  </div>
                </div>
                <div className="text-[10px] text-gray-500">
                  {new Date(log.started_at).toLocaleString("ar-EG")}
                </div>
              </div>
              {log.admin_warning && (
                <div className="mt-1 mr-2 flex items-center gap-1.5 text-[10px] text-gold-400">
                  <AlertTriangle className="w-3 h-3" />
                  {log.admin_warning}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {activeTab === "raw" && (
        <div className="space-y-2">
          {rawLoading ? <LoadingSpinner size="sm" /> : null}
          {(rawPrices || []).map((rp, i) => (
            <div key={rp.id} className="glass-sm rounded-xl p-3">
              <div className="flex items-center gap-2 mb-1.5">
                <span className="badge-green text-[9px]">{(rp.confidence * 100).toFixed(0)}%</span>
                <span className="text-[10px] text-gray-500">{rp.extraction_method}</span>
                {rp.is_duplicate && <span className="text-[10px] text-gold-500">مكرر</span>}
                {rp.product_type && (
                  <span className="text-[10px] text-gray-300">
                    {rp.product_type === "fertilized_eggs" ? "بيض مخصب" : "كتاكيت"}
                    {rp.category ? ` · ${rp.category}` : ""}
                    {rp.price ? ` · ${rp.price} ج.م` : ""}
                    {rp.region ? ` · ${rp.region}` : ""}
                  </span>
                )}
              </div>
              {rp.raw_text && (
                <p className="text-[10px] text-gray-600 leading-relaxed line-clamp-2">{rp.raw_text}</p>
              )}
            </div>
          ))}
        </div>
      )}
      {resetConfirm && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={() => setResetConfirm(false)}
        >
          <GlassCard
            glow="none"
            hover={false}
            onClick={(e: React.MouseEvent) => e.stopPropagation()}
            className="w-full max-w-md mx-4"
          >
            <h3 className="text-base font-semibold text-white mb-3">إعادة تهيئة البيانات</h3>
            <p className="text-sm text-gold-400 flex items-center gap-1.5 mb-3">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              سيتم حذف جميع بيانات السوق بشكل كامل
            </p>
            <ul className="text-xs text-gray-400 space-y-1 mb-4 mr-5 list-disc">
              <li>جميع أسعار السوق (price_records)</li>
              <li>جميع الأسعار الخام المستخرجة (raw_extracted_prices)</li>
              <li>جميع سجلات الجمع (scraping_logs)</li>
              <li>جميع المقالات الإخبارية (news_articles)</li>
            </ul>
            <p className="text-xs text-gray-500 mb-5">لا يمكن التراجع عن هذا الإجراء. المصادر ستبقى كما هي.</p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setResetConfirm(false)}
                className="flex-1 bg-white/5 hover:bg-white/10 text-gray-300 rounded-xl py-2.5 text-sm font-medium transition-colors"
              >
                إلغاء
              </button>
              <button
                onClick={() => resetMutation.mutate()}
                disabled={resetMutation.isPending}
                className="flex-1 bg-red-600 hover:bg-red-500 disabled:opacity-40 text-white rounded-xl py-2.5 text-sm font-medium transition-colors"
              >
                {resetMutation.isPending ? "جاري المسح..." : "مسح كل البيانات"}
              </button>
            </div>
          </GlassCard>
        </div>
      )}
      {showManualPrice && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={() => setShowManualPrice(false)}
        >
          <GlassCard
            glow="none"
            hover={false}
            onClick={(e: React.MouseEvent) => e.stopPropagation()}
            className="w-full max-w-lg mx-4"
          >
            <h3 className="text-base font-semibold text-white mb-4">إضافة سعر يدوي</h3>
            <div className="space-y-3">
              <div>
                <label className="text-xs text-gray-500 mb-1 block">نوع المنتج</label>
                <select
                  value={manualPrice.product_type}
                  onChange={(e) => setManualPrice({ ...manualPrice, product_type: e.target.value })}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500/50"
                >
                  <option value="fertilized_eggs" className="bg-gray-900">بيض مخصب</option>
                  <option value="day_old_chicks" className="bg-gray-900">كتاكيت عمر يوم</option>
                  <option value="feed" className="bg-gray-900">أعلاف</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">التصنيف</label>
                <select
                  value={manualPrice.category}
                  onChange={(e) => setManualPrice({ ...manualPrice, category: e.target.value })}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500/50"
                >
                  {manualPrice.product_type === "feed" ? (
                    <>
                      <option value="feed_corn" className="bg-gray-900">ذرة</option>
                      <option value="feed_soy" className="bg-gray-900">صويا</option>
                    </>
                  ) : (
                    <>
                      <option value="white" className="bg-gray-900">أبيض</option>
                      <option value="sasso" className="bg-gray-900">ساسو</option>
                      <option value="baladi" className="bg-gray-900">بلدي</option>
                      <option value="local" className="bg-gray-900">محلي / فيومي وجميزة</option>
                      <option value="duck" className="bg-gray-900">بط</option>
                      <option value="quail" className="bg-gray-900">سمان</option>
                      <option value="turkey" className="bg-gray-900">رومي</option>
                      <option value="ostrich" className="bg-gray-900">نعام</option>
                      <option value="other" className="bg-gray-900">أخرى</option>
                    </>
                  )}
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">السعر (ج.م)</label>
                  <input
                    type="number" step="0.01" min="0"
                    value={manualPrice.price}
                    onChange={(e) => setManualPrice({ ...manualPrice, price: e.target.value })}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500/50"
                  />
                </div>
                <div>
                  <label className="text-xs text-gray-500 mb-1 block">الوحدة</label>
                  <select
                    value={manualPrice.unit}
                    onChange={(e) => setManualPrice({ ...manualPrice, unit: e.target.value })}
                    className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500/50"
                  >
                    <option value="per_tray" className="bg-gray-900">للطبق</option>
                    <option value="per_egg" className="bg-gray-900">للبيضة</option>
                    <option value="per_unit" className="bg-gray-900">للواحدة</option>
                    <option value="per_ton" className="bg-gray-900">للطن</option>
                  </select>
                </div>
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">اسم المصدر</label>
                <input
                  type="text"
                  value={manualPrice.source_name}
                  onChange={(e) => setManualPrice({ ...manualPrice, source_name: e.target.value })}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500/50"
                  placeholder="إدخال يدوي"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">ملاحظة (اختياري)</label>
                <input
                  type="text"
                  value={manualPrice.raw_note}
                  onChange={(e) => setManualPrice({ ...manualPrice, raw_note: e.target.value })}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-emerald-500/50"
                  placeholder="وصف أو مصدر السعر"
                />
              </div>
              <div>
                <label className="text-xs text-gray-500 mb-1 block">التاريخ</label>
                <input
                  type="date"
                  value={manualPrice.recorded_date}
                  onChange={(e) => setManualPrice({ ...manualPrice, recorded_date: e.target.value })}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500/50"
                />
              </div>
            </div>
            <div className="flex items-center gap-2 mt-5">
              <button
                onClick={() => setShowManualPrice(false)}
                className="flex-1 bg-white/5 hover:bg-white/10 text-gray-300 rounded-xl py-2.5 text-sm font-medium transition-colors"
              >
                إلغاء
              </button>
              <button
                onClick={() => manualPriceMutation.mutate(manualPrice)}
                disabled={!manualPrice.price || manualPriceMutation.isPending}
                className="flex-1 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white rounded-xl py-2.5 text-sm font-medium transition-colors"
              >
                {manualPriceMutation.isPending ? "جاري الحفظ..." : "حفظ السعر اليدوي"}
              </button>
            </div>
          </GlassCard>
        </div>
      )}
      {deleteConfirm.show && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          onClick={() => setDeleteConfirm({ source: null as unknown as Source, show: false })}
        >
          <GlassCard
            glow="none"
            hover={false}
            onClick={(e: React.MouseEvent) => e.stopPropagation()}
            className="w-full max-w-md mx-4"
          >
            <h3 className="text-base font-semibold text-white mb-3">تأكيد الحذف</h3>
            <p className="text-sm text-gray-300 mb-1">
              هل أنت متأكد من حذف المصدر <span className="text-white font-medium">{deleteConfirm.source.name}</span>؟
            </p>
            {deleteConfirm.source.is_active && (
              <p className="text-xs text-gold-400 flex items-center gap-1.5 mb-3">
                <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                سيتم حذف المصدر وكل السجلات المرتبطة به
              </p>
            )}
            <p className="text-xs text-gray-500 mb-5">لا يمكن التراجع عن هذا الإجراء.</p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setDeleteConfirm({ source: null as unknown as Source, show: false })}
                className="flex-1 bg-white/5 hover:bg-white/10 text-gray-300 rounded-xl py-2.5 text-sm font-medium transition-colors"
              >
                إلغاء
              </button>
              <button
                onClick={() => deleteSourceMutation.mutate(deleteConfirm.source.id)}
                disabled={deleteSourceMutation.isPending}
                className="flex-1 bg-red-600 hover:bg-red-500 disabled:opacity-40 text-white rounded-xl py-2.5 text-sm font-medium transition-colors"
              >
                {deleteSourceMutation.isPending ? "جاري الحذف..." : "حذف المصدر"}
              </button>
            </div>
          </GlassCard>
        </div>
      )}
    </div>
  );
}
