"""Processamento assíncrono de lotes (etapa 8, RF-004).

Une as camadas já prontas: para cada imagem do lote, lê o arquivo do disco,
executa OCR + parser (via ``extrator``), e depois aplica as regras de negócio
(validação, dúvidas). Erros são isolados por imagem e o progresso é persistido
em ``lote.json`` a cada arquivo.

O OCR só reconhece: nenhum horário é inventado aqui. A coluna "Hora Extra" já é
ignorada pelo parser.
"""

from __future__ import annotations

from collections.abc import Callable

from ..business import validar_ficha
from ..ocr import ErroImagem, TesseractIndisponivel, ler_documento
from ..parser import FolhaExtraida, parse_folha
from ..persistence import (
    FichaPonto,
    Progresso,
    RepositorioLotes,
)
from ..storage import ler_imagem

#: Extrai uma folha estruturada a partir dos bytes de uma imagem.
Extrator = Callable[..., FolhaExtraida]

#: Status de validação que exigem revisão humana.
_STATUS_REVISAO = ("pendente", "invalido")


def processar_imagem(dados: bytes, *, origem: str) -> FolhaExtraida:
    """OCR + parser de uma única imagem (sem regras de negócio)."""
    resultado = ler_documento(dados)
    return parse_folha(resultado, origem=origem)


def _mensagem_erro(exc: Exception) -> str:
    """Mensagem segura (sem caminhos locais nem detalhes internos)."""
    if isinstance(exc, (ErroImagem, TesseractIndisponivel)):
        texto = str(exc).strip()
        if texto:
            return texto
    return "Falha ao processar a imagem."


def _contar_revisao(fichas: list[FichaPonto]) -> int:
    return sum(
        1
        for ficha in fichas
        for registro in ficha.registros
        if registro.status_validacao in _STATUS_REVISAO
    )


def _estado_final(progresso: Progresso) -> str:
    if progresso.total > 0 and progresso.falhas == progresso.total:
        return "falhou"
    if progresso.falhas or progresso.revisao:
        return "concluido_com_pendencias"
    return "concluido"


def processar_lote(
    lote_id: str,
    *,
    repo: RepositorioLotes,
    extrator: Extrator = processar_imagem,
) -> None:
    """Processa todas as imagens de um lote, persistindo progresso e resultados."""
    lote = repo.obter(lote_id)
    progresso = Progresso(total=len(lote.imagens))
    fichas: list[FichaPonto] = []

    for imagem in lote.imagens:
        try:
            dados = ler_imagem(lote_id, imagem.nome_interno, base=repo.base)
            folha = extrator(dados, origem=imagem.nome_interno)
            fichas.append(folha.para_ficha())
            imagem.status = "ok"
            imagem.erro = None
            progresso.processados += 1
        except Exception as exc:  # erro isolado: não interrompe o lote
            imagem.status = "falha"
            imagem.erro = _mensagem_erro(exc)
            progresso.falhas += 1
        lote.progresso = progresso
        repo.salvar(lote)

    duvidas = []
    for ficha in fichas:
        duvidas.extend(validar_ficha(ficha).duvidas)

    progresso.revisao = _contar_revisao(fichas)
    lote.progresso = progresso
    repo.salvar(lote)
    repo.salvar_fichas(lote_id, fichas)
    repo.salvar_duvidas(lote_id, duvidas)
    repo.atualizar(lote_id, estado=_estado_final(progresso), progresso=progresso)
