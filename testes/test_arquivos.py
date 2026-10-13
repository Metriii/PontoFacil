import io
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.arquivos import (
    _caminho_seguro,
    extrair_zip_seguro,
    nome_seguro,
    validar_arquivo,
)


def test_validar_arquivo_imagem_valida():
    ok, motivo = validar_arquivo("foto.jpg", 1024)
    assert ok
    assert motivo == ""


def test_validar_arquivo_jfif():
    ok, motivo = validar_arquivo("ANA KAROLINA.jfif", 1024)
    assert ok
    assert motivo == ""


def test_validar_arquivo_vazio():
    ok, motivo = validar_arquivo("foto.jpg", 0)
    assert not ok
    assert "vazio" in motivo.lower()


def test_validar_arquivo_extensao_invalida():
    ok, motivo = validar_arquivo("malware.exe", 1024)
    assert not ok
    assert "não suportado" in motivo.lower()


def test_validar_arquivo_tamanho_excedido():
    from backend.config import MAX_FILE_SIZE_BYTES
    ok, motivo = validar_arquivo("foto.jpg", MAX_FILE_SIZE_BYTES + 1)
    assert not ok
    assert "limite" in motivo.lower()


def test_nome_seguro_remove_path():
    nome = nome_seguro("../../../etc/passwd.jpg")
    assert ".." not in nome
    assert "/" not in nome
    assert nome.endswith(".jpg")


def test_nome_seguro_remove_caracteres_especiais():
    nome = nome_seguro("minha foto (cópia) @2024!.png")
    assert "(" not in nome
    assert ")" not in nome
    assert "@" not in nome
    assert "!" not in nome
    assert nome.endswith(".png")


def test_caminho_seguro_rejeita_path_traversal(tmp_path):
    try:
        _caminho_seguro(tmp_path, "../evil.png")
        assert False, "Deveria ter levantado ValueError"
    except ValueError as e:
        assert "traversal" in str(e).lower()


def test_caminho_seguro_rejeita_path_absoluto(tmp_path):
    try:
        _caminho_seguro(tmp_path, "C:/Windows/System32/evil.png")
        assert False, "Deveria ter levantado ValueError"
    except ValueError as e:
        assert "permitido" in str(e).lower() or "traversal" in str(e).lower()


def test_extrair_zip_seguro_valido(tmp_path):
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as zf:
        zf.writestr("foto1.jpg", b"fake image data")
        zf.writestr("subpasta/foto2.png", b"fake png data")
    zip_bytes.seek(0)

    destino = tmp_path / "extraido"
    extraidos = extrair_zip_seguro(zip_bytes.getvalue(), destino)

    assert len(extraidos) == 2
    assert all(e.exists() for e in extraidos)


def test_extrair_zip_seguro_path_traversal(tmp_path):
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as zf:
        zf.writestr("../evil.png", b"malicious")
    zip_bytes.seek(0)

    destino = tmp_path / "extraido"
    try:
        extrair_zip_seguro(zip_bytes.getvalue(), destino)
        assert False, "Deveria ter levantado ValueError"
    except ValueError as e:
        assert "traversal" in str(e).lower()


def test_extrair_zip_seguro_ignora_macosx(tmp_path):
    zip_bytes = io.BytesIO()
    with zipfile.ZipFile(zip_bytes, "w") as zf:
        zf.writestr("__MACOSX/._foto.jpg", b"resource fork")
        zf.writestr("foto.jpg", b"real image")
    zip_bytes.seek(0)

    destino = tmp_path / "extraido"
    extraidos = extrair_zip_seguro(zip_bytes.getvalue(), destino)

    assert len(extraidos) == 1
    assert extraidos[0].name == "foto.jpg"
