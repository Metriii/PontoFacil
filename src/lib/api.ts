// Integração com a API Python + FastAPI. Configure VITE_API_URL para sobrescrever.
/** URL padrão do backend local, usada quando VITE_API_URL não está definida. */
export const DEFAULT_API_URL = "http://127.0.0.1:8000";

function envApiUrl(): string | undefined {
  return (import.meta.env["VITE_API_URL"] as string | undefined)?.replace(/\/$/, "") || undefined;
}

export const API_URL: string = envApiUrl() ?? DEFAULT_API_URL;

/** URL base da API resolvida em tempo de chamada (facilita testes). */
function apiBase(): string {
  return envApiUrl() ?? DEFAULT_API_URL;
}

export const isBackendConnected = () => Boolean(apiBase());

export type Registro = {
  id: string;
  funcionario: string | null;
  data: string | null;
  dia_semana: string | null;
  entrada: string | null;
  saida_almoco: string | null;
  volta_almoco: string | null;
  saida: string | null;
  confianca: number | null; // 0..1
  revisar?: boolean;
};

export type Planilha = {
  arquivo: string;
  funcionario: string | null;
  referencia: string | null;
  status: string;
  url: string;
};

export type ResultadoProcessamento = {
  total_cartoes: number;
  processados: number;
  registros: Registro[];
  planilhas: Planilha[];
  consolidado?: Planilha | null;
};

export function resolveUrl(url: string) {
  const base = apiBase();
  return /^https?:\/\//.test(url) ? url : `${base}${url.startsWith("/") ? "" : "/"}${url}`;
}

// --- Lote assíncrono (etapa 8/9 do backend) ---------------------------------

export type LoteCriado = { lote_id: string; estado: string };

export type ProgressoLote = {
  total: number;
  processados: number;
  falhas: number;
  revisao: number;
};

export type ImagemLote = {
  imagem_id: string;
  nome_original: string;
  status: string;
  erro: string | null;
};

export type ArquivoGerado = {
  arquivo_id: string;
  nome: string;
  tipo: string;
  funcionario: string | null;
  referencia: string | null;
  gerado_em: string;
};

export type LoteStatus = {
  lote_id: string;
  criado_em: string;
  estado: string;
  progresso: ProgressoLote;
  imagens: ImagemLote[];
  arquivos_gerados: ArquivoGerado[];
};

export type CampoHorario = "entrada" | "saida_almoco" | "volta_almoco" | "saida";

export type FuncionarioAPI = {
  funcionario_id: string;
  nome: string | null;
  codigo: string | null;
  empresa: string | null;
  departamento: string | null;
  funcao: string | null;
};

export type CorrecaoAPI = {
  correcao_id: string;
  campo: string;
  valor_anterior: string | null;
  valor_novo: string | null;
  corrigido_em: string;
  autor: string | null;
};

export type RegistroAPI = {
  registro_id: string;
  dia: number | null;
  dia_semana: string | null;
  entrada: string | null;
  saida_almoco: string | null;
  volta_almoco: string | null;
  saida: string | null;
  tipo_dia: string | null;
  status_validacao: string;
  confianca: number | null;
  observacao: string | null;
  origem: string | null;
  correcao: CorrecaoAPI | null;
};

export type FichaAPI = {
  funcionario: FuncionarioAPI;
  mes: number | null;
  ano: number | null;
  registros: RegistroAPI[];
};

export type ResultadosLote = { lote_id: string; fichas: FichaAPI[] };

export type Duvida = {
  duvida_id: string;
  registro_id: string;
  campo: string;
  motivo: string;
  origem: string | null;
};

/** Estados terminais do lote (não muda mais o progresso). */
export const ESTADOS_FINAIS = ["concluido", "concluido_com_pendencias", "falhou"] as const;
export const loteFinalizado = (estado: string) =>
  (ESTADOS_FINAIS as readonly string[]).includes(estado);

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const base = apiBase();
  if (!base) throw new Error("Backend não conectado.");
  let resp: Response;
  try {
    resp = await fetch(`${base}${path}`, init);
  } catch {
    throw new Error("Não foi possível conectar à API.");
  }
  if (!resp.ok) {
    let msg = `Erro da API (${resp.status}).`;
    try {
      const body = (await resp.json()) as { detail?: unknown };
      if (typeof body.detail === "string" && body.detail) msg = body.detail;
    } catch {
      /* corpo não-JSON: mantém a mensagem padrão */
    }
    throw new Error(msg);
  }
  return (await resp.json()) as T;
}

/** Cria um lote enviando os arquivos (multipart, campo "arquivos"). */
export function criarLote(
  files: { file: File; path: string }[],
  onUploadProgress: (pct: number) => void,
): Promise<LoteCriado> {
  return new Promise((resolve, reject) => {
    const base = apiBase();
    if (!base) return reject(new Error("Backend não conectado."));
    const fd = new FormData();
    files.forEach(({ file, path }) => fd.append("arquivos", file, path));
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${base}/api/lotes`);
    xhr.upload.onprogress = (e) =>
      e.lengthComputable && onUploadProgress(Math.round((e.loaded / e.total) * 100));
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as LoteCriado);
        } catch {
          reject(new Error("Resposta inválida da API."));
        }
      } else {
        let msg = `Erro da API (${xhr.status}).`;
        try {
          const b = JSON.parse(xhr.responseText) as { detail?: unknown };
          if (typeof b.detail === "string" && b.detail) msg = b.detail;
        } catch {
          /* mantém padrão */
        }
        reject(new Error(msg));
      }
    };
    xhr.onerror = () => reject(new Error("Não foi possível conectar à API."));
    xhr.send(fd);
  });
}

export const obterLote = (loteId: string) =>
  jsonFetch<LoteStatus>(`/api/lotes/${encodeURIComponent(loteId)}`);
export const obterResultados = (loteId: string) =>
  jsonFetch<ResultadosLote>(`/api/lotes/${encodeURIComponent(loteId)}/resultados`);
export const obterDuvidas = (loteId: string) =>
  jsonFetch<Duvida[]>(`/api/lotes/${encodeURIComponent(loteId)}/duvidas`);

// --- Exportação e downloads (etapas 10/11 do backend) ----------------------

export type ExportacaoLote = {
  lote_id: string;
  planilhas: Planilha[];
  consolidado: Planilha | null;
  total_registros: number;
};

/** Gera (ou regenera) as planilhas do lote, retornando os arquivos disponíveis. */
export const exportarLote = (loteId: string) =>
  jsonFetch<ExportacaoLote>(`/api/lotes/${encodeURIComponent(loteId)}/exportar`, {
    method: "POST",
  });

/** Lista os arquivos gerados do lote. */
export const listarDownloads = (loteId: string) =>
  jsonFetch<Planilha[]>(`/api/lotes/${encodeURIComponent(loteId)}/downloads`);

/** Baixa uma planilha gerada, tratando erros de rede e de resposta da API. */
export async function baixarArquivo(url: string): Promise<Blob> {
  const base = apiBase();
  if (!base) throw new Error("Backend não conectado.");
  const alvo = /^https?:\/\//.test(url) ? url : `${base}${url.startsWith("/") ? "" : "/"}${url}`;
  let resp: Response;
  try {
    resp = await fetch(alvo);
  } catch {
    throw new Error("Não foi possível baixar a planilha. Verifique a conexão com a API.");
  }
  if (!resp.ok) {
    let msg = `Erro ao baixar a planilha (${resp.status}).`;
    try {
      const body = (await resp.json()) as { detail?: unknown };
      if (typeof body.detail === "string" && body.detail) msg = body.detail;
    } catch {
      /* corpo não-JSON: mantém a mensagem padrão */
    }
    throw new Error(msg);
  }
  return resp.blob();
}

/** Corrige um horário de um registro, validado no backend (distingue do OCR). */
export function corrigirRegistro(
  registroId: string,
  campo: CampoHorario,
  valor: string | null,
): Promise<RegistroAPI> {
  return jsonFetch<RegistroAPI>(`/api/registros/${encodeURIComponent(registroId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ campo, valor }),
  });
}

/** Consulta o lote a cada `intervaloMs` até atingir um estado terminal. */
export async function aguardarLote(
  loteId: string,
  onProgresso: (status: LoteStatus) => void,
  intervaloMs = 1200,
): Promise<LoteStatus> {
  for (;;) {
    const status = await obterLote(loteId);
    onProgresso(status);
    if (loteFinalizado(status.estado)) return status;
    await new Promise((r) => setTimeout(r, intervaloMs));
  }
}

const STATUS_REVISAO = ["pendente", "invalido"];

function formatarData(dia: number | null, mes: number | null, ano: number | null): string | null {
  if (dia == null) return null;
  const dd = String(dia).padStart(2, "0");
  const mm = mes != null ? String(mes).padStart(2, "0") : "--";
  const aaaa = ano != null ? String(ano) : "----";
  return `${dd}/${mm}/${aaaa}`;
}

/**
 * Converte as fichas/registros da API para o formato exibido pela tela atual,
 * marcando para revisão os registros pendentes/inválidos ou com dúvida.
 */
export function paraRegistros(resultados: ResultadosLote, duvidas: Duvida[] = []): Registro[] {
  const comDuvida = new Set(duvidas.map((d) => d.registro_id).filter(Boolean));
  const out: Registro[] = [];
  for (const ficha of resultados.fichas) {
    const funcionario = ficha.funcionario.nome ?? ficha.funcionario.codigo ?? null;
    for (const r of ficha.registros) {
      out.push({
        id: r.registro_id,
        funcionario,
        data: formatarData(r.dia, ficha.mes, ficha.ano),
        dia_semana: r.dia_semana,
        entrada: r.entrada,
        saida_almoco: r.saida_almoco,
        volta_almoco: r.volta_almoco,
        saida: r.saida,
        confianca: r.confianca,
        revisar: STATUS_REVISAO.includes(r.status_validacao) || comDuvida.has(r.registro_id),
      });
    }
  }
  return out;
}

/** Envia arquivos para POST {API_URL}/processar (multipart, campo "arquivos"). */
export function processarCartoes(
  files: { file: File; path: string }[],
  onUploadProgress: (pct: number) => void,
): Promise<ResultadoProcessamento> {
  return new Promise((resolve, reject) => {
    const base = apiBase();
    if (!base) return reject(new Error("Backend não conectado."));
    const fd = new FormData();
    files.forEach(({ file, path }) => fd.append("arquivos", file, path));
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${base}/processar`);
    xhr.upload.onprogress = (e) =>
      e.lengthComputable && onUploadProgress(Math.round((e.loaded / e.total) * 100));
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText));
        } catch {
          reject(new Error("Resposta inválida da API."));
        }
      } else reject(new Error(`Erro da API (${xhr.status}).`));
    };
    xhr.onerror = () => reject(new Error("Não foi possível conectar à API."));
    xhr.send(fd);
  });
}
