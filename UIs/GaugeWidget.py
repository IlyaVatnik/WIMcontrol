# -*- coding: utf-8 -*-
"""
Created on Wed Apr 15 16:14:27 2026

@author: Илья
"""

from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtGui import QPainter, QPen, QFont
from PyQt5.QtCore import Qt, QRectF, QPointF
import math


__version__ = '1.1'
__date__ = '2026.04.15'


class GaugeWindow(QWidget):
    def __init__(self,
                 weight_min=0,
                 weight_max=200,
                 x_min=100,
                 x_max=200):
        super().__init__()

        self.setWindowTitle("Weight")
        self.resize(320, 400)

        self.gauge = GaugeWidget(self)
        self.gauge.setRange(weight_min, weight_max)

    
        self.axis = AxisWidget(self)
        self.axis.setRange(x_min, x_max)

        layout = QVBoxLayout()
        layout.addWidget(self.gauge)
        layout.addWidget(self.axis)
        self.setLayout(layout)

    
    def update_value(self, value, x1=None, x2=None):
        self.gauge.setValue(value)

        if x1 is not None and x2 is not None:
            self.axis.setValues(x1, x2)


class GaugeWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._min = 0
        self._max = 100

    def setRange(self, vmin, vmax):
        self._min = vmin
        self._max = vmax
        self.update()

    def setValue(self, value):
        self._value = max(self._min, min(self._max, value))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect()
        side = min(rect.width(), rect.height())

        painter.translate(rect.center())
        painter.scale(side / 200.0, side / 200.0)

        pen = QPen(Qt.black, 2)
        painter.setPen(pen)

        start_angle = 225
        span_angle = 270

        painter.drawArc(QRectF(-90, -90, 180, 180),
                        int(start_angle * 16),
                        int(-span_angle * 16))

        steps = 10
        for i in range(steps + 1):
            angle = start_angle - (span_angle / steps) * i
            rad = math.radians(angle)

            x1 = 70 * math.cos(rad)
            y1 = -70 * math.sin(rad)
            x2 = 85 * math.cos(rad)
            y2 = -85 * math.sin(rad)

            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # защита от деления на 0
        if self._max == self._min:
            value_ratio = 0
        else:
            value_ratio = (self._value - self._min) / (self._max - self._min)

        angle = start_angle - span_angle * value_ratio
        rad = math.radians(angle)

        painter.setPen(QPen(Qt.red, 3))
        painter.drawLine(QPointF(0, 0),
                         QPointF(60 * math.cos(rad),
                                 -60 * math.sin(rad)))

        painter.setPen(Qt.NoPen)
        painter.setBrush(Qt.black)
        painter.drawEllipse(QPointF(0, 0), 5, 5)

        painter.setPen(Qt.black)
        painter.setFont(QFont("Arial", 10))
        painter.drawText(QRectF(-50, 30, 100, 30),
                         Qt.AlignCenter,
                         f"{self._value:.2f} g")



class AxisWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._min = 0
        self._max = 100
        self._x1 = 0
        self._x2 = 0

        self.setMinimumHeight(80)

    def setRange(self, vmin, vmax):
        self._min = vmin
        self._max = vmax
        self.update()

    def setValues(self, x1, x2):
        self._x1 = x1
        self._x2 = x2
        self.update()

    def _to_pos(self, val, w, margin):
        if self._max == self._min:
            return margin
        ratio = (val - self._min) / (self._max - self._min)
        return margin + ratio * (w - 2 * margin)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w = self.width()
        h = self.height()
        margin = 20
        y = h // 2

        painter.setPen(QPen(Qt.black, 2))
        painter.drawLine(margin, y, w - margin, y)

        steps = 10
        for i in range(steps + 1):
            x = margin + i * (w - 2 * margin) / steps
            painter.drawLine(int(x), y - 5, int(x), y + 5)

        x1p = self._to_pos(self._x1, w, margin)
        x2p = self._to_pos(self._x2, w, margin)

        painter.setPen(QPen(Qt.blue, 3))
        painter.drawLine(int(x1p), y - 10, int(x1p), y + 10)

        painter.setPen(QPen(Qt.red, 3))
        painter.drawLine(int(x2p), y - 10, int(x2p), y + 10)

        painter.setFont(QFont("Arial", 9))

        painter.setPen(Qt.blue)
        painter.drawText(int(x1p) - 30, y - 15, 60, 15,
                         Qt.AlignCenter, f"{self._x1:.2f}")

        painter.setPen(Qt.red)
        painter.drawText(int(x2p) - 30, y + 10, 60, 15,
                         Qt.AlignCenter, f"{self._x2:.2f}")