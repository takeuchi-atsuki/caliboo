import { useEffect, useState } from "react";

import { apiClient } from "../../lib/apiClient";
import type { HomeSummary } from "../../lib/types";

export function useHomeSummary() {
  const [summary, setSummary] = useState<HomeSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    apiClient
      .get<HomeSummary>("/api/home/summary")
      .then((data) => {
        if (!cancelled) setSummary(data);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return { summary, error };
}
