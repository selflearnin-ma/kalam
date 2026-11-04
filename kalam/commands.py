"""Command registry: command name -> function. Commands have one (English) name in every interface language;
the French and Arabic names of earlier versions are kept only to update old notebooks when they are opened.
User commands live in ~/.kalam/user_commands.json and must define `run(*args)`.
"""
import json
import os
import re

from . import runtime

USER_FILE = os.path.join(os.path.expanduser('~'), '.kalam', 'user_commands.json')

CATEGORIES = ['geometry', 'transform', 'algebra', 'calculus', 'tables', 'matrix', 'graph2d', 'graph3d']

# name, former French and Arabic names (old files only), category, argument hint
BUILTINS = [
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
    ('Tangent', 'Tangente', 'مماس', 'geometry', 'f, a'),
    ('Vector', 'Vecteur', 'متجهة', 'geometry', 'A, B'),
    ('Reflect', 'Symétrie', 'تماثل', 'transform', 'o, d'),
    ('Rotate', 'Rotation', 'دوران', 'transform', 'o, pi/2, O'),
    ('Translate', 'Translation', 'إزاحة', 'transform', 'o, u'),
    ('Dilate', 'Homothétie', 'تحاك', 'transform', 'o, k, O'),
    ('Simplify', 'Simplifier', 'تبسيط', 'algebra', 'e'),
    ('Expand', 'Développer', 'نشر', 'algebra', 'e'),
    ('Factor', 'Factoriser', 'تعميل', 'algebra', 'e'),
    ('Solve', 'Résoudre', 'حل', 'algebra', 'x^2 = 4, x'),
    ('CSolve', 'RésoudreC', 'حل_عقدي', 'algebra', 'x^2 = -4, x'),
    ('NSolve', 'RésoudreN', 'حل_عددي', 'algebra', 'e, x'),
    ('Substitute', 'Substituer', 'تعويض', 'algebra', 'e, x, 2'),
    ('Numeric', 'Valeur', 'قيمة_مقربة', 'algebra', 'e, 5'),
    ('PartialFractions', 'ElémentsSimples', 'تفكيك', 'algebra', 'e'),
    ('GCD', 'PGCD', 'قاسم_مشترك', 'algebra', 'a, b'),
    ('LCM', 'PPCM', 'مضاعف_مشترك', 'algebra', 'a, b'),
    ('Divisors', 'Diviseurs', 'قواسم', 'algebra', 'n'),
    ('IsPrime', 'EstPremier', 'أولي', 'algebra', 'n'),
    ('Derivative', 'Dérivée', 'مشتقة', 'calculus', 'f'),
    ('Integral', 'Intégrale', 'تكامل', 'calculus', 'f, a, b'),
    ('Limit', 'Limite', 'نهاية', 'calculus', 'f, oo'),
    ('Series', 'DL', 'نشر_محدود', 'calculus', 'f, 0, 4'),
    ('Sum', 'Somme', 'مجموع', 'calculus', 'k^2, k, 1, n'),
    ('Sequence', 'Suite', 'متتالية', 'calculus', 'k^2, k, 1, 5'),
    ('Matrix', 'Matrice', 'مصفوفة', 'matrix', '[[1, 2], [3, 4]]'),
    ('Det', 'Déterminant', 'محددة', 'matrix', 'M'),
    ('Inverse', 'Inverse', 'مقلوب', 'matrix', 'M'),
    ('Transpose', 'Transposée', 'منقول', 'matrix', 'M'),
    ('Eigenvalues', 'ValeursPropres', 'قيم_ذاتية', 'matrix', 'M'),
    ('Table', 'Tableau', 'جدول', 'tables', '3, 2'),
    ('Row', 'Ligne', 'سطر', 'tables', 'T, a, b, c'),
    ('SignTable', 'TableauSignes', 'جدول_الإشارة', 'tables', 'x^2 - 4'),
    ('VariationTable', 'TableauVariations', 'جدول_التغيرات', 'tables', 'f'),
    ('Graphic', 'Graphique', 'رسم', 'graph2d', ''),
    ('Graphic3D', None, None, 'graph3d', ''),
    ('Draw', 'Tracer', 'ارسم', 'graph2d', 'f, A, c'),
    ('Plot', 'Courbe', 'منحنى', 'graph2d', 'f, a, b'),
    ('ParametricCurve', 'CourbeParamétrée', 'منحنى_وسيطي', 'graph2d', 'cos(t), sin(t), t, 0, 2pi'),
    ('Slider', 'Curseur', 'منزلق', 'graph2d', '-5, 5, 0.1'),
    ('Plot3D', 'Graphe3D', 'رسم_فضائي', 'graph3d', 'x^2 - y^2'),
    ('ParametricSurface', 'SurfaceParamétrée', 'سطح_وسيطي', 'graph3d',
     'cos(u)cos(v), sin(u)cos(v), sin(v), u, 0, 2pi, v, -pi/2, pi/2'),
    ('Sphere', 'Sphère', 'فلكة', 'graph3d', 'O, r'),
    ('Plane', 'Plan', 'مستوى', 'graph3d', 'A, B, C'),
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
        cmd = Command(d['name'], d.get('fr'), d.get('ar'), d.get('category', 'algebra'),
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
