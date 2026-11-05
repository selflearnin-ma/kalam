"""SymNote runtime: every built-in command, written with SymPy only.

This file is self-contained on purpose: the Python exporter copies it verbatim
into exported scripts, so an exported notebook runs with nothing but SymPy.
Inside, always use `sp.X` (never bare names) because commands such as
`Integral` or `Matrix` shadow SymPy's own names in the exported namespace.
"""
import copy
import sympy as sp
from sympy.geometry.entity import GeometryEntity
from sympy.geometry.line import LinearEntity3D

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


def _M(P):
    return sp.Matrix(list(P.args) if isinstance(P, sp.Point) else list(P))


class Circle3D:
    """A circle in space: center, radius and the normal of its plane."""
    def __init__(self, center, r, normal):
        self.center, self.r, self.dim = sp.Point3D(*center), sp.sympify(r), 3
        n = _M(normal)
        self.normal = n / sp.sqrt(n.dot(n))

    def points(self, k=72):
        """Numeric points around the circle (for drawing)."""
        n = [float(c) for c in self.normal]
        a = [1.0, 0.0, 0.0] if abs(n[0]) < 0.9 else [0.0, 1.0, 0.0]
        u = [n[1] * a[2] - n[2] * a[1], n[2] * a[0] - n[0] * a[2], n[0] * a[1] - n[1] * a[0]]
        lu = sum(c * c for c in u) ** 0.5
        u = [c / lu for c in u]
        v = [n[1] * u[2] - n[2] * u[1], n[2] * u[0] - n[0] * u[2], n[0] * u[1] - n[1] * u[0]]
        c, r = [float(t) for t in self.center.args], float(self.r)
        import math
        return [[c[i] + r * (math.cos(2 * math.pi * j / k) * u[i] + math.sin(2 * math.pi * j / k) * v[i]) for i in range(3)]
                for j in range(k + 1)]

    def _latex(self, printer):
        a, b, c = self.center.args
        sph = sp.Eq((x - a)**2 + (y - b)**2 + (z - c)**2, self.r**2, evaluate=False)
        n = self.normal
        pl = sp.Eq(sp.expand(n[0] * (x - a) + n[1] * (y - b) + n[2] * (z - c)), 0)
        return r'\begin{cases} %s \\ %s \end{cases}' % (printer._print(sph), printer._print(pl))


class Polygon3D:
    """A polygon in space (its vertices lie in one plane)."""
    def __init__(self, vertices):
        self.vertices, self.dim = [sp.Point3D(*v) for v in vertices], 3

    @property
    def area(self):
        o, s_ = _M(self.vertices[0]), sp.zeros(3, 1)
        for a, b in zip(self.vertices[1:], self.vertices[2:]):
            s_ += (_M(a) - o).cross(_M(b) - o)
        return sp.simplify(sp.sqrt(s_.dot(s_)) / 2)

    @property
    def perimeter(self):
        v = self.vertices
        return sp.simplify(sum(a.distance(b) for a, b in zip(v, v[1:] + v[:1])))

    def _latex(self, printer):
        return r'\mathcal{P}\left(%s\right),\ \mathcal{A} = %s' % (
            ', '.join(r'\left(%s\right)' % ', '.join(printer._print(c) for c in p.args) for p in self.vertices), printer._print(self.area))


class Solid:
    """A solid: vertices and faces (for drawing), its volume and its area (exact)."""
    def __init__(self, vertices, faces, volume, area, edges=True):
        self.vertices, self.faces, self.dim = vertices, faces, 3
        self.volume, self.area, self.edges = sp.simplify(volume), sp.simplify(area), edges

    def _latex(self, printer):
        return r'\mathcal{V} = %s,\ \mathcal{A} = %s' % (printer._print(self.volume), printer._print(self.area))


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
    """Circle(center, radius) | Circle(center, point) | Circle(A, B, C).
    In space: Circle(center, radius, normal vector) (horizontal when no normal is given) | Circle(A, B, C)."""
    C = _pt(C)
    if C.ambient_dimension == 3:
        if len(r) == 2 and all(isinstance(_pt(p), sp.Point) for p in r):        # through three points
            A, a, b = _M(C), _M(_pt(r[0])) - _M(C), _M(_pt(r[1])) - _M(C)
            n = a.cross(b)
            O = A + (a.dot(a) * b.cross(n) + b.dot(b) * n.cross(a)) / (2 * n.dot(n))
            return Circle3D(list(O), sp.sqrt(sp.simplify((O - A).dot(O - A))), n)
        rad = C.distance(_pt(r[0])) if isinstance(r[0], (tuple, sp.Point)) else r[0]
        n = r[1] if len(r) > 1 else (0, 0, 1)
        return Circle3D(C, rad, n.comps if isinstance(n, Vec) else n)
    if len(r) == 2:
        return sp.Circle(C, _pt(r[0]), _pt(r[1]))
    r = r[0]
    if isinstance(r, (tuple, sp.Point)):
        r = C.distance(_pt(r))
    return sp.Circle(C, r)


def Polygon(*pts):
    pts = [_pt(p) for p in pts]
    return Polygon3D(pts) if pts[0].ambient_dimension == 3 else sp.Polygon(*pts)


def Midpoint(A, B=None):
    if B is None:
        return A.midpoint
    return _pt(A).midpoint(_pt(B))


def _sphere_cut(s, o):
    """Intersection of a sphere with a line, a plane or another sphere."""
    C, r = _M(s.center), s.r
    if isinstance(o, SphereObj):           # two spheres: their radical plane cuts the first one
        D = _M(o.center)
        n = D - C
        if n.dot(n) == 0:
            return []
        k = (n.dot(n) + r**2 - o.r**2) / (2 * n.dot(n))
        o = sp.Plane(sp.Point3D(*(C + k * n)), normal_vector=list(n))
    if isinstance(o, sp.Plane):
        d = sp.simplify(o.distance(s.center))
        if (d - r).is_positive:
            return []
        H = o.projection(s.center)
        rr = sp.sqrt(sp.simplify(r**2 - d**2))
        return H if rr == 0 else Circle3D(H, rr, o.normal_vector)
    if isinstance(o, LinearEntity3D):
        t = sp.Symbol('t', real=True)
        P, u = _M(o.p1), _M(o.direction_ratio)
        pts = [sp.Point3D(*(P + v * u)) for v in sp.solveset((P + t * u - C).dot(P + t * u - C) - r**2, t, sp.S.Reals)]
        return [p for p in pts if o.contains(p)]
    raise ValueError('cannot intersect a sphere with %s' % type(o).__name__)


def Intersect(a, b):
    a, b = _pt(a), _pt(b)
    if isinstance(a, SphereObj) or isinstance(b, SphereObj):
        r = _sphere_cut(*((a, b) if isinstance(a, SphereObj) else (b, a)))
        return _one(r) if isinstance(r, list) else r      # points, or a circle (plane / sphere)
    if isinstance(a, GeometryEntity) and isinstance(b, GeometryEntity):
        return _one(a.intersection(b))
    sols = sp.solve([_as_eq(a), _as_eq(b)], [x, y], dict=True)
    pts = [sp.Point2D(s[x], s[y]) for s in sols if x in s and y in s
           and s[x].is_real is not False and s[y].is_real is not False]
    return _one(pts)


def Perpendicular(P, l):
    return l.perpendicular_line(_pt(P))


def Parallel(P, l):
    """The parallel to l through P: a line, or (l a plane) a plane."""
    if isinstance(l, sp.Plane):
        return sp.Plane(_pt(P), normal_vector=l.normal_vector)
    return l.parallel_line(_pt(P))


def PerpendicularBisector(A, B=None):
    """The perpendicular bisector of [AB]: a line in the plane, a plane in space."""
    seg = A if B is None else Segment(A, B)
    if isinstance(seg, sp.Segment3D):
        return sp.Plane(seg.midpoint, normal_vector=list(_M(seg.p2) - _M(seg.p1)))
    return seg.perpendicular_bisector()


def AngleBisector(A, B, C):
    """Bisector of angle ABC (vertex B)."""
    A, B, C = _pt(A), _pt(B), _pt(C)
    u = (A - B) / A.distance(B)
    v = (C - B) / C.distance(B)
    w = [sp.simplify(c) for c in (u + v).args]
    return sp.Line3D(B, B + sp.Point3D(*w)) if len(w) == 3 else sp.Line(B, B + sp.Point(*w))


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
    if isinstance(o, Circle3D):
        return 2 * sp.pi * o.r
    if isinstance(o, (sp.Polygon, Polygon3D)):
        return sp.simplify(o.perimeter)
    return sp.simplify(o.length)


def Area(o):
    """Area of a polygon or a circle (disc); in space also of a sphere and of a solid's surface."""
    if isinstance(o, SphereObj):
        return 4 * sp.pi * o.r**2
    if isinstance(o, Circle3D):
        return sp.pi * o.r**2
    return sp.simplify(abs(o.area))


def Volume(o):
    """Volume of a solid (Tetrahedron, Pyramid, Prism, Cube, Cuboid, Cylinder, Cone) or of a sphere (ball)."""
    if isinstance(o, SphereObj):
        return sp.Rational(4, 3) * sp.pi * o.r**3
    if isinstance(o, Solid):
        return o.volume
    raise ValueError('Volume(...) is for solids and spheres')


# ---------------------------------------------------------------- solids
def _p3(P):
    P = _pt(P)
    if not (isinstance(P, sp.Point) and P.ambient_dimension == 3):
        raise ValueError('a solid needs points of space (x, y, z)')
    return sp.Point3D(*P.args)


def _face_area(pts):
    return Polygon3D(pts).area


def _polyhedron(vs, faces, volume):
    return Solid(vs, faces, volume, sum(_face_area([vs[i] for i in f]) for f in faces))


def Pyramid(S, *base):
    """Pyramid(S, A, B, C, ...): apex S and base polygon A B C ... (Pyramid(S, A, B, C) is a tetrahedron)."""
    S, base = _p3(S), [_p3(P) for P in base]
    if len(base) < 3:
        raise ValueError('the base needs at least 3 points')
    vs = base + [S]
    k = len(base)
    faces = [list(range(k))] + [[i, (i + 1) % k, k] for i in range(k)]
    plane = sp.Plane(*base[:3])
    return _polyhedron(vs, faces, Polygon3D(base).area * plane.distance(S) / 3)


def Tetrahedron(A, B, C, D):
    """Tetrahedron(A, B, C, D)."""
    return Pyramid(D, A, B, C)


def Prism(*args):
    """Prism(A, B, C, ..., u): the base polygon A B C ... moved along the vector u."""
    *base, u = args
    base = [_p3(P) for P in base]
    u = u.comps if isinstance(u, Vec) else list(_pt(u).args)
    top = [sp.Point3D(*[a + b for a, b in zip(P.args, u)]) for P in base]
    k = len(base)
    faces = [list(range(k)), list(range(k, 2 * k))] + [[i, (i + 1) % k, k + (i + 1) % k, k + i] for i in range(k)]
    n = _M(sp.Plane(*base[:3]).normal_vector)
    h = abs(n.dot(sp.Matrix(u))) / sp.sqrt(n.dot(n))
    return _polyhedron(base + top, faces, Polygon3D(base).area * h)


def Cuboid(A, a, b, c):
    """Cuboid(A, a, b, c): rectangular box with corner A and edges a, b, c along the axes."""
    A = _p3(A)
    return Prism(A, A + sp.Point3D(a, 0, 0), A + sp.Point3D(a, b, 0), A + sp.Point3D(0, b, 0), (0, 0, c))


def Cube(A, a):
    """Cube(A, a): cube with corner A and edge a along the axes."""
    return Cuboid(A, a, a, a)


def _round(A, B, r, apex, n=36):
    """Cylinder (apex False) or cone (apex True): base disc centered at A, axis to B; a mesh of n sides."""
    A, B, r = _p3(A), _p3(B), sp.sympify(r)
    base = Circle3D(A, r, _M(B) - _M(A)).points(n)[:-1]
    h = A.distance(B)
    d = [float(b - a) for a, b in zip(A.args, B.args)]
    ring = [sp.Point3D(*p) for p in base]
    if apex:
        vs = ring + [B, A]
        faces = [[i, (i + 1) % n, n] for i in range(n)] + [[i, (i + 1) % n, n + 1] for i in range(n)]
        return Solid(vs, faces, sp.pi * r**2 * h / 3, sp.pi * r**2 + sp.pi * r * sp.sqrt(r**2 + h**2), edges=False)
    top = [sp.Point3D(*[p[i] + d[i] for i in range(3)]) for p in base]
    vs = ring + top + [A, B]
    faces = [[i, (i + 1) % n, n + (i + 1) % n, n + i] for i in range(n)] + \
            [[i, (i + 1) % n, 2 * n] for i in range(n)] + [[n + i, n + (i + 1) % n, 2 * n + 1] for i in range(n)]
    return Solid(vs, faces, sp.pi * r**2 * h, 2 * sp.pi * r**2 + 2 * sp.pi * r * h, edges=False)


def Cylinder(A, B, r):
    """Cylinder(A, B, r): axis from the center A of one base to the center B of the other, radius r."""
    return _round(A, B, r, False)


def Cone(A, B, r):
    """Cone(A, B, r): base disc centered at A with radius r, apex B."""
    return _round(A, B, r, True)


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


def _is3d(o):
    if isinstance(o, (list, tuple)):
        return any(_is3d(i) for i in o)
    return isinstance(o, (sp.Point3D, LinearEntity3D, sp.Plane, SphereObj, Circle3D, Polygon3D, Solid)) or (isinstance(o, Vec) and o.dim == 3)


def _map3d(o, f, k=1):
    """A 3D object whose points are moved by f (k: ratio of lengths, for the radius of a sphere)."""
    if isinstance(o, (list, tuple)):
        return [_map3d(i, f, k) for i in o]
    if isinstance(o, sp.Point3D):
        return sp.Point3D(*f(o))
    if isinstance(o, LinearEntity3D):
        return type(o)(sp.Point3D(*f(o.p1)), sp.Point3D(*f(o.p2)))
    if isinstance(o, sp.Plane):           # three points of the plane, moved
        n = sp.Matrix(o.normal_vector)
        u = n.cross(sp.Matrix([1, 0, 0]) if n[1] != 0 or n[2] != 0 else sp.Matrix([0, 1, 0]))
        v = n.cross(u)
        P = sp.Matrix(o.p1)
        return sp.Plane(*[sp.Point3D(*f(sp.Point3D(*(P + w)))) for w in (sp.zeros(3, 1), u, v)])
    if isinstance(o, SphereObj):
        return SphereObj(sp.Point3D(*f(o.center)), abs(k) * o.r)
    if isinstance(o, Circle3D):
        n2 = sp.Matrix(f(sp.Point3D(*(_M(o.center) + o.normal)))) - sp.Matrix(f(o.center))
        return Circle3D(f(o.center), abs(k) * o.r, n2)
    if isinstance(o, Polygon3D):
        return Polygon3D([f(P) for P in o.vertices])
    if isinstance(o, Solid):
        return Solid([sp.Point3D(*f(P)) for P in o.vertices], o.faces, abs(k)**3 * o.volume, k**2 * o.area, o.edges)
    if isinstance(o, Vec):                # a free vector: only its direction and length change
        O = sp.Point3D(0, 0, 0)
        return Vec(list(sp.Matrix(f(sp.Point3D(*o.comps))) - sp.Matrix(f(O))))
    raise ValueError('cannot transform %s in space' % type(o).__name__)


def _proj(P, about):
    """Orthogonal projection of a 3D point on a plane or a line."""
    return about.projection(P)


def Reflect(o, about):
    """Symmetric of o with respect to a point, a line or (in space) a plane."""
    o = _pt(o) if isinstance(o, tuple) else o      # (1, 2) written in place is a point
    about = _pt(about)
    if _is3d(o) or isinstance(about, (sp.Point3D, sp.Plane, LinearEntity3D)):
        if isinstance(about, sp.Point):
            about = sp.Point3D(*about.args) if len(about.args) == 3 else about
            return _map3d(o, lambda P: [2 * a - b for a, b in zip(about.args, P.args)])
        return _map3d(o, lambda P: [2 * a - b for a, b in zip(_proj(P, about).args, P.args)])
    if isinstance(about, sp.Point):
        return o.rotate(sp.pi, about)
    return o.reflect(about)


def Rotate(o, angle, center=None):
    """Rotation of o by angle: around a point in the plane, around an axis (a line) in space."""
    o = _pt(o) if isinstance(o, tuple) else o      # (1, 2) written in place is a point
    if not _is3d(o):
        return o.rotate(angle, _pt(center) if center is not None else sp.Point(0, 0))
    if not isinstance(center, LinearEntity3D):
        raise ValueError('in space a rotation turns around an axis: Rotate(o, angle, Line(A, B))')
    A = sp.Matrix(center.p1)
    d = sp.Matrix(center.direction_ratio)
    d = d / sp.sqrt(d.dot(d))
    c, s = sp.cos(angle), sp.sin(angle)

    def turn(P):          # Rodrigues: v cos + (d × v) sin + d (d·v)(1 - cos), around the axis through A
        v = sp.Matrix(P) - A
        w = v * c + d.cross(v) * s + d * d.dot(v) * (1 - c)
        return [sp.simplify(t) for t in A + w]
    return _map3d(o, turn)


def Translate(o, v):
    """Translation of o by the vector v (in the plane or in space)."""
    o = _pt(o) if isinstance(o, tuple) else o      # (1, 2) written in place is a point
    if isinstance(v, sp.Point):
        v = Vector(v)
    comps = v.comps if isinstance(v, Vec) else list(v)
    if _is3d(o) or len(comps) == 3:
        comps = (list(comps) + [0, 0, 0])[:3]
        return _map3d(o, lambda P: [a + b for a, b in zip(P.args, comps)])
    return o.translate(*comps)


def Dilate(o, k, center=None):
    """Homothety of ratio k and given center (in the plane or in space)."""
    o = _pt(o) if isinstance(o, tuple) else o      # (1, 2) written in place is a point
    if _is3d(o):
        C = _pt(center) if center is not None else sp.Point3D(0, 0, 0)
        return _map3d(o, lambda P: [c + k * (p - c) for p, c in zip(P.args, C.args)], k)
    return o.scale(k, k, _pt(center) if center is not None else sp.Point(0, 0))


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


def Draw3D(*objs):
    """Draw3D(S, P, ...): a 3D figure with these objects."""
    return Figure(objs, 3)


def _cond(c):
    """A condition of Represent: an equation or inequality (a set in x, y, z)."""
    c = sp.sympify(c)
    if not isinstance(c, (sp.Rel, sp.And)):
        raise ValueError('Represent(...) takes equations or inequalities in x, y (z): x^2 + y^2 = 4, x + y - 1 > 0')
    return c


def Represent(*conds):
    """Represent(x^2 + y^2 = 4) | Represent(x + y - 1 > 0) | Represent(x > 0, y > 0, x + y < 2): the set of points
    (x, y) satisfying the conditions, in the plane (a curve, or a shaded region for inequalities)."""
    cs = [_cond(c) for c in conds]
    if any(c.has(z) for c in cs):
        raise ValueError('a condition with z is a set of space: Represent3D(...)')
    return Figure([cs[0] if len(cs) == 1 else sp.And(*cs, evaluate=False)], 2)


def _surface3d(e):
    """The surface e(x, y, z) = 0: a plane, a sphere, or pieces z = f(x, y) (or y = ..., x = ...)."""
    e = sp.expand(e)
    p = sp.Poly(e, x, y, z) if e.free_symbols <= {x, y, z} else None
    if p is not None and p.total_degree() == 1:
        n = [p.coeff_monomial(v) for v in (x, y, z)]
        k = next(i for i, c in enumerate(n) if c != 0)
        P = [0, 0, 0]
        P[k] = -p.coeff_monomial(1) / n[k]
        return [sp.Plane(sp.Point3D(*P), normal_vector=n)]
    if p is not None and p.total_degree() == 2:
        a = [p.coeff_monomial(v**2) for v in (x, y, z)]
        cross = [p.coeff_monomial(m) for m in (x * y, y * z, x * z)]
        if a[0] != 0 and a[0] == a[1] == a[2] and not any(cross):       # a sphere: complete the squares
            b = [p.coeff_monomial(v) for v in (x, y, z)]
            C = [-bi / (2 * a[0]) for bi in b]
            r2 = sum(c**2 for c in C) - p.coeff_monomial(1) / a[0]
            if r2.is_positive:
                return [SphereObj(sp.Point3D(*C), sp.sqrt(r2))]
    if p is not None and p.total_degree() == 2:   # a circle in two variables, the third free: a cylinder
        for free, (u, w) in ((z, (x, y)), (y, (x, z)), (x, (y, z))):
            if e.has(free):
                continue
            a2 = [p.coeff_monomial(v**2) for v in (u, w)]
            if a2[0] != 0 and a2[0] == a2[1] and p.coeff_monomial(u * w) == 0:
                C = [-p.coeff_monomial(v) / (2 * a2[0]) for v in (u, w)]
                r2 = C[0]**2 + C[1]**2 - p.coeff_monomial(1) / a2[0]
                if r2.is_positive:
                    t, h = sp.Symbol('t'), sp.Symbol('h')
                    pos = {u: C[0] + sp.sqrt(r2) * sp.cos(t), w: C[1] + sp.sqrt(r2) * sp.sin(t), free: h}
                    return [Surface([pos[x], pos[y], pos[z]], t, (0, 2 * sp.pi), h, (-5, 5))]
    R = (-5, 5)
    for v, (u, w) in ((z, (x, y)), (y, (x, z)), (x, (y, z))):
        if not e.has(v):
            continue
        sols = [s for s in sp.solve(e, v) if s.free_symbols <= {u, w}]
        if sols:
            if v == z:
                return [Surface([s]) for s in sols]
            return [Surface([s if c == v else c for c in (x, y, z)], u, R, w, R) for s in sols]
    raise ValueError('cannot draw %s = 0' % e)


def Represent3D(*conds):
    """Represent3D(x^2 + y^2 + z^2 = 4) | Represent3D(x + y + z = 1) | Represent3D(x^2 + y^2 = 1): the surfaces of
    space given by the conditions (for an inequality, the surface that bounds the region)."""
    items = []
    for c in conds:
        c = _cond(c)
        for r in (c.args if isinstance(c, sp.And) else [c]):
            items += _surface3d(r.lhs - r.rhs)
    return Figure(items, 3)


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


# ---------------------------------------------------------------- sets
def Interval(a, b):
    """Interval(a, b) = [a ; b] (closed); a or b may be -oo, oo."""
    return sp.Interval(a, b, left_open=a == -sp.oo, right_open=b == sp.oo)


def IntervalOpen(a, b):
    """IntervalOpen(a, b) = ]a ; b[."""
    return sp.Interval.open(a, b)


def IntervalLOpen(a, b):
    """IntervalLOpen(a, b) = ]a ; b]."""
    return sp.Interval.Lopen(a, b)


def IntervalROpen(a, b):
    """IntervalROpen(a, b) = [a ; b[."""
    return sp.Interval.Ropen(a, b)


def FiniteSet(*el):
    """FiniteSet(1, 2, 3) = {1, 2, 3}."""
    return sp.FiniteSet(*el)


def Union(*sets):
    """Union(A, B, ...) = A ∪ B ∪ ... (also written A ∪ B)."""
    return sp.Union(*sets)


def Intersection(*sets):
    """Intersection(A, B, ...) = A ∩ B ∩ ... (also written A ∩ B)."""
    return sp.Intersection(*sets)


def Complement(A, B):
    """Complement(A, B) = A ∖ B: the elements of A not in B (also written A ∖ B)."""
    return sp.Complement(A, B)


def IsIn(a, S):
    """IsIn(a, S): is a an element of S (a ∈ S)?"""
    return sp.Contains(a, S).doit()


def IsSubset(A, B):
    """IsSubset(A, B): is A included in B (A ⊂ B)?"""
    return A.is_subset(B)


def Cardinal(S):
    """Cardinal(S): the number of elements of a finite set."""
    if not isinstance(S, sp.FiniteSet):
        raise ValueError('Cardinal(...) is for finite sets: {1, 2, 3}')
    return len(S)


def Inf(S):
    """Inf(S): the infimum of S (its smallest element when there is one)."""
    return sp.sympify(S).inf


def Sup(S):
    """Sup(S): the supremum of S (its largest element when there is one)."""
    return sp.sympify(S).sup
