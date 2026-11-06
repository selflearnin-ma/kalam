"""Core checks (no GUI). Run:  python -m pytest tests   or   python tests/test_core.py"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sympy as sp  # noqa: E402

from symnote.engine import Cell, Session, dimension  # noqa: E402
from symnote import runtime  # noqa: E402
from symnote.export import figure_tkz, load_syn, save_syn, to_latex, to_python  # noqa: E402

x, y = sp.symbols('x y')


def run(*lines):
    s = Session()
    for t in lines:
        s.add_cell(t)
    s.evaluate_all()
    for c in s.cells:
        assert c.error is None, (c.text, c.error)
    return s


def test_languages_and_parsing():
    s = run('A = (1, 2)', 'B := Point(5, 4)', 'I = Midpoint(A, B)', 'ع = Midpoint(A, B)',
            'f(x) = x^2 - 2x - 3', "f'(1)", 'Solve(f(x) = 0, x)', 'Solve(x^2 = 4, x)',
            '2(x+1) + 3x', 'e^(i π)', '√4 + 5!', '1/2 + 0.25', '$7')
    v = [c.value for c in s.cells]
    assert v[2] == sp.Point(3, 3) == v[3]
    assert v[5] == 0
    assert v[6] == sp.FiniteSet(-1, 3) and v[7] == sp.FiniteSet(-2, 2)
    assert v[8] == 5 * x + 2
    assert v[9] == -1 and v[10] == 122 and v[11] == sp.Rational(3, 4)
    assert v[12] == v[6]
    # a definition shows nothing; results only when asked for
    assert s.cells[0].latex == '' and s.cells[4].latex == ''
    s.add_cell('A')
    s.add_cell('f')
    s.add_cell('f(x)')
    s.evaluate_all()
    assert [c.latex for c in s.cells[-3:]] == [r'\left(1, 2\right)', r'f : x \mapsto x^{2} - 2 x - 3', 'x^{2} - 2 x - 3']
    assert [c.dim for c in s.cells[-3:]] == [None, None, None]     # a bare name shows, it does not draw again
    # {{expr}} inside $...$ joins that formula; outside it becomes its own formula
    s.add_cell('on pose $f(x)={{f(x)}}$ et {{f(1)}}', 'text')
    s.evaluate_all()
    assert s.cells[-1].parts == [(False, 'on pose $f(x)=x^{2} - 2 x - 3$ et $-4$')]


def test_old_names_are_updated():
    # notebooks of earlier versions used French / Arabic command names: they open in English
    s = Session()
    s.load_cells([dict(text='A = (1, 2)\nc = Cercle(A, 2)'.split('\n')[0]), dict(text='c = Cercle(A, 2)'),
                  dict(text='ع = منتصف(A, (3, 4))'), dict(text='G = Graphique()'), dict(text='G.Tracer(c, A)'),
                  dict(text='"Tracer(f) reste un texte"'), dict(text='Cercle(A, 1)')])
    assert [c.text for c in s.cells] == ['A = (1, 2)', 'c = Circle(A, 2)', 'ع = Midpoint(A, (3, 4))', 'G = Graphic()',
                                         'G.Draw(c, A)', '"Tracer(f) reste un texte"', 'Circle(A, 1)']
    assert all(c.error is None for c in s.cells)
    s.add_cell('Cercle(A, 1)')                 # typed now: French names are not commands any more
    s.evaluate_all()
    assert not isinstance(s.cells[-1].value, sp.Circle)


def test_example_exercise():
    # examples/exercice3_fr.syn: Domain, Factor, Solve, VariationTable, a graphic; no cell in error
    from symnote import web
    import json
    path = os.path.join(os.path.dirname(__file__), '..', 'examples', 'exercice3_fr.syn')
    web.load_syn_text(open(path, encoding='utf-8').read())
    lines = json.loads(web.state())['lines']
    assert not [ln['error'] for ln in lines if ln.get('error')]
    assert any('D_f = \\mathbb{R}' in (ln.get('parts') or [(0, '')])[0][1] for ln in lines)
    # a solution of Solve(...) used as a number: S[0] is the smallest (numbered from 0, like lists)
    s = run('f(x) = x^2 - 2x - 3', 'S = Solve(f(x) = 0, x)', 'S[0]', 'S[1]', 'f(S[1] + 1)', 'a = Solve(x^2 = 2, x)[1]')
    assert [c.value for c in s.cells[2:5]] == [-1, 3, 5] and s.env['a'] == sp.sqrt(2)
    # Hold(...): kept as typed, in that order
    s = run('Hold(2 * 3^2 - 4/6)', 'e1 = Hold(1/2 + 1/3)', 'e1', 'Simplify(e1)', '"{{Hold(3x - x)}} = {{3x - x}}"')
    assert s.cells[0].latex == r'2 \cdot 3^{2} - \frac{4}{6}' and s.cells[2].latex == r'\frac{1}{2} + \frac{1}{3}'
    assert s.cells[3].value == sp.Rational(5, 6) and s.cells[4].parts == [(False, '$3 x - x$ = $2 x$')]
    assert run('Domain(1/(x - 2))').cells[0].value == sp.Union(sp.Interval.open(-sp.oo, 2), sp.Interval.open(2, sp.oo))


def test_arithmetic_polynomials_trigonometry():
    s = run('PrimeFactors(360)', 'Quotient(17, 5)', 'Remainder(-17, 5)', 'Degree(x^3 - 2x)', 'Coefficients(2x^2 - 3x + 1)',
            'Roots((x - 1)^2 (x + 2))', 'Discriminant(x^2 + x + 1)', 'Divide(x^3 + 2x + 5, x^2 + 1)', 'TrigLinearize(cos(x)^2)',
            'SolveIn(sin(x) = 1/2, x, 0, 2pi)', 'Degrees(pi/3)', 'Radians(60)')
    v = [c.value for c in s.cells]
    assert s.cells[0].latex == r'2^{3} \cdot 3^{2} \cdot 5' and v[1:4] == [3, 3, 3] and v[4] == [2, -3, 1]
    assert v[5] == {1: 2, -2: 1} and v[6] == -3 and v[7] == [x, x + 5] and v[8] == sp.cos(2 * x) / 2 + sp.Rational(1, 2)
    assert v[9] == sp.FiniteSet(sp.pi / 6, 5 * sp.pi / 6) and v[10] == 60 and v[11] == sp.pi / 3


def test_transformations_in_space():
    s = run('A = (1, 2, 3)', 'B = (0, 0, 1)', 'S = Sphere(A, 2)', 'P = Plane((0,0,0), (1,0,0), (0,1,0))', 'k = Line((0,0,0), (0,0,1))',
            'Translate(A, Vector(1, 1, 1))', 'Dilate(S, 2, B)', 'Reflect(A, P)', 'Reflect(A, B)', 'Reflect(A, k)',
            'Rotate(A, pi/2, k)', 'Translate(P, Vector(0, 0, 2))', 'Rotate((1, 2), pi/2)', 'Draw(S, Reflect(S, P))')
    v = [c.value for c in s.cells[5:]]
    assert v[0] == sp.Point3D(2, 3, 4) and (v[1].center, v[1].r) == (sp.Point3D(2, 4, 5), 4)
    assert v[2:6] == [sp.Point3D(1, 2, -3), sp.Point3D(-1, -2, -1), sp.Point3D(-1, -2, 3), sp.Point3D(-2, 1, 3)]
    assert v[6].distance(sp.Point3D(0, 0, 2)) == 0 and v[6].normal_vector[2] != 0 and v[7] == sp.Point(-2, 1)
    assert s.cells[-1].shows_figure


def test_geometry_in_space_and_sets():
    s = run('O = (0, 0, 0)', 'A = (1, 0, 0)', 'B = (0, 2, 0)', 'C = (0, 0, 3)', 'S = Sphere(O, 2)',
            'Area(Polygon(A, B, C))', 'PerpendicularBisector(A, B)', 'Intersect(S, Plane((0,0,1), Vector(0,0,1)))',
            'Volume(Tetrahedron(O, A, B, C))', 'Volume(Cube(O, 2))', 'Volume(Cylinder(O, (0,0,3), 1))', 'Volume(Cone(O, (0,0,3), 1))',
            'Draw(Cube(O, 1), Circle(O, 2), Polygon(A, B, C))')
    v = [c.value for c in s.cells]
    assert v[5] == sp.Rational(7, 2) and isinstance(v[6], sp.Plane) and isinstance(v[7], runtime.Circle3D) and v[7].r == sp.sqrt(3)
    assert v[8:12] == [1, 8, 3 * sp.pi, sp.pi] and s.cells[-1].shows_figure and dimension(v[-1].items) == 3
    s = run('A = Interval(-1, 3)', 'B = IntervalOpen(2, oo)', 'A ∪ B', 'A ∩ B', 'A ∖ B', 'ℝ ∖ FiniteSet(0)', 'IsIn(3, A)', 'ℤ ∩ A', 'ℝ')
    assert [c.latex for c in s.cells[2:5]] == [r'\left[ -1\,;\,+\infty \right[', r'\left] 2\,;\,3 \right]', r'\left[ -1\,;\,2 \right]']
    assert s.cells[6].value is sp.true and s.cells[7].value == sp.Range(-1, 4) and s.cells[8].latex == r'\mathbb{R}'


def test_represent_sets():
    import json
    from symnote import web
    web.new()
    web.set_cell(0, 'Represent(x^2 + y^2 = 4)\nRepresent(x > 0, y > 0, x + y < 2)\nRepresent3D(x^2 + y^2 + z^2 - 2x = 3)\n'
                    'Represent3D(x + y + z = 1)\nRepresent3D(x^2 + y^2 = 1)\nDraw3D(Sphere((0,0,0), 1))\nRepresent(x + z > 0)')
    lines = json.loads(web.state())['lines']
    kinds = [[sc['k'] for it in ln['figure']['items'] for sc in it['scene']] if ln.get('figure') else ln.get('error') for ln in lines]
    assert kinds[:6] == [['imp'], ['imp'] * 3, ['sph'], ['plane'], ['psurf'], ['sph']] and 'Represent3D' in kinds[6]
    sph = lines[2]['figure']['items'][0]['scene'][0]
    assert sph['c'] == [1, 0, 0] and sph['r'] == 2                 # (x - 1)^2 + y^2 + z^2 = 4
    assert lines[1]['figure']['items'][0]['scene'][0]['mask'] and lines[1]['figure']['items'][0]['scene'][0]['shade']


def test_drawables():
    s = run('y = 2x + 1', 'x^2 + y^2 < 4', 'z = x y', 'S = Sphere((0,0,0), 1)', 'c = Circle((0,0), 2)', '3 + 4')
    assert [dimension(c.value) for c in s.cells] == [2, 2, 3, 3, 2, None]


def test_dynamic_points_and_sliders():
    s = run('A = (1, 2)', 'B = (3, 4)', 'm = Midpoint(A, B)', 'a = Slider(-5, 5, 0.5)', 'g(x) = a x')
    assert s.cells[0].is_free_point and not s.cells[2].is_free_point
    s.move_point(s.cells[0], 5, 6)
    assert s.cells[0].text == 'A = (5, 6)' and s.cells[2].value == sp.Point(4, 5)
    s.move_slider(s.cells[3], 2.5)
    assert s.cells[4].value(1) == sp.Rational(5, 2)


def test_user_command():
    s = Session()
    s.registry.add_user(dict(name='Double', fr='Double', ar='ضعف', category='algebra', hint='e',
                             code='def run(e):\n    return 2*e\n'))
    s.add_cell('Double(x + 1)')
    s.evaluate_all()
    assert s.cells[0].value == 2 * x + 2


def test_exports():
    s = run('A = (1, 2)', 'f(x) = x^2', 'k = Slider(0, 3)', 'T = Tangent(f, k)', 'Solve(f(x) = 4, x)',
            'c = Circle(A, 2)', 'Plot(sin(x), 0, pi)', 'u = ParametricCurve(cos(t), sin(t), t, 0, 2pi)',
            'Draw(A, c, T, u)', 'Plot(f)')
    with tempfile.TemporaryDirectory() as d:
        py = os.path.join(d, 'out.py')
        with open(py, 'w', encoding='utf-8') as f:
            f.write(to_python(s))
        r = subprocess.run([sys.executable, py], capture_output=True, text=True, encoding='utf-8',
                           env=dict(os.environ, PYTHONIOENCODING='utf-8'))   # Windows consoles are cp1252
        assert r.returncode == 0, r.stderr
        assert 'Line2D(Point2D(1, 1), Point2D(2, 3))' in r.stdout          # tangent at k = 1: y = 2x - 1
        syn = os.path.join(d, 'a.syn')
        save_syn(s, syn)
        s2, _, _ = load_syn(syn, s.registry)
        assert [c.latex for c in s2.cells] == [c.latex for c in s.cells]
    tex = to_latex(s)
    assert '\\begin{document}' in tex and '\\left\\{-2, 2\\right\\}' in tex   # Solve(f(x) = 4, x)
    assert tex.count('\\begin{tikzpicture}') == 3 and '\\usepackage{tkz-fct}' in tex   # Plot(sin), Draw(...), Plot(f)
    fig = figure_tkz(s)
    assert '\\tkzDefPoint(1,2){A}' in fig and '\\tkzFct' in fig and '\\tkzDrawCircle' in fig
    assert fig.count('\\begin{tikzpicture}') == 3


def test_figures():
    s = Session()
    for t in ('f(x) = x^2 - 2x - 3', 'A = (-2, 1)', 'c = Circle(A, 2)', 'Draw(A, c)', 'p = Plot(f);', 'p',
              'Plot(sin(x), 0, pi)', 'Plot3D(x y)', 'Draw(A, Sphere((0,0,0), 1))', 'Draw(3)'):
        s.add_cell(t)
    s.evaluate_all()
    shows = [c.shows_figure for c in s.cells]
    assert shows == [False, False, False, True, False, True, True, True, False, False]   # only drawing commands
    assert s.cells[3].labels == ['A', 'c'] and s.cells[3].latex == ''
    assert 'either 2D or 3D' in s.cells[8].error and 'geometric objects' in s.cells[9].error
    # several objects added to one graphic, shown where its name is typed
    s.add_cell('G = Graphic()')
    s.add_cell('G.Plot(f)')
    s.add_cell('G.Draw(A)')
    s.add_cell('G.Plot(sin(x));')
    s.add_cell('G.Draw(c)')
    s.add_cell('G')
    s.evaluate_all()
    g = s.cells[-6:]
    assert [c.error for c in g] == [None] * 6 and [c.shows_figure for c in g] == [False] * 5 + [True]
    assert len(g[-1].value.items) == 4 and g[-1].labels[:2] == ['f', 'A']
    s.move_point(s.cells[1], 0, 0)
    assert s.cells[-1].value.items[1] == sp.Point(0, 0)
    assert 'G = Draw(G, Draw(c))' in to_python(s)
    # a 3D graphic is built the same way; each graphic keeps its dimension
    s.add_cell('H = Graphic3D()')
    s.add_cell('H.Plot3D(x y)')
    s.add_cell('H.Draw(Sphere((0, 0, 0), 1))')
    s.add_cell('H.Represent3D(x^2 + y^2 + z = 0)')
    s.add_cell('H.Draw((2, -2, 3))')
    s.add_cell('H')
    s.add_cell('H.Plot(f)')
    s.add_cell('K = Graphic()')
    s.add_cell('K.Draw(Sphere((0, 0, 0), 1))')
    s.evaluate_all()
    h = s.cells[-9:]
    h = h[:3] + h[5:]
    assert [c.error for c in h[:4]] == [None] * 4 and h[3].shows_figure and len(h[3].value.items) == 4
    assert 'a 3D graphic draws 3D objects' in h[4].error and 'a 2D graphic draws 2D objects' in h[6].error
    from symnote.export import figure_window
    assert figure_window(s.cells[3].value.items + s.cells[5].value.items) == [-6, 6, -5, 11]    # A, c and the parabola (|y| <= 10)


def test_tables():
    s = run('g(x) = x^3 - 3x', 'SignTable(x^2 - x - 6)', 'VariationTable(g)', 'VariationTable(1/x)', 'SignTable(sqrt(x) - 1)')
    st, vt, inv, rt = (c.value for c in s.cells[1:])
    assert isinstance(st, runtime.TableObj) and isinstance(vt, runtime.TableObj)      # they are tables
    assert st.xs == [-sp.oo, -2, 3, sp.oo] and st.rows[-1][1:] == ['', '+', '0', '-', '0', '+', '']
    assert vt.name == 'g' and vt.rows[2][1::2] == [-sp.oo, 2, -2, sp.oo] and vt.rows[1][1:] == ['', '+', '0', '-', '0', '+', '']
    assert vt.rows[2][2::2] == ['↗', '↘', '↗'] and vt.rows[1][0] == "$g'(x)$"
    assert inv.rows[2][3] == (-sp.oo, sp.oo) and 'tkzTabVar{+/ $0$, -D+/ $-\\infty$ / $+\\infty$, -/ $0$}' in '\n'.join(inv.tkztab())
    assert rt.xs == [0, 1, sp.oo]
    tex = to_latex(s)
    assert '\\usepackage{tkz-tab}' in tex and tex.count('tkzTabInit') == 4 and 'tkz-fct' not in tex


def test_table_by_rows():
    import json
    from symnote import web
    web.new()
    web.set_cell(0, 'f(x) = x^2\nT = Table(3, 2)\nT.Row(x, 1, 2)\nT.Row("$f(x)$", f(1), "+")\nT.Row(1, 2, 3, 4)\nT\nV = Table(2)\nV.Row("-∞", 1)\nV')
    lines = json.loads(web.state())['lines']
    assert [('table' in ln) for ln in lines] == [False] * 5 + [True] + [False] * 2 + [True]
    assert 'columns' in lines[4]['error'] or 'not 4' in lines[4]['error']
    rows = lines[5]['table']['rows']
    assert [c['t'] for c in rows[1]] == ['f(x)', '1', '+'] and lines[8]['table']['rows'][0][0]['t'] == '-\\infty'
    web.set_style(5, json.dumps({'borders': 'outer', 'headrow': True, 'colw': 1.5}))
    tex = web.export_text('tex', 'fr')
    assert '\\rowcolor{gray!15}$x$ & $1$ & $2$' in tex and 'p{1.5cm}' in tex and '\\usepackage{array,colortbl}' in tex
    # sign/variation tables are tables: rows can be added, cells edited (an arrow moves the values)
    web.set_cell(0, 'V = VariationTable(x^2 - 4x)\nV.Row("signe", "", "-", "", "-", "")\nV')
    web.set_style(2, json.dumps({'cells': {'2,3': '$-4$ (min)', '2,2': '↗'}}))
    tex = web.export_text('tex', 'fr')
    assert '\\tkzTabVar{-/ $+\\infty$, +/ $-4\\text{ (min)}$, +/ $+\\infty$}' in tex and "\\tkzTabLine{, -, t, -, }" in tex
    web.set_style(2, json.dumps({'lines': 'solid', 'cells': {'2,4': '↘'}}))
    assert 't style/.style={style=solid}' in web.export_text('tex', 'fr')
    arrows = [c['ar'] for c in json.loads(web.state())['lines'][2]['table']['rows'][3] if 'ar' in c]
    assert arrows == ['-', '-']             # x^2-4x with its ↗ edited to ↘: two arrows down
    web.set_cell(0, 'SignTable((x - 1)/(x + 2))')
    web.set_style(0, json.dumps({'factors': False, 'dots': False}))
    assert len(json.loads(web.state())['lines'][0]['table']['rows']) == 2
    assert '\\tkzTabLine{, +, d, -, z, +, }' in web.export_text('tex', 'fr')


def test_cells_of_several_lines():
    s = Session()
    b = s.insert_block(0, 'f(x) = x^2 - 2x - 3\n"Étude de $f$ : on pose $f(x)={{f(x)}}$."\n# pour moi\nSolve(f(x) = 0, x)\nf(2);')
    lines = s.block_lines(b)
    assert [c.latex for c in lines] == ['', '', '', r'\left\{-1, 3\right\}', '']   # definition, text, comment, result, ;
    assert lines[1].is_text and lines[1].parts == [(False, 'Étude de $f$ : on pose $f(x)=x^{2} - 2 x - 3$.')]
    assert lines[0].dim == 2 and s.env['f'](2) == -3
    # only definitions are drawn: results and unnamed equations are only shown
    s.insert_block(1, 'f(x)\nTangent(f, 3)\ny = 2x + 1\nC = x^2 + y^2 = 4')
    assert [c.dim for c in s.block_lines(s.blocks()[1])] == [None, None, None, 2]
    s.delete_block(s.blocks()[1])
    s.insert_block(1, '$1')                       # $n = cell n on screen (its last line)
    assert s.block_lines(s.blocks()[1])[0].value == -3
    s.set_block(b, 'f(x) = x^2 - 4\nSolve(f(x) = 0, x)')    # editing a cell recomputes the cells after it
    assert s.block_lines(b)[1].value == sp.FiniteSet(-2, 2)
    s.move_block(s.blocks()[1], -1)
    assert s.block_lines(s.blocks()[0])[0].text == '$1'
    # old .syn: one line per cell, text cells become "..." lines
    s.load_cells([dict(kind='text', text='Bonjour "tous"\n\nsuite'), dict(kind='math', text='g(x) = 2x')])
    assert [c.text for c in s.cells] == ['"Bonjour \\"tous\\""', '"suite"', 'g(x) = 2x']
    assert s.cells[0].parts == [(False, 'Bonjour "tous"')] and len(s.blocks()) == 2
    # block ids in a file must not capture new cells (ids are renumbered on load)
    s.load_cells([dict(text='a = 1', block=Cell._next + 1), dict(text='b = 2', block=Cell._next + 2)])
    s.insert_block(2, 'c = 3')
    assert len(s.blocks()) == 3


def test_move_keeps_values():
    # a cell moves only where every variable keeps its definition (drag and drop, ↑ ↓)
    from symnote.engine import DependencyError
    s = Session()
    for t in ('a = 2', 'f(x) = a x^2', 'G = Graphic()', 'G.Plot(f)', 'G', '"{{f(1)}}"', 'a = 5\nb = a + 1'):
        s.insert_block(len(s.blocks()), t)
    for i, j, var in [(1, 0, 'a'), (3, 1, 'G'), (4, 2, 'G'), (5, 0, 'f')]:
        try:
            s.move_block_to(s.blocks()[i], j)
            assert False, (i, j)
        except DependencyError as e:
            assert e.args[0] == var
    assert [s.block_lines(b)[0].text for b in s.blocks()][:2] == ['a = 2', 'f(x) = a x^2']    # nothing moved
    s.move_block_to(s.blocks()[2], 0)                  # G = Graphic() uses nothing: anywhere before its uses
    s.move_block_to(s.blocks()[6], 5)
    assert [s.block_lines(b)[0].text for b in s.blocks()] == ['G = Graphic()', 'a = 2', 'f(x) = a x^2', 'G.Plot(f)', 'G', 'a = 5', '"{{f(1)}}"']
    assert all(c.error is None for c in s.cells)


def test_sequences():
    from symnote import web
    s = Session()
    ev = s.evaluate_expression
    assert ev('RecSequence(u/2 + 1, 0, 3)') == [0, 1, sp.Rational(3, 2), sp.Rational(7, 4)]
    assert ev('SeqLimit((2*n + 1)/(n + 3))') == 2
    assert ev('RecLimit(sqrt(u + 2), 0)') == 2
    assert ev('SeriesLimit(1/k^2, k, 1)') == sp.pi**2 / 6
    assert ev('SeqLimit(Sequence((2*n + 1)/(n + 3), n, 0, 5))') == 2
    assert ev('RecLimit(RecSequence(sqrt(u + 2), 0, 5))') == ev('SeqLimit(RecSequence(sqrt(u + 2), 0, 5))') == 2
    assert ev('SeriesLimit(Sequence(1/k^2, k, 1, 5))') == sp.pi**2 / 6
    assert ev('Sequence(k^2, k, 1, 3)') == [1, 4, 9]
    import json
    web.new()
    web.set_cell(0, 'g(x) = x/2 + 1\nv = RecSequence(g(u), 4, 5)\nPlotSeq(v)\nPlotSeq(Sequence(1/n, n, 1, 5))\nG = Graphic()\nG.PlotSeq(Sequence(n^2, n, 0, 3))\nG')
    lines = json.loads(web.state())['lines']
    kinds = [{p['k'] for it in ln['figure']['items'] for p in it['scene']} for ln in lines if 'figure' in ln]
    assert kinds == [{'fx', 'seg', 'pt'}, {'pt'}, {'pt'}], kinds


def test_web_bridge():
    import json
    import zipfile
    import io
    from symnote import web
    web.new()
    web.set_cell(0, 'f(x) = x^2\nA = (1, 2)\nD = x^2 + y^2 < 4\nG = Graphic()\nG.Plot(f)\nG.Draw(A)\nG.Represent(D)\nG\nPlot3D(x y)')
    lines = json.loads(web.state())['lines']
    assert [('figure' in ln) for ln in lines] == [False] * 7 + [True, True]     # only where a figure is shown
    fig = lines[7]['figure']
    assert fig['dim'] == 2 and [it['name'] for it in fig['items']] == ['f', 'A', 'D']
    assert fig['items'][0]['scene'] == [dict(k='fx', v='x', js='Math.pow(x, 2)', lo=None, hi=None)]
    assert fig['items'][1]['line'] == 1 and fig['items'][1]['scene'][0]['free']       # A can be dragged
    assert fig['items'][2]['scene'][0]['op'] == '<' and lines[8]['figure']['dim'] == 3
    web.move_point(1, 3, 4)
    assert json.loads(web.state())['lines'][1]['text'] == 'A = (3, 4)'
    web.insert_cell(1, '"texte"')
    assert json.loads(web.syn_text())['cells'][-1]['text'] == '"texte"'
    # figure options: kept in the file, when the line is edited unchanged, and used by the tkz export
    web.set_style(7, json.dumps({'grid': False, 'objs': {'f': {'color': '#ff0000', 'dash': True}, 'D': {'hide': True}}}))
    web.load_syn_text(web.syn_text())
    web.set_cell(0, 'f(x) = x^2\nA = (3, 5)\nD = x^2 + y^2 < 4\nG = Graphic()\nG.Plot(f)\nG.Draw(A)\nG.Represent(D)\nG\nPlot3D(x y)')
    assert json.loads(web.state())['lines'][7]['figure']['style']['objs']['f'] == {'color': '#ff0000', 'dash': True}
    fig = web.export_text('fig', 'fr')
    assert 'tkzGrid' not in fig and 'red,255;green,0;blue,0},dashed]' in fig
    names = zipfile.ZipFile(io.BytesIO(web.export_zip('k'))).namelist()
    assert sorted(names) == ['k.py', 'k.syn', 'k.tex', 'k_figures.tex']


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
