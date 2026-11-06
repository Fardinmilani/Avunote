"""Shared native line icons for the workspace and chat composer."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

from studio_theme import COLORS


def icon(kind, color=None):
    color = color or COLORS['light']['muted']
    pixmap = QPixmap(64, 64)
    pixmap.setDevicePixelRatio(2)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor(color), 1.8, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                        Qt.PenJoinStyle.RoundJoin))
    if kind == 'mic':
        painter.drawRoundedRect(12, 4, 8, 16, 4, 4)
        painter.drawArc(7, 8, 18, 18, 180*16, 180*16)
        painter.drawLine(16, 26, 16, 30)
        painter.drawLine(10, 30, 22, 30)
    elif kind == 'file':
        painter.drawRoundedRect(7, 4, 18, 24, 3, 3)
        painter.drawLine(11, 12, 21, 12)
        painter.drawLine(11, 17, 21, 17)
        painter.drawLine(11, 22, 17, 22)
    elif kind == 'stop':
        painter.setBrush(QColor(color))
        painter.drawRoundedRect(8, 8, 16, 16, 3, 3)
    elif kind == 'library':
        for x in [5, 18]:
            for y in [5, 18]:
                painter.drawRoundedRect(x, y, 9, 9, 2, 2)
    elif kind == 'download':
        painter.drawLine(16, 4, 16, 22)
        painter.drawLine(9, 15, 16, 22)
        painter.drawLine(23, 15, 16, 22)
        painter.drawLine(6, 27, 26, 27)
    elif kind == 'refresh':
        painter.drawArc(6, 6, 20, 20, 40*16, 285*16)
        painter.drawLine(23, 5, 25, 12)
        painter.drawLine(25, 12, 18, 10)
    elif kind == 'chat':
        painter.drawRoundedRect(4, 5, 24, 18, 4, 4)
        painter.drawLine(10, 23, 10, 28)
        painter.drawLine(10, 28, 16, 23)
        painter.drawLine(10, 12, 22, 12)
        painter.drawLine(10, 17, 18, 17)
    elif kind == 'history':
        painter.drawArc(5, 5, 22, 22, 140*16, 300*16)
        painter.drawLine(5, 12, 5, 5)
        painter.drawLine(5, 12, 12, 12)
        painter.drawLine(16, 9, 16, 16)
        painter.drawLine(16, 16, 21, 19)
    elif kind == 'folder':
        painter.drawRoundedRect(4, 10, 24, 16, 3, 3)
        painter.drawLine(5, 10, 5, 7)
        painter.drawLine(5, 7, 13, 7)
        painter.drawLine(13, 7, 16, 10)
    elif kind == 'plus':
        painter.drawLine(16, 6, 16, 26)
        painter.drawLine(6, 16, 26, 16)
    elif kind == 'send':
        painter.drawLine(16, 26, 16, 7)
        painter.drawLine(8, 15, 16, 7)
        painter.drawLine(16, 7, 24, 15)
    elif kind == 'copy':
        painter.drawRoundedRect(10, 10, 16, 17, 3, 3)
        painter.drawLine(6, 21, 6, 8)
        painter.drawLine(6, 8, 9, 5)
        painter.drawLine(9, 5, 21, 5)
    elif kind == 'gear':
        painter.drawEllipse(10, 10, 12, 12)
        for dx, dy in ((1, 0), (0, 1), (-1, 0), (0, -1)):
            painter.drawLine(16 + 9*dx, 16 + 9*dy, 16 + 13*dx, 16 + 13*dy)
        for dx, dy in ((1, 1), (-1, 1), (-1, -1), (1, -1)):
            painter.drawLine(16 + 6*dx, 16 + 6*dy, 16 + 9*dx, 16 + 9*dy)
    elif kind == 'tune':
        for y, x in ((8, 12), (16, 21), (24, 15)):
            painter.drawLine(5, y, x-3, y)
            painter.drawLine(x+3, y, 27, y)
            painter.drawEllipse(x-3, y-3, 6, 6)
    elif kind == 'more':
        painter.setBrush(QColor(color))
        for x in (8, 16, 24):
            painter.drawEllipse(x-1, 15, 2, 2)
    else:
        for x, height in [(5, 9), (10, 18), (16, 27), (22, 18), (27, 9)]:
            painter.drawLine(x, (32-height)//2, x, (32+height)//2)
    painter.end()
    return QIcon(pixmap)


