# ARQUITETURA — PontoFácil

> **Estado:** implementação parcial. O backend (FastAPI, persistência JSON, OCR, regras de negócio, API de lote assíncrono — etapas 1–8 — e **exportação Excel + downloads — etapas 10–11**) e a integração do frontend com os endpoints de lote/resultados/dúvidas/correção/exportação estão implementados. A tela preenche a seção "Planilhas" e baixa os `.xlsx`. O endpoint de compatibilidade `POST /processar` (etapa 9) segue pendente. O frontend (TanStack Start + React + Vite) é preservado.

---

## 1. Visão geral

O PontoFácil é composto por:

- **Frontend** já existente, criado no Lovable (TanStack Start + React + Vite + TypeScript), que deve ser **preservado**.
- **Backend** proposto em **Python + FastAPI**, com OCR local (**OpenCV + Tesseract**), **persistência em JSON** (sem banco de dados) e exportação **Excel (openpyxl)**.

Comunicação: **API REST/JSON** entre frontend e backend. CORS restrito a origens locais de desenvolvimento.

---

## 2. Estrutura atual (verificada)

```
PontoFacil/
├─ .lovable/project.json          # template tanstack_start_ts_current
├─ public/                        # favicon, robots.txt
├─ src/
│  ├─ components/ui/              # componentes shadcn/Radix
│  ├─ hooks/use-mobile.tsx
│  ├─ lib/
│  │  ├─ api.ts                   # INTEGRAÇÃO COM O BACKEND (contrato atual)
│  │  ├─ error-capture.ts
│  │  ├─ error-page.ts
│  │  ├─ lovable-error-reporting.ts
│  │  └─ utils.ts
│  ├─ routes/
│  │  ├─ __root.tsx               # shell da aplicação (meta, QueryClient, Outlet)
│  │  ├─ index.tsx                # TELA PRINCIPAL (upload, progresso, revisão, planilhas)
│  │  └─ README.md
│  ├─ test/app-routing.test.tsx   # Vitest
│  ├─ router.tsx                  # createRouter + QueryClient
│  ├─ routeTree.gen.ts            # gerado automaticamente
│  ├─ server.ts                   # SSR error wrapper
│  ├─ start.ts                    # middleware de erro + CSRF
│  └─ styles.css                  # design system (Tailwind 4, oklch)
├─ package.json                   # scripts: dev/build/lint/test
├─ vite.config.ts                 # @lovable.dev/vite-tanstack-config
├─ CONTEXT.md                     # instruções permanentes
├─ ALESSANY.jpg                   # imagem de referência (folha de ponto 08/2026)
└─ AGENTS.md                      # aviso Lovable
```

### Pontos-chave do frontend

- **Roteamento:** file-based (TanStack Router). Não criar `src/pages/`. O único layout raiz é `src/routes/__root.tsx`.
- **Contrato atual (`src/lib/api.ts`):**
  - `API_URL = import.meta.env.VITE_API_URL` (sem barra final); `isBackendConnected()` habilita a UI só quando `VITE_API_URL` existe.
  - `processarCartoes(files, onUploadProgress)` → **`POST {API_URL}/processar`** via `XMLHttpRequest`, `multipart/form-data`, campo `arquivos`; progresso pelo evento de upload.
  - **Lote assíncrono (integrado):** `criarLote` (`POST /api/lotes`), `obterLote` (`GET /api/lotes/{id}`), `obterResultados` (`/resultados`), `obterDuvidas` (`/duvidas`), `corrigirRegistro` (`PATCH /api/registros/{id}`), `aguardarLote` (polling até estado terminal), `paraRegistros` (conversão para o formato da tela) e **`exportarLote`** (`POST /api/lotes/{id}/exportar`) / **`baixarArquivo`** (download).
  - Tipos: `Registro`, `Planilha`, `ResultadoProcessamento`, `LoteStatus`, `ResultadosLote`, `Duvida`, `RegistroAPI`, `ExportacaoLote`, entre outros.
  - `resolveUrl(url)` monta URLs absolutas de download a partir de caminhos relativos retornados pela API.
- **Tela principal (`src/routes/index.tsx`):** upload (fotos/pasta/ZIP com `jszip`), etapas visuais, resumo (enviados/processados/revisão/planilhas), tabela de revisão editável (4 campos) e lista de planilhas com "Baixar Excel". O envio usa `criarLote` + `aguardarLote`; resultados e dúvidas vêm de `obterResultados`/`obterDuvidas`; a correção usa `corrigirRegistro` (o layout foi preservado). ZIPs são expandidos no cliente antes do envio.
- **Regra de revisão na UI:** `needsReview()` usa o campo `revisar` derivado de `status_validacao`/dúvidas; a lógica antiga (revisar, confiança <0.7 ou horário nulo) permanece como fallback.

### Ferramentas de qualidade já disponíveis

- `npm run lint` (ESLint), `npm run format` (Prettier), `npm run test` (Vitest), `npm run build`.

---

## 3. Arquitetura proposta

```
PontoFacil/
├─ src/                              # FRONTEND (preservado; apenas evolui lib/api.ts)
│  └─ lib/api.ts                     # adiciona funções de lote assíncrono
├─ backend/                          # NOVO — Python + FastAPI
│  ├─ app/
│  │  ├─ main.py                     # app FastAPI, CORS, routers, healthcheck
│  │  ├─ config.py                   # limites, caminhos de storage, origens CORS
│  │  ├─ api/
│  │  │  ├─ lotes.py                 # POST /api/lotes, GET status/resultados/duvidas
│  │  │  ├─ registros.py             # PATCH /api/registros/{id}
│  │  │  ├─ exportacao.py            # POST /api/lotes/{id}/exportar + downloads
│  │  │  └─ compat.py                # POST /processar (contrato atual do frontend)
│  │  ├─ schemas/                    # modelos Pydantic (entrada/saída)
│  │  ├─ services/                   # orquestração de lote, worker/progresso, exportação
│  │  ├─ ocr/                        # OpenCV (pré-processo) + Tesseract + parser da folha
│  │  ├─ business/                   # normalização, validação, cálculo de horas e exportabilidade (puro)
│  │  ├─ persistence/                # repositórios JSON (sem SGBD)
│  │  ├─ security/                   # validação de arquivos, paths seguros, limites
│  │  └─ exports/                    # geração openpyxl (planilha por funcionário e consolidada)
│  ├─ storage/                       # dados locais (gitignored)
│  │  ├─ lotes/{lote_id}/            # imagens + JSONs do lote
│  │  └─ exports/                    # planilhas geradas
│  ├─ tests/                         # pytest (unitário/integração/segurança)
│  └─ requirements.txt
├─ docs/                             # PRD.md, ARQUITETURA.md
└─ memoria/                          # memória por prompt
```

> Adapta a estrutura de referência do `CONTEXT.md` §9 ao projeto real. Não move nem recria o frontend.

### Diagrama de camadas

```
┌──────────────────────────────────────────────┐
│ Frontend (TanStack Start + React)            │
│ src/routes/index.tsx  ── src/lib/api.ts      │
└───────────────┬──────────────────────────────┘
                │ REST/JSON (multipart para upload)
┌───────────────▼──────────────────────────────┐
│ FastAPI (app/api)                             │
│  /processar (compat)   /api/lotes ...         │
├──────────────────────────────────────────────┤
│ services  (orquestração de lote + worker)     │
│    │              │                │          │
│  ocr/          business/         exports/     │
│ OpenCV+Tesser  regras+cálculo    openpyxl     │
│    │              │                │          │
│  security/    persistence/ (JSON) ─┘          │
└──────────────────────────────────────────────┘
                │
        storage/lotes/{id}/ (imagens + JSONs)
        storage/exports/    (planilhas .xlsx)
```

---

## 4. Fluxo de processamento

```
Seleção (fotos/pasta/ZIP)
   │
   ▼
RF-001/002  Upload + validação (assinatura, tamanho, quantidade)
   │
   ▼
RF-003  Criar lote  →  storage/lotes/{lote_id}/lote.json
   │
   ▼
RF-004  Worker em segundo plano (progresso em lote.json)
   │   ┌─────────────────────────────────────────────┐
   │   │ por imagem (erros isolados):                 │
   │   │  OpenCV: correção de inclinação/contraste/   │
   │   │          ruído/recorte                        │
   │   │  Tesseract: OCR → texto bruto                 │
   │   │  parser: funcionário, período e dias         │
   │   │  (coluna "Hora Extra" é ignorada)             │
   │   └─────────────────────────────────────────────┘
   ▼
RF-007  Normalização → registros.json (valor bruto preservado)
   ▼
RF-008  Validação/regras → duvidas.json (incertos marcados)
   ▼
RF-009  Revisão manual (PATCH /api/registros/{id}) → correcoes.json
   ▼
RF-010  Cálculo de horas (só dados validados)
   ▼
RF-012/013  openpyxl → storage/exports/{lote_id}/ (por funcionário + consolidado;
    │        apenas confirmados/corrigidos válidos; "Hora Extra" ignorada)
    ▼
RF-015  Downloads (GET lista; download restrito ao lote)
```

Um erro em uma imagem **não** interrompe as demais; o lote pode terminar como `concluido_com_pendencias`.

---

## 5. Persistência em JSON (sem banco)

Decisão explícita do usuário: **não usar banco de dados**.

- Um diretório por lote: `storage/lotes/{lote_id}/`.
- Arquivos: `lote.json` (metadados/estado/progresso), `registros.json`, `duvidas.json`, `correcoes.json`, `imagens/` (arquivos de entrada com nome interno), e a lista `arquivos_gerados` com referência às planilhas em `storage/exports/{lote_id}/`.
- **Escrita atômica:** gravar em arquivo temporário e renomear para evitar corrupção.
- **Recuperação:** estado reconstruído pela releitura dos JSONs (sem transações de SGBD).
- **Sem duplicar imagens** desnecessariamente.
- **`lote_id`** gerado pelo sistema (opaco), nunca derivado de entrada do usuário.
- **Exportações isoladas por lote:** `storage/exports/{lote_id}/`; o download exige que o `arquivo_id` pertença ao lote (evita acesso cruzado).

> O `CONTEXT.md` foi atualizado para refletir a persistência em JSON (antes especificava SQLite). O controle de concorrência deve ser simples (um worker por lote), já que não há SGBD.

---

## 6. Componentes e responsabilidades

- **`api/`** — expõe endpoints, valida Pydantic, nunca contém regra de negócio.
- **`services/`** — cria lote, dispara/coordena worker em segundo plano, atualiza progresso, isola erros por arquivo.
- **`ocr/`** — apenas pré-processa e reconhece; **não decide** que um valor incerto é verdadeiro; entrega resultado bruto + confiança.
- **`business/`** — funções puras e testáveis: normalização de horários, validação, detecção de dúvidas, cálculo de horas. Determinístico, independente do OCR.
- **`persistence/`** — repositórios JSON com escrita atômica e validação antes de gravar.
- **`security/`** — assinatura de arquivo, limites, nomes internos seguros, resolução segura de caminhos, pertencimento ao lote.
- **`exports/`** — openpyxl; neutraliza fórmulas e separa pendências dos confirmados.

---

## 7. Processamento em segundo plano

- Um **worker** por lote (thread/processo), sem manter a requisição HTTP aberta.
- Opções de implementação (a decidir na etapa correspondente, sem dependências extras obrigatórias): `concurrent.futures` (ThreadPool/ProcessPool) ou `BackgroundTasks` do FastAPI com executor dedicado para etapas CPU-bound.
- Progresso persistido em `lote.json` a cada imagem; consulta por `GET /api/lotes/{id}`.
- Limites de tempo por operação e controle de concorrência/memória.

---

## 8. Compatibilidade com o frontend atual

- **`POST /processar`** é mantido para a tela atual, retornando `ResultadoProcessamento` exatamente como `src/lib/api.ts` espera.
- A tela usa a **API assíncrona** (`criarLote` + `aguardarLote` + `obterResultados`/`obterDuvidas` + `corrigirRegistro` + `exportarLote`/`baixarArquivo`); as novas funções foram **adicionadas** a `src/lib/api.ts` sem remover `processarCartoes`, `resolveUrl`, `isBackendConnected` nem alterar o design.
- A seção "Planilhas" (`src/routes/index.tsx`) é preenchida por `POST /api/lotes/{id}/exportar` e o download usa `baixarArquivo` (com tratamento de erro). Lotes sem registros exportáveis mostram aviso; falhas de download aparecem no painel.
- `VITE_API_URL` continua sendo a chave de conexão; sem ela, a UI permanece no estado "Backend ainda não conectado".

---

## 9. Segurança (mapeamento às camadas)

| Camada | Controles |
|---|---|
| Entrada | formatos permitidos, assinatura real, limites, nomes internos seguros, proteção contra imagens malformadas |
| API | validação de parâmetros, CORS restrito, limites, exceções sem vazar caminhos, verificação de pertencimento ao lote |
| Processamento | erros isolados, concorrência/memória, limites de tempo, sem executar comandos com dados do usuário, conteúdo de imagem não é instrução |
| Persistência | escrita atômica, validação antes de gravar, sem duplicação, sem segredos em texto puro |
| Arquivos gerados | download só do lote correto, proteção contra travessia de diretório, neutralização de fórmulas, política de não sobrescrita |
| Privacidade | tudo local, sem telemetria, logs mínimos, LGPD |
| Dependências | `.gitignore` para `storage/`, `.env`, temporários; avaliação de dependências |

**`.gitignore` a adicionar (proposta):** `backend/storage/`, `backend/**/__pycache__/`, `.venv/`, `*.pyc`, `.env`, arquivos de dados de funcionários.

---

## 10. Dependências propostas (não instaladas)

`fastapi`, `uvicorn[standard]`, `pydantic`, `python-multipart`, `opencv-python`, `pytesseract`, `Pillow`, `openpyxl`, e `pytest`/`httpx` para testes. Requer **binário do Tesseract** instalado no sistema (fora do `pip`).

**Sem banco de dados** e sem ORM (decisão do usuário).

---

## 11. Riscos arquiteturais

- **Precisão de OCR em manuscrito** — revisão humana é parte do fluxo, não um extra.
- **Persistência JSON sem transações** — mitigada por escrita atômica e um worker por lote.
- **Concorrência sem SGBD** — limitar a um lote ativo por vez ou serializar escritas.
- **Coluna "Hora Extra" ignorada** — modelos que a possuem devem ser processados desconsiderando essa coluna (ver PRD §8, regra 10).
- **Tesseract como dependência externa** — precisa estar instalado e no PATH.

---

## 12. Próximos passos

1. Implementar `POST /processar` (etapa 9 — compatibilidade com o contrato original).
2. Testes de integração reais frontend × backend com a imagem `ALESSANY.jpg` e modelos com dias em branco.
3. Definir política de retenção/remoção de `storage/` (dados LGPD).
