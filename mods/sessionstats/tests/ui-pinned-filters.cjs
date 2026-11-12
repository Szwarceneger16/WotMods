/* Pinning uses normal-flow geometry, independent of native scroll/paint order. */
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
const shipped=()=>fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8');
function actual(source,name){const start=source.indexOf('    function '+name+'('),end=source.indexOf('\n    }\n',start)+7;
  assert(start>=0&&end>start,'Exercise shipped '+name);return source.slice(start,end);}
function fixture(source=shipped(),scale=1){
  let getter=0,paint=0,origin=200*scale,height=3000*scale,foreignRect=0,styles=0;
  const frames=[],classes=new Set(),style={};
  Object.defineProperty(style,'transform',{get(){return style.value||'';},set(value){styles++;style.value=value;}});
  const scroll={clientHeight:500*scale,scrollHeight:5000*scale,
    get scrollTop(){return getter;},set scrollTop(value){getter=value;},
    getBoundingClientRect:()=>({top:100*scale,bottom:600*scale,height:500*scale,width:700*scale})};
  const state={destroyed:false,nativeScale:scale,filterShift:0,filterBase:null,scrollTarget:null,
    renderedFeed:null,groupCards:[{}],cardPages:[],battleJump:null,pageJump:null};
  const panel={offsetParent:scroll,get offsetTop(){return origin;},offsetHeight:80*scale,style,
    classList:{contains:name=>classes.has(name),add:name=>classes.add(name),remove:name=>classes.delete(name)},
    getBoundingClientRect:()=>({top:100*scale+origin-paint+state.filterShift+foreignRect,width:700*scale,height:80*scale})};
  const groups={offsetParent:scroll,get offsetTop(){return origin+80*scale;},get offsetHeight(){return height;},
    getBoundingClientRect:()=>({top:100*scale+origin+80*scale-paint+foreignRect,
      bottom:100*scale+origin+80*scale+height-paint+foreignRect,width:700*scale,height})};
  const context={state,nodes:{scroll,groups,'filter-panel':panel},Math,hasNumber:value=>typeof value==='number'&&Number.isFinite(value),
    window:{requestAnimationFrame:callback=>frames.push(callback),getComputedStyle:()=>({paddingBottom:String(10*scale)})},
    updateFeedControls(){},syncScrollbar(){},
    queueResize(){throw Error('Pin-only settlement must not resize the native view');},loadNearEdges(){throw Error('Pin-only settlement must not rebuild/load results');}};
  vm.createContext(context);
  for(const name of ['battleLayoutOffset','battleScrollPending','normalFlowScrollMaximum','queuePinnedFilters','updatePinnedFilters'])vm.runInContext(actual(source,name),context);
  return {state,context,scroll,panel,frames,classes,
    sample(raw,physical){getter=raw*scale;paint=physical*scale;},moveOrigin(value){origin=value*scale;},
    stale(value){foreignRect=value*scale;},grow(value){height=value*scale;},
    tick(){assert(frames.length,'An owned follow-up frame is pending');frames.shift()();},
    settle(){let count=0;while(frames.length&&count++<20)frames.shift()();assert(count<20,'Pin work has a bounded frame lifetime');},
    top(){return panel.getBoundingClientRect().top;},styles:()=>styles};
}
function assertPinnedFilterSource(source=shipped()){
  for(const scale of [1,1.25,2])for(const phase of ['getter-late','paint-late']){
    const view=fixture(source,scale);view.sample(700,700);view.context.updatePinnedFilters(true);view.settle();
    assert.strictEqual(view.top(),100*scale,'An initially pinned bar reaches the viewport top');
    view.sample(phase==='getter-late'?1000:1500,phase==='getter-late'?1500:1000);
    view.context.updatePinnedFilters(true);
    assert.strictEqual(view.state.filterBase,200*scale,'A mixed '+phase+' sample cannot relearn the origin from its translated rectangle');
    view.tick();view.tick();view.sample(1500,1500);view.settle();
    assert.strictEqual(view.top(),100*scale,'The bar returns to the top after '+phase+' acknowledgement without another scroll event');
    assert.strictEqual(view.scroll.scrollTop,1500*scale,'Mixed native rectangles cannot clamp a valid scroll offset');
    assert(view.classes.has('is-pinned'));
    view.stale(-4000);view.context.updatePinnedFilters(true);
    assert.strictEqual(view.state.filterBase,200*scale,'A stale native rectangle cannot poison later filter measurements');
    assert.strictEqual(view.scroll.scrollTop,1500*scale,'A stale content rectangle cannot manufacture an empty scroll range');
    view.stale(0);view.grow(4000);view.moveOrigin(260);view.context.updatePinnedFilters(true);view.settle();
    assert.strictEqual(view.top(),100*scale,'A loading/reflow origin change uses the new normal-flow position');
  }
  const burst=fixture(source);burst.sample(800,800);
  for(let index=0;index<20;index++)burst.context.updatePinnedFilters(index%2===0);
  assert.strictEqual(burst.frames.length,1,'Fast scroll notifications coalesce into one pin-only follow-up');
  burst.settle();assert.strictEqual(burst.frames.length,0);assert.strictEqual(burst.state.pinnedFilterWork,null);
  assert.strictEqual(burst.styles(),1,'Repeated settled pin measurements do not rewrite the same transform');
  const delayed=fixture(source);delayed.sample(900,1200);delayed.context.updatePinnedFilters(true);
  for(let index=0;index<12;index++)delayed.tick();
  assert(delayed.state.pinnedFilterWork,'A native getter that lags more than eight frames retains bounded settlement');
  delayed.sample(1200,1200);delayed.settle();assert.strictEqual(delayed.top(),100,'A later getter acknowledgement still pins without another event');
  const unavailable=fixture(source);unavailable.sample(900,1200);unavailable.context.updatePinnedFilters();
  let attempts=0;while(unavailable.frames.length&&attempts++<70)unavailable.tick();
  assert(attempts===60&&!unavailable.state.pinnedFilterWork,'Permanently mismatched native samples retire one bounded pin-only frame budget');
  burst.sample(10,10);burst.context.updatePinnedFilters();burst.settle();
  assert.strictEqual(burst.state.filterShift,0,'Returning above the filter origin removes its translation');
  assert(!burst.classes.has('is-pinned'));
  burst.sample(800,800);burst.context.updatePinnedFilters();const retained=burst.frames.shift(),writes=burst.styles();
  burst.state.destroyed=true;burst.state.pinnedFilterWork=null;retained();
  assert.strictEqual(burst.styles(),writes,'A retained pin callback cannot mutate a destroyed view');
  const optional=fixture(source),originalRAF=optional.context.window.requestAnimationFrame;
  optional.sample(800,800);optional.context.updatePinnedFilters();
  optional.context.window.requestAnimationFrame=undefined;
  optional.tick();
  assert.strictEqual(optional.state.pinnedFilterWork,null,'A retained pin callback retires ownership when optional RAF disappears');
  assert.strictEqual(optional.frames.length,0,'Unavailable RAF does not leave follow-up work queued');
  optional.context.window.requestAnimationFrame=originalRAF;
  optional.context.updatePinnedFilters();
  assert.strictEqual(optional.frames.length,1,'Restored RAF lets a newer scroll own fresh pin work');
  optional.settle();assert.strictEqual(optional.state.pinnedFilterWork,null);
}
module.exports={assertPinnedFilterSource};
if(require.main===module){assertPinnedFilterSource();console.log('Actual-source fast pinning, mixed native frames, normal-flow bounds and coalescing passed.');}
