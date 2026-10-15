"""Configuração da aplicação.

Valores podem ser sobrescritos por variáveis de ambiente:

- ``PONTOFACIL_STORAGE_DIR``: diretório raiz dos dados locais (JSON e arquivos).
- ``PONTOFACIL_CORS_ORIGINS``: origens permitidas no CORS, separadas por vírgula.

Usamos apenas a biblioteca padrão para evitar dependências extras neste estágio.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:3000,http://127.0.0.1:3000,"
    "http://localhost:8080,http://127.0.0.1:8080"
)


def _split_env(name: str, default: str) -> list[str]:
    raw = os.getenv(name, default)
    return [item.strip() for item in raw.split(",") if item.strip()]


@dataclass(frozen=True)
class Settings:
    """Configurações imutáveis da aplicação."""

    app_name: str = "PontoFácil API"
    version: str = "0.1.0"
    storage_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("PONTOFACIL_STORAGE_DIR", str(BACKEND_DIR / "storage"))
        )
    )
    cors_origins: list[str] = field(
        default_factory=lambda: _split_env(
            "PONTOFACIL_CORS_ORIGINS", DEFAULT_CORS_ORIGINS
        )
    )
    max_arquivo_bytes: int = field(
        default_factory=lambda: int(
            os.getenv("PONTOFACIL_MAX_ARQUIVO_BYTES", 25 * 1024 * 1024)
        )
    )
    max_arquivos_por_lote: int = field(
        default_factory=lambda: int(os.getenv("PONTOFACIL_MAX_ARQUIVOS", 500))
    )
    max_total_bytes: int = field(
        default_factory=lambda: int(
            os.getenv("PONTOFACIL_MAX_TOTAL_BYTES", 1024 * 1024 * 1024)
        )
    )
    tesseract_cmd: str | None = field(
        default_factory=lambda: os.getenv("PONTOFACIL_TESSERACT_CMD") or None
    )
    ocr_langs: str = field(
        default_factory=lambda: os.getenv("PONTOFACIL_OCR_LANGS", "por")
    )
    max_pixels_imagem: int = field(
        default_factory=lambda: int(
            os.getenv("PONTOFACIL_MAX_PIXELS_IMAGEM", 40_000_000)
        )
    )

    @property
    def lotes_dir(self) -> Path:
        """Diretório dos lotes de processamento (um subdiretório por lote)."""
        return self.storage_dir / "lotes"

    @property
    def exports_dir(self) -> Path:
        """Diretório das planilhas e demais arquivos gerados."""
        return self.storage_dir / "exports"


settings = Settings()
