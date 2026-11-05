"""SymNote runtime: every built-in command, written with SymPy only.

This file is self-contained on purpose: the Python exporter copies it verbatim
into exported scripts, so an exported notebook runs with nothing but SymPy.
Inside, always use `sp.X` (never bare names) because commands such as
`Integral` or `Matrix` shadow SymPy's own names in the exported namespace.
"""
import copy
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


def _set_item(self, k):
    """S[0], S[1], ...: the elements of a solution set in increasing order (S[0] is the smallest, as in Python lists)."""
    el = list(self.args)
    if all(e.is_real for e in el):
        el.sort(key=lambda e: float(e))
    if not 0 <= int(k) < len(el):
        raise IndexError('this set has %d element(s): use S[0] to S[%d]' % (len(el), len(el) - 1) if el else 'this set is empty')
    return el[int(k)]


sp.FiniteSet.__getitem__ = _set_item     # so a = Solve(f(x) = 0, x)[0] is a number


def Hold(e):
    """Hold(2 + 3*4): the expression as written, not computed (in the notebook; here it is computed)."""
    return e


def Domain(f):
    """Domain(f): the real numbers where f is defined (D_f)."""
    e, v = _body(f)
    return sp.calculus.util.continuous_domain(e, v, sp.S.Reals)


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
    """What a drawing command shows: the objects to draw (all 2D or all 3D).
    dim: 2 or 3 for Graphic() / Graphic3D(), kept when objects are added; None for Draw(...) alone."""
    def __init__(self, items, dim=None):
        self.items, self.dim = [], dim
        for i in items:
            if isinstance(i, Figure):
                self.items += i.items
                self.dim = self.dim or i.dim
            elif isinstance(i, tuple) and len(i) in (2, 3) and all(isinstance(c, (int, float, sp.Expr)) for c in i):
                self.items.append(_pt(i))          # Draw((2, -2, 3)): a point written in place
            elif isinstance(i, (list, tuple)):     # e.g. the points of Intersect(...)
                self.items += list(i)
            else:
                self.items.append(i)

    def _latex(self, printer):
        return r'\text{[figure]}'

    def __repr__(self):
        return 'Figure(%s)' % self.items


def Graphic():
    """Graphic(): an empty 2D figure; add objects with G.Draw(f, A, ...)."""
    return Figure([], 2)


def Graphic3D():
    """Graphic3D(): an empty 3D figure; add objects with G.Draw(S, P, ...) or G.Plot3D(x y)."""
    return Figure([], 3)


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
    if isinstance(f, sp.Eq):           # x^2 + y^2 + z = 0: one surface per solution for z
        sols = [e for e in sp.solve(f, z) if e.free_symbols <= {x, y}]
        if not sols:
            raise ValueError('cannot write %s as z = f(x, y)' % f)
        return Figure([Surface([e]) for e in sols])
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
    """A number moved by a slider; outside SymNote it is just its value."""
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


# A table is rows of cells (TableObj). Sign and variation tables are tables whose rows the CAS fills in:
#   row 0: the variable, then x0, '', x1, '', ... (points and the intervals between them)
#   sign rows: a label, then '+', '-', '0', '||' (forbidden value) or '' in the same columns
#   the f(x) row of a variation table: values at points ((left, right) at a forbidden value), arrows between
# Cells can be edited from the table's options (style['cells'] = {"row,col": text}); the shown and exported
# table follows the edited cells, arrows included.
_MARKS = {'+': '+', '-': '-', '0': '0', '||': '\\|', '|': '|', '/': '\\nearrow', '\\': '\\searrow',
          '↗': '\\nearrow', '↘': '\\searrow', '->': '\\rightarrow', '→': '\\rightarrow', '': '',
          'oo': '+\\infty', '+oo': '+\\infty', '-oo': '-\\infty'}     # ∞ in a text was already written oo
_TKZ = {'+': '+', '-': '-', '0': 'z', 'z': 'z', '||': 'd', 'd': 'd', '': ''}
_UP, _DOWN = ('↗', '/'), ('↘', '\\')


def cell_tex(v):
    """LaTeX of one table cell: a value, or text ("+", "-", "0", "||", "↗", "↘" are drawn as signs and arrows)."""
    if v is None:
        return ''
    if isinstance(v, str):
        if v.strip() in _MARKS:
            return _MARKS[v.strip()]
        # text, with $...$ parts as formulas: "Valeur de $f(x)$"
        parts = v.split('$')
        clean = lambda t: t.replace('\\', '').replace('{', '').replace('}', '')
        return ''.join(p if k % 2 else ('\\text{%s}' % clean(p) if p else '') for k, p in enumerate(parts))
    return _tex_x(v) if isinstance(v, sp.Basic) else sp.latex(v)


def cell_src(v):
    """The text of a cell as it is edited in the options: marks as they are, values as $LaTeX$."""
    if v is None:
        return ''
    if isinstance(v, tuple):
        return ' || '.join(cell_src(p) for p in v)
    if isinstance(v, str):
        return v
    return '$%s$' % cell_tex(v)


def _tkz(v):
    """A cell in tkz-tab: a sign code, or $LaTeX$."""
    if isinstance(v, str) and v.strip() in _TKZ:
        return _TKZ[v.strip()]
    t = cell_tex(v)
    return '$%s$' % t if t else ''


class TableObj:
    """A table of `ncols` columns: T = Table(3, 2) then T.Row(a, b, c) fills the next row."""
    kind = 'grid'

    def __init__(self, ncols, rows):
        self.ncols, self.rows = ncols, rows

    def _latex(self, printer=None):
        return r'\text{[table]}'

    def cells(self, style=None):
        """The rows with the edits of the options applied (an edited "a || b" splits a forbidden-value cell)."""
        rows = [list(r) for r in self.rows]
        for key, txt in ((style or {}).get('cells') or {}).items():
            try:
                r, c = map(int, key.split(','))
            except ValueError:
                continue
            if 0 <= r < len(rows) and 0 <= c < len(rows[r]):
                rows[r][c] = tuple(t.strip() for t in txt.split('||', 1)) if isinstance(rows[r][c], tuple) else txt
        return rows

    def sources(self):
        """Text of every cell, for the editor of the options."""
        return [[cell_src(c) for c in r] for r in self.rows]

    def grid(self, style=None):
        return [[{'t': cell_tex(c), 'k': 'g'} for c in r] for r in self.cells(style)]

    def tabular(self, style=None):
        """The table as a LaTeX tabular (math cells), following its options."""
        st = style or {}
        b = st.get('borders', 'all')
        w = st.get('colw') if isinstance(st.get('colw'), (int, float)) and 0.3 <= st['colw'] <= 15 else None
        al = {'left': 'l', 'right': 'r'}.get(st.get('align'), 'c')
        col = '>{%s\\arraybackslash}p{%scm}' % ({'l': '\\raggedright', 'r': '\\raggedleft'}.get(al, '\\centering'), _fmt_cm(w)) if w else al
        sep = '|' if b == 'all' else ''
        spec = ('|' if b != 'none' else '') + sep.join([col] * self.ncols) + ('|' if b != 'none' else '')
        rows = self.cells(st)
        out = ['\\begin{tabular}{%s}' % spec] + (['\\hline'] if b != 'none' else [])
        for k, r in enumerate(rows):
            cells = [('$%s$' % cell_tex(c)) if cell_tex(c) else '' for c in r]
            if st.get('headcol') and cells:
                cells[0] = '\\cellcolor{gray!15}' + cells[0]
            line = ('\\rowcolor{gray!15}' if st.get('headrow') and k == 0 else '') + ' & '.join(cells) + ' \\\\'
            if b == 'all' or (b == 'outer' and (k == len(rows) - 1 or (k == 0 and st.get('headrow')))):
                line += ' \\hline'
            out.append(line)
        return out + ['\\end{tabular}']

    def latex(self, style=None):
        """The table in a LaTeX document (tabular, or tkz-tab for sign and variation tables)."""
        return self.tabular(style)

    def __str__(self):
        return '\n'.join(' | '.join(cell_src(c) for c in r) for r in self.rows)


def _lines(st):
    """Vertical lines at the points of sign rows: 'dots' (default), 'solid' (cut at the number) or 'none'."""
    if st.get('lines') in ('dots', 'solid', 'none'):
        return st['lines']
    return 'none' if st.get('dots') is False else 'dots'      # files saved before the choice existed


def _tikz_lines(st):
    """tkz-tab draws its point lines dotted; solid lines are a style switch inside the picture."""
    # the zeros of tkz-tab are plain nodes: a white fill cuts the solid line at the number
    return ['\\tikzset{t style/.style={style=solid}, every node/.append style={fill=white}}'] if _lines(st) == 'solid' else []


class _XTable(TableObj):
    """Common part of sign and variation tables: row 0 holds the points, sign rows hold marks."""
    def _point(self, c):
        return c % 2 == 1          # column 0 is the label; then x0, gap, x1, ...

    def _sign_cells(self, row, r, st, head=False):
        n = len(row)
        out = [{'t': cell_tex(row[0]), 'k': 'lab', 'r': r, 'c': 0}]
        for c in range(1, n):
            v = row[c]
            if head:
                k = 'head'
            elif not self._point(c):
                k = 'iv'
            elif isinstance(v, str) and v.strip() == '||':
                k, v = 'bar', ''
            else:
                k = 'pt' + ({'dots': ' dot', 'solid': ' sol'}.get(_lines(st), '') if 1 < c < n - 1 else '')
            out.append({'t': cell_tex(v), 'k': k, 'r': r, 'c': c})
        return out

    def _tab_line(self, row, st):
        dots = _lines(st) != 'none'
        return [_tkz(v) or ('t' if dots and self._point(c) and 1 < c < len(row) - 1 else '') for c, v in enumerate(row) if c]

    def _tab_init(self, st, labels):
        xs = self.cells(st)[0]
        return '\\tkzTabInit[%s]{%s}{%s}' % (_tab_opts(st), ', '.join(labels),
                                             ', '.join(_tkz(v) for c, v in enumerate(xs) if c and self._point(c)))

    def latex(self, style=None):
        return self.tkztab(style)


class SignTableObj(_XTable):
    """Sign table of an expression: one row per factor (when there are several), then the expression."""
    kind = 'sign'

    def __init__(self, e, v):
        _numeric(e, v)
        self.var = v
        pts, dom, excluded = _table_points(e, v)
        num, den = sp.fraction(sp.factor(sp.together(e)))
        facs = [f ** k for f, k in sp.factor_list(num)[1] if f.has(v)] + [f ** k for f, k in sp.factor_list(den)[1] if f.has(v)]
        zeros = set()
        for f in facs:
            zeros |= _roots(f, v, sp.Interval(pts[0], pts[-1]))
        self.xs = xs = sorted(set(pts) | zeros, key=lambda b: float(b))
        rows = [[v] + [p if p is not None else '' for p in _spread(xs)]]
        for f in (facs if len(facs) > 1 else []):
            rows.append([f] + self._marks(f, xs, lambda p: '0' if sp.simplify(f.subs(v, p)) == 0 else ''))
        rows.append([e] + self._marks(e, xs, lambda p: '||' if p in excluded or p not in dom
                                      else '0' if sp.simplify(e.subs(v, p)) == 0 else ''))
        self.nfac = len(rows) - 2           # factor rows: 1 .. nfac
        super().__init__(len(rows[0]), rows)

    def _marks(self, f, xs, at_point):
        out = []
        for k, p in enumerate(xs):
            if k:
                out.append(_sign(f, self.var, _test_point(xs[k - 1], p)))
            out.append(at_point(p) if p.is_finite else '')
        return out

    def _shown(self, st):
        rows = list(enumerate(self.cells(st)))
        return rows if st.get('factors', True) else [rc for rc in rows if not 1 <= rc[0] <= self.nfac]

    def grid(self, style=None):
        st = style or {}
        return [self._sign_cells(row, r, st, head=r == 0) for r, row in self._shown(st)]

    def tkztab(self, style=None):
        st = style or {}
        shown = self._shown(st)
        out = ['\\begin{tikzpicture}'] + _tikz_lines(st) + [self._tab_init(st, ['%s/1' % _tkz(row[0]) for _, row in shown])]
        out += ['\\tkzTabLine{%s}' % ', '.join(self._tab_line(row, st)) for r, row in shown if r]
        return out + ['\\end{tikzpicture}']


class VariationTableObj(_XTable):
    """Variation table of f: sign of f', and f with arrows, values and limits."""
    kind = 'var'

    def __init__(self, f):
        e, v = _body(f)
        _numeric(e, v)
        self.var, self.f = v, f
        pts, dom, excluded = _table_points(e, v)
        d = sp.simplify(sp.diff(e, v))
        crit = _roots(d, v, sp.Interval.open(pts[0], pts[-1]) - sp.FiniteSet(*excluded))
        self.xs = xs = sorted(set(pts) | crit, key=lambda b: float(b))
        fp, fv = [], []
        for k, p in enumerate(xs):
            if k:
                s = _sign(d, v, _test_point(xs[k - 1], p))
                fp.append(s)
                fv.append('↗' if s == '+' else '↘' if s == '-' else '→')
            if not p.is_finite:
                fp.append('')
                fv.append(sp.limit(e, v, p, '-' if k else '+'))
            elif p in excluded or p not in dom:       # forbidden value (or open end): limits on each side
                fp.append('||')
                fv.append((sp.limit(e, v, p, '-') if k > 0 else None, sp.limit(e, v, p, '+') if k < len(xs) - 1 else None))
            else:
                dv = d.subs(v, p)
                fp.append('||' if not dv.is_finite else '0' if p in crit and sp.simplify(dv) == 0 else '')
                fv.append(sp.simplify(e.subs(v, p)))
        super().__init__(2 * len(xs), [[v] + [p if p is not None else '' for p in _spread(xs)], [None] + fp, [None] + fv])
        self.rename('f')

    def rename(self, name):
        """Labels f'(x) and f(x) with the function's own name (set by the notebook)."""
        self.name = name
        v = sp.latex(self.var)
        self.rows[1][0], self.rows[2][0] = "$%s'(%s)$" % (name, v), '$%s(%s)$' % (name, v)

    @staticmethod
    def _dir(a):
        return '+' if a in _UP else '-' if a in _DOWN else '0'

    def _places(self, fv):
        """Per point column: (left place, right place), '+' top or '-' bottom, from the arrows around it."""
        n, out = len(fv), {}
        for c in range(1, n, 2):
            left = self._dir(fv[c - 1]) if c > 1 else None
            right = self._dir(fv[c + 1]) if c + 1 < n else None
            lp = '+' if left == '+' else '-' if left else None
            rp = '-' if right == '+' else '+' if right else None
            out[c] = (lp or rp or '+', rp or lp or '+')
        return out

    def grid(self, style=None):
        st = style or {}
        rows = self.cells(st)
        fv = [str(a).strip() if isinstance(a, str) else a for a in rows[2]]
        places = self._places(fv)
        out = [self._sign_cells(rows[0], 0, st, head=True), self._sign_cells(rows[1], 1, st)]
        sub = {'+': [], '0': [], '-': []}
        for c in range(1, len(fv)):
            v = fv[c]
            for lvl, k in (('+', ' vt'), ('0', ' vm'), ('-', ' vb')):
                cell = {'k': ('pt' if self._point(c) else 'iv') + k, 'r': 2, 'c': c, 't': ''}
                if isinstance(v, tuple):          # forbidden value: double bar, left and right values
                    lp, rp = places[c]
                    cell.update(k='bar' + k, t=cell_tex(v[0]) if lp == lvl and v[0] is not None else '',
                                t2=cell_tex(v[1]) if rp == lvl and len(v) > 1 and v[1] is not None else '')
                elif self._point(c):
                    if places[c][0 if c > 1 else 1] == lvl:
                        cell['t'] = cell_tex(v)
                elif lvl == '0':                  # between two points: an arrow (drawn value to value) or text
                    d = self._dir(v)
                    if d != '0' or (isinstance(v, str) and v in ('→', '->')):
                        cell['ar'] = d
                    else:
                        cell['t'] = cell_tex(v)
                sub[lvl].append(cell)
        lab = {'t': cell_tex(rows[2][0]), 'k': 'lab', 'rs': 3, 'r': 2, 'c': 0}
        out += [[lab] + sub['+'], sub['0'], sub['-']]
        out += [self._sign_cells(row, r, st) for r, row in enumerate(rows) if r > 2]
        return out

    def tkztab(self, style=None):
        st = style or {}
        rows = self.cells(st)
        fv = [str(a).strip() if isinstance(a, str) else a for a in rows[2]]
        places, var = self._places(fv), []
        for c in range(1, len(fv), 2):
            v, (lp, rp) = fv[c], places[c]
            if isinstance(v, tuple):
                a, b = v[0], v[1] if len(v) > 1 else None
                if a is None or a == '':
                    var.append('D%s/ / %s' % (rp, _tkz(b)))
                elif b is None or b == '':
                    var.append('%sD/ %s /' % (lp, _tkz(a)))
                else:
                    var.append('%sD%s/ %s / %s' % (lp, rp, _tkz(a), _tkz(b)))
            else:
                var.append('%s/ %s' % (lp if c > 1 else rp, _tkz(v)))
        labels = ['%s/1' % _tkz(rows[0][0]), '%s/1' % _tkz(rows[1][0]), '%s/2' % _tkz(rows[2][0])] + \
                 ['%s/1' % _tkz(r[0]) for r in rows[3:]]
        out = ['\\begin{tikzpicture}'] + _tikz_lines(st) + [self._tab_init(st, labels),
               '\\tkzTabLine{%s}' % ', '.join(self._tab_line(rows[1], st)), '\\tkzTabVar{%s}' % ', '.join(var)]
        out += ['\\tkzTabLine{%s}' % ', '.join(self._tab_line(r, st)) for r in rows[3:]]
        return out + ['\\end{tikzpicture}']


def _tab_opts(style):
    """tkzTabInit options: espcl (space between two x values) and lgt (first column), in cm."""
    st = style or {}
    num = lambda k, d: float(st[k]) if isinstance(st.get(k), (int, float)) and 0.3 <= st[k] <= 15 else d
    return 'espcl=%s,lgt=%s' % (_fmt_cm(num('colw', 2)), _fmt_cm(num('lgt', 2)))


def _fmt_cm(v):
    return ('%.2f' % v).rstrip('0').rstrip('.')


def _spread(xs):
    """x0, gap, x1, gap, ... (the columns of a table)."""
    out = []
    for k, p in enumerate(xs):
        if k:
            out.append(None)
        out.append(p)
    return out


def SignTable(f, var=None):
    """SignTable(x^2 - 4): sign table (one row per factor, then the expression)."""
    e, v = _body(f)
    return SignTableObj(e, var or v)


def VariationTable(f):
    """VariationTable(f): sign of f' and variations of f, with values and limits."""
    return VariationTableObj(f)


def Table(columns, rows=0):
    """Table(columns, rows): an empty table; add its rows with T.Row(a, b, ...)."""
    n = int(columns)
    if n < 1 or n > 40:
        raise ValueError('a table has 1 to 40 columns')
    return TableObj(n, [[None] * n for _ in range(int(rows))])


def Row(table, *cells):
    """Row(T, a, b, ...) — written T.Row(a, b, ...): fills the first empty row of T, or adds one.
    On a sign or variation table it adds a sign row: a label, then marks under the points and intervals."""
    if not isinstance(table, TableObj):
        raise ValueError('Row(...) adds a row to a table: T = Table(3) then T.Row(a, b, c)')
    if len(cells) > table.ncols:
        raise ValueError('this table has %d columns, not %d' % (table.ncols, len(cells)))
    new = copy.copy(table)                        # a new table: the lines before this one keep theirs
    new.rows = [list(r) for r in table.rows]
    row = list(cells) + [None if table.kind == 'grid' else ''] * (table.ncols - len(cells))
    k = next((i for i, r in enumerate(new.rows) if all(c is None for c in r)), None) if table.kind == 'grid' else None
    if k is None:
        new.rows.append(row)
    else:
        new.rows[k] = row
    return new


TABLES = (TableObj,)


# ---------------------------------------------------------------- arithmetic
def PrimeFactors(n):
    """PrimeFactors(360) = 2^3 · 3^2 · 5 (the decomposition into prime factors, not computed back)."""
    f = sp.factorint(sp.Integer(n))
    return sp.Mul(*[sp.Pow(p, k, evaluate=False) if k > 1 else sp.Integer(p) for p, k in sorted(f.items())], evaluate=False)


def Quotient(a, b):
    """Quotient(17, 5) = 3: the quotient of the Euclidean division (17 = 5·3 + 2)."""
    return sp.floor(sp.Integer(a) / sp.Integer(b))


def Remainder(a, b):
    """Remainder(17, 5) = 2: the remainder of the Euclidean division, 0 <= r < |b|."""
    return sp.Mod(sp.Integer(a), abs(sp.Integer(b)))


# ---------------------------------------------------------------- polynomials
def _poly_var(p):
    return _var(p) if p.free_symbols else x


def Degree(p):
    """Degree(x^3 - 2x) = 3."""
    p = sp.sympify(p)
    return sp.degree(p, _poly_var(p))


def Coefficients(p):
    """Coefficients(2x^2 - 3x + 1) = [2, -3, 1], from the highest degree."""
    p = sp.sympify(p)
    return sp.Poly(p, _poly_var(p)).all_coeffs()


def Roots(p):
    """Roots((x - 1)^2 (x + 2)) = {-2: 1, 1: 2}: each root with its multiplicity."""
    p = sp.sympify(p.lhs - p.rhs if isinstance(p, sp.Eq) else p)
    return sp.roots(sp.Poly(p, _poly_var(p)))


def Discriminant(p):
    """Discriminant(a x^2 + b x + c) = b^2 - 4ac."""
    p = sp.sympify(p)
    return sp.discriminant(p, _poly_var(p))


def Divide(a, b):
    """Divide(A, B) = [Q, R] with A = B·Q + R and deg R < deg B (Euclidean division of polynomials)."""
    a, b = sp.sympify(a), sp.sympify(b)
    q, r = sp.div(a, b, _poly_var(a))
    return [q, r]


# ---------------------------------------------------------------- trigonometry
def TrigSimplify(e):
    """TrigSimplify(sin(x)^2 + cos(x)^2) = 1."""
    return sp.trigsimp(e)


def TrigExpand(e):
    """TrigExpand(cos(2x)) = 2cos(x)^2 - 1 (formulas of sums and multiple angles)."""
    return sp.expand_trig(e)


def TrigLinearize(e):
    """TrigLinearize(cos(x)^2) = cos(2x)/2 + 1/2: products and powers into sums."""
    from sympy.simplify.fu import TR8
    return sp.expand(TR8(sp.expand(e)))


def SolveIn(eq, var, a, b):
    """SolveIn(sin(x) = 1/2, x, 0, 2pi): the solutions in [a, b]."""
    return sp.solveset(sp.sympify(eq), var, sp.Interval(a, b))


def Degrees(r):
    """Degrees(pi/3) = 60: radians to degrees."""
    return sp.nsimplify(r * 180 / sp.pi)


def Radians(d):
    """Radians(60) = pi/3: degrees to radians."""
    return sp.nsimplify(d * sp.pi / 180)
