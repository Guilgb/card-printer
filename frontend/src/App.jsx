import { useEffect, useRef, useState } from "react";
import { createJob, downloadPdf, getJob, getMeta, getToken, health, setToken } from "./api.js";

const FORMAT_LABELS = {
  moxfield: "Moxfield", mtga: "MTG Arena", mtgo: "MTGO", archidekt: "Archidekt",
  deckstats: "Deckstats", simple: "Simples (1 Nome)", scryfall_json: "Scryfall JSON",
  cubecobra_csv: "CubeCobra CSV",
};
const LANGS = ["en", "sp", "fr", "de", "it", "pt", "jp", "kr", "ru", "cs", "ct"];
const STATUS_LABELS = {
  queued: "Na fila…", fetching: "Baixando imagens das cartas…",
  building: "Montando o PDF…", done: "Pronto!", error: "Erro",
};
const EXAMPLE = `1 Sol Ring (C21) 263
1 Command Tower (CMR) 350
1 Pegasus Guardian // Rescue the Foal (CLB) 36

SIDEBOARD:
1 Containment Priest (M21) 13`;

const DEFAULTS = {
  format: "moxfield", paper_size: "a4", card_size: "standard", back_mode: "blank",
  ignore_set_and_collector_number: false, prefer_older_sets: false, prefer_showcase: false,
  prefer_extra_art: false, prefer_ub: false, ignore_ub: false, tokens: false,
  prefer_set: [], ignore_set: [], prefer_lang: [],
  fit: "stretch", crop: "", extend_edges: "", show_outline: false, borderless: false,
  only_fronts: false, ppi: 300, quality: 100,
};

const splitCodes = (s) => s.split(/[\s,]+/).filter(Boolean).map((c) => c.toLowerCase());

function Check({ label, hint, checked, onChange }) {
  return (
    <label className="check">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span>{label}{hint && <small>{hint}</small>}</span>
    </label>
  );
}

function Field({ label, children }) {
  return <label className="field"><span>{label}</span>{children}</label>;
}

function Login({ onDone }) {
  const [value, setValue] = useState("");
  return (
    <main className="card narrow">
      <h1>Acesso</h1>
      <form onSubmit={(e) => { e.preventDefault(); setToken(value); onDone(); }}>
        <Field label="Token de acesso">
          <input type="password" value={value} onChange={(e) => setValue(e.target.value)} autoFocus />
        </Field>
        <button className="primary">Entrar</button>
      </form>
    </main>
  );
}

export default function App() {
  const [meta, setMeta] = useState(null);
  const [needsLogin, setNeedsLogin] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [deckText, setDeckText] = useState("");
  const [opts, setOpts] = useState(DEFAULTS);
  const [setsText, setSetsText] = useState({ prefer: "", ignore: "" });
  const [backFile, setBackFile] = useState(null);
  const [job, setJob] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const logRef = useRef(null);

  const set = (key) => (value) => setOpts((o) => ({ ...o, [key]: value }));

  const load = async () => {
    setLoadError("");
    try {
      const h = await health();
      if (h.auth_required && !getToken()) return setNeedsLogin(true);
      setMeta(await getMeta());
      setNeedsLogin(false);
    } catch (e) {
      if (e.status === 401) setNeedsLogin(true);
      else setLoadError("Não foi possível conectar ao servidor.");
    }
  };
  useEffect(() => { load(); }, []);

  const active = job && !["done", "error"].includes(job.status);
  useEffect(() => {
    if (!active) return;
    const t = setInterval(async () => {
      try { setJob(await getJob(job.id)); } catch (e) { setError(e.message); setJob(null); }
    }, 1500);
    return () => clearInterval(t);
  }, [active, job?.id]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [job?.log?.length]);

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      const options = {
        ...opts,
        prefer_set: splitCodes(setsText.prefer),
        ignore_set: splitCodes(setsText.ignore),
        crop: opts.crop || null,
        extend_edges: opts.extend_edges || null,
      };
      setJob(await createJob({ options, deckText, backFile: opts.back_mode === "upload" ? backFile : null }));
    } catch (err) {
      if (err.status === 401) setNeedsLogin(true);
      else setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (needsLogin) return <Login onDone={load} />;
  if (loadError) return <main className="card narrow"><p className="error">{loadError}</p><button onClick={load}>Tentar novamente</button></main>;
  if (!meta) return <main className="card narrow"><p>Carregando…</p></main>;

  const pct = job?.cards_total ? Math.min(100, Math.round((job.cards_done / job.cards_total) * 100)) : 0;

  return (
    <main className="layout">
      <header>
        <h1>Card Printer</h1>
        <p>Cole sua lista, escolha o papel e baixe o PDF pronto para imprimir e cortar (Silhouette Card Maker).</p>
      </header>

      <form className="card" onSubmit={submit}>
        <section>
          <div className="row between">
            <h2>1. Lista de cartas</h2>
            <button type="button" className="link" onClick={() => setDeckText(EXAMPLE)}>Usar exemplo</button>
          </div>
          <Field label="Formato">
            <select value={opts.format} onChange={(e) => set("format")(e.target.value)}>
              {meta.formats.map((f) => <option key={f} value={f}>{FORMAT_LABELS[f] || f}</option>)}
            </select>
          </Field>
          <textarea
            rows={12} value={deckText} onChange={(e) => setDeckText(e.target.value)}
            placeholder="No Moxfield: More → Export → Copy for Moxfield, e cole aqui."
            spellCheck={false}
          />
        </section>

        <section>
          <h2>2. Impressão</h2>
          <div className="grid">
            <Field label="Papel">
              <select value={opts.paper_size} onChange={(e) => set("paper_size")(e.target.value)}>
                {meta.paper_sizes.map((p) => <option key={p}>{p}</option>)}
              </select>
            </Field>
            <Field label="Tamanho da carta">
              <select value={opts.card_size} onChange={(e) => set("card_size")(e.target.value)}>
                {meta.card_sizes.map((p) => <option key={p}>{p}</option>)}
              </select>
            </Field>
            <Field label="Verso">
              <select value={opts.back_mode} onChange={(e) => set("back_mode")(e.target.value)}>
                <option value="blank">Em branco</option>
                <option value="upload">Enviar imagem</option>
              </select>
            </Field>
          </div>
          {opts.back_mode === "upload" && (
            <Field label="Imagem do verso (retrato, até 10MB)">
              <input type="file" accept="image/*" onChange={(e) => setBackFile(e.target.files[0] || null)} required />
            </Field>
          )}
          <Check label="Somente frentes" checked={opts.only_fronts} onChange={set("only_fronts")} />
        </section>

        <section>
          <h2>3. Versões das cartas</h2>
          <div className="checks">
            <Check label="Ignorar set/número da lista" hint="Usa a versão mais recente padrão" checked={opts.ignore_set_and_collector_number} onChange={set("ignore_set_and_collector_number")} />
            <Check label="Preferir sets mais antigos" checked={opts.prefer_older_sets} onChange={set("prefer_older_sets")} />
            <Check label="Preferir showcase" checked={opts.prefer_showcase} onChange={set("prefer_showcase")} />
            <Check label="Preferir arte estendida/borderless" checked={opts.prefer_extra_art} onChange={set("prefer_extra_art")} />
            <Check label="Preferir Universes Beyond" checked={opts.prefer_ub} onChange={(v) => setOpts((o) => ({ ...o, prefer_ub: v, ignore_ub: v ? false : o.ignore_ub }))} />
            <Check label="Excluir Universes Beyond" checked={opts.ignore_ub} onChange={(v) => setOpts((o) => ({ ...o, ignore_ub: v, prefer_ub: v ? false : o.prefer_ub }))} />
            <Check label="Incluir tokens relacionados" checked={opts.tokens} onChange={set("tokens")} />
          </div>
          <div className="grid">
            <Field label="Sets preferidos (ex: eld woe)">
              <input value={setsText.prefer} onChange={(e) => setSetsText((s) => ({ ...s, prefer: e.target.value }))} />
            </Field>
            <Field label="Sets ignorados">
              <input value={setsText.ignore} onChange={(e) => setSetsText((s) => ({ ...s, ignore: e.target.value }))} />
            </Field>
            <Field label="Idioma preferido">
              <select value={opts.prefer_lang[0] || ""} onChange={(e) => set("prefer_lang")(e.target.value ? [e.target.value] : [])}>
                <option value="">Inglês (padrão)</option>
                {LANGS.filter((l) => l !== "en").map((l) => <option key={l}>{l}</option>)}
              </select>
            </Field>
          </div>
        </section>

        <details>
          <summary>Opções avançadas do PDF</summary>
          <div className="grid">
            <Field label="Ajuste da imagem">
              <select value={opts.fit} onChange={(e) => set("fit")(e.target.value)}>
                <option value="stretch">Esticar</option>
                <option value="crop">Cortar (mantém proporção)</option>
              </select>
            </Field>
            <Field label="Recortar bordas (ex: 3mm)">
              <input value={opts.crop} onChange={(e) => set("crop")(e.target.value)} placeholder="opcional" pattern="\d{1,2}(\.\d{1,2})?(mm|in)?" />
            </Field>
            <Field label="Estender bordas (ex: 0.125in)">
              <input value={opts.extend_edges} onChange={(e) => set("extend_edges")(e.target.value)} placeholder="opcional" pattern="\d{1,2}(\.\d{1,2})?(mm|in)?" />
            </Field>
            <Field label="PPI">
              <input type="number" min={100} max={600} value={opts.ppi} onChange={(e) => set("ppi")(Number(e.target.value))} />
            </Field>
            <Field label="Qualidade (50–100)">
              <input type="number" min={50} max={100} value={opts.quality} onChange={(e) => set("quality")(Number(e.target.value))} />
            </Field>
          </div>
          <div className="checks">
            <Check label="Mostrar contorno de corte" checked={opts.show_outline} onChange={set("show_outline")} />
            <Check label="Sem borda (mais cartas por página)" checked={opts.borderless} onChange={set("borderless")} />
          </div>
        </details>

        {error && <p className="error">{error}</p>}
        <button className="primary" disabled={submitting || active || !deckText.trim()}>
          {submitting ? "Enviando…" : "Gerar PDF"}
        </button>
      </form>

      {job && (
        <section className="card">
          <h2>{STATUS_LABELS[job.status]}</h2>
          {job.status !== "error" && job.status !== "done" && (
            <div className="bar"><div style={{ width: `${job.status === "building" ? 100 : pct}%` }} /></div>
          )}
          {job.cards_total > 0 && <p className="muted">{Math.min(job.cards_done, job.cards_total)} / {job.cards_total} cartas</p>}
          {job.error && <p className="error">{job.error}</p>}
          {job.status === "done" && (
            <>
              <button className="primary" onClick={() => downloadPdf(job.id)}>Baixar PDF</button>
              <p className="muted">O arquivo fica disponível por cerca de 1 hora. Imprima em tamanho real (sem ajustar à página); frente e verso com inversão pela borda longa.</p>
            </>
          )}
          <details open={job.status === "error"}>
            <summary>Log</summary>
            <pre ref={logRef}>{job.log.join("\n")}</pre>
          </details>
        </section>
      )}
    </main>
  );
}
