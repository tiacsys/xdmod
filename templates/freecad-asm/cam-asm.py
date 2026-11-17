# FreeCADCmd script of `curatrix cam <repo> <asm>` (task 5.26; XD-ADR-0137, XD-ADR-0143). Run only
# through curatrix: workspace-local FreeCAD config, limits. Inputs by environment variables
# (FreeCADCmd opens extra arguments as files, FreeCAD spike):
#   XD_TOP, XD_SKELETON  the top document and its skeleton (opened skeleton first, XD-ADR-0146)
#   XD_OUT               the output folder of this variant (fresh, made by curatrix)
#   XD_VARIANT           the variant: links whose own Configs do not name it are left out; "" = all
#                        links; "base" = only the links without Configs (every configuration that
#                        no link names)
#   XD_VERSION           the full version (drawing title block); XD_SHORT the short one (embossed)
#   XD_FONT              the pinned font file for the emboss
#   XD_EXPLODE           JSON {link name: [dx, dy, dz]} of the exploded view, or {} (automatic)
#   XD_RELEASE           "1" for a release, else the renderings carry the PREVIEW marking
#   QT_QPA_PLATFORM      offscreen (set by curatrix): Qt writes the text and the PNG, without OpenGL
#   XD_RESULT            the result file
# FreeCADCmd exits 0 when a script raises: the caller judges success by the result file. The script
# never raises and never saves a document (curatrix checks the md5 of the sources before and after).
#
# Writes into XD_OUT: <asm>.step (the present links of the assembly), parts/<part>.stl and .3mf per
# printed part (an object with a PrintProfile property; embossed with XD_SHORT on its version mark,
# an LCS with Role = version-emboss, TextSize, MaxWidth, optional EmbossDepth), views/<view>.svg
# (TechDraw views front, top, right, iso of the assembly), exploded.svg (TechDraw view of the
# exploded compound with explosion lines), renderings/<view>.png (front, top, right, iso; shaded
# with visible edges, from FreeCAD's tessellation, without OpenGL, task 5.30). The result lists the BOM rows
# (one per present leaf link) and the files.
import json
import os
import traceback

import FreeCAD as App

res = os.environ.get("XD_RESULT", "")
out = {"ok": False}
LCS_TYPES = ("Part::LocalCoordinateSystem", "PartDesign::CoordinateSystem")
BOM_PROPS = ("TraceID", "PrintProfile", "Material", "Standard", "Manufacturer", "MPN")
# view: (Direction, the view normal towards the viewer; XDirection, the model direction that points
# right in the view). Up is Direction x XDirection: +z for front, right and iso, +y for top.
VIEWS = {"front": ((0, -1, 0), (1, 0, 0)), "top": ((0, 0, 1), (1, 0, 0)), "right": ((1, 0, 0), (0, 1, 0)),
         "iso": ((1, -1, 1), (1, 1, 0))}


def prop(o, name):
    return str(getattr(o, name, "") or "").strip() if o is not None and name in o.PropertiesList else ""


def present(link, variant):
    cfgs = [c.strip() for c in prop(link, "Configs").replace(";", ",").split(",") if c.strip()]
    if variant == "base":
        return not cfgs
    return not variant or not cfgs or variant in cfgs


def is_asm(o):
    return o is not None and prop(o, "TraceID").startswith("ME-ASM-")


def walk(asm, variant, path, rows, placement):
    """BOM rows of the present leaf links below an assembly object (sub-assemblies recursively)."""
    for c in getattr(asm, "Group", []) or []:
        if not c.TypeId.startswith("App::Link") or not present(c, variant):
            continue
        t = c.getLinkedObject(True)
        f = t.Document.FileName if t is not None else ""
        if f.endswith("-skeleton.FCStd"):
            continue
        pl = placement.multiply(c.Placement)
        if is_asm(t):
            walk(t, variant, path + [c.Name], rows, pl)
            continue
        rows.append({"path": "/".join(path + [c.Name]), "file": f, "object": t.Name if t else "",
                     "label": t.Label if t else c.Label, **{p: prop(t, p) for p in BOM_PROPS}, "_obj": t, "_pl": pl})


def view_svg(shape, view, name, d):
    """A TechDraw view of a shape as SVG (FreeCAD spike §5: a page with a template is needed, the
    view computes in a thread, so wait for its edges; no GUI, no event loop)."""
    import TechDraw
    import time
    page = d.getObject("XdPage")
    if page is None:
        page = d.addObject("TechDraw::DrawPage", "XdPage")
        tpl = d.addObject("TechDraw::DrawSVGTemplate", "XdTemplate")
        tpl.Template = App.getResourceDir() + "Mod/TechDraw/Templates/Default_Template_A4_Landscape.svg"
        page.Template = tpl
    holder = d.addObject("Part::Feature", f"XdSrc_{name}")
    holder.Shape = shape
    v = d.addObject("TechDraw::DrawViewPart", f"XdView_{name}")
    page.addView(v)
    v.Source = [holder]
    v.Direction = App.Vector(*view[0])
    v.XDirection = App.Vector(*view[1])
    d.recompute()
    for _ in range(120):
        if v.getVisibleEdges():
            break
        time.sleep(0.25)
    edges = len(v.getVisibleEdges())
    return TechDraw.viewPartAsSvg(v), edges


def emboss(part, text, font):
    """(shape, info) of a part with the text embossed on its version mark, or (None, why). The mark
    is the LCS with Role = version-emboss of the part's document, not tied to one object: one mark per
    document (CK-F19), so one printed part per document."""
    import Draft
    import Part
    mark = next((o for o in part.Document.Objects if o.TypeId in LCS_TYPES and prop(o, "Role") == "version-emboss"),
                None)
    if mark is None:
        return None, "no version mark (LCS with Role = version-emboss)"
    size = float(getattr(mark, "TextSize", 3) or 3)
    maxw = float(getattr(mark, "MaxWidth", 0) or 0)
    depth = float(getattr(mark, "EmbossDepth", 0.6) or 0.6)
    base = part.Shape.copy()
    for _ in range(6):
        ss = Draft.make_shapestring(String=text, FontFile=font, Size=size, Tracking=0)
        ss.Document.recompute()
        w = ss.Shape.BoundBox.XLength
        if not maxw or w <= maxw:
            break
        size *= maxw / w * 0.98
        ss.Document.removeObject(ss.Name)
    txt = ss.Shape.copy()
    ss.Document.removeObject(ss.Name)
    gp = mark.getGlobalPlacement() if hasattr(mark, "getGlobalPlacement") else mark.Placement
    txt.Placement = gp.multiply(txt.Placement)
    z = gp.Rotation.multVec(App.Vector(0, 0, 1))
    solid = txt.extrude(z * depth)
    result = base.fuse(solid).removeSplitter()
    info = {"text": text, "size": round(size, 3), "depth": depth, "width": round(w, 3),
            "solids": len(result.Solids), "valid": result.isValid(),
            "volume_before": round(base.Volume, 4), "volume_after": round(result.Volume, 4)}
    if len(result.Solids) != 1 or not result.isValid() or result.Volume <= base.Volume:
        return None, f"the embossed part is not exactly one valid solid: {info}"
    return result, info


# renderings (task 5.30; the fallback when Blender is not there): FreeCAD tessellates the parts; each
# facet is shaded flat (one light from the viewer's upper left) and drawn into a z-buffer (numpy, a
# dependency of FreeCAD) at twice the size, as scanline spans, vectorised in chunks; the visible edges
# (without seam edges) on top; then averaged down. FreeCAD's Qt (QImage, QPainter, offscreen
# platform) writes the text and the PNG. No OpenGL: Coin3D offscreen snapshots and the Render
# workbench do not work headless here (claude/notes/me-renderings-spike.md).
KIND_RGB = {"printed": (232, 140, 40), "board": (40, 125, 70), "fastener": (165, 165, 175),
            "bought": (95, 95, 105), "part": (85, 130, 185)}
RENDER_W, RENDER_H, RENDER_MARGIN, RENDER_TOP, SS = 1600, 1200, 90, 150, 2
BATCH_SAMPLES = 2_000_000             # sample points per z-buffer batch (memory: ~100 bytes each)


def kind_of(r):
    return ("board" if r.get("TraceID", "").startswith("EE-PCBA") else "printed" if r.get("PrintProfile")
            else "fastener" if r.get("Standard") else "bought" if r.get("Manufacturer") or r.get("MPN") else "part")


def leaf_shape(asm, r, kids):
    """The shape of a BOM row in assembly coordinates: the sub-object along the row's link path."""
    import Part
    try:
        s = Part.getShape(asm, r["path"].replace("/", ".") + ".")
        if not s.isNull():
            return s
    except Exception:
        pass
    first = r["path"].split("/")[0]
    return next((c.Shape for c in kids if c.Name == first), None)


def scene(asm, rows, kids):
    """(facets, edges, diagonal) of the present leaf parts: facets as (rgb, 3x3 points, normal),
    edges as polylines (lists of points), both in assembly coordinates. Seam edges (an edge that
    bounds the same face twice, as on a cylinder) are left out."""
    import MeshPart
    import Part
    shapes = [(r, leaf_shape(asm, r, kids)) for r in rows]
    shapes = [(r, s) for r, s in shapes if s is not None and not s.isNull()]
    if not shapes:
        return [], [], 1.0
    diag = Part.makeCompound([s for _, s in shapes]).BoundBox.DiagonalLength
    fs, es = [], []
    for i, (r, s) in enumerate(shapes):
        rgb = tuple(int(c * (1 - 0.12 * (i % 3))) for c in KIND_RGB[kind_of(r)])
        mesh = MeshPart.meshFromShape(Shape=s, LinearDeflection=max(diag / 2000, 0.005), AngularDeflection=0.2,
                                      Relative=False)
        for f in mesh.Facets:
            fs.append((rgb, [tuple(p) for p in f.Points], tuple(f.Normal)))
        seams = set()
        for f in s.Faces:
            hs = [e.hashCode() for e in f.Edges]
            seams |= {h for h in hs if hs.count(h) > 1}
        for e in s.Edges:
            if e.hashCode() in seams:
                continue
            try:
                pts = e.discretize(Deflection=max(diag / 4000, 0.002))
            except Exception:
                continue
            if len(pts) > 1:
                es.append([tuple(p) for p in pts])
    return fs, es, diag


def _axes(view):
    import numpy as np
    D = np.array(view[0], float)
    D /= np.linalg.norm(D)
    X = np.array(view[1], float)
    X /= np.linalg.norm(X)
    return D, X, np.cross(D, X)


def fit_scale(sc, view):
    """Pixels per mm at which the scene fills the image in this view (below the text band)."""
    import numpy as np
    if not sc[0]:
        return 1.0
    D, X, U = _axes(view)
    P = np.array([f[1] for f in sc[0]], float)
    sx, sy = P @ X, P @ U
    return min((RENDER_W - 2 * RENDER_MARGIN) / max(sx.max() - sx.min(), 1e-9),
               (RENDER_H - 2 * RENDER_MARGIN - RENDER_TOP) / max(sy.max() - sy.min(), 1e-9))


def render(sc, view, path, lines, preview, font, scale=None):
    """Render the scene in a view (VIEWS) into a PNG at ``scale`` px/mm (None: fit); returns the
    number of facets that won at least one pixel when they were drawn (0: an empty rendering).
    No back-face culling: a solid with flipped normals (some STEP imports) still renders."""
    import numpy as np
    from PySide import QtCore, QtGui
    fs, es, diag = sc
    D, X, U = _axes(view)
    light = D + 0.6 * U - 0.4 * X
    light /= np.linalg.norm(light)
    W, H = RENDER_W * SS, RENDER_H * SS
    zbuf = np.full(H * W, -np.inf)
    cbuf = np.full((H * W, 3), 255, np.uint8)
    drawn = 0
    if fs:
        scale = fit_scale(sc, view) if scale is None else scale
        P = np.array([f[1] for f in fs], float)                       # (n, 3, 3)
        N = np.array([f[2] for f in fs], float)
        rgb = np.array([f[0] for f in fs], float)
        sx, sy, sz = P @ X, P @ U, P @ D
        x0, x1, y0, y1 = sx.min(), sx.max(), sy.min(), sy.max()
        s = scale * SS
        ox = (W - (x1 - x0) * s) / 2
        oy = RENDER_MARGIN * SS + (H - 2 * RENDER_MARGIN * SS - RENDER_TOP * SS - (y1 - y0) * s) / 2

        def to_px(x, y):
            return ox + (x - x0) * s, H - oy - (y - y0) * s
        px, py = to_px(sx, sy)
        col = np.clip(rgb * (0.3 + 0.7 * np.abs(N @ light))[:, None], 0, 255).astype(np.uint8)
        zeps = diag * 1e-6                       # coplanar faces: the first facet drawn stays (no speckle)
        zq = sz / zeps                           # depth in steps of zeps (rounded per pixel below)
        area = (px[:, 1] - px[:, 0]) * (py[:, 2] - py[:, 0]) - (px[:, 2] - px[:, 0]) * (py[:, 1] - py[:, 0])
        ok = np.abs(area) > 1e-12
        # depth plane per facet: z = za * x + zb * y + zc (in pixel coordinates)
        ar = np.where(ok, area, 1.0)
        za = ((zq[:, 1] - zq[:, 0]) * (py[:, 2] - py[:, 0]) - (zq[:, 2] - zq[:, 0]) * (py[:, 1] - py[:, 0])) / ar
        zb = ((px[:, 1] - px[:, 0]) * (zq[:, 2] - zq[:, 0]) - (px[:, 2] - px[:, 0]) * (zq[:, 1] - zq[:, 0])) / ar
        zc = zq[:, 0] - za * px[:, 0] - zb * py[:, 0]
        # scanline spans: the rows whose pixel centre lies in the facet
        r0 = np.clip(np.ceil(py.min(1) - 0.5), 0, H).astype(int)
        r1 = np.clip(np.floor(py.max(1) - 0.5), -1, H - 1).astype(int)
        nrow = np.where(ok, np.maximum(r1 - r0 + 1, 0), 0)
        hit = np.zeros(len(fs), bool)

        def fill(idx):
            """Rasterise the facets idx (scanline spans, vectorised) and z-test them into the buffers."""
            n = nrow[idx]
            fi = np.repeat(idx, n)
            if not len(fi):
                return
            row = r0[fi] + (np.arange(len(fi)) - np.repeat(np.cumsum(n) - n, n))
            yc = row + 0.5
            xl = np.full(len(fi), np.inf)
            xr = np.full(len(fi), -np.inf)
            for i, j in ((0, 1), (1, 2), (2, 0)):      # where the row crosses each edge (half-open in y)
                y0_, y1_, x0_, x1_ = py[fi, i], py[fi, j], px[fi, i], px[fi, j]
                cross = ((y0_ <= yc) & (yc < y1_)) | ((y1_ <= yc) & (yc < y0_))
                xc = x0_ + (yc - y0_) * (x1_ - x0_) / np.where(y1_ != y0_, y1_ - y0_, 1.0)
                xl = np.where(cross, np.minimum(xl, xc), xl)
                xr = np.where(cross, np.maximum(xr, xc), xr)
            c0 = np.clip(np.ceil(xl - 0.5), 0, W).astype(int)
            c1 = np.clip(np.floor(xr - 0.5), -1, W - 1).astype(int)
            m = np.where(np.isfinite(xl) & np.isfinite(xr), np.maximum(c1 - c0 + 1, 0), 0)
            pf = np.repeat(fi, m)
            if not len(pf):
                return
            colx = np.repeat(c0, m) + (np.arange(len(pf)) - np.repeat(np.cumsum(m) - m, m))
            rowx = np.repeat(row, m)
            z = np.round(za[pf] * (colx + 0.5) + zb[pf] * (rowx + 0.5) + zc[pf])
            pix = rowx * W + colx
            front = z > zbuf[pix]                       # drop what is behind the buffer already
            pix, z, pf = pix[front][::-1], z[front][::-1], pf[front][::-1]
            np.maximum.at(zbuf, pix, z)
            win = z == zbuf[pix]                        # reversed: on a tie the earlier facet is written last
            cbuf[pix[win]] = col[pf[win]]
            pf = pf[win]
            hit[pf] = True
        # chunks of about BATCH_SAMPLES pixels (estimated from the bounding boxes)
        est = nrow * np.maximum(px.max(1) - px.min(1), 1)
        cut = np.searchsorted(np.cumsum(est), np.arange(1, int(est.sum() // BATCH_SAMPLES) + 2) * BATCH_SAMPLES)
        start = 0
        for c in list(cut) + [len(fs)]:
            c = max(int(c), start + 1)
            if start >= len(fs):
                break
            fill(np.arange(start, min(c, len(fs))))
            start = c
        drawn = int(hit.sum())
        # visible edges: points of the shape edges not behind the z-buffer, 2 px wide
        tol = diag * 2e-3 / zeps
        zimg = zbuf.reshape(H, W)
        cimg = cbuf.reshape(H, W, 3)
        for pl in es:
            q = np.array(pl, float)
            ex, ey = to_px(q @ X, q @ U)
            ez = (q @ D) / zeps
            n = np.maximum(np.ceil(np.hypot(np.diff(ex), np.diff(ey))), 1).astype(int)
            t = np.concatenate([np.linspace(0, 1, m + 1) for m in n])
            seg = np.repeat(np.arange(len(n)), n + 1)
            xx = ex[seg] + (ex[seg + 1] - ex[seg]) * t
            yy = ey[seg] + (ey[seg + 1] - ey[seg]) * t
            zz = ez[seg] + (ez[seg + 1] - ez[seg]) * t
            ix, iy = xx.astype(int), yy.astype(int)
            inn = (ix >= 0) & (ix < W - 1) & (iy >= 0) & (iy < H - 1)
            ix, iy, zz = ix[inn], iy[inn], zz[inn]
            vis = zz >= zimg[iy, ix] - tol
            for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                cimg[iy[vis] + dy, ix[vis] + dx] = (25, 25, 30)
    img_arr = cbuf.reshape(RENDER_H, SS, RENDER_W, SS, 3).mean(axis=(1, 3)).round().astype(np.uint8)
    data = np.ascontiguousarray(img_arr).tobytes()
    img = QtGui.QImage(data, RENDER_W, RENDER_H, RENDER_W * 3, QtGui.QImage.Format_RGB888).copy()
    p = QtGui.QPainter(img)
    p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
    f = QtGui.QFont(font)
    f.setPixelSize(30)
    p.setFont(f)
    p.setPen(QtGui.QColor(60, 60, 60))
    for i, t in enumerate(lines + ([f"{scale:.3g} px/mm"] if fs else [])):
        p.drawText(40, 60 + i * 40, t)
    if preview:
        f.setPixelSize(64)
        f.setBold(True)
        p.setFont(f)
        p.setPen(QtGui.QColor(192, 0, 0))
        p.drawText(QtCore.QRect(0, 30, RENDER_W - 40, 90), int(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter),
                   "PREVIEW")
    p.end()
    if not img.save(path, "PNG"):
        raise RuntimeError(f"QImage.save failed: {path}")
    return drawn


def qt_font(path):
    """A QGuiApplication (offscreen platform) and the family of the pinned font; fails when the
    font does not load (no silent fallback to a system font)."""
    from PySide import QtGui
    app = QtGui.QGuiApplication.instance()
    if app is None:
        app = QtGui.QGuiApplication([])
    if not isinstance(app, QtGui.QGuiApplication):
        raise RuntimeError("a QCoreApplication runs already; the renderings need a QGuiApplication")
    fid = QtGui.QFontDatabase.addApplicationFont(path)
    fams = QtGui.QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
    if not fams:
        raise RuntimeError(f"the pinned font {path} does not load in Qt; the renderings need it")
    return app, fams[0]


try:
    import Import
    import Mesh
    import MeshPart
    import Part
    for d in list(App.listDocuments().values()):
        App.closeDocument(d.Name)
    App.openDocument(os.environ["XD_SKELETON"])
    top = App.openDocument(os.environ["XD_TOP"])
    for d in list(App.listDocuments().values()):
        if getattr(d, "Partial", False):
            d.restore()
    for d in App.listDocuments().values():
        d.recompute()
    variant = os.environ.get("XD_VARIANT", "")
    dest = os.environ["XD_OUT"]
    name = os.path.splitext(os.path.basename(os.environ["XD_TOP"]))[0]
    asm = next(o for o in top.Objects if is_asm(o) and o.TypeId == "Assembly::AssemblyObject")
    rows = []
    walk(asm, variant, [], rows, App.Placement())
    files, warnings, embossed = [], [], {}
    kids = [c for c in asm.Group if c.TypeId.startswith("App::Link") and present(c, variant)
            and not (c.getLinkedObject(True) and c.getLinkedObject(True).Document.FileName.endswith("-skeleton.FCStd"))]
    # STEP of the assembly (the present links, with their structure)
    step = os.path.join(dest, f"{name}.step")
    Import.export(kids, step)
    files.append(step)
    # printed parts: 3MF and STL, embossed
    os.makedirs(os.path.join(dest, "parts"), exist_ok=True)
    done = set()
    for r in rows:
        t = r["_obj"]
        key = (r["file"], r["object"])
        if not r["PrintProfile"] or key in done:
            continue
        done.add(key)
        stem = os.path.splitext(os.path.basename(r["file"]))[0]
        shape, info = emboss(t, os.environ["XD_SHORT"], os.environ["XD_FONT"])
        if shape is None:
            raise RuntimeError(f"{os.path.basename(r['file'])}#{t.Name}: {info}")
        embossed[stem] = info
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.02, AngularDeflection=0.1, Relative=False)
        for ext in ("stl", "3mf"):
            p = os.path.join(dest, "parts", f"{stem}.{ext}")
            mesh.write(p)
            files.append(p)
    # views of the assembly and the exploded view
    shapes = [c.Shape.copy() for c in kids]
    comp = Part.makeCompound(shapes)
    os.makedirs(os.path.join(dest, "views"), exist_ok=True)
    edges = {}
    for v, view in VIEWS.items():
        svg, n = view_svg(comp, view, v, top)
        edges[v] = n
        p = os.path.join(dest, "views", f"{v}.svg")
        with open(p, "w") as f:
            f.write(svg)
        files.append(p)
    moves = json.loads(os.environ.get("XD_EXPLODE") or "{}")
    cb = comp.BoundBox
    center = cb.Center
    exploded, lines, used = [], [], {}
    for c, s in zip(kids, shapes):
        if moves:
            mv = App.Vector(*moves.get(c.Name, (0, 0, 0)))
        else:                               # automatic: away from the assembly's centre
            dv = s.BoundBox.Center - center
            mv = dv * 1.0 if dv.Length > 1e-6 else App.Vector(0, 0, 0)
        used[c.Name] = [round(x, 4) for x in (mv.x, mv.y, mv.z)]
        m = s.copy()
        m.translate(mv)
        exploded.append(m)
        if mv.Length > 1e-6:
            lines.append(Part.makeLine(s.BoundBox.Center, s.BoundBox.Center + mv))
    svg, n = view_svg(Part.makeCompound(exploded + lines), VIEWS["iso"], "exploded", top)
    p = os.path.join(dest, "exploded.svg")
    with open(p, "w") as f:
        f.write(svg)
    files.append(p)
    edges["exploded"] = n
    # renderings: shaded, z-buffer (no OpenGL), with the version, the scale and the preview marking
    _app, family = qt_font(os.environ["XD_FONT"])
    os.makedirs(os.path.join(dest, "renderings"), exist_ok=True)
    sc = scene(asm, rows, kids)
    painted = {}
    label = [f"{name}  variant {variant or 'all'}", os.environ.get("XD_VERSION", "")]
    ortho = min(fit_scale(sc, VIEWS[v]) for v in ("front", "top", "right"))   # one scale for the three
    scales = {v: ortho if v != "iso" else fit_scale(sc, VIEWS[v]) for v in VIEWS}
    for v, view in VIEWS.items():
        p = os.path.join(dest, "renderings", f"{v}.png")
        painted[v] = render(sc, view, p, label + [v], os.environ.get("XD_RELEASE") != "1", family, scales[v])
        files.append(p)
    out = {"ok": True, "files": [os.path.relpath(f, dest) for f in files], "edges": edges, "painted": painted,
           "facets": len(sc[0]), "render_scale": {k: round(x, 4) for k, x in scales.items()}, "embossed": embossed,
           "moves": used, "bbox": [round(x, 4) for x in (cb.XMin, cb.YMin, cb.ZMin, cb.XMax, cb.YMax, cb.ZMax)],
           "bom": [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows], "warnings": warnings}
    for d in list(App.listDocuments().values()):
        App.closeDocument(d.Name)
except Exception:
    out["error"] = traceback.format_exc()
if res:
    with open(res, "w") as f:
        json.dump(out, f, indent=1)
