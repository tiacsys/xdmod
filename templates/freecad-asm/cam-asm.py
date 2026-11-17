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


# renderings (task 5.30): FreeCAD tessellates the parts; each facet is shaded flat (one light from
# the viewer's upper left) and drawn into a z-buffer (numpy, a FreeCAD dependency) at twice the
# size, the visible edges of the shapes on top, then averaged down; FreeCAD's Qt (QImage, QPainter,
# offscreen platform) writes the text and the PNG. No OpenGL: Coin3D offscreen snapshots and the
# Render workbench do not work headless here (claude/notes/me-renderings-spike.md).
KIND_RGB = {"printed": (232, 140, 40), "board": (40, 125, 70), "fastener": (165, 165, 175),
            "bought": (95, 95, 105), "part": (85, 130, 185)}
RENDER_W, RENDER_H, RENDER_MARGIN, RENDER_TOP, SS = 1600, 1200, 90, 150, 2


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
    """(facets, edges, diagonal) of the present leaf parts: facets as (rgb, closed, 3x3 points,
    normal), edges as polylines (lists of points), both in assembly coordinates."""
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
        closed = bool(s.Solids)
        mesh = MeshPart.meshFromShape(Shape=s, LinearDeflection=max(diag / 2000, 0.005), AngularDeflection=0.2,
                                      Relative=False)
        for f in mesh.Facets:
            fs.append((rgb, closed, [tuple(p) for p in f.Points], tuple(f.Normal)))
        for e in s.Edges:
            try:
                pts = e.discretize(Deflection=max(diag / 4000, 0.002))
            except Exception:
                continue
            if len(pts) > 1:
                es.append([tuple(p) for p in pts])
    return fs, es, diag


def render(sc, view, path, lines, preview, font):
    """Render the scene in a view (VIEWS) into a PNG; returns the number of facets drawn."""
    import numpy as np
    from PySide import QtCore, QtGui
    fs, es, diag = sc
    D = np.array(view[0], float)
    D /= np.linalg.norm(D)
    X = np.array(view[1], float)
    X /= np.linalg.norm(X)
    U = np.cross(D, X)
    light = D + 0.6 * U - 0.4 * X
    light /= np.linalg.norm(light)
    W, H = RENDER_W * SS, RENDER_H * SS
    zbuf = np.full((H, W), -np.inf)
    cbuf = np.full((H, W, 3), 255, np.uint8)
    drawn = 0
    keep = np.zeros(0, bool)
    if fs:
        P = np.array([f[2] for f in fs], float)                       # (n, 3, 3)
        N = np.array([f[3] for f in fs], float)
        nd = N @ D
        keep = np.array([not f[1] for f in fs]) | (nd > 1e-9)        # back faces of solids go
        sx, sy, sz = P @ X, P @ U, P @ D
    if fs and keep.any():
        x0, x1, y0, y1 = sx[keep].min(), sx[keep].max(), sy[keep].min(), sy[keep].max()
        m, top = RENDER_MARGIN * SS, RENDER_TOP * SS
        s = min((W - 2 * m) / max(x1 - x0, 1e-9), (H - 2 * m - top) / max(y1 - y0, 1e-9))
        ox = (W - (x1 - x0) * s) / 2
        oy = m + (H - 2 * m - top - (y1 - y0) * s) / 2

        def to_px(x, y):
            return ox + (x - x0) * s, H - oy - (y - y0) * s
        px, py = to_px(sx, sy)
        shade = 0.3 + 0.7 * np.abs(N @ light)
        zeps = diag * 1e-6                           # coplanar faces: the first one drawn stays (no speckle)
        for k in np.nonzero(keep)[0]:
            xs, ys, zs = px[k], py[k], sz[k]
            xa, xb = max(int(np.floor(xs.min())), 0), min(int(np.ceil(xs.max())), W - 1)
            ya, yb = max(int(np.floor(ys.min())), 0), min(int(np.ceil(ys.max())), H - 1)
            if xa > xb or ya > yb:
                continue
            area = (xs[1] - xs[0]) * (ys[2] - ys[0]) - (xs[2] - xs[0]) * (ys[1] - ys[0])
            if abs(area) < 1e-12:
                continue
            gx, gy = np.meshgrid(np.arange(xa, xb + 1) + 0.5, np.arange(ya, yb + 1) + 0.5)
            w0 = ((xs[1] - gx) * (ys[2] - gy) - (xs[2] - gx) * (ys[1] - gy)) / area
            w1 = ((xs[2] - gx) * (ys[0] - gy) - (xs[0] - gx) * (ys[2] - gy)) / area
            w2 = 1 - w0 - w1
            z = w0 * zs[0] + w1 * zs[1] + w2 * zs[2]
            zsub = zbuf[ya:yb + 1, xa:xb + 1]
            inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6) & (z > zsub + zeps)
            if not inside.any():
                continue
            zsub[inside] = z[inside]
            cbuf[ya:yb + 1, xa:xb + 1][inside] = [int(c * shade[k]) for c in fs[k][0]]
            drawn += 1
        # visible edges: points of the shape edges not behind the z-buffer, 2 px wide
        tol = diag * 2e-3
        for pl in es:
            q = np.array(pl, float)
            ex, ey = to_px(q @ X, q @ U)
            ez = q @ D
            nseg = np.maximum(np.ceil(np.hypot(np.diff(ex), np.diff(ey))), 1).astype(int)
            for a in range(len(q) - 1):
                t = np.linspace(0, 1, nseg[a] + 1)
                xx = ex[a] + (ex[a + 1] - ex[a]) * t
                yy = ey[a] + (ey[a + 1] - ey[a]) * t
                zz = ez[a] + (ez[a + 1] - ez[a]) * t
                ix, iy = xx.astype(int), yy.astype(int)
                ok = (ix >= 0) & (ix < W - 1) & (iy >= 0) & (iy < H - 1)
                ix, iy, zz = ix[ok], iy[ok], zz[ok]
                vis = zz >= zbuf[iy, ix] - tol
                for dx, dy in ((0, 0), (1, 0), (0, 1), (1, 1)):
                    cbuf[iy[vis] + dy, ix[vis] + dx] = (25, 25, 30)
    img_arr = cbuf.reshape(RENDER_H, SS, RENDER_W, SS, 3).mean(axis=(1, 3)).round().astype(np.uint8)
    data = np.ascontiguousarray(img_arr).tobytes()
    img = QtGui.QImage(data, RENDER_W, RENDER_H, RENDER_W * 3, QtGui.QImage.Format_RGB888).copy()
    p = QtGui.QPainter(img)
    p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
    f = QtGui.QFont(font)
    f.setPixelSize(30)
    p.setFont(f)
    p.setPen(QtGui.QColor(60, 60, 60))
    for i, t in enumerate(lines):
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
    """A QGuiApplication (offscreen platform) and the family of the pinned font."""
    from PySide import QtGui
    app = QtGui.QGuiApplication.instance()
    if app is None:
        app = QtGui.QGuiApplication([])
    if not isinstance(app, QtGui.QGuiApplication):
        raise RuntimeError("a QCoreApplication runs already; the renderings need a QGuiApplication")
    fid = QtGui.QFontDatabase.addApplicationFont(path)
    fams = QtGui.QFontDatabase.applicationFontFamilies(fid) if fid >= 0 else []
    return app, (fams[0] if fams else "monospace")


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
    # renderings: shaded, painted with Qt (no OpenGL), with the version and the preview marking
    _app, family = qt_font(os.environ["XD_FONT"])
    os.makedirs(os.path.join(dest, "renderings"), exist_ok=True)
    sc = scene(asm, rows, kids)
    painted = {}
    label = [f"{name}  variant {variant or 'all'}", os.environ.get("XD_VERSION", "")]
    for v, view in VIEWS.items():
        p = os.path.join(dest, "renderings", f"{v}.png")
        painted[v] = render(sc, view, p, label + [v], os.environ.get("XD_RELEASE") != "1", family)
        files.append(p)
    out = {"ok": True, "files": [os.path.relpath(f, dest) for f in files], "edges": edges, "painted": painted,
           "facets": len(sc[0]), "embossed": embossed,
           "moves": used, "bbox": [round(x, 4) for x in (cb.XMin, cb.YMin, cb.ZMin, cb.XMax, cb.YMax, cb.ZMax)],
           "bom": [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows], "warnings": warnings}
    for d in list(App.listDocuments().values()):
        App.closeDocument(d.Name)
except Exception:
    out["error"] = traceback.format_exc()
if res:
    with open(res, "w") as f:
        json.dump(out, f, indent=1)
