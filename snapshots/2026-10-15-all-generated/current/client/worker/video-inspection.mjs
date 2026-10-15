/* Bounded, dependency-free container inspection for the community upload profile.
 * This is NOT a decoder, virus scanner, or proof that every compressed frame plays.
 * Supported: AVC/AAC ISO-BMFF (including explicit-timing fragments), VP8/VP9/Opus
 * WebM without lacing. Encryption, edit rates, extra tracks and ambiguous timing
 * are deliberately rejected. Container durations supplied by clients are ignored.
 */
export const VIDEO_MAX_BYTES = 20_000_000;
export const VIDEO_MAX_SECONDS = 60;
const MAX_ITEMS = 60_000, MAX_TRACKS = 2, MAX_DEPTH = 12;
export class VideoInspectionError extends Error {
  constructor(code, message, status = 422) { super(message); this.name = 'VideoInspectionError'; this.code = code; this.status = status; }
}
const fail = (code, message, status) => { throw new VideoInspectionError(code, message, status); };
const invalid = message => fail('VIDEO_INVALID', message);
const profile = message => fail('VIDEO_PROFILE', message, 415);
const positive = (n, message) => { if (!Number.isSafeInteger(n) || n <= 0) invalid(message); return n; };
const safe = n => { if (!Number.isSafeInteger(n) || n < 0) invalid('Unsafe media integer.'); return n; };
function dimensions(width, height) {
  if (!Number.isInteger(width) || !Number.isInteger(height) || width < 1 || height < 1 || width > 4096 || height > 4096 || width * height > 8_294_400) fail('VIDEO_LIMIT', 'Video dimensions exceed the supported profile.');
}
function boundedTime(value) { if (!Number.isFinite(value) || value <= 0) invalid('No finite sample duration.'); if (value > VIDEO_MAX_SECONDS + 1e-9) fail('VIDEO_DURATION', 'Video exceeds 60 seconds.'); return value; }
function context(bytes) {
  const b = bytes instanceof Uint8Array ? bytes : bytes instanceof ArrayBuffer ? new Uint8Array(bytes) : null;
  if (!b || b.byteLength < 12) invalid('Video is empty or truncated.');
  if (b.byteLength > VIDEO_MAX_BYTES) fail('VIDEO_LIMIT', 'Video exceeds 20,000,000 bytes.');
  const v = new DataView(b.buffer, b.byteOffset, b.byteLength); let count = 0;
  const need = (p, n, end = b.length) => { if (!Number.isSafeInteger(p) || !Number.isSafeInteger(n) || p < 0 || n < 0 || p + n > end || end > b.length) invalid('Truncated media structure.'); };
  return { b, v, need, item() { if (++count > MAX_ITEMS) fail('VIDEO_LIMIT', 'Too many media structures.'); },
    u16(p) { need(p, 2); return v.getUint16(p); }, u32(p) { need(p, 4); return v.getUint32(p); },
    i32(p) { need(p, 4); return v.getInt32(p); },
    u64(p) { need(p, 8); const n = v.getBigUint64(p); if (n > BigInt(Number.MAX_SAFE_INTEGER)) invalid('Unsafe 64-bit media integer.'); return Number(n); },
    str(p, n) { need(p, n); let s = ''; for (let i = p; i < p + n; i++) s += String.fromCharCode(b[i]); return s; }
  };
}
function boxes(c, start, end, depth = 0) {
  if (depth > MAX_DEPTH) fail('VIDEO_LIMIT', 'Media nesting is too deep.');
  const result = []; let p = start;
  while (p < end) { c.item(); c.need(p, 8, end); let n = c.u32(p), head = 8; const type = c.str(p + 4, 4);
    if (n === 1) { c.need(p, 16, end); n = c.u64(p + 8); head = 16; }
    if (n === 0) n = end - p;
    if (n < head || n > end - p) invalid('Invalid MP4 box size.');
    result.push({ type, start: p, data: p + head, end: p + n, depth }); p += n;
  }
  return result;
}
const children = (c, box) => boxes(c, box.data, box.end, box.depth + 1);
function one(list, type, required = true) { const found = list.filter(b => b.type === type); if (found.length > 1 || (required && found.length !== 1)) invalid(`Missing or repeated ${type}.`); return found[0]; }
function full(c, box, min = 4) { c.need(box.data, min, box.end); return { version: c.b[box.data], flags: c.u32(box.data) & 0xffffff, p: box.data + 4 }; }
function table(c, box, rowBytes, max = MAX_ITEMS) { const f = full(c, box, 8), count = c.u32(f.p); if (count > max || box.end - f.p - 4 !== count * rowBytes) invalid(`Invalid ${box.type} table.`); return { ...f, count, p: f.p + 4 }; }
function descriptors(c, start, end, depth = 0, result = {}) {
  if (depth > 4) invalid('AAC descriptor nesting is too deep.');
  let p = start;
  while (p < end) { c.item(); c.need(p, 2, end); const tag = c.b[p++]; let n = 0, complete = false;
    for (let i = 0; i < 4; i++) { c.need(p, 1, end); const v = c.b[p++]; n = n * 128 + (v & 127); if (!(v & 128)) { complete = true; break; } }
    if (!complete || n > end - p) invalid('Truncated AAC descriptor.'); const finish = p + n;
    if (tag === 3) { c.need(p, 3, finish); const flags = c.b[p + 2]; let q = p + 3; if (flags & 128) q += 2; if (flags & 64) { c.need(q, 1, finish); q += 1 + c.b[q]; } if (flags & 32) q += 2; c.need(q, 0, finish); descriptors(c, q, finish, depth + 1, result); }
    else if (tag === 4) { c.need(p, 13, finish); if (c.b[p] !== 0x40 || (c.b[p + 1] >>> 2) !== 5) profile('Only MPEG-4 AAC audio is supported.'); descriptors(c, p + 13, finish, depth + 1, result); }
    else if (tag === 5) { if (result.asc) invalid('Repeated AAC configuration.'); result.asc = c.b.subarray(p, finish); }
    else if (tag !== 6) profile('Unsupported AAC descriptor.'); p = finish;
  }
  return result;
}
function avcConfig(c, box) {
  let p = box.data; c.need(p, 7, box.end); if (c.b[p] !== 1) profile('Unsupported AVC configuration.');
  const nalBytes = (c.b[p + 4] & 3) + 1; if (nalBytes === 3) profile('Unsupported AVC NAL length size.');
  let count = c.b[p + 5] & 31; p += 6; if (!count) invalid('AVC SPS is missing.');
  for (let i = 0; i < count; i++) { c.need(p, 2, box.end); const n = c.u16(p); p += 2; c.need(p, n, box.end); if (n < 2 || (c.b[p] & 31) !== 7) invalid('Invalid AVC SPS.'); p += n; }
  c.need(p, 1, box.end); count = c.b[p++]; if (!count) invalid('AVC PPS is missing.');
  for (let i = 0; i < count; i++) { c.need(p, 2, box.end); const n = c.u16(p); p += 2; c.need(p, n, box.end); if (n < 2 || (c.b[p] & 31) !== 8) invalid('Invalid AVC PPS.'); p += n; }
  // High-profile configuration extensions are optional; they do not change the
  // explicit NAL length size. Bound them, rather than treating them as frames.
  if (p < box.end) { c.need(p, 4, box.end); const ext = c.b[p + 3]; p += 4; for (let i = 0; i < ext; i++) { c.need(p, 2, box.end); const n = c.u16(p); p += 2; c.need(p, n, box.end); p += n; } if (p !== box.end) invalid('Invalid AVC extension.'); }
  return nalBytes;
}
function sampleDescription(c, stsd, kind) {
  const f = full(c, stsd, 8); if (c.u32(f.p) !== 1) profile('One sample description per track is required.');
  const entries = boxes(c, f.p + 4, stsd.end, stsd.depth + 1); if (entries.length !== 1) invalid('Invalid sample description.'); const e = entries[0];
  c.need(e.data, 8, e.end); if (c.u16(e.data + 6) !== 1) profile('External media references are unsupported.');
  if (kind === 'vide') { if (!['avc1', 'avc3'].includes(e.type)) profile('Only H.264 video is supported in MP4.'); c.need(e.data, 78, e.end); const width = c.u16(e.data + 24), height = c.u16(e.data + 26); dimensions(width, height);
    const cs = boxes(c, e.data + 78, e.end, e.depth + 1); return { width, height, codec: 'h264', nalBytes: avcConfig(c, one(cs, 'avcC')) };
  }
  if (e.type !== 'mp4a') profile('Only AAC audio is supported in MP4.'); c.need(e.data, 28, e.end);
  if (c.u16(e.data + 8) !== 0) profile('Extended audio sample entries are unsupported.');
  const channels = c.u16(e.data + 16); if (channels < 1 || channels > 2) profile('Only mono or stereo audio is supported.');
  const cs = boxes(c, e.data + 28, e.end, e.depth + 1), esds = one(cs, 'esds'); full(c, esds);
  const asc = descriptors(c, esds.data + 4, esds.end).asc; if (!asc || asc.length < 2 || (asc[0] >>> 3) !== 2 || ((asc[0] & 7) * 2 + (asc[1] >>> 7)) >= 13) profile('Only explicit AAC-LC configurations are supported.');
  return { codec: 'aac' };
}
function parseTrack(c, box) {
  const cs = children(c, box), tk = one(cs, 'tkhd'), tf = full(c, tk, 24); let id;
  if (tf.version === 0) id = c.u32(tk.data + 12); else if (tf.version === 1) { c.need(tk.data, 36, tk.end); id = c.u32(tk.data + 20); } else profile('Unsupported track-header version.'); positive(id, 'Invalid track ID.');
  const mdia = children(c, one(cs, 'mdia')), mdhd = one(mdia, 'mdhd'), mf = full(c, mdhd, 24); let timescale;
  if (mf.version === 0) timescale = c.u32(mdhd.data + 12); else if (mf.version === 1) { c.need(mdhd.data, 36, mdhd.end); timescale = c.u32(mdhd.data + 20); } else profile('Unsupported media-header version.'); positive(timescale, 'Invalid track timescale.');
  const h = one(mdia, 'hdlr'); c.need(h.data, 12, h.end); const kind = c.str(h.data + 8, 4); if (!['vide', 'soun'].includes(kind)) profile('Only one video and optional audio track are supported.');
  const stbl = children(c, one(children(c, one(mdia, 'minf')), 'stbl'));
  const edts = one(cs, 'edts', false); if (edts) { const elst = one(children(c, edts), 'elst'); const ef = full(c, elst, 8), n = c.u32(ef.p); if (n > 2 || ![0, 1].includes(ef.version)) profile('Complex edit lists are unsupported.'); const stride = ef.version ? 20 : 12; if (elst.end - ef.p - 4 !== n * stride) invalid('Invalid edit list.'); for (let i = 0; i < n; i++) { const p = ef.p + 4 + i * stride; if (c.u16(p + stride - 4) !== 1 || c.u16(p + stride - 2) !== 0) profile('Only normal-rate edits are supported.'); } }
  return { id, kind, timescale, stbl, ...sampleDescription(c, one(stbl, 'stsd'), kind), samples: 0, duration: 0, decodeEnd: 0, videoSlice: false, keyframe: false };
}
function verifyPayload(c, track, start, size, ranges) {
  positive(size, 'Empty media sample.'); const end = safe(start + size); if (!ranges.some(r => start >= r.data && end <= r.end)) invalid('Sample does not point to complete media data.');
  if (track.kind === 'vide') { let p = start, slice = false, key = false, nals = 0;
    while (p < end) { if (++nals > 4096) fail('VIDEO_LIMIT', 'Too many AVC NAL units.'); c.need(p, track.nalBytes, end); let n = 0; for (let i = 0; i < track.nalBytes; i++) n = n * 256 + c.b[p++]; c.need(p, n, end); if (!n || (c.b[p] & 128)) invalid('Invalid AVC NAL payload.'); const type = c.b[p] & 31; if (type < 1 || type > 12) profile('Unsupported AVC NAL type.'); if (type === 1 || type === 5) { if (n < 2) invalid('Truncated AVC slice.'); slice = true; if (type === 5) key = true; } p += n; }
    if (!slice) invalid('Video sample has no coded picture.'); if (!track.samples && !key) profile('The first video sample must be independently decodable.'); track.videoSlice = true; track.keyframe ||= key;
  } else if (size < 2) invalid('Truncated AAC sample.');
}
function sampleTime(track, dts, delta, offset) {
  positive(delta, 'Sample duration is missing.'); const end = safe(dts + delta); const presentationEnd = end + offset;
  if (!Number.isSafeInteger(presentationEnd)) invalid('Unsafe sample timeline.'); track.duration = Math.max(track.duration, end / track.timescale, presentationEnd / track.timescale); track.decodeEnd = end;
  if (track.duration > VIDEO_MAX_SECONDS + 1e-9) fail('VIDEO_DURATION', 'Video exceeds 60 seconds.'); if (++track.samples > MAX_ITEMS) fail('VIDEO_LIMIT', 'Too many media samples.');
}
function ordinarySamples(c, track, ranges, references) {
  const sizesBox = one(track.stbl, 'stsz'), sf = full(c, sizesBox, 12), fixed = c.u32(sf.p), n = c.u32(sf.p + 4);
  if (n > MAX_ITEMS || sizesBox.end - sf.p - 8 !== (fixed ? 0 : n * 4)) invalid('Invalid MP4 sample-size table.');
  const stts = table(c, one(track.stbl, 'stts'), 8); if (stts.version !== 0) profile('Unsupported sample timing version.');
  const timing = []; let sampleCount = 0; for (let i = 0; i < stts.count; i++) { const p = stts.p + i * 8, count = positive(c.u32(p), 'Empty timing run.'), delta = positive(c.u32(p + 4), 'Zero sample duration.'); sampleCount += count; if (sampleCount > MAX_ITEMS) fail('VIDEO_LIMIT', 'Too many timed samples.'); timing.push({ count, delta }); }
  if (sampleCount !== n) invalid('Sample timing and payload counts disagree.');
  const ctts = one(track.stbl, 'ctts', false), offsets = []; if (ctts) { const ct = table(c, ctts, 8); if (ct.version > 1) profile('Unsupported composition-time version.'); let count = 0; for (let i = 0; i < ct.count; i++) { const p = ct.p + 8 * i, num = positive(c.u32(p), 'Empty composition run.'); count += num; if (count > MAX_ITEMS) fail('VIDEO_LIMIT', 'Too many composition samples.'); const offset = ct.version ? c.i32(p + 4) : c.u32(p + 4); for (let j = 0; j < num; j++) offsets.push(offset); } if (count !== n) invalid('Composition timing count disagrees.'); }
  const map = table(c, one(track.stbl, 'stsc'), 12), chunks = one(track.stbl, 'stco', false), wide = one(track.stbl, 'co64', false); if (!!chunks === !!wide) invalid('Exactly one chunk-offset table is required.'); const ct = table(c, chunks || wide, chunks ? 4 : 8), rows = [];
  for (let i = 0; i < map.count; i++) { const p = map.p + i * 12, first = c.u32(p), count = c.u32(p + 4), desc = c.u32(p + 8); if (!first || first > ct.count || (i ? first <= rows[i - 1].first : first !== 1) || !count || count > MAX_ITEMS || desc !== 1) invalid('Invalid sample-to-chunk map.'); rows.push({ first, count }); }
  if (!n) { if (ct.count || rows.length) invalid('Empty sample table references chunks.'); return 0; }
  if (!rows.length || !ct.count) invalid('Video payload references are missing.');
  let index = 0, row = 0, timeRun = 0, timeLeft = timing[0].count, dts = 0;
  for (let chunk = 1; chunk <= ct.count; chunk++) { while (row + 1 < rows.length && rows[row + 1].first <= chunk) row++; let p = chunks ? c.u32(ct.p + (chunk - 1) * 4) : c.u64(ct.p + (chunk - 1) * 8);
    for (let j = 0; j < rows[row].count; j++) { if (index >= n) invalid('Chunk map exceeds sample count.'); const size = fixed || c.u32(sf.p + 8 + index * 4), delta = timing[timeRun].delta; verifyPayload(c, track, p, size, ranges); references.push({ start: p, end: p + size }); sampleTime(track, dts, delta, offsets[index] || 0); p = safe(p + size); dts = safe(dts + delta); index++; if (!--timeLeft && index < n) timeLeft = timing[++timeRun].count; }
  }
  if (index !== n) invalid('Some media samples are unreferenced.'); return n;
}
function fragments(c, top, tracks, ranges, references, moov) {
  const mvex = one(children(c, moov), 'mvex', false), defaults = new Map(); if (mvex) for (const b of children(c, mvex)) { if (b.type !== 'trex') continue; const f = full(c, b, 24); const id = c.u32(f.p); if (defaults.has(id) || !tracks.some(t => t.id === id) || c.u32(f.p + 4) !== 1) invalid('Invalid fragment defaults.'); defaults.set(id, { duration: c.u32(f.p + 8), size: c.u32(f.p + 12) }); }
  for (const moof of top.filter(b => b.type === 'moof')) { const cs = children(c, moof); one(cs, 'mfhd'); const trafs = cs.filter(b => b.type === 'traf'); if (!trafs.length || trafs.length > MAX_TRACKS) invalid('Invalid fragment track count.');
    for (const traf of trafs) { const ts = children(c, traf), h = one(ts, 'tfhd'), hf = full(c, h, 8), id = c.u32(hf.p), track = tracks.find(t => t.id === id); if (!track) invalid('Fragment references an unknown track.'); if (hf.version || hf.flags & ~0x03003b || hf.flags & 0x010000) profile('Unsupported fragment-header flags.'); let p = hf.p + 4, base;
      if (hf.flags & 1) { c.need(p, 8, h.end); base = c.u64(p); p += 8; } else if (hf.flags & 0x020000) base = moof.start; else profile('Fragment must declare its media-data base.');
      if (hf.flags & 2) { c.need(p, 4, h.end); if (c.u32(p) !== 1) profile('Multiple fragment descriptions are unsupported.'); p += 4; }
      let duration = defaults.get(id)?.duration || 0, size = defaults.get(id)?.size || 0;
      if (hf.flags & 8) { c.need(p, 4, h.end); duration = c.u32(p); p += 4; } if (hf.flags & 16) { c.need(p, 4, h.end); size = c.u32(p); p += 4; } if (hf.flags & 32) p += 4; if (p !== h.end) invalid('Malformed fragment-header fields.');
      const t = one(ts, 'tfdt'), tf = full(c, t, 8); if (tf.flags || tf.version > 1) profile('Unsupported decode-time header.'); c.need(tf.p, tf.version ? 8 : 4, t.end); let dts = tf.version ? c.u64(tf.p) : c.u32(tf.p); if (dts < track.decodeEnd || dts / track.timescale > VIDEO_MAX_SECONDS) invalid('Fragment timeline overlaps or exceeds its bounds.');
      const runs = ts.filter(b => b.type === 'trun'); if (!runs.length) invalid('Fragment contains no samples.'); let cursor;
      for (const run of runs) { const rf = full(c, run, 8); if (rf.version > 1 || rf.flags & ~0x000f05) profile('Unsupported fragment-run flags.'); const n = c.u32(rf.p); if (!n || n > MAX_ITEMS || track.samples + n > MAX_ITEMS) fail('VIDEO_LIMIT', 'Invalid fragment sample count.'); let q = rf.p + 4; if (rf.flags & 1) { c.need(q, 4, run.end); cursor = safe(base + c.i32(q)); q += 4; } else if (cursor === undefined) cursor = base;
        if (rf.flags & 4) q += 4; c.need(q, 0, run.end);
        for (let i = 0; i < n; i++) { let delta = duration, bytes = size, offset = 0; if (rf.flags & 0x100) { c.need(q, 4, run.end); delta = c.u32(q); q += 4; } if (rf.flags & 0x200) { c.need(q, 4, run.end); bytes = c.u32(q); q += 4; } if (rf.flags & 0x400) { c.need(q, 4, run.end); q += 4; } if (rf.flags & 0x800) { c.need(q, 4, run.end); offset = rf.version ? c.i32(q) : c.u32(q); q += 4; }
          verifyPayload(c, track, cursor, bytes, ranges); references.push({ start: cursor, end: cursor + bytes }); sampleTime(track, dts, delta, offset); dts = safe(dts + delta); cursor = safe(cursor + bytes);
        } if (q !== run.end) invalid('Malformed fragment sample fields.');
      }
    }
  }
}
function inspectMP4(c) {
  const top = boxes(c, 0, c.b.length), ftyp = one(top, 'ftyp'), moov = one(top, 'moov'), ranges = top.filter(b => b.type === 'mdat'); c.need(ftyp.data, 8, ftyp.end); if ((ftyp.end - ftyp.data) % 4) invalid('Invalid MP4 brands.');
  const brands = []; for (let p = ftyp.data; p < ftyp.end; p += 4) if (p !== ftyp.data + 4) brands.push(c.str(p, 4)); if (!brands.some(b => /^(isom|iso[2-9]|avc1|mp4[12]|dash|cmf[cs])$/.test(b))) profile('Unsupported MP4 brand.');
  if (!ranges.some(b => b.end > b.data)) invalid('MP4 media data is missing.');
  const tracks = children(c, moov).filter(b => b.type === 'trak').map(b => parseTrack(c, b)); if (!tracks.length || tracks.length > MAX_TRACKS || new Set(tracks.map(t => t.id)).size !== tracks.length || tracks.filter(t => t.kind === 'vide').length !== 1 || tracks.filter(t => t.kind === 'soun').length > 1) profile('One video and optional audio track are required.');
  const references = []; let samples = 0; for (const track of tracks) samples += ordinarySamples(c, track, ranges, references);
  const fragmented = top.some(b => b.type === 'moof'); if (fragmented && samples) profile('Mixed ordinary and fragmented samples are unsupported.'); if (fragmented) fragments(c, top, tracks, ranges, references, moov);
  for (const track of tracks) if (!track.samples || track.kind === 'vide' && (!track.videoSlice || !track.keyframe)) invalid('A declared track has no complete samples.');
  references.sort((a, b) => a.start - b.start); for (let i = 1; i < references.length; i++) if (references[i].start < references[i - 1].end) invalid('Media samples overlap.');
  const video = tracks.find(t => t.kind === 'vide'); return { mime: 'video/mp4', container: 'mp4', videoCodec: 'h264', audioCodec: tracks.some(t => t.kind === 'soun') ? 'aac' : null, duration: boundedTime(Math.max(...tracks.map(t => t.duration))), durationVerification: 'sample-timeline', width: video.width, height: video.height };
}

// EBML IDs retain the marker bit; sizes and block track numbers remove it.
function vint(c, p, end, id = false) {
  c.need(p, 1, end); const first = c.b[p]; if (!first) invalid('Invalid EBML variable integer.'); let length = 1, mask = 128; while (!(first & mask)) { length++; mask >>>= 1; }
  if (length > (id ? 4 : 8)) invalid('EBML integer is too wide.'); c.need(p, length, end); let value = BigInt(id ? first : first & (mask - 1)), unknown = !id && (first & (mask - 1)) === mask - 1;
  for (let i = 1; i < length; i++) { value = value * 256n + BigInt(c.b[p + i]); unknown &&= c.b[p + i] === 255; }
  if (!unknown && value > BigInt(Number.MAX_SAFE_INTEGER)) invalid('Unsafe EBML integer.'); return { value: unknown ? 0 : Number(value), length, unknown };
}
function element(c, p, end, depth = 0) {
  if (depth > MAX_DEPTH) fail('VIDEO_LIMIT', 'EBML nesting is too deep.'); c.item(); const id = vint(c, p, end, true), n = vint(c, p + id.length, end); const data = p + id.length + n.length; if (!n.unknown && n.value > end - data) invalid('Truncated EBML element.'); return { id: id.value, start: p, data, end: n.unknown ? end : data + n.value, unknown: n.unknown, depth };
}
function elements(c, e) { if (e.unknown) invalid('Unexpected unknown-sized element.'); const result = []; for (let p = e.data; p < e.end;) { const v = element(c, p, e.end, e.depth + 1); if (v.unknown) invalid('Unexpected unknown-sized child.'); result.push(v); p = v.end; } return result; }
function unique(es, id, required = false) { const a = es.filter(e => e.id === id); if (a.length > 1 || required && !a.length) invalid('Missing or repeated EBML field.'); return a[0]; }
function uint(c, e) { if (!e || e.end - e.data < 1 || e.end - e.data > 8) invalid('Invalid EBML unsigned integer.'); let n = 0n; for (let p = e.data; p < e.end; p++) n = n * 256n + BigInt(c.b[p]); if (n > BigInt(Number.MAX_SAFE_INTEGER)) invalid('Unsafe EBML unsigned integer.'); return Number(n); }
function float(c, e) { const n = e.end - e.data; if (n !== 4 && n !== 8) invalid('Invalid EBML float.'); const v = n === 4 ? c.v.getFloat32(e.data) : c.v.getFloat64(e.data); if (!Number.isFinite(v)) invalid('Nonfinite EBML float.'); return v; }
function webmTrack(c, e) {
  const es = elements(c, e), number = uint(c, unique(es, 0xd7, true)), type = uint(c, unique(es, 0x83, true)); if (!number || number > 16383 || ![1, 2].includes(type)) profile('Only video and audio WebM tracks are supported.');
  if (unique(es, 0x6d80) || unique(es, 0xe2)) profile('Encoded/encrypted WebM tracks are unsupported.'); const scale = unique(es, 0x23314f); if (scale && float(c, scale) !== 1) profile('Track-specific timestamp scaling is unsupported.');
  const codecE = unique(es, 0x86, true), codec = c.str(codecE.data, codecE.end - codecE.data); const dd = unique(es, 0x23e383), defaultDuration = dd ? uint(c, dd) / 1e9 : 0; if (dd && (defaultDuration <= 0 || defaultDuration > 1)) profile('Unsupported frame duration.');
  const track = { number, type, codec, defaultDuration, count: 0, last: -Infinity, end: 0, keyframe: false, uncertain: false };
  if (type === 1) { if (!['V_VP8', 'V_VP9'].includes(codec)) profile('Only VP8/VP9 video is supported in WebM.'); const video = elements(c, unique(es, 0xe0, true)); track.width = uint(c, unique(video, 0xb0, true)); track.height = uint(c, unique(video, 0xba, true)); dimensions(track.width, track.height); }
  else { if (codec !== 'A_OPUS') profile('Only Opus audio is supported in WebM.'); const privateE = unique(es, 0x63a2, true); c.need(privateE.data, 19, privateE.end); if (c.str(privateE.data, 8) !== 'OpusHead' || c.b[privateE.data + 8] > 15 || ![1, 2].includes(c.b[privateE.data + 9]) || c.b[privateE.data + 18] !== 0 || privateE.end - privateE.data !== 19) profile('Unsupported Opus channel mapping.'); }
  return track;
}
function bits(bytes, start, end) { let p = start * 8; return n => { if (p + n > end * 8) invalid('Truncated compressed frame header.'); let v = 0; for (let i = 0; i < n; i++, p++) v = v * 2 + ((bytes[p >>> 3] >>> (7 - (p & 7))) & 1); return v; }; }
function vpxFrame(c, t, p, end) {
  let key = false;
  if (t.codec === 'V_VP8') { c.need(p, 3, end); const tag = c.b[p] + c.b[p + 1] * 256 + c.b[p + 2] * 65536, partition = tag >>> 5; if (!partition || partition > end - p - 3 || ((tag >>> 1) & 7) > 3) invalid('Invalid VP8 frame header.'); key = !(tag & 1);
    if (key) { c.need(p, 10, end); if (c.str(p + 3, 3) !== '\x9d\x01\x2a') invalid('Invalid VP8 keyframe signature.'); const w = (c.b[p + 6] | c.b[p + 7] << 8) & 0x3fff, h = (c.b[p + 8] | c.b[p + 9] << 8) & 0x3fff; if (w !== t.width || h !== t.height) invalid('VP8 keyframe dimensions disagree.'); }
  } else { const read = bits(c.b, p, end); if (read(2) !== 2) invalid('Invalid VP9 frame marker.'); const profileNo = read(1) + read(1) * 2; if (profileNo !== 0) profile('Only VP9 profile 0 is supported.'); if (read(1)) profile('VP9 show-existing-frame packets are unsupported.'); key = !read(1); read(1); read(1); if (key) { if (read(24) !== 0x498342) invalid('Invalid VP9 keyframe signature.'); const color = read(3); if (color === 7) profile('Unsupported VP9 RGB profile.'); read(1); const w = read(16) + 1, h = read(16) + 1; if (w !== t.width || h !== t.height) invalid('VP9 keyframe dimensions disagree.'); } if (end - p < 3) invalid('Truncated VP9 frame.'); }
  if (!t.count && !key) profile('The first video block must be a keyframe.'); t.keyframe ||= key;
}
function opusDuration(c, p, end) {
  c.need(p, 1, end); const toc = c.b[p], config = toc >>> 3, code = toc & 3; let ms;
  if (config < 12) ms = [10, 20, 40, 60][config & 3]; else if (config < 16) ms = [10, 20][config & 1]; else ms = [2.5, 5, 10, 20][config & 3];
  let count = code === 0 ? 1 : 2, data = p + 1;
  if (code === 3) { c.need(data, 1, end); const flags = c.b[data++]; count = flags & 63; if (!count || flags & 0xc0) profile('Only unpadded constant-rate Opus packets are supported.'); }
  else if (code === 2) { c.need(data, 1, end); let first = c.b[data++]; if (first >= 252) { c.need(data, 1, end); first += c.b[data++] * 4; } if (first > end - data) invalid('Truncated Opus packet.'); }
  if (ms * count > 120 || data >= end) invalid('Invalid Opus packet duration or payload.'); if ((code === 1 || code === 3) && (end - data) % count) invalid('Invalid constant-rate Opus packet sizes.'); return ms * count / 1000;
}
function block(c, e, tracks, timestamp, scale, explicitDuration = 0, simple = true) {
  const number = vint(c, e.data, e.end); if (number.unknown) invalid('Invalid block track.'); const t = tracks.find(t => t.number === number.value); if (!t) invalid('Block references an unknown track.'); let p = e.data + number.length; c.need(p, 3, e.end); const relative = c.v.getInt16(p), flags = c.b[p + 2]; p += 3;
  if (flags & 6) profile('WebM lacing is unsupported.'); if (flags & (simple ? 0x70 : 0xf1)) profile('Unsupported WebM block flags.'); if (p >= e.end) invalid('Empty WebM frame.');
  const time = (timestamp + relative) * scale / 1e9; if (!Number.isFinite(time) || time < -0.2 || time > VIDEO_MAX_SECONDS || time < t.last) invalid('Invalid or reordered WebM timeline.');
  if ((!t.count && time > 1) || (t.count && time - t.last > 1.001)) profile('WebM tracks must start promptly and contain no gaps over one second.');
  if (t.type === 1 && t.uncertain) t.end = Math.max(t.end, time);
  let duration; if (t.type === 1) { vpxFrame(c, t, p, e.end); duration = explicitDuration || t.defaultDuration; t.uncertain = !duration; }
  else { duration = opusDuration(c, p, e.end); if (explicitDuration && Math.abs(explicitDuration - duration) > 0.001) invalid('Opus block duration disagrees with its packet.'); }
  if (!Number.isFinite(duration) || duration < 0 || duration > 1 || !duration && !t.uncertain) profile('Unsupported block duration.');
  t.last = time; t.end = Math.max(t.end, time + duration); if (++t.count > MAX_ITEMS) fail('VIDEO_LIMIT', 'Too many WebM frames.');
  if (t.end > VIDEO_MAX_SECONDS + 1e-9) fail('VIDEO_DURATION', 'Video exceeds 60 seconds.');
}
const SEGMENT_IDS = new Set([0x114d9b74, 0x1549a966, 0x1654ae6b, 0x1f43b675, 0x1c53bb6b, 0x1254c367, 0x1043a770, 0x1941a469]);
function cluster(c, e, tracks, scale) {
  let p = e.data, timestamp, blocks = 0;
  while (p < e.end) { const child = element(c, p, e.end, e.depth + 1); if (e.unknown && SEGMENT_IDS.has(child.id)) break; if (child.unknown) invalid('Unknown-sized cluster child.');
    if (child.id === 0xe7) { if (timestamp !== undefined || blocks) invalid('Cluster timestamp must precede its blocks.'); timestamp = uint(c, child); }
    else if (child.id === 0xa3 || child.id === 0xa0) { if (timestamp === undefined) invalid('Cluster timestamp is missing.'); if (child.id === 0xa3) block(c, child, tracks, timestamp, scale); else { const es = elements(c, child), b = unique(es, 0xa1, true), duration = unique(es, 0x9b); if (unique(es, 0xa4) || unique(es, 0x75a1)) profile('Codec state changes and block additions are unsupported.'); block(c, b, tracks, timestamp, scale, duration ? uint(c, duration) * scale / 1e9 : 0, false); } blocks++; }
    else if (![0xa7, 0xab, 0xec, 0xbf].includes(child.id)) profile('Unsupported cluster element.'); p = child.end;
  }
  if (!blocks) invalid('Cluster contains no media blocks.'); return p;
}
function inspectWebM(c) {
  const header = element(c, 0, c.b.length); if (header.id !== 0x1a45dfa3 || header.unknown) invalid('WebM EBML header is missing.'); const hs = elements(c, header), doc = unique(hs, 0x4282, true); if (c.str(doc.data, doc.end - doc.data) !== 'webm') profile('Only WebM documents are supported.');
  const segment = element(c, header.end, c.b.length); if (segment.id !== 0x18538067 || segment.end !== c.b.length) invalid('Exactly one complete WebM segment is required.'); let p = segment.data, tracks, scale = 1_000_000, clusters = 0, info = false;
  while (p < segment.end) { const e = element(c, p, segment.end, 1); if (e.unknown && e.id !== 0x1f43b675) invalid('Unexpected unknown-sized segment child.');
    if (e.id === 0x1549a966) { if (info || clusters) invalid('WebM info must precede media.'); info = true; const es = elements(c, e), s = unique(es, 0x2ad7b1); if (s) scale = positive(uint(c, s), 'Invalid WebM timestamp scale.'); if (scale > 1e9) profile('Unsupported WebM timestamp scale.'); /* Duration is intentionally not trusted. */ }
    else if (e.id === 0x1654ae6b) { if (tracks || clusters) invalid('WebM tracks must precede media.'); const entries = elements(c, e).filter(v => v.id === 0xae); if (!entries.length || entries.length > MAX_TRACKS) profile('Unsupported WebM track count.'); tracks = entries.map(v => webmTrack(c, v)); if (new Set(tracks.map(t => t.number)).size !== tracks.length || tracks.filter(t => t.type === 1).length !== 1 || tracks.filter(t => t.type === 2).length > 1) profile('One video and optional audio track are required.'); }
    else if (e.id === 0x1f43b675) { if (!tracks || !info) invalid('WebM initialization is missing.'); p = cluster(c, e, tracks, scale); clusters++; continue; }
    else if (![0x114d9b74, 0x1c53bb6b, 0x1254c367, 0xec, 0xbf].includes(e.id)) profile('Unsupported WebM segment element.'); p = e.end;
  }
  if (!clusters || !tracks || tracks.some(t => !t.count)) invalid('WebM media blocks are missing.'); const video = tracks.find(t => t.type === 1), audio = tracks.find(t => t.type === 2);
  // Browser MediaRecorder often omits Duration and DefaultDuration. Such a file
  // has no exact final video-frame duration. We accept only the conservative
  // short-capture profile: an Opus termination clock, final-frame allowance of
  // one second, and an upper bound safely inside 60s. This is explicitly an
  // estimated upper-bound policy, not a recovered exact presentation duration.
  if (video.uncertain) {
    if (!audio || audio.end + 0.001 < video.last) fail('VIDEO_DURATION_UNCERTAIN', 'WebM needs explicit final-frame timing or an Opus termination clock covering the final video timestamp.');
    video.end = Math.max(video.end, video.last + 1);
    if (video.end > VIDEO_MAX_SECONDS + 1e-9) fail('VIDEO_DURATION_UNCERTAIN', 'The final video frame has no exact duration; the conservative one-second allowance exceeds 60 seconds. Remux or shorten the recording.');
  }
  return { mime: 'video/webm', container: 'webm', videoCodec: video.codec === 'V_VP8' ? 'vp8' : 'vp9', audioCodec: audio ? 'opus' : null, duration: boundedTime(Math.max(...tracks.map(t => t.end))), durationVerification: video.uncertain ? 'block-timeline-conservative' : 'block-timeline', width: video.width, height: video.height, ...(video.uncertain ? { durationPrecision: 'conservative-final-frame-allowance', finalFrameAllowance: 1 } : {}) };
}
export function inspectVideo(bytes, mime) {
  const c = context(bytes), normalized = typeof mime === 'string' ? mime.split(';', 1)[0].trim().toLowerCase() : '';
  if (!['video/mp4', 'video/webm'].includes(normalized)) fail('VIDEO_UNSUPPORTED', 'Only MP4 or WebM video is supported.', 415);
  const isWebM = c.b[0] === 0x1a && c.b[1] === 0x45 && c.b[2] === 0xdf && c.b[3] === 0xa3;
  if (normalized === 'video/webm' ? !isWebM : isWebM) fail('VIDEO_MIME_MISMATCH', 'Declared video type does not match its container.', 415);
  try { return normalized === 'video/mp4' ? inspectMP4(c) : inspectWebM(c); }
  catch (error) { if (error instanceof VideoInspectionError) throw error; throw new VideoInspectionError('VIDEO_INVALID', 'Malformed or unsupported video structure.'); }
}
