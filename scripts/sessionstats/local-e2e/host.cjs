'use strict';

const {spawn} = require('node:child_process');
const {createInterface} = require('node:readline');
const http = require('node:http');
const path = require('node:path');
const fs = require('node:fs/promises');

function startBackend(python, source, {profile, gameClient}={}) {
  const args=['-B','-u',path.join(__dirname,'backend.py'),'--source',source];
  if(profile) args.push('--profile',profile);
  if(gameClient) args.push('--game-client',gameClient);
  const child = spawn(python, args,
    {stdio:['pipe', 'pipe', 'pipe'], windowsHide:true});
  const waiting = new Map();
  let sequence = 0, failure, diagnostic = '';
  function fail(error) {
    failure = error;
    for (const item of waiting.values()) { clearTimeout(item.timer); item.reject(error); }
    waiting.clear();
  }
  child.on('error', fail);
  child.stdin.on('error', fail);
  child.stderr.on('data', bytes => { diagnostic = (diagnostic + bytes.toString()).slice(-4000); });
  child.on('exit', (code, signal) => fail(new Error(`Python exited (${code ?? signal}) ${diagnostic}`)));
  createInterface({input:child.stdout}).on('line', line => {
    let message;
    try { message = JSON.parse(line); }
    catch (error) { fail(new Error(`Invalid bridge response (${error.message}): ${line.slice(0,240)}`)); return; }
    const item = waiting.get(message.id);
    if (!item) return;
    waiting.delete(message.id);
    clearTimeout(item.timer);
    if (message.error) item.reject(new Error(String(message.error)));
    else item.resolve(message.result);
  });
  return {
    ask(op, input = {}) {
      if (failure) return Promise.reject(failure);
      const id = ++sequence;
      return new Promise((resolve, reject) => {
        const timer = setTimeout(() => {
          waiting.delete(id);
          reject(new Error(`Python bridge did not answer ${op} ${diagnostic}`));
        }, op === 'inventory' ? 180000 : 45000);
        waiting.set(id, {resolve,reject,timer});
        child.stdin.write(JSON.stringify({id,op,...input})+'\n');
      });
    },
    async close() {
      if (child.exitCode !== null || child.signalCode !== null) return;
      const done = new Promise(resolve => child.once('close', resolve));
      child.stdin.end();
      const timer = setTimeout(() => child.kill(), 3000);
      try { await done; }
      finally { clearTimeout(timer); }
    }
  };
}

// Injected before the shipped module in both renderers. Gameface retains its
// rendering and browser engine; these objects reproduce WoT's View contract.
function bindHost({images, fonts, version}) {
  var previousEngine = window.engine;
  var events = {};
  var callbacks = [];
  window.__localActions = [];
  window.__localErrors = [];
  window.__localWheels = [];
  window.__localSize = null;
  window.isDomBuilt = true;
  window.engine = { whenReady:previousEngine && previousEngine.whenReady || Promise.resolve(),
    on:function(name,listener){events[name]=listener;}, off:function(name){delete events[name];} };
  window.viewEnv = {
    remToPx:function(value){return value;},
    resizeViewPx:function(width,height){window.__localSize=[width,height];},
    setTrackMouseOnStage:function(){}, setEventHandled:function(){},
    handleViewEvent:function(){},
    addDataChangedCallback:function(){
      for(var i=0;i<arguments.length;i++){if(typeof arguments[i]==='function') callbacks.push(arguments[i]);}
      return callbacks.length;
    },
    removeDataChangedCallback:function(index){delete callbacks[index-1];}
  };
  window.model = { payload:JSON.stringify({version:version,account_key:'starting',loading:true,
      scopes:{launch:{summary:{}},manual:{summary:{}}}}),
    onAction:function(action){window.__localActions.push(JSON.parse(JSON.stringify(action)));} };
  window.__localPublish = function(data){
    window.model.payload=JSON.stringify(data);
    return window.GRZSessionStats.update(data);
  };
  window.addEventListener('error',function(event){window.__localErrors.push(String(event.message||'script error'));});
  window.addEventListener('unhandledrejection',function(event){window.__localErrors.push(String(event.reason));});
  document.addEventListener('wheel',function(event){
    var scroll = document.getElementById('ss-scroll');
    if(scroll && scroll.contains(event.target)) window.__localWheels.push({delta:event.deltaY,trusted:event.isTrusted});
  },true);

  function urlFor(source) { return images[source] ? '/'+images[source] : source; }
  function rewrite(node) {
    if (!node || node.nodeType !== 1) return;
    var source = node.getAttribute('src');
    if (source && images[source]) node.setAttribute('src',urlFor(source));
    var setting = node.style && node.style.backgroundImage;
    if (setting && setting.indexOf('img://') !== -1) {
      var background = setting.replace(/img:\/\/[^)"']+/g,urlFor);
      if (background !== setting) node.style.backgroundImage=background;
    }
  }
  new MutationObserver(function(changes){
    changes.forEach(function(change){
      if(change.type==='attributes'){rewrite(change.target);return;}
      Array.prototype.forEach.call(change.addedNodes,function(node){
        if(node.nodeType!==1)return;
        rewrite(node);
        Array.prototype.forEach.call(node.querySelectorAll('img[src^="img://"],[style*="img://"]'),rewrite);
      });
    });
  }).observe(document.documentElement,{subtree:true,childList:true,attributes:true,attributeFilter:['src','style']});
  var style = document.createElement('style');
  style.textContent = Object.keys(fonts).map(function(weight){
    return '@font-face{font-family:Warhelios;font-style:normal;font-weight:'+(weight==='bold'?'700':'400')+
      ';src:url("/'+fonts[weight]+'") format("truetype")}';
  }).join('\n')+'\nbody {background:#141711;}';
  document.head.appendChild(style);
}

async function serve(source, inventory) {
  const ui = path.resolve(source, 'ui');
  const assetRoot = inventory.asset_root || source;
  const assets = path.resolve(assetRoot, 'assets');
  const html = await fs.readFile(path.join(ui,'SessionStats.html'), 'utf8');
  const marker = '<script type="module" src="session_stats.js"></script>';
  if (!html.includes(marker)) throw new Error('SessionStats.html has no expected module entry point');
  const document = html.replace(marker,'<script src="local-host.js"></script>\n  '+marker);
  const bootstrap = `(${bindHost})(${JSON.stringify({...inventory.assets,version:inventory.version})});`;
  const staticFiles = new Map(Object.values({...inventory.assets.images,...inventory.assets.fonts}).map(relative => {
    const file = path.resolve(assetRoot,relative);
    if (!file.startsWith(assets+path.sep)) throw new Error('Asset escaped the private fixture directory');
    return ['/'+relative,file];
  }));
  staticFiles.set('/session_stats.js', path.join(ui, 'session_stats.js'));
  staticFiles.set('/session_stats.css', path.join(ui, 'session_stats.css'));
  staticFiles.set('/session_stats_camo.png', path.join(ui, 'session_stats_camo.png'));
  const types={'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8',
    '.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.ttf':'font/ttf','.woff2':'font/woff2','.webp':'image/webp'};
  const cache = new Map([['/SessionStats.html',Buffer.from(document)],['/local-host.js',Buffer.from(bootstrap)]]);
  const server = http.createServer(async (request,response) => {
    try {
      const name=decodeURIComponent(new URL(request.url,'http://127.0.0.1').pathname);
      const type=types[path.extname(name)];
      if (!type || request.method!=='GET') { response.writeHead(404).end(); return; }
      if(!cache.has(name)&&staticFiles.has(name)) cache.set(name,await fs.readFile(staticFiles.get(name)));
      if(!cache.has(name)) { response.writeHead(404).end(); return; }
      const body=cache.get(name);
      response.writeHead(200,{'Content-Type':type,'Content-Length':body.length,'Cache-Control':'no-store'}).end(body);
    } catch(error) { response.writeHead(404).end(); }
  });
  await new Promise((resolve,reject)=>server.once('error',reject).listen(0,'127.0.0.1',resolve));
  return {url:`http://127.0.0.1:${server.address().port}/SessionStats.html`, close:()=>new Promise(resolve=>{
    server.close(resolve);server.closeAllConnections();
  })};
}

async function openChromium(executable) {
  const {chromium}=require('playwright');
  const browser=await chromium.launch({executablePath:executable,headless:true,args:['--disable-background-timer-throttling','--disable-renderer-backgrounding']});
  return {
    version:browser.version(),
    async open({url,width,height,useWarhelios=false}) {
      const context=await browser.newContext({viewport:{width,height},timezoneId:'Europe/Warsaw',deviceScaleFactor:1,reducedMotion:'reduce',
        serviceWorkers:'block'});
      const origin=new URL(url).origin;
      let page;
      try {
        await context.route('**/*',route=>new URL(route.request().url()).origin===origin
          ? route.continue() : route.abort());
        page=await context.newPage();
        await page.goto(url);
        if(useWarhelios) {
          const loaded=await page.evaluate(async()=>{
            const faces=await Promise.all([document.fonts.load('400 14px Warhelios'),document.fonts.load('700 14px Warhelios')]);
            return faces.every(items=>items.length>0);
          });
          if(!loaded) throw new Error('Chromium did not load both Warhelios fonts');
        }
      }
      catch(error) { await context.close(); throw error; }
      return {version:browser.version(),evaluate:(...args)=>page.evaluate(...args),press:key=>page.keyboard.press(key),
        click:(x,y)=>page.mouse.click(x,y), mouseMove:(x,y)=>page.mouse.move(x,y),
        mouseDown:async (x,y)=>{await page.mouse.move(x,y);await page.mouse.down();},
        mouseUp:async (x,y)=>{await page.mouse.move(x,y);await page.mouse.up();},
        wheel:async (x,y,deltaY,deltaX=0)=>{await page.mouse.move(x,y);await page.mouse.wheel(deltaX,deltaY);},
        setViewportSize:size=>page.setViewportSize(size),
        screenshot:options=>page.screenshot(options),close:()=>context.close()};
    },
    close:()=>browser.close()
  };
}

module.exports={startBackend,serve,openChromium};
