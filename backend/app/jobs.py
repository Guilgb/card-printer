import json
import shutil
import subprocess
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

from . import config
from .models import JobOptions


@dataclass
class Job:
    id: str
    options: JobOptions
    status: str = "queued"  # queued | fetching | building | done | error
    error: str | None = None
    log: list[str] = field(default_factory=list)
    cards_total: int = 0
    cards_done: int = 0
    created: float = field(default_factory=time.time)

    @property
    def dir(self) -> Path:
        return config.DATA_DIR / self.id

    @property
    def pdf_path(self) -> Path:
        return self.dir / "game" / "output" / "game.pdf"

    def public(self) -> dict:
        return {
            "id": self.id,
            "status": self.status,
            "error": self.error,
            "cards_total": self.cards_total,
            "cards_done": self.cards_done,
            "log": self.log[-200:],
            "expires_at": self.created + config.JOB_TTL_SECONDS,
        }


_jobs: dict[str, Job] = {}
_lock = threading.Lock()
_pool = ThreadPoolExecutor(max_workers=config.MAX_WORKERS)


def get(job_id: str) -> Job | None:
    return _jobs.get(job_id)


def create(deck_text: str, options: JobOptions, back_bytes: bytes | None) -> Job:
    job = Job(id=uuid.uuid4().hex, options=options)
    job.cards_total = _count_cards(deck_text)
    # Cada job roda numa cópia isolada do motor: o fetch.py escreve em game/ relativo à raiz.
    shutil.copytree(config.ENGINE_DIR, job.dir)
    for sub in ("front", "back", "double_sided", "output", "decklist"):
        (job.dir / "game" / sub).mkdir(parents=True, exist_ok=True)
    (job.dir / "game" / "decklist" / "deck.txt").write_text(deck_text, encoding="utf-8")
    if back_bytes:
        (job.dir / "game" / "back" / "back.png").write_bytes(back_bytes)
    with _lock:
        _jobs[job.id] = job
    _pool.submit(_run, job)
    return job


def _count_cards(text: str) -> int:
    n = 0
    for line in text.splitlines():
        parts = line.strip().split(maxsplit=1)
        if len(parts) == 2 and parts[0].rstrip("xX").isdigit():
            n += int(parts[0].rstrip("xX"))
    return n


def _fetch_args(o: JobOptions) -> list[str]:
    a = ["plugins/mtg/fetch.py", "game/decklist/deck.txt", o.format]
    flags = {
        "-i": o.ignore_set_and_collector_number, "--prefer_older_sets": o.prefer_older_sets,
        "--prefer_showcase": o.prefer_showcase, "--prefer_extra_art": o.prefer_extra_art,
        "--prefer_ub": o.prefer_ub, "--ignore_ub": o.ignore_ub, "--tokens": o.tokens,
    }
    a += [f for f, on in flags.items() if on]
    for s in o.prefer_set:
        a += ["-s", s]
    for s in o.ignore_set:
        a += ["--ignore_set", s]
    for s in o.prefer_lang:
        a += ["--prefer_lang", s]
    return a


def _pdf_args(o: JobOptions) -> list[str]:
    a = ["create_pdf.py", "--paper_size", o.paper_size, "--card_size", o.card_size,
         "--fit", o.fit, "--ppi", str(o.ppi), "--quality", str(o.quality)]
    if o.crop:
        a += ["--crop", o.crop]
    if o.extend_edges:
        a += ["--extend_edges", o.extend_edges]
    for flag, on in (("--show_outline", o.show_outline), ("--borderless", o.borderless),
                     ("--only_fronts", o.only_fronts)):
        if on:
            a.append(flag)
    return a


def _exec(job: Job, args: list[str]) -> int:
    proc = subprocess.Popen(
        [config.PYTHON, "-u", *args], cwd=job.dir, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, text=True, errors="replace",
    )
    timer = threading.Timer(config.STEP_TIMEOUT_SECONDS, proc.kill)
    timer.start()
    try:
        assert proc.stdout
        for line in proc.stdout:
            line = line.rstrip()
            if not line:
                continue
            job.log.append(line)
            if line.startswith("Index:"):
                job.cards_done += _qty(line)
        return proc.wait()
    finally:
        timer.cancel()


def _qty(line: str) -> int:
    try:
        return int(line.split("quantity:")[1].split(",")[0])
    except (IndexError, ValueError):
        return 1


def _run(job: Job) -> None:
    o = job.options
    try:
        job.status = "fetching"
        if _exec(job, _fetch_args(o)) != 0 or not any((job.dir / "game" / "front").iterdir()):
            raise RuntimeError("Falha ao buscar as cartas. Confira o formato da lista.")
        job.status = "building"
        if o.only_fronts:
            ds = job.dir / "game" / "double_sided"
            shutil.rmtree(ds, ignore_errors=True)
            ds.mkdir(parents=True, exist_ok=True)
        if _exec(job, _pdf_args(o)) != 0 or not job.pdf_path.exists():
            raise RuntimeError("Falha ao gerar o PDF.")
        job.status = "done"
    except Exception as e:  # noqa: BLE001
        job.status, job.error = "error", str(e)
    finally:
        # Imagens intermediárias não são mais necessárias; só o PDF fica até expirar.
        for sub in ("front", "back", "double_sided"):
            shutil.rmtree(job.dir / "game" / sub, ignore_errors=True)


def cleanup_loop() -> None:
    while True:
        time.sleep(300)
        now = time.time()
        with _lock:
            expired = [j for j in _jobs.values()
                       if now - j.created > config.JOB_TTL_SECONDS and j.status in ("done", "error")]
            for j in expired:
                _jobs.pop(j.id, None)
        for j in expired:
            shutil.rmtree(j.dir, ignore_errors=True)


def purge_orphans() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    for p in config.DATA_DIR.iterdir():
        shutil.rmtree(p, ignore_errors=True)
