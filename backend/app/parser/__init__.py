"""Parser da folha de ponto (etapa 6)."""

from .folha import (
    Colunas,
    FolhaExtraida,
    agrupar_linhas,
    detectar_colunas,
    extrair_campos_cabecalho,
    extrair_funcionario,
    extrair_periodo,
    extrair_registros,
    normalizar,
    parse_folha,
)

__all__ = [
    "Colunas",
    "FolhaExtraida",
    "agrupar_linhas",
    "detectar_colunas",
    "extrair_campos_cabecalho",
    "extrair_funcionario",
    "extrair_periodo",
    "extrair_registros",
    "normalizar",
    "parse_folha",
]
