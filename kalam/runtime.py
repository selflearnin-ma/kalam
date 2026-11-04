"""Kalam runtime: every built-in command, written with SymPy only.

This file is self-contained on purpose: the Python exporter copies it verbatim
into exported scripts, so an exported notebook runs with nothing but SymPy.
Inside, always use `sp.X` (never bare names) because commands such as
`Integral` or `Matrix` shadow SymPy's own names in the exported namespace.
"""
import sympy as sp
from sympy.geometry.entity import GeometryEntity

x, y, z, t = sp.symbols('x y z t')


# ---------------------------------------------------------------- objects
class Graph:
    """Graph of y = expr(var) on [a, b] (a, b None = whole view)."""
    def __init__(self, expr, var=x, a=None, b=None):
        self.expr, self.var, self.a, self.b = sp.sympify(expr), var, a, b

    def _latex(self, printer):
        dom = '' if self.a is None else r',\ %s \in [%s, %s]' % (
            printer._print(self.var), printer._print(self.a), printer._print(self.b))
        return 'y = ' + printer._print(self.expr) + dom

    def __repr__(self):
        return 'Graph(%s)' % self.expr


class Curve:
    """Parametric curve (2D or 3D) of parameter `var` on [a, b]."""
    def __init__(self, comps, var=t, a=0, b=1):
        self.comps, self.var, self.a, self.b = [sp.sympify(c) for c in comps], var, a, b
        self.dim = len(self.comps)

    def _latex(self, printer):
        return r'\left(%s\right),\ %s \in [%s, %s]' % (
            ', '.join(printer._print(c) for c in self.comps), printer._print(self.var),
            printer._print(self.a), printer._print(self.b))

    def __repr__(self):
        return 'Curve(%s)' % (self.comps,)


class Surface:
    """Surface z = f(x, y), or parametric surface (X, Y, Z)(u, v)."""
    def __init__(self, comps, u=x, ur=None, v=y, vr=None):
        self.comps = [sp.sympify(c) for c in comps]
        self.u, self.v, self.ur, self.vr = u, v, ur, vr
        self.dim = 3

    def _latex(self, printer):
        if len(self.comps) == 1:
            return 'z = ' + printer._print(self.comps[0])
        return r'\left(%s\right)' % ', '.join(printer._print(c) for c in self.comps)

    def __repr__(self):
        return 'Surface(%s)' % (self.comps,)


class SphereObj:
    def __init__(self, center, r):
        self.center, self.r, self.dim = center, sp.sympify(r), 3

    def equation(self):
        a, b, c = self.center.args
        return sp.Eq((x - a)**2 + (y - b)**2 + (z - c)**2, self.r**2, evaluate=False)

    def _latex(self, printer):
        return printer._print(self.equation())

    def __repr__(self):
        return 'SphereObj(%s, %s)' % (self.center, self.r)


class Vec:
    """Vector with optional origin point (for drawing)."""
    def __init__(self, comps, origin=None):
        self.comps = [sp.sympify(c) for c in comps]
        self.origin, self.dim = origin, len(self.comps)

    def norm(self):
        return sp.sqrt(sum(c**2 for c in self.comps))

    def _latex(self, printer):
        return r'\left(%s\right)' % ', '.join(printer._print(c) for c in self.comps)

    def __repr__(self):
        return 'Vec(%s)' % (self.comps,)


# ---------------------------------------------------------------- helpers
def _pt(p):
    if isinstance(p, (tuple, list)):
        return Point(*p)
    return p


def _var(expr, default=x):
    """The variable of an expression: x if present, else its first free symbol."""
    fs = sorted(getattr(expr, 'free_symbols', set()), key=str)
    return default if default in fs or not fs else fs[0]


def _body(f):
    """(expression, variable) from a Lambda or an expression."""
    if isinstance(f, sp.Lambda):
        return f.expr, f.variables[0]
    f = sp.sympify(f)
    return f, _var(f)


def _as_eq(obj):
    """Convert curves to equations in x, y (for Intersect)."""
    if isinstance(obj, sp.Lambda):
        return sp.Eq(y, obj.expr.subs(obj.variables[0], x))
    if isinstance(obj, (sp.Line, sp.Circle)):
        return sp.Eq(obj.equation(x, y), 0)
    if isinstance(obj, sp.Equality):
        return obj
    return sp.Eq(y, sp.sympify(obj))


def _one(lst):
    lst = list(lst)
    return lst[0] if len(lst) == 1 else lst


# ---------------------------------------------------------------- geometry
def Point(*a):
    if len(a) == 1:
        a = tuple(a[0])
    return sp.Point3D(*a) if len(a) == 3 else sp.Point2D(*a)


def Segment(A, B):
    A, B = _pt(A), _pt(B)
    return sp.Segment3D(A, B) if A.ambient_dimension == 3 else sp.Segment(A, B)


def Line(A, B):
    A, B = _pt(A), _pt(B)
    if isinstance(B, Vec):
        B = A + Point(*B.comps)
    return sp.Line3D(A, B) if A.ambient_dimension == 3 else sp.Line(A, B)


def Ray(A, B):
    A, B = _pt(A), _pt(B)
    return sp.Ray3D(A, B) if A.ambient_dimension == 3 else sp.Ray(A, B)


def Circle(C, *r):
    """Circle(center, radius) | Circle(center, point) | Circle(A, B, C)."""
    C = _pt(C)
    if len(r) == 2:
        return sp.Circle(C, _pt(r[0]), _pt(r[1]))
    r = r[0]
    if isinstance(r, (tuple, sp.Point)):
        r = C.distance(_pt(r))
    return sp.Circle(C, r)


def Polygon(*pts):
    return sp.Polygon(*[_pt(p) for p in pts])


def Midpoint(A, B=None):
    if B is None:
        return A.midpoint
    return _pt(A).midpoint(_pt(B))


def Intersect(a, b):
    a, b = _pt(a), _pt(b)
    if isinstance(a, GeometryEntity) and isinstance(b, GeometryEntity):
        return _one(a.intersection(b))
    sols = sp.solve([_as_eq(a), _as_eq(b)], [x, y], dict=True)
    pts = [sp.Point2D(s[x], s[y]) for s in sols if x in s and y in s
           and s[x].is_real is not False and s[y].is_real is not False]
    return _one(pts)


def Perpendicular(P, l):
    return l.perpendicular_line(_pt(P))


def Parallel(P, l):
    return l.parallel_line(_pt(P))


def PerpendicularBisector(A, B=None):
    seg = A if B is None else sp.Segment(_pt(A), _pt(B))
    return seg.perpendicular_bisector()


def AngleBisector(A, B, C):
    """Bisector of angle ABC (vertex B)."""
    A, B, C = _pt(A), _pt(B), _pt(C)
    u = (A - B) / A.distance(B)
    v = (C - B) / C.distance(B)
    return sp.Line(B, B + u + v)


def Distance(a, b):
    a, b = _pt(a), _pt(b)
    if isinstance(a, sp.Point):
        return sp.simplify(b.distance(a))
    return sp.simplify(a.distance(b))


def Length(o):
    if isinstance(o, Vec):
        return sp.simplify(o.norm())
    if isinstance(o, sp.Circle):
        return o.circumference
    if isinstance(o, sp.Polygon):
        return sp.simplify(o.perimeter)
    return sp.simplify(o.length)


def Area(o):
    return sp.simplify(abs(o.area))


def Tangent(f, a):
    """Tangent(f, a): tangent line to the graph of f at x = a.
    Tangent(P, circle): tangent lines from P to the circle."""
    if isinstance(a, sp.Circle):
        return _one(a.tangent_lines(_pt(f)))
    e, v = _body(f)
    d = sp.diff(e, v)
    return sp.Eq(y, sp.expand(d.subs(v, a) * (x - a) + e.subs(v, a)))


def Vector(*a):
    """Vector(A, B) | Vector(a, b) | Vector(a, b, c)."""
    if len(a) == 2 and all(isinstance(p, (sp.Point, tuple)) for p in a):
        A, B = _pt(a[0]), _pt(a[1])
        return Vec(list((B - A).args), origin=A)
    if len(a) == 1 and isinstance(a[0], sp.Point):
        return Vec(list(a[0].args))
    return Vec(list(a))


def Reflect(o, about):
    """Symmetric of o with respect to a line or a point."""
    about = _pt(about)
    if isinstance(about, sp.Point):
        return o.rotate(sp.pi, about)
    return o.reflect(about)


def Rotate(o, angle, center=(0, 0)):
    return o.rotate(angle, _pt(center))


def Translate(o, v):
    if isinstance(v, sp.Point):
        v = Vector(v)
    return o.translate(*v.comps)


def Dilate(o, k, center=(0, 0)):
    """Homothety of ratio k and given center."""
    return o.scale(k, k, _pt(center))


# ---------------------------------------------------------------- algebra
def Simplify(e):
    return sp.simplify(e)


def Expand(e):
    return sp.expand(e)


def Factor(e):
    e = sp.sympify(e)
    if e.is_Integer:
        return sp.factorint(e, visual=True)
    return sp.factor(e)


def Solve(eq, var=None, domain='R'):
    """Real solutions (equation, inequality or system)."""
    if isinstance(eq, (list, tuple)):
        vs = var or sorted(set().union(*[sp.sympify(e).free_symbols for e in eq]), key=str)
        return sp.solve(list(eq), list(vs), dict=True)
    eq = sp.sympify(eq)
    var = var or _var(eq)
    dom = sp.S.Complexes if str(domain).upper().startswith('C') else sp.S.Reals
    return sp.solveset(eq, var, domain=dom)


def CSolve(eq, var=None):
    return Solve(eq, var, 'C')


def NSolve(eq, var=None, guess=0):
    eq = sp.sympify(eq)
    var = var or _var(eq)
    f = eq.lhs - eq.rhs if isinstance(eq, sp.Equality) else eq
    try:
        sols = sp.Poly(f, var).nroots()
        return [s for s in sols if s.is_real] or sols
    except sp.PolynomialError:
        return sp.nsolve(f, var, guess)


def Substitute(e, var, val):
    return sp.sympify(e).subs(var, val)


def Numeric(e, digits=10):
    if isinstance(e, (list, tuple)):
        return [Numeric(i, digits) for i in e]
    return sp.N(e, digits)


def PartialFractions(e, var=None):
    return sp.apart(e, var)


def GCD(a, b):
    return sp.gcd(a, b)


def LCM(a, b):
    return sp.lcm(a, b)


def Divisors(n):
    return sp.divisors(n)


def IsPrime(n):
    return sp.isprime(n)


# ---------------------------------------------------------------- calculus
def Derivative(f, var=None, n=1):
    """Derivative(f) | Derivative(f, n) | Derivative(expr, x) | Derivative(expr, x, n)."""
    if isinstance(var, (int, sp.Integer)):
        var, n = None, int(var)
    if isinstance(f, sp.Lambda):
        v = f.variables[0]
        return sp.Lambda(v, sp.simplify(sp.diff(f.expr, v, n)))
    f = sp.sympify(f)
    return sp.simplify(sp.diff(f, var or _var(f), n))


def Integral(f, *a):
    """Integral(f) | Integral(f, a, b) | Integral(expr, x) | Integral(expr, x, a, b)."""
    e, v = _body(f)
    if a and isinstance(a[0], sp.Symbol):
        v, a = a[0], a[1:]
    if len(a) == 2:
        return sp.simplify(sp.integrate(e, (v, a[0], a[1])))
    return sp.integrate(e, v)


def Limit(f, *a):
    """Limit(f, a) | Limit(expr, x, a) | Limit(expr, x, a, '+')."""
    e, v = _body(f)
    if len(a) >= 2 and isinstance(a[0], sp.Symbol):
        v, a = a[0], a[1:]
    side = '+-' if len(a) < 2 else str(a[1])
    return sp.limit(e, v, a[0], dir=side)


def Series(f, *a):
    """Series(f, a, n) | Series(expr, x, a, n): Taylor expansion."""
    e, v = _body(f)
    if a and isinstance(a[0], sp.Symbol):
        v, a = a[0], a[1:]
    a0 = a[0] if a else 0
    n = int(a[1]) if len(a) > 1 else 6
    return sp.series(e, v, a0, n)


def Sum(e, k, a, b):
    return sp.summation(e, (k, a, b))


def Sequence(e, k, a, b):
    return [sp.sympify(e).subs(k, i) for i in range(int(a), int(b) + 1)]


# ---------------------------------------------------------------- matrices
def Matrix(*rows):
    if len(rows) == 1:
        rows = rows[0]
    return sp.Matrix(rows)


def Det(M):
    return sp.Matrix(M).det()


def Inverse(M):
    return sp.Matrix(M).inv()


def Transpose(M):
    return sp.Matrix(M).T


def Eigenvalues(M):
    return sp.Matrix(M).eigenvals()


# ---------------------------------------------------------------- plotting
class Figure:
    """What a drawing command shows: the objects to draw (all 2D or all 3D)."""
    def __init__(self, items):
        self.items = []
        for i in items:
            if isinstance(i, Figure):
                self.items += i.items
            elif isinstance(i, (list, tuple)):     # e.g. the points of Intersect(...)
                self.items += list(i)
            else:
                self.items.append(i)

    def _latex(self, printer):
        return r'\text{[figure]}'

    def __repr__(self):
        return 'Figure(%s)' % self.items


def Graphic():
    """Graphic(): an empty figure; add objects with G.Draw(f, A, ...)."""
    return Figure([])


def Draw(*objs):
    """Draw(f, A, c, ...): a figure with these objects (2D or 3D)."""
    return Figure(objs)


def Plot(f, a=None, b=None):
    """Plot(f) | Plot(f, a, b): figure with the graph of f."""
    e, v = _body(f)
    return Figure([Graph(e, v, a, b)])


def ParametricCurve(*a):
    """ParametricCurve(x(t), y(t), t, a, b) or with z(t) before t."""
    *comps, var, lo, hi = a
    return Curve(comps, var, lo, hi)


def Plot3D(f):
    """Plot3D(f) | Plot3D(expr in x, y): 3D figure of the surface z = f(x, y)."""
    if isinstance(f, sp.Lambda):
        return Figure([Surface([f.expr.subs(dict(zip(f.variables, (x, y))))])])
    return Figure([Surface([f])])


def ParametricSurface(X, Y, Z, u, u0, u1, v, v0, v1):
    return Surface([X, Y, Z], u, (u0, u1), v, (v0, v1))


def Sphere(C, r):
    C = _pt(C)
    if isinstance(r, sp.Point):
        r = C.distance(r)
    return SphereObj(C, r)


def Plane(A, B, C=None):
    """Plane(A, B, C) through 3 points | Plane(A, normal vector)."""
    A = _pt(A)
    if C is None:
        n = B.comps if isinstance(B, Vec) else B
        return sp.Plane(A, normal_vector=tuple(n))
    return sp.Plane(A, _pt(B), _pt(C))


def Slider(lo, hi, step=None, value=None):
    """A number moved by a slider; outside Kalam it is just its value."""
    return sp.nsimplify(lo if value is None else value)



# ---------------------------------------------------------------- sign and variation tables
def _table_points(e, v):
    """Domain of e (finite union of intervals) -> (sorted boundary points, excluded boundary points)."""
    dom = sp.calculus.util.continuous_domain(e, v, sp.S.Reals)
    parts = dom.args if isinstance(dom, sp.Union) else (dom,)
    if not all(isinstance(p, sp.Interval) for p in parts):
        raise ValueError('domain too complicated for a table: %s' % dom)
    pts = sorted({b for p in parts for b in (p.start, p.end)}, key=lambda b: float(b))
    return pts, dom, {b for b in pts if b.is_finite and b not in dom}


def _roots(e, v, dom):
    r = sp.solveset(e, v, sp.S.Reals)
    if r is sp.S.EmptySet:
        return set()
    if not isinstance(r, sp.FiniteSet):
        raise ValueError('cannot find the zeros of %s' % e)
    return {p for p in r if p in dom}


def _test_point(a, b):
    if a == -sp.oo and b == sp.oo:
        return sp.Integer(0)
    if a == -sp.oo:
        return b - 1
    if b == sp.oo:
        return a + 1
    return (a + b) / 2


def _sign(e, v, t):
    s = sp.sign(sp.N(e.subs(v, t), 30))
    return '+' if s > 0 else '-' if s < 0 else '0'


def _numeric(e, v):
    others = e.free_symbols - {v}
    if others:
        raise ValueError('coefficients must be numbers (give a value to %s, or use a Slider)'
                         % ', '.join(sorted(map(str, others))))


def _tex_x(p):
    return {sp.oo: '+\\infty', -sp.oo: '-\\infty'}.get(p, sp.latex(p))


class SignTableObj:
    """Sign table of an expression: one row per factor (when there are several) and the expression."""
    def __init__(self, e, v):
        _numeric(e, v)
        self.var = v
        pts, self.dom, excluded = _table_points(e, v)
        num, den = sp.fraction(sp.factor(sp.together(e)))
        facs = [(f ** k, False) for f, k in sp.factor_list(num)[1] if f.has(v)] + \
               [(f ** k, True) for f, k in sp.factor_list(den)[1] if f.has(v)]
        zeros = set()
        for f, _ in facs:
            zeros |= _roots(f, v, sp.Interval(pts[0], pts[-1]))
        self.xs = sorted(set(pts) | zeros, key=lambda b: float(b))
        rows = [(f, is_den) for f, is_den in facs] if len(facs) > 1 else []
        self.rows = [(sp.latex(f), self._cells(f, is_den, excluded)) for f, is_den in rows]
        self.rows.append((sp.latex(e), self._cells(e, None, excluded)))

    def _cells(self, f, is_den, excluded):
        v, xs, out = self.var, self.xs, []
        for k, p in enumerate(xs):
            if k:
                out.append(_sign(f, v, _test_point(xs[k - 1], p)))
            if not p.is_finite:
                out.append('')
                continue
            if is_den is None:   # the expression itself: || where it is not defined, 0 at its zeros
                out.append('d' if p in excluded or p not in self.dom else 'z' if sp.simplify(f.subs(v, p)) == 0 else '')
            else:
                out.append('z' if sp.simplify(f.subs(v, p)) == 0 else '')     # a factor: 0 at its zeros
        return out

    def _latex(self, printer=None):
        n = len(self.xs)
        head = ' & '.join(_tex_x(p) if k % 2 == 0 else '' for k, p in enumerate(_spread(self.xs)))
        mark = {'+': '+', '-': '-', 'z': '0', 'd': '\\|', '': '', '0': '0'}
        lines = ['%s & %s' % (sp.latex(self.var), head)]
        lines += ['%s & %s' % (lab, ' & '.join(mark[c] for c in cells)) for lab, cells in self.rows]
        return '\\begin{array}{|c|%s|}\\hline %s \\\\ \\hline\\end{array}' % ('c' * (2 * n - 1), ' \\\\ \\hline '.join(lines))

    def tkztab(self):
        rows = ', '.join('$%s$/1' % lab for lab, _ in self.rows)
        code = {'+': '+', '-': '-', 'z': 'z', 'd': 'd', '': '', '0': 'z'}
        out = ['\\begin{tikzpicture}',
               '\\tkzTabInit[espcl=2]{$%s$/1, %s}{%s}' % (sp.latex(self.var), rows, ', '.join('$%s$' % _tex_x(p) for p in self.xs))]
        out += ['\\tkzTabLine{%s}' % ', '.join(_tab_line(cells, code)) for _, cells in self.rows]
        return out + ['\\end{tikzpicture}']

    def __str__(self):
        return '\n'.join('%-12s %s' % (lab, ' '.join(c or '.' for c in cells)) for lab, cells in
                         [(str(self.var), [str(p) if k % 2 == 0 else '' for k, p in enumerate(_spread(self.xs))])] + self.rows)


def _tab_line(cells, code):
    """tkz-tab codes of a row; an interior point with no mark gets a dotted line (t)."""
    return [code[c] or ('t' if 0 < k < len(cells) - 1 and k % 2 == 0 else '') for k, c in enumerate(cells)]


def _spread(xs):
    """x0, gap, x1, gap, ... (the columns of a table)."""
    out = []
    for k, p in enumerate(xs):
        if k:
            out.append(None)
        out.append(p)
    return out


class VariationTableObj:
    """Variation table of f: sign of f' and the arrows of f, with values and limits."""
    def __init__(self, f):
        e, v = _body(f)
        _numeric(e, v)
        self.var, self.name, self.f = v, 'f', f      # the notebook sets name to the function's own name
        pts, dom, excluded = _table_points(e, v)
        d = sp.simplify(sp.diff(e, v))
        crit = _roots(d, v, sp.Interval.open(pts[0], pts[-1]) - sp.FiniteSet(*excluded))
        self.xs = xs = sorted(set(pts) | crit, key=lambda b: float(b))
        self.dsign = [_sign(d, v, _test_point(xs[k], xs[k + 1])) for k in range(len(xs) - 1)]
        self.fp = []      # f'(x) row: point marks and interval signs
        self.vals = []    # per point: (kind, left value, right value); kind 'v' value, 'D' forbidden, 'Ds'/'sD' at ends
        for k, p in enumerate(xs):
            if k:
                self.fp.append(self.dsign[k - 1])
            if p in excluded or not p.is_finite or p not in dom:
                lv = sp.limit(e, v, p, '-') if k > 0 else None
                rv = sp.limit(e, v, p, '+') if k < len(xs) - 1 else None
                if not p.is_finite:
                    self.fp.append('')
                    self.vals.append(('v', lv if k else rv, None))
                else:
                    self.fp.append('d')
                    self.vals.append(('D', lv, rv))
            else:
                dv = d.subs(v, p)
                self.fp.append('d' if not dv.is_finite else 'z' if p in crit and sp.simplify(dv) == 0 else '')
                self.vals.append(('v', sp.simplify(e.subs(v, p)), None))

    def _pos(self, k, side):
        """'+' (top) or '-' (bottom) for the value at point k on its left ('l') or right ('r') side."""
        n = len(self.xs)
        if side == 'l' and k > 0:
            return '+' if self.dsign[k - 1] == '+' else '-'
        if side == 'r' and k < n - 1:
            return '-' if self.dsign[k] == '+' else '+'
        return '+'

    def _point_pos(self, k):
        if k == 0:
            return self._pos(0, 'r')
        return self._pos(k, 'l')

    def _latex(self, printer=None):
        cols = 2 * len(self.xs) - 1
        top, mid, bot = [''] * cols, [''] * cols, [''] * cols
        for k, (kind, a, b) in enumerate(self.vals):
            c = 2 * k
            if kind == 'D':
                mid[c] = '\\|'
                left = _tex_x(a) + '\\,' if a is not None else ''
                right = '\\,' + _tex_x(b) if b is not None else ''
                for row, s in ((top, '+'), (bot, '-')):
                    row[c] = (left if a is not None and self._pos(k, 'l') == s else '') + '\\|' + \
                             (right if b is not None and self._pos(k, 'r') == s else '')
            else:
                (top if self._point_pos(k) == '+' else bot)[c] = _tex_x(a)
        for k, s in enumerate(self.dsign):
            mid[2 * k + 1] = '\\nearrow' if s == '+' else '\\searrow' if s == '-' else '\\rightarrow'
        mark = {'+': '+', '-': '-', 'z': '0', 'd': '\\|', '': ''}
        head = ' & '.join(_tex_x(p) if p is not None else '' for p in _spread(self.xs))
        lines = ['%s & %s' % (sp.latex(self.var), head),
                 "%s'(%s) & %s" % (self.name, sp.latex(self.var), ' & '.join(mark[c] for c in self.fp)),
                 ' & ' + ' & '.join(top) + ' \\\\ %s(%s) & ' % (self.name, sp.latex(self.var)) + ' & '.join(mid) +
                 ' \\\\ & ' + ' & '.join(bot)]
        return '\\begin{array}{|c|%s|}\\hline %s \\\\ \\hline\\end{array}' % ('c' * cols, ' \\\\ \\hline '.join(lines))

    def tkztab(self):
        v, xs = sp.latex(self.var), self.xs
        code = {'+': '+', '-': '-', 'z': 'z', 'd': 'd', '': ''}
        var = []
        for k, (kind, a, b) in enumerate(self.vals):
            if kind == 'D':
                if a is None:
                    var.append('D%s/ / $%s$' % (self._pos(k, 'r'), _tex_x(b)))
                elif b is None:
                    var.append('%sD/ $%s$ /' % (self._pos(k, 'l'), _tex_x(a)))
                else:
                    var.append('%sD%s/ $%s$ / $%s$' % (self._pos(k, 'l'), self._pos(k, 'r'), _tex_x(a), _tex_x(b)))
            else:
                var.append('%s/ $%s$' % (self._point_pos(k), _tex_x(a)))
        return ['\\begin{tikzpicture}',
                "\\tkzTabInit[espcl=2]{$%s$/1, $%s'(%s)$/1, $%s(%s)$/2}{%s}" % (
                    v, self.name, v, self.name, v, ', '.join('$%s$' % _tex_x(p) for p in xs)),
                '\\tkzTabLine{%s}' % ', '.join(_tab_line(self.fp, code)),
                '\\tkzTabVar{%s}' % ', '.join(var),
                '\\end{tikzpicture}']

    def __str__(self):
        return "x: %s\n%s': %s\n%s: %s" % (' '.join(map(str, self.xs)), self.name, ' '.join(c or '.' for c in self.fp),
                                           self.name, ' '.join(str(a) for _, a, _ in self.vals))


def SignTable(f, var=None):
    """SignTable(x^2 - 4): sign table (one row per factor, then the expression)."""
    e, v = _body(f)
    return SignTableObj(e, var or v)


def VariationTable(f):
    """VariationTable(f): sign of f' and variations of f, with values and limits."""
    return VariationTableObj(f)
