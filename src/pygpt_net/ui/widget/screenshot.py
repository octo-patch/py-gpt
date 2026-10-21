#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2026.09.03 14:55:00                  #
# ================================================== #

from PySide6.QtCore import Qt, QPoint, QRect, Signal, QTimer
from PySide6.QtGui import QColor, QCursor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget


class ScreenshotFlash(QWidget):
    """Short non-interactive fullscreen flash shown after a screenshot is captured."""

    def __init__(self, screen=None):
        flags = (
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
            | Qt.WindowTransparentForInput
        )
        super().__init__(None, flags)

        self.screen = screen or QApplication.primaryScreen()
        self.screen_geometry = QRect(self.screen.geometry()) if self.screen is not None else QRect()
        self._alpha = 90

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_DeleteOnClose, True)

    def show_flash(self):
        """Show a brief camera-like white flash without taking focus."""
        if self.screen is None or self.screen_geometry.isNull():
            self.close()
            return

        self.setGeometry(self.screen_geometry)
        self.show()
        self.raise_()

        QTimer.singleShot(45, lambda: self._set_alpha(45))
        QTimer.singleShot(90, lambda: self._set_alpha(18))
        QTimer.singleShot(140, self.close)

    def _set_alpha(self, alpha: int):
        """Update flash opacity while fading out."""
        if not self.isVisible():
            return
        self._alpha = alpha
        self.update()

    def paintEvent(self, event):
        """Paint the fullscreen white flash."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(255, 255, 255, self._alpha))
        painter.end()


class ScreenRegionSelector(QWidget):
    """Fullscreen overlay used to select a rectangular screen region."""

    region_selected = Signal(QRect)
    cancelled = Signal()

    def __init__(self, screen=None):
        flags = Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        super().__init__(None, flags)

        self.screen = screen or QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        screens = QApplication.screens()
        self.screen_index = screens.index(self.screen) if self.screen in screens else 0
        self.screen_geometry = QRect(self.screen.geometry()) if self.screen is not None else QRect()

        self._selecting = False
        self._selection_start = QPoint()
        self._selection_rect = QRect()

        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self.setCursor(QCursor(Qt.CrossCursor))

    def show_selector(self):
        """Show the selector over the target screen."""
        if self.screen is None or self.screen_geometry.isNull():
            self.cancel()
            return

        self.setGeometry(self.screen_geometry)
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.ActiveWindowFocusReason)

    def _clamp_point(self, point: QPoint) -> QPoint:
        """Clamp a point to the overlay bounds."""
        return QPoint(
            max(0, min(point.x(), max(0, self.width() - 1))),
            max(0, min(point.y(), max(0, self.height() - 1))),
        )

    def _finish_selection(self):
        """Hide the overlay and emit the selected global rectangle."""
        selection = self._selection_rect.normalized().intersected(self.rect())
        self._selecting = False

        if selection.width() <= 1 or selection.height() <= 1:
            self.cancel()
            return

        global_top_left = self.mapToGlobal(selection.topLeft())
        global_rect = QRect(global_top_left, selection.size())

        # Ensure the dimming overlay is gone before the actual screenshot is made.
        self.hide()
        QApplication.processEvents()
        self.region_selected.emit(global_rect)
        self.close()

    def cancel(self):
        """Cancel region selection."""
        if self._selecting:
            self.releaseMouse()
        self._selecting = False
        self.hide()
        QApplication.processEvents()
        self.cancelled.emit()
        self.close()

    def mousePressEvent(self, event):
        """Start a selection with the left mouse button; right click cancels."""
        if event.button() == Qt.RightButton:
            self.cancel()
            event.accept()
            return

        if event.button() == Qt.LeftButton:
            self._selecting = True
            self._selection_start = self._clamp_point(event.position().toPoint())
            self._selection_rect = QRect(self._selection_start, self._selection_start)
            self.grabMouse()
            self.update()
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Update the selection rectangle while dragging."""
        if self._selecting and (event.buttons() & Qt.LeftButton):
            current = self._clamp_point(event.position().toPoint())
            self._selection_rect = QRect(self._selection_start, current)
            self.update()
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Finish the screenshot region when the left button is released."""
        if event.button() == Qt.LeftButton and self._selecting:
            self.releaseMouse()
            current = self._clamp_point(event.position().toPoint())
            self._selection_rect = QRect(self._selection_start, current)
            self._finish_selection()
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        """Allow Escape to cancel region selection."""
        if event.key() == Qt.Key_Escape:
            self.cancel()
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event):
        """Draw a Painter-like dimmed crop overlay and selection border."""
        painter = QPainter(self)

        # Clear the translucent backing store first so the selected area becomes
        # a real transparent "hole" even after the rectangle changes size.
        painter.setCompositionMode(QPainter.CompositionMode_Source)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))
        painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

        overlay = QColor(0, 0, 0, 120)

        if self._selecting and not self._selection_rect.isNull():
            selection = self._selection_rect.normalized().intersected(self.rect())
            width = self.width()
            height = self.height()

            if selection.left() > 0:
                painter.fillRect(0, 0, selection.left(), height, overlay)
            if selection.right() < width - 1:
                painter.fillRect(
                    selection.right() + 1,
                    0,
                    width - (selection.right() + 1),
                    height,
                    overlay,
                )
            if selection.top() > 0:
                painter.fillRect(selection.left(), 0, selection.width(), selection.top(), overlay)
            if selection.bottom() < height - 1:
                painter.fillRect(
                    selection.left(),
                    selection.bottom() + 1,
                    selection.width(),
                    height - (selection.bottom() + 1),
                    overlay,
                )

            painter.setPen(QPen(QColor(255, 255, 255, 200), 1, Qt.DashLine))
            painter.drawRect(selection.adjusted(0, 0, -1, -1))
        else:
            painter.fillRect(self.rect(), overlay)

        painter.end()
