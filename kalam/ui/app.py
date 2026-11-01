"""Kalam main window: palette + notebook on one side, 2D / 3D graphics on the other."""
import os
import sys

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QApplication, QComboBox, QFileDialog, QMainWindow, QMessageBox,
                               QSizePolicy, QSplitter, QTabWidget, QToolBar, QVBoxLayout, QWidget)

from ..commands import Registry
from ..engine import Session
from ..export import figure_tkz, load_klm, save_klm, to_latex, to_python
from ..i18n import LANGS, tr
from .canvas2d import Canvas2D
from .cmdeditor import CommandsEditor
from .notebook import NotebookWidget
from .palette import Palette
from .view3d import View3D

STYLE = """
* { font-size: 13px; }
QMainWindow, #nbinner { background: #f6f7f9; }
QToolBar { background: #ffffff; border: none; border-bottom: 1px solid #e5e7eb; spacing: 4px; padding: 4px; }
QToolBar QToolButton { padding: 5px 9px; border-radius: 6px; color: #1f2430; }
QToolBar QToolButton:hover { background: #eef1f6; }
QSplitter::handle { background: #e5e7eb; width: 1px; }
#cell { background: #ffffff; border: 1px solid #e7e9ee; border-radius: 10px; }
#cell[editing="true"] { border: 1.5px solid #4c6ef5; }
#cellnum { color: #a0a6b1; font-size: 11px; min-width: 18px; }
#editor { border: none; background: transparent; padding: 4px 2px; font-size: 14px; }
#addbtn { background: transparent; border: 1px dashed #c5cad3; border-radius: 8px; padding: 5px 12px; color: #4c6ef5; }
#addbtn:hover { background: #eef2ff; }
#palette QTabBar::tab { padding: 5px 10px; color: #5b6170; border: none; }
#palette QTabBar::tab:selected { color: #4c6ef5; border-bottom: 2px solid #4c6ef5; }
#palbtn { background: #ffffff; border: 1px solid #e3e6eb; border-radius: 7px; padding: 5px 6px; color: #1f2430; }
#palbtn:hover { background: #eef2ff; border-color: #4c6ef5; }
#canvasbtn { background: #ffffff; border: 1px solid #dfe3e8; border-radius: 8px; min-width: 28px; min-height: 28px; font-size: 15px; }
#canvasbtn:hover { background: #eef2ff; }
QTabWidget#views::pane { border: none; }
QTabWidget#views QTabBar::tab { padding: 7px 16px; color: #5b6170; border: none; }
QTabWidget#views QTabBar::tab:selected { color: #1f2430; border-bottom: 2px solid #4c6ef5; }
QScrollArea { border: none; }
QSlider::groove:horizontal { height: 4px; background: #e3e6eb; border-radius: 2px; }
QSlider::handle:horizontal { background: #4c6ef5; width: 14px; margin: -6px 0; border-radius: 7px; }
"""


class MainWindow(QMainWindow):
    def __init__(self, path=None):
        super().__init__()
        self.settings = QSettings('Kalam', 'Kalam')
        self.lang = self.settings.value('lang', 'fr')
        self.path, self.modified = None, False
        self.session = Session(Registry())

        self.canvas = Canvas2D(self.session)
        self.canvas.point_dragged.connect(self.on_drag)
        self.canvas.drag_finished.connect(lambda: self.notebook.refresh_outputs_now())
        self.view3d = View3D(self.session)
        self.views = QTabWidget()
        self.views.setObjectName('views')
        self.views.setDocumentMode(True)
        self.views.addTab(self.canvas, '')
        self.views.addTab(self.view3d, '')
        self.views.currentChanged.connect(lambda _: self.redraw())

        self.notebook = NotebookWidget(self.session, self.on_changed, self.lang)
        self.palette = Palette(self.session.registry, self.notebook.insert_text, self.lang)
        self.palette.setFixedHeight(150)
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(0)
        lv.addWidget(self.palette)
        lv.addWidget(self.notebook, 1)

        split = QSplitter(Qt.Horizontal)
        split.addWidget(left)
        split.addWidget(self.views)
        split.setSizes([480, 720])
        split.setChildrenCollapsible(False)
        self.setCentralWidget(split)
        self.build_toolbar()
        self.retranslate()
        self.resize(1280, 800)
        if path:
            self.open(path)

    # ------------------------------------------------------------ ui
    def build_toolbar(self):
        tb = QToolBar()
        tb.setMovable(False)
        self.addToolBar(tb)
        self.actions = {}
        for key, fn, sc in (('new', self.new, QKeySequence.New), ('open', self.open, QKeySequence.Open),
                            ('save', self.save, QKeySequence.Save), (None, None, None),
                            ('export_py', self.export_py, None), ('export_tex', self.export_tex, None),
                            ('export_fig', self.export_fig, None), (None, None, None),
                            ('cmd_editor', self.edit_commands, None)):
            if key is None:
                tb.addSeparator()
                continue
            a = QAction(self)
            a.triggered.connect(lambda _=False, f=fn: f())
            if sc:
                a.setShortcut(sc)
            tb.addAction(a)
            self.actions[key] = a
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)
        self.lang_box = QComboBox()
        for code, name in LANGS.items():
            self.lang_box.addItem(name, code)
        self.lang_box.setCurrentIndex(self.lang_box.findData(self.lang))
        self.lang_box.currentIndexChanged.connect(lambda _: self.set_lang(self.lang_box.currentData()))
        tb.addWidget(self.lang_box)

    def retranslate(self):
        L = self.lang
        QApplication.instance().setLayoutDirection(Qt.RightToLeft if L == 'ar' else Qt.LeftToRight)
        for k, a in self.actions.items():
            a.setText(tr(k, L))
        self.views.setTabText(0, tr('graphics2d', L))
        self.views.setTabText(1, tr('graphics3d', L))
        for b, k in zip(self.canvas.buttons, ('zoom_in', 'zoom_out', 'home')):
            b.setToolTip(tr(k, L))
        self.update_title()

    def set_lang(self, lang):
        self.lang = lang
        self.settings.setValue('lang', lang)
        self.notebook.set_lang(lang)
        self.palette.set_lang(lang)
        self.retranslate()

    def update_title(self):
        name = os.path.basename(self.path) if self.path else 'sans titre' if self.lang == 'fr' else \
            'بدون عنوان' if self.lang == 'ar' else 'untitled'
        self.setWindowTitle('Kalam — %s%s' % (name, ' •' if self.modified else ''))

    # ------------------------------------------------------------ updates
    def redraw(self):
        self.canvas.update()
        if self.views.currentWidget() is self.view3d:
            self.view3d.redraw()

    def on_changed(self):
        self.modified = True
        self.update_title()
        self.redraw()

    def on_drag(self, cell, x, y):
        self.session.move_point(cell, x, y)
        self.notebook.changed(light=True)

    # ------------------------------------------------------------ files
    def ask_save(self):
        if not self.modified:
            return True
        r = QMessageBox.question(self, 'Kalam', tr('unsaved', self.lang),
                                 QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if r == QMessageBox.Save:
            return self.save()
        return r == QMessageBox.Discard

    def set_session(self, session, view=None):
        self.session = session
        for w in (self.canvas, self.view3d, self.notebook):
            w.session = session
        self.palette.registry = session.registry
        self.canvas.set_view(view or {})
        self.notebook.rebuild()
        self.redraw()

    def new(self):
        if self.ask_save():
            self.path, self.modified = None, False
            self.set_session(Session(self.session.registry))
            self.update_title()

    def open(self, path=None):
        if not path:
            if not self.ask_save():
                return
            path, _ = QFileDialog.getOpenFileName(self, tr('open', self.lang), '', 'Kalam (*.klm)')
        if not path:
            return
        try:
            session, view, _ = load_klm(path, self.session.registry)
        except Exception as e:
            return QMessageBox.warning(self, tr('error', self.lang), str(e))
        self.path, self.modified = path, False
        self.set_session(session, view)
        self.palette.rebuild()
        self.update_title()

    def save(self, as_=False):
        path = self.path
        if as_ or not path:
            path, _ = QFileDialog.getSaveFileName(self, tr('save_as', self.lang), 'notebook.klm', 'Kalam (*.klm)')
            if not path:
                return False
            if not path.endswith('.klm'):
                path += '.klm'
        save_klm(self.session, path, self.canvas.view(), self.lang)
        self.path, self.modified = path, False
        self.update_title()
        self.statusBar().showMessage(tr('saved', self.lang) % path, 4000)
        return True

    def _export(self, text, filt, default):
        base = os.path.splitext(self.path)[0] if self.path else 'kalam'
        path, _ = QFileDialog.getSaveFileName(self, 'Kalam', base + default, filt)
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            self.statusBar().showMessage(tr('saved', self.lang) % path, 4000)

    def export_py(self):
        self._export(to_python(self.session), 'Python (*.py)', '.py')

    def export_tex(self):
        self._export(to_latex(self.session, self.lang), 'LaTeX (*.tex)', '.tex')

    def export_fig(self):
        self._export(figure_tkz(self.session), 'LaTeX (*.tex)', '_figures.tex')

    def edit_commands(self):
        def saved():
            self.palette.rebuild()
            self.session.evaluate_all()
            self.notebook.refresh_outputs_now()
            self.redraw()
        CommandsEditor(self.session, self.lang, saved, self).exec()

    def closeEvent(self, e):
        if self.ask_save():
            e.accept()
        else:
            e.ignore()


def main(argv=None):
    argv = argv if argv is not None else sys.argv
    app = QApplication(argv)
    app.setApplicationName('Kalam')
    app.setStyle('Fusion')
    app.setStyleSheet(STYLE)
    w = MainWindow(argv[1] if len(argv) > 1 else None)
    w.show()
    return app.exec()
