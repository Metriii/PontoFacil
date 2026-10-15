"""Modelos persistidos em JSON (PRD §9).

Os *timestamps* são armazenados como strings ISO-8601 para manter a
serialização simples e estável, sem dependência de bibliotecas externas.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

ESTADOS_LOTE = (
    "recebido",
    "processando",
    "concluido",
    "concluido_com_pendencias",
    "falhou",
)
STATUS_IMAGEM = ("ok", "falha", "ignorada")
STATUS_VALIDACAO = ("pendente", "confirmado", "corrigido", "invalido")
TIPOS_DIA = ("util", "fim_de_semana", "feriado", "ferias")
TIPOS_ARQUIVO = ("funcionario", "consolidado", "pendencias")


def agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class _Serializavel:
    def para_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Progresso(_Serializavel):
    total: int = 0
    processados: int = 0
    falhas: int = 0
    revisao: int = 0

    @classmethod
    def de_dict(cls, dados: dict[str, Any]) -> "Progresso":
        return cls(**dados)


@dataclass
class Imagem(_Serializavel):
    imagem_id: str
    nome_interno: str
    nome_original: str
    caminho: str
    status: str = "ok"
    erro: str | None = None

    @classmethod
    def de_dict(cls, dados: dict[str, Any]) -> "Imagem":
        return cls(**dados)


@dataclass
class ArquivoGerado(_Serializavel):
    arquivo_id: str
    nome: str
    tipo: str
    caminho: str
    funcionario: str | None = None
    referencia: str | None = None
    gerado_em: str = field(default_factory=agora_iso)

    @classmethod
    def de_dict(cls, dados: dict[str, Any]) -> "ArquivoGerado":
        return cls(**dados)


@dataclass
class Correcao(_Serializavel):
    correcao_id: str
    registro_id: str
    campo: str
    corrigido_em: str
    valor_anterior: str | None = None
    valor_novo: str | None = None
    autor: str | None = None

    @classmethod
    def de_dict(cls, dados: dict[str, Any]) -> "Correcao":
        return cls(**dados)


@dataclass
class Duvida(_Serializavel):
    duvida_id: str
    registro_id: str
    campo: str
    motivo: str
    origem: str | None = None

    @classmethod
    def de_dict(cls, dados: dict[str, Any]) -> "Duvida":
        return cls(**dados)


@dataclass
class RegistroDiario(_Serializavel):
    registro_id: str
    dia: int | None = None
    dia_semana: str | None = None
    entrada: str | None = None
    saida_almoco: str | None = None
    volta_almoco: str | None = None
    saida: str | None = None
    tipo_dia: str | None = None
    status_validacao: str = "pendente"
    confianca: float | None = None
    valor_bruto: dict[str, Any] = field(default_factory=dict)
    observacao: str | None = None
    origem: str | None = None
    correcao: "Correcao | None" = None

    @classmethod
    def de_dict(cls, dados: dict[str, Any]) -> "RegistroDiario":
        valores = dict(dados)
        correcao = valores.get("correcao")
        valores["correcao"] = Correcao.de_dict(correcao) if correcao else None
        return cls(**valores)


@dataclass
class Funcionario(_Serializavel):
    funcionario_id: str
    nome: str | None = None
    codigo: str | None = None
    empresa: str | None = None
    departamento: str | None = None
    funcao: str | None = None

    @classmethod
    def de_dict(cls, dados: dict[str, Any]) -> "Funcionario":
        return cls(**dados)


@dataclass
class FichaPonto(_Serializavel):
    funcionario: Funcionario
    mes: int | None = None
    ano: int | None = None
    registros: list[RegistroDiario] = field(default_factory=list)

    @classmethod
    def de_dict(cls, dados: dict[str, Any]) -> "FichaPonto":
        valores = dict(dados)
        valores["funcionario"] = Funcionario.de_dict(valores["funcionario"])
        valores["registros"] = [
            RegistroDiario.de_dict(r) for r in valores.get("registros", [])
        ]
        return cls(**valores)


@dataclass
class Lote(_Serializavel):
    lote_id: str
    criado_em: str
    estado: str
    progresso: Progresso = field(default_factory=Progresso)
    imagens: list[Imagem] = field(default_factory=list)
    arquivos_gerados: list[ArquivoGerado] = field(default_factory=list)

    @classmethod
    def de_dict(cls, dados: dict[str, Any]) -> "Lote":
        valores = dict(dados)
        valores["progresso"] = Progresso.de_dict(valores.get("progresso", {}))
        valores["imagens"] = [
            Imagem.de_dict(i) for i in valores.get("imagens", [])
        ]
        valores["arquivos_gerados"] = [
            ArquivoGerado.de_dict(a) for a in valores.get("arquivos_gerados", [])
        ]
        return cls(**valores)
