"""Notebook: a column of cells. A cell shows its rendered result; click it to edit."""
import html
import re

import sympy as sp
from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QColorDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QMenu,
                               QPlainTextEdit, QPushButton, QScrollArea, QSizePolicy, QSlider,
                               QToolButton, QVBoxLayout, QWidget)

from ..engine import dimension
from ..i18n import tr
from . import mathrender

PALETTE = ['#2F6FED', '#E8590C', '#2B8A3E', '#C2255C', '#7048E8', '#0C8599', '#E67700', '#495057']


def cell_color(session, cell):
    return cell.color or PALETTE[session.index(cell) % len(PALETTE)]


class ClickLabel(QLabel):
    def __init__(self, on_click):
        super().__init__()
        self.on_click = on_click
        self.setTextFormat(Qt.RichText)
        self.setWordWrap(True)
        self.setCursor(Qt.IBeamCursor)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.on_click()
        super().mousePressEvent(e)


class CellWidget(QFrame):
    def __init__(self, nb, cell):
        super().__init__()
        self.nb, self.cell = nb, cell
        self.setObjectName('cell')
        self.setProperty('editing', False)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(6, 4, 8, 4)
        lay.setSpacing(6)

        gutter = QVBoxLayout()
        gutter.setSpacing(2)
        self.num = QLabel()
        self.num.setObjectName('cellnum')
        self.num.setAlignment(Qt.AlignHCenter)
        self.dot = QToolButton()
        self.dot.setObjectName('dot')
        self.dot.setFixedSize(18, 18)
        self.dot.clicked.connect(self.toggle_visible)
        gutter.addWidget(self.num)
        gutter.addWidget(self.dot, 0, Qt.AlignHCenter)
        gutter.addStretch()
        lay.addLayout(gutter)

        body = QVBoxLayout()
        body.setSpacing(3)
        if cell.kind == 'math':
            self.editor = QLineEdit()
            self.editor.setFont(QFont('monospace', 11))
            self.editor.setLayoutDirection(Qt.LeftToRight)     # code and math stay LTR in Arabic too
        else:
            self.editor = QPlainTextEdit()
            self.editor.setFixedHeight(70)
        self.editor.setObjectName('editor')
        self.editor.installEventFilter(self)
        self.view = ClickLabel(self.start_edit)
        self.view.setObjectName('view')
        if cell.kind == 'math':
            self.view.setLayoutDirection(Qt.LeftToRight)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.valueChanged.connect(self.slider_moved)
        self.slider.sliderReleased.connect(nb.refresh_outputs_now)
        for w in (self.editor, self.view, self.slider):
            body.addWidget(w)
        lay.addLayout(body, 1)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.menu)
        self.refresh()
        self.show_view()

    # ------------------------------------------------------------ display
    def refresh(self):
        c, s = self.cell, self.nb.session
        self.num.setText(str(s.index(c) + 1))
        drawable = c.kind == 'math' and dimension(c.value) is not None
        self.dot.setVisible(drawable)
        col = cell_color(s, c)
        self.dot.setStyleSheet('QToolButton#dot{border:2px solid %s;border-radius:9px;background:%s}'
                               % (col, col if c.visible else 'transparent'))
        self.slider.setVisible(bool(c.slider))
        if c.slider:
            sl = c.slider
            n = max(1, round((sl.hi - sl.lo) / sl.step))
            self.slider.blockSignals(True)
            self.slider.setRange(0, n)
            self.slider.setValue(round((float(c.value) - sl.lo) / sl.step))
            self.slider.blockSignals(False)
        self.view.setText(self.view_html())

    def view_html(self):
        c = self.cell
        if c.kind == 'text':
            if not c.text.strip():
                return '<span style="color:#9aa0aa">%s</span>' % html.escape(tr('text_placeholder', self.nb.lang))
            return '<div style="font-size:14px">%s</div>' % mathrender.html_text_with_math(c.parts, 13)
        if not c.text.strip():
            return '<span style="color:#9aa0aa">%s</span>' % html.escape(tr('placeholder', self.nb.lang))
        # isolate Arabic words so the numbers after them keep left-to-right order
        code, sep, note = c.text.partition('#')
        code = re.sub(r'([\u0600-\u06FF][\u0600-\u06FF_\w]*)', '\u200e\\1\u200e', html.escape(code))
        code += html.escape(sep) + '<span dir="auto">%s</span>' % html.escape(note) if sep else ''
        src = '<div dir="ltr" style="color:#8a909c;font-family:monospace;font-size:11px">%s</div>' % code
        if c.error:
            return src + '<div style="color:#c92a2a">⚠ %s</div>' % html.escape(c.error)
        if c.value is None:
            return src
        label = '<span style="font-family:serif;font-style:italic;font-size:15px">%s</span>&nbsp;' % \
            html.escape(c.label) if c.label else ''
        math = mathrender.html_math(c.latex, 14)
        if math is None:      # matrices and other formulas mathtext can't draw
            math = '<pre style="margin:0">%s</pre>' % html.escape(sp.pretty(c.value, use_unicode=True))
        note = '&nbsp;&nbsp;<span style="color:#6b7280;font-style:italic">%s</span>' % html.escape(c.note) \
            if c.note else ''
        return src + '<div dir="ltr" style="margin-top:2px">%s%s%s</div>' % (label, math, note)

    # ------------------------------------------------------------ editing
    def start_edit(self):
        self.editor.setVisible(True)
        self.view.setVisible(False)
        self.setProperty('editing', True)
        self.style().polish(self)
        if isinstance(self.editor, QLineEdit):
            self.editor.setText(self.cell.text)
        else:
            self.editor.setPlainText(self.cell.text)
        self.editor.setFocus()
        self.nb.active = self

    def show_view(self):
        self.editor.setVisible(False)
        self.view.setVisible(True)
        self.setProperty('editing', False)
        self.style().polish(self)

    def text(self):
        return self.editor.text() if isinstance(self.editor, QLineEdit) else self.editor.toPlainText()

    def commit(self, go_next=True):
        self.nb.commit(self, self.text(), go_next)

    def eventFilter(self, obj, e):
        if e.type() == QEvent.FocusIn:
            self.nb.active = self
        if e.type() == QEvent.KeyPress:
            k, mod = e.key(), e.modifiers()
            enter = k in (Qt.Key_Return, Qt.Key_Enter)
            if enter and (isinstance(self.editor, QLineEdit) or mod & (Qt.ControlModifier | Qt.ShiftModifier)):
                self.commit()
                return True
            if k == Qt.Key_Escape:
                self.show_view()
                return True
            if isinstance(self.editor, QLineEdit) and k in (Qt.Key_Up, Qt.Key_Down):
                self.nb.commit(self, self.text(), go_next=False)
                self.nb.edit_neighbour(self, -1 if k == Qt.Key_Up else 1)
                return True
        return super().eventFilter(obj, e)

    def insert(self, text, cursor_back=0):
        if not self.property('editing'):
            self.start_edit()
        if isinstance(self.editor, QLineEdit):
            self.editor.insert(text)
            self.editor.setCursorPosition(self.editor.cursorPosition() - cursor_back)
        else:
            cur = self.editor.textCursor()
            cur.insertText(text)
            cur.setPosition(cur.position() - cursor_back)
            self.editor.setTextCursor(cur)
        self.editor.setFocus()

    # ------------------------------------------------------------ actions
    def toggle_visible(self):
        self.cell.visible = not self.cell.visible
        self.refresh()
        self.nb.changed()

    def slider_moved(self, i):
        sl = self.cell.slider
        if sl:
            self.nb.session.move_slider(self.cell, sl.lo + i * sl.step)
            self.nb.changed(light=True)

    def menu(self, pos):
        L = self.nb.lang
        m = QMenu(self)
        m.addAction(tr('insert_above', L), lambda: self.nb.insert(self, 0))
        m.addAction(tr('insert_below', L), lambda: self.nb.insert(self, 1))
        m.addAction(tr('move_up', L), lambda: self.nb.move(self, -1))
        m.addAction(tr('move_down', L), lambda: self.nb.move(self, 1))
        m.addSeparator()
        m.addAction(tr('to_math' if self.cell.kind == 'text' else 'to_text', L), lambda: self.nb.convert(self))
        if self.dot.isVisible():
            m.addAction(tr('show', L), self.toggle_visible)
            m.addAction(tr('color', L), self.pick_color)
        m.addSeparator()
        m.addAction(tr('delete', L), lambda: self.nb.delete(self))
        m.exec(self.mapToGlobal(pos))

    def pick_color(self):
        c = QColorDialog.getColor(QColor(cell_color(self.nb.session, self.cell)), self)
        if c.isValid():
            self.cell.color = c.name()
            self.refresh()
            self.nb.changed()


class NotebookWidget(QScrollArea):
    def __init__(self, session, on_changed, lang='fr'):
        super().__init__()
        self.session, self.on_changed, self.lang = session, on_changed, lang
        self.active = None
        self.widgets = []
        self.setWidgetResizable(True)
        self.setObjectName('notebook')
        inner = QWidget()
        inner.setObjectName('nbinner')
        self.col = QVBoxLayout(inner)
        self.col.setContentsMargins(10, 10, 10, 10)
        self.col.setSpacing(6)
        bar = QHBoxLayout()
        self.b_math, self.b_text = QPushButton(), QPushButton()
        for b, kind in ((self.b_math, 'math'), (self.b_text, 'text')):
            b.setObjectName('addbtn')
            b.clicked.connect(lambda _=False, k=kind: self.append(k))
            bar.addWidget(b)
        bar.addStretch()
        self.col.addLayout(bar)
        self.col.addStretch()
        self.setWidget(inner)
        self._timer = QTimer(self, singleShot=True, interval=200, timeout=self.refresh_outputs_now)
        self.retranslate()
        self.rebuild()

    def retranslate(self):
        self.b_math.setText(tr('add_math', self.lang))
        self.b_text.setText(tr('add_text', self.lang))
        for w in self.widgets:
            w.refresh()
            if isinstance(w.editor, QLineEdit):
                w.editor.setPlaceholderText(tr('placeholder', self.lang))

    def rebuild(self):
        for w in self.widgets:
            w.setParent(None)
            w.deleteLater()
        self.widgets = []
        if not self.session.cells:
            self.session.add_cell()
        for i, c in enumerate(self.session.cells):
            w = CellWidget(self, c)
            self.col.insertWidget(i, w)
            self.widgets.append(w)
        self.active = None
        self.retranslate()

    def refresh_outputs_now(self):
        for w in self.widgets:
            w.refresh()

    def changed(self, light=False):
        """light: graphics only now, cell outputs a bit later (slider/drag)."""
        if light:
            self._timer.start()
        else:
            self.refresh_outputs_now()
        self.on_changed()

    def widget_of(self, cell):
        return next(w for w in self.widgets if w.cell is cell)

    def commit(self, w, text, go_next=True):
        if text != w.cell.text or w.cell.value is None and not w.cell.error:
            self.session.set_text(w.cell, text)
            self.changed()
        w.show_view()
        if go_next:
            i = self.widgets.index(w)
            if i == len(self.widgets) - 1 and text.strip():
                self.append(w.cell.kind if w.cell.kind == 'math' else 'math')
            elif i < len(self.widgets) - 1:
                self.widgets[i + 1].start_edit()

    def edit_neighbour(self, w, step):
        i = self.widgets.index(w) + step
        if 0 <= i < len(self.widgets):
            self.widgets[i].start_edit()

    def append(self, kind='math'):
        self.session.add_cell('', kind)
        self.rebuild()
        self.widgets[-1].start_edit()
        QTimer.singleShot(0, lambda: self.verticalScrollBar().setValue(self.verticalScrollBar().maximum()))

    def insert(self, w, offset):
        i = self.widgets.index(w) + offset
        self.session.add_cell('', 'math', at=i)
        self.session.evaluate_all()
        self.rebuild()
        self.widgets[i].start_edit()
        self.on_changed()

    def move(self, w, step):
        cells = self.session.cells
        i = cells.index(w.cell)
        j = i + step
        if 0 <= j < len(cells):
            cells[i], cells[j] = cells[j], cells[i]
            self.session.evaluate_all()
            self.rebuild()
            self.on_changed()

    def convert(self, w):
        w.cell.kind = 'math' if w.cell.kind == 'text' else 'text'
        self.session.evaluate_all()
        self.rebuild()
        self.on_changed()

    def delete(self, w):
        self.session.remove_cell(w.cell)
        self.rebuild()
        self.on_changed()

    def insert_text(self, text, cursor_back=0):
        """From the palette: into the cell being edited, else into the last cell."""
        w = self.active if self.active in self.widgets else self.widgets[-1]
        w.insert(text, cursor_back)

    def set_lang(self, lang):
        self.lang = lang
        self.retranslate()
