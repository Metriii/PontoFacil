import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState, type ReactNode } from "react";
import JSZip from "jszip";
import {
  Clock, ImageIcon, FolderOpen, FileArchive, UploadCloud, X, Trash2, AlertCircle,
  CheckCircle2, Loader2, Download, FileSpreadsheet, Pencil, Info, Check,
} from "lucide-react";
import {
  isBackendConnected,
  criarLote, aguardarLote, obterResultados, obterDuvidas, corrigirRegistro, paraRegistros,
  exportarLote, baixarArquivo,
  type Registro, type ResultadoProcessamento, type Duvida, type CampoHorario, type RegistroAPI, type Planilha,
} from "@/lib/api";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "PontoFácil — Automação de cartões de ponto" },
      { name: "description", content: "Envie cartões de ponto manuscritos, revise os horários reconhecidos e gere planilhas Excel." },
      { property: "og:title", content: "PontoFácil — Automação de cartões de ponto" },
      { property: "og:description", content: "Envie cartões de ponto, revise os horários e gere planilhas Excel." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Index,
});

const IMG_EXT = ["jpg", "jpeg", "png", "webp"];
const ext = (n: string) => n.split(".").pop()?.toLowerCase() ?? "";
const isImg = (n: string) => IMG_EXT.includes(ext(n));
const fmtSize = (b: number) => b < 1024 ? `${b} B` : b < 1048576 ? `${(b / 1024).toFixed(1)} KB` : `${(b / 1048576).toFixed(1)} MB`;

type Item = {
  key: string; file: File; path: string; kind: "imagem" | "zip";
  folder?: string | undefined; preview?: string; zipCount?: number | null;
};

const ETAPAS = ["Arquivos enviados", "Leitura dos cartões", "Validação dos horários", "Planilha pronta"];

function Index() {
  const [items, setItems] = useState<Item[]>([]);
  const [msgs, setMsgs] = useState<string[]>([]);
  const [drag, setDrag] = useState(false);
  const [loading, setLoading] = useState(false);
  const [etapa, setEtapa] = useState(-1);
  const [progress, setProgress] = useState(0);
  const [erro, setErro] = useState<string | null>(null);
  const [res, setRes] = useState<ResultadoProcessamento | null>(null);
  const [registros, setRegistros] = useState<Registro[]>([]);
  const [loteId, setLoteId] = useState<string | null>(null);
  const [duvidas, setDuvidas] = useState<Duvida[]>([]);
  const [erroDownload, setErroDownload] = useState<string | null>(null);
  const [baixando, setBaixando] = useState<string | null>(null);
  const fotosRef = useRef<HTMLInputElement>(null);
  const pastaRef = useRef<HTMLInputElement>(null);
  const zipRef = useRef<HTMLInputElement>(null);
  const connected = isBackendConnected();

  useEffect(() => () => items.forEach((i) => i.preview && URL.revokeObjectURL(i.preview)), []); // eslint-disable-line

  async function addFiles(list: { file: File; path: string }[]) {
    const warn: string[] = [];
    if (!list.length) { setMsgs(["Nenhum arquivo foi selecionado."]); return; }
    const existing = new Set(items.map((i) => i.key));
    const novos: Item[] = [];
    for (const { file, path } of list) {
      const key = `${path}|${file.size}|${file.lastModified}`;
      if (existing.has(key)) { warn.push(`"${file.name}" já foi adicionado.`); continue; }
      existing.add(key);
      const folder = path.includes("/") ? path.split("/").slice(0, -1).join("/") : undefined;
      if (isImg(file.name)) novos.push({ key, file, path, kind: "imagem", folder, preview: URL.createObjectURL(file) });
      else if (ext(file.name) === "zip") {
        let zipCount: number | null = null;
        try {
          const z = await JSZip.loadAsync(file);
          zipCount = Object.values(z.files).filter((f) => !f.dir && isImg(f.name) && !f.name.startsWith("__MACOSX")).length;
          if (zipCount === 0) warn.push(`O ZIP "${file.name}" não contém imagens suportadas.`);
        } catch { warn.push(`Não foi possível ler o conteúdo de "${file.name}".`); }
        novos.push({ key, file, path, kind: "zip", zipCount });
      } else if (!file.name.startsWith(".")) warn.push(`Formato não suportado: "${file.name}". Use JPG, JPEG, PNG, WEBP ou ZIP.`);
    }
    if (list.length && !novos.length && !warn.length) warn.push("Nenhuma imagem encontrada na seleção.");
    setItems((p) => [...p, ...novos]);
    setMsgs(warn);
  }

  const fromInput = (fl: FileList | null) =>
    addFiles(Array.from(fl ?? []).map((f) => ({ file: f, path: (f as File & { webkitRelativePath?: string }).webkitRelativePath || f.name })));

  async function readEntry(entry: FileSystemEntry, out: { file: File; path: string }[]) {
    if (entry.isFile) {
      const f = await new Promise<File>((r, j) => (entry as FileSystemFileEntry).file(r, j));
      out.push({ file: f, path: entry.fullPath.replace(/^\//, "") });
    } else if (entry.isDirectory) {
      const reader = (entry as FileSystemDirectoryEntry).createReader();
      let batch: FileSystemEntry[];
      do {
        batch = await new Promise((r, j) => reader.readEntries(r, j));
        for (const e of batch) await readEntry(e, out);
      } while (batch.length);
    }
  }

  async function onDrop(e: React.DragEvent) {
    e.preventDefault(); setDrag(false);
    const entries = Array.from(e.dataTransfer.items).map((i) => i.webkitGetAsEntry?.()).filter(Boolean) as FileSystemEntry[];
    if (entries.length) {
      const out: { file: File; path: string }[] = [];
      for (const en of entries) await readEntry(en, out);
      addFiles(out);
    } else fromInput(e.dataTransfer.files);
  }

  const remove = (key: string) => setItems((p) => {
    const alvo = p.find((i) => i.key === key);
    if (alvo?.preview) URL.revokeObjectURL(alvo.preview);
    return p.filter((i) => i.key !== key);
  });
  const clear = () => { items.forEach((i) => i.preview && URL.revokeObjectURL(i.preview)); setItems([]); setMsgs([]); };

  const validos = items.filter((i) => i.kind === "imagem" || (i.zipCount ?? 1) > 0);
  const totalCartoes = items.reduce((s, i) => s + (i.kind === "imagem" ? 1 : i.zipCount ?? 0), 0);

  async function montarArquivos(list: Item[]): Promise<{ file: File; path: string }[]> {
    const out: { file: File; path: string }[] = [];
    for (const it of list) {
      if (it.kind === "imagem") { out.push({ file: it.file, path: it.path }); continue; }
      const z = await JSZip.loadAsync(it.file);
      const base = it.path.replace(/\.zip$/i, "");
      for (const [name, entry] of Object.entries(z.files)) {
        if (entry.dir || name.startsWith("__MACOSX") || !isImg(name)) continue;
        const blob = await entry.async("blob");
        out.push({ file: new File([blob], name.split("/").pop() ?? name, { type: blob.type }), path: `${base}/${name}` });
      }
    }
    return out;
  }

  async function processar() {
    setErro(null); setLoading(true); setEtapa(0); setProgress(0);
    setRes(null); setRegistros([]); setDuvidas([]); setLoteId(null);
    setErroDownload(null);
    try {
      const arquivos = await montarArquivos(validos);
      if (!arquivos.length) throw new Error("Nenhuma imagem válida para enviar.");
      const criado = await criarLote(arquivos, (p) => { setProgress(p); if (p >= 100) setEtapa(1); });
      setLoteId(criado.lote_id); setEtapa(1);
      const lote = await aguardarLote(criado.lote_id, (s) => {
        const total = s.progresso.total || 1;
        setProgress(Math.min(100, Math.round(((s.progresso.processados + s.progresso.falhas) / total) * 100)));
      });
      setEtapa(2);
      const [resultados, listaDuvidas] = await Promise.all([obterResultados(criado.lote_id), obterDuvidas(criado.lote_id)]);
      const regs = paraRegistros(resultados, listaDuvidas);
      setRegistros(regs); setDuvidas(listaDuvidas);

      let planilhas: Planilha[] = [];
      let consolidado: Planilha | null = null;
      try {
        const exportacao = await exportarLote(criado.lote_id);
        planilhas = exportacao.planilhas;
        consolidado = exportacao.consolidado;
      } catch (e) {
        setErroDownload(e instanceof Error ? e.message : "Não foi possível gerar as planilhas.");
      }

      setRes({ total_cartoes: lote.progresso.total, processados: lote.progresso.processados, registros: regs, planilhas, consolidado });
      setEtapa(3);
      if (lote.estado === "falhou" && !regs.length) setErro("O lote falhou: nenhuma imagem pôde ser processada.");
      else if (lote.progresso.falhas > 0) setErro(`${lote.progresso.falhas} imagem(ns) não puderam ser processadas.`);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao processar."); setEtapa(-1);
    } finally { setLoading(false); }
  }

  async function baixar(url: string, nome: string) {
    setErroDownload(null);
    setBaixando(url);
    try {
      const blob = await baixarArquivo(url);
      const obj = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = obj; a.download = nome;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(obj);
    } catch (e) {
      setErroDownload(e instanceof Error ? e.message : "Não foi possível baixar a planilha.");
    } finally {
      setBaixando(null);
    }
  }

  async function corrigir(id: string, changes: Partial<Registro>) {
    if (!loteId) return;
    const atualizados: RegistroAPI[] = [];
    for (const [campo, valor] of Object.entries(changes)) {
      atualizados.push(await corrigirRegistro(id, campo as CampoHorario, (valor as string | null) ?? null));
    }
    const ultimo = atualizados.at(-1);
    const novas = await obterDuvidas(loteId);
    setDuvidas(novas);
    if (ultimo) setRegistros((prev) => prev.map((r) => r.id === id
      ? { ...r, entrada: ultimo.entrada, saida_almoco: ultimo.saida_almoco, volta_almoco: ultimo.volta_almoco, saida: ultimo.saida,
          revisar: ultimo.status_validacao === "pendente" || ultimo.status_validacao === "invalido" || novas.some((d) => d.registro_id === id) }
      : r));
  }

  const precisaRevisao = registros.filter(needsReview).length;
  const groups = groupItems(items);

  return (
    <div className="min-h-screen">
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-6xl items-center gap-4 px-5 py-6">
          <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Clock className="h-6 w-6" />
          </div>
          <div>
            <h1 className="font-display text-2xl font-bold text-primary">PontoFácil</h1>
            <p className="text-sm text-muted-foreground">Automação de cartões de ponto</p>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-8 px-5 py-8">
        <p className="max-w-2xl text-lg">Envie os cartões de ponto, revise os horários reconhecidos e gere suas planilhas Excel.</p>

        {/* Upload */}
        <Section title="1. Envio de arquivos">
          <div
            onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
            onDragLeave={() => setDrag(false)}
            onDrop={onDrop}
            className={`rounded-xl border-2 border-dashed p-8 text-center transition-colors ${drag ? "border-primary bg-accent" : "border-border bg-muted"}`}
          >
            <UploadCloud className="mx-auto h-10 w-10 text-primary" />
            <p className="mt-3 font-medium">Arraste fotos, pastas ou arquivos ZIP aqui</p>
            <p className="text-sm text-muted-foreground">JPG, JPEG, PNG, WEBP ou ZIP com várias fotos</p>
            <div className="mt-5 flex flex-wrap justify-center gap-3">
              <PickBtn icon={<ImageIcon className="h-4 w-4" />} onClick={() => fotosRef.current?.click()}>Selecionar fotos</PickBtn>
              <PickBtn icon={<FolderOpen className="h-4 w-4" />} onClick={() => pastaRef.current?.click()}>Selecionar pasta</PickBtn>
              <PickBtn icon={<FileArchive className="h-4 w-4" />} onClick={() => zipRef.current?.click()}>Selecionar arquivo ZIP</PickBtn>
            </div>
            <input ref={fotosRef} type="file" multiple hidden accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp"
              onChange={(e) => { fromInput(e.target.files); e.target.value = ""; }} />
            <input ref={pastaRef} type="file" multiple hidden
              {...({ webkitdirectory: "", directory: "" } as Record<string, string>)}
              onChange={(e) => { fromInput(e.target.files); e.target.value = ""; }} />
            <input ref={zipRef} type="file" multiple hidden accept=".zip,application/zip"
              onChange={(e) => { fromInput(e.target.files); e.target.value = ""; }} />
          </div>

          {msgs.length > 0 && (
            <div className="mt-4 space-y-1 rounded-lg bg-warning p-3 text-sm text-warning-foreground">
              {msgs.map((m, i) => <p key={i} className="flex gap-2"><AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />{m}</p>)}
            </div>
          )}

          {items.length > 0 && (
            <div className="mt-5">
              <div className="mb-3 flex items-center justify-between">
                <p className="text-sm font-medium">{items.length} arquivo(s) selecionado(s)</p>
                <button onClick={clear} className="flex items-center gap-1 text-sm text-primary hover:underline">
                  <Trash2 className="h-4 w-4" /> Limpar seleção
                </button>
              </div>
              <div className="space-y-4">
                {groups.map(([folder, list]) => (
                  <div key={folder || "_"}>
                    {folder && <p className="mb-2 flex items-center gap-2 text-sm font-semibold text-primary"><FolderOpen className="h-4 w-4" />{folder} <span className="font-normal text-muted-foreground">({list.length} imagem(ns))</span></p>}
                    <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                      {list.map((i) => (
                        <li key={i.key} className="flex items-center gap-3 rounded-lg border border-border bg-card p-2">
                          {i.preview
                            ? <img src={i.preview} alt={i.file.name} className="h-12 w-12 rounded object-cover" />
                            : <div className="flex h-12 w-12 items-center justify-center rounded bg-secondary"><FileArchive className="h-5 w-5 text-primary" /></div>}
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-medium">{i.file.name}</p>
                            <p className="text-xs text-muted-foreground">
                              {i.kind === "zip" ? "ZIP" : ext(i.file.name).toUpperCase()} · {fmtSize(i.file.size)}
                              {i.kind === "zip" && (i.zipCount == null ? " · conteúdo não verificado" : ` · ${i.zipCount} imagem(ns)`)}
                            </p>
                          </div>
                          <button onClick={() => remove(i.key)} aria-label={`Remover ${i.file.name}`} className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-primary">
                            <X className="h-4 w-4" />
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Section>

        {/* Processamento */}
        <Section title="2. Processamento">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
            <button
              onClick={processar}
              disabled={!validos.length || loading || !connected}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-6 py-3 font-semibold text-primary-foreground shadow-sm transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {loading ? <Loader2 className="h-5 w-5 animate-spin" /> : <CheckCircle2 className="h-5 w-5" />}
              Processar cartões
            </button>
            {!connected && (
              <p className="flex items-center gap-2 text-sm text-muted-foreground"><Info className="h-4 w-4" />Backend ainda não conectado. O processamento estará disponível após a integração.</p>
            )}
            {connected && !validos.length && <p className="text-sm text-muted-foreground">Selecione ao menos um arquivo válido.</p>}
          </div>
          <ol className="mt-6 grid gap-3 sm:grid-cols-4">
            {ETAPAS.map((e, idx) => {
              const done = etapa > idx || (etapa === 3 && idx === 3);
              const active = loading && etapa === idx;
              return (
                <li key={e} className={`flex items-center gap-2 rounded-lg border p-3 text-sm ${done ? "border-success text-success" : active ? "border-primary text-primary" : "border-border text-muted-foreground"}`}>
                  {done ? <Check className="h-4 w-4" /> : active ? <Loader2 className="h-4 w-4 animate-spin" /> : <span className="h-4 w-4 rounded-full border border-current" />}
                  {e}
                </li>
              );
            })}
          </ol>
          {loading && (etapa === 0 || etapa === 1) && (
            <div className="mt-3 h-2 overflow-hidden rounded-full bg-muted"><div className="h-full bg-primary transition-all" style={{ width: `${progress}%` }} /></div>
          )}
          {erro && <p className="mt-3 flex items-center gap-2 text-sm text-destructive"><AlertCircle className="h-4 w-4" />{erro}</p>}
        </Section>

        {/* Resumo */}
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          <Stat label="Cartões enviados" value={res?.total_cartoes ?? (res ? 0 : totalCartoes)} />
          <Stat label="Cartões processados" value={res?.processados ?? 0} />
          <Stat label="Precisam de revisão" value={precisaRevisao} highlight={precisaRevisao > 0} />
          <Stat label="Planilhas disponíveis" value={res?.planilhas?.length ?? 0} />
        </div>

        {/* Revisão */}
        <Section title="3. Revisão dos horários">
          {duvidas.length > 0 && (
            <div className="mb-4 space-y-1 rounded-lg bg-warning p-3 text-sm text-warning-foreground">
              <p className="flex items-center gap-2 font-medium"><AlertCircle className="h-4 w-4 shrink-0" />{duvidas.length} dúvida(s) pendente(s) para revisão</p>
              <ul className="list-disc space-y-0.5 pl-6">
                {duvidas.map((d) => {
                  const reg = registros.find((r) => r.id === d.registro_id);
                  const ref = [reg?.funcionario, reg?.data].filter(Boolean).join(" · ");
                  return <li key={d.duvida_id}>{d.campo}{ref ? ` (${ref})` : ""}: {d.motivo}</li>;
                })}
              </ul>
            </div>
          )}
          <ReviewTable registros={registros} onCorrigir={corrigir} />
        </Section>

        {/* Planilhas */}
        <section className="rounded-xl border-2 border-primary bg-card p-6 shadow-sm">
          <h2 className="mb-4 flex items-center gap-2 font-display text-xl font-bold text-primary"><FileSpreadsheet className="h-5 w-5" />Planilhas geradas</h2>
          {erroDownload && (
            <p className="mb-3 flex items-center gap-2 text-sm text-destructive"><AlertCircle className="h-4 w-4" />{erroDownload}</p>
          )}
          {!res || (!res.planilhas?.length && !res.consolidado) ? (
            <div className="rounded-lg bg-muted p-6 text-center text-sm text-muted-foreground">
              {res ? (
                <p className="font-medium text-foreground">Nenhum registro confirmado ou corrigido para exportar.</p>
              ) : (
                <p className="font-medium text-foreground">Suas planilhas aparecerão aqui após o processamento.</p>
              )}
              <p className="mt-1">O botão “Baixar Excel” só fica disponível quando houver uma planilha real gerada pelo sistema.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {res.consolidado && (
                <PlanilhaRow p={res.consolidado} destaque onBaixar={baixar} baixando={baixando} />
              )}
              {res.planilhas.map((p) => <PlanilhaRow key={p.url} p={p} onBaixar={baixar} baixando={baixando} />)}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

function needsReview(r: Registro) {
  if (typeof r.revisar === "boolean") return r.revisar;
  return r.confianca == null || r.confianca < 0.7 ||
    [r.entrada, r.saida_almoco, r.volta_almoco, r.saida].some((h) => !h);
}

function groupItems(items: Item[]): [string, Item[]][] {
  const m = new Map<string, Item[]>();
  items.forEach((i) => { const k = i.folder ?? ""; m.set(k, [...(m.get(k) ?? []), i]); });
  return Array.from(m.entries()).sort(([a], [b]) => (a === "" ? -1 : b === "" ? 1 : a.localeCompare(b)));
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-border bg-card p-6 shadow-sm">
      <h2 className="mb-4 font-display text-xl font-bold">{title}</h2>
      {children}
    </section>
  );
}

function PickBtn({ icon, children, onClick }: { icon: ReactNode; children: ReactNode; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} className="inline-flex items-center gap-2 rounded-lg border border-primary bg-card px-4 py-2 text-sm font-medium text-primary transition hover:bg-accent">
      {icon}{children}
    </button>
  );
}

function Stat({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div className={`rounded-xl border p-4 ${highlight ? "border-primary bg-accent" : "border-border bg-card"}`}>
      <p className="font-display text-3xl font-bold text-primary">{value}</p>
      <p className="text-sm text-muted-foreground">{label}</p>
    </div>
  );
}

const CAMPOS: { k: keyof Registro; l: string }[] = [
  { k: "entrada", l: "Entrada 1º turno" }, { k: "saida_almoco", l: "Saída almoço" },
  { k: "volta_almoco", l: "Volta almoço" }, { k: "saida", l: "Saída final" },
];

function ReviewTable({ registros, onCorrigir }: { registros: Registro[]; onCorrigir: (id: string, changes: Partial<Registro>) => Promise<void> }) {
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState<Registro | null>(null);
  const [salvando, setSalvando] = useState(false);
  if (!registros.length)
    return <div className="rounded-lg bg-muted p-6 text-center text-sm text-muted-foreground">Os horários reconhecidos aparecerão aqui após o processamento real dos cartões.</div>;
  const iniciar = (r: Registro) => { setEditing(r.id); setDraft({ ...r }); };
  const cancelar = () => { setEditing(null); setDraft(null); };
  const set = (k: keyof Registro, v: string) => setDraft((d) => (d ? { ...d, [k]: v || null } : d));
  const concluir = async () => {
    const orig = registros.find((r) => r.id === editing);
    if (!orig || !draft) { cancelar(); return; }
    const changes: Partial<Registro> = {};
    for (const c of CAMPOS) if ((draft[c.k] as string | null) !== (orig[c.k] as string | null)) (changes as Record<string, string | null>)[c.k] = draft[c.k] as string | null;
    if (Object.keys(changes).length) {
      setSalvando(true);
      try { await onCorrigir(orig.id, changes); } finally { setSalvando(false); }
    }
    cancelar();
  };
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[900px] text-sm">
        <thead><tr className="border-b border-border text-left text-muted-foreground">
          <th className="p-2">Funcionário</th><th className="p-2">Data</th><th className="p-2">Dia</th>
          {CAMPOS.map((c) => <th key={c.k} className="p-2">{c.l}</th>)}
          <th className="p-2">Confiança</th><th className="p-2">Ação</th>
        </tr></thead>
        <tbody>
          {registros.map((r) => {
            const rev = needsReview(r); const ed = editing === r.id;
            const linha = ed && draft ? draft : r;
            return (
              <tr key={r.id} className={`border-b border-border ${rev ? "bg-warning" : ""}`}>
                <td className="p-2">{r.funcionario ?? "—"}</td><td className="p-2">{r.data ?? "—"}</td><td className="p-2">{r.dia_semana ?? "—"}</td>
                {CAMPOS.map((c) => (
                  <td key={c.k} className="p-2">
                    {ed ? <input type="time" value={(linha[c.k] as string) ?? ""} disabled={salvando} onChange={(e) => set(c.k, e.target.value)} className="rounded border border-input bg-card px-1 py-0.5" />
                      : (r[c.k] as string) ?? <span className="font-medium text-destructive">Revisar</span>}
                  </td>
                ))}
                <td className="p-2">{r.confianca == null ? "—" : `${Math.round(r.confianca * 100)}%`}{rev && <span className="ml-1 text-xs text-warning-foreground">· revisão manual</span>}</td>
                <td className="p-2">
                  {ed ? (
                    <div className="flex items-center gap-2">
                      <button onClick={concluir} disabled={salvando} className="inline-flex items-center gap-1 rounded border border-primary px-2 py-1 text-xs text-primary hover:bg-accent disabled:opacity-50">
                        {salvando ? <Loader2 className="h-3 w-3 animate-spin" /> : <Check className="h-3 w-3" />}{salvando ? "Salvando" : "Concluir"}
                      </button>
                      <button onClick={cancelar} disabled={salvando} className="inline-flex items-center gap-1 rounded border border-border px-2 py-1 text-xs text-muted-foreground hover:bg-muted disabled:opacity-50">Cancelar</button>
                    </div>
                  ) : (
                    <button onClick={() => iniciar(r)} className="inline-flex items-center gap-1 rounded border border-primary px-2 py-1 text-xs text-primary hover:bg-accent">
                      <Pencil className="h-3 w-3" />Corrigir
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function PlanilhaRow({
  p,
  destaque,
  onBaixar,
  baixando,
}: {
  p: Planilha;
  destaque?: boolean;
  onBaixar: (url: string, nome: string) => void;
  baixando: string | null;
}) {
  const carregando = baixando === p.url;
  const subtitulo = [p.funcionario, p.referencia, p.status].filter(Boolean).join(" · ");
  return (
    <div
      className={`flex flex-col gap-3 rounded-lg border p-4 sm:flex-row sm:items-center ${destaque ? "border-primary bg-accent" : "border-border"}`}
    >
      <FileSpreadsheet className="h-8 w-8 shrink-0 text-success" />
      <div className="flex-1">
        <p className="font-medium">
          {destaque ? "Planilha consolidada · " : ""}
          {p.arquivo}
        </p>
        <p className="text-sm text-muted-foreground">{subtitulo}</p>
      </div>
      <button
        type="button"
        onClick={() => onBaixar(p.url, p.arquivo)}
        disabled={carregando}
        className="inline-flex items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:opacity-90 disabled:opacity-60"
      >
        {carregando ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <Download className="h-4 w-4" />
        )}
        {carregando ? "Baixando..." : "Baixar Excel"}
      </button>
    </div>
  );
}
