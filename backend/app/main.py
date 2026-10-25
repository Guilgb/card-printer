import hmac
import io
import json
import threading

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image
from pydantic import ValidationError

from . import config, jobs
from .models import JobOptions


def auth(x_access_token: str = Header(default="")) -> None:
    if config.ACCESS_TOKEN and not hmac.compare_digest(x_access_token, config.ACCESS_TOKEN):
        raise HTTPException(401, "Token de acesso inválido")


app = FastAPI(title="Card Printer", docs_url=None, redoc_url=None)


@app.on_event("startup")
def _startup() -> None:
    jobs.purge_orphans()
    threading.Thread(target=jobs.cleanup_loop, daemon=True).start()


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "auth_required": bool(config.ACCESS_TOKEN)}


@app.get("/api/meta", dependencies=[Depends(auth)])
def meta() -> dict:
    layouts = json.loads((config.ENGINE_DIR / "assets" / "layouts.json").read_text())
    return {
        "paper_sizes": list(layouts["paper_sizes"]),
        "card_sizes": list(layouts["card_sizes"]),
        "formats": list(JobOptions.model_fields["format"].annotation.__args__),
    }


@app.post("/api/jobs", dependencies=[Depends(auth)], status_code=202)
async def create_job(
    options: str = Form("{}"),
    deck_text: str = Form(""),
    deck_file: UploadFile | None = File(None),
    back: UploadFile | None = File(None),
) -> dict:
    try:
        opts = JobOptions.model_validate_json(options)
    except ValidationError as e:
        raise HTTPException(422, e.errors(include_url=False, include_context=False)) from e

    layouts = json.loads((config.ENGINE_DIR / "assets" / "layouts.json").read_text())
    if opts.paper_size not in layouts["paper_sizes"] or opts.card_size not in layouts["card_sizes"]:
        raise HTTPException(422, "Tamanho de papel ou carta inválido")

    if deck_file is not None:
        deck_text = (await deck_file.read(config.MAX_DECK_BYTES + 1)).decode("utf-8", "replace")
    if len(deck_text.encode()) > config.MAX_DECK_BYTES:
        raise HTTPException(413, "Lista grande demais")
    lines = [l for l in deck_text.splitlines() if l.strip()]
    if not lines:
        raise HTTPException(422, "Cole ou envie a lista de cartas")
    if len(lines) > config.MAX_DECK_LINES:
        raise HTTPException(413, f"Máximo de {config.MAX_DECK_LINES} linhas")

    back_png = None
    if opts.back_mode == "upload":
        if back is None:
            raise HTTPException(422, "Envie a imagem do verso")
        raw = await back.read(config.MAX_BACK_BYTES + 1)
        if len(raw) > config.MAX_BACK_BYTES:
            raise HTTPException(413, "Imagem do verso grande demais (máx 10MB)")
        try:
            img = Image.open(io.BytesIO(raw))
            img.load()
        except Exception as e:  # noqa: BLE001
            raise HTTPException(422, "Imagem do verso inválida") from e
        buf = io.BytesIO()
        img.convert("RGB").save(buf, "PNG")
        back_png = buf.getvalue()

    job = jobs.create("\n".join(lines) + "\n", opts, back_png)
    return job.public()


@app.get("/api/jobs/{job_id}", dependencies=[Depends(auth)])
def job_status(job_id: str) -> dict:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job não encontrado ou expirado")
    return job.public()


@app.get("/api/jobs/{job_id}/pdf", dependencies=[Depends(auth)])
def job_pdf(job_id: str) -> FileResponse:
    job = jobs.get(job_id)
    if not job or job.status != "done":
        raise HTTPException(404, "PDF indisponível")
    return FileResponse(job.pdf_path, media_type="application/pdf", filename="deck.pdf")
