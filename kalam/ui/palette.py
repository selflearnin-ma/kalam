"""Palette: buttons that insert commands (in the current language) into the active cell."""
from PySide6.QtWidgets import QGridLayout, QPushButton, QScrollArea, QTabWidget, QWidget

from ..commands import CATEGORIES
from ..i18n import tr

SYMBOLS = ['π', 'e', 'i', '√(', '^', '²', '∞', '≤', '≥', '≠', '×', '÷', '(', ')', '[', ']',
           'x', 'y', 'z', 't', 'θ', 'α', '$', '#']
COLS = 3


class Palette(QTabWidget):
    def __init__(self, registry, insert, lang='fr'):
        super().__init__()
        self.registry, self.insert, self.lang = registry, insert, lang
        self.setObjectName('palette')
        self.setDocumentMode(True)
        self.setUsesScrollButtons(True)
        self.rebuild()

    def _page(self, buttons):
        inner = QWidget()
        g = QGridLayout(inner)
        g.setContentsMargins(4, 4, 4, 4)
        g.setSpacing(4)
        for i, b in enumerate(buttons):
            g.addWidget(b, i // COLS, i % COLS)
        g.setRowStretch(len(buttons) // COLS + 1, 1)
        sc = QScrollArea()
        sc.setWidgetResizable(True)
        sc.setWidget(inner)
        sc.setFrameShape(QScrollArea.NoFrame)
        return sc

    def _button(self, text, tip, insert, back=0):
        b = QPushButton(text)
        b.setObjectName('palbtn')
        b.setToolTip(tip)
        b.clicked.connect(lambda: self.insert(insert, back))
        return b

    def rebuild(self):
        cur = self.currentIndex()
        self.clear()
        L = self.lang
        sym = [self._button(s, s, s) for s in SYMBOLS]
        self.addTab(self._page(sym), tr('symbols', L))
        cmds = [c for c in self.registry.commands.values() if c.palette]
        for cat in CATEGORIES:
            bs = [self._button(c.label(L), '%s(%s)' % (c.label(L), c.hint), c.label(L) + '()', 1)
                  for c in cmds if c.category == cat and c.code is None]
            self.addTab(self._page(bs), tr(cat, L))
        user = [self._button(c.label(L), '%s(%s)' % (c.label(L), c.hint), c.label(L) + '()', 1)
                for c in cmds if c.code is not None]
        if user:
            self.addTab(self._page(user), tr('user', L))
        self.setCurrentIndex(max(cur, 1) if cur < self.count() else 1)

    def set_lang(self, lang):
        self.lang = lang
        self.rebuild()
