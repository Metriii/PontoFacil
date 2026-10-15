"""Camada de armazenamento local em disco.

Organiza os dados do PontoFácil sem banco de dados: um diretório por lote com
as imagens de entrada e (em etapas futuras) os arquivos JSON, além de um
diretório de exportações. Toda gravação de disponibilização de caminho passa
por ``resolver_caminho_seguro``.
"""

from __future__ import annotations

from pathlib import Path

from .config import settings
from .security.files import exigir_id_lote, resolver_caminho_seguro


def _raiz(base: Path | None) -> Path:
    return (base if base is not None else settings.storage_dir).resolve()


def garantir_storage(*, base: Path | None = None) -> Path:
    """Garante a existência dos diretórios base de armazenamento."""
    raiz = _raiz(base)
    (raiz / "lotes").mkdir(parents=True, exist_ok=True)
    (raiz / "exports").mkdir(parents=True, exist_ok=True)
    return raiz


def criar_pasta_lote(lote_id: str, *, base: Path | None = None) -> Path:
    """Cria (se necessário) e retorna o diretório de um lote."""
    raiz = garantir_storage(base=base)
    exigir_id_lote(lote_id)
    pasta = resolver_caminho_seguro(raiz / "lotes", lote_id)
    (pasta / "imagens").mkdir(parents=True, exist_ok=True)
    return pasta


def pasta_imagens_lote(lote_id: str, *, base: Path | None = None) -> Path:
    """Retorna o diretório de imagens de um lote, com caminho validado."""
    return resolver_caminho_seguro(criar_pasta_lote(lote_id, base=base), "imagens")


def salvar_imagem(
    lote_id: str, nome_interno: str, conteudo: bytes, *, base: Path | None = None
) -> Path:
    """Salva uma imagem com escrita atômica e retorna o caminho final."""
    pasta = pasta_imagens_lote(lote_id, base=base)
    destino = resolver_caminho_seguro(pasta, nome_interno)
    temporario = destino.with_name(destino.name + ".tmp")
    temporario.write_bytes(conteudo)
    temporario.replace(destino)
    return destino
