import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient

from backend.main import app
from backend.processador import PROCESSAMENTOS
from backend.schemas import ProcessamentoStatus, ResultadoProcessamento, Registro

client = TestClient(app)


def _criar_processamento_com_registro():
    pid = "test-revisao-1"
    reg = Registro(
        id="reg-1",
        funcionario="João",
        data="2026-09-15",
        dia_semana="ter",
        entrada="08:00",
        saida_almoco=None,
        volta_almoco=None,
        saida=None,
        confianca=0.3,
        revisar=True,
    )
    status = ProcessamentoStatus(
        id=pid,
        status="concluido",
        resultado=ResultadoProcessamento(
            total_cartoes=1,
            processados=1,
            registros=[reg],
            planilhas=[],
        ),
    )
    PROCESSAMENTOS[pid] = status
    return pid, reg


def test_patch_registro_valido():
    pid, reg = _criar_processamento_com_registro()
    resp = client.patch(f"/api/registros/{reg.id}", json={"campo": "saida_almoco", "valor": "12:00"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_patch_registro_horario_invalido():
    pid, reg = _criar_processamento_com_registro()
    resp = client.patch(f"/api/registros/{reg.id}", json={"campo": "entrada", "valor": "25:00"})
    assert resp.status_code == 422


def test_patch_registro_nao_encontrado():
    resp = client.patch("/api/registros/inexistente", json={"campo": "entrada", "valor": "08:00"})
    assert resp.status_code == 404


def test_patch_registro_campo_invalido():
    pid, reg = _criar_processamento_com_registro()
    resp = client.patch(f"/api/registros/{reg.id}", json={"campo": "campo_invalido", "valor": "x"})
    assert resp.status_code == 422


def test_listar_duvidas():
    pid, reg = _criar_processamento_com_registro()
    resp = client.get(f"/api/processamentos/{pid}/duvidas")
    assert resp.status_code == 200
    data = resp.json()
    assert "duvidas" in data
    assert len(data["duvidas"]) > 0


def test_listar_duvidas_processamento_inexistente():
    resp = client.get("/api/processamentos/inexistente/duvidas")
    assert resp.status_code == 404


def test_listar_duvidas_sem_registros():
    pid = "test-vazio"
    PROCESSAMENTOS[pid] = ProcessamentoStatus(
        id=pid,
        status="concluido",
        resultado=ResultadoProcessamento(total_cartoes=0, processados=0, registros=[]),
    )
    resp = client.get(f"/api/processamentos/{pid}/duvidas")
    assert resp.status_code == 200
    assert resp.json()["duvidas"] == []
