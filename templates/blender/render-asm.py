# Blender script of `curatrix cam <repo> <asm>` (renderings with Blender, owner decision 2026-11-17;
# refines XD-ADR-0147). Run only through curatrix: `blender -b --factory-startup --offline-mode
# --disable-autoexec --python-exit-code 1 -P render-asm.py`, user paths under <ws>/.xdmod/blender/,
# `blender` limits. Inputs by environment variables:
#   XD_SCENE    the .glb that cam-asm.py wrote (FreeCAD's tessellation, colour by BOM kind, FreeCAD axes)
#   XD_OUT      the renderings folder: front.png, top.png, right.png, iso.png are written there
#   XD_LABEL    JSON list of text lines (assembly and variant, full version); the view and the scale
#               (px/mm; front, top and right share one, as in cam-asm.py) are appended
#   XD_RELEASE  "1" for a release, else PREVIEW in red
#   XD_FONT     the pinned font file
#   XD_SAMPLES  Cycles samples (default 32)
#   XD_THREADS  Cycles threads (curatrix: half the cores; the output does not depend on it)
#   XD_RESULT   the result file: {"ok", "pixels": {view: pixels off the background}, "seconds", ...}
# Deterministic: Cycles on the CPU, fixed samples and seed, no adaptive sampling, no denoiser, no
# time-dependent input; the same input gives the same PNG on the same machine and Blender version.
import json
import os
import time
import traceback

import bpy

res = os.environ.get("XD_RESULT", "")
out = {"ok": False}
# view: (Direction towards the viewer, XDirection to the right); up = Direction x XDirection. The same
# as VIEWS in templates/freecad-asm/cam-asm.py (views, drawing and the z-buffer renderings).
VIEWS = {"front": ((0, -1, 0), (1, 0, 0)), "top": ((0, 0, 1), (1, 0, 0)), "right": ((1, 0, 0), (0, 1, 0)),
         "iso": ((1, -1, 1), (1, 1, 0))}
W, H, MARGIN, TOP = 1600, 1200, 90, 150          # px; TOP: the band of the text lines
BACKGROUND = (1.0, 1.0, 1.0)


def unit(v):
    import mathutils
    v = mathutils.Vector(v)
    v.normalize()
    return v


def setup_scene(samples, threads):
    sc = bpy.context.scene
    sc.render.threads_mode = "FIXED"
    sc.render.threads = threads
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = False
    sc.cycles.use_denoising = False
    sc.cycles.seed = 0
    sc.cycles.use_animated_seed = False
    sc.cycles.max_bounces = 2
    sc.cycles.caustics_reflective = sc.cycles.caustics_refractive = False
    sc.cycles.pixel_filter_type = "BLACKMAN_HARRIS"
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.use_stamp = False
    sc.view_settings.view_transform = "Standard"     # AgX/Filmic would grey the white background
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0.0
    sc.view_settings.gamma = 1.0
    # world: white for camera rays (the background of the image), a dim grey sky for the lighting
    w = bpy.data.worlds.new("xd-world")
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    lp = nt.nodes.new("ShaderNodeLightPath")
    sky = nt.nodes.new("ShaderNodeBackground")
    sky.inputs["Color"].default_value = (0.8, 0.82, 0.85, 1)
    sky.inputs["Strength"].default_value = 0.3
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (*BACKGROUND, 1)
    bg.inputs["Strength"].default_value = 1.0
    mix = nt.nodes.new("ShaderNodeMixShader")
    o = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(sky.outputs[0], mix.inputs[1])
    nt.links.new(bg.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], o.inputs["Surface"])
    # visible edges: Freestyle silhouettes, borders and creases, dark and thin
    sc.render.use_freestyle = True
    sc.render.line_thickness_mode = "ABSOLUTE"
    sc.render.line_thickness = 1.4
    vl = sc.view_layers[0]
    vl.use_freestyle = True
    fs = vl.freestyle_settings
    fs.crease_angle = 2.36                          # 135 degrees: edges of faces that meet at <= 135 deg
    ls = fs.linesets[0] if len(fs.linesets) else fs.linesets.new("xd-edges")
    ls.select_by_visibility = True
    ls.visibility = "VISIBLE"
    ls.select_by_edge_types = True
    ls.select_silhouette = ls.select_border = ls.select_crease = True
    if ls.linestyle is None:
        ls.linestyle = bpy.data.linestyles.new("xd-edges")
    ls.linestyle.color = (0.06, 0.06, 0.07)
    ls.linestyle.thickness = 1.4
    return sc


def import_parts(path):
    bpy.ops.import_scene.gltf(filepath=path)
    objs = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not objs:
        raise RuntimeError(f"{path}: no mesh")
    for o in objs:
        # no shadows: parts that overlap or share a face (a collision, a part on another) would shade
        # each other black where a ray starts inside the other solid; shading stays local, as in the
        # z-buffer renderer
        o.visible_shadow = False
        for p in o.data.polygons:
            p.use_smooth = True
        with bpy.context.temp_override(selected_editable_objects=[o], active_object=o, object=o):
            bpy.ops.object.shade_smooth_by_angle(angle=0.6)     # ~34 deg: curved faces smooth, edges sharp
        for m in o.data.materials:
            b = m.node_tree.nodes.get("Principled BSDF") if m and m.use_nodes else None
            if b is not None:
                b.inputs["Roughness"].default_value = 0.55
                b.inputs["Metallic"].default_value = 0.0
    return objs


def points(objs):
    import numpy as np
    out = []
    for o in objs:
        me = o.data
        a = np.empty(len(me.vertices) * 3, np.float64)
        me.vertices.foreach_get("co", a)
        a = a.reshape(-1, 3)
        mw = np.array(o.matrix_world)
        out.append(a @ mw[:3, :3].T + mw[:3, 3])
    return np.vstack(out)


def fit_scale(pts, view):
    """Pixels per metre at which the parts fill the area below the text band in this view (the
    same rule as fit_scale in cam-asm.py, there in px/mm)."""
    import numpy as np
    D, X = unit(view[0]), unit(view[1])
    U = D.cross(X)
    P = np.asarray(pts)
    sx, sy = P @ np.array(X), P @ np.array(U)
    return min((W - 2 * MARGIN) / max(sx.max() - sx.min(), 1e-9),
               (H - 2 * MARGIN - TOP) / max(sy.max() - sy.min(), 1e-9))


def place_camera(cam, pts, view, s):
    """Orthographic camera along the view at ``s`` px per metre, the parts centred in the area
    below the text band."""
    import mathutils
    import numpy as np
    D, X = unit(view[0]), unit(view[1])
    U = D.cross(X)
    P = np.asarray(pts)
    sx, sy, sz = P @ np.array(X), P @ np.array(U), P @ np.array(D)
    x0, x1, y0, y1 = sx.min(), sx.max(), sy.min(), sy.max()
    ah = H - 2 * MARGIN - TOP
    # the parts' centre goes to the centre of the area below the text band
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    dy_px = (MARGIN + TOP + ah / 2) - H / 2                       # area centre below image centre
    cy_cam = cy + dy_px / s
    depth = sz.max() - sz.min()
    dist = depth + 1.0
    centre = mathutils.Vector(X * cx + U * cy_cam + D * (sz.max() + dist))
    rot = mathutils.Matrix((X, U, D)).transposed()                # columns: camera x, y, z (looks along -z)
    cam.matrix_world = mathutils.Matrix.Translation(centre) @ rot.to_4x4()
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = W / s
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.clip_start = 0.001
    cam.data.clip_end = dist + depth + 1.0
    return D, X, U


def place_lights(lights, D, X, U):
    """Key light from the viewer's upper left (as the z-buffer renderings), fill from the right,
    rim from behind; suns, so the size of the model does not matter."""
    import mathutils
    for obj, vec in zip(lights, (D + 0.9 * U - 0.7 * X, D - 0.3 * U + 0.9 * X, -D + 0.6 * U)):
        v = mathutils.Vector(vec)
        v.normalize()
        obj.rotation_euler = (-v).to_track_quat("-Z", "Y").to_euler()


def mark(path, lines, preview, font):
    """The text lines and the PREVIEW marking, drawn into the PNG by Blender's font module
    (blf into an image buffer; no GPU)."""
    import blf
    import imbuf
    ib = imbuf.load(path)
    fid = blf.load(font)
    if fid < 0:
        raise RuntimeError(f"blf could not load {font}")
    with blf.bind_imbuf(fid, ib):
        blf.size(fid, 30)
        blf.color(fid, 60 / 255, 60 / 255, 60 / 255, 1)
        for i, t in enumerate(lines):
            blf.position(fid, 40, H - (60 + i * 40), 0)
            blf.draw_buffer(fid, t)
        if preview:
            blf.size(fid, 64)
            blf.color(fid, 192 / 255, 0, 0, 1)
            w, h = blf.dimensions(fid, "PREVIEW")
            blf.position(fid, W - 40 - w, H - 75 - h / 2, 0)
            blf.draw_buffer(fid, "PREVIEW")
    imbuf.write(ib, filepath=path)
    blf.unload(font)


def painted(path):
    """Pixels that differ from the background (the parts and their edges)."""
    import numpy as np
    img = bpy.data.images.load(path)
    a = np.empty(img.size[0] * img.size[1] * 4, np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    a = a.reshape(-1, 4)[:, :3]
    return int((np.abs(a - np.array(BACKGROUND)).max(axis=1) > 0.02).sum())


try:
    t0 = time.monotonic()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    samples = int(os.environ.get("XD_SAMPLES") or 32)
    threads = int(os.environ.get("XD_THREADS") or 1)
    sc = setup_scene(samples, threads)
    objs = import_parts(os.environ["XD_SCENE"])
    pts = points(objs)
    cam = bpy.data.objects.new("xd-camera", bpy.data.cameras.new("xd-camera"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    lights = []
    # strengths: a face lit head-on stays at or below its kind colour (Standard view transform)
    for name, energy in (("key", 2.2), ("fill", 0.7), ("rim", 0.8)):
        ld = bpy.data.lights.new(f"xd-{name}", "SUN")
        ld.energy = energy
        lo = bpy.data.objects.new(f"xd-{name}", ld)
        sc.collection.objects.link(lo)
        lights.append(lo)
    label = json.loads(os.environ.get("XD_LABEL") or "[]")
    dest = os.environ["XD_OUT"]
    os.makedirs(dest, exist_ok=True)
    pix, secs = {}, {}
    # front, top and right share one scale (the smallest fit), iso has its own; written on the image
    ortho = min(fit_scale(pts, VIEWS[v]) for v in ("front", "top", "right"))
    scales = {v: ortho if v != "iso" else fit_scale(pts, VIEWS[v]) for v in VIEWS}
    for v, view in VIEWS.items():
        t = time.monotonic()
        D, X, U = place_camera(cam, pts, view, scales[v])
        place_lights(lights, D, X, U)
        p = os.path.join(dest, f"{v}.png")
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        pix[v] = painted(p)
        mark(p, label + [v, f"{scales[v] / 1000:.3g} px/mm"], os.environ.get("XD_RELEASE") != "1",
             os.environ["XD_FONT"])
        secs[v] = round(time.monotonic() - t, 2)
    out = {"ok": True, "pixels": pix, "threads": threads, "seconds": secs,
           "render_scale": {k: round(x / 1000, 4) for k, x in scales.items()}, "total_seconds": round(time.monotonic() - t0, 2),
           "engine": "CYCLES", "device": "CPU", "samples": samples, "seed": 0, "parts": len(objs),
           "blender": bpy.app.version_string}
except Exception:
    out["error"] = traceback.format_exc()
if res:
    with open(res, "w") as f:
        json.dump(out, f, indent=1)
