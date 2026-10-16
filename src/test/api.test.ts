import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  aguardarLote,
  baixarArquivo,
  corrigirRegistro,
  criarLote,
  exportarLote,
  isBackendConnected,
  obterDuvidas,
  obterLote,
  obterResultados,
  paraRegistros,
  resolveUrl,
  type LoteStatus,
  type ResultadosLote,
} from "@/lib/api";

const BASE = "http://localhost:8000";

type RespostaFalsa = { ok: boolean; status: number; json: () => Promise<unknown> };

function mockFetch(corpo: unknown, status = 200) {
  const resp: RespostaFalsa = {
    ok: status >= 200 && status < 300,
    status,
    json: async () => corpo,
  };
  const fn = vi.fn(async (_url: string, _init?: RequestInit) => resp);
  vi.stubGlobal("fetch", fn);
  return fn;
}

beforeEach(() => {
  vi.stubEnv("VITE_API_URL", BASE);
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("conexão com o backend", () => {
  it("usa a URL padrão local quando VITE_API_URL não está definida", () => {
    vi.unstubAllEnvs();
    expect(isBackendConnected()).toBe(true);
    expect(resolveUrl("/api/health")).toBe("http://127.0.0.1:8000/api/health");
  });

  it("respeita VITE_API_URL quando definida", () => {
    expect(isBackendConnected()).toBe(true);
    expect(resolveUrl("/api/lotes")).toBe(`${BASE}/api/lotes`);
  });
});

describe("api de lote assíncrono", () => {
  it("cria lote via multipart reportando progresso de upload", async () => {
    class FakeXHR {
      upload: {
        onprogress:
          ((e: { lengthComputable: boolean; loaded: number; total: number }) => void) | null;
      } = { onprogress: null };
      status = 201;
      responseText = JSON.stringify({ lote_id: "abc", estado: "processando" });
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;
      open = vi.fn();
      send = vi.fn(() => {
        this.upload.onprogress?.({ lengthComputable: true, loaded: 1, total: 2 });
        this.onload?.();
      });
    }
    vi.stubGlobal("XMLHttpRequest", FakeXHR);
    const pcts: number[] = [];

    const res = await criarLote([{ file: new File(["x"], "a.jpg"), path: "a.jpg" }], (p) =>
      pcts.push(p),
    );

    expect(res).toEqual({ lote_id: "abc", estado: "processando" });
    expect(pcts).toContain(50);
  });

  it("consulta estado, resultados e dúvidas", async () => {
    const status = {
      lote_id: "L1",
      criado_em: "2026-10-16T08:00:00",
      estado: "concluido",
      progresso: { total: 2, processados: 2, falhas: 0, revisao: 1 },
      imagens: [],
      arquivos_gerados: [],
    } satisfies LoteStatus;

    const f1 = mockFetch(status);
    await expect(obterLote("L1")).resolves.toMatchObject({ estado: "concluido" });
    expect(f1.mock.calls[0]?.[0]).toBe(`${BASE}/api/lotes/L1`);

    const f2 = mockFetch({ lote_id: "L1", fichas: [] });
    await expect(obterResultados("L1")).resolves.toEqual({ lote_id: "L1", fichas: [] });
    expect(f2.mock.calls[0]?.[0]).toBe(`${BASE}/api/lotes/L1/resultados`);

    const f3 = mockFetch([]);
    await expect(obterDuvidas("L1")).resolves.toEqual([]);
    expect(f3.mock.calls[0]?.[0]).toBe(`${BASE}/api/lotes/L1/duvidas`);
  });

  it("envia correção por PATCH com campo e valor", async () => {
    const fn = mockFetch({ registro_id: "r1", entrada: "09:00", status_validacao: "corrigido" });

    await corrigirRegistro("r1", "entrada", "09:00");

    const [url, init] = fn.mock.calls[0] ?? [];
    expect(url).toBe(`${BASE}/api/registros/r1`);
    expect(init?.method).toBe("PATCH");
    expect(JSON.parse(String(init?.body))).toEqual({ campo: "entrada", valor: "09:00" });
  });

  it("propaga a mensagem de erro da API", async () => {
    mockFetch({ detail: "Lote não encontrado." }, 404);
    await expect(obterLote("inexistente")).rejects.toThrow("Lote não encontrado.");
  });

  it("aguarda o lote até um estado terminal", async () => {
    const processando = {
      lote_id: "L1",
      criado_em: "2026-10-16T08:00:00",
      estado: "processando",
      progresso: { total: 2, processados: 1, falhas: 0, revisao: 0 },
      imagens: [],
      arquivos_gerados: [],
    } satisfies LoteStatus;
    const concluido = {
      ...processando,
      estado: "concluido",
      progresso: { ...processando.progresso, processados: 2 },
    };
    let chamadas = 0;
    vi.stubGlobal("fetch", async () => ({
      ok: true,
      status: 200,
      json: async () => (++chamadas <= 1 ? processando : concluido),
    }));

    const vistos: string[] = [];
    const final = await aguardarLote("L1", (s) => vistos.push(s.estado), 1);

    expect(final.estado).toBe("concluido");
    expect(vistos).toEqual(["processando", "concluido"]);
  });
});

describe("paraRegistros", () => {
  const resultados: ResultadosLote = {
    lote_id: "L1",
    fichas: [
      {
        funcionario: {
          funcionario_id: "f1",
          nome: "Maria",
          codigo: null,
          empresa: null,
          departamento: null,
          funcao: null,
        },
        mes: 8,
        ano: 2026,
        registros: [
          {
            registro_id: "r1",
            dia: 3,
            dia_semana: "segunda-feira",
            entrada: "08:00",
            saida_almoco: "12:00",
            volta_almoco: "13:00",
            saida: "17:00",
            tipo_dia: "util",
            status_validacao: "confirmado",
            confianca: 0.9,
            observacao: null,
            origem: "a.jpg",
            correcao: null,
          },
          {
            registro_id: "r2",
            dia: 4,
            dia_semana: null,
            entrada: null,
            saida_almoco: null,
            volta_almoco: null,
            saida: null,
            tipo_dia: "util",
            status_validacao: "pendente",
            confianca: null,
            observacao: null,
            origem: "a.jpg",
            correcao: null,
          },
        ],
      },
    ],
  };

  it("mapeia fichas para o formato da tela, marcando dúvidas para revisão", () => {
    const regs = paraRegistros(resultados, [
      {
        duvida_id: "d1",
        registro_id: "r2",
        campo: "entrada",
        motivo: "Horário ausente",
        origem: "a.jpg",
      },
    ]);

    expect(regs).toHaveLength(2);
    expect(regs[0]).toMatchObject({
      id: "r1",
      funcionario: "Maria",
      data: "03/08/2026",
      revisar: false,
    });
    expect(regs[1]).toMatchObject({
      id: "r2",
      funcionario: "Maria",
      data: "04/08/2026",
      revisar: true,
    });
  });

  it("usa o código quando não há nome", () => {
    const semNome: ResultadosLote = {
      ...resultados,
      fichas: [
        {
          ...resultados.fichas[0]!,
          funcionario: { ...resultados.fichas[0]!.funcionario, nome: null, codigo: "007" },
        },
      ],
    };
    expect(paraRegistros(semNome)[0]?.funcionario).toBe("007");
  });
});

describe("exportação de planilhas", () => {
  const planilha = {
    arquivo: "ponto-maria-2026-08.xlsx",
    funcionario: "Maria",
    referencia: "2026-08",
    status: "disponível",
    url: "/api/lotes/L1/downloads/a1",
  };

  it("exporta o lote via POST e devolve planilhas e consolidado", async () => {
    const fn = mockFetch({
      lote_id: "L1",
      planilhas: [planilha],
      consolidado: {
        ...planilha,
        arquivo: "consolidado.xlsx",
        funcionario: null,
        url: "/api/lotes/L1/downloads/a2",
      },
      total_registros: 1,
    });

    const res = await exportarLote("L1");

    const [url, init] = fn.mock.calls[0] ?? [];
    expect(url).toBe(`${BASE}/api/lotes/L1/exportar`);
    expect(init?.method).toBe("POST");
    expect(res.planilhas).toHaveLength(1);
    expect(res.consolidado?.arquivo).toBe("consolidado.xlsx");
    expect(res.total_registros).toBe(1);
  });

  it("trata lote sem dados exportáveis", async () => {
    mockFetch({ lote_id: "L1", planilhas: [], consolidado: null, total_registros: 0 });
    const res = await exportarLote("L1");
    expect(res.planilhas).toEqual([]);
    expect(res.consolidado).toBeNull();
  });

  it("baixa a planilha pela URL relativa e devolve o blob", async () => {
    const blob = new Blob(["xlsx"]);
    const fn = vi.fn(async (_url: string) => ({ ok: true, status: 200, blob: async () => blob }));
    vi.stubGlobal("fetch", fn);

    const res = await baixarArquivo("/api/lotes/L1/downloads/a1");

    expect(res).toBe(blob);
    expect(fn.mock.calls[0]?.[0]).toBe(`${BASE}/api/lotes/L1/downloads/a1`);
  });

  it("propaga erro de download da API", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 404,
        json: async () => ({ detail: "Arquivo não encontrado para este lote." }),
      })),
    );
    await expect(baixarArquivo("/api/lotes/L1/downloads/x")).rejects.toThrow(
      "Arquivo não encontrado para este lote.",
    );
  });
});
