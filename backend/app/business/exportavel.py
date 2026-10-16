"""Seleção de registros exportáveis (RF-012, PRD §8 regras 7 e 9).

Somente registros **confirmados** ou **corrigidos e validados** podem entrar na
planilha. Registros pendentes/inválidos nunca são exportados como se fossem
confirmados, e nenhum horário é inventado: dias sem marcação só são exportados
quando o tipo de dia é reconhecido (fim de semana, feriado, férias), com as
batidas em branco e sem total.

Este módulo é puro e independente do OCR (RNF-008/RNF-010).
"""

from __future__ import annotations

from ..persistence.models import FichaPonto, RegistroDiario
from .calculo import CAMPOS_HORARIO, calcular_horas

#: Status de validação aceitos para exportação.
STATUS_EXPORTAVEIS = ("confirmado", "corrigido")

#: Tipos de dia sem marcação cuja ausência de batidas é legítima (não inventa nada).
_TIPOS_SEM_MARCACAO = ("fim_de_semana", "feriado", "ferias")


def registro_exportavel(registro: RegistroDiario) -> bool:
    """Indica se um registro pode ser exportado sem inventar dados.

    - ``confirmado``/``corrigido`` **e** jornada confirmada pelo cálculo, ou
    - dia sem marcação com tipo de dia reconhecido (sem horários nem total).
    """
    if registro.status_validacao not in STATUS_EXPORTAVEIS:
        return False

    if calcular_horas(registro).confirmado:
        return True

    tem_marcacao = any(
        getattr(registro, campo) is not None for campo in CAMPOS_HORARIO
    )
    return not tem_marcacao and registro.tipo_dia in _TIPOS_SEM_MARCACAO


def registros_exportaveis(ficha: FichaPonto) -> list[RegistroDiario]:
    """Registros exportáveis de uma ficha, na ordem original."""
    return [registro for registro in ficha.registros if registro_exportavel(registro)]
