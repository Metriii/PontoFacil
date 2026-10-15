"""Camada de segurança do PontoFácil (CONTEXT §8)."""

from .files import (
    ArquivoExcedeLimite,
    ArquivoVazio,
    CaminhoInseguro,
    ErroUpload,
    FormatoImagem,
    FormatoNaoPermitido,
    LoteExcedeLimite,
    detectar_formato,
    exigir_id_lote,
    extensao,
    gerar_id_lote,
    gerar_nome_interno,
    resolver_caminho_seguro,
    validar_id_lote,
)
from .upload import (
    ArquivoRecebido,
    LimitesUpload,
    validar_arquivo,
    validar_lote,
    validar_quantidade,
)

__all__ = [
    "ArquivoExcedeLimite",
    "ArquivoRecebido",
    "ArquivoVazio",
    "CaminhoInseguro",
    "ErroUpload",
    "FormatoImagem",
    "FormatoNaoPermitido",
    "LimitesUpload",
    "LoteExcedeLimite",
    "detectar_formato",
    "exigir_id_lote",
    "extensao",
    "gerar_id_lote",
    "gerar_nome_interno",
    "resolver_caminho_seguro",
    "validar_arquivo",
    "validar_id_lote",
    "validar_lote",
    "validar_quantidade",
]
