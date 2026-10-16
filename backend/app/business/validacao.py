"""Validação de registros diários e detecção de dúvidas (etapa 7, RF-008).

Regras (PRD §8):

- Um horário ausente ou ilegível é representado como ``None`` e gera uma
  :class:`Duvida` — nunca é interpretado como folga/falta/ausência.
- Registros incompletos são marcados para revisão; não produzem total confirmado.
- Correções ainda não existem aqui: apenas o status do OCR é avaliado.
- A coluna **"Hora Extra"** está fora do escopo: só os quatro campos de
  :data:`~app.business.calculo.CAMPOS_HORARIO` são considerados.

O módulo é puro e independente do OCR; apenas lê/produz os modelos persistidos.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass, field

from ..persistence.models import (
    STATUS_VALIDACAO,
    Duvida,
    FichaPonto,
    RegistroDiario,
)
from .calculo import CAMPOS_HORARIO, calcular_horas
from .horarios import horario_valido

#: Tipos de dia em que a ausência de marcações não gera dúvida por si só.
_TIPOS_SEM_MARCACAO = ("fim_de_semana", "feriado", "ferias")


def _nova_duvida(
    registro: RegistroDiario,
    campo: str,
    motivo: str,
    origem: str | None,
) -> Duvida:
    return Duvida(
        duvida_id=secrets.token_hex(8),
        registro_id=registro.registro_id,
        campo=campo,
        motivo=motivo,
        origem=origem if origem is not None else registro.origem,
    )


def _nova_duvida_ficha(campo: str, motivo: str) -> Duvida:
    return Duvida(
        duvida_id=secrets.token_hex(8),
        registro_id="",
        campo=campo,
        motivo=motivo,
        origem=None,
    )


def validar_registro(
    registro: RegistroDiario, *, origem: str | None = None
) -> list[Duvida]:
    """Valida um registro diário, atualiza seu status e retorna suas dúvidas.

    Efeitos colaterais em ``registro``: ``status_validacao`` e, quando aplicável,
    ``observacao``. Nenhum horário é criado, alterado ou completado.
    """
    valores = {campo: getattr(registro, campo) for campo in CAMPOS_HORARIO}
    presentes = {c: v for c, v in valores.items() if v is not None}

    invalidos = [c for c, v in presentes.items() if not horario_valido(v)]
    if invalidos:
        registro.status_validacao = "invalido"
        return [
            _nova_duvida(registro, campo, "Horário em formato inválido.", origem)
            for campo in invalidos
        ]

    ilegiveis = [
        campo
        for campo in CAMPOS_HORARIO
        if valores[campo] is None and registro.valor_bruto.get(campo)
    ]
    duvidas = [
        _nova_duvida(
            registro,
            campo,
            f"Horário ilegível: {registro.valor_bruto.get(campo)!r}.",
            origem,
        )
        for campo in ilegiveis
    ]

    if not presentes and not ilegiveis:
        if registro.tipo_dia in _TIPOS_SEM_MARCACAO:
            registro.status_validacao = "confirmado"
            registro.observacao = (
                registro.observacao
                or f"Sem marcações (tipo de dia reconhecido: {registro.tipo_dia})."
            )
            return []
        registro.status_validacao = "pendente"
        duvidas.append(
            _nova_duvida(
                registro, "registro", "Nenhum horário reconhecido para o dia.", origem
            )
        )
        return duvidas

    # Jornada apenas com entrada e saída: intervalo não informado (regra pendente).
    if set(presentes) == {"entrada", "saida"} and not ilegiveis:
        registro.status_validacao = "pendente"
        duvidas.append(
            _nova_duvida(
                registro,
                "intervalo",
                "Jornada sem marcação de intervalo; regra de intervalo "
                "pendente de definição.",
                origem,
            )
        )
        return duvidas

    if len(presentes) == len(CAMPOS_HORARIO):
        calculo = calcular_horas(registro)
        if calculo.pendencias:
            registro.status_validacao = "pendente"
            duvidas.extend(
                _nova_duvida(registro, "registro", motivo, origem)
                for motivo in calculo.pendencias
            )
        else:
            registro.status_validacao = "confirmado"
        return duvidas

    faltando = [
        campo
        for campo in CAMPOS_HORARIO
        if valores[campo] is None and not registro.valor_bruto.get(campo)
    ]
    for campo in faltando:
        duvidas.append(_nova_duvida(registro, campo, "Horário ausente.", origem))
    registro.status_validacao = "pendente"
    return duvidas


@dataclass
class ResultadoValidacao:
    """Dúvidas encontradas em uma ficha e contagem por status."""

    ficha: FichaPonto
    duvidas: list[Duvida] = field(default_factory=list)

    def contagem_status(self) -> dict[str, int]:
        contagem = {status: 0 for status in STATUS_VALIDACAO}
        for registro in self.ficha.registros:
            contagem[registro.status_validacao] = (
                contagem.get(registro.status_validacao, 0) + 1
            )
        return contagem

    @property
    def tem_pendencias(self) -> bool:
        return any(
            registro.status_validacao in ("pendente", "invalido")
            for registro in self.ficha.registros
        ) or any(d.registro_id == "" for d in self.duvidas)


def validar_ficha(ficha: FichaPonto) -> ResultadoValidacao:
    """Valida todos os registros de uma ficha e o cabeçalho (período/funcionário)."""
    duvidas: list[Duvida] = []
    if ficha.mes is None or ficha.ano is None:
        duvidas.append(
            _nova_duvida_ficha("periodo", "Período (mês/ano) não reconhecido.")
        )
    if ficha.funcionario.nome is None:
        duvidas.append(
            _nova_duvida_ficha("funcionario", "Funcionário não reconhecido.")
        )
    for registro in ficha.registros:
        duvidas.extend(validar_registro(registro))
    return ResultadoValidacao(ficha=ficha, duvidas=duvidas)


def validar_fichas(fichas: list[FichaPonto]) -> list[ResultadoValidacao]:
    """Valida várias fichas, retornando um resultado por ficha."""
    return [validar_ficha(ficha) for ficha in fichas]
