export function money(n: number | undefined | null): string {
  if (n == null) return "—";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(n);
}
export function pct(n: number | undefined | null, dp = 2): string {
  if (n == null) return "—";
  return `${(n * 100).toFixed(dp)}%`;
}
export function relTime(iso: string): string {
  const s = (Date.now() - new Date(iso).getTime()) / 1000;
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} hr ago`;
  return `${Math.floor(s / 86400)} d ago`;
}
export const STATUS_STEPS = [
  "DRAFT", "INGESTED", "CERTIFYING", "CALCULATED", "VALIDATED",
  "REMEDIATION", "SIGNED_OFF", "EXPORTED",
];
