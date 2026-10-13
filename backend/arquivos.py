from __future__ import annotations

import re
import uuid
import zipfile
from pathlib import Path

from backend.config import (
    ALLOWED_IMAGE_EXTS,
    ALLOWED_ZIP_EXTS,
    MAX_FILE_SIZE_BYTES,
)

_UNSAFE_CHARS = re.compile(r"[^a-zA-Z0-9._-]")


def validar_arquivo(filename: str, size: int) -> tuple[bool, str]:
    if size <= 0:
        return False, f"Arquivo vazio: '{filename}'."
    if size > MAX_FILE_SIZE_BYTES:
        mb = size / (1024 * 1024)
        return False, f"Arquivo '{filename}' excede o limite de {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB ({mb:.1f} MB)."
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTS and ext not in ALLOWED_ZIP_EXTS:
        return False, f"Formato não suportado: '{filename}'. Use JPG, JPEG, PNG, WEBP ou ZIP."
    return True, ""


def nome_seguro(filename: str) -> str:
    base = Path(filename).name
    base = base.replace("\\", "/").split("/")[-1]
    base = _UNSAFE_CHARS.sub("_", base).strip("._")
    if not base:
        base = "arquivo"
    stem = Path(base).stem or "arquivo"
    suffix = Path(base).suffix.lower()
    return f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"


def _caminho_seguro(destino: Path, nome: str) -> Path:
    nome_limpo = nome.replace("\\", "/").lstrip("/")
    partes = nome_limpo.split("/")
    if ".." in partes:
        raise ValueError(f"Path traversal detectado: {nome}")
    caminho = (destino / nome_limpo).resolve()
    destino_resolvido = destino.resolve()
    if not str(caminho).startswith(str(destino_resolvido) + "\\") and not str(caminho).startswith(str(destino_resolvido) + "/") and str(caminho) != str(destino_resolvido):
        raise ValueError(f"Fora do diretório permitido: {nome}")
    return caminho


def extrair_zip_seguro(zip_bytes: bytes, destino: Path) -> list[Path]:
    destino.mkdir(parents=True, exist_ok=True)
    extraidos: list[Path] = []
    with zipfile.ZipFile(__import__("io").BytesIO(zip_bytes)) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            nome = info.filename
            if nome.startswith("__MACOSX/") or "/__MACOSX/" in nome:
                continue
            caminho = _caminho_seguro(destino, nome)
            caminho.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, open(caminho, "wb") as dst:
                dst.write(src.read())
            extraidos.append(caminho)
    return extraidos


def salvar_upload(file_bytes: bytes, filename: str, destino: Path) -> Path:
    destino.mkdir(parents=True, exist_ok=True)
    nome = nome_seguro(filename)
    caminho = destino / nome
    with open(caminho, "wb") as f:
        f.write(file_bytes)
    return caminho


def listar_imagens(pasta: Path) -> list[Path]:
    if not pasta.exists():
        return []
    return sorted(
        p for p in pasta.rglob("*")
        if p.is_file() and p.suffix.lower() in ALLOWED_IMAGE_EXTS
    )
