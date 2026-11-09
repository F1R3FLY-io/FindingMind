// Render every math expression in read/*.html with KaTeX and the book's macro table;
// print any parse error. Usage: node _build/katex-check.js   (from the repo root)
const fs = require('fs'), path = require('path');
const katex = require(path.join(__dirname, '..', 'katex', 'katex.min.js'));
const mj = fs.readFileSync(path.join(__dirname, '..', 'macros.js'), 'utf8');
const macros = JSON.parse(mj.slice(mj.indexOf('=') + 1).trim().replace(/;$/, ''));
let bad = 0, total = 0;
const dir = path.join(__dirname, '..', 'read');
for (const f of fs.readdirSync(dir).filter(f => f.endsWith('.html')).sort()) {
  const h = fs.readFileSync(path.join(dir, f), 'utf8');
  const re = /\\\((.*?)\\\)|\\\[([\s\S]*?)\\\]/g;
  let m;
  while ((m = re.exec(h))) {
    const tex = (m[1] !== undefined ? m[1] : m[2]).replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>');
    total++;
    try { katex.renderToString(tex, {displayMode: m[2] !== undefined, throwOnError: true, macros: {...macros}, trust: true}); }
    catch (e) { bad++; console.log(f + ': ' + e.message.split('\n')[0].slice(0, 160)); }
  }
}
console.log(`katex: ${total} expressions, ${bad} errors`);
process.exit(bad ? 1 : 0);
