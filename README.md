# Card Printer

Interface web para o [silhouette-card-maker](https://github.com/Alan-Cha/silhouette-card-maker) (MIT, código em `engine/`).
O usuário cola a lista do Moxfield, escolhe papel/opções e baixa o PDF. Equivale a:

```
python plugins/mtg/fetch.py game/decklist/deck.txt moxfield
python create_pdf.py --paper_size a4
```

- `backend/` FastAPI. Cada job roda numa cópia isolada do motor (`engine/`), em fila com `MAX_WORKERS` simultâneos; PDFs expiram após `JOB_TTL_SECONDS`.
- `frontend/` Vite + React, servido por nginx (que também faz proxy de `/api`).

## Deploy (VPS)

```sh
cp .env.example .env   # ajuste PORT / ACCESS_TOKEN
docker compose up -d --build
```

Acesse `http://IP:PORT`. Para HTTPS, ponha um proxy reverso (Caddy/Traefik/nginx do host) na frente da porta publicada.
Recomendado: defina `ACCESS_TOKEN`, pois cada job baixa muitas imagens do Scryfall e usa CPU.

## Desenvolvimento

```sh
pip install -r engine/requirements.txt -r backend/requirements.txt
ENGINE_PYTHON=$(which python) uvicorn app.main:app --app-dir backend --reload
cd frontend && npm install && npm run dev   # proxy /api -> localhost:8000
```

## Atualizar o motor

Substitua os `.py`, `assets/` e `plugins/mtg/` em `engine/` pelos do repositório upstream.
