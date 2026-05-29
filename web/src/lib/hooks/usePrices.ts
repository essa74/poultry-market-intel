import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, PriceListParams, PriceRecordCreate, PredictionListParams } from "@/lib/api";
import toast from "react-hot-toast";

export function usePricesList(params?: PriceListParams) {
  return useQuery({
    queryKey: ["prices", params],
    queryFn: () => api.prices.list(params),
    staleTime: 30_000,
    retry: 2,
  });
}

export function usePredictionsList(params?: PredictionListParams) {
  return useQuery({
    queryKey: ["predictions", params],
    queryFn: () => api.predictions.list(params),
    staleTime: 60_000,
    retry: 2,
  });
}

export function useHealthCheck() {
  return useQuery({
    queryKey: ["health"],
    queryFn: () => api.health(),
    retry: 1,
  });
}

export function useCreatePrice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: PriceRecordCreate) => api.prices.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prices"] });
      toast.success("تم إضافة السجل بنجاح");
    },
    onError: (err: Error) => {
      toast.error(err.message || "حدث خطأ أثناء إضافة السجل");
    },
  });
}

export function useDeletePrice() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: number) => api.prices.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["prices"] });
      toast.success("تم حذف السجل بنجاح");
    },
    onError: (err: Error) => {
      toast.error(err.message || "حدث خطأ أثناء حذف السجل");
    },
  });
}

export function useLatestEggPrice() {
  return useQuery({
    queryKey: ["prices", "latestEgg"],
    queryFn: async () => {
      const records = await api.prices.list({
        product_type: "fertilized_eggs",
        limit: 1,
      });
      return records.length > 0 ? records[0] : null;
    },
    staleTime: 30_000,
  });
}

export function useLatestChickPrice() {
  return useQuery({
    queryKey: ["prices", "latestChick"],
    queryFn: async () => {
      const records = await api.prices.list({
        product_type: "day_old_chicks",
        limit: 1,
      });
      return records.length > 0 ? records[0] : null;
    },
    staleTime: 30_000,
  });
}

export function useRecentTrend(productType?: string, weeks: number = 6) {
  const startDate = new Date();
  startDate.setDate(startDate.getDate() - weeks * 7);

  return useQuery({
    queryKey: ["prices", "trend", productType, weeks],
    queryFn: () =>
      api.prices.list({
        product_type: productType,
        start_date: startDate.toISOString().split("T")[0],
      }),
    staleTime: 60_000,
  });
}

export function useLatestPrices(params?: { source_id?: number; product_type?: string; category?: string; limit?: number }) {
  return useQuery({
    queryKey: ["prices", "latest", params],
    queryFn: () => api.prices.latest(params),
    refetchInterval: 15_000,
    staleTime: 10_000,
  });
}

export function usePriceTrends(productType?: string, days: number = 90) {
  return useQuery({
    queryKey: ["prices", "trends", productType, days],
    queryFn: () => api.prices.trends(productType, days),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
}

export function usePriceStats(params?: { product_type?: string; start_date?: string; end_date?: string }) {
  return useQuery({
    queryKey: ["prices", "stats", params],
    queryFn: async () => {
      const records = await api.prices.list(params);
      if (!records.length) return null;

      const prices = records.map((r) => r.price);
      const sum = prices.reduce((a, b) => a + b, 0);
      const avg = sum / prices.length;
      const sorted = [...prices].sort((a, b) => a - b);

      return {
        count: records.length,
        average: avg,
        min: sorted[0],
        max: sorted[sorted.length - 1],
        latest: records[0],
        change: records.length >= 2 ? ((records[0].price - records[records.length - 1].price) / records[records.length - 1].price) * 100 : 0,
      };
    },
    staleTime: 30_000,
  });
}
