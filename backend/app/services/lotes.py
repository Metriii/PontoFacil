"""Serviço de lotes: criação, agendamento e correção de registros (etapa 8).

Concentra a orquestração entre segurança (arquivos já validados), armazenamento,
persistência e regras de negócio. Nenhum acesso HTTP direto aqui.
"""

from __future__ import annotations

import secrets

from ..business import CAMPOS_HORARIO, normalizar_horario, validar_ficha
from ..persistence import (
    Correcao,
    Imagem,
    Lote,
    Progresso,
    RegistroDiario,
    RepositorioLotes,
    agora_iso,
)
from ..security import ArquivoRecebido
from ..storage import salvar_imagem
from .execucao import ExecutorLotes
from .processamento import Extrator, processar_imagem, processar_lote


class RegistroNaoEncontrado(Exception):
    """Nenhum registro com o identificador informado."""


class CorrecaoInvalida(Exception):
    """Correção rejeitada (campo ou valor inválido)."""


def _aplicar_correcao(
    registro: RegistroDiario, campo: str, valor: str | None
) -> Correcao:
    novo: str | None = None
    if valor is not None:
        novo = normalizar_horario(valor)
        if novo is None:
            raise CorrecaoInvalida(
                f"Horário inválido para correção: {valor!r}. Use HH:MM."
            )
    anterior = getattr(registro, campo)
    setattr(registro, campo, novo)
    correcao = Correcao(
        correcao_id=secrets.token_hex(8),
        registro_id=registro.registro_id,
        campo=campo,
        corrigido_em=agora_iso(),
        valor_anterior=anterior,
        valor_novo=novo,
        autor="local",
    )
    registro.correcao = correcao
    return correcao


class ServicoLotes:
    """Orquestra criação, processamento em segundo plano e correção de lotes."""

    def __init__(
        self,
        repo: RepositorioLotes,
        executor: ExecutorLotes,
        *,
        extrator: Extrator = processar_imagem,
    ) -> None:
        self.repo = repo
        self.executor = executor
        self.extrator = extrator

    def criar_lote(self, arquivos: list[ArquivoRecebido]) -> Lote:
        """Cria o lote, grava as imagens validadas e marca-o como ``processando``."""
        lote = self.repo.criar()
        for arquivo in arquivos:
            salvar_imagem(
                lote.lote_id,
                arquivo.nome_interno,
                arquivo.conteudo,
                base=self.repo.base,
            )
            self.repo.registrar_imagem(
                lote.lote_id,
                Imagem(
                    imagem_id=secrets.token_hex(8),
                    nome_interno=arquivo.nome_interno,
                    nome_original=arquivo.nome_original,
                    caminho=f"imagens/{arquivo.nome_interno}",
                ),
            )
        return self.repo.atualizar(
            lote.lote_id,
            estado="processando",
            progresso=Progresso(total=len(arquivos)),
        )

    def agendar(self, lote_id: str) -> None:
        """Envia o processamento do lote para execução em segundo plano."""
        self.executor.enviar(
            lote_id,
            lambda: processar_lote(
                lote_id, repo=self.repo, extrator=self.extrator
            ),
        )

    def corrigir_registro(
        self, registro_id: str, *, campo: str, valor: str | None
    ) -> RegistroDiario:
        """Aplica uma correção manual, distinta do resultado original do OCR.

        Grava a correção no histórico (``correcoes.json``), marca o registro como
        ``corrigido`` e revalida as dúvidas do lote afetado.
        """
        if campo not in CAMPOS_HORARIO:
            raise CorrecaoInvalida(f"Campo não corrigível: {campo!r}.")

        for lote in self.repo.listar():
            fichas = self.repo.carregar_fichas(lote.lote_id)
            for ficha in fichas:
                for registro in ficha.registros:
                    if registro.registro_id != registro_id:
                        continue
                    correcao = _aplicar_correcao(registro, campo, valor)
                    self.repo.registrar_correcao(lote.lote_id, correcao)
                    self._revalidar_lote(lote.lote_id, fichas)
                    return registro
        raise RegistroNaoEncontrado(registro_id)

    def _revalidar_lote(self, lote_id: str, fichas) -> None:
        duvidas = []
        for ficha in fichas:
            duvidas.extend(validar_ficha(ficha).duvidas)
            for registro in ficha.registros:
                if registro.correcao is not None:
                    registro.status_validacao = "corrigido"
        self.repo.salvar_fichas(lote_id, fichas)
        self.repo.salvar_duvidas(lote_id, duvidas)
