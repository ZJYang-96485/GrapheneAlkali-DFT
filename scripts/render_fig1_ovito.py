#!/usr/bin/env python3
"""Render and assemble Figure 1 with OVITO's Python API.

The four 1200x900 atomistic panels are rendered by OVITO/Tachyon. Qt, bundled
with the OVITO Python package, is used only to add consistent labels and
assemble the lossless 2x2 PNG and PDF.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import sys
from pathlib import Path

if sys.platform.startswith("linux"):
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import ovito
from ovito.io import import_file
from ovito.modifiers import CreateBondsModifier, PythonScriptModifier
from ovito.vis import BondsVis, TachyonRenderer, Viewport
from PySide6.QtCore import QMarginsF, QRect, QSizeF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QGuiApplication,
    QImage,
    QPageLayout,
    QPageSize,
    QPainter,
    QPdfWriter,
    QPen,
)

ROOT = Path(__file__).resolve().parents[1]
PANEL_SIZE = (1200, 900)
COLORS = {
    "C": (0.30, 0.32, 0.34),
    "Li": (0.00, 0.45, 0.70),
    "Na": (0.90, 0.56, 0.08),
}
RADII = {"C": 0.50, "Li": 0.86, "Na": 1.00}
CASES = (
    ("a", "li_c50", "Li/C50"),
    ("b", "na_c50", "Na/C50"),
    ("c", "li_c49", "Li/C49"),
    ("d", "na_c49", "Na/C49"),
)

def style_particle_types(_frame, data):
    particle_types = data.particles_.particle_types_
    for particle_type in particle_types.types:
        mutable_type = particle_types.type_by_id_(particle_type.id)
        symbol = particle_type.name
        if symbol in COLORS:
            mutable_type.color = COLORS[symbol]
            mutable_type.radius = RADII[symbol]

def normalized(vector):
    norm = math.sqrt(sum(value * value for value in vector))
    return tuple(value / norm for value in vector)

def read_provenance(path: Path):
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["panel"]: row for row in csv.DictReader(handle)}

def render_panel(structure_path: Path, panel_path: Path):
    pipeline = import_file(str(structure_path))
    pipeline.modifiers.append(PythonScriptModifier(function=style_particle_types))
    bonds = CreateBondsModifier(mode=CreateBondsModifier.Mode.Pairwise)
    bonds.set_pairwise_cutoff("C", "C", 1.85)
    bonds.vis.width = 0.15
    bonds.vis.color = (0.38, 0.40, 0.42)
    bonds.vis.coloring_mode = BondsVis.ColoringMode.Uniform
    pipeline.modifiers.append(bonds)

    data = pipeline.compute()
    data.cell.vis.enabled = True
    data.cell.vis.rendering_color = (0.58, 0.60, 0.62)
    data.cell.vis.line_width = 0.025
    pipeline.add_to_scene()

    camera_dir = normalized((0.18, 0.42, -1.0))
    up_seed = (0.0, 0.0, 1.0)
    projection = sum(a * b for a, b in zip(up_seed, camera_dir))
    camera_up = normalized(tuple(
        a - projection * b for a, b in zip(up_seed, camera_dir)
    ))
    matrix = data.cell.matrix
    cell_center = tuple(
        matrix[axis, 3] + 0.5 * sum(matrix[axis, vector] for vector in range(3))
        for axis in range(3)
    )

    viewport = Viewport(type=Viewport.Type.Ortho)
    viewport.camera_dir = camera_dir
    viewport.camera_up = camera_up
    viewport.camera_pos = tuple(
        center - 32.0 * direction
        for center, direction in zip(cell_center, camera_dir)
    )
    viewport.fov = 10.5

    renderer = TachyonRenderer()
    renderer.ambient_occlusion = True
    renderer.shadows = True
    renderer.antialiasing_samples = 16
    renderer.direct_light_intensity = 0.82
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    viewport.render_image(
        filename=str(panel_path),
        size=PANEL_SIZE,
        background=(1.0, 1.0, 1.0),
        renderer=renderer,
    )
    pipeline.remove_from_scene()

def draw_centered_text(painter, rect, text, font):
    painter.setFont(font)
    painter.setPen(QColor("#17191b"))
    painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

def build_montage(panel_paths, provenance, png_path: Path):
    panel_width, panel_height = PANEL_SIZE
    margin, gutter, title_height, legend_height = 56, 44, 86, 132
    canvas_width = 2 * panel_width + 2 * margin + gutter
    canvas_height = 2 * (title_height + panel_height) + 2 * margin + gutter + legend_height
    canvas = QImage(canvas_width, canvas_height, QImage.Format.Format_RGB32)
    canvas.fill(QColor("white"))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    title_font = QFont("Arial", 27, QFont.Weight.Bold)
    detail_font = QFont("Arial", 24, QFont.Weight.Normal)
    legend_font = QFont("Arial", 24, QFont.Weight.Normal)

    for index, (panel, _key, system) in enumerate(CASES):
        row, column = divmod(index, 2)
        left = margin + column * (panel_width + gutter)
        top = margin + row * (title_height + panel_height + gutter)
        height = float(provenance[panel]["adsorbate_height_angstrom"])
        draw_centered_text(painter, QRect(left, top, 135, title_height),
                           f"({panel})", title_font)
        draw_centered_text(
            painter, QRect(left + 125, top, panel_width - 125, title_height),
            f"{system}    h = {height:.3f} Å", detail_font)
        panel_image = QImage(str(panel_paths[panel]))
        if panel_image.isNull():
            raise RuntimeError(f"Cannot load rendered panel {panel_paths[panel]}")
        painter.drawImage(
            QRect(left, top + title_height, panel_width, panel_height),
            panel_image)
        painter.setPen(QPen(QColor("#c6c8ca"), 2))
        painter.drawRect(left, top + title_height, panel_width, panel_height)

    legend_y = canvas_height - margin - legend_height // 2
    legend_items = (("C", "C"), ("Li", "Li"), ("Na", "Na"))
    item_width = 220
    start_x = (canvas_width - item_width * len(legend_items)) // 2
    for index, (symbol, label) in enumerate(legend_items):
        center_x = start_x + index * item_width + 42
        painter.setBrush(QColor.fromRgbF(*COLORS[symbol]))
        painter.setPen(QPen(QColor("#44474a"), 2))
        radius = 20 if symbol == "C" else (25 if symbol == "Li" else 29)
        painter.drawEllipse(center_x - radius, legend_y - radius,
                            2 * radius, 2 * radius)
        painter.setFont(legend_font)
        painter.setPen(QColor("#17191b"))
        painter.drawText(
            QRect(center_x + 42, legend_y - 35, 125, 70),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            label)
    painter.end()
    canvas.setDotsPerMeterX(round(300 / 0.0254))
    canvas.setDotsPerMeterY(round(300 / 0.0254))
    png_path.parent.mkdir(parents=True, exist_ok=True)
    if not canvas.save(str(png_path), "PNG", 100):
        raise RuntimeError(f"Failed to save {png_path}")
    return canvas

def save_pdf(canvas: QImage, pdf_path: Path):
    dpi = 300
    writer = QPdfWriter(str(pdf_path))
    writer.setResolution(dpi)
    width_mm = canvas.width() / dpi * 25.4
    height_mm = canvas.height() / dpi * 25.4
    writer.setPageSize(QPageSize(
        QSizeF(width_mm, height_mm), QPageSize.Unit.Millimeter))
    writer.setPageMargins(
        QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Millimeter)
    painter = QPainter(writer)
    painter.drawImage(QRect(0, 0, writer.width(), writer.height()), canvas)
    painter.end()

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--structure-dir", type=Path,
                        default=ROOT / "structures" / "report" / "fig1")
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT / "figures" / "report")
    args = parser.parse_args()
    structure_dir = args.structure_dir.resolve()
    output_dir = args.output_dir.resolve()
    provenance = read_provenance(structure_dir / "provenance.csv")
    qt_app = QGuiApplication.instance() or QGuiApplication(["render_fig1_ovito"])

    panel_dir = output_dir / "fig01_panels"
    panel_paths = {}
    for panel, key, _system in CASES:
        structure_path = structure_dir / f"{key}_relaxed.extxyz"
        panel_path = panel_dir / f"panel_{panel}_{key}.png"
        render_panel(structure_path, panel_path)
        panel_paths[panel] = panel_path

    png_path = output_dir / "fig01_relaxed_structures.png"
    pdf_path = output_dir / "fig01_relaxed_structures.pdf"
    canvas = build_montage(panel_paths, provenance, png_path)
    save_pdf(canvas, pdf_path)
    print(f"OVITO version: {ovito.version_string}")
    print(f"PNG: {png_path}")
    print(f"PDF: {pdf_path}")
    del qt_app
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
