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
const {viewportForPanel} = require('./screenshot.cjs');

const checkoutSource = path.resolve(__dirname, '../../../mods/sessionstats');
const sourceDefault = existsSync(path.join(checkoutSource,'VERSION')) ? checkoutSource :
  path.resolve(__dirname, '../WotMods-pr17-next/mods/sessionstats');
const standardWidths = [365,625,780,913,1120,1350,1800];
const routes = new Set(['since-sunday','history']);
const label = ({width,height,language,range,group}) => `${width}x${height}/${language}/${range}/${group}`;
const variant = order => [order.metric,order.statistic,order.direction,order.chronology].join('-');
const actionFields = ['metric','statistic','direction','chronology'];

async function applySortOrder(group, order, {wide, read, click, select, idle}) {
  const toggle='#ss-sort-off';
  const fields=['metric','chronology'];
  let actual=read();
  if(actual.chronology!==order.chronology || order.metric==='off') {
    if(actual.metric!=='off') {
      if(wide) await click(toggle);
      else await select('#ss-sort-metric','off');
    }
    if(read().chronology!==order.chronology) await select('#ss-sort-chronology',order.chronology);
  }
  if(order.metric!=='off') {
    if(wide&&read().metric==='off') await click(toggle);
    if(read().metric!==order.metric) await select('#ss-sort-metric',order.metric);
    fields.push('direction');
    if(read().direction!==order.direction) await select('#ss-sort-direction',order.direction);
    if(group!=='battles'&&order.metric!=='battles'&&order.metric!=='win_rate') {
      fields.push('statistic');
      if(read().statistic!==order.statistic) await select('#ss-sort-statistic',order.statistic);
    }
  }
  await idle();
  actual=read();
  for(const field of fields) assert.equal(actual?.[field],order[field],`Python did not accept ${field}`);
}

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

function resultPage(model, task) {
  const scope=model.scopes[task.scope], order=scope.ordering[task.group];
  const {page,page_size:pageSize,total}=scope.pagination[task.group];
  const offset=page*pageSize, rows=scope[task.group];
  const owner=JSON.stringify([model.account_key,task.scope,scope.period_id,scope.order_epoch,
    scope.data_revision,task.group,pageSize,total,...actionFields.map(field=>order[field])]);
  return {owner,page,offset,total,ids:rows.map(row=>String(row.id))};
}

async function resetScenarioScroll(driver) {
  await driver.evaluate(()=>{
    // Use the panel action so a queued layout cannot restore the previous
    // scenario's scroll offset after a direct scrollTop assignment.
    document.getElementById('ss-scroll-top').onclick();
    window.__localWheels=[];
  });
}

function session(driver, backend, inventory, out, hostSize, compare, screenshotOptions) {
  let size, model, currentPage, submitted = 0;
  const pythonPages = new Map();
  const screenshots = [];
  async function publish(payload) {
    model=decorate(payload,size);
    const accepted=await driver.evaluate(model=>window.__localPublish(model),model);
    assert(accepted,'Shipped panel rejected the Python payload');
    currentPage=resultPage(model,size);
    if(!pythonPages.has(currentPage.owner)) pythonPages.set(currentPage.owner,new Map());
    pythonPages.get(currentPage.owner).set(currentPage.page,currentPage);
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
    const scope=task.scope||inventory.ranges.find(range=>range.id===task.range).scope;
    size={...hostSize,...task,scope};
    model=null;
    pythonPages.clear();
    await collectActions();
    const payload=await backend.ask('setup',{range:task.range,group:task.group,language:task.language});
    assert(scope!=='manual'||!payload.scopes.timeline,'Timeline overrides the planned legacy manual scope');
    await publish(payload);
    const active=`#ss-scope-${scope==='timeline'?'manual':scope}`;
    await until(()=>driver.evaluate(()=>window.GRZSessionStats?.getState().nativeBound),'WoT host bridge was not bound');
    if(!await driver.evaluate(selector=>document.querySelector(selector)?.getAttribute('aria-pressed')==='true',active)) await click(active);
    const group='#ss-group-'+task.group;
    if(!await driver.evaluate(selector=>document.querySelector(selector)?.getAttribute('aria-pressed')==='true',group)) await click(group);
    await resetScenarioScroll(driver);
    await idle();
  }
  function orderFor(task) {
    return model?.scopes[task.scope]?.ordering[task.group];
  }
  async function applyOrder(task,order) {
    const wide=await driver.evaluate(()=>getComputedStyle(document.getElementById('ss-sort-off')).display!=='none');
    await applySortOrder(task.group,order,{wide,read:()=>orderFor(task),click,select,idle});
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
    resultPages:()=>({current:currentPage,pages:pythonPages.get(currentPage.owner)}),
    read:()=>model, count:()=>submitted, screenshots, check:(condition,explanation)=>assert(condition,explanation)};
}

function assertResultOrder({current,pages}, cards, wide) {
  const mounted=new Map();
  let previousPage=-1;
  for(const card of cards) {
    assert(/^\d+$/.test(card.page)&&/^\d+$/.test(card.index),'Result card is missing a page or list position');
    const page=Number(card.page), index=Number(card.index), expected=pages.get(page);
    assert(expected,`Panel mounted page ${page+1} without a matching Python response`);
    assert(page>=previousPage,'Mounted result pages are out of order');
    previousPage=page;
    const position=index-expected.offset;
    assert(position>=0&&position<expected.ids.length,`Result card at list position ${index+1} is outside page ${page+1}`);
    if(!mounted.has(page)) mounted.set(page,{positions:new Set(),lastInLane:[null,null],left:[null,null]});
    const rendered=mounted.get(page);
    assert(!rendered.positions.has(position),`Duplicate result card at list position ${index+1}`);
    rendered.positions.add(position);
    assert(card.id===expected.ids[position],`Rendered result order differs from Python on page ${page+1} at list position ${index+1}`);

    // Matrix cases leave cards collapsed. The two lanes then alternate in
    // Python order, with each lane flowing down independently.
    const lane=wide ? position%2 : 0;
    assert(card.lane===lane,`Result card at list position ${index+1} is in the wrong lane`);
    const prior=rendered.lastInLane[lane];
    assert(!prior||Number(prior.index)<index,'Result cards in one lane are out of order');
    assert(!prior||prior.top===null||card.top===null||prior.top<card.top,'Result cards in one lane appear in reverse vertical order');
    rendered.lastInLane[lane]=card;
    if(rendered.left[lane]===null) rendered.left[lane]=card.left;
  }
  if(current.ids.length) assert(mounted.has(current.page),`Panel did not mount Python page ${current.page+1}`);
  for(const [page,rendered] of mounted) {
    assert(rendered.positions.size===pages.get(page).ids.length,`Panel mounted only part of Python page ${page+1}`);
    const [left,right]=rendered.left;
    assert(left===null||right===null||left<right,'Result lanes are out of order across the panel');
  }
}

async function measure(driver) {
  return driver.evaluate(()=>{
    const get=id=>document.getElementById(id);
    const panel=get('grz-session-stats').getBoundingClientRect(),scroll=get('ss-scroll'),scrollBox=scroll.getBoundingClientRect();
    const filter=get('ss-filter-panel'), filterBox=filter.getBoundingClientRect(), sort=get('ss-sorting'), sortBox=sort.getBoundingClientRect();
    const pinned=filter.classList.contains('is-pinned');
    const contentTop=pinned ? Math.max(scrollBox.top,filterBox.bottom) : scrollBox.top;
    const contentBottom=scrollBox.bottom;
    const groups=get('ss-groups'), cards=Array.from(groups.querySelectorAll('.ss-group'));
    const rendered=[];
    // A translated filter can enlarge scrollHeight beyond the end of the list.
    const paddingBottom=parseFloat(getComputedStyle(scroll).paddingBottom)||0;
    const listRemaining=groups.getBoundingClientRect().bottom+paddingBottom-contentBottom;
    const remaining=Math.max(0,Math.min(scroll.scrollHeight-scroll.clientHeight-scroll.scrollTop,listRemaining));
    let visible=0, resultsTop=null, resultsReached=false;
    for(const card of cards) {
      const box=card.getBoundingClientRect();
      const validLayout=box.width>0&&box.height>0;
      const parent=card.parentNode;
      let section=parent;
      while(section!==groups&&!section.hasAttribute('data-page-index')) section=section.parentNode;
      rendered.push({id:card.getAttribute('data-group-id'),index:card.getAttribute('data-list-index'),
        page:section===groups?null:section.getAttribute('data-page-index'),
        lane:parent.classList.contains('ss-card-column-left')?0:parent.classList.contains('ss-card-column-right')?1:null,
        top:validLayout?box.top:null,left:validLayout?box.left:null});
      if(box.width<=0||box.height<=0) continue;
      const top=Math.max(contentTop,box.top), bottom=Math.min(contentBottom,box.bottom);
      const left=Math.max(scrollBox.left,box.left), right=Math.min(scrollBox.right,box.right);
      if(right<=left+1) continue;
      const intersects=bottom>top+1;
      if(!intersects&&resultsTop!==null&&box.top>=resultsTop) continue;
      const style=getComputedStyle(card);
      const hidden=style.visibility==='hidden'||style.visibility==='collapse'||(style.opacity&&Number(style.opacity)===0);
      if(!hidden) {
        resultsTop=resultsTop===null ? box.top : Math.min(resultsTop,box.top);
      }
      if(!intersects) continue;
      resultsReached=true;
      if(hidden) continue;
      const y=(top+bottom)/2;
      if([0.5,0.25,0.75].some(ratio=>card.contains(document.elementFromPoint(left+(right-left)*ratio,y)))) visible++;
    }
    const controls=Array.from(sort.querySelectorAll('.ss-select-trigger,#ss-sort-off')).filter(node=>{
      const box=node.getBoundingClientRect();
      return box.width>0&&box.height>0&&(box.left<sortBox.left-1||box.right>sortBox.right+1||box.top<sortBox.top-1||box.bottom>sortBox.bottom+1);
    });
    let wheelAt=null;
    for(const yRatio of [0.65,0.80,0.40]) for(const xRatio of [0.66,0.32,0.50]) {
      const x=Math.round(scrollBox.left+scrollBox.width*xRatio),y=Math.round(scrollBox.top+scrollBox.height*yRatio);
      if(!wheelAt&&scroll.contains(document.elementFromPoint(x,y))) wheelAt={x,y};
    }
    return {width:panel.width,height:panel.height,top:Math.round(scroll.scrollTop),remaining,
      visible,resultsTop,resultsReached,contentTop,contentBottom,
      rendered,wide:groups.classList.contains('ss-two-columns'),
      mounted:cards.length,wheelAt,layout:get('ss-list-controls').getAttribute('data-filter-layout'),
      group:document.querySelector('.ss-group-tab[aria-pressed="true"]')?.id.slice('ss-group-'.length),
      version:get('ss-version').textContent,overflow:controls.length,warning:getComputedStyle(get('ss-sort-data-warning')).display!=='none',
      pinned,filterInside:filterBox.top>=scrollBox.top-1&&filterBox.bottom<=scrollBox.bottom+1,
      wheels:window.__localWheels.slice(),errors:window.__localErrors.slice()};
  });
}

async function runCase(ctx, task, order, version, capture) {
  await ctx.applyOrder(task,order);
  await resetScenarioScroll(ctx.driver);
  await ctx.idle();
  const phases=[];
  const root=label(task)+'/'+variant(order);
  for(let step=0;step<=3;step++) {
    const previous=phases[step-1];
    if(step) {
      const at=previous.wheelAt;
      assert(at,'No visible point in the primary scrolling view');
      await ctx.driver.wheel(at.x,at.y,-120);
      await ctx.idle();
    }
    const expected=ctx.resultPages();
    const {rendered,wide,...state}=await measure(ctx.driver);
    assert(Math.abs(state.width-task.width)<=1 && Math.abs(state.height-task.height)<=1,`Wrong rendered size ${state.width}x${state.height}`);
    assert.equal(state.group,task.group);
    assert.equal(state.version,'v'+version);
    assert(!state.overflow,`${state.overflow} filter controls overflow their container`);
    assert(!state.pinned||state.filterInside,'Pinned filters escaped the scroll viewport');
    assert.deepEqual(state.errors,[]);
    assert.equal(state.wheels.length,step,`Wrong number of wheel events after step ${step}`);
    assert(state.wheels.every(event=>event.trusted&&event.delta<0),'Wheel events did not reach the panel using native input');
    if(!step) assert.equal(state.top,0,`Viewport started at ${state.top} px after the panel's back-to-top action`);
    else {
      assert(state.top>=previous.top,'Scrolling reversed unexpectedly');
      assert(previous.remaining<=1||state.top>previous.top,
        `Wheel ${step} did not move the primary scroll viewport with ${Math.round(previous.remaining)} px available`);
    }
    if(expected.current.total>0) {
      assert(state.mounted>0,'Python returned results but the panel mounted no cards');
      assert(state.resultsTop!==null,'Python returned results but no result card has visible layout');
      if(state.resultsReached) assert(state.visible>0,'The results area is visible without any result cards');
    } else {
      assert.equal(state.mounted,0,'The panel retained result cards for an empty Python response');
    }
    assertResultOrder(expected,rendered,wide);
    if(capture==='all'||(capture==='final'&&step===3)) state.image=await ctx.snapshot(root+'/'+step);
    phases.push(state);
  }
  const last=phases.at(-1);
  if(last.mounted>0&&!phases.some(phase=>phase.visible>0)) {
    // The compact summary can still be taller than three wheel movements.
    // A clipped card must lie below the viewport and within its scroll range.
    assert(last.contentBottom>last.contentTop+1&&last.resultsTop>=last.contentBottom-1&&
      last.resultsTop<last.contentBottom+last.remaining-1,
      'No result card appeared in the viewport or can be reached below it');
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
    'jpeg-quality':{type:'string'},shard:{type:'string'},commit:{type:'string'}};
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
    '  --commit SHA records the checked-out CI commit in the report\n' +
    '  --player-visible allows a Gameface Player desktop window if it cannot run hidden');return;}
  if(!['gameface','chromium'].includes(values.engine)||!['full','smoke','build'].includes(values.suite)) throw new Error('Unknown engine or suite');
  assert(['all','final','failures'].includes(values.capture),'Invalid screenshot capture mode');
  assert(values.commit===undefined||/^[a-f0-9]{40}$/.test(values.commit),'Invalid matrix commit SHA');
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
    const state={version:inventory.version,commit:values.commit,engine:values.engine,renderer:null,suite:values.suite,planned:total,
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
        const {width:hostWidth,height:hostHeight}=viewportForPanel(width,height);
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

if(require.main===module) main().catch(error=>{console.error(error.message);process.exitCode=1;});

module.exports={applySortOrder,runCase};
