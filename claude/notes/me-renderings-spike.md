# ME renderings spike (task 5.30)

Agent spike, 2026-11-17, about 30 minutes. **Update after the spike:** the owner then allowed Blender as
an optional local renderer (a separate change on `feat/me-renderings-blender`); the renderer described
here (`zbuffer`, XD-ADR-0147) is the fallback when Blender is absent. FreeCAD 1.1.4 (Arch package `freecad 1.1.4-3`, Coin
4.0.10, pivy 0.6.11, Qt 6.12.0, Mesa 26.2.6). Owner decision before the spike: **no Blender**;
renderings use FreeCAD's own means only. Scripts and logs under `build/spike-renderings/` (not
committed): `scripts/snap.py`, `scripts/coin.py`, `scripts/qtrender.py`, `out/`. Input: the canary
assembly of robarm-me (`assemblies/canary-assembly/`, origin/main 246ada0). Every run went through
`curatrix run --use freecad -t <short>` (workspace-local FreeCAD config, memory limit).

## Verdict

| Way | Verdict | Evidence |
|---|---|---|
| Render workbench | **No-go** | not installed; an addon that only writes scenes for an external renderer (POV-Ray, LuxCore, Appleseed, Cycles = Blender, OSPRay). None is installed (`which povray luxcoreui appleseed.cli`), each would be a new system package or Blender |
| Coin3D snapshot in the GUI binary, `QT_QPA_PLATFORM=offscreen` (`View3DInventorPy.saveImage`) | **No-go** | runs (0.04 s per view) but every PNG is blank white: `QOpenGLWidget is not supported on this platform` (`out/gui-offscreen/`) |
| Same with `QT_QPA_PLATFORM=minimalegl` | **No-go** | `Could not create the egl surface: error = 0x300b`, core dump (`out/gui-minimalegl/log.txt`) |
| pivy `SoOffscreenRenderer` in `FreeCADCmd` | **No-go** | `Coin warning in glxglue_context_create_software(): Couldn't create GLX context`, `render()` returns 0 (`out/coin-offscreen/`, `out/coin-minimalegl/`); Coin is built for GLX and needs an X server |
| **FreeCAD tessellation, drawn without OpenGL** | **Go** | `FreeCADCmd`, offscreen Qt: the canary in 4 PNGs in under a second (`out/qt/`); the first try painted facets back to front with `QPainter` and showed sorting errors on parts that touch or cross; a z-buffer in numpy (a dependency of the FreeCAD package) fixed that |

Not tried: the Qt platform plugins `eglfs` (needs a DRM/KMS device, i.e. direct access to the
graphics card, not there in CI or a container) and `vnc` (raster only, so `QOpenGLWidget` has no GL
either), and OSMesa (Coin 4.0.10 here is built for GLX; Mesa's OSMesa would be a separate build of
Coin, i.e. a system package). They fail for the same reason as the tries above: no GL context
without a display.

A headless OpenGL context would need an X server (Xvfb is not installed and would be a system
package) or an EGL setup that Qt's platform plugins do not give here; both would also be needed in
CI. Not pursued, because the fallback below needs no GL at all.

The first GUI run hung after the script raised (the `faulthandler` call failed on a Qt stdout
without `fileno`, so `os._exit(0)` was never reached) until curatrix's timeout: in the GUI binary,
catch everything and always end with `os._exit(0)`, as the FreeCAD spike said.

## What `curatrix cam` does now

`templates/freecad-asm/cam-asm.py`, after the TechDraw views, in the same `FreeCADCmd` process:

1. The shape of every present leaf part in assembly coordinates (`Part.getShape(asm, "<link path>.")`),
   tessellated by `MeshPart.meshFromShape` (deflection 1/2000 of the assembly diagonal); the
   shape's edges discretized.
2. Per view (front, top, right, iso: the directions of the TechDraw views, z up): each facet shaded
   flat (Lambert, one light from the viewer's upper left, 30 % ambient), rasterised as scanline
   spans (numpy, vectorised in chunks of about 2 million pixels) into a z-buffer at 3200 x 2400 px;
   no back-face culling (a solid with flipped normals still renders); visible edges (not behind the
   z-buffer; without seam edges, such as the line along a cylinder) 2 px dark on top; averaged down
   to 1600 x 1200 (anti-aliasing). Front, top and right share one scale (the smallest that fits all
   three), iso has its own; the scale in px/mm is written on the image and into `cam.json`
   (`render_scale`).
3. A `QImage` of that, `QPainter` writes assembly, variant, full version, view and scale (pinned
   DejaVu Sans Mono; the run fails if it does not load), and `PREVIEW` in red unless a release;
   `QImage.save` writes the PNG.

Colours come from the BOM kind (printed orange, board green, fastener grey, bought dark grey, other
blue, a bit darker for every second and third part), not from the document's colours: those live
in `GuiDocument.xml`, which `FreeCADCmd` does not load. Reading them is a follow-up if the owner
wants it.

Names: `renderings/front.png`, `top.png`, `right.png`, `iso.png`; `right` is the side view, as in
`views/` and the drawing. `cam.json` lists them per variant (`per_variant.<v>.renderings`) and the
method and marking (`renderings`). A rendering without a drawn facet fails the run.

Limits: orthographic and flat-shaded, no perspective, shadows or materials; coplanar faces of two
parts that overlap (a collision) show the part drawn first; edges of faces that lie in another
part's face can show through (tolerance 1/500 of the diagonal).

Cost (this machine, `curatrix run --use freecad`, the review's stress scenes): a few boxes about 1 s
per view (mostly the full-size buffers); 60 filleted tubes with 272 000 facets: tessellation 3.4 s,
then 2.7 to 6.5 s per view (the side view, with the most overdraw, is the slowest), about 740 MB
peak. The first version sampled every facet's bounding box and took 11 to 13 s per view (30 s for the
side view); the review measured it. The time grows with the drawn pixels times the overdraw and with
the facet count, so a full arm with several variants stays well inside the `freecad` limit of 10
minutes; `cam.json` records the facet count per variant (`facets`) to show the growth.

## User dirs

`~/.config/FreeCAD`, `~/.local/share/FreeCAD`, `~/.cache/FreeCAD`: modification times unchanged by
the spike and the implementation (newest entries 2026-11-17 00:23, before this task started at 17:03).
FreeCAD reported the workspace config dir (`GuiUp 1 cfg .../ws-syseng/.xdmod/freecad/config/FreeCAD/v1-1/`).
