// All communication with the Python backend lives in this one file.
const BASE = (import.meta.env.VITE_API_URL || "").replace(/\/$/, "");

async function get(path, params = {}, signal) {
  const query = new URLSearchParams(params).toString();
  const response = await fetch(`${BASE}/api${path}${query ? `?${query}` : ""}`, { signal });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      if (body.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* response was not JSON - keep the generic message */
    }
    throw new Error(detail);
  }
  return response.json();
}

export const getMeta = (signal) => get("/meta", {}, signal);
export const getAnalysis = (params, signal) => get("/analysis", params, signal);
export const getHorizonProfile = (params, signal) => get("/horizon-profile", params, signal);
export const getDayAhead = (params, signal) => get("/day-ahead", params, signal);
export const exportUrl = (params) => `${BASE}/api/export.csv?${new URLSearchParams(params)}`;
