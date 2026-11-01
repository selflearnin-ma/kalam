"""JSON bridge between the Kalam core and the web page (runs in Pyodide).

Every call returns JSON text; the page keeps no math state of its own.
Scenes describe drawables with plain numbers, and functions as JavaScript
expressions (sympy.jscode) so the browser can sample them at full speed.
"""
import io
import json
import math
import zipfile

import sympy as sp
from sympy.geometry.line import LinearEntity3D
from sympy.printing.jscode import jscode

from . import runtime
from .commands import CATEGORIES, Registry
from .engine import Session, dimension
from .export import figure_tkz, to_latex, to_python
from .i18n import STRINGS

X, Y, Z = runtime.x, runtime.y, runtime.z
session = Session(Registry(load_user=False))


# ---------------------------------------------------------------- scene
def _n(v):
    v = float(v)
    if not math.isfinite(v):
        raise ValueError('not finite')
    return v


def _p(pt):
    return [_n(a) for a in pt.args]


def _js(expr, allowed):
    expr = sp.sympify(expr)
    if not {s.name for s in expr.free_symbols} <= set(allowed):
        return None
    code = jscode(expr)
    return None if 'Not supported' in code else code


def scene(v, free=False):
    """List of drawing primitives for a value (empty when not drawable or symbolic)."""
    try:
        return _scene(v, free)
    except (TypeError, ValueError, AttributeError):
        return []


def _scene(v, free):
    if isinstance(v, (list, tuple)):
        return [p for i in v for p in scene(i)]
    if isinstance(v, sp.Point2D):
        return [dict(k='pt', p=_p(v), free=free)]
    if isinstance(v, sp.Segment2D):
        return [dict(k='seg', a=_p(v.p1), b=_p(v.p2))]
    if isinstance(v, (sp.Line2D, sp.Ray2D)):
        return [dict(k='line', a=_p(v.p1), b=_p(v.p2), ray=isinstance(v, sp.Ray2D))]
    if isinstance(v, sp.Circle):
        return [dict(k='circ', c=_p(v.center), r=_n(v.radius))]
    if isinstance(v, sp.Polygon):
        return [dict(k='poly', pts=[_p(a) for a in v.vertices])]
    if isinstance(v, sp.Lambda) and len(v.variables) == 1:
        var = v.variables[0].name
        js = _js(v.expr, [var])
        return [dict(k='fx', v=var, js=js, lo=None, hi=None)] if js else []
    if isinstance(v, sp.Lambda) and len(v.variables) == 2:
        js = _js(v.expr.subs(dict(zip(v.variables, (X, Y)))), 'xy')
        return [dict(k='surf', js=js)] if js else []
    if isinstance(v, runtime.Graph):
        js = _js(v.expr, [v.var.name])
        lo = None if v.a is None else _n(v.a)
        hi = None if v.b is None else _n(v.b)
        return [dict(k='fx', v=v.var.name, js=js, lo=lo, hi=hi)] if js else []
    if isinstance(v, runtime.Curve):
        js = [_js(c, [v.var.name]) for c in v.comps]
        if None in js:
            return []
        return [dict(k='par' if v.dim == 2 else 'cur3', v=v.var.name, js=js, lo=_n(v.a), hi=_n(v.b))]
    if isinstance(v, runtime.Vec):
        o = v.origin or (sp.Point3D(0, 0, 0) if v.dim == 3 else sp.Point2D(0, 0))
        a = _p(o)
        b = [x + _n(c) for x, c in zip(a, v.comps)]
        return [dict(k='vec' if v.dim == 2 else 'vec3', a=a, b=b)]
    if isinstance(v, sp.Point3D):
        return [dict(k='pt3', p=_p(v))]
    if isinstance(v, sp.Segment3D):
        return [dict(k='seg3', a=_p(v.p1), b=_p(v.p2))]
    if isinstance(v, LinearEntity3D):
        return [dict(k='line3', p=_p(v.p1), d=[_n(a) for a in v.direction_ratio], ray=isinstance(v, sp.Ray3D))]
    if isinstance(v, sp.Plane):
        n = [_n(a) for a in v.normal_vector]
        return [dict(k='plane', n=n, d=-sum(a * b for a, b in zip(n, _p(v.p1))))]
    if isinstance(v, runtime.SphereObj):
        return [dict(k='sph', c=_p(v.center), r=_n(v.r))]
    if isinstance(v, runtime.Surface):
        if len(v.comps) == 1:
            js = _js(v.comps[0], 'xy')
            return [dict(k='surf', js=js)] if js else []
        names = [v.u.name, v.v.name]
        js = [_js(c, names) for c in v.comps]
        if None in js:
            return []
        return [dict(k='psurf', u=names[0], v=names[1], js=js,
                     ur=[_n(a) for a in v.ur], vr=[_n(a) for a in v.vr])]
    if isinstance(v, sp.Equality) and v.has(Z):
        return [dict(k='surf', js=_js(b, 'xy')) for b in sp.solve(v, Z) if _js(b, 'xy')]
    if isinstance(v, sp.Equality) and v.lhs == Y and not v.rhs.has(Y):
        js = _js(v.rhs, 'x')
        return [dict(k='fx', v='x', js=js, lo=None, hi=None)] if js else []
    if isinstance(v, sp.Rel):
        op = {sp.Equality: '=', sp.StrictLessThan: '<', sp.LessThan: '<=',
              sp.StrictGreaterThan: '>', sp.GreaterThan: '>='}.get(type(v))
        js = _js(v.lhs - v.rhs, 'xy')
        return [dict(k='imp', js=js, op=op)] if js and op else []
    return []


# ---------------------------------------------------------------- state
def _cell_json(c):
    d = dict(kind=c.kind, text=c.text, visible=c.visible, color=c.color, name=c.name,
             label=c.label, latex=c.latex, error=c.error, note=c.note, parts=c.parts)
    if c.kind == 'math' and c.value is not None and not c.error:
        d['dim'] = dimension(c.value)
        d['free'] = c.is_free_point
        d['scene'] = scene(c.value, c.is_free_point) if d['dim'] else []
    if c.slider:
        s = c.slider
        d['slider'] = dict(lo=s.lo, hi=s.hi, step=s.step, value=float(c.value))
    return d


def state():
    return json.dumps(dict(cells=[_cell_json(c) for c in session.cells]))


def _cell(i):
    return session.cells[int(i)]


def set_text(i, text):
    session.set_text(_cell(i), text)
    return state()


def insert(i, kind='math', text=''):
    session.add_cell(text, kind, at=int(i))
    session.evaluate_from(int(i))
    return state()


def delete(i):
    session.remove_cell(_cell(i))
    if not session.cells:
        session.add_cell()
    return state()


def move(i, j):
    cells = session.cells
    i, j = int(i), int(j)
    cells[i], cells[j] = cells[j], cells[i]
    session.evaluate_from(min(i, j))
    return state()


def set_kind(i, kind):
    c = _cell(i)
    c.kind = kind
    session.evaluate_from(int(i))
    return state()


def set_style(i, visible, color):
    c = _cell(i)
    c.visible, c.color = bool(visible), color or None
    return state()


def move_point(i, x, y):
    session.move_point(_cell(i), x, y)
    return state()


def move_slider(i, value):
    session.move_slider(_cell(i), value)
    return state()


def new():
    session.cells[:] = []
    session.env = {}
    session.add_cell()
    return state()


# ---------------------------------------------------------------- files
def klm_text(lang='fr', view=None):
    data = {'format': 'kalam', 'version': 1, 'lang': lang, 'view2d': json.loads(view) if view else {},
            'cells': [dict(kind=c.kind, text=c.text, visible=c.visible, color=c.color) for c in session.cells],
            'commands': [c.to_json() for c in session.registry.user_commands()]}
    return json.dumps(data, ensure_ascii=False, indent=1)


def load_klm_text(text):
    data = json.loads(text)
    if data.get('format') != 'kalam':
        raise ValueError('not a Kalam file')
    for d in data.get('commands', []):
        if d['name'] not in session.registry.commands or session.registry.commands[d['name']].code is not None:
            session.registry.add_user(d)
    session.cells[:] = []
    for d in data['cells']:
        c = session.add_cell(d['text'], d.get('kind', 'math'))
        c.visible, c.color = d.get('visible', True), d.get('color')
    if not session.cells:
        session.add_cell()
    session.evaluate_all()
    return json.dumps(dict(view=data.get('view2d') or {}, lang=data.get('lang')))


def export_zip(name='kalam', lang='fr', view=None):
    """One zip with the notebook (.klm), Python, LaTeX notebook and tkz figure."""
    v = json.loads(view) if view else dict(xmin=-8, xmax=8, ymin=-6, ymax=6)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr(name + '.klm', klm_text(lang, view))
        z.writestr(name + '.py', to_python(session))
        z.writestr(name + '.tex', to_latex(session, lang))
        z.writestr(name + '_figure.tex', figure_tkz(session, v))
    return buf.getvalue()


def export_text(kind, lang='fr', view=None):
    v = json.loads(view) if view else dict(xmin=-8, xmax=8, ymin=-6, ymax=6)
    return {'py': lambda: to_python(session), 'tex': lambda: to_latex(session, lang),
            'fig': lambda: figure_tkz(session, v), 'klm': lambda: klm_text(lang, view)}[kind]()


# ---------------------------------------------------------------- commands
def catalog():
    cmds = [dict(name=c.name, fr=c.fr, ar=c.ar, category=c.category, hint=c.hint,
                 palette=c.palette, user=c.code is not None, code=c.code)
            for c in session.registry.commands.values()]
    return json.dumps(dict(categories=CATEGORIES, commands=cmds,
                           strings={k: list(v) for k, v in STRINGS.items()}))


def source(name):
    import inspect
    c = session.registry.commands[name]
    return c.code if c.code is not None else inspect.getsource(c.func)


def save_command(d_json):
    d = json.loads(d_json)
    reg = session.registry
    if not d['name'].isidentifier():
        raise ValueError('the name must be a single word (letters, digits, _)')
    old = reg.commands.get(d['name'])
    if old is not None and old.code is None:
        raise ValueError('"%s" is a built-in command' % d['name'])
    for a in (d.get('fr'), d.get('ar')):
        if a and reg.aliases().get(a) not in (None, d['name']):
            raise ValueError('"%s" is already used' % a)
    reg.add_user(d)
    session.evaluate_all()
    return catalog()


def delete_command(name):
    session.registry.remove(name)
    session.evaluate_all()
    return catalog()


def user_commands_json():
    return json.dumps([c.to_json() for c in session.registry.user_commands()], ensure_ascii=False)


def load_user_commands(text):
    for d in json.loads(text or '[]'):
        try:
            session.registry.add_user(d)
        except Exception:
            pass


def test_command(code, args):
    from .commands import compile_user
    f = compile_user(code)
    a = session.evaluate_expression('[%s]' % args) if args.strip() else []
    return str(f(*a))
