/* Exercise shipped preview code with synthetic registry URLs; no client art is bundled. */
const assert = require('assert'), fs = require('fs'), path = require('path'), vm = require('vm');
function sourceFunction(text, name) {
  const start = text.indexOf('    function ' + name + '(');
  const end = text.indexOf('\n    }\n', start) + 7;
  assert(start >= 0 && end > start, 'Exercise shipped ' + name);
  return text.slice(start, end);
}
function run() {
  class Node {
    constructor() { this.style = {}; this.attributes = {}; this.children = []; this.nodeType = 1; }
    setAttribute(key, value) { this.attributes[key] = String(value); }
    getAttribute(key) { return this.attributes[key] || null; }
    removeAttribute(key) { delete this.attributes[key]; }
  }
  const root = new Node(), preview = new Node(), image = new Node(); preview.id = 'ss-map-preview';
  let bounds = {left: 40, top: 30, width: 700, height: 730};
  root.getBoundingClientRect = () => bounds;
  root.contains = node => root.children.includes(node);
  const context = { root, mapPreview: preview, mapPreviewImage: image, mapPreviewTarget: null,
    state: {group: 'maps', nativeScale: 1}, hideHelp() {}, t: (key, args) => key + args[0],
    element: () => new Node(), append(parent, node) { parent.children.push(node); node.parentNode = parent; return node; } };
  vm.createContext(context);
  const source = fs.readFileSync(path.join(__dirname, '../ui/session_stats.js'), 'utf8');
  vm.runInContext(['nativeVisualSource', 'appendVisual', 'hideMapPreview', 'showMapPreview']
    .map(name => sourceFunction(source, name)).join('\n'), context);
  const small = 'img://gui/maps/icons/map/small/synthetic.png';
  const screen = 'img://gui/maps/icons/map/screen/synthetic.dds';
  const minimap = 'img://gui/maps/icons/map/synthetic.png';
  function thumbnail(extra) {
    context.appendVisual(root, {name: 'Synthetic map', visual: {kind: 'map', src: small, ...extra}});
    const node = root.children[root.children.length - 1];
    node.getBoundingClientRect = () => ({left: 60, top: 90, right: 114, width: 54, height: 32});
    return node;
  }
  let target = thumbnail({preview_src: screen, preview_mode: 'image'});
  assert.strictEqual(target.style.backgroundImage, 'url("' + small + '")', 'Card keeps the small native thumbnail');
  context.showMapPreview(target);
  assert.strictEqual(image.style.backgroundImage, 'url("' + screen + '")', 'Hover selects verified high-resolution DDS');
  assert.strictEqual(preview.style.width, '216px'); assert.strictEqual(preview.style.height, '128px');
  target = thumbnail({preview_src: minimap, preview_mode: 'minimap'});
  context.showMapPreview(target);
  assert.strictEqual(image.style.backgroundImage, 'url("' + minimap + '")');
  assert.strictEqual(preview.style.width, '216px'); assert.strictEqual(preview.style.height, '216px');
  context.hideMapPreview(); bounds = {left: 40, top: 30, width: 150, height: 140};
  context.showMapPreview(target);
  assert.strictEqual(preview.style.width, '124px'); assert.strictEqual(preview.style.height, '124px');
  assert(parseFloat(preview.style.left) >= 8 && parseFloat(preview.style.top) >= 8);
  assert(parseFloat(preview.style.left) + 124 <= bounds.width - 8);
  assert(parseFloat(preview.style.top) + 124 <= bounds.height - 8);
  for (const invalid of ['https://example.test/map.png', 'data:image/png;base64,AA==',
    'img://gui/maps/icons/vehicle/test.png', 'img://gui/maps/icons/map/../vehicle/test.png',
    'img://gui/maps/icons/map/./test.png', 'img://gui/maps/icons/map/screen//test.png',
    'img://gui/maps/icons/map/test.png?size=large', 'img://gui/maps/icons/map/test.png#foo',
    'img://gui/maps/icons/map/test:other.png', 'img://gui/maps/icons/map/test.png"); color:red;']) {
    target = thumbnail({preview_src: invalid, preview_mode: 'minimap'});
    assert.strictEqual(target.getAttribute('data-ss-map-preview'), small, 'Invalid preview falls back: ' + invalid);
    assert.strictEqual(target.getAttribute('data-ss-map-preview-mode'), 'image');
  }
  target = thumbnail({});
  assert.strictEqual(target.getAttribute('data-ss-map-preview'), small, 'Older snapshots retain hover support');
  const count = root.children.length;
  context.appendVisual(root, {visual: {kind: 'map', src: 'https://example.test/map.png', preview_src: screen}});
  assert.strictEqual(root.children.length, count, 'Invalid base image cannot create a thumbnail');
  console.log('Map preview quality: verified screen selection, unchanged thumbnails, square bounded minimap and safe fallback passed.');
}
module.exports = run;
if (require.main === module) { run(); }
