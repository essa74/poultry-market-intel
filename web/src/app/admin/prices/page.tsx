"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { Save, FileText, Loader2, CheckCircle2, XCircle } from "lucide-react";
import PageHeader from "@/components/PageHeader";
import GlassCard from "@/components/GlassCard";

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

function getAdminToken(): string {
  if (typeof window !== "undefined") {
    return localStorage.getItem("admin_token") || "";
  }
  return "";
}

function headers(): Record<string, string> {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  const token = getAdminToken();
  if (token) h["X-Admin-Token"] = token;
  return h;
}

const PRODUCT_TYPES = [
  { value: "fertilized_eggs", label: "بيض مخصب" },
  { value: "day_old_chicks", label: "كتاكيت عمر يوم" },
];

const CATEGORIES: Record<string, { value: string; label: string }[]> = {
  fertilized_eggs: [
    { value: "white", label: "أبيض" },
    { value: "sasso", label: "ساسو" },
    { value: "baladi", label: "بلدي" },
    { value: "local", label: "محلي" },
    { value: "duck", label: "بط" },
    { value: "quail", label: "سمان" },
    { value: "turkey", label: "رومي" },
    { value: "ostrich", label: "نعام" },
  ],
  day_old_chicks: [
    { value: "white", label: "أبيض" },
    { value: "sasso", label: "ساسو" },
    { value: "baladi", label: "بلدي" },
  ],
};

type Mode = "single" | "bulk";

export default function AdminPricesPage() {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<Mode>("single");

  const [productType, setProductType] = useState("fertilized_eggs");
  const [category, setCategory] = useState("white");
  const [rawName, setRawName] = useState("");
  const [price, setPrice] = useState("");
  const [source, setSource] = useState("يدوي");
  const [recordedDate, setRecordedDate] = useState(new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");

  const [bulkText, setBulkText] = useState("");
  const [bulkSource, setBulkSource] = useState("يدوي");
  const [bulkDate, setBulkDate] = useState(new Date().toISOString().slice(0, 10));

  const [result, setResult] = useState<{
    saved?: number; failed?: number; failedLines?: string[];
  } | null>(null);

  const singleMutation = useMutation({
    mutationFn: async (data: Record<string, unknown>) => {
      const r = await fetch(`${getApiBase()}/admin/prices/manual`, {
        method: "POST", headers: headers(), body: JSON.stringify(data),
      });
      return r.json();
    },
    onSuccess: (data) => {
      if (data.success) {
        toast.success("تم حفظ السعر بنجاح");
        setPrice("");
        setRawName("");
        setNotes("");
        queryClient.invalidateQueries({ queryKey: ["prices"] });
      } else {
        toast.error(data.error || "فشل الحفظ");
      }
    },
    onError: () => toast.error("فشل الاتصال بالخادم"),
  });

  const bulkMutation = useMutation({
    mutationFn: async (data: Record<string, unknown>) => {
      const r = await fetch(`${getApiBase()}/admin/prices/bulk`, {
        method: "POST", headers: headers(), body: JSON.stringify(data),
      });
      return r.json();
    },
    onSuccess: (data) => {
      if (data.success) {
        toast.success(data.message);
        setResult({ saved: data.saved_count, failed: data.failed_count, failedLines: data.failed_lines });
        setBulkText("");
        queryClient.invalidateQueries({ queryKey: ["prices"] });
      } else {
        toast.error(data.error || "فشل الحفظ");
      }
    },
    onError: () => toast.error("فشل الاتصال بالخادم"),
  });

  function handleSingleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const p = parseFloat(price);
    if (!p || p <= 0) { toast.error("السعر مطلوب"); return; }
    singleMutation.mutate({
      product_type: productType,
      category,
      raw_product_name: rawName,
      price: p,
      unit: "per_unit",
      source,
      recorded_date: recordedDate,
      notes: notes || undefined,
    });
  }

  function handleBulkSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!bulkText.trim()) { toast.error("الصق الأسطر أولاً"); return; }
    bulkMutation.mutate({
      lines: bulkText,
      source: bulkSource,
      recorded_date: bulkDate,
    });
  }

  const categories = CATEGORIES[productType] || CATEGORIES.fertilized_eggs;

  return (
    <div dir="rtl">
      <PageHeader
        title="إدخال الأسعار يدوياً"
        subtitle="إضافة أسعار السوق الحقيقية بشكل يدوي — مفرد أو بالجملة"
        badge="يدوي"
      />

      <GlassCard>
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setMode("single")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              mode === "single"
                ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                : "text-gray-400 hover:text-white hover:bg-white/5"
            }`}
          >
            <Save className="w-4 h-4" /> إدخال مفرد
          </button>
          <button
            onClick={() => setMode("bulk")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              mode === "bulk"
                ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                : "text-gray-400 hover:text-white hover:bg-white/5"
            }`}
          >
            <FileText className="w-4 h-4" /> إدخال بالجملة
          </button>
        </div>

        {mode === "single" ? (
          <form onSubmit={handleSingleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">نوع المنتج</label>
                <select
                  value={productType}
                  onChange={(e) => { setProductType(e.target.value); setCategory(CATEGORIES[e.target.value]?.[0]?.value || "white"); }}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                >
                  {PRODUCT_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">التصنيف</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                >
                  {categories.map((c) => (
                    <option key={c.value} value={c.value}>{c.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">اسم المنتج (وصف)</label>
                <input
                  type="text"
                  value={rawName}
                  onChange={(e) => setRawName(e.target.value)}
                  placeholder="مثال: بيض مخصب أبيض شركات"
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500 placeholder:text-gray-600"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">السعر (ج.م)</label>
                <input
                  type="number"
                  step="0.1"
                  min="0.1"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  placeholder="15.0"
                  required
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500 placeholder:text-gray-600"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">المصدر</label>
                <input
                  type="text"
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">التاريخ</label>
                <input
                  type="date"
                  value={recordedDate}
                  onChange={(e) => setRecordedDate(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">ملاحظات</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500 placeholder:text-gray-600"
              />
            </div>
            <div className="flex justify-start">
              <button
                type="submit"
                disabled={singleMutation.isPending}
                className="flex items-center gap-2 px-6 py-2.5 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-lg text-sm font-medium hover:bg-emerald-500/30 transition-colors disabled:opacity-50"
              >
                {singleMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                حفظ السعر
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleBulkSubmit} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">المصدر</label>
                <input
                  type="text"
                  value={bulkSource}
                  onChange={(e) => setBulkSource(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-400 mb-1">التاريخ</label>
                <input
                  type="date"
                  value={bulkDate}
                  onChange={(e) => setBulkDate(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">
                الأسعار — سطر لكل منتج
              </label>
              <textarea
                value={bulkText}
                onChange={(e) => setBulkText(e.target.value)}
                rows={8}
                dir="rtl"
                placeholder={"بيض مخصب ابيض شركات 15\nبيض مخصب ساسو 11\nبيض مخصب بلدي هجين 4.5"}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white font-arabic focus:outline-none focus:border-emerald-500 placeholder:text-gray-600"
              />
              <p className="text-xs text-gray-500 mt-1">
                كل سطر: اسم المنتج + السعر. أمثلة: بيض مخصب ابيض شركات 15, بيض ساسو 11, بيض بلدي 4.5
              </p>
            </div>
            <div className="flex justify-start">
              <button
                type="submit"
                disabled={bulkMutation.isPending}
                className="flex items-center gap-2 px-6 py-2.5 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-lg text-sm font-medium hover:bg-emerald-500/30 transition-colors disabled:opacity-50"
              >
                {bulkMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
                حفظ الكل
              </button>
            </div>

            {result && (
              <div className="mt-4 p-4 rounded-lg bg-white/5 border border-white/10">
                <div className="flex items-center gap-2 mb-2">
                  {result.failed && result.failed > 0 ? (
                    <XCircle className="w-5 h-5 text-gold-400" />
                  ) : (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  )}
                  <span className="text-sm text-white font-medium">
                    تم حفظ {result.saved} سعر بنجاح
                    {result.failed && result.failed > 0 ? `، فشل ${result.failed} سطر` : ""}
                  </span>
                </div>
                {result.failedLines && result.failedLines.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs text-gray-400 mb-1">الأسطر التي لم يتم التعرف عليها:</p>
                    <div className="text-xs text-gray-500 space-y-0.5">
                      {result.failedLines.map((line, i) => (
                        <p key={i} dir="ltr" className="text-gold-400/70">{line}</p>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </form>
        )}
      </GlassCard>
    </div>
  );
}
