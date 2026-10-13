# AGENTS.md — Backend da Automação de Cartões de Ponto

## 1. Objetivo do projeto

Desenvolver o backend local em Python para uma aplicação que automatiza a leitura de cartões de ponto manuscritos de funcionários e gera planilhas Excel por funcionário e mês.

O sistema deve funcionar localmente no computador do usuário. O Claude Code, OpenCode e outros agentes de desenvolvimento são ferramentas para construir/manter o software; não devem ser dependências necessárias para a execução diária da aplicação.

Não utilizar serviços pagos de IA generativa, APIs remotas de OCR ou banco de dados nesta versão.

## 2. Antes de implementar

1. Inspecione a estrutura atual do repositório e leia os arquivos existentes, especialmente `CLAUDE.md`, `gerar_planilha.py`, os arquivos em `.claude/agents/` e `.claude/commands/`, caso existam.
2. Preserve o trabalho já existente. Não sobrescreva nem remova arquivos úteis sem necessidade.
3. Verifique se o frontend do Lovable já foi exportado e identifique como está organizado. Não reescreva o frontend.
4. Se o modelo real de planilha Excel da empresa estiver disponível no repositório, examine-o antes de alterar a geração. Se não estiver disponível, mantenha a estrutura definida neste documento e registre a limitação.
5. Implemente em etapas pequenas, testando cada etapa. Não declare que uma funcionalidade está concluída se não foi implementada e testada.

## 3. Stack desejada

- Python 3.11 ou versão compatível com as bibliotecas selecionadas.
- FastAPI para a API HTTP local.
- Uvicorn para executar a API.
- Pydantic para validar os dados.
- `python-multipart` para uploads.
- Pillow e OpenCV para processamento de imagens.
- `openpyxl` para gerar arquivos Excel.
- `pytest` para testes.
- Biblioteca padrão `zipfile` para arquivos ZIP.
- Para OCR, avaliar primeiro a adequação de um mecanismo local e sem cobrança por chamada. Considerar Tesseract com `pytesseract`, PaddleOCR ou TrOCR com `transformers`/`torch`, conforme compatibilidade e resultados de testes.
- Não instalar vários mecanismos pesados de OCR sem justificativa. Documentar os requisitos de instalação externos, se houver, e escolher a opção mais adequada depois de testar exemplos reais.

O OCR deve operar localmente depois da instalação e obtenção dos modelos necessários. Não enviar imagens para serviços externos.

## 4. Estrutura de diretórios

Preservar as pastas existentes e utilizar, sempre que possível, esta organização:

```text
frontend/                 # Interface do Lovable, se já exportada
backend/
  __init__.py
  main.py                 # FastAPI e endpoints
  config.py               # Configurações e caminhos
  schemas.py              # Modelos Pydantic
  arquivos.py             # Upload, validação e extração de ZIP
  tratamento_imagem.py    # Rotação, contraste, recortes
  leitor_imagem.py        # OCR local
  estrutura_cartao.py     # Associação de texto/células aos campos do cartão
  validador.py            # Validação e identificação de dúvidas
  processador.py          # Coordenação do fluxo
  gerar_planilha.py       # Geração das planilhas
fotos/                    # Fotos originais ou recebidas
json/                     # JSONs extraídos
saida/                    # Planilhas Excel geradas
temporarios/              # Arquivos temporários
testes/
requirements.txt
README.md
AGENTS.md
CLAUDE.md                 # Preservar se já existir
```

Adapte os nomes apenas quando a estrutura atual exigir. Não crie duplicatas desnecessárias de scripts existentes; reaproveite ou refatore `gerar_planilha.py` com cuidado.

## 5. Fluxo funcional obrigatório

1. A interface envia uma ou mais imagens, um ZIP ou arquivos selecionados.
2. A API valida extensão, tamanho e conteúdo dos arquivos.
3. O sistema salva os arquivos de maneira segura e extrai ZIPs sem permitir path traversal ou gravação fora das pastas autorizadas.
4. O sistema identifica os cartões e executa o processamento de imagem e OCR local.
5. O sistema tenta identificar nome do funcionário, mês, ano, dia e horários.
6. Se nome, mês ou ano não puderem ser identificados com segurança, o cartão deve ficar pendente para revisão; nunca inventar esses dados.
7. Para cada dia, reconhecer:
   - `entrada`
   - `saida_almoco`
   - `volta_almoco`
   - `saida_final`
8. Normalizar horários reconhecidos para `HH:MM` em formato 24 horas. Horários não reconhecidos devem ser `null`.
9. Não deduzir nem inventar horários. Quando houver ambiguidade, registrar uma dúvida e solicitar revisão humana.
10. Salvar os dados estruturados em JSON na pasta `json/`.
11. Após revisão, gerar um Excel por funcionário, ano e mês em `saida/`.
12. A API deve expor o progresso, as dúvidas, a possibilidade de corrigir campos e os links/rotas de download.
13. Os arquivos originais devem ser preservados, salvo se o usuário explicitamente solicitar remoção.

## 6. Formato de JSON

Manter compatibilidade com o formato já estabelecido no projeto. Usar como referência:

```json
{
  "arquivo": "foto01.jpg",
  "funcionario": "Nome do funcionário",
  "mes": 9,
  "ano": 2026,
  "registros": [
    {
      "dia": 1,
      "entrada": "08:00",
      "saida_almoco": "12:00",
      "volta_almoco": "13:00",
      "saida_final": "17:30",
      "confianca": "alta",
      "observacao": "",
      "duvidas": []
    }
  ]
}
```

Regras:
- `confianca` deve aceitar `alta`, `media` ou `baixa`.
- `duvidas` pode listar os nomes dos campos que precisam de revisão.
- `observacao` deve explicar a dúvida sem inventar uma resposta.
- Se adicionar campos ao formato, manter compatibilidade com os JSONs existentes e documentar a mudança.
- Validar mês (1–12), ano, dias válidos do mês e formato dos horários.
- Um dia sem registro deve ter os quatro horários como `null`; preservar observações como `FOLGA`, `FALTA` ou `ATESTADO` quando estiverem claramente escritas.
- Não assumir que todo domingo é folga nem inferir ausência a partir de uma célula vazia.

## 7. Regras de cálculo e Excel

A planilha final deve usar as colunas:

- A: Dia/data
- B: Dia da semana
- C: C.H. (carga horária diária, calculada por fórmula)
- D: Entrada do 1º turno
- E: Saída para almoço
- F: Volta do almoço
- G: Saída final do 2º turno

A carga horária diária é a soma dos dois turnos:
`(E - D) + (G - F)`.

Usar fórmulas do Excel, não calcular a carga horária no OCR. As durações devem usar formato `[h]:mm`. As células de horário devem usar formato `hh:mm`.

As fórmulas precisam evitar exibir um total enganoso quando faltarem horários necessários. Tratar, conforme aplicável:
- quatro horários presentes: calcular os dois turnos;
- somente entrada e saída, sem almoço: não presumir automaticamente que esse padrão é válido para a empresa; documentar a regra ou deixá-la configurável;
- horários incompletos: deixar o resultado em branco ou marcar para revisão;
- jornadas que cruzem a meia-noite: só implementar cálculo especial se isso fizer parte das regras confirmadas.

Realçar campos de confiança `media` e `baixa` com cores diferentes e adicionar comentário contendo a observação, quando houver. Gerar um total mensal por fórmula. Não sobrescrever arquivos de saída silenciosamente; evitar colisões de nomes e informar o que foi gerado.

## 8. Endpoints mínimos sugeridos

Implementar e documentar endpoints REST equivalentes a estes. Os nomes podem ser ajustados para se integrar ao frontend existente:

- `GET /api/health` — verificar se o backend está disponível.
- `POST /api/processamentos` — receber imagens e/ou ZIP e iniciar processamento.
- `GET /api/processamentos/{id}` — consultar status e progresso.
- `GET /api/processamentos/{id}/duvidas` — listar campos pendentes de revisão.
- `PATCH /api/registros/{id}` ou endpoint equivalente — salvar correção manual validada.
- `POST /api/processamentos/{id}/gerar-excel` — gerar as planilhas após validação/revisão.
- `GET /api/processamentos/{id}/download` — baixar resultado compactado.
- Endpoint adicional para baixar planilha individual, se necessário.

Os endpoints devem refletir o comportamento real implementado. Não devolver progresso fictício nem sucesso antes da conclusão da tarefa.

Como esta versão não utiliza banco de dados, persistir JSONs e resultados no disco. Se o estado dos trabalhos ficar em memória, documentar que reiniciar o backend pode apagar o estado transitório, embora os arquivos persistidos permaneçam.

## 9. Integração com frontend

- Não recriar nem redesenhar o frontend.
- Inspecionar as chamadas e os componentes já existentes e ajustar a API para encaixar-se neles quando viável.
- Se o frontend ainda não existir, documentar o contrato dos endpoints e exemplos de requisição/resposta.
- Configurar CORS somente para a origem local necessária, sem liberar origens indiscriminadamente.
- Manter a API e o frontend executáveis localmente.
- Mostrar erros compreensíveis para upload inválido, backend indisponível, OCR sem resultado, campos pendentes e falha ao gerar Excel.

## 10. Segurança e confiabilidade

- Aceitar apenas formatos de imagem previstos e ZIPs válidos.
- Limitar tamanho de arquivos e número de arquivos por lote, com valores configuráveis.
- Prevenir path traversal na extração de ZIP.
- Gerar nomes seguros para arquivos salvos.
- Não executar arquivos enviados.
- Não expor caminhos arbitrários do sistema nos endpoints.
- Não registrar dados pessoais desnecessários nos logs.
- Manter o processamento local; não enviar fotos para serviços externos.
- Não usar reconhecimento facial: não é necessário para este projeto.
- Tratar dados de funcionários como informações pessoais e preservar os arquivos com cuidado.

## 11. Testes obrigatórios

Criar testes automatizados para:
- validação de JSON e horários;
- datas válidas e inválidas;
- dias sem registros;
- campos nulos e confiança baixa;
- fórmulas e colunas do Excel;
- agrupamento por funcionário/mês/ano;
- ZIP válido, ZIP inválido e tentativa de path traversal;
- extensões não permitidas;
- endpoint de saúde e principais endpoints da API;
- correção manual de um campo e regeneração do Excel.

Não afirmar que o OCR lê com precisão os cartões reais sem testar imagens reais. Se não houver imagens de exemplo no repositório, criar testes de unidade com dados artificiais e registrar claramente que a precisão do OCR ainda precisa ser validada com cartões reais.

## 12. Entrega esperada

Ao concluir:
1. Implementar o backend funcional e a integração necessária com o frontend existente.
2. Criar ou atualizar `requirements.txt`.
3. Atualizar `README.md` com instalação, configuração, execução, endpoints, localização dos arquivos e limitações do OCR.
4. Fornecer comandos exatos para criar/ativar ambiente virtual, instalar dependências e iniciar o backend no sistema operacional detectado.
5. Executar os testes disponíveis e corrigir falhas relacionadas às mudanças.
6. Listar arquivos criados/alterados e testes executados.
7. Identificar explicitamente o que não foi possível testar, especialmente reconhecimento manuscrito sem fotos reais.
8. Não fazer refatorações fora do escopo e não remover arquivos existentes sem justificativa.

## 13. Princípio central

A prioridade é preservar a fidelidade dos cartões. Nunca inventar horários, nomes, meses, anos ou observações. Quando o sistema não souber, deve sinalizar a dúvida para uma pessoa revisar.
