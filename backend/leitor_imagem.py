from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

import pytesseract


@dataclass
class Palavra:
    texto: str
    confianca: float
    x: int
    y: int
    w: int
    h: int


@dataclass
class LeitorResultado:
    texto_completo: str
    palavras: list[Palavra] = field(default_factory=list)
    erro: str | None = None


def tesseract_disponivel() -> bool:
    return shutil.which("tesseract") is not None


def ler_horarios(imagem_path: Path) -> LeitorResultado:
    if not tesseract_disponivel():
        return LeitorResultado(
            texto_completo="",
            erro="Tesseract OCR não está instalado. Instale o Tesseract no Windows e adicione ao PATH.",
        )
    try:
        import cv2
        from backend.tratamento_imagem import preprocessar

        img = preprocessar(imagem_path)
        temp_path = imagem_path.parent / f"_ocr_{imagem_path.stem}.png"
        cv2.imwrite(str(temp_path), img)

        try:
            data = pytesseract.image_to_data(
                str(temp_path),
                lang="por",
                config="--psm 6",
                output_type=pytesseract.Output.DICT,
            )
        finally:
            temp_path.unlink(missing_ok=True)

        palavras: list[Palavra] = []
        textos: list[str] = []
        n = len(data["text"])
        for i in range(n):
            texto = data["text"][i].strip()
            if not texto:
                continue
            conf = float(data["conf"][i])
            if conf < 0:
                conf = 0.0
            palavras.append(
                Palavra(
                    texto=texto,
                    confianca=conf / 100.0,
                    x=data["left"][i],
                    y=data["top"][i],
                    w=data["width"][i],
                    h=data["height"][i],
                )
            )
            textos.append(texto)

        return LeitorResultado(
            texto_completo=" ".join(textos),
            palavras=palavras,
        )
    except Exception as e:
        return LeitorResultado(
            texto_completo="",
            erro=f"Falha ao processar imagem: {str(e)}",
        )
