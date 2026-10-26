// Formatting helpers. All times are shown in UTC, which equals UK time in January.

export function fmtNumber(value, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(value)) return "–";
  return Number(value).toLocaleString("en-GB", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

export const fmtMW = (value, digits = 0) => (value === null || value === undefined ? "–" : `${fmtNumber(value, digits)} MW`);
export const fmtMWh = (value) => (value === null || value === undefined ? "–" : `${fmtNumber(value)} MWh`);

export function fmtTime(iso) {
  if (!iso) return "–";
  return new Date(iso).toLocaleString("en-GB", {
    timeZone: "UTC", day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", hour12: false,
  });
}

export function fmtHourMinute(iso) {
  if (!iso) return "";
  return new Date(iso).toLocaleTimeString("en-GB", { timeZone: "UTC", hour: "2-digit", minute: "2-digit", hour12: false });
}

/** "2026-01-05" + 3 -> "2026-01-08" (pure date arithmetic, no time-zone surprises). */
export function addDays(dateString, days) {
  const date = new Date(`${dateString}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

/** Convert two inclusive calendar days into the API's [start, end) timestamps. */
export function toApiRange(startDate, endDate) {
  return { start: `${startDate}T00:00:00Z`, end: `${addDays(endDate, 1)}T00:00:00Z` };
}
