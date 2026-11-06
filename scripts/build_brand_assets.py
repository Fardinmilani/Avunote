"""Package approved transparent Avunote artwork into PNGs and a multi-size ICO.

Requires the application's existing PySide6 dependency. No image generation API
is used here: this only frames, resizes and encodes the approved raster assets.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, Qt
from PySide6.QtGui import QColor, QImage, QPainter

ROOT = Path(__file__).resolve().parents[1]
SIZES = (16, 20, 24, 32, 40, 48, 64, 96, 128, 256)


def content_bounds(image: QImage) -> tuple[int, int, int, int]:
    """Ignore negligible generated alpha specks when calculating visual framing."""
    image = image.convertToFormat(QImage.Format.Format_RGBA8888)
    pixels = bytes(image.constBits())
    width, height = image.width(), image.height()
    xs, ys = [], []
    for y in range(height):
        row = pixels[y * image.bytesPerLine() : (y + 1) * image.bytesPerLine()]
        row_x = [x for x in range(width) if row[x * 4 + 3] >= 32]
        if row_x:
            xs.extend((row_x[0], row_x[-1]))
            ys.append(y)
    if not xs:
        raise ValueError("Artwork contains no visible pixels")
    return min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1


def framed(source: Path, size: int | None = None) -> QImage:
    image = QImage(str(source))
    if image.isNull() or not image.hasAlphaChannel():
        raise ValueError(f"A valid transparent source PNG is required: {source}")
    x, y, width, height = content_bounds(image)
    artwork = image.copy(x, y, width, height)
    margin = max(2, round(max(width, height) * 0.055))
    canvas_width = max(width, height) + margin * 2 if size else width + margin * 2
    canvas_height = canvas_width if size else height + margin * 2
    canvas = QImage(canvas_width, canvas_height, QImage.Format.Format_ARGB32_Premultiplied)
    canvas.fill(Qt.GlobalColor.transparent)
    painter = QPainter(canvas)
    painter.drawImage((canvas_width - width) // 2, (canvas_height - height) // 2, artwork)
    painter.end()
    return canvas.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                         Qt.TransformationMode.SmoothTransformation) if size else canvas


def png_bytes(image: QImage) -> bytes:
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not image.save(buffer, "PNG"):
        raise RuntimeError("Failed to encode PNG")
    return bytes(buffer.data())


def save_ico(image: QImage, destination: Path) -> None:
    frames = [png_bytes(image.scaled(size, size, Qt.AspectRatioMode.IgnoreAspectRatio,
                                    Qt.TransformationMode.SmoothTransformation)) for size in SIZES]
    offset = 6 + 16 * len(frames)
    directory = []
    for size, frame in zip(SIZES, frames):
        directory.append(struct.pack("<BBBBHHII", size % 256, size % 256, 0, 0,
                                     1, 32, len(frame), offset))
        offset += len(frame)
    destination.write_bytes(struct.pack("<HHH", 0, 1, len(frames)) + b"".join(directory) + b"".join(frames))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mark", type=Path, required=True)
    parser.add_argument("--logo", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "assets")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    mark = framed(args.mark, 1024)
    logo = framed(args.logo)
    mark.save(str(args.output / "avunote-mark.png"))
    logo.save(str(args.output / "avunote-logo-transparent.png"))
    save_ico(mark, args.output / "avunote.ico")

    # A contact sheet makes the actual alpha appearance reviewable on both themes.
    preview = QImage(1100, 600, QImage.Format.Format_RGB32)
    preview.fill(QColor("#FFFFFF"))
    painter = QPainter(preview)
    painter.fillRect(0, 300, 1100, 300, QColor("#111827"))
    for top in (0, 300):
        painter.drawImage(20, top + 25, mark.scaled(210, 210, Qt.AspectRatioMode.KeepAspectRatio,
                                                  Qt.TransformationMode.SmoothTransformation))
        painter.drawImage(260, top + 90, logo.scaledToWidth(810, Qt.TransformationMode.SmoothTransformation))
    painter.end()
    preview.save(str(args.output / "avunote-brand-preview.png"))
    for name, image in (("mark", mark), ("logo", logo)):
        for x, y in ((0, 0), (image.width() - 1, 0), (0, image.height() - 1),
                     (image.width() - 1, image.height() - 1)):
            assert image.pixelColor(x, y).alpha() == 0, "Artwork corner must remain transparent"
        print(json.dumps({"asset": name, "width": image.width(), "height": image.height(),
                          "alpha_corners": 0}))
    print(json.dumps({"ico_sizes": SIZES, "ico_bytes": (args.output / "avunote.ico").stat().st_size}))


if __name__ == "__main__":
    main()
