"""Serviço de exportação Excel e localização de arquivos (etapas 10-11).

Concentra a orquestração da exportação: seleciona os registros exportáveis
(``app.business.exportavel``), gera os ``.xlsx`` em ``<storage>/exports/<lote>/``,
registra os arquivos gerados no lote e resolve, de forma segura, o caminho de
download apenas para arquivos pertencentes ao lote solicitado.
"""

from __future__ import annotations

import re
import secrets
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from ..business.exportavel import registros_exportaveis
from ..exports import gerar_planilha_consolidada, gerar_planilha_funcionario
from ..persistence import ArquivoGerado, FichaPonto, RepositorioLotes, agora_iso
from ..security import exigir_id_lote, resolver_caminho_seguro


class ArquivoNaoEncontrado(Exception):
    """Arquivo gerado inexistente ou que não pertence ao lote solicitado."""


@dataclass
class ResultadoExportacao:
    """Arquivos gerados e total de registros exportados."""

    lote_id: str
    arquivos: list[ArquivoGerado] = field(default_factory=list)
    total_registros: int = 0


def _slug(texto: str | None) -> str:
    bruto = re.sub(r"[^A-Za-z0-9]+", "-", texto or "").strip("-")
    return (bruto[:40] or "funcionario").lower()


def _referencia(ficha: FichaPonto | None) -> str | None:
    if ficha is None or ficha.mes is None or ficha.ano is None:
        return None
    return f"{ficha.ano:04d}-{ficha.mes:02d}"


class ServicoExportacao:
    """Gera planilhas por funcionário e consolidadas, e resolve downloads."""

    def __init__(self, repo: RepositorioLotes) -> None:
        self.repo = repo

    def pasta_exports(self, lote_id: str) -> Path:
        return self.repo.pasta_exports(lote_id)

    def exportar(self, lote_id: str) -> ResultadoExportacao:
        """Gera (ou regenera) as planilhas do lote.

        Política de reexportação explícita: os arquivos anteriores do lote são
        removidos e a lista ``arquivos_gerados`` é substituída, evitando acúmulo
        e mantendo a exportação idempotente em relação ao estado atual.
        """
        self.repo.obter(lote_id)  # LoteNaoEncontrado se não existir
        fichas = self.repo.carregar_fichas(lote_id)
        exportaveis = [
            (ficha, registros_exportaveis(ficha)) for ficha in fichas
        ]
        exportaveis = [
            (ficha, registros) for ficha, registros in exportaveis if registros
        ]
        total = sum(len(registros) for _, registros in exportaveis)
        if total == 0:
            return ResultadoExportacao(lote_id=lote_id)

        pasta = self.pasta_exports(lote_id)
        shutil.rmtree(pasta, ignore_errors=True)
        pasta.mkdir(parents=True, exist_ok=True)

        arquivos: list[ArquivoGerado] = []
        usados: set[str] = set()
        for ficha, _registros in exportaveis:
            nome = self._nome_funcionario(ficha, usados)
            usados.add(nome.lower())
            gerar_planilha_funcionario(ficha, resolver_caminho_seguro(pasta, nome))
            arquivos.append(self._registro(nome, "funcionario", ficha, lote_id))

        nome_consolidado = "consolidado.xlsx"
        gerar_planilha_consolidada(
            [ficha for ficha, _ in exportaveis],
            resolver_caminho_seguro(pasta, nome_consolidado),
        )
        arquivos.append(
            self._registro(nome_consolidado, "consolidado", None, lote_id)
        )

        self.repo.definir_arquivos_gerados(lote_id, arquivos)
        return ResultadoExportacao(
            lote_id=lote_id, arquivos=arquivos, total_registros=total
        )

    def localizar(self, lote_id: str, arquivo_id: str) -> tuple[Path, ArquivoGerado]:
        """Caminho absoluto de um arquivo gerado, garantindo pertencimento ao lote."""
        lote = self.repo.obter(lote_id)
        registro = next(
            (a for a in lote.arquivos_gerados if a.arquivo_id == arquivo_id), None
        )
        if registro is None:
            raise ArquivoNaoEncontrado(arquivo_id)
        raiz = self.repo.base
        destino = resolver_caminho_seguro(raiz, registro.caminho)
        if not destino.is_file():
            raise ArquivoNaoEncontrado(arquivo_id)
        return destino, registro

    def _nome_funcionario(self, ficha: FichaPonto, usados: set[str]) -> str:
        base = (
            f"ponto-{_slug(ficha.funcionario.nome or ficha.funcionario.codigo)}"
            f"-{_referencia(ficha) or 'periodo'}"
        )
        nome = f"{base}.xlsx"
        contador = 2
        while nome.lower() in usados:
            nome = f"{base}-{contador}.xlsx"
            contador += 1
        return nome

    def _registro(
        self,
        nome: str,
        tipo: str,
        ficha: FichaPonto | None,
        lote_id: str,
    ) -> ArquivoGerado:
        funcionario = None
        if ficha is not None:
            funcionario = ficha.funcionario.nome or ficha.funcionario.codigo
        return ArquivoGerado(
            arquivo_id=secrets.token_hex(8),
            nome=nome,
            tipo=tipo,
            caminho=f"exports/{lote_id}/{nome}",
            funcionario=funcionario,
            referencia=_referencia(ficha),
            gerado_em=agora_iso(),
        )
