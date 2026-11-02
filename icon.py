#!/usr/bin/env python3
"""Draw the small Rubik's cube icon. Headless. No display needed."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import cairo

ROOT = Path(__file__).resolve().parent
# Same sticker colours as the cube page.
WHITE = (0.957, 0.957, 0.957)
RED = (0.718, 0.071, 0.204)
GREEN = (0.000, 0.608, 0.282)
PLASTIC = (0.078, 0.078, 0.094)


def _project(x: float, y: float, z: float) -> tuple[float, float]:
    """Isometric: +x down-right, +z down-left, +y up."""
    return (
        (x - z) * math.cos(math.radians(30)),
        (x + z) * math.sin(math.radians(30)) - y,
    )


def _corners(axis: str, a0: float, a1: float, b0: float, b1: float) -> list[tuple[float, float]]:
    if axis == "top":
        raw = ((a0, 3, b0), (a1, 3, b0), (a1, 3, b1), (a0, 3, b1))
    elif axis == "right":
        raw = ((3, a0, b0), (3, a1, b0), (3, a1, b1), (3, a0, b1))
    else:
        raw = ((a0, b0, 3), (a1, b0, 3), (a1, b1, 3), (a0, b1, 3))
    return [_project(*corner) for corner in raw]


def _face(axis: str, i: int, j: int, inset: float) -> list[tuple[float, float]]:
    return _corners(axis, i + inset, i + 1 - inset, j + inset, j + 1 - inset)


def _plastic(axis: str) -> list[tuple[float, float]]:
    return _corners(axis, 0, 3, 0, 3)


def _bounds(points: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return min(xs), min(ys), max(xs), max(ys)


def _all_points() -> list[tuple[float, float]]:
    points = []
    for axis in ("left", "right", "top"):
        points.extend(_plastic(axis))
    return points


def draw_icon(size: int) -> cairo.ImageSurface:
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    context = cairo.Context(surface)
    context.set_operator(cairo.OPERATOR_SOURCE)
    context.set_source_rgba(0, 0, 0, 0)
    context.paint()
    context.set_operator(cairo.OPERATOR_OVER)

    left, top, right, bottom = _bounds(_all_points())
    pad = size * 0.08
    scale = min((size - pad * 2) / (right - left), (size - pad * 2) / (bottom - top))
    ox = (size - (right - left) * scale) / 2 - left * scale
    oy = (size - (bottom - top) * scale) / 2 - top * scale

    def poly(points: list[tuple[float, float]], rgb: tuple[float, float, float]) -> None:
        context.new_path()
        x0, y0 = points[0]
        context.move_to(ox + x0 * scale, oy + y0 * scale)
        for x, y in points[1:]:
            context.line_to(ox + x * scale, oy + y * scale)
        context.close_path()
        context.set_source_rgb(*rgb)
        context.fill()

    # Plastic under the stickers, so the gaps stay dark.
    for axis in ("left", "right", "top"):
        poly(_plastic(axis), PLASTIC)

    inset = 0.10
    for i in range(3):
        for j in range(3):
            poly(_face("left", i, j, inset), RED)
            poly(_face("right", i, j, inset), GREEN)
            poly(_face("top", i, j, inset), WHITE)
    return surface


def write_svg(path: Path) -> None:
    """Text icon for the repo. Same geometry as the PNG."""
    left, top, right, bottom = _bounds(_all_points())
    width = right - left
    height = bottom - top
    pad = max(width, height) * 0.08

    def points(raw: list[tuple[float, float]]) -> str:
        bits = []
        for x, y in raw:
            bits.append(f"{x - left + pad:.2f},{y - top + pad:.2f}")
        return " ".join(bits)

    def shape(raw: list[tuple[float, float]], fill: str) -> str:
        return f'<polygon points="{points(raw)}" fill="{fill}"/>'

    body = []
    for axis in ("left", "right", "top"):
        body.append(shape(_plastic(axis), "#141418"))
    for i in range(3):
        for j in range(3):
            body.append(shape(_face("left", i, j, 0.10), "#b71234"))
            body.append(shape(_face("right", i, j, 0.10), "#009b48"))
            body.append(shape(_face("top", i, j, 0.10), "#f4f4f4"))
    side = max(width, height) + pad * 2
    # Centre the cube in a square.
    extra_x = (side - (width + pad * 2)) / 2
    extra_y = (side - (height + pad * 2)) / 2
    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{-extra_x:.2f} {-extra_y:.2f} {side:.2f} {side:.2f}">\n'
        + "\n".join(body)
        + "\n</svg>\n"
    )
    path.write_text(svg, encoding="utf-8")


def install_icons() -> None:
    base = Path.home() / ".local" / "share" / "icons" / "hicolor"
    svg = ROOT / "data" / "rubik-cube.svg"
    write_svg(svg)
    scalable = base / "scalable" / "apps"
    scalable.mkdir(parents=True, exist_ok=True)
    (scalable / "rubik-cube.svg").write_text(svg.read_text(encoding="utf-8"), encoding="utf-8")
    for size in (48, 64, 128, 256, 512):
        folder = base / f"{size}x{size}" / "apps"
        folder.mkdir(parents=True, exist_ok=True)
        draw_icon(size).write_to_png(str(folder / "rubik-cube.png"))
        print(folder / "rubik-cube.png")
    print(scalable / "rubik-cube.svg")


if __name__ == "__main__":
    if "--install" in sys.argv:
        install_icons()
    else:
        out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "data" / "rubik-cube.png"
        size = int(sys.argv[2]) if len(sys.argv) > 2 else 256
        draw_icon(size).write_to_png(str(out))
        write_svg(ROOT / "data" / "rubik-cube.svg")
        print(out)
