import { useResource } from "../../lib/useResource";
import type { HomeSummary } from "../../lib/types";

export function useHomeSummary() {
  const { data, error } = useResource<HomeSummary>("/api/home/summary", 5000);
  return { summary: data, error };
}
