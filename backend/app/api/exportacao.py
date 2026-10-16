"""Endpoints de exportação e download de planilhas (RF-012/013/015).

- ``POST /api/lotes/{lote_id}/exportar``: gera (ou regenera) as planilhas.
- ``GET  /api/lotes/{lote_id}/downloads``: lista os arquivos gerados do lote.
- ``GET  /api/lotes/{lote_id}/downloads/{arquivo_id}``: baixa um arquivo do lote.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from ..persistence import LoteNaoEncontrado
from ..schemas import ExportacaoLote, PlanilhaSchema, planilha_schema
from ..security import CaminhoInseguro
from ..services import ArquivoNaoEncontrado
from .deps import ServicoDep

router = APIRouter(prefix="/api/lotes", tags=["exportacao"])

_MEDIA_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _planilhas(servico: ServicoDep, lote_id: str) -> list[PlanilhaSchema]:
    lote = servico.repo.obter(lote_id)
    return [planilha_schema(arquivo, lote_id) for arquivo in lote.arquivos_gerados]


@router.post("/{lote_id}/exportar", response_model=ExportacaoLote)
def exportar_lote(lote_id: str, servico: ServicoDep) -> ExportacaoLote:
    """Gera as planilhas do lote com apenas registros confirmados/corrigidos válidos."""
    try:
        resultado = servico.exportar_lote(lote_id)
    except (LoteNaoEncontrado, CaminhoInseguro) as exc:
        raise HTTPException(status_code=404, detail="Lote não encontrado.") from exc

    planilhas = [
        planilha_schema(arquivo, lote_id) for arquivo in resultado.arquivos
    ]
    consolidado = next(
        (p for p in planilhas if p.arquivo == "consolidado.xlsx"), None
    )
    individuais = [p for p in planilhas if p is not consolidado]
    return ExportacaoLote(
        lote_id=lote_id,
        planilhas=individuais,
        consolidado=consolidado,
        total_registros=resultado.total_registros,
    )


@router.get("/{lote_id}/downloads", response_model=list[PlanilhaSchema])
def listar_downloads(lote_id: str, servico: ServicoDep) -> list[PlanilhaSchema]:
    """Lista os arquivos gerados, restritos ao lote solicitado."""
    try:
        return _planilhas(servico, lote_id)
    except (LoteNaoEncontrado, CaminhoInseguro) as exc:
        raise HTTPException(status_code=404, detail="Lote não encontrado.") from exc


@router.get("/{lote_id}/downloads/{arquivo_id}")
def baixar_arquivo(lote_id: str, arquivo_id: str, servico: ServicoDep) -> FileResponse:
    """Disponibiliza o download de um arquivo gerado pertencente ao lote."""
    try:
        caminho, registro = servico.localizar_arquivo(lote_id, arquivo_id)
    except (LoteNaoEncontrado, CaminhoInseguro, ArquivoNaoEncontrado) as exc:
        raise HTTPException(
            status_code=404, detail="Arquivo não encontrado para este lote."
        ) from exc
    return FileResponse(caminho, media_type=_MEDIA_XLSX, filename=registro.nome)
