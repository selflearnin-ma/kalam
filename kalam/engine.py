"""Kalam engine: turns notebook cells into SymPy objects.

Input language (close to GeoGebra CAS / Desmos):
  A = (1, 2)            point (also A := Point(1, 2))
  f(x) = x^2 - 2x       function
  y = 2x + 1            equation -> drawn
  x^2 + y^2 < 4         inequality -> drawn region
  Solve(x^2 = 4, x)     command (English, French or Arabic name)
  a = Slider(-5, 5)     number with a slider
  $3                    output of cell 3
  f'(x), 2x, 3(x+1), π, √2, x², ∞, ≤ ...
  anything after # is a text note shown next to the result
"""
import io
import keyword
import re
import tokenize

import sympy as sp
from sympy.geometry.line import LinearEntity3D
from sympy.geometry.entity import GeometryEntity
from sympy.parsing.sympy_parser import parse_expr, standard_transformations

from . import runtime
from .commands import Registry

X, Y, Z = runtime.x, runtime.y, runtime.z
EQUATION_VARS = {'x', 'y', 'z'}

_MATH = ['sin', 'cos', 'tan', 'cot', 'sec', 'csc', 'asin', 'acos', 'atan', 'sinh', 'cosh',
         'tanh', 'exp', 'log', 'sqrt', 'root', 'Abs', 'floor', 'ceiling', 'factorial', 'binomial',
         're', 'im', 'arg', 'conjugate', 'Max', 'Min', 'sign', 'pi', 'oo', 'Eq', 'Ne', 'Lt',
         'Le', 'Gt', 'Ge', 'Lambda', 'Integer', 'Float', 'Rational', 'Symbol', 'Function']
GLOBALS_BASE = {n: getattr(sp, n) for n in _MATH}
GLOBALS_BASE.update(sp=sp, e_=sp.E, i_=sp.I)

_UNICODE = {'²': '^2', '³': '^3', '×': '*', '÷': '/', '·': '*', '−': '-', '≤': '<=', '≥': '>=',
            '≠': '!=', '∞': 'oo', '،': ',', '٫': '.', '٬': ''}
_DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹', '0123456789' * 2)
_RENAME = {'e': 'e_', 'i': 'i_', 'π': 'pi', 'ln': 'log', 'abs': 'Abs', 'racine': 'sqrt'}
_DEF = re.compile(r'^\s*([^\W\d]\w*)\s*(?:\(([^()]*)\))?\s*(:=|=)(?!=)\s*(.+)$', re.S)
_METHOD = re.compile(r'^\s*([^\W\d]\w*)\s*\.\s*([^\W\d]\w*)\s*\((.*)\)\s*$', re.S)
_NUM = r'-?\d+(?:\.\d+)?'
_FREE_POINT = re.compile(r'^\s*(\w*)\s*\(\s*(%s)\s*,\s*(%s)\s*\)\s*$' % (_NUM, _NUM))
_SLIDER = re.compile(r'^\s*(\w+)\s*\((.*)\)\s*$', re.S)


class KalamError(Exception):
    pass


# ---------------------------------------------------------------- normalizer
class _Group:
    def __init__(self, opener):
        self.opener, self.items, self.is_call = opener, [], False


def _tokens(text):
    try:
        toks = [t for t in tokenize.generate_tokens(io.StringIO(text).readline)
                if t.type not in (tokenize.NEWLINE, tokenize.NL, tokenize.ENDMARKER,
                                  tokenize.INDENT, tokenize.DEDENT, tokenize.COMMENT)]
    except (tokenize.TokenError, IndentationError, SyntaxError) as e:
        raise KalamError('syntax: %s' % e.args[0])
    root = _Group(None)
    stack = [root]
    pairs = {')': '(', ']': '[', '}': '{'}
    for t in toks:
        s = t.string
        if s in '([{' and t.type == tokenize.OP:
            g = _Group(s)
            stack[-1].items.append(g)
            stack.append(g)
        elif s in pairs and t.type == tokenize.OP:
            if len(stack) == 1 or stack[-1].opener != pairs[s]:
                raise KalamError('syntax: unbalanced "%s"' % s)
            stack.pop()
        else:
            stack[-1].items.append(t)
    if len(stack) != 1:
        raise KalamError('syntax: missing ")"')
    return root.items


class Normalizer:
    """Rewrites user text into plain SymPy-Python source (also used for export)."""

    def __init__(self, aliases, callables, defined):
        self.aliases, self.callables, self.defined = aliases, callables, defined

    def __call__(self, text):
        for k, v in _UNICODE.items():
            text = text.replace(k, v)
        text = text.translate(_DIGITS)
        text = re.sub(r'√\s*(\(|[^\W\d]\w*|\d+(?:\.\d+)?)',
                      lambda m: 'sqrt(' if m.group(1) == '(' else 'sqrt(%s)' % m.group(1), text)
        text = re.sub(r'\$(\d+)', r'_c\1', text)
        text = re.sub(r"([^\W\d]\w*)('+)\(", lambda m: 'Derivative(%s, %d)(' % (
            m.group(1), len(m.group(2))), text)
        return self._args(_tokens(text), top=True)

    # split by commas; an argument "a = b" becomes Eq(a, b)
    def _args(self, items, top=False):
        args, cur = [], []
        for it in items:
            if isinstance(it, tokenize.TokenInfo) and it.string == ',':
                args.append(cur)
                cur = []
            else:
                cur.append(it)
        args.append(cur)
        out = []
        for a in args:
            eqs = [i for i, it in enumerate(a) if isinstance(it, tokenize.TokenInfo) and it.string == '=']
            if len(eqs) == 1:
                k = eqs[0]
                out.append('Eq(%s, %s)' % (self._seq(a[:k]), self._seq(a[k + 1:])))
            elif eqs:
                raise KalamError('syntax: several "=" in one expression')
            else:
                out.append(self._seq(a))
        if top and len(out) > 1:
            return '(%s)' % ', '.join(out)
        return ', '.join(out)

    def _name(self, s):
        if s in self.defined:
            return s
        if s in _RENAME:
            return _RENAME[s]
        return self.aliases.get(s, s)

    def _is_callable(self, s):
        if s in self.callables:
            return True
        # unknown multi-letter names followed by "(" are undefined functions f(x);
        # unknown single letters are factors: a(x+1) = a*(x+1)
        return s not in self.defined and len(s) > 1 and s not in EQUATION_VARS

    def _seq(self, items):
        parts = []
        prev = None          # kind of previous unit: num, name, call, close, op
        prev_dot = False
        for idx, it in enumerate(items):
            if isinstance(it, _Group):
                if it.opener == '(' and prev in ('call', 'callclose'):
                    it.is_call = True
                    body = self._args(it.items)
                    parts.append('(%s)' % body)
                    prev = 'callclose'
                    continue
                if it.opener == '[' and prev in ('name', 'call', 'close', 'callclose'):
                    parts.append('[%s]' % self._args(it.items))
                    prev = 'close'
                    continue
                if prev in ('num', 'name', 'close'):
                    parts.append('*')
                o, c = it.opener, {'(': ')', '[': ']', '{': '}'}[it.opener]
                parts.append(o + self._args(it.items) + c)
                prev = 'close'
                continue
            s, typ = it.string, it.type
            if typ == tokenize.NUMBER:
                nxt = items[idx + 1] if idx + 1 < len(items) else None
                if prev in ('num', 'name', 'close', 'callclose'):
                    parts.append('*')
                if '.' in s or 'e' in s.lower():
                    parts.append("Rational('%s')" % s)
                elif isinstance(nxt, tokenize.TokenInfo) and nxt.string == '/':
                    parts.append('Integer(%s)' % s)
                else:
                    parts.append(s)
                prev = 'num'
            elif typ == tokenize.NAME and keyword.iskeyword(s):
                parts.append(' %s ' % s)
                prev = 'op'
            elif typ == tokenize.NAME:
                if prev_dot:
                    parts.append(s)
                    prev, prev_dot = 'name', False
                    continue
                if prev in ('num', 'name', 'close', 'callclose'):
                    parts.append('*')
                n = self._name(s)
                parts.append(n)
                nxt = items[idx + 1] if idx + 1 < len(items) else None
                is_call = isinstance(nxt, _Group) and nxt.opener == '(' and self._is_callable(n)
                prev = 'call' if is_call else 'name'
            elif s == '^':
                parts.append('**')
                prev = 'op'
            elif s == '!':
                parts[-1] = 'factorial(%s)' % parts[-1]
                prev = 'close'
            elif s == '.':
                parts.append('.')
                prev_dot, prev = True, 'op'
            elif s == '=':
                raise KalamError('syntax: unexpected "="')
            else:
                parts.append(' %s ' % s if s in ('<', '>', '<=', '>=', '==', '!=') else s)
                prev = 'op'
        return ''.join(parts).strip()


# ---------------------------------------------------------------- cells
class SliderSpec:
    def __init__(self, lo, hi, step=None, value=None):
        self.lo, self.hi = float(lo), float(hi)
        self.step = float(step) if step is not None else (self.hi - self.lo) / 100
        v = 1 if value is None and self.lo <= 1 <= self.hi else (self.lo if value is None else value)
        self.value = sp.nsimplify(v)


def string_line(text):
    """Inner text of a text line ("..." or « ... »), else None."""
    s = text.strip()
    if s.startswith('"'):
        s = s[1:-1] if len(s) > 1 and s.endswith('"') else s[1:]
        return s.replace('\\"', '"')
    if s.startswith('«'):
        return (s[1:-1] if s.endswith('»') else s[1:]).strip()
    return None


class Cell:
    """One line of the notebook. Lines with the same `block` form one cell on screen."""
    _next = 1

    def __init__(self, text='', kind='math', visible=True, color=None, block=None):
        self.id = Cell._next
        Cell._next += 1
        self.text, self.kind, self.visible, self.color = text, kind, visible, color
        self.style = None          # figure options set in its properties panel (size, axes, colours…)
        self.block = self.id if block is None else block
        self.reset()

    @property
    def is_text(self):
        return self.kind == 'text' or string_line(self.text) is not None

    def reset(self):
        self.name = self.value = self.error = self.slider = self.note = None
        self.latex = ''
        self.norm = None          # normalized source (export)
        self.params = None        # function parameters
        self.parts = []           # text cell: [(is_math, str)]
        self.labels = None        # figure: name of each object (None if unnamed)
        self.silent = False       # trailing ;
        self.version = getattr(self, 'version', 0) + 1

    @property
    def dim(self):
        """2 or 3 when the line draws something: only definitions (f(x) = ..., A = ..., C = x^2 + y^2 = 4).
        Results (f(x), f, Tangente(f, 3), an unnamed equation) are shown in the notebook, never drawn."""
        if self.kind != 'math' or self.value is None or self.name is None:
            return None
        return dimension(self.value)

    @property
    def shows_figure(self):
        """The line's output is a figure: Tracer(...), Courbe(...), Graphe3D(...) or the name of one."""
        return isinstance(self.value, runtime.Figure) and not self.name and not self.silent and not self.error

    @property
    def is_free_point(self):
        m = _DEF.match(self.text.partition('#')[0]) if self.kind == 'math' else None
        if not m or m.group(2) is not None:
            return False
        f = _FREE_POINT.match(m.group(4))
        return bool(f) and f.group(1) in ('', 'Point', 'نقطة')


class Session:
    def __init__(self, registry=None):
        self.registry = registry or Registry()
        self.cells = []
        self.env = {}
        self._snap = {}     # cell id -> env before that cell

    # ------------------------------------------------------------ helpers
    def normalizer(self, extra_defined=()):
        funcs = self.registry.functions()
        defined = set(self.env) | set(extra_defined)
        callables = set(funcs) | {k for k, v in GLOBALS_BASE.items() if callable(v)} | {
            k for k, v in self.env.items() if isinstance(v, sp.Lambda) or callable(v) and not isinstance(v, sp.Basic)}
        callables -= {k for k in defined if not callable(self.env.get(k))}
        return Normalizer(self.registry.aliases(), callables, defined)

    def _eval(self, src, local=None):
        g = dict(GLOBALS_BASE)
        g.update(self.registry.functions())
        loc = dict(self.env)
        loc.update(local or {})
        try:
            v = parse_expr(src, local_dict=loc, global_dict=g,
                           transformations=standard_transformations, evaluate=True)
        except KalamError:
            raise
        except SyntaxError as e:
            raise KalamError('syntax: %s' % (e.msg or e))
        if isinstance(v, tuple) and len(v) in (2, 3) and all(isinstance(c, sp.Expr) for c in v):
            v = runtime.Point(*v)
        if isinstance(v, tuple):
            v = list(v)
        return v

    def evaluate_expression(self, text):
        return self._eval(self.normalizer()(text))

    # ------------------------------------------------------------ evaluation
    def evaluate_from(self, index=0):
        if index < len(self.cells) and self.cells[index].id in self._snap:
            self.env = dict(self._snap[self.cells[index].id])
        else:
            index, self.env = 0, {}
        for c in self.cells[index:]:
            self._snap[c.id] = dict(self.env)
            self.evaluate_cell(c)

    def evaluate_all(self):
        self.evaluate_from(0)

    def evaluate_cell(self, c):
        c.reset()
        n = self.blocks().index(c.block) + 1        # $n = cell n as numbered on screen
        if c.is_text:
            # {{expr}} becomes LaTeX: as is inside $...$ ("$f(x)={{f(x)}}$"), wrapped in $...$ outside
            text = c.text if c.kind == 'text' else string_line(c.text)
            out = []
            for i, chunk in enumerate(re.split(r'\{\{(.*?)\}\}', text, flags=re.S)):
                if i % 2 == 0:
                    out.append(chunk)
                    continue
                in_math = ''.join(out).count('$') % 2 == 1
                try:
                    v = self.evaluate_expression(chunk)
                    tex = sp.latex(v.expr) if isinstance(v, sp.Lambda) else value_latex(v)
                except Exception as e:
                    tex = r'\text{[%s]}' % str(e).replace('$', '')
                out.append(tex if in_math else '$%s$' % tex)
            c.parts = [(False, ''.join(out))]      # one text with $...$ formulas, rendered by the UI
            return
        code, _, note = c.text.partition('#')
        c.note = note.strip() or None              # a comment: never shown, kept in the Python export
        code = code.strip()
        silent = c.silent = code.endswith(';')     # trailing ; computes without showing the result
        code = code.rstrip(';').strip()
        if not code:
            return
        try:
            self._evaluate_math(c, code)
            if isinstance(c.value, runtime.Figure):
                self._check_figure(c)
            if isinstance(c.value, runtime.VariationTableObj):     # f'(x) and f(x) rows use the function's name
                c.value.name = next((k for k, v in self.env.items() if v is c.value.f and not k.startswith('_c')), 'f')
            # a definition (f(x) = ..., A = ...) shows nothing; type `f`, `f(x)` or `A` to see a result
            if c.name is None and not silent:
                c.latex = display_latex(c.value)
                if isinstance(c.value, sp.Lambda) and code.isidentifier():
                    c.latex = function_latex(code, c.value)
        except Exception as e:  # any CAS failure is shown in the cell, never raised
            c.error = str(e) if isinstance(e, KalamError) else '%s: %s' % (type(e).__name__, e)
            c.value = None
        self.env['_c%d' % n] = c.value
        if c.name and c.value is not None:
            self.env[c.name] = c.value

    def _check_figure(self, c):
        items = c.value.items
        if not items:
            if c.name:                                 # G = Graphic(): empty until G.Draw(...)
                return
            raise KalamError('nothing to draw')
        dims = [dimension(i) for i in items]
        bad = [i for i, d in zip(items, dims) if d is None]
        if bad:
            raise KalamError('cannot be drawn: %s' % ', '.join(map(str, bad)))
        if len(set(dims)) > 1:
            raise KalamError('a figure is either 2D or 3D, not both')
        names = {id(v): k for k, v in self.env.items() if not k.startswith('_c')}
        c.labels = [names.get(id(i)) for i in items]

    def _evaluate_math(self, c, code):
        m = _METHOD.match(code)
        if m and isinstance(self.env.get(m.group(1)), runtime.Figure):   # G.Draw(f, A) means G = Draw(G, Draw(f, A))
            code = '%s = Draw(%s, %s(%s))' % (m.group(1), m.group(1), m.group(2), m.group(3))
        m = _DEF.match(code)
        if m and m.group(3) == '=' and m.group(1) in EQUATION_VARS and not m.group(2):
            m = None                                   # y = 2x+1 is an equation
        if m and m.group(3) == '=' and m.group(2) is not None and m.group(1) in EQUATION_VARS:
            m = None
        if m is None:
            c.norm = self.normalizer()(code)
            c.value = self._eval(c.norm)
            return
        name, params, rhs = m.group(1), m.group(2), m.group(4)
        if name in self.registry.aliases() or name in GLOBALS_BASE or name in _RENAME:
            raise KalamError('"%s" is a reserved name' % name)
        c.name = name
        if params is not None:
            ps = [p.strip() for p in params.split(',') if p.strip()]
            syms = {p: sp.Symbol(p) for p in ps}
            c.params = ps
            c.norm = self.normalizer(extra_defined=ps)(rhs)
            body = self._eval(c.norm, local=syms)
            c.value = sp.Lambda(tuple(syms[p] for p in ps) if len(ps) > 1 else syms[ps[0]], body)
            return
        c.norm = self.normalizer()(rhs)
        if c.norm.startswith('Slider('):
            g = dict(GLOBALS_BASE)
            spec = parse_expr('SliderSpec' + c.norm[len('Slider'):], local_dict=dict(self.env),
                              global_dict=dict(g, SliderSpec=SliderSpec),
                              transformations=standard_transformations)
            c.slider, c.value = spec, spec.value
            return
        c.value = self._eval(c.norm)

    # ------------------------------------------------------------ editing
    def index(self, c):
        return self.cells.index(c)

    def add_cell(self, text='', kind='math', at=None, block=None):
        c = Cell(text, kind, block=block)
        self.cells.insert(len(self.cells) if at is None else at, c)
        return c

    def load_cells(self, items):
        """Cells from a .klm list. Old files: no `block` (one line per cell) and kind "text" cells,
        which become "..." lines of a single cell."""
        self.cells[:] = []
        self._snap = {}
        ids = {}       # block in the file -> fresh id (ids saved in a file may collide with new cells' ids)
        for k, d in enumerate(items):
            key = d.get('block', ('old', k))
            if d.get('kind') == 'text':
                lines = ['"%s"' % ln.replace('"', '\\"') for ln in d['text'].split('\n') if ln.strip()] or ['']
            else:
                lines = [d['text']]
            for ln in lines:
                c = self.add_cell(ln, block=ids.get(key))
                ids.setdefault(key, c.block)
                c.visible, c.color, c.style = d.get('visible', True), d.get('color'), d.get('style')
        if not self.cells:
            self.add_cell()
        self.evaluate_all()

    def cells_json(self):
        return [dict(text=c.text, block=c.block, visible=c.visible, color=c.color, **({'style': c.style} if c.style else {}))
                for c in self.cells]

    # ------------------------------------------------------------ cells on screen (blocks of lines)
    def blocks(self):
        return list(dict.fromkeys(c.block for c in self.cells))

    def block_lines(self, b):
        return [c for c in self.cells if c.block == b]

    def set_block(self, b, text):
        """Replace the lines of cell b with `text` (one line per statement) and recompute."""
        old = self.block_lines(b)
        at = self.index(old[0]) if old else len(self.cells)
        keep = {}                                  # unchanged lines keep their colour and visibility
        for c in old:
            keep.setdefault(c.text, (c.visible, c.color, c.style))
            self.cells.remove(c)
            self._snap.pop(c.id, None)
        lines = [ln for ln in text.split('\n') if ln.strip()] or ['']
        for k, ln in enumerate(lines):
            c = self.add_cell(ln.rstrip(), at=at + k, block=b)
            c.visible, c.color, c.style = keep.get(c.text, (True, None, None))
        self.evaluate_from(at)

    def insert_block(self, pos, text=''):
        """New cell at screen position pos; returns its block id."""
        bs = self.blocks()
        at = self.index(self.block_lines(bs[pos])[0]) if pos < len(bs) else len(self.cells)
        c = self.add_cell('', at=at)
        self.set_block(c.block, text)
        return c.block

    def delete_block(self, b):
        at = self.index(self.block_lines(b)[0])
        for c in self.block_lines(b):
            self.cells.remove(c)
            self._snap.pop(c.id, None)
        if not self.cells:
            self.add_cell()
        self.evaluate_from(min(at, len(self.cells) - 1))

    def move_block(self, b, step):
        bs = self.blocks()
        j = bs.index(b) + step
        if 0 <= j < len(bs):
            bs[bs.index(b)], bs[j] = bs[j], b
            self.cells.sort(key=lambda c: bs.index(c.block))   # stable: lines keep their order
            self.evaluate_all()

    def remove_cell(self, c):
        i = self.index(c)
        self.cells.remove(c)
        self._snap.pop(c.id, None)
        self.evaluate_from(i)

    def set_text(self, c, text):
        c.text = text
        self.evaluate_from(self.index(c))

    def move_point(self, c, px, py):
        lhs = re.match(r'^(.*?(?::=|=))', c.text).group(1)
        c.text = '%s (%s, %s)' % (lhs, fmt(px), fmt(py))
        self.evaluate_from(self.index(c))

    def move_slider(self, c, value):
        s = c.slider
        code = c.text.partition('#')[0]
        lhs, rhs = re.match(r'^(.*?(?::=|=))\s*(.*)$', code, re.S).groups()
        word = _SLIDER.match(rhs).group(1)
        note = ' #' + c.text.partition('#')[2] if '#' in c.text else ''
        c.text = '%s %s(%s, %s, %s, %s)%s' % (lhs, word, fmt(s.lo), fmt(s.hi), fmt(s.step), fmt(value), note)
        self.evaluate_from(self.index(c))


def fmt(v, digits=2):
    v = float(v)
    if abs(v - round(v)) < 1e-9:
        return str(int(round(v)))
    return ('%.*f' % (digits, v)).rstrip('0').rstrip('.')


# ---------------------------------------------------------------- display
def _eq_latex(eq, l=sp.latex):
    return l(eq.lhs) + ' = ' + l(eq.rhs)


def line_equation(line):
    """Reduced equation y = mx + p (or x = c) of a 2D line."""
    eq = line.equation(X, Y)
    if eq.has(Y):
        return sp.Eq(Y, sp.expand(sp.radsimp(sp.simplify(sp.solve(eq, Y)[0]))))
    return sp.Eq(X, sp.solve(eq, X)[0])


def value_latex(v):
    L = sp.latex
    if isinstance(v, sp.Point):
        return r'\left(%s\right)' % ', '.join(L(a) for a in v.args)
    if isinstance(v, sp.Line2D):
        return _eq_latex(line_equation(v))
    if isinstance(v, sp.Plane):
        return L(v.equation(X, Y, Z)) + ' = 0'
    if isinstance(v, sp.Line3D):
        p, d = v.p1, v.direction_ratio
        return r'\left(%s\right) + t\left(%s\right)' % (', '.join(L(a) for a in p.args), ', '.join(L(a) for a in d))
    if isinstance(v, (sp.Segment2D, sp.Segment3D)):
        return r'\left[%s, %s\right],\ \ell = %s' % (value_latex(v.p1), value_latex(v.p2), L(sp.simplify(v.length)))
    if isinstance(v, (sp.Ray2D, sp.Ray3D)):
        return r'\left[%s, %s\right)' % (value_latex(v.p1), value_latex(v.p2))
    if isinstance(v, sp.Circle):
        a, b = v.center.args
        lhs = sp.Add((X - a)**2, (Y - b)**2, evaluate=False)
        return L(lhs) + ' = ' + L(v.radius**2)
    if isinstance(v, sp.Polygon):
        return r'\mathcal{P}\left(%s\right),\ \mathcal{A} = %s' % (
            ', '.join(value_latex(p) for p in v.vertices), L(abs(v.area)))
    if isinstance(v, sp.Equality):
        return _eq_latex(v)
    if isinstance(v, (list, tuple)):
        return r'\left\{%s\right\}' % ', '.join(value_latex(i) for i in v)
    if isinstance(v, dict):
        return r'\left\{%s\right\}' % ', '.join('%s: %s' % (value_latex(k), value_latex(i)) for k, i in v.items())
    return L(v)


def function_latex(name, f):
    """f : x ↦ x² − 4 (a bare function name typed alone)."""
    n = name if name.isascii() else r'\text{%s}' % name
    vs = ', '.join(sp.latex(s) for s in f.variables)
    vs = vs if len(f.variables) == 1 else r'\left(%s\right)' % vs
    return r'%s : %s \mapsto %s' % (n, vs, sp.latex(f.expr))


def display_latex(v):
    """LaTeX of a result: the value only, never a "name =" label (the input line shows the name)."""
    if v is None or isinstance(v, runtime.Figure):      # a figure is drawn, not written
        return ''
    if isinstance(v, sp.Lambda):
        return sp.latex(v.expr)
    body = value_latex(v)
    if isinstance(v, sp.Expr) and not v.free_symbols and v.is_number and not v.is_rational \
            and not v.has(sp.oo, -sp.oo, sp.zoo, sp.nan) and not isinstance(v, sp.Float):
        try:
            body += r' \approx ' + sp.latex(sp.N(v, 6))
        except Exception:
            pass
    return body


# ---------------------------------------------------------------- drawable kind
_3D = (sp.Point3D, LinearEntity3D, sp.Plane, runtime.Surface, runtime.SphereObj)


def dimension(v):
    """2, 3 or None (not drawable)."""
    if isinstance(v, (list, tuple)):
        dims = [dimension(i) for i in v]
        return next((d for d in dims if d), None)
    if isinstance(v, _3D):
        return 3
    if isinstance(v, (runtime.Curve, runtime.Vec)):
        return v.dim
    if isinstance(v, (GeometryEntity, runtime.Graph)):
        return 2
    if isinstance(v, sp.Lambda):
        if len(v.variables) == 1 and v.expr.free_symbols <= set(v.variables):
            return 2
        if len(v.variables) == 2 and v.expr.free_symbols <= set(v.variables):
            return 3
        return None
    if isinstance(v, sp.Rel):
        names = {s.name for s in v.free_symbols}
        if names and names <= {'x', 'y', 'z'}:
            return 3 if 'z' in names else 2
    return None
