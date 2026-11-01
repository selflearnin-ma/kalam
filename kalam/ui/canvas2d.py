"""2D graphics view: draws every visible 2D object of the notebook."""
import math

import contourpy
import numpy as np
import sympy as sp
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen, QPolygonF
from PySide6.QtWidgets import QHBoxLayout, QToolButton, QWidget

from .. import runtime
from ..engine import dimension
from .notebook import cell_color

X, Y = runtime.x, runtime.y
BG, MINOR, MAJOR, AXIS, TICK = '#ffffff', '#f1f3f6', '#e2e6ec', '#3b4250', '#7a8190'


def _f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _numeric(expr, vars_):
    """Vectorised numeric function, or None when expr has other free symbols."""
    expr = sp.sympify(expr)
    if not expr.free_symbols <= set(vars_):
        return None
    f = sp.lambdify(vars_, expr, 'numpy')
    return lambda *a: np.broadcast_to(np.asarray(f(*a), dtype=complex), np.broadcast(*a).shape)


def _real(v):
    v = np.asarray(v, dtype=complex)
    out = v.real.copy()
    out[np.abs(v.imag) > 1e-9] = np.nan
    return out


class Canvas2D(QWidget):
    point_dragged = Signal(object, float, float)   # cell, x, y
    drag_finished = Signal()

    def __init__(self, session):
        super().__init__()
        self.session = session
        self.setMouseTracking(True)
        self.setMinimumSize(300, 300)
        self.setLayoutDirection(Qt.LeftToRight)        # axes read left to right in every language
        self.cx, self.cy, self.scale = 0.0, 0.0, 50.0
        self._drag = None          # ('pan', last pos) | ('point', cell)
        self._mouse = None
        self._cache = {}           # (cell.id, version) -> numeric functions
        bar = QHBoxLayout(self)
        bar.setContentsMargins(8, 8, 8, 8)
        bar.addStretch()
        self.buttons = []
        for txt, fn in (('+', lambda: self.zoom(1.25)), ('−', lambda: self.zoom(0.8)), ('⌂', self.home)):
            b = QToolButton()
            b.setText(txt)
            b.setObjectName('canvasbtn')
            b.clicked.connect(fn)
            bar.addWidget(b, 0, Qt.AlignTop)
            self.buttons.append(b)

    # ------------------------------------------------------------ view
    def view(self):
        w, h = self.width(), self.height()
        return dict(cx=self.cx, cy=self.cy, scale=self.scale,
                    xmin=self.cx - w / 2 / self.scale, xmax=self.cx + w / 2 / self.scale,
                    ymin=self.cy - h / 2 / self.scale, ymax=self.cy + h / 2 / self.scale)

    def set_view(self, v):
        self.cx, self.cy, self.scale = v.get('cx', 0.0), v.get('cy', 0.0), v.get('scale', 50.0)
        self.update()

    def home(self):
        self.set_view({})

    def zoom(self, k, at=None):
        if at is not None:
            wx, wy = self.world(at)
        self.scale = min(max(self.scale * k, 2), 5000)
        if at is not None:          # keep the point under the cursor fixed
            nx, ny = self.world(at)
            self.cx += wx - nx
            self.cy += wy - ny
        self.update()

    def sx(self, x):
        return self.width() / 2 + (x - self.cx) * self.scale

    def sy(self, y):
        return self.height() / 2 - (y - self.cy) * self.scale

    def S(self, x, y):
        return QPointF(self.sx(x), self.sy(y))

    def world(self, p):
        return (self.cx + (p.x() - self.width() / 2) / self.scale,
                self.cy - (p.y() - self.height() / 2) / self.scale)

    # ------------------------------------------------------------ painting
    def objects(self):
        for c in self.session.cells:
            if c.kind == 'math' and c.visible and c.value is not None and dimension(c.value) == 2:
                yield c

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor(BG))
        self.draw_grid(p)
        points = []
        for c in self.objects():
            col = QColor(cell_color(self.session, c))
            try:
                self.draw(p, c, c.value, col, c.name, points)
            except Exception as e:       # one bad object must not blank the view
                print('Kalam draw:', c.text, e)
        for pt, col, label, free in points:     # points on top
            r = 5.5 if free else 4.5
            p.setPen(QPen(QColor('white'), 2))
            p.setBrush(col)
            p.drawEllipse(pt, r, r)
            if label:
                p.setPen(col.darker(130))
                p.setFont(QFont('sans-serif', 11, QFont.DemiBold))
                p.drawText(pt + QPointF(8, -8), label)
        if self._mouse:
            x, y = self.world(self._mouse)
            p.setPen(QColor(TICK))
            p.setFont(QFont('monospace', 9))
            p.drawText(10, self.height() - 10, '(%.2f, %.2f)' % (x, y))
        p.end()

    def draw_grid(self, p):
        v = self.view()
        raw = 90 / self.scale
        e = 10 ** math.floor(math.log10(raw))
        step = next(m * e for m in (1, 2, 5, 10) if m * e >= raw)
        minor = step / 5
        for s, col in ((minor, MINOR), (step, MAJOR)):
            p.setPen(QPen(QColor(col), 1))
            for i in range(math.ceil(v['xmin'] / s), math.floor(v['xmax'] / s) + 1):
                X0 = self.sx(i * s)
                p.drawLine(QPointF(X0, 0), QPointF(X0, self.height()))
            for i in range(math.ceil(v['ymin'] / s), math.floor(v['ymax'] / s) + 1):
                Y0 = self.sy(i * s)
                p.drawLine(QPointF(0, Y0), QPointF(self.width(), Y0))
        p.setPen(QPen(QColor(AXIS), 1.4))
        ox = min(max(self.sx(0), 0), self.width())
        oy = min(max(self.sy(0), 0), self.height())
        p.drawLine(QPointF(0, oy), QPointF(self.width(), oy))
        p.drawLine(QPointF(ox, 0), QPointF(ox, self.height()))
        p.setFont(QFont('sans-serif', 9))
        p.setPen(QColor(TICK))
        lab = lambda val: '\u200e%g' % round(val, 10)   # LRM: '-8' not '8-' in Arabic mode
        for i in range(math.ceil(v['xmin'] / step), math.floor(v['xmax'] / step) + 1):
            if i:
                p.drawText(QPointF(self.sx(i * step) - 8, min(oy + 15, self.height() - 4)), lab(i * step))
        for i in range(math.ceil(v['ymin'] / step), math.floor(v['ymax'] / step) + 1):
            if i:
                p.drawText(QPointF(max(ox - 30, 2), self.sy(i * step) + 4), lab(i * step))

    def draw(self, p, c, v, col, name, points):
        pen = QPen(col, 2.2)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)
        if isinstance(v, (list, tuple)):
            for i in v:
                self.draw(p, c, i, col, None, points)
        elif isinstance(v, sp.Point2D):
            x, y = _f(v.x), _f(v.y)
            if x is not None and y is not None:
                points.append((self.S(x, y), col, name, c.is_free_point))
        elif isinstance(v, sp.Segment2D):
            p.drawLine(self.S(*map(_f, v.p1.args)), self.S(*map(_f, v.p2.args)))
        elif isinstance(v, (sp.Line2D, sp.Ray2D)):
            self.draw_line(p, v)
        elif isinstance(v, sp.Circle):
            r = _f(v.radius) * self.scale
            p.drawEllipse(self.S(_f(v.center.x), _f(v.center.y)), r, r)
        elif isinstance(v, sp.Polygon):
            poly = QPolygonF([self.S(_f(a.x), _f(a.y)) for a in v.vertices])
            fill = QColor(col)
            fill.setAlpha(40)
            p.setBrush(fill)
            p.drawPolygon(poly)
        elif isinstance(v, sp.Lambda):
            self.draw_explicit(p, c, v.expr, v.variables[0], None, None, name)
        elif isinstance(v, runtime.Graph):
            self.draw_explicit(p, c, v.expr, v.var, _f(v.a), _f(v.b), name)
        elif isinstance(v, runtime.Curve):
            self.draw_param(p, c, v)
        elif isinstance(v, runtime.Vec):
            o = v.origin or sp.Point(0, 0)
            self.draw_arrow(p, col, _f(o.x), _f(o.y), _f(o.x + v.comps[0]), _f(o.y + v.comps[1]))
        elif isinstance(v, sp.Equality) and v.lhs == Y and not v.rhs.has(Y):
            self.draw_explicit(p, c, v.rhs, X, None, None, name)
        elif isinstance(v, sp.Rel):
            self.draw_implicit(p, c, v, col)

    def draw_line(self, p, l):
        """Clip a line/ray to the view (long segment through the visible box)."""
        v = self.view()
        x1, y1 = _f(l.p1.x), _f(l.p1.y)
        dx, dy = _f(l.p2.x) - x1, _f(l.p2.y) - y1
        n = math.hypot(dx, dy)
        dx, dy = dx / n, dy / n
        big = (v['xmax'] - v['xmin']) + (v['ymax'] - v['ymin']) + abs(x1 - self.cx) + abs(y1 - self.cy)
        t0 = 0 if isinstance(l, sp.Ray2D) else -big
        p.drawLine(self.S(x1 + t0 * dx, y1 + t0 * dy), self.S(x1 + big * dx, y1 + big * dy))

    def _fn(self, c, key, expr, vars_):
        k = (c.id, c.version, key)
        if k not in self._cache:
            self._cache[k] = _numeric(expr, vars_)
        return self._cache[k]

    def draw_path(self, p, xs, ys):
        """Polyline that breaks on NaN and on vertical jumps (asymptotes)."""
        path = QPainterPath()
        pen_down = False
        h = self.height()
        prev = None
        for x, y in zip(xs, ys):
            if not (np.isfinite(x) and np.isfinite(y)):
                pen_down = False
                continue
            X0, Y0 = self.sx(x), self.sy(y)
            if pen_down and prev is not None and abs(Y0 - prev) > 3 * h:
                pen_down = False
            Y0 = min(max(Y0, -10 * h), 11 * h)
            if pen_down:
                path.lineTo(X0, Y0)
            else:
                path.moveTo(X0, Y0)
                pen_down = True
            prev = Y0
        p.drawPath(path)

    def draw_explicit(self, p, c, expr, var, a, b, name):
        f = self._fn(c, 'explicit', expr, (var,))
        if f is None:
            return
        v = self.view()
        lo = v['xmin'] if a is None else max(a, v['xmin'])
        hi = v['xmax'] if b is None else min(b, v['xmax'])
        xs = np.linspace(lo, hi, max(int((hi - lo) * self.scale), 2) + 1)
        with np.errstate(all='ignore'):
            ys = _real(f(xs))
        self.draw_path(p, xs, ys)
        if name:
            ok = np.where(np.isfinite(ys) & (ys > v['ymin']) & (ys < v['ymax']))[0]
            if len(ok):
                i = ok[int(len(ok) * 0.85)]
                p.setFont(QFont('sans-serif', 11, QFont.DemiBold))
                p.drawText(self.S(xs[i], ys[i]) + QPointF(6, -8), name)

    def draw_param(self, p, c, v):
        f = [self._fn(c, 'param%d' % i, e, (v.var,)) for i, e in enumerate(v.comps)]
        if None in f:
            return
        ts = np.linspace(_f(v.a), _f(v.b), 1200)
        with np.errstate(all='ignore'):
            self.draw_path(p, _real(f[0](ts)), _real(f[1](ts)))

    def draw_arrow(self, p, col, x1, y1, x2, y2):
        a, b = self.S(x1, y1), self.S(x2, y2)
        p.drawLine(a, b)
        ang = math.atan2(b.y() - a.y(), b.x() - a.x())
        head = QPolygonF([b, b - QPointF(12 * math.cos(ang - 0.4), 12 * math.sin(ang - 0.4)),
                          b - QPointF(12 * math.cos(ang + 0.4), 12 * math.sin(ang + 0.4))])
        p.setBrush(col)
        p.drawPolygon(head)

    def draw_implicit(self, p, c, rel, col):
        F = self._fn(c, 'implicit', rel.lhs - rel.rhs, (X, Y))
        if F is None:
            return
        v = self.view()
        n = 260
        xs = np.linspace(v['xmin'], v['xmax'], n)
        ys = np.linspace(v['ymin'], v['ymax'], n)
        gx, gy = np.meshgrid(xs, ys)
        with np.errstate(all='ignore'):
            Zv = _real(F(gx, gy))
        if not isinstance(rel, sp.Equality):
            ok = {sp.StrictLessThan: Zv < 0, sp.LessThan: Zv <= 0,
                  sp.StrictGreaterThan: Zv > 0, sp.GreaterThan: Zv >= 0}.get(type(rel))
            if ok is not None:
                img = np.zeros((n, n, 4), dtype=np.uint8)
                img[ok] = (col.red(), col.green(), col.blue(), 55)
                img = np.ascontiguousarray(img[::-1])
                qi = QImage(img.data, n, n, 4 * n, QImage.Format_RGBA8888)
                p.drawImage(QRectF(0, 0, self.width(), self.height()), qi)
        pen = p.pen()
        if isinstance(rel, (sp.StrictLessThan, sp.StrictGreaterThan)):
            pen.setStyle(Qt.DashLine)
        p.setPen(pen)
        Zm = np.where(np.isfinite(Zv), Zv, np.nan)
        try:
            lines = contourpy.contour_generator(xs, ys, Zm).lines(0.0)
        except Exception:
            return
        for ln in lines:
            p.drawPolyline(QPolygonF([self.S(a, b) for a, b in ln]))

    # ------------------------------------------------------------ mouse
    def hit_point(self, pos):
        for c in reversed(list(self.objects())):
            if c.is_free_point and isinstance(c.value, sp.Point2D):
                q = self.S(_f(c.value.x), _f(c.value.y))
                if (q - pos).manhattanLength() < 14:
                    return c
        return None

    def mousePressEvent(self, e):
        c = self.hit_point(e.position())
        self._drag = ('point', c) if c else ('pan', e.position())
        self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        pos = e.position()
        self._mouse = pos
        if self._drag and self._drag[0] == 'pan':
            d = pos - self._drag[1]
            self.cx -= d.x() / self.scale
            self.cy += d.y() / self.scale
            self._drag = ('pan', pos)
        elif self._drag:
            x, y = self.world(pos)
            snap = lambda u: round(u) if abs(u - round(u)) < 12 / self.scale else round(u, 1)
            self.point_dragged.emit(self._drag[1], snap(x), snap(y))
        else:
            self.setCursor(Qt.OpenHandCursor if self.hit_point(pos) else Qt.ArrowCursor)
        self.update()

    def mouseReleaseEvent(self, e):
        if self._drag and self._drag[0] == 'point':
            self.drag_finished.emit()
        self._drag = None
        self.setCursor(Qt.ArrowCursor)

    def wheelEvent(self, e):
        self.zoom(1.15 if e.angleDelta().y() > 0 else 1 / 1.15, e.position())

    def leaveEvent(self, _):
        self._mouse = None
        self.update()
