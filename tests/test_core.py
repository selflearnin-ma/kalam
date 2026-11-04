"""Core checks (no GUI). Run:  python -m pytest tests   or   python tests/test_core.py"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sympy as sp  # noqa: E402

from kalam.engine import Cell, Session, dimension  # noqa: E402
from kalam import runtime  # noqa: E402
from kalam.export import figure_tkz, load_klm, save_klm, to_latex, to_python  # noqa: E402

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
    s = run('A = (1, 2)', 'B := Point(5, 4)', 'I = Milieu(A, B)', 'ع = منتصف(A, B)',
            'f(x) = x^2 - 2x - 3', "f'(1)", 'Résoudre(f(x) = 0, x)', 'حل(x^2 = 4, x)',
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
    s.add_cell('ضعف(x + 1)')
    s.evaluate_all()
    assert s.cells[0].value == 2 * x + 2


def test_exports():
    s = run('A = (1, 2)', 'f(x) = x^2', 'k = Slider(0, 3)', 'T = Tangente(f, k)', 'Solve(f(x) = 4, x)',
            'c = Cercle(A, 2)', 'Plot(sin(x), 0, pi)', 'u = ParametricCurve(cos(t), sin(t), t, 0, 2pi)',
            'Tracer(f, A, c, T, u)')
    with tempfile.TemporaryDirectory() as d:
        py = os.path.join(d, 'out.py')
        with open(py, 'w', encoding='utf-8') as f:
            f.write(to_python(s))
        r = subprocess.run([sys.executable, py], capture_output=True, text=True, encoding='utf-8',
                           env=dict(os.environ, PYTHONIOENCODING='utf-8'))   # Windows consoles are cp1252
        assert r.returncode == 0, r.stderr
        assert 'Eq(y, 2*x - 1)' in r.stdout          # tangent at k = 1
        klm = os.path.join(d, 'a.klm')
        save_klm(s, klm)
        s2, _, _ = load_klm(klm, s.registry)
        assert [c.latex for c in s2.cells] == [c.latex for c in s.cells]
    tex = to_latex(s)
    assert '\\begin{document}' in tex and '\\left\\{-2, 2\\right\\}' in tex   # Solve(f(x) = 4, x)
    assert tex.count('\\begin{tikzpicture}') == 2 and '\\usepackage{tkz-fct}' in tex   # Plot(...) and Tracer(...)
    fig = figure_tkz(s)
    assert '\\tkzDefPoint(1,2){A}' in fig and '\\tkzFct' in fig and '\\tkzDrawCircle' in fig
    assert fig.count('\\begin{tikzpicture}') == 2


def test_figures():
    s = Session()
    for t in ('f(x) = x^2 - 2x - 3', 'A = (-2, 1)', 'c = Cercle(A, 2)', 'Tracer(f, A, c)', 'p = Tracer(f);', 'p',
              'Courbe(sin(x), 0, pi)', 'Graphe3D(x y)', 'Tracer(A, Sphere((0,0,0), 1))', 'Tracer(3)'):
        s.add_cell(t)
    s.evaluate_all()
    shows = [c.shows_figure for c in s.cells]
    assert shows == [False, False, False, True, False, True, True, True, False, False]   # only drawing commands
    assert s.cells[3].labels == ['f', 'A', 'c'] and s.cells[3].latex == ''
    assert 'either 2D or 3D' in s.cells[8].error and 'cannot be drawn' in s.cells[9].error
    # several objects added to one graphic, shown where its name is typed
    s.add_cell('G = Graphique()')
    s.add_cell('G.Tracer(f, A)')
    s.add_cell('G.Courbe(sin(x));')
    s.add_cell('G.Draw(c)')
    s.add_cell('G')
    s.evaluate_all()
    g = s.cells[-5:]
    assert [c.error for c in g] == [None] * 5 and [c.shows_figure for c in g] == [False] * 4 + [True]
    assert len(g[-1].value.items) == 4 and g[-1].labels[:2] == ['f', 'A']
    s.move_point(s.cells[1], 0, 0)
    assert s.cells[-1].value.items[1] == sp.Point(0, 0)
    assert 'G = Draw(G, Draw(c))' in to_python(s)
    from kalam.export import figure_window
    assert figure_window(s.cells[3].value.items) == [-6, 6, -5, 11]    # A, c and the parabola (|y| <= 10) on [-6, 6]


def test_tables():
    s = run('g(x) = x^3 - 3x', 'TableauSignes(x^2 - x - 6)', 'TableauVariations(g)', 'جدول_التغيرات(1/x)', 'TableauSignes(sqrt(x) - 1)')
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
    from kalam import web
    web.new()
    web.set_cell(0, 'f(x) = x^2\nT = Tableau(3, 2)\nT.Ligne(x, 1, 2)\nT.Ligne("$f(x)$", f(1), "+")\nT.Ligne(1, 2, 3, 4)\nT\nV = جدول(2)\nV.سطر("-∞", 1)\nV')
    lines = json.loads(web.state())['lines']
    assert [('table' in ln) for ln in lines] == [False] * 5 + [True] + [False] * 2 + [True]
    assert 'columns' in lines[4]['error'] or 'not 4' in lines[4]['error']
    rows = lines[5]['table']['rows']
    assert [c['t'] for c in rows[1]] == ['f(x)', '1', '+'] and lines[8]['table']['rows'][0][0]['t'] == '-\\infty'
    web.set_style(5, json.dumps({'borders': 'outer', 'headrow': True, 'colw': 1.5}))
    tex = web.export_text('tex', 'fr')
    assert '\\rowcolor{gray!15}$x$ & $1$ & $2$' in tex and 'p{1.5cm}' in tex and '\\usepackage{array,colortbl}' in tex
    # sign/variation tables are tables: rows can be added, cells edited (an arrow moves the values)
    web.set_cell(0, 'V = TableauVariations(x^2 - 4x)\nV.Ligne("signe", "", "-", "", "-", "")\nV')
    web.set_style(2, json.dumps({'cells': {'2,3': '$-4$ (min)', '2,2': '↗'}}))
    tex = web.export_text('tex', 'fr')
    assert '\\tkzTabVar{-/ $+\\infty$, +/ $-4\\text{ (min)}$, +/ $+\\infty$}' in tex and "\\tkzTabLine{, -, t, -, }" in tex
    web.set_cell(0, 'TableauSignes((x - 1)/(x + 2))')
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
    # old .klm: one line per cell, text cells become "..." lines
    s.load_cells([dict(kind='text', text='Bonjour "tous"\n\nsuite'), dict(kind='math', text='g(x) = 2x')])
    assert [c.text for c in s.cells] == ['"Bonjour \\"tous\\""', '"suite"', 'g(x) = 2x']
    assert s.cells[0].parts == [(False, 'Bonjour "tous"')] and len(s.blocks()) == 2
    # block ids in a file must not capture new cells (ids are renumbered on load)
    s.load_cells([dict(text='a = 1', block=Cell._next + 1), dict(text='b = 2', block=Cell._next + 2)])
    s.insert_block(2, 'c = 3')
    assert len(s.blocks()) == 3


def test_web_bridge():
    import json
    import zipfile
    import io
    from kalam import web
    web.new()
    web.set_cell(0, 'f(x) = x^2\nA = (1, 2)\nD = x^2 + y^2 < 4\nTracer(f, A, D)\nGraphe3D(x y)')
    lines = json.loads(web.state())['lines']
    assert [('figure' in ln) for ln in lines] == [False, False, False, True, True]     # only drawing commands
    fig = lines[3]['figure']
    assert fig['dim'] == 2 and [it['name'] for it in fig['items']] == ['f', 'A', 'D']
    assert fig['items'][0]['scene'] == [dict(k='fx', v='x', js='Math.pow(x, 2)', lo=None, hi=None)]
    assert fig['items'][1]['line'] == 1 and fig['items'][1]['scene'][0]['free']       # A can be dragged
    assert fig['items'][2]['scene'][0]['op'] == '<' and lines[4]['figure']['dim'] == 3
    web.move_point(1, 3, 4)
    assert json.loads(web.state())['lines'][1]['text'] == 'A = (3, 4)'
    web.insert_cell(1, '"texte"')
    assert json.loads(web.klm_text())['cells'][-1]['text'] == '"texte"'
    # figure options: kept in the file, when the line is edited unchanged, and used by the tkz export
    web.set_style(3, json.dumps({'grid': False, 'objs': {'f': {'color': '#ff0000', 'dash': True}, 'D': {'hide': True}}}))
    web.load_klm_text(web.klm_text())
    web.set_cell(0, 'f(x) = x^2\nA = (3, 5)\nD = x^2 + y^2 < 4\nTracer(f, A, D)\nGraphe3D(x y)')
    assert json.loads(web.state())['lines'][3]['figure']['style']['objs']['f'] == {'color': '#ff0000', 'dash': True}
    fig = web.export_text('fig', 'fr')
    assert 'tkzGrid' not in fig and 'red,255;green,0;blue,0},dashed]' in fig
    names = zipfile.ZipFile(io.BytesIO(web.export_zip('k'))).namelist()
    assert sorted(names) == ['k.klm', 'k.py', 'k.tex', 'k_figures.tex']


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
