"""Leitura e escrita de JSON em disco, com gravação atômica.

Evita dados corrompidos: a escrita ocorre em um arquivo temporário que só é
movido para o destino (``os.replace``) após ser finalizado com sucesso.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class DadosCorrompidos(Exception):
    """Arquivo JSON existente mas inválido."""


def gravar_json(caminho: Path, dados: Any) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(dados, ensure_ascii=False, indent=2)
    temporario = caminho.with_name(caminho.name + ".tmp")
    temporario.write_text(texto, encoding="utf-8")
    os.replace(temporario, caminho)


def ler_json(caminho: Path) -> Any:
    texto = caminho.read_text(encoding="utf-8")
    try:
        return json.loads(texto)
    except json.JSONDecodeError as exc:
        raise DadosCorrompidos(f"Arquivo JSON inválido: {caminho.name}") from exc


def ler_json_ou(caminho: Path, padrao: Any) -> Any:
    """Lê o JSON ou retorna ``padrao`` caso o arquivo ainda não exista."""
    try:
        return ler_json(caminho)
    except FileNotFoundError:
        return padrao
