const TOKEN_KEY = "cp_token";

export const getToken = () => localStorage.getItem(TOKEN_KEY) || "";
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t);

async function request(path, init = {}) {
  const res = await fetch(path, {
    ...init,
    headers: { "X-Access-Token": getToken(), ...(init.headers || {}) },
  });
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const body = await res.json();
      msg = typeof body.detail === "string" ? body.detail : body.detail?.map((d) => d.msg).join("; ") || msg;
    } catch {}
    const err = new Error(msg);
    err.status = res.status;
    throw err;
  }
  return res;
}

export const health = () => fetch("/api/health").then((r) => r.json());
export const getMeta = () => request("/api/meta").then((r) => r.json());
export const getJob = (id) => request(`/api/jobs/${id}`).then((r) => r.json());

export function createJob({ options, deckText, backFile }) {
  const form = new FormData();
  form.append("options", JSON.stringify(options));
  form.append("deck_text", deckText);
  if (backFile) form.append("back", backFile);
  return request("/api/jobs", { method: "POST", body: form }).then((r) => r.json());
}

export async function downloadPdf(id) {
  const blob = await request(`/api/jobs/${id}/pdf`).then((r) => r.blob());
  const url = URL.createObjectURL(blob);
  const a = Object.assign(document.createElement("a"), { href: url, download: "deck.pdf" });
  a.click();
  URL.revokeObjectURL(url);
}
