// Read an ELK JSON graph on stdin, write the laid-out graph on stdout.
// usage: node elk_layout.mjs NODE_PREFIX     (NODE_PREFIX = <ws>/.venv/opt/node, holds elkjs)
import { createRequire } from "module";
const require = createRequire(process.argv[2] + "/");
const ELK = require("elkjs/lib/elk.bundled.js");
const elk = new ELK();
let buf = "";
process.stdin.on("data", (d) => (buf += d));
process.stdin.on("end", async () => {
  try {
    const out = await elk.layout(JSON.parse(buf));
    process.stdout.write(JSON.stringify(out));
  } catch (e) {
    // the bundled elkjs is minified: print the message, not a line of minified source
    process.stderr.write(`elkjs: ${e && (e.message || e.toString())}\n`);
    process.exit(1);
  }
});
