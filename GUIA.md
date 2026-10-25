# Guia: iniciar e usar o Card Printer

O Card Printer transforma uma lista de deck (Moxfield) em um PDF pronto para imprimir e cortar. Por baixo ele roda o [silhouette-card-maker](https://alan-cha.github.io/silhouette-card-maker/tutorial/guide/), equivalente a:

```sh
python plugins/mtg/fetch.py game/decklist/deck.txt moxfield
python create_pdf.py --paper_size a4
```

## 1. Estrutura

| Pasta | O que é |
|---|---|
| `engine/` | O silhouette-card-maker (scripts Python, `assets/`, `plugins/mtg/`). |
| `backend/` | API FastAPI. Recebe a lista, roda o motor e entrega o PDF. |
| `frontend/` | Interface React (Vite). |
| `docker-compose.yml` | Sobe back-end e front-end (nginx) juntos. |

## 2. Iniciar com Docker (produção / VPS)

Requisitos: Docker e Docker Compose.

```sh
cd card-printer
cp .env.example .env
# edite o .env (veja a tabela abaixo)
docker compose up -d --build
```

Acesse `http://IP_DA_VPS:8080` (ou a porta definida em `PORT`).

Comandos úteis:

```sh
docker compose logs -f backend   # acompanhar logs
docker compose restart           # reiniciar
docker compose down              # parar
docker compose up -d --build     # reconstruir após alterações
```

### Variáveis do `.env`

| Variável | Padrão | Descrição |
|---|---|---|
| `PORT` | `8080` | Porta publicada no host. |
| `ACCESS_TOKEN` | vazio | Se preenchido, o app pede esse token ao abrir. Recomendado em servidor público. |
| `MAX_WORKERS` | `2` | Quantos PDFs são gerados ao mesmo tempo. Os demais ficam na fila. |
| `JOB_TTL_SECONDS` | `3600` | Tempo que o PDF fica disponível para download. |

### HTTPS

O compose publica apenas HTTP. Coloque um proxy reverso na frente (Caddy, Traefik ou nginx do host) apontando para a porta `PORT`. Exemplo com Caddy:

```
cartas.seudominio.com {
    reverse_proxy localhost:8080
}
```

## 3. Iniciar em modo desenvolvimento (sem Docker)

Requisitos: Python 3.12+ e Node 20+.

**Back-end** (terminal 1):

```sh
cd card-printer
python3 -m venv venv
. venv/bin/activate
pip install -r engine/requirements.txt -r backend/requirements.txt
DATA_DIR=/tmp/card-printer-data ENGINE_PYTHON=$(which python) \
  uvicorn app.main:app --app-dir backend --reload --port 8000
```

**Front-end** (terminal 2):

```sh
cd card-printer/frontend
npm install
npm run dev
```

Acesse `http://localhost:5173`. O Vite redireciona `/api` para `localhost:8000` (mude com `API_URL=http://host:porta npm run dev`).

## 4. Como usar

1. **Exportar a lista no Moxfield:** abra o deck, vá em *More → Export → Copy for Moxfield*.
2. **Colar na tela:** cole na caixa de texto. Se usar outro site, troque o *Formato* (MTG Arena, MTGO, Archidekt, Deckstats, Simples, Scryfall JSON, CubeCobra CSV). O botão *Usar exemplo* preenche uma lista de teste.
3. **Impressão:**
   - *Papel*: `a4`, `letter`, etc.
   - *Tamanho da carta*: `standard` é o padrão de Magic.
   - *Verso*: em branco ou envie uma imagem (retrato, até 10 MB). Marque *Somente frentes* para não gerar versos.
4. **Versões das cartas** (opcional):
   - *Ignorar set/número da lista*: usa a versão padrão mais recente.
   - Preferir sets antigos, showcase, arte estendida/borderless, Universes Beyond (ou excluí-los), tokens.
   - *Sets preferidos/ignorados*: códigos separados por espaço, ex.: `eld woe`.
   - *Idioma preferido*: cai para inglês se não existir.
5. **Opções avançadas do PDF:** ajuste da imagem (esticar ou cortar), recortar/estender bordas (`3mm`, `0.125in`), PPI, qualidade, contorno de corte, modo sem borda.
6. Clique em **Gerar PDF**. Acompanhe o progresso (baixando imagens, depois montando o PDF) e clique em **Baixar PDF**. O arquivo expira após `JOB_TTL_SECONDS`.

### Imprimir e cortar

- Imprima em **tamanho real** (100%, sem "ajustar à página").
- Para frente e verso, use impressão duplex com **inversão pela borda longa**.
- Para cortar com Silhouette, use os templates de corte do [repositório original](https://github.com/Alan-Cha/silhouette-card-maker/tree/main/cutting_templates) (o tamanho está impresso no PDF). Veja o [tutorial](https://alan-cha.github.io/silhouette-card-maker/tutorial/guide/) para configurações de lâmina.

## 5. API (para scripts)

Se `ACCESS_TOKEN` estiver definido, envie o header `X-Access-Token`.

```sh
# criar job
curl -F 'options={"format":"moxfield","paper_size":"a4"}' \
     -F deck_file=@deck.txt http://localhost:8080/api/jobs
# consultar (status: queued | fetching | building | done | error)
curl http://localhost:8080/api/jobs/ID
# baixar
curl -o deck.pdf http://localhost:8080/api/jobs/ID/pdf
```

Outros endpoints: `GET /api/health`, `GET /api/meta` (papéis, tamanhos e formatos disponíveis).

## 6. Problemas comuns

| Sintoma | Causa provável |
|---|---|
| "Falha ao buscar as cartas" | Formato selecionado não bate com a lista; veja o log na tela. |
| Carta errada ou versão inesperada | Set/número na lista não corresponde à carta; marque *Ignorar set/número*. |
| Job lento | Cada carta é baixada do Scryfall; listas grandes levam minutos. Aumente `MAX_WORKERS` só se a VPS tiver CPU e RAM. |
| "Token de acesso inválido" | O token digitado difere do `ACCESS_TOKEN` do `.env`. |
| "Job não encontrado ou expirado" | O PDF passou do `JOB_TTL_SECONDS` ou o back-end foi reiniciado (jobs ficam em memória). |

## 7. Atualizar o motor

Substitua os `.py` da raiz, `assets/` e `plugins/mtg/` dentro de `engine/` pelos do repositório upstream e rode `docker compose up -d --build`.
