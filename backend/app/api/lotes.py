"""Endpoints de lote: upload em lote, progresso, resultados e dúvidas (RF-001..004/014)."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..config import settings
from ..persistence import Lote, LoteNaoEncontrado
from ..schemas import (
    DuvidaSchema,
    LoteCriado,
    LoteStatus,
    ResultadosLote,
    duvida_schema,
    lote_status,
    resultados_lote,
)
from ..security import CaminhoInseguro, LimitesUpload, validar_lote
from .deps import ServicoDep

router = APIRouter(prefix="/api/lotes", tags=["lotes"])


def _limites() -> LimitesUpload:
    return LimitesUpload(
        max_arquivo_bytes=settings.max_arquivo_bytes,
        max_arquivos=settings.max_arquivos_por_lote,
        max_total_bytes=settings.max_total_bytes,
    )


def _obter_lote(servico: ServicoDep, lote_id: str) -> Lote:
    try:
        return servico.repo.obter(lote_id)
    except (LoteNaoEncontrado, CaminhoInseguro) as exc:
        raise HTTPException(status_code=404, detail="Lote não encontrado.") from exc


@router.post("", response_model=LoteCriado, status_code=201)
async def criar_lote(
    servico: ServicoDep, arquivos: list[UploadFile] = File(...)
) -> LoteCriado:
    """Recebe imagens em lote, cria o lote e dispara o processamento assíncrono."""
    entradas = [
        (arquivo.filename or "arquivo", await arquivo.read()) for arquivo in arquivos
    ]
    validados = validar_lote(entradas, _limites())
    lote = servico.criar_lote(validados)
    servico.agendar(lote.lote_id)
    atual = servico.repo.obter(lote.lote_id)
    return LoteCriado(lote_id=atual.lote_id, estado=atual.estado)


@router.get("/{lote_id}", response_model=LoteStatus)
def obter_lote(lote_id: str, servico: ServicoDep) -> LoteStatus:
    """Estado e progresso de um lote."""
    return lote_status(_obter_lote(servico, lote_id))


@router.get("/{lote_id}/resultados", response_model=ResultadosLote)
def resultados(lote_id: str, servico: ServicoDep) -> ResultadosLote:
    """Fichas e registros extraídos do lote."""
    lote = _obter_lote(servico, lote_id)
    fichas = servico.repo.carregar_fichas(lote.lote_id)
    return resultados_lote(lote.lote_id, fichas)


@router.get("/{lote_id}/duvidas", response_model=list[DuvidaSchema])
def duvidas(lote_id: str, servico: ServicoDep) -> list[DuvidaSchema]:
    """Pendências que precisam de revisão manual."""
    lote = _obter_lote(servico, lote_id)
    return [duvida_schema(d) for d in servico.repo.carregar_duvidas(lote.lote_id)]
