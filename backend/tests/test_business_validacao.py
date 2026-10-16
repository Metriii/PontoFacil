from app.business import (
    validar_ficha,
    validar_fichas,
    validar_registro,
)
from app.persistence import FichaPonto, Funcionario, RegistroDiario


def reg(**kwargs) -> RegistroDiario:
    base = {"registro_id": "r1", "dia": 3, "tipo_dia": "util"}
    base.update(kwargs)
    return RegistroDiario(**base)


def ficha(registros, **kwargs) -> FichaPonto:
    base = {
        "funcionario": Funcionario(funcionario_id="f1", nome="ALESSANY", codigo="007"),
        "mes": 8,
        "ano": 2026,
        "registros": registros,
    }
    base.update(kwargs)
    return FichaPonto(**base)


def test_registro_completo_confirmado_sem_duvidas() -> None:
    registro = reg(
        entrada="08:00", saida_almoco="12:00", volta_almoco="13:00", saida="17:00"
    )
    duvidas = validar_registro(registro)
    assert registro.status_validacao == "confirmado"
    assert duvidas == []


def test_dia_util_sem_marcacoes_fica_pendente() -> None:
    registro = reg()
    duvidas = validar_registro(registro)
    assert registro.status_validacao == "pendente"
    assert len(duvidas) == 1
    assert duvidas[0].campo == "registro"


def test_fim_de_semana_sem_marcacoes_nao_gera_duvida() -> None:
    registro = reg(tipo_dia="fim_de_semana")
    duvidas = validar_registro(registro)
    assert registro.status_validacao == "confirmado"
    assert duvidas == []
    assert registro.observacao is not None
    # Não inventa horários: continuam nulos.
    assert (registro.entrada, registro.saida) == (None, None)


def test_horario_ausente_gera_duvida_sem_inventar() -> None:
    registro = reg(entrada="08:00", saida_almoco="12:00", volta_almoco="13:00")
    duvidas = validar_registro(registro)
    assert registro.status_validacao == "pendente"
    assert registro.saida is None
    assert any(d.campo == "saida" and "ausente" in d.motivo.lower() for d in duvidas)


def test_horario_ilegivel_gera_duvida() -> None:
    registro = reg(
        entrada="08:00",
        saida_almoco="12:00",
        volta_almoco="13:00",
        saida=None,
        valor_bruto={"saida": "O8:OO"},
    )
    duvidas = validar_registro(registro)
    assert registro.status_validacao == "pendente"
    assert registro.saida is None
    assert any(d.campo == "saida" and "ilegível" in d.motivo for d in duvidas)


def test_dois_horarios_gera_duvida_de_intervalo() -> None:
    registro = reg(entrada="08:00", saida="17:00")
    duvidas = validar_registro(registro)
    assert registro.status_validacao == "pendente"
    assert any(d.campo == "intervalo" for d in duvidas)


def test_horario_formato_invalido_marca_invalido() -> None:
    registro = reg(
        entrada="8:00", saida_almoco="12:00", volta_almoco="13:00", saida="17:00"
    )
    duvidas = validar_registro(registro)
    assert registro.status_validacao == "invalido"
    assert any(d.campo == "entrada" for d in duvidas)


def test_validar_ficha_acumula_duvidas_e_status() -> None:
    resultado = validar_ficha(
        ficha(
            [
                reg(
                    registro_id="a",
                    dia=3,
                    entrada="08:00",
                    saida_almoco="12:00",
                    volta_almoco="13:00",
                    saida="17:00",
                ),
                reg(registro_id="b", dia=4),
            ]
        )
    )
    assert resultado.ficha.registros[0].status_validacao == "confirmado"
    assert resultado.ficha.registros[1].status_validacao == "pendente"
    assert resultado.contagem_status()["confirmado"] == 1
    assert resultado.contagem_status()["pendente"] == 1
    assert resultado.tem_pendencias is True


def test_validar_ficha_sem_periodo_e_funcionario() -> None:
    resultado = validar_ficha(
        ficha(
            [reg(entrada="08:00", saida="17:00")],
            funcionario=Funcionario(funcionario_id="f1"),
            mes=None,
            ano=None,
        )
    )
    campos_ficha = {d.campo for d in resultado.duvidas if d.registro_id == ""}
    assert campos_ficha == {"periodo", "funcionario"}


def test_validar_fichas_em_lote() -> None:
    resultados = validar_fichas(
        [
            ficha([reg(registro_id="a", dia=3)], funcionario=Funcionario("f1", "A")),
            ficha([reg(registro_id="b", dia=4)], funcionario=Funcionario("f2", "B")),
        ]
    )
    assert len(resultados) == 2
    assert all(r.tem_pendencias for r in resultados)
