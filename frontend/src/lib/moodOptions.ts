import type { Mood } from "./types";

export const MOOD_OPTIONS: { value: Mood; label: string; bg: string; fg: string }[] = [
  { value: "happy", label: "うれしい", bg: "var(--color-pink-200)", fg: "var(--color-pink-500)" },
  { value: "fun", label: "たのしい", bg: "var(--color-orange-200)", fg: "var(--color-orange-600)" },
  { value: "foggy", label: "もやもや", bg: "var(--color-purple-200)", fg: "var(--color-purple-500)" },
  { value: "tired", label: "つかれた", bg: "var(--color-blue-200)", fg: "var(--color-blue-500)" },
];
