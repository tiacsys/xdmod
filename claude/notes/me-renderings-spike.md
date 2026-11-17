# ME renderings spike (task 5.30)

Agent spike, 2026-11-17, about 30 minutes. FreeCAD 1.1.4 (Arch package `freecad 1.1.4-3`, Coin
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
2. Per view (front, top, right, iso: the directions of the TechDraw views, z up): back faces of
   solids dropped, each facet shaded flat (Lambert, one light from the viewer's upper left, 30 %
   ambient), drawn into a z-buffer at 3200 x 2400 px; visible edges (not behind the z-buffer)
   2 px dark on top; averaged down to 1600 x 1200 (anti-aliasing).
3. A `QImage` of that, `QPainter` writes assembly, variant, full version and view (pinned DejaVu
   Sans Mono), and `PREVIEW` in red unless a release; `QImage.save` writes the PNG.

Colours come from the BOM kind (printed orange, board green, fastener grey, bought dark grey, other
blue, a bit darker for every second and third part), not from the document's colours: those live
in `GuiDocument.xml`, which `FreeCADCmd` does not load. Reading them is a follow-up if the owner
wants it.

Names: `renderings/front.png`, `top.png`, `right.png`, `iso.png`; `right` is the side view, as in
`views/` and the drawing. `cam.json` lists them per variant (`per_variant.<v>.renderings`) and the
method and marking (`renderings`). A rendering without a drawn facet fails the run.

Limits: orthographic and flat-shaded, no perspective, shadows or materials; coplanar faces of two
parts that overlap (a collision) show the part drawn first; edges of faces that lie in another
part's face can show through (tolerance 1/500 of the diagonal). Time on the fixture of the tests
(4 parts, 2 variants): the whole `curatrix cam` run 11 s.

## User dirs

`~/.config/FreeCAD`, `~/.local/share/FreeCAD`, `~/.cache/FreeCAD`: modification times unchanged by
the spike and the implementation (newest entries 2026-11-17 00:23, before this task started at 17:03).
FreeCAD reported the workspace config dir (`GuiUp 1 cfg .../ws-syseng/.xdmod/freecad/config/FreeCAD/v1-1/`).
