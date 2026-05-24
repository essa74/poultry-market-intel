const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface PriceRecord {
  id: number;
  product_type: string;
  category: string;
  price: number;
  currency: string;
  unit: string;
  market?: string;
  region?: string;
  recorded_date: string;
  source?: string;
}

export interface Prediction {
  id: number;
  product_type: string;
  predicted_price: number;
  predicted_date: string;
  confidence_lower?: number;
  confidence_upper?: number;
  model_version?: string;
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return res.json();
}

export const api = {
  prices: {
    list: (params?: { product_type?: string; start_date?: string; end_date?: string }) => {
      const qs = new URLSearchParams(params as Record<string, string>).toString();
      return fetchJson<PriceRecord[]>(`${API_BASE}/prices/?${qs}`);
    },
    create: (data: Omit<PriceRecord, "id" | "created_at" | "updated_at">) =>
      fetchJson<PriceRecord>(`${API_BASE}/prices/`, {
        method: "POST",
        body: JSON.stringify(data),
      }),
  },
  predictions: {
    list: (params?: { product_type?: string; from_date?: string }) => {
      const qs = new URLSearchParams(params as Record<string, string>).toString();
      return fetchJson<Prediction[]>(`${API_BASE}/predictions/?${qs}`);
    },
  },
};
