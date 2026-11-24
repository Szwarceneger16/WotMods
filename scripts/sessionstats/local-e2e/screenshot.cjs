'use strict';

const { inflateSync } = require('node:zlib');

const pngSignature = Buffer.from('89504e470d0a1a0a', 'hex');
const crcTable = Uint32Array.from({length: 256}, (_, byte) => {
  for (let bit = 0; bit < 8; bit++) byte = (byte >>> 1) ^ (byte & 1 ? 0xedb88320 : 0);
  return byte;
});

function viewportForPanel(width, height) {
  return {width: width + 20, height: height + 20};
}

function crc32(bytes, start, end) {
  let crc = 0xffffffff;
  for (let i = start; i < end; i++) crc = (crc >>> 8) ^ crcTable[(crc ^ bytes[i]) & 255];
  return (crc ^ 0xffffffff) >>> 0;
}

function validPng(bytes, {width, height}) {
  if (!bytes.subarray(0, 8).equals(pngSignature)) return false;
  const data = [];
  let dataClosed = false;
  let channels = 0;
  let offset = 8;
  while (offset + 12 <= bytes.length) {
    const length = bytes.readUInt32BE(offset);
    const type = bytes.toString('latin1', offset + 4, offset + 8);
    const body = offset + 8;
    const end = body + length;
    if (end + 4 > bytes.length || crc32(bytes, offset + 4, end) !== bytes.readUInt32BE(end)) return false;
    if (offset === 8) {
      if (type !== 'IHDR' || length !== 13 || bytes.readUInt32BE(body) !== width ||
          bytes.readUInt32BE(body + 4) !== height || bytes[body + 8] !== 8 ||
          ![2, 6].includes(bytes[body + 9]) || bytes[body + 10] || bytes[body + 11] || bytes[body + 12]) return false;
      channels = bytes[body + 9] === 2 ? 3 : 4;
    } else if (type === 'IDAT') {
      if (dataClosed) return false;
      data.push(bytes.subarray(body, end));
    } else if (type === 'IEND') {
      if (length || end + 4 !== bytes.length || !data.length) return false;
      const stride = width * channels + 1;
      const compressed = Buffer.concat(data);
      try {
        const {buffer, engine} = inflateSync(compressed, {maxOutputLength: height * stride, info: true});
        if (buffer.length !== height * stride || engine.bytesWritten !== compressed.length) return false;
        for (let row = 0; row < buffer.length; row += stride) if (buffer[row] > 4) return false;
        return true;
      } catch { return false; }
    } else {
      if (!/^[a-z][A-Za-z][A-Z][A-Za-z]$/.test(type)) return false;
      dataClosed = data.length > 0;
    }
    offset = end + 4;
  }
  return false;
}

function readJpegTables(bytes, start, end, quantization, huffman) {
  if (start === end) return false;
  while (start < end) {
    const id = bytes[start++];
    if (quantization) {
      if (id > 3 || start + 64 > end) return false;
      quantization.add(id);
      start += 64;
    } else {
      if ((id & 0xf0) > 0x10 || (id & 15) > 3 || start + 16 > end) return false;
      let available = 1, count = 0;
      for (let length = 0; length < 16; length++) {
        const codes = bytes[start++];
        available = available * 2 - codes;
        count += codes;
        if (available <= 0) return false;
      }
      if (!count || count > 256 || start + count > end) return false;
      huffman.add(id);
      start += count;
    }
  }
  return start === end;
}

function validJpegScan(bytes, start, minimumBytes) {
  // Chromium writes one baseline scan with stuffed 0xff bytes and no restart
  // markers. Inspect its encoded structure without building a decoded bitmap.
  let stuffed = 0;
  for (let marker = bytes.indexOf(0xff, start); marker !== -1; marker = bytes.indexOf(0xff, marker + 2)) {
    if (bytes[marker + 1] === 0) { stuffed++; continue; }
    return bytes[marker + 1] === 0xd9 && marker + 2 === bytes.length && marker - start - stuffed >= minimumBytes;
  }
  return false;
}

function validJpeg(bytes, {width, height}) {
  if (bytes[0] !== 0xff || bytes[1] !== 0xd8) return false;
  const quantization = new Set(), huffman = new Set(), components = new Map();
  let maxH = 0, maxV = 0, blocks = 0;
  for (let offset = 2; offset + 4 <= bytes.length;) {
    if (bytes[offset] !== 0xff) return false;
    while (bytes[offset + 1] === 0xff) offset++;
    if (offset + 4 > bytes.length) return false;
    const marker = bytes[offset + 1];
    const length = bytes.readUInt16BE(offset + 2);
    const start = offset + 4, end = start + length - 2;
    if (length < 2 || end > bytes.length) return false;
    if (marker === 0xc0) {
      if (components.size || length !== 17 || bytes[start] !== 8 || bytes.readUInt16BE(start + 1) !== height ||
          bytes.readUInt16BE(start + 3) !== width || bytes[start + 5] !== 3) return false;
      for (let component = start + 6; component < end; component += 3) {
        const id = bytes[component], sampling = bytes[component + 1];
        const h = sampling >>> 4, v = sampling & 15;
        if (components.has(id) || h < 1 || h > 4 || v < 1 || v > 4) return false;
        components.set(id, bytes[component + 2]);
        maxH = Math.max(maxH, h);
        maxV = Math.max(maxV, v);
        blocks += h * v;
      }
    } else if (marker === 0xdb || marker === 0xc4) {
      if (!readJpegTables(bytes, start, end, marker === 0xdb ? quantization : null, huffman)) return false;
    } else if (marker === 0xda) {
      if (components.size !== 3 || length !== 12 || bytes[start] !== components.size ||
          bytes[end - 3] !== 0 || bytes[end - 2] !== 63 || bytes[end - 1] !== 0) return false;
      const scanned = new Set();
      for (let component = start + 1; component < end - 3; component += 2) {
        const id = bytes[component], table = bytes[component + 1];
        if (scanned.has(id) || !quantization.has(components.get(id)) ||
            !huffman.has(table >>> 4) || !huffman.has(0x10 | (table & 15))) return false;
        scanned.add(id);
      }
      // Each block requires at least a DC symbol and an AC symbol.
      const units = Math.ceil(width / (8 * maxH)) * Math.ceil(height / (8 * maxV));
      return validJpegScan(bytes, end, Math.ceil(units * blocks / 4));
    } else if ((marker < 0xe0 || marker > 0xef) && marker !== 0xfe) {
      return false;
    }
    offset = end;
  }
  return false;
}

function validScreenshot(bytes, filename, viewport) {
  return filename.endsWith('.png') ? validPng(bytes, viewport) : validJpeg(bytes, viewport);
}

module.exports = { validScreenshot, viewportForPanel };
