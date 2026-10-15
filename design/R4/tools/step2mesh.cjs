// Convert SmartVio STEP parts to a compact mesh bundle for three.js (positions in mm, assembly coords).
const fs = require('fs'), path = require('path');
const occtimportjs = require('occt-import-js');
(async () => {
  const occt = await occtimportjs();
  const M = process.argv[2], out = process.argv[3];
  const files = [];
  for (const f of fs.readdirSync(path.join(M, 'cad'))) if (f.endsWith('.step') && !/assembly|reference_components/.test(f)) files.push(['part', f.replace('.step', ''), path.join(M, 'cad', f)]);
  for (const f of fs.readdirSync(path.join(M, 'reference/components'))) if (f.endsWith('.step')) files.push(['ref', f.replace('.step', ''), path.join(M, 'reference/components', f)]);
  const parts = []; const bufs = []; let off = 0;
  for (const [kind, name, file] of files) {
    const res = occt.ReadStepFile(fs.readFileSync(file), { linearUnit: 'millimeter', linearDeflectionType: 'absolute_value', linearDeflection: kind === 'part' ? 0.02 : 0.05, angularDeflection: 0.25 });
    if (!res.success) { console.log('FAIL', name); continue; }
    let pos = [], idx = [], base = 0;
    for (const m of res.meshes) {
      const p = m.attributes.position.array, ix = m.index.array;
      for (let i = 0; i < p.length; i++) pos.push(p[i]);
      for (let i = 0; i < ix.length; i++) idx.push(ix[i] + base);
      base += p.length / 3;
    }
    const pa = Float32Array.from(pos), ia = Uint32Array.from(idx);
    parts.push({ kind, name, posOff: off, posLen: pa.length, idxOff: off + pa.byteLength, idxLen: ia.length });
    bufs.push(Buffer.from(pa.buffer), Buffer.from(ia.buffer)); off += pa.byteLength + ia.byteLength;
  }
  fs.writeFileSync(out + '.bin', Buffer.concat(bufs));
  fs.writeFileSync(out + '.json', JSON.stringify(parts));
  console.log('parts', parts.length, 'bytes', off);
})();
