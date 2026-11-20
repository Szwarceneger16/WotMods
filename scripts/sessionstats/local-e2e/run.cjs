'use strict';

const assert = require('node:assert/strict');
const {existsSync} = require('node:fs');
const fs = require('node:fs/promises');
const {homedir} = require('node:os');
const path = require('node:path');
const {parseArgs} = require('node:util');
const {setTimeout: delay} = require('node:timers/promises');
const {startBackend,serve,openChromium} = require('./host.cjs');
const {writeReport} = require('./report.cjs');

const checkoutSource = path.resolve(__dirname, '../../../mods/sessionstats');
const sourceDefault = existsSync(path.join(checkoutSource,'VERSION')) ? checkoutSource :
  path.resolve(__dirname, '../WotMods-pr17-next/mods/sessionstats');
const standardWidths = [365,625,780,913,1120,1350,1800];
const routes = new Set(['since-sunday','history']);
const label = ({width,height,language,range,group}) => `${width}x${height}/${language}/${range}/${group}`;
const variant = order => [order.metric,order.statistic,order.direction,order.chronology].join('-');
const actionFields = ['metric','statistic','direction','chronology'];

function requested(values, option, defaults, cast) {
  if (!values[option]) return defaults;
  return [...new Set(values[option].split(',').map(value=>cast ? Number(value) : value.trim()))];
}

function plan(inventory, values) {
  const smoke = values.suite === 'smoke';
  const build = values.suite === 'build';
  const widths = requested(values,'widths',build?[625,1350]:smoke?[365,780,1350]:standardWidths,true);
  const heights = requested(values,'heights',[730,900],true);
  const names = requested(values,'ranges',null);
  const languages = requested(values,'languages',null);
  if (widths.some(width=>!Number.isInteger(width)||width<365||width>1920) ||
      heights.some(height=>!Number.isInteger(height)||height<730||height>1014)) throw new Error('Invalid panel dimensions');
  const allRanges = inventory.ranges;
  if (names && names.some(name=>!allRanges.some(range=>range.id===name))) throw new Error('Unknown date range');
  if (languages && languages.some(language=>!inventory.languages.includes(language))) throw new Error('Unknown language');
  const ranges = allRanges.filter(range=>names ? names.includes(range.id) :
    build ? range.id==='since-sunday' : !smoke || routes.has(range.id));
  const tasks = [];
  for(const width of widths) for(const height of heights) for(const range of ranges) {
    if(build&&!values.widths&&!values.heights&&((width===625)!==(height===730))) continue;
    const locales = languages || (!smoke&&!build && range.id==='since-sunday'&&[365,780,1350].includes(width) ? ['en','pl'] : ['en']);
    for(const language of locales) for(const group of inventory.groups) {
      const chronology = group==='tiers'?'tier_desc':'newest';
      const orders = inventory.orders[group].filter(order=>{
        const regular = order.metric==='off'&&order.chronology===chronology;
        const highlighted = order.metric===(group==='battles'?'xp_received':'win_rate') &&
          order.statistic==='avg' && order.direction==='desc' && order.chronology===chronology;
        if (build) return width<875 ? highlighted : regular;
        if (smoke) return regular||highlighted;
        if (!routes.has(range.id) && !values['all-ranges']) return order.metric==='off';
        return language==='en'||languages||regular||highlighted;
      });
      if(orders.length) tasks.push({width,height,language,range:range.id,scope:range.scope,group,orders});
    }
  }
  if(!tasks.length) throw new Error('The selected matrix is empty');
  return tasks;
}

function planShard(tasks, shard) {
  if (!shard) return tasks;
  const match=/^(\d+)\/(\d+)$/.exec(shard);
  assert(match,'Use --shard INDEX/TOTAL with 1-based integers');
  const [index,total]=match.slice(1).map(Number);
  assert(index>=1&&index<=total&&total<=tasks.length,'Shard is outside the available task range');
  const load=Array.from({length:total},()=>0);
  const owners=new Map();
  for(const task of [...tasks].sort((a,b)=>b.orders.length-a.orders.length)) {
    const owner=load.indexOf(Math.min(...load));
    owners.set(task,owner);
    load[owner]+=task.orders.length;
  }
  return tasks.filter(task=>owners.get(task)===index-1);
}

function decorate(payload, size) {
  const {width,height}=size;
  payload.window_size=[width,height];
  payload.viewport={width:size.hostWidth||width,height:size.hostHeight||height,scale:1};
  const style=payload.appearance||{};
  style.window_settings={...style.window_settings,maximized:false,background_transparency:0,restored_width:width,restored_height:height};
  payload.appearance=style;
  return payload;
}

function session(driver, backend, inventory, out, hostSize, compare, screenshotOptions) {
  let size, model, submitted = 0;
  const screenshots = [];
  async function publish(payload) {
    model=decorate(payload,size);
    const accepted=await driver.evaluate(model=>window.__localPublish(model),model);
    assert(accepted,'Shipped panel rejected the Python payload');
  }
  const collectActions = () => driver.evaluate(()=>window.__localActions.splice(0));
  async function flush() {
    for(let round=0;round<8;round++) {
      // Send only real frontend actions. The simulated host acknowledges pure
      // cursor/placement operations without a Python round-trip.
      const actions=await collectActions();
      if(!actions.length) return;
      for(const action of actions) {
        if (action.account_key && model && action.account_key!==model.account_key) continue;
        if (['close','resize','window_size','window_position','resize_cursor','resize_begin','resize_end'].includes(action.action)) continue;
        submitted++;
        const reply=await backend.ask('command',{action});
        if(reply) await publish(reply);
      }
    }
    throw new Error('Panel kept issuing commands without reaching idle');
  }
  async function until(predicate, message, deadline=5500) {
    const end=Date.now()+deadline;
    do {
      await flush();
      const result=await predicate();
      if(result) return result;
      await delay(25);
    } while(Date.now()<end);
    throw new Error(message);
  }
  async function idle() {
    await delay(35);
    await until(()=>driver.evaluate(()=>document.getElementById('ss-filter-loading').getAttribute('aria-hidden')==='true'&&
      document.getElementById('ss-groups').getAttribute('aria-busy')!=='true'),'The result list did not become idle');
    await delay(35);
    await flush();
  }
  function point(selector) {
    return driver.evaluate(selector=>{
      const node=document.querySelector(selector);
      if(!node||node.disabled||node.getAttribute('aria-disabled')==='true') return null;
      const box=node.getBoundingClientRect();
      if(box.width<1||box.height<1)return null;
      const x=box.left+box.width/2,y=box.top+box.height/2,target=document.elementFromPoint(x,y);
      return node.contains(target)?{x,y}:null;
    },selector);
  }
  async function click(selector,{reveal=true}={}) {
    let at=await point(selector);
    if(!at&&reveal) {
      await driver.evaluate(selector=>{
        const node=document.querySelector(selector),scroll=document.getElementById('ss-scroll');
        if(!node||!scroll.contains(node)) return;
        const viewport=scroll.getBoundingClientRect(),target=node.getBoundingClientRect();
        scroll.scrollTop=Math.max(0,scroll.scrollTop+target.top-viewport.top-viewport.height/3);
      },selector);
      at=await until(()=>point(selector),`Control is not clickable: ${selector}`,1200);
    }
    assert(at,`Control is not clickable: ${selector}`);
    await driver.click(at.x,at.y);
    await delay(16);
    await flush();
  }
  function choice(holder,value){return `${holder} .ss-select-option[data-value=${JSON.stringify(value)}]`;}
  async function select(holder,value) {
    const selector=choice(holder,value);
    const already=await driver.evaluate(selector=>document.querySelector(selector)?.getAttribute('aria-selected')==='true',selector);
    if(already) return;
    await click(holder+' .ss-select-trigger');
    if(await point(selector)) { await click(selector,{reveal:false}); return; }
    const position=await driver.evaluate(selector=>{
      const target=document.querySelector(selector);
      if(!target)return null;
      const options=Array.from(target.parentNode.querySelectorAll('.ss-select-option')).filter(node=>
        !node.disabled&&node.style.display!=='none'&&node.getAttribute('aria-disabled')!=='true');
      return {index:options.indexOf(target),focused:options.indexOf(document.activeElement),length:options.length};
    },selector);
    assert(position&&position.index>=0,`Option ${value} is not present in ${holder}`);
    if(position.focused<0) {await driver.press('Home'); position.focused=0;}
    const delta=position.index-position.focused;
    for(let i=0;i<Math.abs(delta);i++) await driver.press(delta<0?'ArrowUp':'ArrowDown');
    const focused=await driver.evaluate(selector=>document.activeElement===document.querySelector(selector),selector);
    assert(focused&&await point(selector),`Keyboard could not reveal ${value} in ${holder}`);
    await driver.press('Enter');
    await flush();
  }
  async function setup(task) {
    size={...hostSize,...task};
    model=null;
    await collectActions();
    await publish(await backend.ask('setup',{range:task.range,group:task.group,language:task.language}));
    const scope=task.scope||(inventory.ranges.find(range=>range.id===task.range)||{}).scope;
    const active=`#ss-scope-${scope==='timeline'?'manual':scope}`;
    await until(()=>driver.evaluate(()=>window.GRZSessionStats?.getState().nativeBound),'WoT host bridge was not bound');
    if(!await driver.evaluate(selector=>document.querySelector(selector)?.getAttribute('aria-pressed')==='true',active)) await click(active);
    const group='#ss-group-'+task.group;
    if(!await driver.evaluate(selector=>document.querySelector(selector)?.getAttribute('aria-pressed')==='true',group)) await click(group);
    await idle();
    await driver.evaluate(()=>{document.getElementById('ss-scroll').scrollTop=0;});
  }
  function orderFor(task) {
    return model?.scopes[task.scope]?.ordering[task.group];
  }
  async function applyOrder(task,order) {
    const toggle='#ss-sort-off';
    const wide=await driver.evaluate(selector=>getComputedStyle(document.querySelector(selector)).display!=='none',toggle);
    let actual=orderFor(task);
    if(actual.chronology!==order.chronology || order.metric==='off') {
      if(actual.metric!=='off') {
        if(wide) await click(toggle);
        else await select('#ss-sort-metric','off');
      }
      if(orderFor(task).chronology!==order.chronology) await select('#ss-sort-chronology',order.chronology);
    }
    if(order.metric!=='off') {
      if(wide&&orderFor(task).metric==='off') await click(toggle);
      if(orderFor(task).metric!==order.metric) await select('#ss-sort-metric',order.metric);
      if(orderFor(task).direction!==order.direction) await select('#ss-sort-direction',order.direction);
      if(orderFor(task).statistic!==order.statistic&&task.group!=='battles') await select('#ss-sort-statistic',order.statistic);
    }
    await idle();
    actual=orderFor(task);
    for(const field of actionFields) if(order.metric!=='off'||field==='metric'||field==='chronology'){
      assert.equal(actual?.[field],order[field],`Python did not accept ${field}`);
    }
  }
  async function snapshot(relative) {
    const key=relative+(screenshotOptions.type==='jpeg'?'.jpg':'.png');
    const filename=path.join(out,key);
    await fs.mkdir(path.dirname(filename),{recursive:true});
    const bytes=await driver.screenshot(screenshotOptions);
    await fs.writeFile(filename,bytes);
    let diff={};
    if(compare){
      const clockBounds=await driver.evaluate(()=>{
        const rect=document.getElementById('ss-time-point-name').getBoundingClientRect();
        return rect.width>12&&rect.height>6?{left:Math.ceil(rect.left+6),right:Math.floor(rect.right-6),
          top:Math.ceil(rect.top+3),bottom:Math.floor(rect.bottom-3)}:null;
      });
      diff=await compare(key,bytes,driver.version,clockBounds);
    }
    screenshots.push({image:key,...diff});
    return key;
  }
  async function resize(width,height) {
    size={...size,width,height};
    await publish(model);
    await idle();
  }
  return {driver, setup, idle, flush, click, select, snapshot, resize, applyOrder, until,
    read:()=>model, count:()=>submitted, screenshots, check:(condition,explanation)=>assert(condition,explanation)};
}

async function measure(driver) {
  return driver.evaluate(()=>{
    const get=id=>document.getElementById(id);
    const panel=get('grz-session-stats').getBoundingClientRect(),scroll=get('ss-scroll'),scrollBox=scroll.getBoundingClientRect();
    const filter=get('ss-filter-panel'), filterBox=filter.getBoundingClientRect(), sort=get('ss-sorting'), sortBox=sort.getBoundingClientRect();
    const contentTop=Math.max(scrollBox.top,filterBox.bottom);
    const cards=Array.from(document.querySelectorAll('#ss-groups .ss-group'));
    const visible=cards.filter(card=>{
      const box=card.getBoundingClientRect();
      return box.width>0&&Math.min(scrollBox.bottom,box.bottom)>Math.max(contentTop,box.top)+1;
    });
    const controls=Array.from(sort.querySelectorAll('.ss-select-trigger,#ss-sort-off')).filter(node=>{
      const box=node.getBoundingClientRect();
      return box.width>0&&box.height>0&&(box.left<sortBox.left-1||box.right>sortBox.right+1||box.top<sortBox.top-1||box.bottom>sortBox.bottom+1);
    });
    let wheelAt=null;
    for(const yRatio of [0.65,0.80,0.40]) for(const xRatio of [0.66,0.32,0.50]) {
      const x=Math.round(scrollBox.left+scrollBox.width*xRatio),y=Math.round(scrollBox.top+scrollBox.height*yRatio);
      if(!wheelAt&&scroll.contains(document.elementFromPoint(x,y))) wheelAt={x,y};
    }
    return {width:panel.width,height:panel.height,top:Math.round(scroll.scrollTop),visible:visible.length,
      resultsReached:cards.some(card=>card.getBoundingClientRect().top<scrollBox.bottom-1),
      mounted:cards.length,wheelAt,layout:get('ss-list-controls').getAttribute('data-filter-layout'),
      group:document.querySelector('.ss-group-tab[aria-pressed="true"]')?.id.slice('ss-group-'.length),
      version:get('ss-version').textContent,overflow:controls.length,warning:getComputedStyle(get('ss-sort-data-warning')).display!=='none',
      pinned:filter.classList.contains('is-pinned'),filterInside:filterBox.top>=scrollBox.top-1&&filterBox.bottom<=scrollBox.bottom+1,
      wheels:window.__localWheels.slice(),errors:window.__localErrors.slice()};
  });
}

async function runCase(ctx, task, order, version, capture) {
  await ctx.applyOrder(task,order);
  await ctx.driver.evaluate(()=>{document.getElementById('ss-scroll').scrollTop=0; window.__localWheels=[];});
  await ctx.idle();
  const phases=[];
  const root=label(task)+'/'+variant(order);
  for(let step=0;step<=3;step++) {
    if(step) {
      const at=phases[step-1].wheelAt;
      assert(at,'No visible point in the primary scrolling view');
      await ctx.driver.wheel(at.x,at.y,-120);
      await ctx.idle();
    }
    const model=ctx.read(),scope=model.scopes[task.scope];
    const state=await measure(ctx.driver);
    assert(Math.abs(state.width-task.width)<=1 && Math.abs(state.height-task.height)<=1,`Wrong rendered size ${state.width}x${state.height}`);
    assert.equal(state.group,task.group);
    assert.equal(state.version,'v'+version);
    assert(!state.overflow,`${state.overflow} filter controls overflow their container`);
    assert(!state.pinned||state.filterInside,'Pinned filters escaped the scroll viewport');
    assert.deepEqual(state.errors,[]);
    assert.equal(state.wheels.length,step);
    assert(state.wheels.every(event=>event.trusted&&event.delta<0),'Wheel events did not reach the panel using native input');
    if(!step) assert.equal(state.top,0);
    else assert(state.top>=phases[step-1].top,'Scrolling reversed unexpectedly');
    if(step===3&&scope.pagination[task.group].total>0){
      assert(state.mounted>0,'Python returned results but the panel mounted no cards');
      if(state.resultsReached) assert(state.visible>0,'The results area is visible without any result cards');
    }
    if(capture==='all'||(capture==='final'&&step===3)) state.image=await ctx.snapshot(root+'/'+step);
    phases.push(state);
  }
  return {key:root,phases};
}

async function makeComparer(baseline, out, threshold, {engine, fixture, assets}) {
  if(!baseline) return null;
  const manifest=JSON.parse(await fs.readFile(path.join(baseline,'run.json'),'utf8'));
  assert.equal(manifest.engine,engine,'The reference must use the same rendering engine');
  assert(manifest.fixture===fixture&&manifest.assets===assets,'The reference must use the same fixture and artwork source');
  const {PNG}=require('pngjs');
  return async (key,bytes,version,clockBounds)=>{
    assert.equal(manifest.renderer,version,'The reference must use the same renderer version');
    let original;
    try {original=await fs.readFile(path.join(baseline,key));}
    catch(error) {if(error.code==='ENOENT') return {missingBaseline:true}; throw error;}
    const before=PNG.sync.read(original),after=PNG.sync.read(bytes);
    assert(before.width===after.width&&before.height===after.height,`Reference screenshot has a different size: ${key}`);
    if(original.equals(bytes)) return {difference:0};
    const image=new PNG({width:after.width,height:after.height});
    let changed=0;
    for(let i=0;i<after.data.length;i+=4){
      const pixel=i/4,x=pixel%after.width,y=Math.floor(pixel/after.width);
      const clock=clockBounds&&x>=clockBounds.left&&x<clockBounds.right&&y>=clockBounds.top&&y<clockBounds.bottom;
      const delta=clock?0:Math.max(Math.abs(before.data[i]-after.data[i]),Math.abs(before.data[i+1]-after.data[i+1]),
        Math.abs(before.data[i+2]-after.data[i+2]),Math.abs(before.data[i+3]-after.data[i+3]));
      if(delta>20){image.data[i]=255;image.data[i+1]=49;image.data[i+2]=88;changed++;}
      else {const grey=Math.round((after.data[i]+after.data[i+1]+after.data[i+2])/6);image.data[i]=grey;image.data[i+1]=grey;image.data[i+2]=grey;}
      image.data[i+3]=255;
    }
    const difference=changed/(after.width*after.height);
    if(difference<=threshold) return {difference};
    const diff='differences/'+key, reference='baseline/'+key;
    for(const [target,data] of [[diff,PNG.sync.write(image)],[reference,original]]){
      const filename=path.join(out,target);
      await fs.mkdir(path.dirname(filename),{recursive:true}); await fs.writeFile(filename,data);
    }
    return {difference,diff,reference,visualFailure:true};
  };
}

async function reportPath(values) {
  const privateInputs=values.profile||values['game-client'];
  const root=privateInputs ? path.join(process.env.LOCALAPPDATA||homedir(),'SessionStatsQA','runs') : path.join(__dirname,'runs');
  const out=path.resolve(values.out||path.join(root,new Date().toISOString().replaceAll(/[:.]/g,'-')+'-'+values.engine));
  if(privateInputs) {
    let ancestor=path.dirname(out);
    while(!existsSync(ancestor)) ancestor=path.dirname(ancestor);
    let real=await fs.realpath(ancestor);
    while(true) {
      assert(!existsSync(path.join(real,'.git')),'Save private QA reports outside any Git checkout');
      const parent=path.dirname(real);
      if(parent===real) break;
      real=parent;
    }
    for(let parent=path.dirname(out);parent!==path.dirname(parent);parent=path.dirname(parent)) {
      assert(!existsSync(path.join(parent,'.git')),'Save private QA reports outside any Git checkout');
    }
  }
  return out;
}

function cli() {
  const options={help:{type:'boolean'},plan:{type:'boolean'},engine:{type:'string',default:'chromium'},suite:{type:'string',default:'smoke'},
    source:{type:'string',default:sourceDefault},out:{type:'string'},baseline:{type:'string'},threshold:{type:'string',default:'0.002'},
    python:{type:'string',default:process.env.SESSIONSTATS_PYTHON||'python'},chrome:{type:'string',default:process.env.GRZ_CHROME},
    player:{type:'string',default:process.env.GAMEFACE_PATH},widths:{type:'string'},heights:{type:'string'},
    ranges:{type:'string'},languages:{type:'string'},'all-ranges':{type:'boolean'}, 'matrix-only':{type:'boolean'},
    'player-visible':{type:'boolean'},limit:{type:'string'},profile:{type:'string'},'game-client':{type:'string'},
    capture:{type:'string',default:'all'},'image-format':{type:'string',default:'png'},
    'jpeg-quality':{type:'string'},shard:{type:'string'}};
  return parseArgs({options}).values;
}

async function main() {
  const values=cli();
  if(values.help){console.log('node run.cjs --engine chromium|gameface --suite build|smoke|full [--plan] [--out folder]\n' +
    '  --player Player.exe --python python --chrome msedge.exe --source mods/sessionstats\n' +
    '  --widths 365,780 --heights 730,900 --ranges since-sunday --languages en,pl\n' +
    '  --all-ranges --matrix-only --limit 20 --baseline folder --threshold 0.002\n' +
    '  --profile anonymous-profile.json --game-client path-to-WoT (local only)\n' +
    '  --shard 1/16 --capture all|final|failures --image-format png|jpeg [--jpeg-quality 82]\n' +
    '  --player-visible allows a Gameface Player desktop window if it cannot run hidden');return;}
  if(!['gameface','chromium'].includes(values.engine)||!['full','smoke','build'].includes(values.suite)) throw new Error('Unknown engine or suite');
  assert(['all','final','failures'].includes(values.capture),'Invalid screenshot capture mode');
  assert(['png','jpeg'].includes(values['image-format']),'Invalid screenshot format');
  const imageFormat=values['image-format'];
  const jpegQuality=Number(values['jpeg-quality']??82);
  assert(values['jpeg-quality']===undefined||
    (imageFormat==='jpeg'&&Number.isInteger(jpegQuality)&&jpegQuality>=1&&jpegQuality<=100),
    '--jpeg-quality requires JPEG and an integer from 1 to 100');
  const screenshotOptions=imageFormat==='jpeg'?{type:'jpeg',quality:jpegQuality}:{type:'png'};
  assert(values.engine==='chromium'||(values['image-format']==='png'&&!values['game-client']),
    'Stock WoT assets and JPEG capture use Chromium');
  assert(!values.baseline||(values.capture==='all'&&values['image-format']==='png'),'Baseline comparison needs PNG for every stage');
  assert(!values.shard||values.limit===undefined,'Use either --limit or --shard');
  if(process.env.GITHUB_ACTIONS==='true'&&(values.profile||values['game-client'])) {
    throw new Error('GitHub Actions uses synthetic fixtures and test artwork only');
  }
  if(!values.plan&&values.engine==='gameface'){
    if(!values.player) throw new Error('Gameface Player is required. Set GAMEFACE_PATH or pass --player.');
    await fs.access(values.player);
  }
  const limit=values.limit===undefined?Infinity:Number(values.limit);
  assert(limit>0&&(limit===Infinity||Number.isInteger(limit)),'--limit must be a positive integer');
  const threshold=Number(values.threshold);
  assert(threshold>=0&&threshold<=1,'--threshold must be between 0 and 1');
  const out=values.plan?null:await reportPath(values);
  const source=path.resolve(values.source);
  const backend=startBackend(values.python,source,{profile:values.profile,gameClient:values['game-client']});
  let web, chromium;
  try {
    const inventory=await backend.ask('inventory');
    const tasks=planShard(plan(inventory,values),values.shard);
    const matrixSize=tasks.reduce((count,task)=>count+task.orders.length,0);
    const total=Math.min(limit,matrixSize);
    console.log(JSON.stringify({version:inventory.version,suite:values.suite,planned:total,available:matrixSize,
      profiles:new Set(tasks.map(task=>`${task.width}x${task.height}`)).size,ranges:[...new Set(tasks.map(task=>task.range))]}));
    if(values.plan) return;
    await fs.mkdir(path.dirname(out),{recursive:true});
    await fs.mkdir(out);
    const ledger=await fs.open(path.join(out,'results.ndjson'),'a');
    const state={version:inventory.version,engine:values.engine,renderer:null,suite:values.suite,planned:total,
      fixture:inventory.fixture||'synthetic',assets:values['game-client']?'local-game':'test-art',
      capture:values.capture,shard:values.shard||null,
      completed:0,failed:0,interactions:0,interactionErrors:0,visualFailures:0,missingBaselines:0,finished:false};
    const write=()=>fs.writeFile(path.join(out,'run.json'),JSON.stringify(state,null,2)+'\n');
    try {
      const compare=await makeComparer(values.baseline,out,threshold,state);
      web=await serve(source,inventory);
      if(values.engine==='chromium') chromium=await openChromium(values.chrome);
      const native=values.engine==='gameface'?require('./gameface-player.cjs'):null;
      let consecutive=0, handledProfiles=new Set();
      for(const profile of [...new Set(tasks.map(task=>`${task.width}x${task.height}`))]) {
        if(state.completed>=total) break;
        const [width,height]=profile.split('x').map(Number);
        const hostWidth=width+20,hostHeight=height+20;
        const surface={url:web.url,width:hostWidth,height:hostHeight,useWarhelios:!!values['game-client']};
        const driver=await (chromium?chromium.open(surface):native.launchGameface({
          ...surface,executable:path.resolve(values.player),allowVisible:!!values['player-visible']}));
        state.renderer=driver.version;
        state.windowMode=driver.windowMode||'headless';
        try {
          const ctx=session(driver,backend,inventory,out,{hostWidth,hostHeight},compare,screenshotOptions);
          let written=0;
          const record=async result=>{
            const newShots=ctx.screenshots.slice(written);written=ctx.screenshots.length;
            state.visualFailures+=newShots.filter(shot=>shot.visualFailure).length;
            state.missingBaselines+=newShots.filter(shot=>shot.missingBaseline).length;
            await ledger.appendFile(JSON.stringify({...result,shots:newShots})+'\n');
          };
          for(const task of tasks.filter(task=>`${task.width}x${task.height}`===profile)) {
            if(state.completed>=total) break;
            let prepared=false;
            for(const order of task.orders) {
              if(state.completed>=total) break;
              let result;
              try {
                if(!prepared) {await ctx.setup(task);prepared=true;}
                result=await runCase(ctx,task,order,inventory.version,values.capture); consecutive=0;
              }
              catch(error){
                const key=label(task)+'/'+variant(order);
                result={key,error:error.message};state.failed++;consecutive++;prepared=false;
                try {result.failureImage=await ctx.snapshot(key+'/failure');} catch(screenshotError){result.screenshotError=screenshotError.message;}
                console.error(`${key}: ${error.message}`);
              }
              state.completed++;
              await record(result);
              if(state.completed%20===0||state.completed===total) {await write();console.log(`${state.completed}/${total}, failures: ${state.failed}`);}
              if(consecutive>=8) throw new Error('Eight consecutive scenarios failed; see the diagnostic report');
            }
          }
          if(!values['matrix-only']&&(!values.shard||values.shard.startsWith('1/'))&&
              handledProfiles.size<(values.suite==='build'?1:2)&&!handledProfiles.has(height)){
            handledProfiles.add(height);
            const {runInteractions}=require('./interactions.cjs');
            const resultName='interactions/'+profile;
            const actionCtx={...ctx,resultName,snapshot:name=>values.capture==='failures'?Promise.resolve(null):ctx.snapshot(resultName+'/'+name)};
            state.interactions++;
            try{const result=await runInteractions(actionCtx,{width,height,language:'en'});await record({key:actionCtx.resultName,interactions:result});}
            catch(error){
              state.interactionErrors++; console.error(`${actionCtx.resultName}: ${error.message}`);
              const result={key:actionCtx.resultName,error:error.message};
              try{result.failureImage=await ctx.snapshot(resultName+'/failure');}
              catch(screenshotError){result.screenshotError=screenshotError.message;}
              await record(result);
            }
          }
          await write();
        } finally {await driver.close();}
      }
      state.finished=state.completed===total;
      const fail=state.failed||state.interactionErrors||state.visualFailures||state.missingBaselines;
      if(fail) process.exitCode=1;
    } finally {await write();await ledger.close();await writeReport(out,state);console.log(out);}
  } finally {
    try{if(chromium) await chromium.close();}
    finally{try{if(web) await web.close();}finally{await backend.close();}}
  }
}

main().catch(error=>{console.error(error.message);process.exitCode=1;});
