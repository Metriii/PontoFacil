"""Repositório de lotes persistidos em JSON (ARQUITETURA §5).

Um diretório por lote em ``<storage>/lotes/<lote_id>/``:

- ``lote.json``      — metadados, estado, progresso, imagens e arquivos gerados.
- ``registros.json`` — fichas de ponto (funcionário + período + registros).
- ``duvidas.json``   — pendências do lote.
- ``correcoes.json`` — correções manuais aplicadas.
- ``imagens/``       — arquivos de imagem de entrada (nome interno).
"""

from __future__ import annotations

from pathlib import Path

from ..config import settings
from ..security.files import exigir_id_lote, gerar_id_lote, resolver_caminho_seguro
from .json_store import DadosCorrompidos, gravar_json, ler_json, ler_json_ou
from .models import (
    ESTADOS_LOTE,
    ArquivoGerado,
    Correcao,
    Duvida,
    FichaPonto,
    Imagem,
    Lote,
    Progresso,
    agora_iso,
)


class LoteNaoEncontrado(Exception):
    """Lote solicitado não existe no armazenamento local."""


class RepositorioLotes:
    def __init__(self, base: Path | None = None) -> None:
        self.base = (base if base is not None else settings.storage_dir).resolve()

    def _pasta_lote(self, lote_id: str) -> Path:
        exigir_id_lote(lote_id)
        return resolver_caminho_seguro(self.base / "lotes", lote_id)

    def _caminho(self, lote_id: str, arquivo: str) -> Path:
        return resolver_caminho_seguro(self._pasta_lote(lote_id), arquivo)

    def caminho_imagens(self, lote_id: str) -> Path:
        return self._caminho(lote_id, "imagens")

    def criar(self) -> Lote:
        lote_id = gerar_id_lote()
        self._caminho(lote_id, "imagens").mkdir(parents=True, exist_ok=True)
        lote = Lote(
            lote_id=lote_id,
            criado_em=agora_iso(),
            estado="recebido",
            progresso=Progresso(),
        )
        self.salvar(lote)
        return lote

    def salvar(self, lote: Lote) -> None:
        gravar_json(self._caminho(lote.lote_id, "lote.json"), lote.para_dict())

    def obter(self, lote_id: str) -> Lote:
        try:
            dados = ler_json(self._caminho(lote_id, "lote.json"))
        except FileNotFoundError as exc:
            raise LoteNaoEncontrado(lote_id) from exc
        return Lote.de_dict(dados)

    def listar(self) -> list[Lote]:
        raiz = self.base / "lotes"
        if not raiz.exists():
            return []
        lotes: list[Lote] = []
        for pasta in sorted(raiz.iterdir()):
            if not pasta.is_dir():
                continue
            try:
                lotes.append(self.obter(pasta.name))
            except (LoteNaoEncontrado, DadosCorrompidos):
                continue
        return lotes

    def atualizar(
        self,
        lote_id: str,
        *,
        estado: str | None = None,
        progresso: Progresso | None = None,
    ) -> Lote:
        lote = self.obter(lote_id)
        if estado is not None:
            if estado not in ESTADOS_LOTE:
                raise ValueError(f"Estado de lote inválido: {estado}")
            lote.estado = estado
        if progresso is not None:
            lote.progresso = progresso
        self.salvar(lote)
        return lote

    def registrar_imagem(self, lote_id: str, imagem: Imagem) -> Lote:
        lote = self.obter(lote_id)
        lote.imagens.append(imagem)
        self.salvar(lote)
        return lote

    def registrar_arquivo_gerado(
        self, lote_id: str, arquivo: ArquivoGerado
    ) -> Lote:
        lote = self.obter(lote_id)
        lote.arquivos_gerados.append(arquivo)
        self.salvar(lote)
        return lote

    def salvar_fichas(self, lote_id: str, fichas: list[FichaPonto]) -> None:
        gravar_json(
            self._caminho(lote_id, "registros.json"),
            [ficha.para_dict() for ficha in fichas],
        )

    def carregar_fichas(self, lote_id: str) -> list[FichaPonto]:
        dados = ler_json_ou(self._caminho(lote_id, "registros.json"), [])
        return [FichaPonto.de_dict(item) for item in dados]

    def salvar_duvidas(self, lote_id: str, duvidas: list[Duvida]) -> None:
        gravar_json(
            self._caminho(lote_id, "duvidas.json"),
            [duvida.para_dict() for duvida in duvidas],
        )

    def carregar_duvidas(self, lote_id: str) -> list[Duvida]:
        dados = ler_json_ou(self._caminho(lote_id, "duvidas.json"), [])
        return [Duvida.de_dict(item) for item in dados]

    def salvar_correcoes(self, lote_id: str, correcoes: list[Correcao]) -> None:
        gravar_json(
            self._caminho(lote_id, "correcoes.json"),
            [correcao.para_dict() for correcao in correcoes],
        )

    def carregar_correcoes(self, lote_id: str) -> list[Correcao]:
        dados = ler_json_ou(self._caminho(lote_id, "correcoes.json"), [])
        return [Correcao.de_dict(item) for item in dados]

    def registrar_correcao(self, lote_id: str, correcao: Correcao) -> list[Correcao]:
        correcoes = self.carregar_correcoes(lote_id)
        correcoes.append(correcao)
        self.salvar_correcoes(lote_id, correcoes)
        return correcoes
