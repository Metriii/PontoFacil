"""Regras de negócio (etapa 7): validação, dúvidas e cálculo de horas.

Funções puras e testáveis, independentes do OCR (PRD §8, RNF-008/RNF-010).
"""

from .calculo import (
    CAMPOS_HORARIO,
    CalculoHoras,
    CalculoRegistro,
    ResumoFicha,
    Segmento,
    calcular_ficha,
    calcular_horas,
)
from .exportavel import (
    STATUS_EXPORTAVEIS,
    registro_exportavel,
    registros_exportaveis,
)
from .horarios import (
    HORARIO_RE,
    formatar_duracao,
    horario_valido,
    minutos_do_dia,
    normalizar_horario,
)
from .validacao import (
    ResultadoValidacao,
    validar_ficha,
    validar_fichas,
    validar_registro,
)

__all__ = [
    "CAMPOS_HORARIO",
    "HORARIO_RE",
    "STATUS_EXPORTAVEIS",
    "CalculoHoras",
    "CalculoRegistro",
    "ResumoFicha",
    "ResultadoValidacao",
    "Segmento",
    "calcular_ficha",
    "calcular_horas",
    "formatar_duracao",
    "horario_valido",
    "minutos_do_dia",
    "normalizar_horario",
    "registro_exportavel",
    "registros_exportaveis",
    "validar_ficha",
    "validar_fichas",
    "validar_registro",
]
