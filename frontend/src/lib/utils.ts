import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDuration(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function assetUrl(storagePath: string): string {
  if (storagePath.startsWith("http")) return storagePath;
  const artifactBase = process.env.NEXT_PUBLIC_ARTIFACT_BASE_URL;
  if (artifactBase) return `${artifactBase.replace(/\/$/, "")}/${storagePath}`;
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  return `${base}/artifacts/${storagePath}`;
}

export function toWsBase(httpBase: string): string {
  // When using Next.js proxy (empty base), derive WS URL from window.location
  if (!httpBase && typeof window !== "undefined") {
    const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${proto}//${window.location.host}`;
  }
  if (httpBase.startsWith("https://")) return httpBase.replace("https://", "wss://");
  return httpBase.replace("http://", "ws://");
}
