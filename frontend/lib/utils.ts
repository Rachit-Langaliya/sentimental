import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function fmtNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

export function fmtPct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

export function sentimentColor(sentiment: string): string {
  if (sentiment === "positive") return "text-success";
  if (sentiment === "negative") return "text-danger";
  return "text-ink-2";
}

export function confidenceBadge(conf: number): string {
  if (conf >= 0.75) return "High";
  if (conf >= 0.55) return "Medium";
  return "Low";
}

export function confidenceColor(conf: number): string {
  if (conf >= 0.75) return "text-success";
  if (conf >= 0.55) return "text-warning";
  return "text-danger";
}

export function velocityArrow(velocity: number): string {
  if (velocity > 0.3) return "↑↑";
  if (velocity > 0.1) return "↑";
  if (velocity < -0.1) return "↓";
  return "→";
}
