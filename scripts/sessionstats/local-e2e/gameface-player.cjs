'use strict';

const { spawn } = require('node:child_process');
const { mkdtemp, rm, stat, writeFile } = require('node:fs/promises');
const net = require('node:net');
const { tmpdir } = require('node:os');
const path = require('node:path');
const { setTimeout: delay } = require('node:timers/promises');

const LOOPBACK = '127.0.0.1';
const KEY_CODES = {
  Backspace: 8, Tab: 9, Enter: 13, Escape: 27, Space: 32,
  PageUp: 33, PageDown: 34, End: 35, Home: 36,
  ArrowLeft: 37, ArrowUp: 38, ArrowRight: 39, ArrowDown: 40, Delete: 46,
};
const PNG_SIGNATURE = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

async function allocatePort() {
  const server = net.createServer();
  const port = await new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen({ host: LOOPBACK, port: 0 }, () => resolve(server.address().port));
  });
  await new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
  return port;
}

async function fetchDebugger(port, routes, accept, deadline, ensureRunning) {
  while (Date.now() < deadline) {
    ensureRunning();
    for (const route of routes) {
      try {
        const remaining = Math.max(1, Math.min(1000, deadline - Date.now()));
        const response = await fetch(`http://${LOOPBACK}:${port}${route}`, {
          signal: AbortSignal.timeout(remaining), redirect: 'error',
        });
        if (response.ok) {
          const data = await response.json();
          if (accept(data)) return data;
        }
      } catch {
        // The process can open the debugger before the page exists.
      }
    }
    await delay(100);
  }
  ensureRunning();
  throw new Error(`Gameface did not expose ${routes.join(' or ')} on port ${port}.`);
}

class DebuggerSocket {
  constructor(socket, timeout) {
    this.socket = socket;
    this.timeout = timeout;
    this.pending = new Map();
    this.sequence = 0;
    this.messages = [];
    socket.addEventListener('message', event => {
      let message;
      try { message = JSON.parse(event.data); }
      catch { return; }
      const request = this.pending.get(message.id);
      if (request) {
        this.pending.delete(message.id);
        clearTimeout(request.timer);
        if (message.error) {
          request.reject(new Error(`Gameface CDP ${request.method} [${message.error.code}]: ${message.error.message}`));
        } else {
          request.resolve(message.result || {});
        }
      } else if (['Runtime.exceptionThrown', 'Log.entryAdded'].includes(message.method)) {
        this.messages.push({ method: message.method, params: message.params });
        if (this.messages.length > 200) this.messages.shift();
      }
    });
    socket.addEventListener('close', () => this.failPending());
    socket.addEventListener('error', () => this.failPending());
  }

  failPending() {
    for (const request of this.pending.values()) {
      clearTimeout(request.timer);
      request.reject(new Error(`The Gameface connection closed during ${request.method}.`));
    }
    this.pending.clear();
  }

  command(method, params = {}) {
    if (this.socket.readyState !== WebSocket.OPEN) {
      return Promise.reject(new Error(`Gameface is disconnected. Cannot run ${method}.`));
    }
    return new Promise((resolve, reject) => {
      const id = ++this.sequence;
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`Gameface did not respond to ${method} within ${this.timeout} ms.`));
      }, this.timeout);
      this.pending.set(id, { method, timer, resolve, reject });
      try { this.socket.send(JSON.stringify({ id, method, params })); }
      catch (error) {
        this.pending.delete(id);
        clearTimeout(timer);
        reject(error);
      }
    });
  }

  close() {
    this.failPending();
    this.socket.close();
  }
}

async function openSocket(url, timeout) {
  if (typeof WebSocket !== 'function') throw new Error('The Gameface adapter requires Node.js 22 or later.');
  const socket = new WebSocket(url);
  try {
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error('The Gameface WebSocket connection timed out.')), timeout);
      socket.addEventListener('open', () => { clearTimeout(timer); resolve(); }, { once: true });
      socket.addEventListener('error', () => {
        clearTimeout(timer);
        reject(new Error('Gameface rejected the WebSocket connection.'));
      }, { once: true });
    });
    return socket;
  } catch (error) {
    socket.close();
    throw error;
  }
}

function createPage(debuggerSocket, version, port, windowMode, close) {
  let mouseHeld = false;
  const command = (method, params) => debuggerSocket.command(method, params);
  async function evaluate(fn, arg) {
    if (typeof fn !== 'function') throw new TypeError('evaluate expects a function that does not close over Node.js state.');
    const expression = `(${fn.toString()})(${arg === undefined ? '' : JSON.stringify(arg)})`;
    const response = await command('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true });
    const details = response.exceptionDetails;
    if (details) throw new Error(`The Gameface view threw an exception. ${details.exception?.description || details.text}`);
    return response.result?.value;
  }

  async function viewport() {
    return evaluate(() => ({ width: window.innerWidth, height: window.innerHeight }));
  }

  function sendMouse(type, x, y, other) {
    if (!Number.isFinite(x) || !Number.isFinite(y)) throw new TypeError('Mouse coordinates must be finite numbers.');
    return command('Input.dispatchMouseEvent', { type, x, y, ...other });
  }

  async function mouseDown(x, y) {
    await sendMouse('mousePressed', x, y, { button: 'left', buttons: 1, clickCount: 1 });
    mouseHeld = true;
  }

  async function mouseUp(x, y) {
    await sendMouse('mouseReleased', x, y, { button: 'left', buttons: 0, clickCount: 1 });
    mouseHeld = false;
  }

  return {
    version, port, windowMode, evaluate, command, viewport, close,
    getMessages: () => debuggerSocket.messages.slice(),
    async goto(url) {
      const pageUrl = new URL(url);
      if (pageUrl.protocol !== 'http:' || pageUrl.hostname !== LOOPBACK) {
        throw new Error(`Gameface Player only accepts HTTP URLs from the test host at ${LOOPBACK}.`);
      }
      const response = await command('Page.navigate', { url: pageUrl.href });
      if (response.errorText) throw new Error(`Gameface Player could not open the view. ${response.errorText}`);
    },
    async setViewportSize({ width, height }) {
      const actual = await viewport();
      if (actual.width !== width || actual.height !== height) {
        throw new Error(`The Gameface viewport is ${actual.width} × ${actual.height}. Launch a separate Player instance at the requested size of ${width} × ${height}.`);
      }
    },
    async screenshot({ path: destination, type = 'png' } = {}) {
      if (type !== 'png') throw new Error('The Gameface adapter only supports native PNG screenshots.');
      const { width, height } = await viewport();
      const clip = { x: 0, y: 0, width, height, scale: 1 };
      const response = await command('Page.captureScreenshot', { format: 'png', clip });
      const bytes = Buffer.from(response.data || '', 'base64');
      if (bytes.length < 24 || !bytes.subarray(0, 8).equals(PNG_SIGNATURE)) {
        throw new Error('Gameface did not return a PNG screenshot.');
      }
      const [actualWidth, actualHeight] = [bytes.readUInt32BE(16), bytes.readUInt32BE(20)];
      if (actualWidth !== width || actualHeight !== height) {
        throw new Error(`Gameface returned a ${actualWidth} × ${actualHeight} PNG for a ${width} × ${height} viewport.`);
      }
      if (destination) await writeFile(destination, bytes);
      return bytes;
    },
    mouseMove: (x, y) => sendMouse('mouseMoved', x, y, { button: 'none', buttons: Number(mouseHeld) }),
    mouseDown, mouseUp,
    async click(x, y) {
      await mouseDown(x, y);
      await mouseUp(x, y);
    },
    wheel(x, y, deltaY, deltaX = 0) {
      if (!Number.isFinite(deltaX) || !Number.isFinite(deltaY)) throw new TypeError('Wheel deltas must be finite numbers.');
      return sendMouse('mouseWheel', x, y, { deltaX, deltaY });
    },
    async press(key) {
      const vk = KEY_CODES[key] || (typeof key === 'string' && /^[A-Za-z0-9 ]$/u.test(key) ? key.toUpperCase().charCodeAt(0) : 0);
      if (!vk) throw new Error(`The Gameface adapter does not support the key ${JSON.stringify(key)}.`);
      // Cohtml consumes a numeric keyIdentifier, including for navigation keys.
      const keys = { keyIdentifier: vk, windowsVirtualKeyCode: vk, modifiers: 0 };
      await command('Input.dispatchKeyEvent', { type: 'keyDown', ...keys });
      if (key.length === 1) {
        const textCode = key.charCodeAt(0);
        await command('Input.dispatchKeyEvent', { type: 'char', keyIdentifier: textCode, windowsVirtualKeyCode: textCode, modifiers: 0 });
      }
      await command('Input.dispatchKeyEvent', { type: 'keyUp', ...keys });
    },
  };
}

async function connectGameface({ port, url, startupTimeout = 15000, commandTimeout = 8000,
  ensureRunning = () => {}, stop = async () => {}, windowMode = 'attached' }) {
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('Specify a valid local Gameface debugger port.');
  const deadline = Date.now() + startupTimeout;
  const identity = await fetchDebugger(port, ['/json/version'], data => data && !Array.isArray(data), deadline, ensureRunning);
  const agent = `${identity.Browser || ''} ${identity['User-Agent'] || ''}`;
  if (!/\bcohtml\b/i.test(agent)) throw new Error(`The debugger on port ${port} reported ${agent.trim() || 'an unknown engine'}. Expected Cohtml.`);
  const isPage = item => item?.type === 'page';
  const targets = await fetchDebugger(port, ['/json/list', '/json'], data => Array.isArray(data) && data.some(isPage), deadline, ensureRunning);
  const target = (url && targets.find(item => isPage(item) && item.url === url)) || targets.find(isPage);
  if (target.id === undefined || !/^[A-Za-z0-9_-]+$/.test(String(target.id))) {
    throw new Error(`Gameface did not report a valid CDP page target on port ${port}.`);
  }
  // Some Player builds prefix their advertised WebSocket path with /json/list.
  const socket = await openSocket(`ws://${LOOPBACK}:${port}/devtools/page/${target.id}`, commandTimeout);
  const client = new DebuggerSocket(socket, commandTimeout);
  const version = agent.match(/\bcohtml\/(\d+(?:\.\d+)*)/i)?.[1] || 'unknown';
  const page = createPage(client, version, port, windowMode, async () => {
    client.close();
    await stop();
  });
  try {
    const userAgent = await page.evaluate(() => navigator.userAgent);
    if (!/\bcohtml\b/i.test(userAgent || '')) throw new Error('The debugger view did not identify itself as Cohtml.');
    page.version = userAgent.match(/\bcohtml\/(\d+(?:\.\d+)*)/i)?.[1] || version;
    await Promise.allSettled([page.command('Runtime.enable'), page.command('Log.enable')]);
    return page;
  } catch (error) {
    await page.close();
    throw error;
  }
}

async function launchGameface({ executable, url, width, height, renderer = 'dx11', extraArgs = [],
  startupTimeout = 15000, commandTimeout = 8000, allowVisible = false }) {
  if (!executable) throw new Error('Specify the path to the official Gameface Player.exe.');
  executable = path.resolve(executable);
  if (!await stat(executable).then(item => item.isFile(), () => false)) throw new Error(`Gameface Player was not found at ${executable}.`);
  if (![width, height].every(value => Number.isInteger(value) && value > 0)) throw new Error('Gameface dimensions must be positive whole pixels.');
  const pageUrl = new URL(url);
  if (pageUrl.protocol !== 'http:' || pageUrl.hostname !== LOOPBACK) throw new Error(`Launch Gameface with an HTTP URL from the local test host at ${LOOPBACK}.`);
  const port = await allocatePort();
  const args = [
    `--remote-debugging-port=${port}`, '--no-first-run', '--enable-gui=false',
    `--renderer=${renderer}`, `--width=${width}`, `--height=${height}`, ...extraArgs, pageUrl.href,
  ];
  const temporary = path.resolve(tmpdir());
  const cwd = await mkdtemp(path.join(temporary,'sessionstats-player-'));
  const cleanup = () => {
    if (path.dirname(cwd) !== temporary || !path.basename(cwd).startsWith('sessionstats-player-')) {
      throw new Error('Unexpected Gameface Player working directory.');
    }
    return rm(cwd,{recursive:true,force:true,maxRetries:3,retryDelay:100});
  };
  let child;
  try {
    child = spawn(executable, args, {cwd,windowsHide:!allowVisible,stdio:['ignore','pipe','pipe']});
  } catch (error) {
    await cleanup();
    throw error;
  }
  let processError = null;
  let output = '';
  function collect(data) { output = (output + data.toString()).slice(-3200); }
  child.stderr.on('data', collect);
  child.stdout.on('data', collect);
  child.once('error', error => { processError = error; });
  const stopped = new Promise(resolve => child.once('close', resolve));
  let stopping;
  function stop() {
    if (stopping) return stopping;
    stopping = (async () => {
      if (child.exitCode === null && child.signalCode === null && !processError) {
        child.kill();
        await Promise.race([stopped, delay(2000, undefined, {ref:false})]);
        if (child.exitCode === null && child.signalCode === null) child.kill('SIGKILL');
        await Promise.race([stopped, delay(2000, undefined, {ref:false})]);
      }
      await cleanup();
    })();
    return stopping;
  }
  const ensureRunning = () => {
    if (processError) throw new Error(`Could not start Gameface Player. ${processError.message}`);
    if (child.exitCode !== null || child.signalCode !== null) {
      throw new Error(`Gameface Player exited (${child.exitCode ?? child.signalCode}). ${output.trim()}`);
    }
  };
  let page;
  try {
    page = await connectGameface({ port, url: pageUrl.href, startupTimeout, commandTimeout, ensureRunning, stop,
      windowMode: allowVisible ? 'desktop-player' : 'windows-hide-requested' });
    await page.setViewportSize({ width, height });
    return page;
  } catch (error) {
    if (page) await page.close();
    else await stop();
    throw new Error(output.trim() && !error.message.includes(output.trim()) ? `${error.message}\n${output.trim()}` : error.message, { cause: error });
  }
}

module.exports = { launchGameface, connectGameface };
