// Render drawio diagrams to SVG with drawio's own viewer JS in headless system Firefox.
// usage: node render_svg.mjs NODE_PREFIX VIEWER_JS FIREFOX PROFILE_DIR IN1.xml OUT1.svg [IN2.xml OUT2.svg ...]
// Each IN is an uncompressed <mxfile>; each OUT gets the bare <svg> (no content attribute).
// One browser start for all views (the start costs most of the time).
import { createRequire } from "module";
import fs from "fs";
const [nodeDir, viewerJs, firefox, profile, ...pairs] = process.argv.slice(2);
const require = createRequire(nodeDir + "/");
const puppeteer = require("puppeteer-core");

const browser = await puppeteer.launch({
  browser: "firefox", executablePath: firefox, headless: true, userDataDir: profile,
});
try {
  const page = await browser.newPage();
  await page.setContent('<!doctype html><html><body><div id="c"></div></body></html>');
  await page.addScriptTag({ content: fs.readFileSync(viewerJs, "utf8") });
  for (let i = 0; i < pairs.length; i += 2) {
    const svg = await page.evaluate((xml) => {
      const doc = mxUtils.parseXml(xml);
      const diagram = doc.documentElement.getElementsByTagName("diagram")[0];
      const model = diagram.getElementsByTagName("mxGraphModel")[0];
      const container = document.getElementById("c");
      container.innerHTML = "";
      const viewer = new GraphViewer(container, model, { nav: false, toolbar: null });
      // Graph.getSvg(background, scale, border, nocrop, crisp, ignoreSelection, showText, imgExport, linkTarget, hasShadow)
      const root = viewer.graph.getSvg("#ffffff", 1, 10, false, null, true, null, null, "_top");
      return mxUtils.getXml(root);
    }, fs.readFileSync(pairs[i], "utf8"));
    fs.writeFileSync(pairs[i + 1], svg);
  }
} finally {
  await browser.close();
}
