export function formatMoney(value: number | null, unit: string) {
  if (value === null) return "Missing";
  const compact = new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 1,
  }).format(value);
  return `${compact} ${unit.replace("PKR ", "")}`;
}

export function formatPercent(value: number | null) {
  if (value === null) return "Missing";
  return `${value.toFixed(value >= 10 ? 1 : 2)}%`;
}

export function formatConfidence(value: number) {
  return `${Math.round(value * 100)}%`;
}

export function formatInteger(value: number | null) {
  if (value === null) return "Pending";
  return new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 }).format(value);
}

export function toneClass(tone: "good" | "watch" | "risk" | "neutral") {
  if (tone === "good") return "border-mint/35 bg-mint/8 text-mint";
  if (tone === "watch") return "border-amber/35 bg-amber/10 text-amber";
  if (tone === "risk") return "border-coral/35 bg-coral/10 text-coral";
  return "border-line bg-white text-muted";
}
