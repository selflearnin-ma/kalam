# Kalam — CAS notebook + 2D/3D graphics in pure Python

Kalam is a GeoGebra/Desmos-style mathematics app written only in Python:
**SymPy** is the computer algebra system, **PySide6 (Qt)** the interface,
**Matplotlib** renders formulas and the 3D view, **NumPy/contourpy** sample curves.

There is no algebra view: everything is typed as **commands in a CAS notebook**,
and every drawable result appears in the **2D** or **3D** graphics view.
Interface and commands work in **French, Arabic (right-to-left) and English**.

```
pip install -r requirements.txt
python -m kalam                      # empty notebook
python -m kalam examples/demo_fr.klm # French demo
python tests/test_core.py            # core self-checks
```

---

## 1. How GeoGebra, Desmos and Polypad work

### GeoGebra
- **Dependency graph of objects.** Each object (`A`, `c`, `f`…) is either *free* (a value: `A=(1,2)`)
  or *dependent* (defined by a command on other objects: `M=Midpoint(A,B)`). The whole file is a
  "construction protocol": an ordered list of definitions. Moving a free point recomputes every
  object downstream — this is what makes geometry *dynamic*.
- **Several views on the same objects**: Algebra view (definitions/values), Graphics 2D, Graphics 3D,
  CAS view (symbolic, powered by the Giac engine), spreadsheet. A CAS cell can be linked to a
  graphical object (the round toggle next to the cell).
- **Commands** are the real API (`Circle`, `Intersect`, `Solve`…): toolbar buttons are only shortcuts
  that build commands from mouse clicks. Command names are translated in every language; the
  file stores them in English so it opens in any language.
- **File format**: `.ggb` = zip of `geogebra.xml` (the construction) + thumbnails.
  **Export**: PGF/TikZ, PSTricks, images, HTML.

### Desmos
- **Expression list**: each line is one expression; lines reference each other *by name* and Desmos
  builds the dependency graph from the names (not from line order).
- **Equations are drawn directly**: `y=x^2`, `x^2+y^2=4`, inequalities `y<2x` (shaded regions),
  parametric `(cos t, sin t)`. Implicit curves are sampled adaptively (quadtree subdivision).
- **Sliders**: an undefined parameter (`a` in `y=ax`) offers a slider; dragging it re-evaluates live.
- **Math editor** (MathQuill): you type plain text and it renders as 2D math in place.
- Mostly **numeric**: very little symbolic algebra (no factoring/solving as a CAS).

### Polypad (Mathigon)
- A **virtual manipulatives canvas**: algebra tiles, fraction bars, number cards, polygons, balance
  scales… Objects are SVG tiles with snapping, grouping and rotation.
- The mathematics lives in the **behaviour of tiles** (e.g. `x` tiles + `1` tiles combine,
  a balance stays equal) rather than in a CAS. Good for discovery, not for symbolic computation.

### What Kalam takes from each
| Idea | From | In Kalam |
|---|---|---|
| Objects defined by commands on other objects, recomputed when a free object moves | GeoGebra | each cell is a definition; editing/dragging re-evaluates the following cells |
| Localized command names, file portable across languages | GeoGebra | every command has an English, French and Arabic name, all accepted everywhere |
| Type an equation, see its graph | Desmos | `y = 2x+1`, `x^2+y^2<4`, `z = x y` are drawn directly |
| Sliders | Desmos | `a = Slider(-5, 5, 0.1)` shows a slider; moving it updates graphs live |
| Input turns into rendered math, click to edit | Desmos / notebooks | each cell shows its rendered result; click it to edit |
| Real symbolic CAS | GeoGebra CAS | SymPy: exact solving, factoring, derivatives, integrals, limits, series… |
| Palette of buttons | GeoGebra toolbar / Polypad | the palette only *inserts commands* into the active cell |

---

## 2. Using the notebook

There is one kind of cell: **code**. A cell can hold several lines, and its output is shown
**in place of the cell**; click it to edit the code again.

| Line | Example | Shown |
|---|---|---|
| definition | `f(x) = x^2 - 2x - 3`, `A = (1, 2)` | nothing (defined, and drawn if drawable) |
| expression | `Résoudre(f(x) = 0, x)`, `f`, `f(x)`, `A` | its result |
| text | `"Soit $f$ définie par $f(x) = {{f(x)}}$."` or `« … »` | the sentence; `$…$` is a formula, `{{expr}}` a computed value |
| hidden result | `Résoudre(f(x) = 0, x);` | nothing (trailing `;`) |
| comment | `# pour moi` | nothing |

- The code is never shown, only the output (a cell of definitions shows nothing); click a cell to edit it.
- **Only definitions are drawn** (`f(x) = …`, `A = …`, `c = Cercle(…)`). Results (`f(x)`, `Tangente(f, 3)`, an
  unnamed equation) are shown, not drawn: name an equation or region to draw it, `C = x^2 + y^2 = 4`.
- **Enter** adds a line, **Ctrl+Enter** evaluates and stays on the cell, **Shift+Enter** evaluates and
  goes to the next cell; the **✓** button evaluates (phones). Cells after an edited one recompute.
- The **coloured dots** show/hide each drawn object of the cell; the **⋯** menu inserts, moves,
  deletes a cell and sets colours.
- **Drag free points** (`A = (1, 2)`) in the 2D view; their line is rewritten.
- 2D view: drag to pan, wheel or pinch to zoom, buttons + − ⌂. 3D view: drag to rotate, wheel to zoom.
- Notebooks from earlier versions open unchanged: their text cells become `"…"` lines.

### Input language

| You type | Meaning |
|---|---|
| `A = (1, 2)` or `A := Point(1, 2)` | point (3 coordinates → 3D point) |
| `f(x) = x^2 - 2x` | function (drawn) |
| `y = 2x + 1`, `x^2 + y^2 = 4` | equations in x, y (drawn) |
| `x^2 + y^2 < 4` | inequality (shaded region) |
| `z = x^2 - y^2`, `x + y + z = 1` | surfaces / planes (3D) |
| `Solve(x^2 = 4, x)` | command; `=` inside a command means an equation |
| `f'(x)`, `f''(2)` | derivatives |
| `2x`, `3(x+1)`, `a x^2` | implicit multiplication |
| `π`, `√2`, `x²`, `∞`, `≤`, `e`, `i`, `ln` | usual notations (`e` = exp(1), `i` = imaginary unit) |
| `$3` | result of cell 3 (its last line) |
| Arabic-Indic digits `٣`, Arabic comma `،` | accepted |

Results are **exact** (decimals are read as fractions: `0.25` → `1/4`); use `Numeric(e)` / `Valeur(e)`
for a decimal approximation. Irrational numbers also show `≈`.

---

## 3. Commands

**Geometry**

| English | Français | العربية | Arguments |
|---|---|---|---|
| Point | Point | نقطة | `x, y` |
| Segment | Segment | قطعة | `A, B` |
| Line | Droite | مستقيم | `A, B` |
| Ray | DemiDroite | نصف_مستقيم | `A, B` |
| Circle | Cercle | دائرة | `O, r` |
| Polygon | Polygone | مضلع | `A, B, C` |
| Midpoint | Milieu | منتصف | `A, B` |
| Intersect | Intersection | تقاطع | `a, b` |
| Perpendicular | Perpendiculaire | عمودي | `A, d` |
| Parallel | Parallèle | مواز | `A, d` |
| PerpendicularBisector | Médiatrice | واسط | `A, B` |
| AngleBisector | Bissectrice | منصف | `A, B, C` |
| Distance | Distance | مسافة | `A, B` |
| Length | Longueur | طول | `s` |
| Area | Aire | مساحة | `P` |
| Tangent | Tangente | مماس | `f, a` |
| Vector | Vecteur | متجهة | `A, B` |

**Transformations**

| English | Français | العربية | Arguments |
|---|---|---|---|
| Reflect | Symétrie | تماثل | `o, d` |
| Rotate | Rotation | دوران | `o, pi/2, O` |
| Translate | Translation | إزاحة | `o, u` |
| Dilate | Homothétie | تحاك | `o, k, O` |

**Algebra**

| English | Français | العربية | Arguments |
|---|---|---|---|
| Simplify | Simplifier | تبسيط | `e` |
| Expand | Développer | نشر | `e` |
| Factor | Factoriser | تعميل | `e` |
| Solve | Résoudre | حل | `x^2 = 4, x` |
| CSolve | RésoudreC | حل_عقدي | `x^2 = -4, x` |
| NSolve | RésoudreN | حل_عددي | `e, x` |
| Substitute | Substituer | تعويض | `e, x, 2` |
| Numeric | Valeur | قيمة_مقربة | `e, 5` |
| PartialFractions | ElémentsSimples | تفكيك | `e` |
| GCD | PGCD | قاسم_مشترك | `a, b` |
| LCM | PPCM | مضاعف_مشترك | `a, b` |
| Divisors | Diviseurs | قواسم | `n` |
| IsPrime | EstPremier | أولي | `n` |

**Calculus**

| English | Français | العربية | Arguments |
|---|---|---|---|
| Derivative | Dérivée | مشتقة | `f` |
| Integral | Intégrale | تكامل | `f, a, b` |
| Limit | Limite | نهاية | `f, oo` |
| Series | DL | نشر_محدود | `f, 0, 4` |
| Sum | Somme | مجموع | `k^2, k, 1, n` |
| Sequence | Suite | متتالية | `k^2, k, 1, 5` |

**Matrices**

| English | Français | العربية | Arguments |
|---|---|---|---|
| Matrix | Matrice | مصفوفة | `[[1, 2], [3, 4]]` |
| Det | Déterminant | محددة | `M` |
| Inverse | Inverse | مقلوب | `M` |
| Transpose | Transposée | منقول | `M` |
| Eigenvalues | ValeursPropres | قيم_ذاتية | `M` |

**Graphs**

| English | Français | العربية | Arguments |
|---|---|---|---|
| Plot | Courbe | منحنى | `f, a, b` |
| ParametricCurve | CourbeParamétrée | منحنى_وسيطي | `cos(t), sin(t), t, 0, 2pi` |
| Slider | Curseur | منزلق | `-5, 5, 0.1` |

**Space**

| English | Français | العربية | Arguments |
|---|---|---|---|
| Plot3D | Graphe3D | رسم_فضائي | `x^2 - y^2` |
| ParametricSurface | SurfaceParamétrée | سطح_وسيطي | `cos(u)cos(v), sin(u)cos(v), sin(v), u, 0, 2pi, v, -pi/2, pi/2` |
| Sphere | Sphère | فلكة | `O, r` |
| Plane | Plan | مستوى | `A, B, C` |

### Your own commands
**Commands → Commands editor**: write a Python function `run(*args)` with SymPy, give it an
English, French and Arabic name, a category and an argument hint; **Test** it, **Save** it.
It appears in the palette (*My commands*) and works in the notebook in all three languages.
Inside the code you have `sp` (SymPy), the symbols `x y z t`, every built-in command and the helpers
`_body(f)` (expression and variable of a function) and `_pt(p)` (tuple → point). Example:

```python
def run(f, a):
    """Normal line to the graph of f at x = a."""
    e, v = _body(f)
    d = sp.diff(e, v).subs(v, a)
    return sp.Eq(y, sp.expand(-(x - a) / d + e.subs(v, a)))
```
User commands are stored in `~/.kalam/user_commands.json` and also inside each `.klm` file.

---

## 4. Files and exports
- **`.klm`** (JSON): cells, colours, visibility, 2D view, language and the user commands used.
- **Export to Python**: a standalone script (only SymPy needed) that recomputes the notebook and
  prints every result. Text cells become comments.
- **Export to LaTeX**: an `article` with text cells, inputs and results (`babel` French; Arabic uses
  `polyglossia` → compile with XeLaTeX/LuaLaTeX).
- **LaTeX figure (tkz)**: `standalone` file, **tkz-euclide** for points/segments/lines/circles/polygons,
  **tkz-fct** for functions and parametric curves, coordinates with 2 decimals, window = current view.
  tkz-fct calls gnuplot: compile with `pdflatex --shell-escape`.

---

## Web version: Windows, Linux, macOS, iOS, Android

The same Python core runs in the browser with **Pyodide** (CPython compiled to WebAssembly).
`kalam/web.py` is a JSON bridge over the engine; `web/app.html` replaces the Qt interface
(notebook, palette, 2D canvas with touch/pinch, 3D via Plotly, formulas via MathJax).
Functions are sent to the page as JavaScript expressions (`sympy.jscode`) so curves are sampled at full speed.

```
python web/build.py PYODIDE_DIR WHEELS_DIR    # see the docstring; output in web/dist/
cd web/dist && python -m http.server           # try it: http://localhost:8000
```
- **Any device**: put `web/dist/` on any static host (GitHub Pages, Netlify, a school server).
  First visit downloads about 20 MB, then it works **offline** (service worker).
- **Install it like an app**: Android (Chrome menu → *Install app*), iOS/iPadOS (Safari → Share →
  *Add to Home Screen*), Windows/Linux/macOS (Chrome or Edge → *Install Kalam*).
- **App stores** (not done here): wrap `web/dist/` with Capacitor (`npx cap add android`, `npx cap add ios`);
  an iOS build needs a Mac with Xcode and an Apple developer account.
- Notebooks are kept in the browser's storage; **Export** gives Python / LaTeX / tkz / .klm text to copy,
  or one `.zip` with all four.
- Archives are shipped base64 in `.txt` files because claude.ai artifacts don't serve `.zip`.

## Native apps with Tauri: Windows, Linux, macOS, Android, iOS

Architecture: **web core** (`web/app.html`) + **Pyodide** (SymPy and the Kalam Python core run
inside the app's webview) + **Tauri 2** (`src-tauri/`, a small Rust shell: window, native save dialog).
Everything is bundled, so the apps work **offline** (`web/build.py --offline` copies MathJax and Plotly locally).

```
npm install                    # Tauri CLI
npx tauri dev                  # run the desktop app (builds web/dist first)
npx tauri build                # installer for this computer (.msi/.exe, .deb/.AppImage/.rpm, .dmg)
npx tauri android init && npx tauri android build --apk     # needs Android SDK + NDK, Java 17
npx tauri ios init && npx tauri ios build                    # needs a Mac with Xcode + Apple team
```
Requirements on your machine: Rust (rustup), Node 22, Python 3. On Linux also
`libwebkit2gtk-4.1-dev libappindicator3-dev librsvg2-dev patchelf`.

**Easiest: let GitHub build everything.** Push the project to a GitHub repository, open
*Actions → build → Run workflow*. `.github/workflows/build.yml` builds Windows, Linux, macOS and an
Android APK (debug-signed, installable directly on a phone) and attaches them to the run.
The iOS job runs once you add the repository variable `APPLE_DEVELOPMENT_TEAM` and the secrets
`APPLE_API_KEY_ID`, `APPLE_API_ISSUER`, `APPLE_API_KEY` (an Apple developer account is required).

Files: `src-tauri/tauri.conf.json` (window, CSP allowing WebAssembly, build hook),
`src-tauri/capabilities/default.json` (only the save dialog and writing the chosen file),
`src-tauri/src/lib.rs` (plugins), `src-tauri/icons/` (all sizes, made with `npx tauri icon src-tauri/app-icon.png`).

## 5. Code layout
```
kalam/
  runtime.py    every built-in command, SymPy only (copied verbatim into Python exports)
  commands.py   registry: names fr/ar/en, categories, palette hints, user commands
  engine.py     parser/normalizer (aliases, unicode, implicit ×, equations), cells, evaluation
  export.py     .klm, Python, LaTeX notebook, tkz figure
  i18n.py       interface strings
  ui/app.py         main window, toolbar, style
  ui/notebook.py    cells (render ↔ edit), sliders
  ui/canvas2d.py    2D view (QPainter): grid, curves, implicit curves, regions, dragging
  ui/view3d.py      3D view (Matplotlib)
  ui/palette.py     command buttons
  ui/cmdeditor.py   commands editor
  ui/mathrender.py  LaTeX → image (Matplotlib mathtext)
```
How evaluation works: each cell's text is normalized to SymPy source (aliases → English names,
`2x` → `2*x`, `a = b` inside a command → `Eq(a, b)`, `x²` → `x**2`…), then evaluated with
`sympy.parse_expr` in the environment left by the previous cells. Kalam keeps a snapshot of the
environment before each cell, so editing cell *n* only recomputes cells *n…end*.

## 6. Known limits
- Formulas are drawn by Matplotlib *mathtext* (not full LaTeX): matrices fall back to a text layout.
- In the editor, Arabic command names followed by numbers follow standard Unicode bidi order
  (the rendered line below is shown left to right).
- Implicit surfaces in 3D are drawn only when the equation can be solved for `z`.
- Points cannot yet be constrained *on* an object (only free points are draggable).
- The tkz export skips implicit curves and inequality regions.
