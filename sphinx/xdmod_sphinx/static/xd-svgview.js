/* xdmod SVG viewer (tiacsys/xdmod#69, decision Q16). SPDX-License-Identifier: Apache-2.0
 *
 * Every <figure class="xd-zoom"> with an inline SVG (schematic sheets, sysml-view block diagrams,
 * harness diagrams, ME drawing sheets) gets:
 *   - pan (drag) and zoom (the +, -, reset buttons) in the page, by the vendored svg-pan-zoom;
 *     the mouse wheel scrolls the page, so a page with many figures stays readable;
 *   - an "Enlarge" button (and a double-click) that opens the SVG in a pop-up using most of the
 *     screen, with pan, zoom and the mouse wheel; Esc, the close button or a click outside the
 *     picture closes it.
 * Without JavaScript the figure stays a plain inline SVG.
 */
(function () {
  "use strict";
  var MAX_INLINE = 0.8;                       // inline height at most 80% of the window height

  function viewBox(svg) {
    var vb = svg.viewBox && svg.viewBox.baseVal;
    if (vb && vb.width > 0 && vb.height > 0) return vb;
    var w = parseFloat(svg.getAttribute("width")), h = parseFloat(svg.getAttribute("height"));
    if (w > 0 && h > 0) {
      svg.setAttribute("viewBox", "0 0 " + w + " " + h);
      return svg.viewBox.baseVal;
    }
    return null;
  }

  function sizeInline(fig, svg, vb) {
    var w = fig.clientWidth || 800;
    var h = Math.min(w * vb.height / vb.width, window.innerHeight * MAX_INLINE);
    svg.style.width = "100%";
    svg.style.height = Math.max(h, 120) + "px";
  }

  var instances = 0;

  function panZoom(svg, inPopup) {
    var pz = window.svgPanZoom(svg, {
      controlIconsEnabled: true,
      mouseWheelZoomEnabled: inPopup,
      dblClickZoomEnabled: inPopup,
      fit: true,
      center: true,
      minZoom: 0.2,
      maxZoom: 40
    });
    // svg-pan-zoom gives its buttons fixed ids (svg-pan-zoom-zoom-in, ...) in every picture: number them
    var n = ++instances;
    Array.prototype.forEach.call(svg.querySelectorAll('[id^="svg-pan-zoom-"]'), function (el) {
      el.id += "-" + n;
    });
    return pz;
  }

  // The pop-up holds a copy of a picture that is still in the page: its ids get a prefix, and the
  // references to them inside the copy (url(#id), href="#id") follow, so every id stays unique.
  function prefixIds(svg, prefix) {
    var ids = {};
    Array.prototype.forEach.call(svg.querySelectorAll("[id]"), function (el) {
      ids[el.id] = true;
      el.id = prefix + el.id;
    });
    var ref = /url\(\s*['"]?#([^'")\s]+)['"]?\s*\)|^#(.+)$/g;
    Array.prototype.forEach.call(svg.querySelectorAll("*"), function (el) {
      Array.prototype.forEach.call(el.attributes, function (a) {
        if (a.value.indexOf("#") < 0) return;
        var v = a.value.replace(ref, function (m, u, h) {
          var id = u || h;
          if (!ids[id]) return m;            // a link to an anchor of the page (a need) stays
          return u ? "url(#" + prefix + id + ")" : "#" + prefix + id;
        });
        if (v !== a.value) el.setAttributeNS(a.namespaceURI, a.name, v);
      });
    });
  }

  // ------------------------------------------------------------------ pop-up
  var overlay = null, current = null, lastFocus = null;

  function close() {
    if (!overlay || overlay.hidden) return;
    if (current) { current.destroy(); current = null; }
    overlay.querySelector(".xd-svgview-stage").innerHTML = "";
    overlay.hidden = true;
    document.documentElement.classList.remove("xd-svgview-open");
    if (lastFocus) lastFocus.focus();
  }

  function makeOverlay() {
    overlay = document.createElement("div");
    overlay.className = "xd-svgview-overlay";
    overlay.hidden = true;
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.innerHTML = '<div class="xd-svgview-box"><div class="xd-svgview-bar">' +
      '<span class="xd-svgview-title"></span>' +
      '<span class="xd-svgview-hint">drag to pan, wheel or buttons to zoom, Esc to close</span>' +
      '<button type="button" class="xd-svgview-close" aria-label="Close">×</button></div>' +
      '<div class="xd-svgview-stage"></div></div>';
    overlay.addEventListener("click", function (e) { if (e.target === overlay) close(); });
    overlay.querySelector(".xd-svgview-close").addEventListener("click", close);
    document.addEventListener("keydown", function (e) { if (e.key === "Escape") close(); });
    document.body.appendChild(overlay);
  }

  function open(fig) {
    if (!overlay) makeOverlay();
    lastFocus = document.activeElement;
    var cap = fig.querySelector("figcaption");
    overlay.querySelector(".xd-svgview-title").textContent = cap ? cap.textContent : "";
    overlay.setAttribute("aria-label", cap ? cap.textContent : "Enlarged picture");
    var stage = overlay.querySelector(".xd-svgview-stage");
    stage.innerHTML = fig.xdSvgSource;
    var svg = stage.querySelector("svg");
    svg.removeAttribute("id");                 // the page's copy keeps its ids
    prefixIds(svg, "xd-svgview-");
    svg.removeAttribute("width");
    svg.removeAttribute("height");
    svg.style.width = "100%";
    svg.style.height = "100%";
    overlay.hidden = false;
    document.documentElement.classList.add("xd-svgview-open");
    if (viewBox(svg) && window.svgPanZoom) current = panZoom(svg, true);
    overlay.querySelector(".xd-svgview-close").focus();
  }

  // ------------------------------------------------------------------ figures in the page
  function setup(fig) {
    var svg = fig.querySelector(":scope > svg");
    if (!svg) return;
    fig.xdSvgSource = svg.outerHTML;            // the pop-up starts from the untouched picture
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "xd-svgview-enlarge";
    btn.textContent = "Enlarge";
    btn.title = "Open in a large pop-up (or double-click the picture)";
    btn.addEventListener("click", function () { open(fig); });
    fig.insertBefore(btn, fig.firstChild);
    fig.addEventListener("dblclick", function (e) {
      if (!e.target.closest(".svg-pan-zoom-control")) open(fig);
    });
    var vb = viewBox(svg);
    if (!vb || !window.svgPanZoom) return;
    svg.removeAttribute("width");
    svg.removeAttribute("height");
    sizeInline(fig, svg, vb);
    var pz = panZoom(svg, false);
    fig.classList.add("xd-zoom-on");
    window.addEventListener("resize", function () {
      // keep the reader's zoom and the point in the middle of the picture
      var z = pz.getZoom(), pan = pz.getPan(), s0 = pz.getSizes();
      var cx = (s0.width / 2 - pan.x) / s0.realZoom, cy = (s0.height / 2 - pan.y) / s0.realZoom;
      sizeInline(fig, svg, vb);
      pz.resize(); pz.fit(); pz.center();
      pz.zoom(z);
      var s1 = pz.getSizes();
      pz.pan({ x: s1.width / 2 - cx * s1.realZoom, y: s1.height / 2 - cy * s1.realZoom });
    });
  }

  function init() {
    Array.prototype.forEach.call(document.querySelectorAll("figure.xd-zoom"), setup);
  }

  window.xdSvgView = { open: open, close: close };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
