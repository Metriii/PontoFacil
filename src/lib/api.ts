// Integração com a API Python + FastAPI. Configure VITE_API_URL no ambiente.
export const API_URL: string | undefined = (import.meta.env["VITE_API_URL"] as string | undefined)?.replace(/\/$/, "") || undefined;
export const isBackendConnected = () => Boolean(API_URL);

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

export type ProcessamentoStatus = {
  id: string;
  status: "processando" | "concluido" | "erro";
  progresso: { atual: number; total: number };
  erro: string | null;
  resultado: ResultadoProcessamento | null;
};

export type Duvida = {
  registro_id: string;
  campo: string;
  motivo: string;
  valor_atual: string | null;
};

export function resolveUrl(url: string) {
  return /^https?:\/\//.test(url) ? url : `${API_URL}${url.startsWith("/") ? "" : "/"}${url}`;
}

async function apiGet<T>(url: string): Promise<T> {
  if (!API_URL) throw new Error("Backend não conectado.");
  const resp = await fetch(resolveUrl(url));
  if (!resp.ok) throw new Error(`Erro da API (${resp.status}).`);
  return resp.json() as Promise<T>;
}

async function apiPatch<T>(url: string, body: unknown): Promise<T> {
  if (!API_URL) throw new Error("Backend não conectado.");
  const resp = await fetch(resolveUrl(url), {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}));
    throw new Error(data.erro || `Erro da API (${resp.status}).`);
  }
  return resp.json() as Promise<T>;
}

export async function consultarProcessamento(id: string): Promise<ProcessamentoStatus> {
  return apiGet<ProcessamentoStatus>(`/api/processamentos/${id}`);
}

export async function corrigirRegistro(id: string, campo: string, valor: string | null): Promise<void> {
  await apiPatch(`/api/registros/${id}`, { campo, valor });
}

export async function listarDuvidas(id: string): Promise<Duvida[]> {
  const data = await apiGet<{ duvidas: Duvida[] }>(`/api/processamentos/${id}/duvidas`);
  return data.duvidas;
}

export async function gerarExcel(id: string): Promise<{ planilhas: Planilha[]; consolidado: Planilha | null }> {
  if (!API_URL) throw new Error("Backend não conectado.");
  const resp = await fetch(resolveUrl(`/api/processamentos/${id}/gerar-excel`), { method: "POST" });
  if (!resp.ok) {
    const data = await resp.json().catch(() => ({}));
    throw new Error(data.erro || `Erro da API (${resp.status}).`);
  }
  return resp.json();
}

export async function baixarResultado(id: string): Promise<Blob> {
  if (!API_URL) throw new Error("Backend não conectado.");
  const resp = await fetch(resolveUrl(`/api/processamentos/${id}/download`));
  if (!resp.ok) throw new Error(`Erro da API (${resp.status}).`);
  return resp.blob();
}

/** Envia arquivos para POST {API_URL}/processar (multipart, campo "arquivos"). */
export function processarCartoes(
  files: { file: File; path: string }[],
  onUploadProgress: (pct: number) => void,
): Promise<ResultadoProcessamento> {
  return new Promise((resolve, reject) => {
    if (!API_URL) return reject(new Error("Backend não conectado."));
    const fd = new FormData();
    files.forEach(({ file, path }) => fd.append("arquivos", file, path));
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}/processar`);
    xhr.upload.onprogress = (e) => e.lengthComputable && onUploadProgress(Math.round((e.loaded / e.total) * 100));
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText);
          if (data.id && data.status === "processando") {
            const pid = data.id;
            const poll = async () => {
              try {
                const status = await consultarProcessamento(pid);
                if (status.status === "concluido" && status.resultado) {
                  resolve(status.resultado);
                } else if (status.status === "erro") {
                  reject(new Error(status.erro || "Erro no processamento."));
                } else {
                  setTimeout(poll, 500);
                }
              } catch (e) {
                reject(e instanceof Error ? e : new Error("Erro ao consultar processamento."));
              }
            };
            poll();
          } else {
            resolve(data as ResultadoProcessamento);
          }
        } catch { reject(new Error("Resposta inválida da API.")); }
      } else reject(new Error(`Erro da API (${xhr.status}).`));
    };
    xhr.onerror = () => reject(new Error("Não foi possível conectar à API."));
    xhr.send(fd);
  });
}
