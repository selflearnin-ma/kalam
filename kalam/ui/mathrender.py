"""LaTeX -> image (Matplotlib mathtext), embedded in Qt rich text as <img>."""
import hashlib
import html
import io
import os
import tempfile

import matplotlib
matplotlib.use('Agg')
from matplotlib import mathtext, rcParams  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402

rcParams['mathtext.fontset'] = 'cm'
_DIR = tempfile.mkdtemp(prefix='kalam-math-')
_cache = {}


def _clean(tex):
    # mathtext has no \text or \operatorname-less fallbacks for these
    return tex.replace(r'\text{', r'\mathrm{').replace(r'\limits', '').replace(r'\displaystyle', '')


def image(tex, size=13, color='#1f2430'):
    """(path, width, height) of the rendered formula, or None if mathtext can't draw it."""
    key = (tex, size, color)
    if key in _cache:
        return _cache[key]
    from PySide6.QtGui import QGuiApplication, QImage
    app = QGuiApplication.instance()
    scale = max(1, round(app.devicePixelRatio())) if app else 1
    stem = os.path.join(_DIR, hashlib.md5(repr(key).encode()).hexdigest())
    # Qt rich text picks name@2x.png on HiDPI screens when asked for name.png
    path = stem + '.png'
    file = stem + ('@%dx.png' % scale if scale > 1 else '.png')
    try:
        buf = io.BytesIO()
        mathtext.math_to_image('$%s$' % _clean(tex), buf, prop=FontProperties(size=size),
                               dpi=96 * scale, format='png', color=color)
        with open(file, 'wb') as f:
            f.write(buf.getvalue())
        img = QImage(file)
        res = (path, img.width() // scale, img.height() // scale)
    except Exception:
        res = None
    _cache[key] = res
    return res


def html_math(tex, size=13, color='#1f2430'):
    """<img> for a formula, with a monospace fallback."""
    r = image(tex, size, color)
    if r is None:
        return None
    return '<img src="%s" style="vertical-align: middle">' % r[0]


def html_text_with_math(parts, size=13):
    """Text cell: [(is_math, str)]; inside text, $...$ is math too."""
    out = []
    for is_math, s in parts:
        if is_math:
            out.append(html_math(s, size) or '<code>%s</code>' % html.escape(s))
            continue
        chunks = s.split('$')
        for i, ch in enumerate(chunks):
            if i % 2 and i < len(chunks) - 1:
                out.append(html_math(ch, size) or '<code>%s</code>' % html.escape(ch))
            else:
                out.append(html.escape(ch).replace('\n', '<br>'))
    return ''.join(out)
