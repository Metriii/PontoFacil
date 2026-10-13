from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.arquivos import (
    extrair_zip_seguro,
    listar_imagens,
    nome_seguro,
    salvar_upload,
    validar_arquivo,
)
from backend.config import (
    ALLOWED_IMAGE_EXTS,
    ALLOWED_PDF_EXTS,
    CORS_ORIGINS,
    FOTOS_DIR,
    MAX_FILES_PER_BATCH,
    TEMP_DIR,
)
from backend.processador import criar_processamento, obter_processamento, processar_cartoes
from backend.schemas import CorreacaoRegistro, Duvida, HealthResponse, ListaDuvidas
from backend.validador import validar_registro

app = FastAPI(
    title="PontoFacil API",
    description="Backend local para automacao de cartoes de ponto manuscritos",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def tesseract_disponivel() -> bool:
    return shutil.which("tesseract") is not None


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", tesseract=tesseract_disponivel())


@app.post("/processar")
async def processar(files: list[UploadFile], background_tasks: BackgroundTasks):
    if not files:
        return JSONResponse(status_code=400, content={"erro": "Nenhum arquivo enviado."})
    if len(files) > MAX_FILES_PER_BATCH:
        return JSONResponse(
            status_code=400,
            content={"erro": f"Limite de {MAX_FILES_PER_BATCH} arquivos por lote excedido."},
        )

    imagens: list[Path] = []
    erros: list[str] = []

    for f in files:
        content = await f.read()
        ok, motivo = validar_arquivo(f.filename or "arquivo_sem_nome", len(content))
        if not ok:
            erros.append(motivo)
            continue
        ext = Path(f.filename or "").suffix.lower()
        if ext in ALLOWED_IMAGE_EXTS:
            caminho = salvar_upload(content, f.filename or "sem_nome.jpg", FOTOS_DIR)
            imagens.append(caminho)
        elif ext in ALLOWED_PDF_EXTS:
            try:
                import fitz
                doc = fitz.open(stream=content, filetype="pdf")
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    pix = page.get_pixmap(dpi=300)
                    img_path = FOTOS_DIR / f"{nome_seguro(f.filename or 'pagina')}_p{page_num}.png"
                    img_path.write_bytes(pix.tobytes("png"))
                    imagens.append(img_path)
            except Exception as e:
                erros.append(f"PDF '{f.filename}': {str(e)}")
        elif ext == ".zip":
            temp_dir = TEMP_DIR / uuid.uuid4().hex[:12]
            try:
                extraidos = extrair_zip_seguro(content, temp_dir)
                for e in extraidos:
                    ok_e, motivo_e = validar_arquivo(e.name, e.stat().st_size)
                    if ok_e:
                        imagens.append(e)
                    else:
                        erros.append(motivo_e)
            except ValueError as ve:
                erros.append(str(ve))

    if not imagens:
        return JSONResponse(
            status_code=400,
            content={"erro": "Nenhuma imagem válida encontrada.", "detalhes": erros},
        )

    pid = criar_processamento()
    background_tasks.add_task(processar_cartoes, pid, imagens)
    return {"id": pid, "status": "processando", "erros_upload": erros}


@app.get("/api/processamentos/{processamento_id}")
async def consultar_processamento(processamento_id: str):
    status = obter_processamento(processamento_id)
    if status is None:
        return JSONResponse(status_code=404, content={"erro": "Processamento não encontrado."})
    return status


@app.get("/api/processamentos/{processamento_id}/duvidas")
async def listar_duvidas(processamento_id: str):
    status = obter_processamento(processamento_id)
    if status is None:
        return JSONResponse(status_code=404, content={"erro": "Processamento não encontrado."})
    if not status.resultado:
        return ListaDuvidas(duvidas=[])

    duvidas: list[Duvida] = []
    for reg in status.resultado.registros:
        if reg.revisar or reg.confianca is None or reg.confianca < 0.7:
            if not reg.funcionario:
                duvidas.append(Duvida(registro_id=reg.id, campo="funcionario", motivo="não identificado", valor_atual=None))
            if not reg.data:
                duvidas.append(Duvida(registro_id=reg.id, campo="data", motivo="não identificada", valor_atual=None))
            for campo, valor in [("entrada", reg.entrada), ("saida_almoco", reg.saida_almoco), ("volta_almoco", reg.volta_almoco), ("saida", reg.saida)]:
                if not valor:
                    duvidas.append(Duvida(registro_id=reg.id, campo=campo, motivo="não identificado", valor_atual=None))
    return ListaDuvidas(duvidas=duvidas)


@app.patch("/api/registros/{registro_id}")
async def corrigir_registro(registro_id: str, body: CorreacaoRegistro):
    for status in PROCESSAMENTOS.values():
        if status.resultado:
            for reg in status.resultado.registros:
                if reg.id == registro_id:
                    campo = body.campo
                    valor = body.valor

                    if campo in ("entrada", "saida_almoco", "volta_almoco", "saida"):
                        if valor is not None:
                            import re
                            if not re.match(r"^([01]\d|2[0-3]):[0-5]\d$", valor):
                                return JSONResponse(status_code=422, content={"erro": f"Horário inválido: {valor}"})

                    if campo == "funcionario":
                        reg.funcionario = valor
                    elif campo == "data":
                        reg.data = valor
                    elif campo == "dia_semana":
                        reg.dia_semana = valor
                    elif campo == "entrada":
                        reg.entrada = valor
                    elif campo == "saida_almoco":
                        reg.saida_almoco = valor
                    elif campo == "volta_almoco":
                        reg.volta_almoco = valor
                    elif campo == "saida":
                        reg.saida = valor

                    reg.revisar = False
                    return {"ok": True}

    return JSONResponse(status_code=404, content={"erro": "Registro não encontrado."})


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"erro": "Erro interno do servidor. Tente novamente."},
    )
