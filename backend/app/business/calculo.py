"""Cálculo de horas trabalhadas (etapa 7, PRD §8 regra 3 e RF-010).

Regras aplicadas (determinísticas e rastreáveis):

- Considera apenas horários existentes e já normalizados (``HH:MM``).
- Uma jornada só gera **total confirmado** quando as quatro marcações estão
  presentes e em ordem crescente: ``entrada < saida_almoco < volta_almoco < saida``.
  Nesse caso o total é a soma de dois segmentos (antes e depois do intervalo).
- **Não presume intervalo:** uma jornada com apenas ``entrada`` e ``saida``
  fica pendente (a regra de intervalo padrão ainda depende de definição — PRD §8/§16).
- Registros incompletos ou com ordem não crescente ficam pendentes; nenhum total
  é confirmado. A virada de dia (turno noturno) só será tratada quando a regra
  aplicável estiver definida, por isso não é presumida.
- Nenhuma tolerância, arredondamento, hora extra ou regra trabalhista é aplicada.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..persistence.models import FichaPonto, RegistroDiario
from .horarios import (
    formatar_duracao,
    horario_valido,
    minutos_do_dia,
)

#: Campos de horário na ordem cronológica esperada da folha.
CAMPOS_HORARIO = ("entrada", "saida_almoco", "volta_almoco", "saida")

_MOTIVO_INTERVALO = (
    "Jornada sem marcação de intervalo; regra de intervalo pendente de definição."
)
_MOTIVO_INCOMPLETO = "Registro incompleto para cálculo das horas."
_MOTIVO_ORDEM = (
    "Ordem dos horários não crescente; verificar inconsistência ou virada de dia "
    "(regra de virada de dia não definida)."
)
_MOTIVO_INVALIDO = "Horário inválido presente no registro."


@dataclass
class Segmento:
    """Trecho trabalhado entre dois horários, para rastreabilidade."""

    inicio: str
    fim: str
    minutos: int


@dataclass
class CalculoHoras:
    """Resultado do cálculo de um registro diário."""

    total_minutos: int | None = None
    segmentos: list[Segmento] = field(default_factory=list)
    pendencias: list[str] = field(default_factory=list)

    @property
    def confirmado(self) -> bool:
        return self.total_minutos is not None and not self.pendencias

    def total_formatado(self) -> str | None:
        if self.total_minutos is None:
            return None
        return formatar_duracao(self.total_minutos)


def _segmento(inicio: str, fim: str) -> Segmento:
    return Segmento(
        inicio=inicio, fim=fim, minutos=minutos_do_dia(fim) - minutos_do_dia(inicio)
    )


def calcular_horas(registro: RegistroDiario) -> CalculoHoras:
    """Calcula as horas de um registro diário sem inventar dados.

    Retorna um :class:`CalculoHoras`; quando o total não pode ser confirmado,
    ``total_minutos`` é ``None`` e ``pendencias`` explica o motivo.
    """
    valores = {campo: getattr(registro, campo) for campo in CAMPOS_HORARIO}
    presentes = {c: v for c, v in valores.items() if v is not None}

    if any(not horario_valido(v) for v in presentes.values()):
        return CalculoHoras(pendencias=[_MOTIVO_INVALIDO])

    entrada = valores["entrada"]
    saida_almoco = valores["saida_almoco"]
    volta_almoco = valores["volta_almoco"]
    saida = valores["saida"]

    if len(presentes) == 4:
        if not (entrada < saida_almoco < volta_almoco < saida):
            return CalculoHoras(pendencias=[_MOTIVO_ORDEM])
        segmento_manha = _segmento(entrada, saida_almoco)
        segmento_tarde = _segmento(volta_almoco, saida)
        total = segmento_manha.minutos + segmento_tarde.minutos
        return CalculoHoras(
            total_minutos=total,
            segmentos=[segmento_manha, segmento_tarde],
            pendencias=[],
        )

    if entrada is not None and saida is not None and not any(
        v is not None for c, v in presentes.items() if c not in ("entrada", "saida")
    ):
        return CalculoHoras(pendencias=[_MOTIVO_INTERVALO])

    return CalculoHoras(pendencias=[_MOTIVO_INCOMPLETO])


@dataclass
class CalculoRegistro:
    registro: RegistroDiario
    calculo: CalculoHoras


@dataclass
class ResumoFicha:
    """Cálculos por registro e totais confirmados de uma ficha."""

    por_registro: list[CalculoRegistro] = field(default_factory=list)

    @property
    def total_confirmado_minutos(self) -> int:
        return sum(
            item.calculo.total_minutos or 0
            for item in self.por_registro
            if item.calculo.confirmado
        )

    @property
    def total_confirmado(self) -> str:
        return formatar_duracao(self.total_confirmado_minutos)

    @property
    def registros_pendentes(self) -> int:
        return sum(1 for item in self.por_registro if not item.calculo.confirmado)


def calcular_ficha(ficha: FichaPonto) -> ResumoFicha:
    """Calcula as horas de todos os registros de uma ficha."""
    return ResumoFicha(
        por_registro=[
            CalculoRegistro(registro=r, calculo=calcular_horas(r))
            for r in ficha.registros
        ]
    )
