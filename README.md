# SymNote — CAS notebook + 2D/3D graphics in pure Python

SymNote is a GeoGebra/Desmos-style mathematics app written only in Python:
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

### What SymNote takes from each
| Idea | From | In SymNote |
|---|---|---|
| Objects defined by commands on other objects, recomputed when a free object moves | GeoGebra | each cell is a definition; editing/dragging re-evaluates the following cells |
| Interface in several languages | GeoGebra | menus, messages and help in French, Arabic and English; commands keep one (English) name |
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
| definition | `f(x) = x^2 - 2x - 3`, `A = (1, 2)` | nothing |
| expression | `Solve(f(x) = 0, x)`, `f`, `f(x)`, `A` | its result |
| drawing | `Draw(A, c)`, `Plot(f)`, `Represent(x^2 + y^2 < 4)` | a figure |
| text | `"Soit $f$ définie par $f(x) = {{f(x)}}$."` or `« … »` | the sentence; `$…$` is a formula, `{{expr}}` a computed value |
| hidden result | `Solve(f(x) = 0, x);` | nothing (trailing `;`) |
| comment | `# pour moi` | nothing |

- The code is never shown, only the output (a cell of definitions shows nothing); click a cell to edit it.
- **Figures appear only where you ask for them**, as the output of a drawing command:
  each kind of object has its command: `Draw(A, s, c)` / `Draw3D(...)` for geometric objects, `Plot(f)`, `Plot(f, g)`,
  `Plot(f, a, b)` / `Plot3D(f)` for functions, `Represent(...)` / `Represent3D(...)` for equations, inequalities and sets.
  To mix them in one figure: `G = Graphic()`, then `G.Plot(f)`, `G.Draw(A)`, `G.Represent(y = 1)`, … (each adds
  to G and shows nothing), then the line `G` shows the figure with all its objects.
  The same for space: `H = Graphic3D()`, then `H.Plot3D(x y)`, `H.Draw(Sphere((0,0,0), 1))`, then `H`.
  3D figures use WebGL (Plotly); where WebGL is missing (some Linux web views) a simpler canvas view is used
  instead (drag to turn, wheel to zoom). It can also be chosen in the figure's ⚙ options ("Rendu 3D").
  The ⚙ button opens the figure's properties: width, height, axes, grid, numbers on the axes, x/y window, tick step (`1`, `0.5`,
  `pi/2` for labels in π), and for each object its label text (`C_f` shows f as a subscript, `$\mathcal{C}_f$`
  is drawn as a formula), colour, label
  on/off, thickness, dashes, visible. They are saved with
  the notebook and used by the LaTeX export (except the tick step).
  In a figure: drag to pan, wheel or pinch to zoom, + − ⌂ buttons; drag a free point (`A = (1, 2)`) and its line
  is rewritten. Figures are exported to LaTeX (tkz) in place.
- **Enter** adds a line, **Ctrl+Enter** evaluates and stays on the cell, **Shift+Enter** evaluates and
  goes to the next cell; the **✓** button evaluates (phones). Cells after an edited one recompute.
- **Fichier** menu: New (Ctrl+N), Open (Ctrl+O), Save (Ctrl+S), Save as (Ctrl+Shift+S), Export (Ctrl+E);
  the **Commandes** button opens the commands editor. In the apps Save writes back to the opened file; in a browser it downloads the `.klm`.
- Typing `(` `[` `{` `"` adds the closing one; typing the closing one steps over it; Backspace on an empty pair
  removes both.
- **Clavier** tab: x, y, □², □^□, □/□, √□, ⁿ√□, |□|, π, e, ∞, ≤, sin, ln… inserted at the cursor, cursor left inside the box.
- Notebooks from earlier versions open unchanged: their text cells become `"…"` lines.

- **Tables**: `SignTable(x^2 - x - 6)` gives the sign table (a row per factor, then the expression;
  `‖` where it is not defined); `VariationTable(f)` gives the sign of f′ and the variations of f with its
  values, limits at ±∞ and on each side of a forbidden value. Coefficients must be numbers (a slider works).
  In the LaTeX export they become `tkz-tab` tables.
- **Your own tables**, built like graphics: `T = Table(5, 2)` (5 columns, 2 empty rows), then
  `T.Row(x, -1, 0, 1, 2)`, `T.Row("$f(x)$", f(-1), f(0), f(1), f(2))` fill the rows (a row is added when
  none is empty); the line `T` shows it. Text cells: `"+"`, `"-"`, `"0"`, `"||"`, `"↗"`, `"↘"` become signs and
  arrows, `"$…$"` is a formula.
- `SignTable` and `VariationTable` are tables too: `V = VariationTable(f)` then `V.Row("signe de $f$", …)`
  adds a sign row under it.
- The ⚙ button of a table (on hover): column width (cm), first column, text size, borders, alignment,
  header row/column; for sign/variation tables also factor rows and the lines at the values (dotted, solid cut
  at the number, or none); and **the content of every
  cell** (values in `$…$`, signs, arrows — changing an arrow moves the values up or down). Used by the LaTeX export.
- Arrows ↗ ↘: buttons in the cell editor of a table, keys on the Clavier tab (`"↗"`), or type `"/"` and `"\\"`.
- **Drag a cell by its number** (a grip appears on hover) to move it. A place where a variable would take another
  value (a cell before the definition it uses, or between two definitions) is refused, with the variable named.
- The Fichier menu can hide the cell numbers. The desktop apps draw their own title bar (minimize, maximize,
  close); drag the empty part of the bar to move the window.
- The tools button of a figure (sliders icon) shows its zoom +, −, ⌂ and ⚙ buttons.

- **Solutions as numbers**: `S = Solve(f(x) = 1/3, x)` then `S[0]` (the smallest solution), `S[1]`, … (numbered
  from 0, like lists); `f(S[0])` is its image, `a = Solve(x^2 = 2, x)[1]` gives `a = √2`.
- **Unsimplified expressions**: `Hold(2 * 3^2 - 4/6)`, `Hold(1/2 + 1/3)`, `Hold(3x - x)` are shown exactly as typed
  (nothing computed or reordered); `Simplify(...)` of one computes it.

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

Results are **exact** (decimals are read as fractions: `0.25` → `1/4`); use `Numeric(e)` / `Numeric(e)`
for a decimal approximation. Irrational numbers also show `≈`.

---

## 3. Commands

Commands have one name, the same in every interface language (French, Arabic and English menus).
Notebooks written with the French or Arabic command names of earlier versions are converted when opened.
The palette shows them in this order: Keyboard, then the groups below. Geometry and transformations work in the
plane and in space (in space Reflect also takes a plane, and Rotate turns around an axis: `Rotate(A, pi/2, Line(O, B))`).
Sets can also be written with symbols: `A ∪ B`, `A ∩ B`, `A ∖ B`, `ℕ ℤ ℚ ℝ ∅` (keys on the Keyboard tab);
intervals are shown as [a ; b], ]a ; b[.
`Represent(...)` draws a set of the plane given by equations or inequalities (several: their system),
`Represent3D(...)` the surfaces of space (planes, spheres, cylinders, z = f(x, y), ...).

**Calculus**

| Command | Example |
|---|---|
| Simplify | `Simplify(e)` |
| Hold | `Hold(2 + 3*4)` |
| Solve | `Solve(x^2 = 4, x)` |
| CSolve | `CSolve(x^2 = -4, x)` |
| NSolve | `NSolve(e, x)` |
| Substitute | `Substitute(e, x, 2)` |
| Numeric | `Numeric(e, 5)` |
| Sum | `Sum(k^2, k, 1, n)` |
| Sequence | `Sequence(k^2, k, 1, 5)` |
| Series | `Series(f, 0, 4)` |

**Arithmetic**

| Command | Example |
|---|---|
| GCD | `GCD(a, b)` |
| LCM | `LCM(a, b)` |
| Divisors | `Divisors(n)` |
| IsPrime | `IsPrime(n)` |
| PrimeFactors | `PrimeFactors(360)` |
| Quotient | `Quotient(17, 5)` |
| Remainder | `Remainder(17, 5)` |

**Sets**

| Command | Example |
|---|---|
| Interval | `Interval(-1, 3)` |
| IntervalOpen | `IntervalOpen(0, oo)` |
| IntervalLOpen | `IntervalLOpen(0, 1)` |
| IntervalROpen | `IntervalROpen(0, 1)` |
| FiniteSet | `FiniteSet(1, 2, 3)` |
| Union | `Union(A, B)` |
| Intersection | `Intersection(A, B)` |
| Complement | `Complement(A, B)` |
| IsIn | `IsIn(2, A)` |
| IsSubset | `IsSubset(A, B)` |
| Cardinal | `Cardinal(A)` |
| Inf | `Inf(A)` |
| Sup | `Sup(A)` |
| Represent | `Represent(x^2 + y^2 <= 4, x + y - 1 > 0)` |
| Represent3D | `Represent3D(x^2 + y^2 + z^2 = 4)` |

**Functions**

| Command | Example |
|---|---|
| Domain | `Domain(f)` |
| Derivative | `Derivative(f)` |
| Integral | `Integral(f, a, b)` |
| Limit | `Limit(f, oo)` |
| Tangent | `Tangent(f, a)` |
| Plot | `Plot(f, a, b)` |
| Plot3D | `Plot3D(f)` |
| SignTable | `SignTable(x^2 - 4)` |
| VariationTable | `VariationTable(f)` |

**Polynomials**

| Command | Example |
|---|---|
| Expand | `Expand(e)` |
| Factor | `Factor(e)` |
| PartialFractions | `PartialFractions(e)` |
| Degree | `Degree(x^3 - 2x)` |
| Coefficients | `Coefficients(2x^2 - 3x + 1)` |
| Roots | `Roots((x - 1)^2 (x + 2))` |
| Discriminant | `Discriminant(x^2 + x + 1)` |
| Divide | `Divide(x^3 - 1, x - 1)` |

**Trigonometry**

| Command | Example |
|---|---|
| TrigSimplify | `TrigSimplify(sin(x)^2 + cos(x)^2)` |
| TrigExpand | `TrigExpand(cos(2x))` |
| TrigLinearize | `TrigLinearize(cos(x)^2)` |
| SolveIn | `SolveIn(sin(x) = 1/2, x, 0, 2pi)` |
| Degrees | `Degrees(pi/3)` |
| Radians | `Radians(60)` |

**Transformations**

| Command | Example |
|---|---|
| Reflect | `Reflect(o, d)` |
| Rotate | `Rotate(o, pi/2, O)` |
| Translate | `Translate(o, u)` |
| Dilate | `Dilate(o, k, O)` |

**Geometry**

| Command | Example |
|---|---|
| Point | `Point(x, y)` |
| Segment | `Segment(A, B)` |
| Line | `Line(A, B)` |
| Ray | `Ray(A, B)` |
| Circle | `Circle(O, r)` |
| Polygon | `Polygon(A, B, C)` |
| Midpoint | `Midpoint(A, B)` |
| Intersect | `Intersect(a, b)` |
| Perpendicular | `Perpendicular(A, d)` |
| Parallel | `Parallel(A, d)` |
| PerpendicularBisector | `PerpendicularBisector(A, B)` |
| AngleBisector | `AngleBisector(A, B, C)` |
| Distance | `Distance(A, B)` |
| Length | `Length(s)` |
| Area | `Area(P)` |
| Vector | `Vector(A, B)` |
| Sphere | `Sphere(O, r)` |
| Plane | `Plane(A, B, C)` |
| Tetrahedron | `Tetrahedron(A, B, C, D)` |
| Pyramid | `Pyramid(S, A, B, C, D)` |
| Prism | `Prism(A, B, C, Vector(0, 0, 2))` |
| Cube | `Cube((0, 0, 0), 2)` |
| Cuboid | `Cuboid((0, 0, 0), 3, 2, 1)` |
| Cylinder | `Cylinder((0, 0, 0), (0, 0, 3), 1)` |
| Cone | `Cone((0, 0, 0), (0, 0, 3), 1)` |
| Volume | `Volume(o)` |

**Figures**

| Command | Example |
|---|---|
| Graphic | `Graphic()` |
| Draw | `Draw(f, A, c)` |
| Draw3D | `Draw3D(S, P)` |
| ParametricCurve | `ParametricCurve(cos(t), sin(t), t, 0, 2pi)` |
| Slider | `Slider(-5, 5, 0.1)` |
| Graphic3D | `Graphic3D()` |
| ParametricSurface | `ParametricSurface(cos(u)cos(v), sin(u)cos(v), sin(v), u, 0, 2pi, v, -pi/2, pi/2)` |
| Table | `Table(3, 2)` |
| Row | `Row(T, a, b, c)` |

**Matrices**

| Command | Example |
|---|---|
| Matrix | `Matrix([[1, 2], [3, 4]])` |
| Det | `Det(M)` |
| Inverse | `Inverse(M)` |
| Transpose | `Transpose(M)` |
| Eigenvalues | `Eigenvalues(M)` |

### Your own commands
**Commands → Commands editor**: write a Python function `run(*args)` with SymPy, give it a name,
a category and an argument hint; **Test** it, **Save** it. It appears in the palette (*My commands*).
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
  *Add to Home Screen*), Windows/Linux/macOS (Chrome or Edge → *Install SymNote*).
- **App stores** (not done here): wrap `web/dist/` with Capacitor (`npx cap add android`, `npx cap add ios`);
  an iOS build needs a Mac with Xcode and an Apple developer account.
- Notebooks are kept in the browser's storage; **Export** gives Python / LaTeX / tkz / .klm text to copy,
  or one `.zip` with all four.
- Archives are shipped base64 in `.txt` files because claude.ai artifacts don't serve `.zip`.

## Native apps with Tauri: Windows, Linux, macOS, Android, iOS

Architecture: **web core** (`web/app.html`) + **Pyodide** (SymPy and the SymNote Python core run
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
`sympy.parse_expr` in the environment left by the previous cells. SymNote keeps a snapshot of the
environment before each cell, so editing cell *n* only recomputes cells *n…end*.

## 6. Known limits
- Formulas are drawn by Matplotlib *mathtext* (not full LaTeX): matrices fall back to a text layout.
- In the editor, Arabic command names followed by numbers follow standard Unicode bidi order
  (the rendered line below is shown left to right).
- Implicit surfaces in 3D are drawn only when the equation can be solved for `z`.
- Points cannot yet be constrained *on* an object (only free points are draggable).
- The tkz export skips implicit curves and inequality regions.
