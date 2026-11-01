"""Core checks (no GUI). Run:  python -m pytest tests   or   python tests/test_core.py"""
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sympy as sp  # noqa: E402

from kalam.engine import Session, dimension  # noqa: E402
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
            'c = Cercle(A, 2)', 'Plot(sin(x), 0, pi)', 'u = ParametricCurve(cos(t), sin(t), t, 0, 2pi)')
    with tempfile.TemporaryDirectory() as d:
        py = os.path.join(d, 'out.py')
        with open(py, 'w') as f:
            f.write(to_python(s))
        r = subprocess.run([sys.executable, py], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert 'Eq(y, 2*x - 1)' in r.stdout          # tangent at k = 1
        klm = os.path.join(d, 'a.klm')
        save_klm(s, klm)
        s2, _, _ = load_klm(klm, s.registry)
        assert [c.latex for c in s2.cells] == [c.latex for c in s.cells]
    tex = to_latex(s)
    assert '\\begin{document}' in tex and 'x^{2}' in tex
    fig = figure_tkz(s, dict(xmin=-5, xmax=5, ymin=-5, ymax=5))
    assert '\\tkzDefPoint(1,2){A}' in fig and '\\tkzFct' in fig and '\\tkzDrawCircle' in fig


def test_web_bridge():
    import json
    import zipfile
    import io
    from kalam import web
    web.new()
    for t in ['f(x) = x^2', 'A = (1, 2)', 'x^2 + y^2 < 4', 'S = Sphere((0,0,0), 1)']:
        web.insert(len(web.session.cells), 'math', t)
    cells = json.loads(web.state())['cells']
    assert cells[1]['scene'] == [dict(k='fx', v='x', js='Math.pow(x, 2)', lo=None, hi=None)]
    assert cells[2]['scene'][0]['free'] and cells[3]['scene'][0]['op'] == '<'
    assert cells[4]['scene'][0]['k'] == 'sph'
    web.move_point(2, 3, 4)
    assert json.loads(web.state())['cells'][2]['text'] == 'A = (3, 4)'
    names = zipfile.ZipFile(io.BytesIO(web.export_zip('k'))).namelist()
    assert sorted(names) == ['k.klm', 'k.py', 'k.tex', 'k_figure.tex']


if __name__ == '__main__':
    for name, fn in list(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
