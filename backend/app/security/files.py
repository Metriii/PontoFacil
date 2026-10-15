"""Primitivas de segurança para arquivos de entrada (CONTEXT §8, camada 1).

Responsabilidades: detectar o formato real pela assinatura (magic bytes), gerar
identificadores e nomes internos seguros e resolver caminhos sem permitir
travessia de diretório.
"""

from __future__ import annotations

import re
import secrets
from enum import Enum
from pathlib import Path

ID_LOTE_RE = re.compile(r"^[0-9a-f]{32}$")


class ErroUpload(Exception):
    """Erro de validação de upload, mapeável para uma resposta HTTP 4xx."""

    codigo = "upload_invalido"

    def __init__(self, mensagem: str) -> None:
        super().__init__(mensagem)
        self.mensagem = mensagem


class FormatoNaoPermitido(ErroUpload):
    codigo = "formato_nao_permitido"


class ArquivoVazio(ErroUpload):
    codigo = "arquivo_vazio"


class ArquivoExcedeLimite(ErroUpload):
    codigo = "arquivo_excede_limite"


class LoteExcedeLimite(ErroUpload):
    codigo = "lote_excede_limite"


class CaminhoInseguro(ErroUpload):
    codigo = "caminho_inseguro"


class FormatoImagem(str, Enum):
    JPEG = "jpeg"
    PNG = "png"
    WEBP = "webp"


_EXTENSOES: dict[FormatoImagem, str] = {
    FormatoImagem.JPEG: ".jpg",
    FormatoImagem.PNG: ".png",
    FormatoImagem.WEBP: ".webp",
}

_ASSINATURA_JPEG = b"\xff\xd8\xff"
_ASSINATURA_PNG = b"\x89PNG\r\n\x1a\n"


def extensao(formato: FormatoImagem) -> str:
    """Extensão de arquivo associada ao formato detectado."""
    return _EXTENSOES[formato]


def detectar_formato(cabecalho: bytes) -> FormatoImagem | None:
    """Detecta o formato pela assinatura real, e não pela extensão informada."""
    if cabecalho.startswith(_ASSINATURA_PNG):
        return FormatoImagem.PNG
    if cabecalho.startswith(_ASSINATURA_JPEG):
        return FormatoImagem.JPEG
    if len(cabecalho) >= 12 and cabecalho[:4] == b"RIFF" and cabecalho[8:12] == b"WEBP":
        return FormatoImagem.WEBP
    return None


def gerar_id_lote() -> str:
    """Gera um identificador de lote opaco (nunca derivado da entrada do usuário)."""
    return secrets.token_hex(16)


def gerar_nome_interno(formato: FormatoImagem) -> str:
    """Gera um nome de arquivo interno seguro, com extensão do formato real."""
    return f"{secrets.token_hex(16)}{extensao(formato)}"


def validar_id_lote(lote_id: str) -> bool:
    return bool(ID_LOTE_RE.fullmatch(lote_id or ""))


def exigir_id_lote(lote_id: str) -> str:
    if not validar_id_lote(lote_id):
        raise CaminhoInseguro("Identificador de lote inválido.")
    return lote_id


def resolver_caminho_seguro(base: Path, *partes: str) -> Path:
    """Resolve ``base / partes`` garantindo que o alvo permaneça dentro de ``base``."""
    raiz = base.resolve()
    alvo = raiz.joinpath(*partes).resolve()
    if not alvo.is_relative_to(raiz):
        raise CaminhoInseguro("Caminho resultante fora do diretório permitido.")
    return alvo
