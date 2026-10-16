"""Fixtures compartilhadas dos testes de API (etapa 8)."""

from __future__ import annotations

import secrets
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_servico_lotes
from app.main import app
from app.parser import FolhaExtraida
from app.persistence import (
    Funcionario,
    RegistroDiario,
    RepositorioLotes,
)
from app.services import ExecutorImediato, ServicoLotes

#: PNG mínimo válido (assinatura + padding), suficiente para a validação de upload.
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 20

#: Registro completo e coerente (gera total confirmado).
REGISTRO_COMPLETO = {
    "entrada": "08:00",
    "saida_almoco": "12:00",
    "volta_almoco": "13:00",
    "saida": "17:00",
}


@pytest.fixture(autouse=True)
def _limpar_overrides() -> Iterator[None]:
    yield
    app.dependency_overrides.clear()


def folha_com(registros: list[dict]) -> Callable[..., FolhaExtraida]:
    """Cria um extrator falso que devolve os registros informados."""

    def extrator(_dados: bytes, *, origem: str) -> FolhaExtraida:
        return FolhaExtraida(
            funcionario=Funcionario(funcionario_id="f1", nome="TESTE", codigo="001"),
            mes=8,
            ano=2026,
            registros=[
                RegistroDiario(
                    registro_id=secrets.token_hex(8),
                    dia=indice + 1,
                    origem=origem,
                    **registro,
                )
                for indice, registro in enumerate(registros)
            ],
        )

    return extrator


def montar_servico(tmp_path, extrator) -> ServicoLotes:
    return ServicoLotes(
        RepositorioLotes(base=tmp_path), ExecutorImediato(), extrator=extrator
    )


def montar_cliente(tmp_path, extrator) -> tuple[TestClient, ServicoLotes]:
    servico = montar_servico(tmp_path, extrator)
    app.dependency_overrides[get_servico_lotes] = lambda: servico
    return TestClient(app), servico


def enviar_lote(cliente: TestClient, quantidade: int = 1):
    arquivos = [("arquivos", (f"foto{i}.png", PNG, "image/png")) for i in range(quantidade)]
    return cliente.post("/api/lotes", files=arquivos)
