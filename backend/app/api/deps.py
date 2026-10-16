"""Dependências compartilhadas dos routers.

O serviço de lotes é único por aplicação (``app.state.servico_lotes``) e injetado
nos endpoints; os testes o substituem por uma instância com repositório
temporário e executor imediato.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from ..services import ServicoLotes


def get_servico_lotes(request: Request) -> ServicoLotes:
    return request.app.state.servico_lotes


ServicoDep = Annotated[ServicoLotes, Depends(get_servico_lotes)]
