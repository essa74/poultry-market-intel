export interface PriceRecord {
  id: number;
  product_type: string;
  category: string;
  price: number;
  currency: string;
  unit: string;
  market?: string | null;
  region?: string | null;
  recorded_date: string;
  source?: string | null;
  raw_product_name?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PriceRecordCreate {
  product_type: string;
  category: string;
  price: number;
  currency: string;
  unit: string;
  market?: string | null;
  region?: string | null;
  recorded_date: string;
  source?: string | null;
}

export interface HolidayEvent {
  id: number;
  name_ar: string;
  name_en: string;
  event_type: string;
  start_date: string;
  end_date: string;
  impact_description?: string | null;
  impact_percentage?: number | null;
  affected_products?: string[] | null;
  notes?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ModelStatusItem {
  model_name: string;
  model_is_trained: boolean;
  required_days: number;
  available_days: number;
  can_train: boolean;
  mae: number | null;
  rmse: number | null;
  mape: number | null;
  forecast_horizon: number | null;
  last_trained_at: string | null;
}

export interface ModelsStatusResponse {
  models: ModelStatusItem[];
  ensemble_can_train: boolean;
  data_start_date: string | null;
  data_end_date: string | null;
}

export interface Prediction {
  id: number;
  product_type: string;
  predicted_price: number;
  predicted_date: string;
  confidence_lower?: number | null;
  confidence_upper?: number | null;
  model_version?: string | null;
  created_at: string;
}

export interface PriceListParams {
  product_type?: string;
  category?: string;
  region?: string;
  source_id?: number;
  start_date?: string;
  end_date?: string;
  limit?: number;
  offset?: number;
}

export interface PredictionListParams {
  product_type?: string;
  from_date?: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public data?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${getApiBase()}${path}`;
  try {
    const res = await fetch(url, {
      headers: { "Content-Type": "application/json", ...init?.headers },
      ...init,
    });

    if (!res.ok) {
      let errorData: unknown;
      try {
        errorData = await res.json();
      } catch {
        errorData = await res.text().catch(() => null);
      }
      throw new ApiError(
        res.status,
        typeof errorData === "object" && errorData && "detail" in errorData
          ? String((errorData as { detail: string }).detail)
          : `خطأ في الخادم (${res.status})`,
        errorData,
      );
    }

    if (res.status === 204) return undefined as T;
    return res.json();
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err instanceof TypeError && err.message === "Failed to fetch") {
      throw new ApiError(0, "تعذر الاتصال بالخادم. تأكد من تشغيل الخادم.");
    }
    throw new ApiError(0, "حدث خطأ غير متوقع في الشبكة.");
  }
}

export const api = {
  holidays: {
    list: (params?: { from_date?: string; to_date?: string; event_type?: string; limit?: number }) => {
      const qs = new URLSearchParams();
      if (params) {
        Object.entries(params).forEach(([key, val]) => {
          if (val !== undefined && val !== null && val !== "") {
            qs.set(key, String(val));
          }
        });
      }
      const query = qs.toString();
      return request<HolidayEvent[]>(`/holidays/${query ? `?${query}` : ""}`);
    },

    upcoming: (days?: number) => {
      const qs = days ? `?days=${days}` : "";
      return request<HolidayEvent[]>(`/holidays/upcoming${qs}`);
    },

    active: () => request<HolidayEvent[]>("/holidays/active"),

    impact: (productType: string, targetDate?: string) => {
      const qs = new URLSearchParams({ product_type: productType });
      if (targetDate) qs.set("target_date", targetDate);
      return request<{ product_type: string; target_date: string; impact_percentage: number }>(
        `/holidays/impact?${qs.toString()}`,
      );
    },

    types: () => request<string[]>("/holidays/types"),
  },

  prices: {
    list: (params?: PriceListParams) => {
      const qs = new URLSearchParams();
      if (params) {
        Object.entries(params).forEach(([key, val]) => {
          if (val !== undefined && val !== null && val !== "") {
            qs.set(key, String(val));
          }
        });
      }
      const query = qs.toString();
      return request<PriceRecord[]>(`/prices/${query ? `?${query}` : ""}`);
    },

    get: (id: number) => request<PriceRecord>(`/prices/${id}`),

    create: (data: PriceRecordCreate) =>
      request<PriceRecord>("/prices/", {
        method: "POST",
        body: JSON.stringify(data),
      }),

    update: (id: number, data: Partial<PriceRecordCreate>) =>
      request<PriceRecord>(`/prices/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      }),

    delete: (id: number) =>
      request<void>(`/prices/${id}`, { method: "DELETE" }),

    latest: (params?: { source_id?: number; product_type?: string; category?: string; limit?: number }) => {
      const qs = new URLSearchParams();
      if (params) {
        Object.entries(params).forEach(([key, val]) => {
          if (val !== undefined && val !== null && val !== "") {
            qs.set(key, String(val));
          }
        });
      }
      const query = qs.toString();
      return request<PriceRecord[]>(`/prices/latest${query ? `?${query}` : ""}`);
    },

    trends: (productType?: string, days?: number) => {
      const qs = new URLSearchParams();
      if (productType) qs.set("product_type", productType);
      if (days) qs.set("days", String(days));
      return request<PriceRecord[]>(`/prices/trends?${qs.toString()}`);
    },
  },

  models: {
    status: (productType?: string) => {
      const qs = productType ? `?product_type=${productType}` : "";
      return request<ModelsStatusResponse>(`/models/status${qs}`);
    },
  },

  predictions: {
    list: (params?: PredictionListParams) => {
      const qs = new URLSearchParams();
      if (params) {
        Object.entries(params).forEach(([key, val]) => {
          if (val !== undefined && val !== null && val !== "") {
            qs.set(key, String(val));
          }
        });
      }
      const query = qs.toString();
      return request<Prediction[]>(`/predictions/${query ? `?${query}` : ""}`);
    },
  },

  health: () => request<{ status: string }>("/health"),
};
