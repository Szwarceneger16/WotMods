/* An owned native rail remains visible, usable and bounded at both UI scales. */
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
const shipped=()=>fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8');
function sourceFunction(source,name){const start=source.indexOf('    function '+name+'('),line=source.indexOf('\n',start);
  const end=source.slice(start,line).endsWith('}')?line:source.indexOf('\n    }\n',start)+7;
  assert(start>=0&&end>start,'Exercise actual shipped '+name);return source.slice(start,end);}
function assertScrollbarSource(source=shipped()){
  const listeners=new Map(),events=[];
  class Node{
    constructor(){this.style={};this.attributes={};this.classList={add(){},remove(){}};}
    setAttribute(key,value){this.attributes[key]=String(value);}contains(node){return node===this;}
    addEventListener(name,callback){let list=listeners.get(this);if(!list)listeners.set(this,list=[]);list.push([name,callback]);}
    removeEventListener(name,callback){const list=listeners.get(this)||[];const index=list.findIndex(item=>item[0]===name&&item[1]===callback);if(index>=0)list.splice(index,1);}
  }
  const scroll=new Node(),rail=new Node(),thumb=new Node(),groups=new Node(),root=new Node(),document=new Node(),window=new Node();
  Object.assign(scroll,{scrollTop:0,scrollHeight:2000,clientHeight:400});
  let contentHeight=1990;
  scroll.getBoundingClientRect=()=>({top:100,height:400,width:700,bottom:500});
  root.getBoundingClientRect=()=>({top:0,height:730,width:700,bottom:730});
  groups.getBoundingClientRect=()=>({top:100-scroll.scrollTop,bottom:100+contentHeight-scroll.scrollTop,height:contentHeight,width:650});
  rail.getBoundingClientRect=()=>({top:parseFloat(rail.style.top)||102,height:parseFloat(rail.style.height)||396,width:10});
  thumb.getBoundingClientRect=()=>({top:rail.getBoundingClientRect().top+1+(parseFloat(thumb.style.top)||0),height:parseFloat(thumb.style.height)||0,width:8});
  window.innerWidth=1800;window.innerHeight=1200;window.getComputedStyle=()=>({paddingBottom:'10'});
  const nativeSizes=[];
  const state={destroyed:false,dialog:false,bound:true,nativeScale:1,scrollTarget:null,scrollSpeed:1,groupCards:[{}],
    payload:{viewport:{width:1800,height:1200}},logicalSize:{width:700,height:620},
    feed:{navigationPage:3,topRequested:true,prependAnchor:{},pending:{navigate:true}},pageJump:{},battleJump:{}};
  const context={state,nodes:{scroll,scrollbar:rail,'scrollbar-thumb':thumb,groups},root,document,window,
    hasNumber:value=>typeof value==='number'&&Number.isFinite(value),focusControl(){},
    consumeResizeInput(){events.push('handled');},loadNearEdges(){events.push('edges');},queueResize(){events.push('resize');},
    cancelBattleNavigation(){state.battleJump=null;},nativeDiagnostic(){},invoke(action,args){if(action==='resize')nativeSizes.push([args.width,args.height]);}};
  vm.createContext(context);
  const names=['windowSizeBounds','setLogicalSize','resizePanelDimensions','resizeNative','onScrollIntent','scrollbarMetrics','syncScrollbar','scrollFromScrollbar',
    'beginScrollbar','moveScrollbar','endScrollbar','scrollbarKey','scrollbarWheel','bindScrollbar'];
  vm.runInContext(names.map(name=>sourceFunction(source,name)).join('\n'),context);
  context.syncScrollbar();assert.strictEqual(rail.style.display,'block');assert.strictEqual(rail.attributes['aria-valuenow'],'0');
  assert(Math.abs(parseFloat(thumb.style.height)-78.8)<0.01,'Thumb represents the visible loaded fraction');
  context.scrollFromScrollbar(800);assert.strictEqual(scroll.scrollTop,800);assert.strictEqual(rail.attributes['aria-valuenow'],'50');
  assert.strictEqual(state.pageJump,null);assert.strictEqual(state.battleJump,null);assert.strictEqual(state.feed.topRequested,false);
  assert.strictEqual(state.feed.prependAnchor,null);assert.strictEqual(state.feed.pending.navigate,false);
  scroll.scrollHeight=5000;assert.strictEqual(context.scrollbarMetrics().maximum,1600,'Pinned filter overflow is excluded from the owned rail range');
  context.scrollbarKey({key:'End'});assert.strictEqual(scroll.scrollTop,1600);assert.strictEqual(rail.attributes['aria-valuenow'],'100');
  context.scrollbarKey({key:'Home'});assert.strictEqual(scroll.scrollTop,0);
  context.beginScrollbar({button:0,target:rail,clientY:450});assert.strictEqual(scroll.scrollTop,360,'Track presses move one viewport page');
  context.endScrollbar();context.beginScrollbar({button:0,target:thumb,clientY:thumb.getBoundingClientRect().top+5});
  context.moveScrollbar({clientY:10000});assert.strictEqual(scroll.scrollTop,1600,'Dragging beyond the rail clamps at its loaded end');
  context.moveScrollbar({clientY:-10000});assert.strictEqual(scroll.scrollTop,0);context.endScrollbar();
  context.beginScrollbar({button:0,target:thumb,clientY:thumb.getBoundingClientRect().top+5});
  context.endScrollbar({type:'mouseup',button:2});assert(state.scrollbarDrag,'Releasing another mouse button does not end a left-button drag');context.endScrollbar();
  context.beginScrollbar({button:0,target:thumb,clientY:thumb.getBoundingClientRect().top+5});
  context.moveScrollbar({type:'mousemove',buttons:0,clientY:10000});
  assert.strictEqual(scroll.scrollTop,0);assert.strictEqual(state.scrollbarDrag,null,'A missed native outside release is retired before returning movement');
  context.scrollbarWheel({deltaY:-1,deltaX:0,cancelable:true});assert.strictEqual(scroll.scrollTop,100,'Native wheel direction matches the result viewport');
  state.scrollTarget=null;scroll.scrollTop=0;contentHeight=100;context.syncScrollbar();
  assert.strictEqual(rail.attributes['aria-disabled'],'true');assert.strictEqual(rail.attributes.tabindex,'-1');
  assert.strictEqual(parseFloat(thumb.style.height),context.scrollbarMetrics().height,'Short result sets show a full disabled thumb');
  contentHeight=1990;context.bindScrollbar(true);
  const retained=(listeners.get(rail)||[]).find(item=>item[0]==='keydown')[1];
  state.destroyed=true;context.bindScrollbar(false);const before=scroll.scrollTop,count=events.length;
  retained({key:'End'});context.moveScrollbar({clientY:1000});context.syncScrollbar();
  assert.strictEqual(scroll.scrollTop,before);assert.strictEqual(events.length,count);
  assert([...listeners.values()].every(list=>list.length===0),'Cleanup removes every owned rail and document input listener');
  assert(source.includes('bindScrollbar(false);'),'Native cleanup retires scrollbar ownership');
  state.destroyed=false;
  const oldRootRect=root.getBoundingClientRect;root.getBoundingClientRect=()=>({top:0,width:700,height:620});context.resizeNative();
  assert.deepStrictEqual(nativeSizes[nativeSizes.length-1],[700,730],'A stale pre-minimum rectangle cannot shrink the native surface');
  state.payload.viewport={width:480,height:640};context.resizeNative();
  assert.deepStrictEqual(nativeSizes[nativeSizes.length-1],[460,620],'A stale pre-shrink rectangle cannot exceed the current game viewport');
  root.getBoundingClientRect=oldRootRect;state.payload.viewport={width:1800,height:1200};
  let size=context.resizePanelDimensions();assert.strictEqual(size.width,700);assert.strictEqual(size.height,730);
  assert.strictEqual(state.logicalSize.height,620,'Rendering the minimum does not rewrite a legacy saved size');
  state.payload.viewport={width:480,height:640};size=context.resizePanelDimensions();
  assert.strictEqual(size.width,460);assert.strictEqual(size.height,620);assert.strictEqual(state.logicalSize.width,700);
  state.payload.viewport={width:1800,height:1200};size=context.resizePanelDimensions();assert.strictEqual(size.width,700);assert.strictEqual(size.height,730);
  root.getBoundingClientRect=()=>({top:0,width:1,height:1});state.payload.viewport={width:1440,height:900};
  state.nativeScale=1.25;context.resizeNative();
  assert.deepStrictEqual(nativeSizes[nativeSizes.length-1],[875,880],'A one-pixel native surface uses the minimum and physical parent cap at 125 percent');
  state.nativeScale=1.5;context.resizeNative();
  assert.deepStrictEqual(nativeSizes[nativeSizes.length-1],[1050,880],'A fractional scale change keeps the physical height within the same parent cap');
  root.getBoundingClientRect=oldRootRect;state.nativeScale=1;state.payload.viewport={width:1800,height:1200};
  context.setLogicalSize(1,1,'se');assert.strictEqual(state.logicalSize.width,550);assert.strictEqual(state.logicalSize.height,730);
  state.nativeScale=2;state.payload.viewport={width:1000,height:1000};size=context.resizePanelDimensions();
  assert.strictEqual(size.width,490);assert.strictEqual(size.height,490,'A smaller scaled viewport overrides minimum display size safely');
  state.nativeScale=1;state.payload.viewport={width:1,height:1};window.innerWidth=1;window.innerHeight=1;
  size=context.resizePanelDimensions();assert.strictEqual(size.height,730,'An unknown first native viewport is not a smaller game window');
}
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let left=10;function next(){if(--left)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);}));
module.exports=async({browser,nativeHost,check})=>{
  assertScrollbarSource();check('Actual-source scrollbar ownership, native range and minimum-size regressions pass',true);
  for(const scale of [1,2]){
    const viewport={width:1800*scale,height:1200*scale,scale};
    const page=await nativeHost(browser,{initialViewport:{width:viewport.width,height:viewport.height},viewport});
    try{
      await page.evaluate(({viewport,scale})=>{const payload=JSON.parse(model.payload),scope=payload.scopes.launch,sample=scope.battles[0];
        payload.account_key='synthetic-scrollbar-'+scale;payload.viewport=viewport;payload.window_size=[900,1000];scope.period_id='synthetic-scrollbar-period';
        scope.data_revision='scrollbar:1';scope.battles=Array.from({length:40},(_,index)=>({...sample,id:'synthetic-scrollbar-'+index}));
        scope.pagination={battles:{page:0,pages:1,page_size:40,total:40}};scope.summary.battles=40;
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();document.getElementById('ss-group-battles').onclick();
      },{viewport,scale});await frames(page);
      const rail=page.locator('#ss-scrollbar'),thumb=page.locator('#ss-scrollbar-thumb'),label=' at '+(scale*100)+'%';
      check('The owned scrollbar remains visible independently of native pseudo-element paint'+label,
        await rail.isVisible()&&await rail.getAttribute('role')==='scrollbar'&&await rail.getAttribute('aria-disabled')==='false');
      await rail.focus();await rail.press('End');await frames(page);
      check('Scrollbar End reaches the visible final battle and updates its thumb'+label,await rail.getAttribute('aria-valuenow')==='100'&&await page.evaluate(()=>{
        const card=document.querySelector('#ss-groups .ss-group:last-child'),cards=[...document.querySelectorAll('#ss-groups .ss-group')],
          last=cards[cards.length-1].getBoundingClientRect(),scroll=document.getElementById('ss-scroll').getBoundingClientRect();
        const rail=document.getElementById('ss-scrollbar').getBoundingClientRect(),thumb=document.getElementById('ss-scrollbar-thumb').getBoundingClientRect();
        return last.bottom<=scroll.bottom+2&&last.bottom>=scroll.top&&Math.abs(rail.bottom-thumb.bottom)<=3*parseFloat(document.documentElement.style.fontSize);
      }));
      await rail.press('Home');await frames(page);const track=await rail.boundingBox();
      await page.mouse.click(track.x+track.width/2,track.y+track.height-8*scale);await frames(page);
      check('Track clicks move through the existing result list'+label,Number(await rail.getAttribute('aria-valuenow'))>0);
      const handle=await thumb.boundingBox();await page.mouse.move(handle.x+handle.width/2,handle.y+handle.height/2);await page.mouse.down();
      await page.mouse.move(track.x+track.width/2,track.y+track.height+100*scale);await page.mouse.up();await frames(page);
      check('Dragging beyond the rail clamps and leaves no captured gesture'+label,
        await rail.getAttribute('aria-valuenow')==='100'&&!await rail.evaluate(node=>node.classList.contains('is-dragging')));
      const grip=await page.locator('#ss-resize-grip').boundingBox(),panel=await page.locator('#grz-session-stats').boundingBox();
      await page.mouse.move(grip.x+grip.width/2,grip.y+grip.height/2);await page.mouse.down();
      await page.mouse.move(panel.x+40*scale,panel.y+40*scale);await page.mouse.up();await frames(page);
      const minimum=await page.locator('#grz-session-stats').boundingBox();
      check('Mouse resizing cannot shrink the window below the compact screenshot dimensions'+label,
        Math.abs(minimum.width-550*scale)<=1&&Math.abs(minimum.height-730*scale)<=1);
      const saves=await page.evaluate(()=>__grzCommands.filter(command=>command.action==='window_settings').length);
      const small={width:500*scale+20,height:600*scale+20,scale};await page.setViewportSize({width:small.width,height:small.height});
      await page.evaluate(viewport=>{const payload=JSON.parse(model.payload);payload.viewport=viewport;model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},small);await frames(page);
      check('A smaller game viewport clamps the minimum inside its own bounds'+label,await page.evaluate(({scale})=>{
        const box=document.getElementById('grz-session-stats').getBoundingClientRect();return Math.abs(box.width-500*scale)<=1&&Math.abs(box.height-600*scale)<=1;
      },{scale}));
      await page.setViewportSize({width:viewport.width,height:viewport.height});await page.evaluate(viewport=>{const payload=JSON.parse(model.payload);
        payload.viewport=viewport;model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},viewport);await frames(page);
      check('Growing the viewport restores the minimum without rewriting preferences'+label,await page.evaluate(({scale,saves})=>{
        const box=document.getElementById('grz-session-stats').getBoundingClientRect();return Math.abs(box.width-550*scale)<=1&&Math.abs(box.height-730*scale)<=1&&
          __grzCommands.filter(command=>command.action==='window_settings').length===saves;
      },{scale,saves}));
      await page.locator('#ss-maximize').click();await frames(page);
      await page.evaluate(()=>{const payload=JSON.parse(model.payload),scope=payload.scopes.launch;scope.battles=[];scope.summary.battles=0;
        scope.pagination.battles={page:0,pages:1,page_size:40,total:0};scope.data_revision='scrollbar:empty';
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();});await frames(page);
      check('An empty result set resets and disables the rail'+label,await rail.getAttribute('aria-disabled')==='true'&&await rail.getAttribute('aria-valuenow')==='0');
      await page.evaluate(()=>{window.__railBeforeDestroy=document.getElementById('ss-scroll').scrollTop;GRZSessionStats.destroy();
        document.getElementById('ss-scrollbar').dispatchEvent(new KeyboardEvent('keydown',{key:'End',bubbles:true}));
        document.dispatchEvent(new MouseEvent('mousemove',{clientY:10000,bubbles:true}));});
      check('Destroyed scrollbar input cannot mutate the retired result viewport'+label,await page.evaluate(()=>document.getElementById('ss-scroll').scrollTop===__railBeforeDestroy));
    }finally{await page.close();}
  }
};
module.exports.assertScrollbarSource=assertScrollbarSource;
if(require.main===module){assertScrollbarSource();console.log('Actual-source native scrollbar, cleanup, range and minimum-size regressions passed.');}
