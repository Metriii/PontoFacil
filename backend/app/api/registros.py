"""Endpoint de correção manual de registros (RF-009)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..schemas import CorrecaoEntrada, RegistroSchema, registro_schema
from ..services import CorrecaoInvalida, RegistroNaoEncontrado
from .deps import ServicoDep

router = APIRouter(prefix="/api/registros", tags=["registros"])


@router.patch("/{registro_id}", response_model=RegistroSchema)
def corrigir_registro(
    registro_id: str, corpo: CorrecaoEntrada, servico: ServicoDep
) -> RegistroSchema:
    """Corrige um horário, validando o valor e distinguindo-o do resultado do OCR."""
    try:
        registro = servico.corrigir_registro(
            registro_id, campo=corpo.campo, valor=corpo.valor
        )
    except RegistroNaoEncontrado as exc:
        raise HTTPException(
            status_code=404, detail="Registro não encontrado."
        ) from exc
    except CorrecaoInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return registro_schema(registro)
