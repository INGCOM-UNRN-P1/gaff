"""Generador de badges SVG de estilo y cumplimiento para GAFF."""

from __future__ import annotations

from pathlib import Path
from typing import Optional


def generar_badge_svg(total_violaciones: int, score: Optional[int] = None) -> str:
    """Genera un badge SVG en formato estándar Shields.io con el puntaje de estilo GAFF."""
    if score is None:
        if total_violaciones == 0:
            score = 100
        else:
            score = max(0, 100 - (total_violaciones * 5))

    if score == 100:
        color = "#4c1"  # Verde brillante
        status = "100% passing"
    elif score >= 80:
        color = "#97ca00"  # Verde amarillento
        status = f"{score}% passing"
    elif score >= 60:
        color = "#dfb317"  # Amarillo
        status = f"{score}% ({total_violaciones} issues)"
    else:
        color = "#e05d44"  # Rojo
        status = f"{score}% failing"

    label = "gaff style"
    
    # Ancho aproximado en píxeles
    label_width = len(label) * 7 + 10
    status_width = len(status) * 7 + 10
    total_width = label_width + status_width

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{total_width}" height="20" role="img" aria-label="{label}: {status}">
  <linearGradient id="s" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <clipPath id="r">
    <rect width="{total_width}" height="20" rx="3" fill="#fff"/>
  </clipPath>
  <g clip-path="url(#r)">
    <rect width="{label_width}" height="20" fill="#555"/>
    <rect x="{label_width}" width="{status_width}" height="20" fill="{color}"/>
    <rect width="{total_width}" height="20" fill="url(#s)"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="Verdana,Geneva,DejaVu Sans,sans-serif" text-rendering="geometricPrecision" font-size="110">
    <text aria-hidden="true" x="{label_width * 5}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{(label_width - 10) * 10}">{label}</text>
    <text x="{label_width * 5}" y="140" transform="scale(.1)" fill="#fff" textLength="{(label_width - 10) * 10}">{label}</text>
    <text aria-hidden="true" x="{(label_width + status_width / 2) * 10}" y="150" fill="#010101" fill-opacity=".3" transform="scale(.1)" textLength="{(status_width - 10) * 10}">{status}</text>
    <text x="{(label_width + status_width / 2) * 10}" y="140" transform="scale(.1)" fill="#fff" textLength="{(status_width - 10) * 10}">{status}</text>
  </g>
</svg>
"""
    return svg_content


def guardar_badge_svg(ruta: Path, total_violaciones: int, score: Optional[int] = None) -> Path:
    """Genera y guarda el badge SVG en la ruta especificada."""
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    contenido = generar_badge_svg(total_violaciones, score)
    ruta.write_text(contenido, encoding="utf-8")
    return ruta
