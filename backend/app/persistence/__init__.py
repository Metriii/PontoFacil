"""Persistência local em JSON (sem banco de dados)."""

from .json_store import DadosCorrompidos, gravar_json, ler_json, ler_json_ou
from .lotes import LoteNaoEncontrado, RepositorioLotes
from .models import (
    ESTADOS_LOTE,
    STATUS_IMAGEM,
    STATUS_VALIDACAO,
    TIPOS_ARQUIVO,
    TIPOS_DIA,
    ArquivoGerado,
    Correcao,
    Duvida,
    FichaPonto,
    Funcionario,
    Imagem,
    Lote,
    Progresso,
    RegistroDiario,
    agora_iso,
)

__all__ = [
    "ESTADOS_LOTE",
    "STATUS_IMAGEM",
    "STATUS_VALIDACAO",
    "TIPOS_ARQUIVO",
    "TIPOS_DIA",
    "ArquivoGerado",
    "Correcao",
    "DadosCorrompidos",
    "Duvida",
    "FichaPonto",
    "Funcionario",
    "Imagem",
    "Lote",
    "LoteNaoEncontrado",
    "Progresso",
    "RegistroDiario",
    "RepositorioLotes",
    "agora_iso",
    "gravar_json",
    "ler_json",
    "ler_json_ou",
]
