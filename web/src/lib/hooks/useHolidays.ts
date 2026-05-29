import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useHolidaysList(params?: { from_date?: string; to_date?: string; event_type?: string; limit?: number }) {
  return useQuery({
    queryKey: ["holidays", "list", params],
    queryFn: () => api.holidays.list(params),
    staleTime: 300_000,
    retry: 2,
  });
}

export function useUpcomingHolidays(days: number = 60) {
  return useQuery({
    queryKey: ["holidays", "upcoming", days],
    queryFn: () => api.holidays.upcoming(days),
    staleTime: 300_000,
    retry: 2,
  });
}

export function useActiveHolidays() {
  return useQuery({
    queryKey: ["holidays", "active"],
    queryFn: () => api.holidays.active(),
    staleTime: 60_000,
    retry: 2,
  });
}

export function useHolidayImpact(productType: string, targetDate?: string) {
  return useQuery({
    queryKey: ["holidays", "impact", productType, targetDate],
    queryFn: () => api.holidays.impact(productType, targetDate),
    staleTime: 300_000,
    enabled: !!productType,
  });
}
