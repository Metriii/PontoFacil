from app.business import CAMPOS_HORARIO, calcular_ficha, calcular_horas
from app.persistence import FichaPonto, Funcionario, RegistroDiario


def reg(**kwargs) -> RegistroDiario:
    base = {"registro_id": "r1", "dia": 3}
    base.update(kwargs)
    return RegistroDiario(**base)


def test_campos_horario_sem_hora_extra() -> None:
    # A coluna "Hora Extra" está fora do escopo: apenas 4 campos.
    assert CAMPOS_HORARIO == ("entrada", "saida_almoco", "volta_almoco", "saida")


def test_calculo_completo_gera_total_e_segmentos() -> None:
    calculo = calcular_horas(
        reg(entrada="08:00", saida_almoco="13:00", volta_almoco="14:00", saida="17:00")
    )
    assert calculo.confirmado is True
    assert calculo.total_minutos == 480
    assert calculo.total_formatado() == "08:00"
    assert [s.minutos for s in calculo.segmentos] == [300, 180]
    assert (calculo.segmentos[0].inicio, calculo.segmentos[0].fim) == ("08:00", "13:00")


def test_calculo_considera_minutos() -> None:
    calculo = calcular_horas(
        reg(entrada="08:05", saida_almoco="12:00", volta_almoco="13:10", saida="17:55")
    )
    assert calculo.total_minutos == (12 * 60 - 8 * 60 - 5) + (17 * 60 + 55 - 13 * 60 - 10)
    assert calculo.total_formatado() == "08:40"


def test_calculo_dois_horarios_fica_pendente_sem_presumir_intervalo() -> None:
    calculo = calcular_horas(reg(entrada="08:00", saida="17:00"))
    assert calculo.total_minutos is None
    assert calculo.pendencias


def test_calculo_incompleto_fica_pendente() -> None:
    calculo = calcular_horas(reg(entrada="08:00"))
    assert calculo.total_minutos is None
    assert calculo.pendencias


def test_calculo_ordem_nao_crescente_fica_pendente() -> None:
    # Turno noturno / inconsistência: virada de dia não definida, não presumir.
    calculo = calcular_horas(
        reg(entrada="22:00", saida_almoco="02:00", volta_almoco="03:00", saida="06:00")
    )
    assert calculo.total_minutos is None
    assert calculo.pendencias


def test_calculo_horario_invalido_fica_pendente() -> None:
    calculo = calcular_horas(reg(entrada="8:00", saida="17:00"))
    assert calculo.total_minutos is None
    assert calculo.pendencias


def test_calculo_nao_confirma_igualdade_de_marcas() -> None:
    calculo = calcular_horas(
        reg(entrada="08:00", saida_almoco="08:00", volta_almoco="12:00", saida="17:00")
    )
    assert calculo.total_minutos is None
    assert calculo.pendencias


def test_calcular_ficha_soma_apenas_confirmados() -> None:
    ficha = FichaPonto(
        funcionario=Funcionario(funcionario_id="f1", nome="ALESSANY"),
        mes=8,
        ano=2026,
        registros=[
            reg(
                registro_id="a",
                dia=3,
                entrada="08:00",
                saida_almoco="12:00",
                volta_almoco="13:00",
                saida="17:00",
            ),
            reg(registro_id="b", dia=4, entrada="08:00", saida="12:00"),
        ],
    )
    resumo = calcular_ficha(ficha)
    assert resumo.total_confirmado_minutos == 480
    assert resumo.total_confirmado == "08:00"
    assert resumo.registros_pendentes == 1
