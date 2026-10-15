"""Validação de uploads em lote, com limites (CONTEXT §8, camada 1).

Camada pura e testável: recebe o nome original e o conteúdo, aplica limites e
retorna os arquivos validados com nome interno seguro. Nenhum endpoint é
definido aqui (isso pertence às etapas de API do PRD §17).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .files import (
    ArquivoExcedeLimite,
    ArquivoVazio,
    FormatoImagem,
    FormatoNaoPermitido,
    LoteExcedeLimite,
    detectar_formato,
    gerar_nome_interno,
)

_CABECALHO_BYTES = 16


@dataclass(frozen=True)
class LimitesUpload:
    """Limites aplicáveis a um lote de upload."""

    max_arquivo_bytes: int
    max_arquivos: int
    max_total_bytes: int


@dataclass(frozen=True)
class ArquivoRecebido:
    """Arquivo de entrada validado, com nome interno seguro."""

    nome_original: str
    nome_interno: str
    formato: FormatoImagem
    tamanho: int
    conteudo: bytes


def validar_quantidade(quantidade: int, limites: LimitesUpload) -> None:
    if quantidade <= 0:
        raise LoteExcedeLimite("Nenhum arquivo foi enviado.")
    if quantidade > limites.max_arquivos:
        raise LoteExcedeLimite(
            f"O lote excede o máximo de {limites.max_arquivos} arquivos."
        )


def validar_arquivo(
    nome_original: str, conteudo: bytes, *, max_bytes: int
) -> ArquivoRecebido:
    """Valida um único arquivo: não vazio, dentro do limite e com assinatura válida."""
    tamanho = len(conteudo)
    if tamanho == 0:
        raise ArquivoVazio(f'O arquivo "{nome_original}" está vazio.')
    if tamanho > max_bytes:
        raise ArquivoExcedeLimite(
            f'O arquivo "{nome_original}" excede o tamanho máximo permitido.'
        )
    formato = detectar_formato(conteudo[:_CABECALHO_BYTES])
    if formato is None:
        raise FormatoNaoPermitido(
            f'O arquivo "{nome_original}" não é uma imagem JPG, PNG ou WEBP válida.'
        )
    return ArquivoRecebido(
        nome_original=nome_original,
        nome_interno=gerar_nome_interno(formato),
        formato=formato,
        tamanho=tamanho,
        conteudo=conteudo,
    )


def validar_lote(
    entradas: Iterable[tuple[str, bytes]], limites: LimitesUpload
) -> list[ArquivoRecebido]:
    """Valida um lote inteiro: quantidade, tamanho por arquivo e tamanho total."""
    itens = list(entradas)
    validar_quantidade(len(itens), limites)

    total = 0
    validados: list[ArquivoRecebido] = []
    for nome_original, conteudo in itens:
        total += len(conteudo)
        if total > limites.max_total_bytes:
            raise LoteExcedeLimite("O lote excede o tamanho total máximo permitido.")
        validados.append(
            validar_arquivo(
                nome_original, conteudo, max_bytes=limites.max_arquivo_bytes
            )
        )
    return validados
