import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useModelsStatus(productType?: string) {
  return useQuery({
    queryKey: ["models", "status", productType],
    queryFn: () => api.models.status(productType),
    staleTime: 60_000,
    retry: 2,
  });
}
