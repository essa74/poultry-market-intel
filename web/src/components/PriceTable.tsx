"use client";

import { motion } from "framer-motion";
import { Trash2, TrendingUp, TrendingDown } from "lucide-react";
import { PriceRecord } from "@/lib/api";
import { useDeletePrice } from "@/lib/hooks/usePrices";
import { PRODUCT_TYPES, BREEDS, GOVERNORATES } from "@/lib/constants";
import { ar } from "@/lib/ar";

interface PriceTableProps {
  data: PriceRecord[];
  isLoading?: boolean;
}

function getLabel(value: string, options: { value: string; label: string }[]): string {
  return options.find((o) => o.value === value)?.label || value;
}

function getBreedLabel(productType: string, category: string): string {
  const breeds = BREEDS[productType];
  if (!breeds) return category;
  return breeds.find((b) => b.value === category)?.label || category;
}

export default function PriceTable({ data, isLoading }: PriceTableProps) {
  const deletePrice = useDeletePrice();

  if (!data.length) {
    return (
      <div className="text-center py-12">
        <p className="text-sm text-gray-500">{ar.common.noData}</p>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/5">
            <th className="text-right py-3 px-3 text-xs font-medium text-gray-500">{ar.dailyPrices.productType}</th>
            <th className="text-right py-3 px-3 text-xs font-medium text-gray-500">{ar.dailyPrices.breed}</th>
            <th className="text-right py-3 px-3 text-xs font-medium text-gray-500">{ar.dailyPrices.governorate}</th>
            <th className="text-right py-3 px-3 text-xs font-medium text-gray-500">{ar.dailyPrices.price}</th>
            <th className="text-right py-3 px-3 text-xs font-medium text-gray-500">{ar.dailyPrices.date}</th>
            <th className="text-center py-3 px-3 text-xs font-medium text-gray-500">{ar.dailyPrices.actions}</th>
          </tr>
        </thead>
        <tbody>
          {data.map((record, i) => {
            const productLabel = getLabel(record.product_type, PRODUCT_TYPES as unknown as { value: string; label: string }[]);
            const breedLabel = getBreedLabel(record.product_type, record.category);
            return (
              <motion.tr
                key={record.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2, delay: i * 0.03 }}
                className="border-b border-white/5 hover:bg-white/[0.02] transition-colors"
              >
                <td className="py-3 px-3">
                  <span className="text-white font-medium">{productLabel}</span>
                </td>
                <td className="py-3 px-3 text-gray-400">{breedLabel}</td>
                <td className="py-3 px-3 text-gray-400">{record.region || "-"}</td>
                <td className="py-3 px-3">
                  <span className="font-semibold text-white">{record.price.toFixed(1)}</span>
                  <span className="text-xs text-gray-500 mr-1">ج.م</span>
                </td>
                <td className="py-3 px-3 text-xs text-gray-500">
                  {record.recorded_date}
                </td>
                <td className="py-3 px-3 text-center">
                  <button
                    onClick={() => {
                      if (window.confirm(ar.form.confirmDelete)) {
                        deletePrice.mutate(record.id);
                      }
                    }}
                    disabled={deletePrice.isPending}
                    className="p-1.5 rounded-lg text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-40"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </motion.tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
