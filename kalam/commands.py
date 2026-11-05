"""Command registry: command name -> function. Commands have one (English) name in every interface language;
the French and Arabic names of earlier versions are kept only to update old notebooks when they are opened.
User commands live in ~/.kalam/user_commands.json and must define `run(*args)`.
"""
import json
import os
import re

from . import runtime

USER_FILE = os.path.join(os.path.expanduser('~'), '.kalam', 'user_commands.json')

CATEGORIES = ['calculus', 'arithmetic', 'sets', 'functions', 'polynomials', 'trigonometry', 'transform', 'geometry', 'figures',
              'matrix']

# name, former French and Arabic names (old files only), category, argument hint
BUILTINS = [
    # calculus
    ('Simplify', 'Simplifier', 'تبسيط', 'calculus', 'e'),
    ('Hold', None, None, 'calculus', '2 + 3*4'),
    ('Solve', 'Résoudre', 'حل', 'calculus', 'x^2 = 4, x'),
    ('CSolve', 'RésoudreC', 'حل_عقدي', 'calculus', 'x^2 = -4, x'),
    ('NSolve', 'RésoudreN', 'حل_عددي', 'calculus', 'e, x'),
    ('Substitute', 'Substituer', 'تعويض', 'calculus', 'e, x, 2'),
    ('Numeric', 'Valeur', 'قيمة_مقربة', 'calculus', 'e, 5'),
    ('Sum', 'Somme', 'مجموع', 'calculus', 'k^2, k, 1, n'),
    ('Sequence', 'Suite', 'متتالية', 'calculus', 'k^2, k, 1, 5'),
    ('Series', 'DL', 'نشر_محدود', 'calculus', 'f, 0, 4'),
    # arithmetic
    ('GCD', 'PGCD', 'قاسم_مشترك', 'arithmetic', 'a, b'),
    ('LCM', 'PPCM', 'مضاعف_مشترك', 'arithmetic', 'a, b'),
    ('Divisors', 'Diviseurs', 'قواسم', 'arithmetic', 'n'),
    ('IsPrime', 'EstPremier', 'أولي', 'arithmetic', 'n'),
    ('PrimeFactors', None, None, 'arithmetic', '360'),
    ('Quotient', None, None, 'arithmetic', '17, 5'),
    ('Remainder', None, None, 'arithmetic', '17, 5'),
    # sets
    ('Interval', None, None, 'sets', '-1, 3'),
    ('IntervalOpen', None, None, 'sets', '0, oo'),
    ('IntervalLOpen', None, None, 'sets', '0, 1'),
    ('IntervalROpen', None, None, 'sets', '0, 1'),
    ('FiniteSet', None, None, 'sets', '1, 2, 3'),
    ('Union', None, None, 'sets', 'A, B'),
    ('Intersection', None, None, 'sets', 'A, B'),
    ('Complement', None, None, 'sets', 'A, B'),
    ('IsIn', None, None, 'sets', '2, A'),
    ('IsSubset', None, None, 'sets', 'A, B'),
    ('Cardinal', None, None, 'sets', 'A'),
    ('Inf', None, None, 'sets', 'A'),
    ('Sup', None, None, 'sets', 'A'),
    ('Represent', None, None, 'sets', 'x^2 + y^2 <= 4, x + y - 1 > 0'),
    ('Represent3D', None, None, 'sets', 'x^2 + y^2 + z^2 = 4'),
    # functions
    ('Domain', None, None, 'functions', 'f'),
    ('Derivative', 'Dérivée', 'مشتقة', 'functions', 'f'),
    ('Integral', 'Intégrale', 'تكامل', 'functions', 'f, a, b'),
    ('Limit', 'Limite', 'نهاية', 'functions', 'f, oo'),
    ('Tangent', 'Tangente', 'مماس', 'functions', 'f, a'),
    ('Plot', 'Courbe', 'منحنى', 'functions', 'f, a, b'),
    ('Plot3D', 'Graphe3D', 'رسم_فضائي', 'functions', 'f'),
    ('SignTable', 'TableauSignes', 'جدول_الإشارة', 'functions', 'x^2 - 4'),
    ('VariationTable', 'TableauVariations', 'جدول_التغيرات', 'functions', 'f'),
    # polynomials
    ('Expand', 'Développer', 'نشر', 'polynomials', 'e'),
    ('Factor', 'Factoriser', 'تعميل', 'polynomials', 'e'),
    ('PartialFractions', 'ElémentsSimples', 'تفكيك', 'polynomials', 'e'),
    ('Degree', None, None, 'polynomials', 'x^3 - 2x'),
    ('Coefficients', None, None, 'polynomials', '2x^2 - 3x + 1'),
    ('Roots', None, None, 'polynomials', '(x - 1)^2 (x + 2)'),
    ('Discriminant', None, None, 'polynomials', 'x^2 + x + 1'),
    ('Divide', None, None, 'polynomials', 'x^3 - 1, x - 1'),
    # trigonometry
    ('TrigSimplify', None, None, 'trigonometry', 'sin(x)^2 + cos(x)^2'),
    ('TrigExpand', None, None, 'trigonometry', 'cos(2x)'),
    ('TrigLinearize', None, None, 'trigonometry', 'cos(x)^2'),
    ('SolveIn', None, None, 'trigonometry', 'sin(x) = 1/2, x, 0, 2pi'),
    ('Degrees', None, None, 'trigonometry', 'pi/3'),
    ('Radians', None, None, 'trigonometry', '60'),
    # transform
    ('Reflect', 'Symétrie', 'تماثل', 'transform', 'o, d'),
    ('Rotate', 'Rotation', 'دوران', 'transform', 'o, pi/2, O'),
    ('Translate', 'Translation', 'إزاحة', 'transform', 'o, u'),
    ('Dilate', 'Homothétie', 'تحاك', 'transform', 'o, k, O'),
    # geometry
    ('Point', 'Point', 'نقطة', 'geometry', 'x, y'),
    ('Segment', 'Segment', 'قطعة', 'geometry', 'A, B'),
    ('Line', 'Droite', 'مستقيم', 'geometry', 'A, B'),
    ('Ray', 'DemiDroite', 'نصف_مستقيم', 'geometry', 'A, B'),
    ('Circle', 'Cercle', 'دائرة', 'geometry', 'O, r'),
    ('Polygon', 'Polygone', 'مضلع', 'geometry', 'A, B, C'),
    ('Midpoint', 'Milieu', 'منتصف', 'geometry', 'A, B'),
    ('Intersect', 'Intersection', 'تقاطع', 'geometry', 'a, b'),
    ('Perpendicular', 'Perpendiculaire', 'عمودي', 'geometry', 'A, d'),
    ('Parallel', 'Parallèle', 'مواز', 'geometry', 'A, d'),
    ('PerpendicularBisector', 'Médiatrice', 'واسط', 'geometry', 'A, B'),
    ('AngleBisector', 'Bissectrice', 'منصف', 'geometry', 'A, B, C'),
    ('Distance', 'Distance', 'مسافة', 'geometry', 'A, B'),
    ('Length', 'Longueur', 'طول', 'geometry', 's'),
    ('Area', 'Aire', 'مساحة', 'geometry', 'P'),
    ('Vector', 'Vecteur', 'متجهة', 'geometry', 'A, B'),
    # geometry in space
    ('Sphere', 'Sphère', 'فلكة', 'geometry', 'O, r'),
    ('Plane', 'Plan', 'مستوى', 'geometry', 'A, B, C'),
    ('Tetrahedron', None, None, 'geometry', 'A, B, C, D'),
    ('Pyramid', None, None, 'geometry', 'S, A, B, C, D'),
    ('Prism', None, None, 'geometry', 'A, B, C, Vector(0, 0, 2)'),
    ('Cube', None, None, 'geometry', '(0, 0, 0), 2'),
    ('Cuboid', None, None, 'geometry', '(0, 0, 0), 3, 2, 1'),
    ('Cylinder', None, None, 'geometry', '(0, 0, 0), (0, 0, 3), 1'),
    ('Cone', None, None, 'geometry', '(0, 0, 0), (0, 0, 3), 1'),
    ('Volume', None, None, 'geometry', 'o'),
    # figures
    ('Graphic', 'Graphique', 'رسم', 'figures', ''),
    ('Draw', 'Tracer', 'ارسم', 'figures', 'f, A, c'),
    ('Draw3D', None, None, 'figures', 'S, P'),
    ('ParametricCurve', 'CourbeParamétrée', 'منحنى_وسيطي', 'figures', 'cos(t), sin(t), t, 0, 2pi'),
    ('Slider', 'Curseur', 'منزلق', 'figures', '-5, 5, 0.1'),
    ('Graphic3D', None, None, 'figures', ''),
    ('ParametricSurface', 'SurfaceParamétrée', 'سطح_وسيطي', 'figures',
     'cos(u)cos(v), sin(u)cos(v), sin(v), u, 0, 2pi, v, -pi/2, pi/2'),
    ('Table', 'Tableau', 'جدول', 'figures', '3, 2'),
    ('Row', 'Ligne', 'سطر', 'figures', 'T, a, b, c'),
    # matrix
    ('Matrix', 'Matrice', 'مصفوفة', 'matrix', '[[1, 2], [3, 4]]'),
    ('Det', 'Déterminant', 'محددة', 'matrix', 'M'),
    ('Inverse', 'Inverse', 'مقلوب', 'matrix', 'M'),
    ('Transpose', 'Transposée', 'منقول', 'matrix', 'M'),
    ('Eigenvalues', 'ValeursPropres', 'قيم_ذاتية', 'matrix', 'M'),
]
class Command:
    def __init__(self, name, fr, ar, category, hint, func, code=None, palette=True):
        self.name, self.fr, self.ar = name, fr or name, ar or name
        self.category, self.hint, self.func = category, hint, func
        self.code = code            # source for user commands, None for built-ins
        self.palette = palette

    def label(self, lang):
        return {'fr': self.fr, 'ar': self.ar}.get(lang, self.name)

    def to_json(self):
        return dict(name=self.name, fr=self.fr, ar=self.ar, category=self.category,
                    hint=self.hint, code=self.code, palette=self.palette)


def compile_user(code):
    """Run user code with the runtime in scope; it must define run(*args)."""
    ns = dict(vars(runtime))
    exec(compile(code, '<user command>', 'exec'), ns)
    if not callable(ns.get('run')):
        raise ValueError('the code must define a function run(*args)')
    return ns['run']


class Registry:
    def __init__(self, load_user=True):
        self.commands = {}
        for name, fr, ar, cat, hint in BUILTINS:
            func = getattr(runtime, name)
            self.commands[name] = Command(name, fr, ar, cat, hint, func)
        if load_user and os.path.exists(USER_FILE):
            with open(USER_FILE, encoding='utf-8') as f:
                for d in json.load(f):
                    try:
                        self.add_user(d)
                    except Exception as e:  # a broken user command must not stop the app
                        print('Kalam: user command %s ignored: %s' % (d.get('name'), e))

    def add_user(self, d):
        cat = d.get('category')       # groups of earlier versions: figures, or calculus
        cat = cat if cat in CATEGORIES else 'figures' if cat in ('graph2d', 'graph3d', 'tables') else 'calculus'
        cmd = Command(d['name'], d.get('fr'), d.get('ar'), cat,
                      d.get('hint', ''), compile_user(d['code']), d['code'], d.get('palette', True))
        self.commands[cmd.name] = cmd
        return cmd

    def remove(self, name):
        if self.commands[name].code is not None:
            del self.commands[name]

    def user_commands(self):
        return [c for c in self.commands.values() if c.code is not None]

    def save_user(self):
        os.makedirs(os.path.dirname(USER_FILE), exist_ok=True)
        with open(USER_FILE, 'w', encoding='utf-8') as f:
            json.dump([c.to_json() for c in self.user_commands()], f, ensure_ascii=False, indent=1)

    def aliases(self):
        """name -> name: the names the input language knows."""
        return {c.name: c.name for c in self.commands.values()}

    def legacy(self):
        """Former French / Arabic command names -> name (for notebooks written with them)."""
        return {a: c.name for c in self.commands.values() for a in (c.fr, c.ar) if a and a != c.name}


    def functions(self):
        return {c.name: c.func for c in self.commands.values()}


def migrate(text, legacy):
    """A line written with former French/Arabic command names, in English: Tracer(f) -> Draw(f), G.Tracer( -> G.Draw(.
    Text between quotes is left as it is."""
    if not legacy:
        return text
    pat = re.compile(r'(?<![\w])(%s)(?=\s*\()' % '|'.join(sorted(map(re.escape, legacy), key=len, reverse=True)))
    parts = re.split(r'("(?:[^"\\]|\\.)*")', text)
    return ''.join(p if k % 2 else pat.sub(lambda m: legacy[m.group(1)], p) for k, p in enumerate(parts))
