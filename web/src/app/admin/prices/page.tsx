"use client";

import { useState, useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import toast from "react-hot-toast";
import { Save, FileText, Loader2, CheckCircle2, XCircle, LayoutDashboard, Scan, Trash2, Upload } from "lucide-react";
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

function jsonHeaders(): Record<string, string> {
  const h: Record<string, string> = { "Content-Type": "application/json" };
  const token = getAdminToken();
  if (token) h["X-Admin-Token"] = token;
  return h;
}

function authHeaders(): Record<string, string> {
  const h: Record<string, string> = {};
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

type Mode = "single" | "bulk" | "ocr";

interface OcrItem {
  product_type: string;
  category: string;
  raw_product_name: string;
  price: number;
  unit: string;
}

export default function AdminPricesPage() {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<Mode>("single");

  // Single entry state
  const [productType, setProductType] = useState("fertilized_eggs");
  const [category, setCategory] = useState("white");
  const [rawName, setRawName] = useState("");
  const [price, setPrice] = useState("");
  const [source, setSource] = useState("يدوي");
  const [recordedDate, setRecordedDate] = useState(new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");

  // Bulk entry state
  const [bulkText, setBulkText] = useState("");
  const [bulkSource, setBulkSource] = useState("يدوي");
  const [bulkDate, setBulkDate] = useState(new Date().toISOString().slice(0, 10));

  // OCR state
  const [ocrImage, setOcrImage] = useState<File | null>(null);
  const [ocrPreviewUrl, setOcrPreviewUrl] = useState<string | null>(null);
  const [ocrDate, setOcrDate] = useState(new Date().toISOString().slice(0, 10));
  const [extractedText, setExtractedText] = useState<string | null>(null);
  const [ocrItems, setOcrItems] = useState<OcrItem[]>([]);
  const [rejectedLines, setRejectedLines] = useState<string[]>([]);
  const [showOcrPreview, setShowOcrPreview] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Common
  const [result, setResult] = useState<{
    saved?: number; failed?: number; failedLines?: string[];
  } | null>(null);
  const [showDashboardLink, setShowDashboardLink] = useState(false);

  const categories = CATEGORIES[productType] || CATEGORIES.fertilized_eggs;

  // Mutations
  const singleMutation = useMutation({
    mutationFn: async (data: Record<string, unknown>) => {
      const r = await fetch(`${getApiBase()}/admin/prices/manual`, {
        method: "POST", headers: jsonHeaders(), body: JSON.stringify(data),
      });
      return r.json();
    },
    onSuccess: (data) => {
      if (data.success) {
        toast.success("تم حفظ السعر بنجاح");
        setPrice(""); setRawName(""); setNotes("");
        setShowDashboardLink(true);
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
        method: "POST", headers: jsonHeaders(), body: JSON.stringify(data),
      });
      return r.json();
    },
    onSuccess: (data) => {
      if (data.success) {
        toast.success(data.message);
        setResult({ saved: data.saved_count, failed: data.failed_count, failedLines: data.failed_lines });
        setBulkText("");
        setShowDashboardLink(true);
        queryClient.invalidateQueries({ queryKey: ["prices"] });
      } else {
        toast.error(data.error || "فشل الحفظ");
      }
    },
    onError: () => toast.error("فشل الاتصال بالخادم"),
  });

  const ocrPreviewMutation = useMutation({
    mutationFn: async (formData: FormData) => {
      const r = await fetch(`${getApiBase()}/admin/prices/ocr-preview`, {
        method: "POST", headers: authHeaders(), body: formData,
      });
      return r.json();
    },
    onSuccess: (data) => {
      if (data.success) {
        setExtractedText(data.extracted_text);
        setOcrItems(data.parsed_items || []);
        setRejectedLines(data.rejected_lines || []);
        setShowOcrPreview(true);
        toast.success(`تم استخراج ${data.parsed_items.length} سعر`);
      } else {
        toast.error(data.error || "فشل التعرف على الصورة");
      }
    },
    onError: () => toast.error("فشل الاتصال بالخادم"),
  });

  const ocrSaveMutation = useMutation({
    mutationFn: async (data: Record<string, unknown>) => {
      const r = await fetch(`${getApiBase()}/admin/prices/ocr-save`, {
        method: "POST", headers: jsonHeaders(), body: JSON.stringify(data),
      });
      return r.json();
    },
    onSuccess: (data) => {
      if (data.success) {
        toast.success(data.message);
        setOcrItems([]);
        setExtractedText(null);
        setShowOcrPreview(false);
        setOcrImage(null);
        setOcrPreviewUrl(null);
        setShowDashboardLink(true);
        queryClient.invalidateQueries({ queryKey: ["prices"] });
      } else {
        toast.error(data.error || "فشل الحفظ");
      }
    },
    onError: () => toast.error("فشل الاتصال بالخادم"),
  });

  // Handlers
  function handleSingleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const p = parseFloat(price);
    if (!p || p <= 0) { toast.error("السعر مطلوب"); return; }
    singleMutation.mutate({
      product_type: productType, category, raw_product_name: rawName,
      price: p, unit: "per_unit", source,
      recorded_date: recordedDate, notes: notes || undefined,
    });
  }

  function handleBulkSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!bulkText.trim()) { toast.error("الصق الأسطر أولاً"); return; }
    bulkMutation.mutate({ lines: bulkText, source: bulkSource, recorded_date: bulkDate });
  }

  function handleImageSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      toast.error("يجب رفع صورة بصيغة jpg أو png أو webp");
      return;
    }
    setOcrImage(file);
    setOcrPreviewUrl(URL.createObjectURL(file));
    setShowOcrPreview(false);
    setExtractedText(null);
    setOcrItems([]);
    setRejectedLines([]);
  }

  function handleOcrPreview() {
    if (!ocrImage) { toast.error("اختر صورة أولاً"); return; }
    const fd = new FormData();
    fd.append("image", ocrImage);
    fd.append("recorded_date", ocrDate);
    ocrPreviewMutation.mutate(fd);
  }

  function handleOcrSave() {
    if (ocrItems.length === 0) { toast.error("لا توجد أسعار للحفظ"); return; }
    ocrSaveMutation.mutate({ items: ocrItems, recorded_date: ocrDate });
  }

  function removeOcrItem(index: number) {
    setOcrItems((prev) => prev.filter((_, i) => i !== index));
  }

  function updateOcrItem(index: number, field: keyof OcrItem, value: string | number) {
    setOcrItems((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], [field]: value };
      return next;
    });
  }

  function getCategoryLabel(cat: string): string {
    for (const group of Object.values(CATEGORIES)) {
      const found = group.find((c) => c.value === cat);
      if (found) return found.label;
    }
    return cat;
  }

  function getProductTypeLabel(t: string): string {
    const found = PRODUCT_TYPES.find((p) => p.value === t);
    return found?.label || t;
  }

  return (
    <div dir="rtl">
      <PageHeader
        title="إدخال أسعار السوق"
        subtitle="أدخل أسعار البيض المخصب والكتاكيت بسرعة لتحديث لوحة التحكم فوراً"
        badge="يدوي"
      />

      <GlassCard>
        <div className="flex gap-2 mb-6 flex-wrap">
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
          <button
            onClick={() => setMode("ocr")}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              mode === "ocr"
                ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                : "text-gray-400 hover:text-white hover:bg-white/5"
            }`}
          >
            <Scan className="w-4 h-4" /> رفع صورة الأسعار
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
        ) : mode === "bulk" ? (
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
              <label className="block text-xs text-gray-400 mb-1">الأسعار — سطر لكل منتج</label>
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
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-gray-400 mb-1">التاريخ</label>
                <input
                  type="date"
                  value={ocrDate}
                  onChange={(e) => setOcrDate(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-emerald-500"
                />
              </div>
              <div className="flex items-end">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handleImageSelect}
                  className="hidden"
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="flex items-center gap-2 px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-sm text-gray-300 hover:text-white hover:bg-white/10 transition-colors"
                >
                  <Upload className="w-4 h-4" />
                  {ocrImage ? ocrImage.name : "اختيار صورة"}
                </button>
              </div>
            </div>

            {ocrPreviewUrl && (
              <div className="rounded-lg overflow-hidden border border-white/10 max-h-80">
                <img src={ocrPreviewUrl} alt="صورة الأسعار" className="w-full object-contain max-h-80" />
              </div>
            )}

            <div className="flex justify-start">
              <button
                type="button"
                onClick={handleOcrPreview}
                disabled={!ocrImage || ocrPreviewMutation.isPending}
                className="flex items-center gap-2 px-6 py-2.5 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-lg text-sm font-medium hover:bg-emerald-500/30 transition-colors disabled:opacity-50"
              >
                {ocrPreviewMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Scan className="w-4 h-4" />}
                قراءة الصورة
              </button>
            </div>

            {showOcrPreview && (
              <div className="space-y-4">
                {extractedText && (
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">النص المستخرج:</label>
                    <div className="bg-white/5 border border-white/10 rounded-lg p-3 text-sm text-gray-300 whitespace-pre-wrap max-h-40 overflow-y-auto" dir="rtl">
                      {extractedText}
                    </div>
                  </div>
                )}

                {rejectedLines.length > 0 && (
                  <div>
                    <label className="block text-xs text-gray-400 mb-1">أسطر غير متعرف عليها:</label>
                    <div className="bg-white/5 border border-white/10 rounded-lg p-3 text-sm text-gold-400/70 whitespace-pre-wrap max-h-24 overflow-y-auto">
                      {rejectedLines.map((l, i) => <p key={i}>{l}</p>)}
                    </div>
                  </div>
                )}

                {ocrItems.length > 0 && (
                  <div>
                    <label className="block text-xs text-gray-400 mb-2">
                      الأسعار المستخرجة — {ocrItems.length} سعر:
                    </label>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="text-gray-400 border-b border-white/10">
                            <th className="text-right px-2 py-1">المنتج</th>
                            <th className="text-right px-2 py-1">التصنيف</th>
                            <th className="text-right px-2 py-1">الوصف</th>
                            <th className="text-left px-2 py-1">السعر</th>
                            <th className="text-center px-2 py-1">الوحدة</th>
                            <th className="text-center px-2 py-1"></th>
                          </tr>
                        </thead>
                        <tbody>
                          {ocrItems.map((item, i) => (
                            <tr key={i} className="border-b border-white/5 hover:bg-white/5">
                              <td className="px-2 py-1">
                                <select
                                  value={item.product_type}
                                  onChange={(e) => updateOcrItem(i, "product_type", e.target.value)}
                                  className="bg-white/5 border border-white/10 rounded px-1 py-0.5 text-xs text-white w-full"
                                >
                                  {PRODUCT_TYPES.map((t) => (
                                    <option key={t.value} value={t.value}>{t.label}</option>
                                  ))}
                                </select>
                              </td>
                              <td className="px-2 py-1">
                                <select
                                  value={item.category}
                                  onChange={(e) => updateOcrItem(i, "category", e.target.value)}
                                  className="bg-white/5 border border-white/10 rounded px-1 py-0.5 text-xs text-white w-full"
                                >
                                  {(CATEGORIES[item.product_type] || CATEGORIES.fertilized_eggs).map((c) => (
                                    <option key={c.value} value={c.value}>{c.label}</option>
                                  ))}
                                </select>
                              </td>
                              <td className="px-2 py-1">
                                <input
                                  type="text"
                                  value={item.raw_product_name}
                                  onChange={(e) => updateOcrItem(i, "raw_product_name", e.target.value)}
                                  className="bg-white/5 border border-white/10 rounded px-1 py-0.5 text-xs text-white w-full"
                                />
                              </td>
                              <td className="px-2 py-1">
                                <input
                                  type="number"
                                  step="0.1"
                                  min="0.1"
                                  value={item.price}
                                  onChange={(e) => updateOcrItem(i, "price", parseFloat(e.target.value) || 0)}
                                  className="bg-white/5 border border-white/10 rounded px-1 py-0.5 text-xs text-white w-20 text-left"
                                />
                              </td>
                              <td className="px-2 py-1 text-center text-xs text-gray-400">
                                {item.unit === "per_unit" ? "للقطعة" : item.unit}
                              </td>
                              <td className="px-2 py-1 text-center">
                                <button
                                  onClick={() => removeOcrItem(i)}
                                  className="text-red-400 hover:text-red-300 transition-colors"
                                >
                                  <Trash2 className="w-3.5 h-3.5" />
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {ocrItems.length > 0 && (
                  <div className="flex justify-start">
                    <button
                      type="button"
                      onClick={handleOcrSave}
                      disabled={ocrSaveMutation.isPending}
                      className="flex items-center gap-2 px-6 py-2.5 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-lg text-sm font-medium hover:bg-emerald-500/30 transition-colors disabled:opacity-50"
                    >
                      {ocrSaveMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                      حفظ الأسعار المستخرجة
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </GlassCard>

      {showDashboardLink && (
        <div className="mt-6 flex justify-center">
          <Link
            href="/dashboard"
            className="flex items-center gap-2 px-6 py-3 bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 rounded-xl text-sm font-medium hover:bg-emerald-500/30 transition-colors"
          >
            <LayoutDashboard className="w-4 h-4" />
            عرض لوحة التحكم
          </Link>
        </div>
      )}
    </div>
  );
}
