"""3D graphics view (Matplotlib mplot3d embedded in Qt)."""
import numpy as np
import sympy as sp
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from sympy.geometry.line import LinearEntity3D

from .. import runtime
from ..engine import dimension
from .canvas2d import _numeric, _real
from .notebook import cell_color

X, Y, Z = runtime.x, runtime.y, runtime.z


class View3D(FigureCanvasQTAgg):
    def __init__(self, session):
        self.fig = Figure(facecolor='white')
        super().__init__(self.fig)
        self.session = session
        self.R = 5.0
        self.ax = self.fig.add_subplot(projection='3d')
        self.fig.subplots_adjust(0, 0, 1, 1)
        self.mpl_connect('scroll_event', self.on_scroll)
        self.redraw()

    def on_scroll(self, e):
        self.R = min(max(self.R * (0.87 if e.button == 'up' else 1.15), 0.5), 200)
        self.redraw()

    def redraw(self):
        ax, R = self.ax, self.R
        elev, azim = ax.elev, ax.azim
        ax.clear()
        ax.view_init(elev, azim)
        for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
            axis.set_pane_color((0.97, 0.975, 0.98, 1))
            axis._axinfo['grid'].update(color='#e2e6ec', linewidth=0.6)
        ax.set_xlim(-R, R)
        ax.set_ylim(-R, R)
        ax.set_zlim(-R, R)
        ax.set_box_aspect((1, 1, 1))
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.set_zlabel('z')
        ax.tick_params(labelsize=7, colors='#7a8190')
        for k in range(3):     # axes through the origin
            seg = np.zeros((2, 3))
            seg[:, k] = (-R, R)
            ax.plot(*seg.T, color='#3b4250', lw=1)
        for c in self.session.cells:
            if c.kind == 'math' and c.visible and c.value is not None and dimension(c.value) == 3:
                try:
                    self.draw_obj(c.value, cell_color(self.session, c), c.name)
                except Exception as e:
                    print('Kalam 3D:', c.text, e)
        self.draw_idle()

    def grid(self, n=50):
        u = np.linspace(-self.R, self.R, n)
        return np.meshgrid(u, u)

    def clip(self, *arrs):
        R = self.R * 1.001
        out = []
        for a in arrs:
            a = np.array(a, dtype=float)
            out.append(a)
        mask = np.zeros_like(out[0], dtype=bool)
        for a in out:
            mask |= ~np.isfinite(a) | (np.abs(a) > R)
        for a in out:
            a[mask] = np.nan
        return out

    def surface(self, X_, Y_, Z_, color):
        X_, Y_, Z_ = self.clip(X_, Y_, Z_)
        self.ax.plot_surface(X_, Y_, Z_, color=color, alpha=0.75, linewidth=0, antialiased=True,
                             shade=True, rstride=1, cstride=1)

    def draw_obj(self, v, color, name):
        ax, R = self.ax, self.R
        f = lambda a: float(a)
        if isinstance(v, (list, tuple)):
            for i in v:
                self.draw_obj(i, color, None)
        elif isinstance(v, sp.Point3D):
            p = [f(a) for a in v.args]
            ax.scatter(*p, color=color, s=36, depthshade=False)
            if name:
                ax.text(*p, '  ' + name, color=color, fontsize=10, fontweight='bold')
        elif isinstance(v, sp.Segment3D):
            ax.plot(*np.array([[f(a) for a in v.p1.args], [f(a) for a in v.p2.args]]).T, color=color, lw=2)
        elif isinstance(v, LinearEntity3D):
            p, d = np.array([f(a) for a in v.p1.args]), np.array([f(a) for a in v.direction_ratio])
            lo = 0 if isinstance(v, sp.Ray3D) else -4 * R
            ts = np.linspace(lo, 4 * R, 400)
            ax.plot(*self.clip(*(p[:, None] + d[:, None] * ts)), color=color, lw=2)
        elif isinstance(v, sp.Plane):
            a, b, c = [f(k) for k in v.normal_vector]
            d = -(a * f(v.p1.x) + b * f(v.p1.y) + c * f(v.p1.z))
            G1, G2 = self.grid(20)
            k = int(np.argmax(np.abs([a, b, c])))
            if k == 2:
                self.surface(G1, G2, -(a * G1 + b * G2 + d) / c, color)
            elif k == 1:
                self.surface(G1, -(a * G1 + c * G2 + d) / b, G2, color)
            else:
                self.surface(-(b * G1 + c * G2 + d) / a, G1, G2, color)
        elif isinstance(v, runtime.SphereObj):
            u, w = np.meshgrid(np.linspace(0, 2 * np.pi, 40), np.linspace(-np.pi / 2, np.pi / 2, 20))
            cx, cy, cz = [f(a) for a in v.center.args]
            r = f(v.r)
            self.surface(cx + r * np.cos(u) * np.cos(w), cy + r * np.sin(u) * np.cos(w), cz + r * np.sin(w), color)
        elif isinstance(v, runtime.Surface):
            if len(v.comps) == 1:
                self.explicit(v.comps[0], color)
            else:
                (u0, u1), (w0, w1) = v.ur, v.vr
                U, W = np.meshgrid(np.linspace(f(u0), f(u1), 50), np.linspace(f(w0), f(w1), 50))
                fs = [_numeric(e, (v.u, v.v)) for e in v.comps]
                with np.errstate(all='ignore'):
                    self.surface(*[_real(g(U, W)) for g in fs], color)
        elif isinstance(v, sp.Lambda):
            self.explicit(v.expr.subs(dict(zip(v.variables, (X, Y)))), color)
        elif isinstance(v, runtime.Curve):
            ts = np.linspace(f(v.a), f(v.b), 800)
            fs = [_numeric(e, (v.var,)) for e in v.comps]
            with np.errstate(all='ignore'):
                ax.plot(*self.clip(*[_real(g(ts)) for g in fs]), color=color, lw=2)
        elif isinstance(v, runtime.Vec):
            o = [f(a) for a in v.origin.args] if v.origin is not None else [0, 0, 0]
            ax.quiver(*o, *[f(a) for a in v.comps], color=color, arrow_length_ratio=0.12, lw=2)
        elif isinstance(v, sp.Equality):
            # surfaces given by an equation: solve for z (each branch is a surface)
            for branch in sp.solve(v, Z):
                self.explicit(branch, color)

    def explicit(self, expr, color):
        g = _numeric(expr, (X, Y))
        if g is None:
            return
        G1, G2 = self.grid()
        with np.errstate(all='ignore'):
            self.surface(G1, G2, _real(g(G1, G2)), color)
