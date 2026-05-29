"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, X, Loader2, Egg } from "lucide-react";
import { useCreatePrice } from "@/lib/hooks/usePrices";
import { PRODUCT_TYPES, BREEDS, GOVERNORATES, UNITS } from "@/lib/constants";
import { ar } from "@/lib/ar";
import GlassCard from "./GlassCard";

interface AddPriceFormProps {
  defaultProduct?: string;
  defaultRegion?: string;
}

export default function AddPriceForm({ defaultProduct, defaultRegion }: AddPriceFormProps) {
  const [isOpen, setIsOpen] = useState(false);
  const createPrice = useCreatePrice();

  const [formData, setFormData] = useState({
    product_type: defaultProduct || "",
    category: "",
    price: "",
    unit: "per_1000",
    region: defaultRegion || "",
    recorded_date: new Date().toISOString().split("T")[0],
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const breeds = formData.product_type ? BREEDS[formData.product_type] || [] : [];

  const validate = () => {
    const errs: Record<string, string> = {};
    if (!formData.product_type) errs.product_type = ar.form.productRequired;
    if (!formData.category) errs.category = ar.form.breedRequired;
    if (!formData.price || Number(formData.price) <= 0) errs.price = ar.form.priceMustBePositive;
    if (!formData.recorded_date) errs.recorded_date = ar.form.dateRequired;
    if (!formData.region) errs.region = ar.form.governorateRequired;
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    createPrice.mutate(
      {
        product_type: formData.product_type,
        category: formData.category,
        price: Number(formData.price),
        currency: "EGP",
        unit: formData.unit,
        region: formData.region,
        recorded_date: formData.recorded_date,
        source: "Poultry Market Intel",
      },
      {
        onSuccess: () => {
          setFormData({
            product_type: defaultProduct || "",
            category: "",
            price: "",
            unit: "per_1000",
            region: defaultRegion || "",
            recorded_date: new Date().toISOString().split("T")[0],
          });
          setErrors({});
          setIsOpen(false);
        },
      },
    );
  };

  const updateField = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: "" }));
    if (field === "product_type") setFormData((prev) => ({ ...prev, category: "" }));
  };

  return (
    <>
      <button
        onClick={() => setIsOpen(true)}
        className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-l from-emerald-600 to-emerald-500 text-white text-sm font-semibold shadow-lg shadow-emerald-500/20 hover:from-emerald-500 hover:to-emerald-400 transition-all duration-300"
      >
        <Plus className="w-4 h-4" />
        {ar.dailyPrices.addPrice}
      </button>

      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
              onClick={() => setIsOpen(false)}
            />
            <motion.div
              initial={{ opacity: 0, scale: 0.95, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.95, y: 20 }}
              transition={{ duration: 0.2, ease: [0.25, 0.25, 0, 1] }}
              className="fixed inset-4 md:inset-auto md:top-1/2 md:left-1/2 md:-translate-x-1/2 md:-translate-y-1/2 md:w-[520px] z-50 glass rounded-2xl p-6 max-h-[90vh] overflow-y-auto"
            >
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-xl bg-emerald-500/10">
                    <Egg className="w-5 h-5 text-emerald-400" />
                  </div>
                  <h2 className="text-lg font-semibold text-white">{ar.dailyPrices.addPrice}</h2>
                </div>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-2 rounded-xl text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1.5">
                      {ar.dailyPrices.productType}
                    </label>
                    <select
                      value={formData.product_type}
                      onChange={(e) => updateField("product_type", e.target.value)}
                      className={`w-full bg-white/5 border ${
                        errors.product_type ? "border-red-500/50" : "border-white/10"
                      } rounded-xl px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-500/50 transition-colors`}
                    >
                      <option value="" className="bg-surface">{ar.form.selectProduct}</option>
                      {PRODUCT_TYPES.map((pt) => (
                        <option key={pt.value} value={pt.value} className="bg-surface">
                          {pt.label}
                        </option>
                      ))}
                    </select>
                    {errors.product_type && (
                      <p className="text-xs text-red-400 mt-1">{errors.product_type}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1.5">
                      {ar.dailyPrices.breed}
                    </label>
                    <select
                      value={formData.category}
                      onChange={(e) => updateField("category", e.target.value)}
                      disabled={!formData.product_type}
                      className={`w-full bg-white/5 border ${
                        errors.category ? "border-red-500/50" : "border-white/10"
                      } rounded-xl px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-500/50 transition-colors disabled:opacity-40`}
                    >
                      <option value="" className="bg-surface">{ar.form.selectBreed}</option>
                      {breeds.map((b) => (
                        <option key={b.value} value={b.value} className="bg-surface">
                          {b.label}
                        </option>
                      ))}
                    </select>
                    {errors.category && (
                      <p className="text-xs text-red-400 mt-1">{errors.category}</p>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1.5">
                      {ar.dailyPrices.governorate}
                    </label>
                    <select
                      value={formData.region}
                      onChange={(e) => updateField("region", e.target.value)}
                      className={`w-full bg-white/5 border ${
                        errors.region ? "border-red-500/50" : "border-white/10"
                      } rounded-xl px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-500/50 transition-colors`}
                    >
                      <option value="" className="bg-surface">{ar.form.selectGovernorate}</option>
                      {GOVERNORATES.map((g) => (
                        <option key={g} value={g} className="bg-surface">
                          {g}
                        </option>
                      ))}
                    </select>
                    {errors.region && (
                      <p className="text-xs text-red-400 mt-1">{errors.region}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1.5">
                      {ar.dailyPrices.date}
                    </label>
                    <input
                      type="date"
                      value={formData.recorded_date}
                      onChange={(e) => updateField("recorded_date", e.target.value)}
                      className={`w-full bg-white/5 border ${
                        errors.recorded_date ? "border-red-500/50" : "border-white/10"
                      } rounded-xl px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-500/50 transition-colors [color-scheme:dark]`}
                    />
                    {errors.recorded_date && (
                      <p className="text-xs text-red-400 mt-1">{errors.recorded_date}</p>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1.5">
                      {ar.dailyPrices.price}
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      min="0"
                      value={formData.price}
                      onChange={(e) => updateField("price", e.target.value)}
                      placeholder={ar.form.enterPrice}
                      className={`w-full bg-white/5 border ${
                        errors.price ? "border-red-500/50" : "border-white/10"
                      } rounded-xl px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-500/50 transition-colors [appearance:textfield]`}
                    />
                    {errors.price && (
                      <p className="text-xs text-red-400 mt-1">{errors.price}</p>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-gray-400 mb-1.5">
                      {ar.dailyPrices.unit}
                    </label>
                    <select
                      value={formData.unit}
                      onChange={(e) => updateField("unit", e.target.value)}
                      className="w-full bg-white/5 border border-white/10 rounded-xl px-3 py-2.5 text-sm text-white outline-none focus:border-emerald-500/50 transition-colors"
                    >
                      {UNITS.map((u) => (
                        <option key={u.value} value={u.value} className="bg-surface">
                          {u.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>

                <div className="flex items-center gap-3 pt-2">
                  <button
                    type="submit"
                    disabled={createPrice.isPending}
                    className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-l from-emerald-600 to-emerald-500 text-white text-sm font-semibold shadow-lg shadow-emerald-500/20 hover:from-emerald-500 hover:to-emerald-400 transition-all duration-300 disabled:opacity-50"
                  >
                    {createPrice.isPending ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Plus className="w-4 h-4" />
                    )}
                    {ar.common.submit}
                  </button>
                  <button
                    type="button"
                    onClick={() => setIsOpen(false)}
                    className="px-4 py-2.5 rounded-xl glass-sm text-sm text-gray-400 hover:text-white transition-colors"
                  >
                    {ar.common.cancel}
                  </button>
                </div>
              </form>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}
