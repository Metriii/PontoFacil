from __future__ import annotations

import cv2
import numpy as np
from pathlib import Path


def para_escala_cinza(img: np.ndarray) -> np.ndarray:
    if len(img.shape) == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def melhorar_contraste(img: np.ndarray) -> np.ndarray:
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(img)


def corrigir_rotacao(img: np.ndarray) -> np.ndarray:
    edges = cv2.Canny(img, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, 100, minLineLength=100, maxLineGap=10)
    if lines is None or len(lines) == 0:
        return img
    angulos = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        if x2 != x1:
            angulo = np.degrees(np.arctan2(y2 - y1, x2 - x1))
            if abs(angulo) < 45:
                angulos.append(angulo)
    if not angulos:
        return img
    mediana_angulo = np.median(angulos)
    if abs(mediana_angulo) < 0.5:
        return img
    (h, w) = img.shape[:2]
    centro = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(centro, mediana_angulo, 1.0)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)


def binarizar(img: np.ndarray) -> np.ndarray:
    return cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)


def preprocessar(imagem_path: Path) -> np.ndarray:
    img = cv2.imread(str(imagem_path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise ValueError(f"Não foi possível ler a imagem: {imagem_path}")
    img = melhorar_contraste(img)
    img = corrigir_rotacao(img)
    img = binarizar(img)
    return img
