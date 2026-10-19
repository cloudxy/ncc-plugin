import { useQuery } from "@tanstack/react-query";
import { api, type Json } from "./api";

export function useCreationPolicy() {
  return useQuery({
    queryKey: ["policy"],
    queryFn: () => api<Json>("/policy"),
  });
}
