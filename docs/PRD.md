# PRD — Leitor de Ponto (PontoFácil)

## 1. Informações do documento

- **Nome do produto:** PontoFácil — Leitura e conferência de folhas de ponto.
- **Versão:** 0.1.2.
- **Data da última atualização:** 2026-10-16.
- **Estado do documento:** Em evolução. Etapas 1–8 do plano (§17) implementadas no backend (docs, esqueleto FastAPI, segurança de upload, persistência JSON, OCR, parser, regras de negócio e API de lote assíncrono). Frontend preservado.
- **Responsável pela validação:** Usuário/proprietário do projeto (a definir formalmente).

> **Nota de decisão.** A persistência é feita em **arquivos JSON** no disco, **sem banco de dados**: o sistema analisa as imagens, transforma o resultado em JSON e gera o Excel. O `CONTEXT.md` foi atualizado para refletir esta decisão (antes especificava SQLite). A coluna **"Hora Extra"** de alguns modelos de folha está **fora do escopo** desta versão.

---

## 2. Visão geral

O PontoFácil resolve o problema de digitalizar folhas de ponto **manuscritas** fotografadas e transformá-las em registros estruturados e planilhas Excel. O sistema é uma ferramenta **local, gratuita e de apoio à conferência**: reconhece o que for possível por OCR, marca explicitamente o que é duvidoso e exige revisão humana antes de considerar qualquer dado como confirmado.

**Proposta de valor:** eliminar digitação manual de horários, manter rastreabilidade entre a imagem de origem e cada registro, e nunca inventar dados ausentes ou ilegíveis.

**Resultado esperado:** o usuário envia fotos (individualmente, em pasta ou em ZIP), o sistema processa o lote, apresenta os horários reconhecidos e as dúvidas, permite corrigir e então gera planilhas `.xlsx` por funcionário/período, uma planilha consolidada e uma relação de pendências.

---

## 3. Problema e objetivos

### Processo manual atual
Folhas de ponto em papel são preenchidas à mão, fotografadas e depois transcritas manualmente para planilhas. A transcrição é lenta, sujeita a erro e não mantém vínculo com a imagem original.

### Problemas
- Digitação repetitiva e propensa a erro.
- Ausência de rastreabilidade entre horário lançado e foto de origem.
- Dificuldade em lidar com campos ilegíveis, em branco ou inconsistentes.
- Diferentes layouts de folha entre funcionários/empresas.

### Objetivos mensuráveis (propostas — **não aprovados como metas contratuais**)
- Reduzir o esforço de transcrição manual de um lote (meta a medir após a primeira versão).
- Permitir processamento de lotes com mais de 100 imagens sem bloquear a interface.
- Garantir que 100% dos registros com dúvida sejam sinalizados e não exportados como confirmados.

> Métricas de desempenho e economia de tempo são **propostas** até serem medidas com dados reais.

---

## 4. Usuários e contexto de uso

- **Operador de RH/Departamento Pessoal (usuário principal):** envia as fotos, revisa os horários, corrige o que for duvidoso e baixa as planilhas.
- **Conferente/revisor:** valida correções e confirma os dados para exportação.

**Contexto:** aplicação executada localmente em um único computador (Windows no ambiente atual), sem login e sem multiusuário na primeira versão. Não há papéis/permissões a implementar sem requisito aprovado.

---

## 5. Escopo

### Incluído na primeira versão
- Upload de imagens (JPG/JPEG/PNG/WEBP), pasta e ZIP.
- Criação de lote e processamento assíncrono com progresso.
- Pré-processamento de imagem (OpenCV) e OCR local (Tesseract).
- Extração de funcionário, período (mês/ano) e registros diários (entrada, saída almoço, volta almoço e saída).
- Detecção e marcação de dúvidas.
- Revisão e correção manual dos registros.
- Cálculo de horas a partir de dados validados.
- Persistência local em **JSON** (sem SGBD).
- Geração de Excel por funcionário/período, consolidado e relação de pendências.
- Endpoint compatível com o contrato atual do frontend (`POST /processar`).

### Fora do escopo (nesta versão)
- Autenticação, login, multiusuário e perfis/permissões.
- Banco de dados hospedado, nuvem obrigatória, APIs pagas de OCR/IA.
- Aplicação de regras trabalhistas (horas extras legais, adicionais, descontos, arredondamentos) sem definição do usuário.
- Reconhecimento de assinaturas.
- Reconhecimento, processamento ou exportação da coluna **"Hora Extra"** presente em alguns modelos de folha.
- Edição/roteamento de imagens além do necessário ao OCR.

---

## 6. Requisitos funcionais

Para cada requisito: objetivo, comportamento, entrada/saída, validações, erros e critérios de aceitação.

### RF-001 — Upload em lote
- **Objetivo:** receber uma ou várias imagens, pastas ou ZIP.
- **Comportamento:** o frontend envia arquivos via `multipart/form-data`, campo `arquivos`. O backend aceita N arquivos por requisição dentro dos limites.
- **Entrada:** arquivos de imagem ou ZIP contendo imagens.
- **Saída:** confirmação de recebimento e identificação do lote.
- **Validações:** formato permitido, assinatura real do arquivo, tamanho por arquivo, quantidade e tamanho total do lote.
- **Erros:** 400 para formato/tamanho inválido; 413 para excesso; mensagem compreensível.
- **Aceitação:** imagens válidas entram no lote; inválidas são rejeitadas com motivo, sem interromper as demais.

### RF-002 — Validação de arquivos de entrada
- **Objetivo:** impedir arquivos inválidos ou maliciosos.
- **Comportamento:** verificar assinatura (magic bytes), extensão permitida e limites; gerar nome interno seguro.
- **Saída:** arquivo aceito e renomeado internamente ou rejeitado.
- **Validações:** nunca usar o nome fornecido pelo usuário como caminho de gravação.
- **Aceitação:** arquivo com extensão falsa é rejeitado; nome interno é opaco e único.

### RF-003 — Criação de lote
- **Objetivo:** agrupar um conjunto de imagens sob identificador único.
- **Comportamento:** gerar `lote_id` opaco; criar diretório `storage/lotes/{lote_id}/`.
- **Saída:** JSON do lote com estado inicial `recebido`.
- **Aceitação:** lote consultável por `lote_id`; nenhum recurso acessível sem pertencer ao lote.

### RF-004 — Processamento assíncrono e progresso
- **Objetivo:** processar >100 imagens sem bloquear a interface.
- **Comportamento:** processamento em segundo plano; estado/progresso persistido em `lote.json`; consulta via `GET /api/lotes/{id}`.
- **Saída:** progresso (`total`, `processados`, `falhas`, `revisao`), estado (`recebido`, `processando`, `concluido`, `concluido_com_pendencias`, `falhou`).
- **Erros:** falha isolada por imagem não interrompe o lote.
- **Aceitação:** interface responde durante o processamento; progresso avança; lote é retomável.

### RF-005 — OCR e extração
- **Objetivo:** reconhecer nome, período, dias e horários.
- **Comportamento:** pré-processar (OpenCV) e aplicar Tesseract; produzir resultado **bruto** e normalizado.
- **Saída:** texto bruto + campos candidatos com confiança.
- **Validações:** OCR não decide sozinho; resultado sempre passa por validação.
- **Aceitação:** valor bruto preservado para auditoria; campo incerto marcado como dúvida.

### RF-006 — Identificação de funcionário e período
- **Objetivo:** associar registros a funcionário e mês/ano.
- **Comportamento:** extrair nome/código do funcionário e período (ex.: 01/08/2026 a 31/08/2026).
- **Erros:** identificação incerta gera dúvida, não um palpite silencioso.
- **Aceitação:** registros agrupáveis por funcionário e mês/ano; incerteza sinalizada.

### RF-007 — Normalização de registros
- **Objetivo:** converter o resultado bruto em estrutura consistente.
- **Comportamento:** normalizar horários para `HH:MM`; manter valor bruto separado; associar `origem` (imagem).
- **Aceitação:** estrutura de registro válida conforme §9; ausência representada como `null`.

### RF-008 — Validação de horários e detecção de dúvidas
- **Objetivo:** validar campos e marcar incertezas.
- **Comportamento:** checar formato, intervalos plausíveis e consistência; gerar registros em `duvidas.json`.
- **Aceitação:** todo registro com campo ausente, ilegível ou inconsistente é marcado para revisão.

### RF-009 — Revisão e correção manual
- **Objetivo:** corrigir sem reprocessar todas as imagens.
- **Comportamento:** `PATCH /api/registros/{registro_id}` valida e grava a correção, distinguindo-a do valor original do OCR.
- **Saída:** registro atualizado com marca de correção manual.
- **Aceitação:** correção é distinguível do resultado original; histórico preservado.

### RF-010 — Cálculo de horas
- **Objetivo:** calcular período trabalhado com regras explícitas.
- **Comportamento:** calcular apenas com horários existentes e validados; considerar minuto e virada de dia quando a regra estiver definida.
- **Validações:** não presumir almoço; não aplicar tolerâncias/arredondamentos/regras não especificadas.
- **Aceitação:** cálculo determinístico e rastreável; pendências não entram como total confirmado.

### RF-011 — Persistência local (JSON)
- **Objetivo:** guardar lotes, registros, dúvidas, correções e arquivos gerados **sem banco de dados**.
- **Comportamento:** gravar arquivos JSON por lote (`lote.json`, `registros.json`, `duvidas.json`, `correcoes.json`) e referenciar imagens/exports.
- **Aceitação:** resultados recuperáveis após reiniciar a aplicação; sem duplicação desnecessária de imagens.

### RF-012 — Geração de planilhas Excel
- **Objetivo:** gerar `.xlsx` com openpyxl.
- **Comportamento:** gerar por funcionário/período, uma consolidada e uma relação de pendências; horários formatados e totais calculados.
- **Validações:** não exportar dúvidas como confirmadas; neutralizar textos que iniciem com `=`, `+`, `-`, `@` (injeção de fórmula).
- **Aceitação:** planilhas abrem no Excel; totais conferem com os cálculos; dúvidas separadas.

### RF-013 — Resumo do lote
- **Objetivo:** informar quantas imagens foram processadas, falharam e precisam de revisão.
- **Aceitação:** números do resumo consistentes com os JSONs do lote.

### RF-014 — Consulta de dúvidas
- **Objetivo:** listar pendências do lote.
- **Comportamento:** `GET /api/lotes/{id}/duvidas`.
- **Aceitação:** todas as dúvidas visíveis com origem e motivo.

### RF-015 — Downloads
- **Objetivo:** disponibilizar arquivos gerados.
- **Comportamento:** `GET /api/lotes/{id}/downloads` lista arquivos; download só do lote correto.
- **Validações:** bloquear travessia de diretório e caminhos arbitrários.
- **Aceitação:** só arquivos do lote solicitado são baixáveis.

### RF-016 — Compatibilidade com o contrato atual
- **Objetivo:** preservar o frontend existente.
- **Comportamento:** manter `POST {VITE_API_URL}/processar` (multipart, campo `arquivos`) retornando `ResultadoProcessamento` (`total_cartoes`, `processados`, `registros[]`, `planilhas[]`, `consolidado`).
- **Aceitação:** a tela atual funciona sem alteração de contrato.

---

## 7. Requisitos não funcionais

- **RNF-001 — Gratuidade e execução local:** apenas ferramentas gratuitas; nenhuma API paga de OCR/IA; nenhum serviço de nuvem obrigatório.
- **RNF-002 — Desempenho e limites:** processar lotes >100 imagens sem bloquear; limites configuráveis de tamanho por arquivo, quantidade por lote, tamanho total e tempo por operação.
- **RNF-003 — Segurança:** controles em 7 camadas (§12), mesmo sem login.
- **RNF-004 — Privacidade/LGPD:** imagens, registros e planilhas permanecem no computador; nenhum dado pessoal enviado a serviços externos; logs sem nomes/horários/imagens desnecessários; documentar onde os dados ficam e como removê-los.
- **RNF-005 — Confiabilidade:** um erro por imagem não derruba o lote; estados consistentes.
- **RNF-006 — Recuperação de falhas:** lote retomável por releitura dos JSONs; sem perda de correções.
- **RNF-007 — Usabilidade:** mensagens de erro compreensíveis; etapa e progresso visíveis; revisão simples.
- **RNF-008 — Manutenibilidade:** cálculos e regras em funções testáveis e independentes do OCR; separação de camadas.
- **RNF-009 — Compatibilidade de ambiente:** executar no Windows local com Python + dependências documentadas; frontend React + Vite preservado.
- **RNF-010 — Determinismo:** mesma entrada validada produz mesmo resultado; sem IA generativa para cálculos.

---

## 8. Regras de negócio

1. **Reconhecimento e normalização de horários:** formato normalizado `HH:MM`; valor bruto preservado separadamente; nunca inventar/completar horários ilegíveis.
2. **Valores ilegíveis/ausentes:** representar como `null` (nunca `00:00`); não interpretar automaticamente como folga/falta/ausência; registrar observação apenas com evidência.
3. **Cálculo de períodos trabalhados:** apenas horários existentes e validados; tratar minutos e virada de dia quando definido; rastreável.
4. **Intervalos:** não presumir existência/ausência de intervalo de almoço.
5. **Registros incompletos:** marcar para revisão; não calcular total confirmado com dados faltantes.
6. **Confirmação de correções:** correção manual distinta do OCR; registrar autor/timestamp e valor anterior.
7. **Separação confirmado × pendência:** dúvidas nunca exportadas como confirmadas.
8. **Agrupamento:** por funcionário e por mês/ano.
9. **Totais e exportação:** gerados somente após validação e cálculo; documentar a composição do total.
10. **Hora extra (fora do escopo):** a coluna "Hora Extra" não é reconhecida, processada, persistida nem exportada nesta versão. Não aplicar regras legais de hora extra ou adicionais sem definição.

> **Regras pendentes (dependem de decisão do usuário):** tolerâncias, arredondamentos, regra de intervalo padrão, tratamento de feriados/férias (ex.: anotação "Féria." na imagem de referência), critério de desempate de horários ambíguos e política de intervalo entre turnos. Não presumir respostas.

### 8.1 Regras implementadas na etapa 7

As regras abaixo foram implementadas em `backend/app/business/` (funções puras, sem OCR) na etapa 7 do plano (§17). São **conservadoras**: nenhuma presume dados ausentes, tolerância ou regra trabalhista.

- **Normalização:** apenas dígitos reais são normalizados para `HH:MM` (`8:00` → `08:00`; `08h30` → `08:30`; `08.15` → `08:15`). Letras do OCR (ex.: `O8:OO`) permanecem `None`; o valor bruto é preservado em `valor_bruto`.
- **Ausência/ilegibilidade:** cada campo ausente gera uma dúvida "Horário ausente"; cada campo com texto bruto não normalizável gera "Horário ilegível". Nunca se cria `00:00` nem se interpreta o vazio como folga/falta/ausência.
- **Status do registro:** `invalido` (horário presente em formato inválido), `pendente` (ausente/ilegível/incompleto/ordem não crescente) ou `confirmado` (os quatro horários presentes e coerentes).
- **Cálculo (`calcular_horas`):** total confirmado somente quando `entrada < saida_almoco < volta_almoco < saida`, somando dois segmentos rastreáveis (antes e depois do intervalo). Jornada com apenas `entrada`+`saida` fica **pendente** (regra de intervalo não presumida). Ordem não crescente (possível turno noturno) fica pendente, pois a virada de dia não está definida.
- **Tipos de dia reconhecidos** (`fim_de_semana`, `feriado`, `ferias`) sem marcações não geram dúvida de ausência, mas também não confirmam folga nem inventam horários; apenas registram observação.
- **Dúvidas:** produzidas como entidades `Duvida` (persistíveis em `duvidas.json`); dúvidas de cabeçalho (período/funcionário) usam `registro_id=""`.
- **Fora do escopo:** a coluna "Hora Extra" não é considerada em nenhuma validação ou cálculo.

---

## 9. Modelo de dados

Persistência em arquivos JSON por lote (sem SGBD). Entidades:

### Lote (`lote.json`)
- `lote_id`: string (opaco, seguro).
- `criado_em`: datetime ISO-8601.
- `estado`: `recebido | processando | concluido | concluido_com_pendencias | falhou`.
- `progresso`: `{ total, processados, falhas, revisao }`.
- `imagens`: lista de `Imagem`.
- `arquivos_gerados`: lista de `ArquivoGerado`.

### Imagem
- `imagem_id`: string.
- `nome_interno`: string (gerado pelo sistema).
- `nome_original`: string (apenas exibição).
- `caminho`: caminho relativo ao storage do lote.
- `status`: `ok | falha | ignorada`.
- `erro`: string | null.

### Funcionário
- `funcionario_id`: string.
- `nome`: string | null.
- `codigo`: string | null (ex.: "007").
- `empresa`: string | null.
- `departamento`, `funcao`: string | null.

### Período
- `mes`: int (1–12) | null.
- `ano`: int | null.

### RegistroDiario
- `registro_id`: string.
- `dia`: int (1–31) | null.
- `dia_semana`: string | null.
- `entrada`, `saida_almoco`, `volta_almoco`, `saida`: `HH:MM` | null.
- `tipo_dia`: `util | fim_de_semana | feriado | ferias | null`.
- `status_validacao`: `pendente | confirmado | corrigido | invalido`.
- `confianca`: float 0..1 | null.
- `valor_bruto`: objeto com textos originais reconhecidos.
- `observacao`: string | null.
- `origem`: string (imagem_id).
- `correcao`: `Correcao | null`.

### Dúvida
- `duvida_id`, `registro_id`, `campo`, `motivo`, `origem`.

### Correção
- `corrigido_em`, `campo`, `valor_anterior`, `valor_novo`, `autor` (local) | null.

### ArquivoGerado
- `arquivo_id`, `nome`, `tipo` (`funcionario | consolidado | pendencias`), `funcionario` | null, `referencia` | null, `caminho`, `gerado_em`.

**Nulabilidade:** todos os campos de horário são nulos quando ausentes/ilegíveis. **Validação:** horários casam `^([01]\d|2[0-3]):[0-5]\d$`; `dia` em 1..31; `mes` em 1..12.

---

## 10. Contratos da API

Base: `{VITE_API_URL}`. JSON UTF-8. CORS restrito a origens locais de desenvolvimento.

| Método | Rota | Descrição |
|---|---|---|
| POST | `/processar` | **Compatibilidade atual.** multipart, campo `arquivos`. Resposta `ResultadoProcessamento`. |
| POST | `/api/lotes` | Cria lote e dispara processamento assíncrono. Resposta `{ lote_id, estado }`. |
| GET | `/api/lotes/{lote_id}` | Estado e progresso do lote. |
| GET | `/api/lotes/{lote_id}/resultados` | Registros extraídos. |
| PATCH | `/api/registros/{registro_id}` | Corrige um registro (validação). |
| GET | `/api/lotes/{lote_id}/duvidas` | Pendências. |
| POST | `/api/lotes/{lote_id}/exportar` | Gera exportações. |
| GET | `/api/lotes/{lote_id}/downloads` | Lista arquivos disponíveis. |

> **Implementado na etapa 8** (`backend/app/api/`): `POST /api/lotes`, `GET /api/lotes/{lote_id}`, `GET /api/lotes/{lote_id}/resultados`, `GET /api/lotes/{lote_id}/duvidas` e `PATCH /api/registros/{registro_id}`. O processamento roda em segundo plano (um worker por lote) e o progresso é persistido em `lote.json`. `POST /processar` (compatibilidade) e exportação/downloads ficam para as etapas 9–10. ZIP/pasta ainda não são aceitos pela API (o frontend expande pastas).

**Códigos de erro:** 400 (validação), 404 (recurso inexistente/lote incorreto), 413 (excesso), 422 (payload inválido), 500 (erro interno sem vazar detalhes/caminhos).

**Estados do lote:** `recebido`, `processando`, `concluido`, `concluido_com_pendencias`, `falhou`.

`ResultadoProcessamento` (compatível com `src/lib/api.ts`):
```
{
  "total_cartoes": int,
  "processados": int,
  "registros": [ { id, funcionario, data, dia_semana,
                   entrada, saida_almoco, volta_almoco, saida,
                   confianca, revisar } ],
  "planilhas": [ { arquivo, funcionario, referencia, status, url } ],
  "consolidado": { arquivo, funcionario, referencia, status, url } | null
}
```

---

## 11. Fluxos principais

1. **Upload:** seleção (fotos/pasta/ZIP) → envio multipart → validação de arquivos → criação do lote.
2. **Processamento:** enfileiramento → pré-processamento OpenCV → OCR Tesseract → normalização → validação/regras → persistência JSON de progresso e resultados.
3. **Revisão:** UI lista registros e dúvidas → usuário corrige → `PATCH` valida e grava correção.
4. **Confirmação:** registros revisados passam a `confirmado`.
5. **Exportação:** cálculo → openpyxl → arquivos por funcionário, consolidado e pendências → downloads.

---

## 12. Segurança e privacidade

- **Arquivos de entrada:** formatos permitidos, assinatura real, limites de tamanho/quantidade/total, nomes internos seguros, proteção contra imagens malformadas.
- **API:** validação de todos os parâmetros, CORS restrito, limites de requisição, exceções sem vazar caminhos/credenciais, identificadores de lote verificados.
- **Processamento:** erros isolados por arquivo, controle de concorrência/memória, limites de tempo, sem execução de comandos construídos com dados do usuário, conteúdo de imagem nunca tratado como instrução.
- **Persistência JSON:** escrita atômica (arquivo temporário + rename), validação antes de gravar, relacionamentos consistentes, sem duplicar imagens.
- **Arquivos gerados:** download só do lote correto, proteção contra travessia de diretório, neutralização de fórmulas (`=`, `+`, `-`, `@`), política explícita de não sobrescrita.
- **Privacidade:** tudo local; sem telemetria; logs sem dados pessoais desnecessários; documentar local e remoção dos dados; tratamento LGPD.
- **Dependências e segredos:** sem versionar segredos/`.env`; `.gitignore` para `storage/`, arquivos JSON de dados locais, dados de funcionários e temporários.

> **Não afirmar segurança sem testes.** Nenhuma verificação de segurança foi executada ainda.

---

## 13. Critérios de aceitação

- **RF-001/002:** arquivos válidos aceitos, inválidos rejeitados com motivo; nome interno seguro.
- **RF-003/004:** lote criado e consultável; progresso avança sem bloquear a UI; >100 imagens suportadas.
- **RF-005/006/007:** texto bruto preservado; estrutura normalizada válida; funcionário/período agrupáveis.
- **RF-008/009:** dúvidas marcadas; correção distinguível do OCR.
- **RF-010:** cálculos determinísticos e testados independentemente do OCR.
- **RF-011:** resultados recuperáveis após reinício, sem SGBD.
- **RF-012/013/014/015:** planilhas abrem e conferem; dúvidas separadas; downloads restritos ao lote.
- **RF-016:** tela atual funciona sem mudança de contrato.

---

## 14. Estratégia de testes

- **Unitários:** validação de horários; cálculo de horas/intervalos; campos nulos; registros incompletos; datas/limites de mês; correções manuais; neutralização de fórmulas.
- **Integração:** criação e progresso de lote; persistência/recuperação JSON; geração e releitura de planilhas; falha isolada em lote; contrato `/processar`.
- **Segurança:** caminhos inválidos/travessia de diretório; validação de arquivos e limites de upload; verificação de pertencimento ao lote.
- **Imagens reais:** lote representativo a partir da imagem `ALESSANY.jpg` e de outros modelos (incluindo dias em branco). Modelos com coluna "Hora Extra" devem ser processados ignorando essa coluna.
- **Regra:** não considerar concluído apenas por escrever código; executar testes e relatar o que foi/não foi verificado. Não criar resultados fictícios.

---

## 15. Restrições e dependências

**Aprovadas:** Python, FastAPI, Pydantic, processamento em segundo plano, **persistência em JSON (sem SGBD)**, openpyxl, OpenCV, Tesseract (pytesseract), armazenamento em disco local. Frontend React + Vite (TanStack Start) preservado.

**Dependências propostas (apenas documentadas, não instaladas):** `fastapi`, `uvicorn`, `pydantic`, `python-multipart`, `opencv-python`, `pytesseract`, `Pillow`, `openpyxl`. Requer binário do Tesseract instalado no sistema.

**Proibido:** APIs pagas de OCR/IA, nuvens obrigatórias, banco hospedado, hospedagem paga.

**Limitações conhecidas:** escrita manual tem precisão OCR limitada; layouts variam entre funcionários/empresas; revisão humana é obrigatória.

---

## 16. Riscos e decisões pendentes

### Decisões confirmadas
- Preservar o frontend Lovable (TanStack Start + React + Vite).
- OCR inicial: Tesseract + OpenCV, com revisão humana.
- Modelo de registro **flexível**, com marcações variáveis por dia (entrada, saída almoço, volta almoço, saída).
- API mantém `/processar` (compatibilidade) e adiciona `/api/lotes` (assíncrono).
- **Sem banco de dados:** persistência em JSON, então Excel.
- Coluna **"Hora Extra"** fora do escopo (não reconhecida, processada, persistida ou exportada).

### Documentos atualizados
- `CONTEXT.md`, `docs/PRD.md` e `docs/ARQUITETURA.md` foram atualizados para refletir a persistência em JSON (a especificação anterior de SQLite foi substituída) e a remoção da coluna "Hora Extra".

### Hipóteses
- Windows como ambiente principal; execução local de um só usuário.
- As quatro marcações (entrada, saída almoço, volta almoço, saída) são comuns, mas não universais.

### Perguntas em aberto
- Regra de intervalo padrão e tolerâncias (se houver).
- Tratamento formal de feriados/férias e fins de semana (ex.: "Féria." na imagem).
- Critério de desempate para horários ambíguos (ex.: `06` vs `08`).
- Formato/estrutura exata esperada das planilhas.
- Onde armazenar `storage/` e política de retenção/remoção.

---

## 17. Plano de implementação

Etapas pequenas, ordenadas por dependência. **Concluídas: 1–8.**

1. ✅ **Documentação e contratos** — PRD + ARQUITETURA.
2. ✅ **Esqueleto do backend FastAPI** — app, config, CORS, healthcheck, `requirements.txt`.
3. ✅ **Segurança de upload** — validação de assinatura/limites, nomes internos, camada `storage/`.
4. ✅ **Persistência JSON** — repositórios de lote/registro/dúvida/correção, escrita atômica, recuperação.
5. ✅ **Pipeline de imagem + OCR (Tesseract)** — pré-processamento e extração bruta.
6. ✅ **Parser da folha** — funcionário, período e dias (coluna "Hora Extra" ignorada).
7. ✅ **Regras de negócio** — normalização, validação, detecção de dúvidas, cálculo de horas (testáveis), em `backend/app/business/` (ver §8.1).
8. ✅ **API de lote assíncrono + progresso** — worker em segundo plano (`app/services/`) e endpoints (`app/api/`, ver §10).
9. **Compatibilidade `/processar`** — adaptar ao contrato atual.
10. **Exportação openpyxl** — por funcionário, consolidada, pendências.
11. **Revisão/correção** — `PATCH` com validação e marcação de correção.
12. **Integração do frontend** — evoluir `src/lib/api.ts` e a UI de progresso sem quebrar o design.
13. **Testes** — unitários, integração, segurança e imagens reais.

**Definição de concluído:** atende ao PRD, preserva o frontend, possui validações/testes executados, não inventa dados, custo zero e memória por prompt registrada.
