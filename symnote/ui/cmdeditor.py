"""Commands editor: browse built-ins, write new commands in Python (function run)."""
import inspect

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QFormLayout, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QMessageBox, QPlainTextEdit, QPushButton,
                               QSplitter, QVBoxLayout, QWidget)

from ..commands import CATEGORIES, compile_user
from ..i18n import tr

TEMPLATE = '''def run(f, a):
    """Example: equation of the normal line to the graph of f at x = a."""
    e, v = _body(f)
    d = sp.diff(e, v).subs(v, a)
    return sp.Eq(y, sp.expand(-(x - a) / d + e.subs(v, a)))
'''


class CommandsEditor(QDialog):
    def __init__(self, session, lang, on_saved, parent=None):
        super().__init__(parent)
        self.session, self.reg, self.lang, self.on_saved = session, session.registry, lang, on_saved
        L = lang
        self.setWindowTitle(tr('ce_title', L))
        self.resize(900, 560)
        split = QSplitter()
        self.list = QListWidget()
        self.list.currentTextChanged.connect(self.show_command)
        split.addWidget(self.list)

        right = QWidget()
        v = QVBoxLayout(right)
        form = QFormLayout()
        self.name, self.fr, self.ar, self.hint = QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit()
        self.cat = QComboBox()
        for c in CATEGORIES:
            self.cat.addItem(tr(c, L), c)
        self.pal = QCheckBox()
        for key, w in (('ce_name', self.name), ('ce_fr', self.fr), ('ce_ar', self.ar),
                       ('ce_cat', self.cat), ('ce_hint', self.hint), ('ce_palette', self.pal)):
            form.addRow(tr(key, L), w)
        v.addLayout(form)
        self.info = QLabel()
        self.info.setStyleSheet('color:#6b7280')
        v.addWidget(QLabel(tr('ce_code', L)))
        v.addWidget(self.info)
        self.code = QPlainTextEdit()
        self.code.setFont(QFont('monospace', 10))
        v.addWidget(self.code, 1)
        test = QHBoxLayout()
        self.test_args = QLineEdit()
        self.test_args.setPlaceholderText(tr('ce_test_args', L))
        self.test_out = QLabel()
        self.test_out.setWordWrap(True)
        b_test = QPushButton(tr('ce_test', L))
        b_test.clicked.connect(self.test)
        test.addWidget(self.test_args, 1)
        test.addWidget(b_test)
        v.addLayout(test)
        v.addWidget(self.test_out)
        btns = QHBoxLayout()
        for key, fn in (('ce_new', self.new), ('ce_save', self.save), ('ce_delete', self.delete)):
            b = QPushButton(tr(key, L))
            b.clicked.connect(fn)
            btns.addWidget(b)
        btns.addStretch()
        v.addLayout(btns)
        split.addWidget(right)
        split.setSizes([220, 680])
        QVBoxLayout(self).addWidget(split)
        self.fill_list()

    def fill_list(self, select=None):
        self.list.blockSignals(True)
        self.list.clear()
        users = sorted(c.name for c in self.reg.user_commands())
        builtins = sorted(n for n, c in self.reg.commands.items() if c.code is None)
        for n in users + builtins:
            self.list.addItem(n)
        self.list.blockSignals(False)
        items = self.list.findItems(select, Qt.MatchExactly) if select else []
        self.list.setCurrentItem(items[0] if items else self.list.item(0))

    def show_command(self, name):
        c = self.reg.commands.get(name)
        if not c:
            return
        self.name.setText(c.name)
        self.fr.setText(c.fr)
        self.ar.setText(c.ar)
        self.hint.setText(c.hint)
        self.cat.setCurrentIndex(max(0, self.cat.findData(c.category)))
        self.pal.setChecked(c.palette)
        builtin = c.code is None
        self.code.setPlainText(inspect.getsource(c.func) if builtin else c.code)
        for w in (self.name, self.fr, self.ar, self.hint, self.code):
            w.setReadOnly(builtin)
        self.cat.setEnabled(not builtin)
        self.info.setText(tr('ce_builtin', self.lang) if builtin else
                          'sp = sympy, x y z t, _body(f), _pt(p), Point, Line, Circle…')

    def new(self):
        self.list.clearSelection()
        for w in (self.name, self.fr, self.ar, self.hint, self.code):
            w.setReadOnly(False)
        self.cat.setEnabled(True)
        self.name.setText('Normal')
        self.fr.setText('Normale')
        self.ar.setText('منظمي')
        self.hint.setText('f, a')
        self.cat.setCurrentIndex(self.cat.findData('calculus'))
        self.pal.setChecked(True)
        self.code.setPlainText(TEMPLATE)
        self.info.setText('sp = sympy, x y z t, _body(f), _pt(p), Point, Line, Circle…')
        self.name.setFocus()

    def data(self):
        return dict(name=self.name.text().strip(), fr=self.fr.text().strip(), ar=self.ar.text().strip(),
                    category=self.cat.currentData(), hint=self.hint.text().strip(),
                    code=self.code.toPlainText(), palette=self.pal.isChecked())

    def save(self):
        d = self.data()
        if not d['name'].isidentifier():
            return QMessageBox.warning(self, tr('error', self.lang), 'Name must be an identifier')
        old = self.reg.commands.get(d['name'])
        if old is not None and old.code is None:
            return QMessageBox.warning(self, tr('error', self.lang), tr('reserved', self.lang))
        clash = [a for a in (d['fr'], d['ar']) if a and self.reg.aliases().get(a) not in (None, d['name'])]
        if clash:
            return QMessageBox.warning(self, tr('error', self.lang), '%s: %s' % (tr('reserved', self.lang), clash[0]))
        try:
            self.reg.add_user(d)
        except Exception as e:
            return QMessageBox.warning(self, tr('error', self.lang), str(e))
        self.reg.save_user()
        self.fill_list(d['name'])
        self.on_saved()

    def delete(self):
        name = self.name.text().strip()
        c = self.reg.commands.get(name)
        if c is None or c.code is None:
            return
        self.reg.remove(name)
        self.reg.save_user()
        self.fill_list()
        self.on_saved()

    def test(self):
        try:
            f = compile_user(self.code.toPlainText()) if not self.code.isReadOnly() \
                else self.reg.commands[self.name.text()].func
            args = self.session.evaluate_expression('[%s]' % self.test_args.text()) if self.test_args.text().strip() else []
            self.test_out.setText('→ %s' % (f(*args),))
        except Exception as e:
            self.test_out.setText('⚠ %s: %s' % (type(e).__name__, e))
