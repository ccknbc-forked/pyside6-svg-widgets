import os
import re
from functools import partial
from typing import Optional, Union, Tuple
import xml.etree.ElementTree as Et

from functools import lru_cache

from PyQt5.QtWidgets import (
    QPushButton, QWidget,
    QLabel, QHBoxLayout, QStyle, QStyleOption,
    QSizePolicy, QSpacerItem, QRadioButton, QToolButton
)
from PyQt5.QtGui import QPixmap, QPainter, QIcon, QColor
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtCore import Qt, QTimer, QSize, QByteArray, QEvent
from PyQt5.QtSvg import QSvgWidget
from PyQt5.QtCore import pyqtSignal as Signal

SIZE = 25
xSize = 10


@lru_cache()
def get_color(object_name, style_sheet, hover=False, pressed=False, checked=False, style_filter="icon-color"):
    style_blocks = style_sheet.split('}')
    for block in style_blocks:

        if not object_name:
            continue

        _filter = any(
            [
                (f'{object_name}:hover') in block.strip(),
                (f'{object_name}:pressed' in block.strip()),
                (f'{object_name}:checked' in block.strip()),
            ]
        )
        if not any([hover, pressed, checked]) and object_name in block.strip() and not _filter:
            style_rules = block.split('{')[-1].strip()

        elif hover and f'{object_name}:hover' in block.strip():
            style_rules = block.split('{')[-1].strip()

        elif checked and f'{object_name}:checked' in block.strip():
            style_rules = block.split('{')[-1].strip()

        elif pressed and f'{object_name}:pressed' in block.strip():
            style_rules = block.split('{')[-1].strip()

        else:
            continue

        clear = lambda e: str(e).replace("/*", "").replace("*/", "")
        style_string = "\n".join(
            [clear(i).strip() for i in style_rules.split("\n") if clear(i).strip().startswith(style_filter)])

        if style_string:
            pattern = style_filter + r":\s*([^;]+);"
            matches = re.findall(pattern, style_string)
            _match = matches[0] if matches else None
            return _match, style_sheet

    return None, None


def get_effective_style(init_widget: QWidget, hover=False, pressed=False, checked=False, style_filter="icon-color"):
    """Get the effective style of a widget, considering parent styles."""

    object_name = type(init_widget).__name__
    current_widget = init_widget
    while current_widget:
        try:
            current_widget

            style_sheet = current_widget.styleSheet()
            if style_sheet and object_name in style_sheet:
                x, y = get_color(object_name, style_sheet, hover, pressed, checked, style_filter)
                if x and y:
                    return x, y

            # Move to the parent widget
            current_widget = current_widget.parentWidget()

        except RuntimeError:
            break
    return None, None


def svg_to_pixmap(
        svg_filename: str,
        width: int,
        height: int,
        color: Union[QColor, str]
) -> QPixmap:
    if svg_filename.startswith("<svg"):
        if "width=" in svg_filename and "height=" in svg_filename:
            w = svg_filename.split("width=\"")[1].split('"')[0]
            _width = f'width="{w}"'
            h = svg_filename.split("height=\"")[1].split('"')[0]
            _height = f'height="{h}"'
            svg_filename = (svg_filename.
                            replace(_width, f'width="{SIZE}px"').
                            replace(_height, f'height="{SIZE}px"'))
        svg_bytes = svg_filename.encode('utf-8')
        svg_qbytes = QByteArray(svg_bytes)

    if not isinstance(color, QColor):
        color = QColor(color)

    renderer = QSvgRenderer(svg_qbytes)
    pixmap = QPixmap(width * xSize, height * xSize)
    pixmap = pixmap.scaled(width * xSize, height * xSize, Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setCompositionMode(
        painter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), color)
    painter.end()
    return pixmap


class QDropButton(QWidget):
    changeState = Signal(bool)
    clicked = Signal()

    def __init__(
            self,
            text: str,
            left_svg: str,
            right_svg: str,
            minus_svg: Optional[str] = None,
            only_click: bool = False,
            save_state: bool = False,
            text_alignment: Optional[str] = "left",
            *args,
            **kwargs
    ):
        super().__init__(*args, **kwargs)
        self.text = text
        self.left_svg = left_svg
        self.right_svg = right_svg
        self.minus_svg = minus_svg
        self.only_click = only_click
        self.save_state = save_state
        self.text_alignment = text_alignment
        self.stylecode = None

        if not self.minus_svg:
            self.save_state = False

        if self.save_state:
            self.only_click = True

        self.state_release = False
        self.size = (20, 20)
        self.initWidget()

    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)

        style = self.style()
        style.drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)
        painter.save()

    def setIconSize(self, width: Union[int, QSize], height: Optional[int] = None):
        if isinstance(width, QSize):
            width, height = width.width(), width.height()
        self.size = (width, height)
        self.right.setSvgSize(*self.size)

    def setIconLeftSize(self, width: Union[int, QSize], height: Optional[int] = None):
        if isinstance(width, QSize):
            width, height = width.width(), width.height()
        size = (width, height)
        self.left.setSvgSize(*size)

    def initWidget(self):
        """Initialize the widget."""
        layout = QHBoxLayout()
        layout.setSpacing(0)

        self.left = self.createButton(self.left_svg)
        self.label = self.createLabel(self.text)
        self.right = self.createButton(self.right_svg)

        layout.addWidget(self.left, alignment=Qt.AlignmentFlag.AlignLeft)
        if self.text_alignment == "right":
            layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        layout.addWidget(self.label, alignment=Qt.AlignmentFlag.AlignLeft)
        if self.text_alignment == "left":
            layout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        layout.addWidget(self.right, alignment=Qt.AlignmentFlag.AlignRight)

        self.setLayout(layout)
        self.setStyleSheet("QLabel {background: transparent;}")
        QTimer.singleShot(100, partial(self.leaveEvent, None))

    def createButton(self, svg_path):
        """Create and return a button with an icon."""
        button = QIconSvg(svg_path)
        button.setObjectName(self.objectName())
        button.setDisabledAnim(True)
        button.setSvgSize(*self.size)
        return button

    def createLabel(self, text):
        """Create and return a label."""
        label = QLabel(text)
        return label

    def updateIcon(self, color, hover=False):
        """Update the color of the icons."""
        if not color:
            return

        svgs = [self.left_svg, self.right_svg if not hover and not self.state_release else self.minus_svg]
        for svg, button in zip(svgs, [self.left, self.right]):
            pixmap = self.generateColoredPixmap(svg, color)
            button.setPixmap(pixmap)

    def generateColoredPixmap(self, svg_path, color):
        """Generate a colored pixmap from an SVG."""
        renderer = QSvgRenderer(svg_path)
        pixmap = QPixmap(*self.size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), color)
        painter.save()
        self.label.setStyleSheet("* {color: {COLOR};}".replace("{COLOR}", color))
        return pixmap

    def setPixmap(self, icon, pixmap):
        icon.setPixmap(pixmap)

    def enterEvent(self, event):
        hover = False
        if (self.minus_svg and not self.only_click):
            hover = True
            self.right.setIcon(self.minus_svg)

        if not self.stylecode:
            effective_style, self.stylecode = get_effective_style(self, hover=True)
        else:
            effective_style, _ = get_color(type(self).__name__, self.stylecode, hover=True)
        self.updateIcon(effective_style, hover)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.minus_svg:
            self.right.setIcon(self.right_svg)

        if not self.stylecode:
            effective_style, self.stylecode = get_effective_style(self)
        else:
            effective_style, _ = get_color(type(self).__name__, self.stylecode)
        self.updateIcon(effective_style, self.state_release)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        hover = False
        if self.minus_svg:
            hover = True
            self.right.setIcon(self.minus_svg)

        if not self.stylecode:
            effective_style, self.stylecode = get_effective_style(self, pressed=True)
        else:
            effective_style, _ = get_color(type(self).__name__, self.stylecode, pressed=True)
        self.updateIcon(effective_style, hover)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event=None):
        self.clicked.emit()
        hover = False
        if self.save_state:
            self.state_release = not self.state_release
            self.changeState.emit(self.state_release)

        if self.underMouse():
            """ If cursor on  widget """
            if (self.minus_svg and not self.only_click) or self.state_release:
                """ If widget have open svg and not active only_click """
                hover = True
                self.right.setIcon(self.minus_svg)

            if not self.stylecode:
                effective_style, self.stylecode = get_effective_style(self, hover=True)
            else:
                effective_style, _ = get_color(type(self).__name__, self.stylecode, hover=True)
        else:
            if not self.stylecode:
                effective_style, self.stylecode = get_effective_style(self, hover=False)
            else:
                effective_style, _ = get_color(type(self).__name__, self.stylecode, hover=True)

        self.updateIcon(effective_style, hover)
        if event:
            super().mouseReleaseEvent(event)


class QIconSvg(QLabel):
    clicked = Signal()

    def __init__(self, svg_path: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.svg_path = svg_path
        self.size = (20, 20)
        self.disable = False
        self.stylecode = None
        if self.svg_path:
            self.setIcon(self.svg_path)

    def setDisabledAnim(self, disable: bool):
        self.disable = disable

    def setSvgSize(self, width: Union[int, QSize], height: Optional[int] = None):
        if isinstance(width, QSize):
            width, height = width.width(), width.height()

        self.size = (width, height)
        self.leaveEvent(None)

    def setIcon(self, icon):
        self.svg_path = icon
        self.icon = QIcon(self.svg_path)
        self.setPixmap(self.icon.pixmap(QSize(*self.size)))
        self.setScaledContents(True)
        QTimer.singleShot(100, partial(self.leaveEvent, None))

    def updateIcon(self, color):
        if not color or not self.svg_path:
            return

        # Render SVG with the specified color
        renderer = QSvgRenderer(self.svg_path)
        pixmap = QPixmap(*self.size)  # Set desired icon size
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), color)
        painter.save()
        self.setPixmap(pixmap)

    def enterEvent(self, event):
        if not self.disable:
            if not self.stylecode:
                effective_style, self.stylecode = get_effective_style(self, hover=True)
            else:
                effective_style, _ = get_color(type(self).__name__, self.stylecode, hover=True)
            self.updateIcon(effective_style)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.disable:
            if not self.stylecode:
                effective_style, self.stylecode = get_effective_style(self)
            else:
                effective_style, _ = get_color(type(self).__name__, self.stylecode)
            self.updateIcon(effective_style)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if not self.disable:
            if not self.stylecode:
                effective_style, self.stylecode = get_effective_style(self, pressed=True)
            else:
                effective_style, _ = get_color(type(self).__name__, self.stylecode, pressed=True)
            self.updateIcon(effective_style)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.underMouse():
            if not self.stylecode:
                effective_style, self.stylecode = get_effective_style(self, hover=True)
            else:
                effective_style, _ = get_color(type(self).__name__, self.stylecode, hover=True)
        else:
            if not self.stylecode:
                effective_style, self.stylecode = get_effective_style(self)
            else:
                effective_style, _ = get_color(type(self).__name__, self.stylecode)

        if not self.disable:
            self.updateIcon(effective_style)

        self.clicked.emit()
        super().mouseReleaseEvent(event)


class QSvgButton(QPushButton):
    enter = Signal()
    leave = Signal()

    def __init__(self, svg_path: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.size = (20, 20)
        self.svg_path = svg_path
        self.stylecode = None
        if self.svg_path:
            self.setSvg(self.svg_path)

    def event(self, e):
        super().event(e)
        if str(e.type()) == "Type.PaletteChange" or e.type() == QEvent.Type.PaletteChange:
            self.leaveEvent(None)
        return True

    def setSvgSize(self, width: Union[int, QSize], height: Optional[int] = None):
        if isinstance(width, QSize):
            width, height = width.width(), width.height()

        self.setIconSize(QSize(width, height))
        self.size = (width, height)
        self.leaveEvent(None)

    def setSvg(self, icon):
        self.svg_path = icon
        QTimer.singleShot(100, partial(self.leaveEvent, None))

    def updateIcon(self, color):
        if not color or not self.svg_path:
            return

        renderer = QSvgRenderer(self.svg_path)
        pixmap = QPixmap(*self.size)  # Set desired icon size
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)

        renderer.setAspectRatioMode(Qt.KeepAspectRatio)

        renderer.render(painter)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pixmap.rect(), color)
        painter.save()
        self.setIcon(QIcon(pixmap))

    def enterEvent(self, event):
        self.enter.emit()
        effective_style, self.stylecode = get_effective_style(self, hover=True)
        self.updateIcon(effective_style)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.leave.emit()
        effective_style, self.stylecode = get_effective_style(self)
        self.updateIcon(effective_style)
        if event:
            super().leaveEvent(event)

    def mousePressEvent(self, event):
        effective_style, self.stylecode = get_effective_style(self, pressed=True)
        self.updateIcon(effective_style)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.underMouse():
            effective_style, self.stylecode = get_effective_style(self, hover=True)
        else:
            effective_style, self.stylecode = get_effective_style(self)

        self.updateIcon(effective_style)
        super().mouseReleaseEvent(event)


class QSvgButtonIcon(QSvgWidget):
    enter = Signal()
    leave = Signal()
    clicked = Signal()

    def __init__(self, svg_path: Optional[str] = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setContentsMargins(0, 0, 0, 0)
        self.size = (20, 20)
        self.svg_path = svg_path
        self.stylecode = None
        self.closed = False

        self.tree = None
        self.root = None
        if self.svg_path:
            self.setSvg(self.svg_path)

    def event(self, e):
        super().event(e)
        if str(e.type()) == "Type.PaletteChange" or e.type() == QEvent.Type.PaletteChange:
            self.leaveEvent(None)
        return True

    def setSvgSize(self, width: Union[int, QSize], height: Optional[int] = None):
        if isinstance(width, QSize):
            width, height = width.width(), width.height()

        self.setFixedSize(QSize(width, height))
        self.size = (width, height)
        self.leaveEvent(None)

    def setSvg(self, icon):
        self.tree = Et.parse(icon)
        self.root = self.tree.getroot()
        self.svg_path = icon
        QTimer.singleShot(100, partial(self.leaveEvent, None))

    def updateIcon(self, color):
        if not color or not self.svg_path:
            return

        c = QColor(color)
        paths = self.root.findall('.//{*}path')
        paths2 = self.root.findall('.//{*}svg')
        for path in paths + paths2:
            path.set('fill', c.name())

        self.load(self.get_QByteArray())
        self.setFixedSize(*self.size)

    def get_QByteArray(self):
        xmlstr = Et.tostring(self.root, encoding='utf8', method='xml')
        return QByteArray(xmlstr)

    def enterEvent(self, event):
        self.enter.emit()
        effective_style, self.stylecode = get_effective_style(self, hover=True)
        self.updateIcon(effective_style)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if self.closed:
            if event:
                event.ignore()
            return

        self.leave.emit()
        effective_style, self.stylecode = get_effective_style(self)
        self.updateIcon(effective_style)
        if event:
            super().leaveEvent(event)

    def mousePressEvent(self, event):
        effective_style, self.stylecode = get_effective_style(self, pressed=True)
        self.updateIcon(effective_style)
        super().mousePressEvent(event)

    def closeEvent(self, event):
        super().closeEvent(event)
        self.closed = True

    def deleteLater(self):
        super().deleteLater()
        self.closed = True

    def mouseReleaseEvent(self, event):
        if self.underMouse():
            effective_style, self.stylecode = get_effective_style(self, hover=True)
        else:
            effective_style, self.stylecode = get_effective_style(self)

        self.updateIcon(effective_style)
        super().mouseReleaseEvent(event)
        self.clicked.emit()


class SVGRenderRadioButton(QRadioButton):
    enter = Signal()
    leave = Signal()

    def __init__(self, svg_string: Optional[str] = None, size_ic: Optional[Tuple[int, int]] = (25, 25), *args,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.clear_cache = None
        self.size_ic = size_ic
        self.svg_string = svg_string
        self.closed = False
        self.set_string_svg(self.svg_string)
        self.setCheckable(False)
        self.toggled.connect(lambda e: self.leaveEvent())
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_name(self, name):
        self.setObjectName(name)
        self.__class__.__name__ = name
        self.leaveEvent()

    def event(self, e):
        super().event(e)
        if str(e.type()) == "Type.PaletteChange" or e.type() == QEvent.Type.PaletteChange:
            get_color.cache_clear()
            self.clear_cache = None
            self.after_load()
            self.leaveEvent(None)
        return True

    def setSvgSize(self, width: Union[int, QSize], height: Optional[int] = None):
        if isinstance(width, QSize):
            width, height = width.width(), width.height()

        self.size_ic = (width, height)
        self.leaveEvent()

    def set_string_svg(self, icon):
        if not icon:
            return

        self.svg_string = icon
        QTimer.singleShot(100, partial(self.leaveEvent))
        QTimer.singleShot(100, partial(self.after_load))

    def after_load(self):
        effective_style, self.clear_cache = get_effective_style(self, checked=True)
        effective_style, self.clear_cache = get_effective_style(self, hover=True)
        effective_style, self.clear_cache = get_effective_style(self, pressed=True)
        effective_style, self.clear_cache = get_effective_style(self)

    def updateIcon(self, color):
        if not color or not self.svg_string:
            return

        pixel = svg_to_pixmap(self.svg_string, *self.size_ic, color)
        self.setIcon(QIcon(pixel))
        self.setIconSize(QSize(*self.size_ic))

    def enterEvent(self, event=None):
        self.enter.emit()
        if self.clear_cache:
            effective_style, _ = get_color(type(self).__name__, self.clear_cache,
                                           hover=True if not self.isChecked() else False, checked=self.isChecked())
        else:
            effective_style, self.clear_cache = get_effective_style(self, hover=True if not self.isChecked() else False,
                                                                    checked=self.isChecked())
        if event:
            super().enterEvent(event)
        self.updateIcon(effective_style)

    def leaveEvent(self, event=None):
        if self.closed:
            if event:
                event.ignore()
            return
        try:
            self.leave.emit()
        except RuntimeError:
            return

        if self.clear_cache:
            effective_style, _ = get_color(type(self).__name__, self.clear_cache, checked=self.isChecked())
        else:
            effective_style, self.clear_cache = get_effective_style(self, checked=self.isChecked())
        if event:
            super().leaveEvent(event)
        self.updateIcon(effective_style)

    def mousePressEvent(self, event):
        if self.clear_cache:
            effective_style, _ = get_color(type(self).__name__, self.clear_cache, pressed=True)
        else:
            effective_style, self.clear_cache = get_effective_style(self, pressed=True)

        self.updateIcon(effective_style)
        super().mousePressEvent(event)

    def closeEvent(self, event):
        super().closeEvent(event)
        self.closed = True

    def deleteLater(self):
        super().deleteLater()
        self.closed = True

    def mouseReleaseEvent(self, event):
        if self.underMouse():
            if self.clear_cache:
                effective_style, _ = get_color(type(self).__name__, self.clear_cache, hover=True)
            else:
                effective_style, self.clear_cache = get_effective_style(self, hover=True)
        else:
            if self.clear_cache:
                effective_style, _ = get_color(type(self).__name__, self.clear_cache)
            else:
                effective_style, self.clear_cache = get_effective_style(self)

        self.updateIcon(effective_style)
        super().mouseReleaseEvent(event)


class SVGRenderButton(QToolButton):
    enter = Signal()
    leave = Signal()

    def __init__(self, svg_string: Optional[str] = None, size_ic: Optional[Tuple[int, int]] = (25, 25), *args,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.clear_cache = None
        self.size_ic = size_ic
        self.svg_string = svg_string
        self.closed = False
        self.set_string_svg(self.svg_string)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_name(self, name):
        self.setObjectName(name)
        self.__class__.__name__ = name
        self.leaveEvent()

    def event(self, e):
        super().event(e)

        if str(e.type()) == "Type.PaletteChange" or e.type() == QEvent.Type.PaletteChange:
            get_color.cache_clear()
            self.clear_cache = None
            self.after_load()
            self.leaveEvent(None)

        return True

    def setSvgSize(self, width: Union[int, QSize], height: Optional[int] = None):
        if isinstance(width, QSize):
            width, height = width.width(), width.height()

        self.size_ic = (width, height)
        self.leaveEvent()

    def set_string_svg(self, icon):
        if not icon:
            return

        self.svg_string = icon

        QTimer.singleShot(100, partial(self.leaveEvent))
        QTimer.singleShot(100, partial(self.after_load))

    def after_load(self):
        if self.closed:
            return

        effective_style, self.clear_cache = get_effective_style(self, checked=True)
        effective_style, self.clear_cache = get_effective_style(self, hover=True)
        effective_style, self.clear_cache = get_effective_style(self, pressed=True)
        effective_style, self.clear_cache = get_effective_style(self)

    def updateIcon(self, color):
        if not color or not self.svg_string:
            return

        pixel = svg_to_pixmap(self.svg_string, *self.size_ic, color)
        self.setIcon(QIcon(pixel))
        self.setIconSize(QSize(*self.size_ic))

    def enterEvent(self, event=None):
        self.enter.emit()
        if self.clear_cache:
            effective_style, _ = get_color(type(self).__name__, self.clear_cache, hover=True)
        else:
            effective_style, self.clear_cache = get_effective_style(self, hover=True)
        if event:
            super().enterEvent(event)
        self.updateIcon(effective_style)

    def leaveEvent(self, event=None):
        if self.closed:
            if event:
                event.ignore()
            return

        try:
            self.leave.emit()
        except RuntimeError:
            return

        if self.clear_cache:
            effective_style, _ = get_color(type(self).__name__, self.clear_cache, checked=self.isChecked())
        else:
            effective_style, self.clear_cache = get_effective_style(self, checked=self.isChecked())
        if event:
            super().leaveEvent(event)
        self.updateIcon(effective_style)

    def mousePressEvent(self, event):
        if self.clear_cache:
            effective_style, _ = get_color(type(self).__name__, self.clear_cache, pressed=True)
        else:
            effective_style, self.clear_cache = get_effective_style(self, pressed=True)

        self.updateIcon(effective_style)
        super().mousePressEvent(event)

    def closeEvent(self, event):
        super().closeEvent(event)
        self.closed = True

    def deleteLater(self):
        super().deleteLater()
        self.closed = True

    def mouseReleaseEvent(self, event):
        if self.underMouse():
            if self.clear_cache:
                effective_style, _ = get_color(type(self).__name__, self.clear_cache, hover=True)
            else:
                effective_style, self.clear_cache = get_effective_style(self, hover=True)
        else:
            if self.clear_cache:
                effective_style, _ = get_color(type(self).__name__, self.clear_cache)
            else:
                effective_style, self.clear_cache = get_effective_style(self)

        self.updateIcon(effective_style)
        super().mouseReleaseEvent(event)


class SVGRenderIcon(QPushButton):
    enter = Signal()
    leave = Signal()

    def __init__(self, svg_string: Optional[str] = None, size_ic: Optional[Tuple[int, int]] = (25, 25), *args,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.clear_cache = None
        self.size_ic = size_ic
        self.svg_string = svg_string
        self.closed = False
        self.toggled.connect(lambda e: self.leaveEvent())
        self.set_string_svg(self.svg_string)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_name(self, name):
        self.setObjectName(name)
        self.__class__.__name__ = name
        self.leaveEvent()

    def event(self, e):
        super().event(e)
        if str(e.type()) == "Type.PaletteChange" or e.type() == QEvent.Type.PaletteChange:
            get_color.cache_clear()
            self.clear_cache = None
            self.after_load()
            self.leaveEvent(None)
        return True

    def setSvgSize(self, width: Union[int, QSize], height: Optional[int] = None):
        if isinstance(width, QSize):
            width, height = width.width(), width.height()

        self.size_ic = (width, height)
        self.leaveEvent()

    def set_string_svg(self, icon):
        if not icon:
            return

        self.svg_string = icon

        QTimer.singleShot(100, partial(self.leaveEvent))
        QTimer.singleShot(100, partial(self.after_load))

    def after_load(self):
        effective_style, self.clear_cache = get_effective_style(self, checked=True)
        effective_style, self.clear_cache = get_effective_style(self, hover=True)
        effective_style, self.clear_cache = get_effective_style(self, pressed=True)
        effective_style, self.clear_cache = get_effective_style(self)

    def updateIcon(self, color):
        if not color or not self.svg_string:
            return

        pixel = svg_to_pixmap(self.svg_string, *self.size_ic, color)
        self.setIcon(QIcon(pixel))
        self.setIconSize(QSize(*self.size_ic))

    def enterEvent(self, event=None):
        self.enter.emit()
        if self.clear_cache:
            effective_style, _ = get_color(type(self).__name__, self.clear_cache, hover=True)
        else:
            effective_style, self.clear_cache = get_effective_style(self, hover=True)
        if event:
            super().enterEvent(event)
        self.updateIcon(effective_style)

    def leaveEvent(self, event=None):
        if self.closed:
            if event:
                event.ignore()
            return

        try:
            self.leave.emit()
        except RuntimeError:
            return

        if self.clear_cache:
            effective_style, _ = get_color(type(self).__name__, self.clear_cache, checked=self.isChecked())
        else:
            effective_style, self.clear_cache = get_effective_style(self, checked=self.isChecked())
        if event:
            super().leaveEvent(event)
        self.updateIcon(effective_style)

    def mousePressEvent(self, event):
        if self.clear_cache:
            effective_style, _ = get_color(type(self).__name__, self.clear_cache, pressed=True)
        else:
            effective_style, self.clear_cache = get_effective_style(self, pressed=True)

        self.updateIcon(effective_style)
        super().mousePressEvent(event)

    def closeEvent(self, event):
        self.enter.disconnect()
        self.leave.disconnect()
        super().closeEvent(event)
        self.closed = True

    def deleteLater(self):
        self.enter.disconnect()
        self.leave.disconnect()
        super().deleteLater()
        self.closed = True

    def mouseReleaseEvent(self, event):
        if self.underMouse():
            if self.clear_cache:
                effective_style, _ = get_color(type(self).__name__, self.clear_cache, hover=True)
            else:
                effective_style, self.clear_cache = get_effective_style(self, hover=True)
        else:
            if self.clear_cache:
                effective_style, _ = get_color(type(self).__name__, self.clear_cache)
            else:
                effective_style, self.clear_cache = get_effective_style(self)

        self.updateIcon(effective_style)
        super().mouseReleaseEvent(event)
