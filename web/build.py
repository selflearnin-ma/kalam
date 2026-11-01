"""Build the web core into web/dist/.

  python web/build.py             web version (MathJax and Plotly from the jsDelivr CDN)
  python web/build.py --offline   also copies MathJax and Plotly into dist/vendor (Tauri apps, no network)

Pyodide, the SymPy/mpmath wheels and the JS libraries are downloaded once into web/.deps
(needs npm and pip). Pinned versions: PYODIDE, WHEELS, VENDOR below.

dist/app.html   page content for a claude.ai artifact (the platform adds <html><head>)
dist/index.html the same page as a standalone, installable web app (any static host, offline after first visit)
dist/py/        Pyodide, wheels and kalam-core.zip, fetched at runtime
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(ROOT, 'web')
DIST = os.path.join(WEB, 'dist')
DEPS = os.path.join(WEB, '.deps')
NPM = {'pyodide': 'pyodide@0.27.7', 'mathjax': 'mathjax@3.2.2', 'plotly': 'plotly.js-dist-min@2.35.2'}
# offline copies of the CDN scripts used by app.html: (CDN url, file in the npm package)
VENDOR = {'mathjax': ('https://cdn.jsdelivr.net/npm/mathjax@3.2.2/es5/tex-svg.js', 'es5/tex-svg.js'),
          'plotly': ('https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js', 'plotly.min.js')}
CORE = ['__init__.py', 'runtime.py', 'commands.py', 'engine.py', 'export.py', 'i18n.py', 'web.py']
PYODIDE = ['pyodide.js', 'pyodide.asm.js', 'pyodide.asm.wasm', 'pyodide-lock.json']
# zips are shipped base64 in .txt files: claude.ai artifacts don't serve archives
ARCHIVES = ['python_stdlib.zip', 'sympy-1.14.0-py3-none-any.whl', 'mpmath-1.3.0-py3-none-any.whl', 'kalam-core.zip']

STANDALONE_HEAD = '''<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#2f5bea"><link rel="manifest" href="manifest.json">
<link rel="apple-touch-icon" href="icon.svg"><meta name="apple-mobile-web-app-capable" content="yes">
<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}
body{margin:0}[hidden]{display:none!important}</style></head><body>
'''
STANDALONE_TAIL = '''
<script>if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(() => {});</script>
</body></html>
'''
SW = '''// Offline cache: the app shell, Pyodide and the wheels (about 20 MB) are kept after the first visit.
const C = 'kalam-v1';
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(clients.claim()));
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(caches.open(C).then(async c => {
    const hit = await c.match(e.request);
    const net = fetch(e.request).then(r => { if (r.ok || r.type === 'opaque') c.put(e.request, r.clone()); return r; });  // opaque: CDN scripts
    return hit || net;
  }));
});
'''
MANIFEST = {
    'name': 'Kalam', 'short_name': 'Kalam', 'start_url': '.', 'display': 'standalone',
    'background_color': '#f3f5f8', 'theme_color': '#2f5bea', 'lang': 'fr',
    'icons': [{'src': 'icon.svg', 'sizes': 'any', 'type': 'image/svg+xml', 'purpose': 'any maskable'}],
}
ICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect width="512" height="512" rx="112" fill="#2f5bea"/>'
        '<path d="M120 380 C200 120 312 120 392 380" fill="none" stroke="#fff" stroke-width="34" stroke-linecap="round"/>'
        '<circle cx="256" cy="186" r="26" fill="#fff"/></svg>')


def fetch_deps():
    """npm packages -> web/.deps/<name>/, wheels -> web/.deps/wheels/ (skipped when present)."""
    os.makedirs(DEPS, exist_ok=True)
    for name, spec in NPM.items():
        if os.path.isdir(os.path.join(DEPS, name)):
            continue
        out = subprocess.run('npm pack %s --silent' % spec, cwd=DEPS, shell=True, check=True,
                             capture_output=True, text=True).stdout.strip().splitlines()[-1]
        with tarfile.open(os.path.join(DEPS, out)) as t:
            t.extractall(os.path.join(DEPS, name + '.tmp'), filter='data')
        os.rename(os.path.join(DEPS, name + '.tmp', 'package'), os.path.join(DEPS, name))
        shutil.rmtree(os.path.join(DEPS, name + '.tmp'))
        os.remove(os.path.join(DEPS, out))
    wheels = os.path.join(DEPS, 'wheels')
    if not all(os.path.exists(os.path.join(wheels, w)) for w in ARCHIVES[1:3]):
        subprocess.run([sys.executable, '-m', 'pip', 'download', '--no-deps', '--only-binary', ':all:', '-q',
                        '-d', wheels, 'sympy==1.14.0', 'mpmath==1.3.0'], check=True)
    return os.path.join(DEPS, 'pyodide'), wheels


def main(offline=False):
    pyodide_dir, wheels_dir = fetch_deps()
    shutil.rmtree(DIST, ignore_errors=True)
    os.makedirs(os.path.join(DIST, 'py'))
    core = os.path.join(DIST, 'kalam-core.zip')
    with zipfile.ZipFile(core, 'w', zipfile.ZIP_DEFLATED) as z:
        for f in CORE:
            z.write(os.path.join(ROOT, 'kalam', f), 'kalam/' + f)
    for f in PYODIDE:
        shutil.copy(os.path.join(pyodide_dir, f), os.path.join(DIST, 'py', f))
    src = {'python_stdlib.zip': os.path.join(pyodide_dir, 'python_stdlib.zip'), 'kalam-core.zip': core}
    for f in ARCHIVES:
        with open(src.get(f) or os.path.join(wheels_dir, f), 'rb') as a, open(os.path.join(DIST, 'py', f + '.txt'), 'wb') as b:
            b.write(base64.b64encode(a.read()))
    os.remove(core)
    page = open(os.path.join(WEB, 'app.html'), encoding='utf-8').read()
    for lang in ('fr', 'ar'):
        with open(os.path.join(ROOT, 'examples', 'demo_%s.klm' % lang), encoding='utf-8') as f:
            page = page.replace('__DEMO_%s__' % lang.upper(), json.dumps(json.load(f), ensure_ascii=False))
    assert '__DEMO_' not in page
    if offline:
        os.makedirs(os.path.join(DIST, 'vendor'))
        for name, (url, rel) in VENDOR.items():
            local = 'vendor/' + os.path.basename(rel)
            shutil.copy(os.path.join(DEPS, name, rel), os.path.join(DIST, local))
            assert url in page, url
            page = page.replace(url, local)
    with open(os.path.join(DIST, 'app.html'), 'w', encoding='utf-8') as f:
        f.write(page)
    with open(os.path.join(DIST, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(STANDALONE_HEAD + page + STANDALONE_TAIL)
    with open(os.path.join(DIST, 'sw.js'), 'w') as f:
        f.write(SW)
    with open(os.path.join(DIST, 'manifest.json'), 'w') as f:
        json.dump(MANIFEST, f, indent=1)
    with open(os.path.join(DIST, 'icon.svg'), 'w') as f:
        f.write(ICON)
    print('built', DIST)


if __name__ == '__main__':
    main('--offline' in sys.argv)
