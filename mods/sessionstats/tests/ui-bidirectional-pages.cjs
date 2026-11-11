/* Mid-history entry supports earlier pages, stable prepends and a true Top. */
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
const shipped=()=>fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8');
function sourceFunction(source,name){const start=source.indexOf('    function '+name+'('),line=source.indexOf('\n',start);
  const end=source.slice(start,line).endsWith('}')?line:source.indexOf('\n    }\n',start)+7;
  assert(start>=0 && end>start,'Exercise actual shipped '+name);return source.slice(start,end);}

function assertBidirectionalSource(source=shipped()){
  class Node{
    constructor(className='',height=0){this.className=className;this.children=[];this.parentNode=null;this.height=height;this.style={};this.attributes={};}
    get firstChild(){return this.children[0]||null;}get firstElementChild(){return this.firstChild;}
    get nextElementSibling(){return this.parentNode&&this.parentNode.children[this.parentNode.children.indexOf(this)+1]||null;}
    appendChild(node){return this.insertBefore(node,null);}
    insertBefore(node,before){if(node===before)return node;if(node.parentNode)node.parentNode.removeChild(node);const index=before===null?this.children.length:this.children.indexOf(before);
      assert(index>=0);this.children.splice(index,0,node);node.parentNode=this;return node;}
    removeChild(node){const index=this.children.indexOf(node);assert(index>=0);this.children.splice(index,1);node.parentNode=null;return node;}
    contains(node){return node===this||this.children.some(child=>child.contains(node));}
    setAttribute(name,value){this.attributes[name]=String(value);}getAttribute(name){return this.attributes[name]||null;}removeAttribute(name){delete this.attributes[name];}
    querySelectorAll(selector){return this.children.flatMap(child=>(child.className.split(/\s+/).includes(selector.slice(1))?[child]:[]).concat(child.querySelectorAll(selector)));}
    querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
    extent(){return this.height||this.children.reduce((total,child)=>total+child.extent(),0);}
    getBoundingClientRect(){let top=this===groups?200-scroll.scrollTop:this.parentNode?this.parentNode.getBoundingClientRect().top:0;
      if(this.parentNode)for(const child of this.parentNode.children){if(child===this)break;top+=child.extent();}
      return {top,bottom:top+this.extent(),height:this.extent(),width:900};}
  }
  const groups=new Node(),scroll={scrollTop:400,clientHeight:500,get scrollHeight(){return 200+groups.extent();},getBoundingClientRect(){return {top:0,bottom:500,height:500,width:900};}};
  const controls={},nodes={groups,scroll,'scroll-top':new Node(),'list-meta':new Node()},scheduled=[],timers=new Map(),commands=[];
  let nextTimer=0,resizes=0,dismissed=0;
  const state={scope:'launch',group:'battles',nativeSession:true,nativeScale:1,feedSequence:0,feedForceStart:null,
    pageJump:null,battleJump:null,scrollTarget:null,xp:'base',language:'en',appearanceCSS:'',payload:{account_key:'synthetic-midfeed'},cardPages:[],groupCards:[],list:[]};
  let scope={period_id:'synthetic-midfeed-period',data_revision:1,summary:{battles:205},ordering:{battles:{metric:'off',statistic:'avg',direction:'desc',chronology:'newest'}}};
  const rows=index=>Array.from({length:index===5?5:40},(_,offset)=>({id:'synthetic-midfeed-'+(index*40+offset)}));
  const context={state,nodes,Date,Math,Object,JSON,Number,String,hasNumber:value=>typeof value==='number'&&isFinite(value),
    document:{getElementById:id=>controls[id]||(controls[id]=new Node())},
    window:{requestAnimationFrame:fn=>scheduled.push(fn),setTimeout(fn){const id=++nextTimer;timers.set(id,fn);return id;},clearTimeout:id=>timers.delete(id)},
    currentScope:()=>scope,scopeName:()=>state.scope,getOrder:()=>scope.ordering.battles,
    viewContext:()=>({account_key:state.payload.account_key,scope:state.scope,period_id:scope.period_id}),
    sameContext:owned=>!state.destroyed&&owned.account_key===state.payload.account_key&&owned.scope===state.scope&&owned.period_id===scope.period_id,
    append:(parent,node)=>parent.appendChild(node),element:(tag,className)=>new Node(className,/ss-page-divider/.test(className)?20:/ss-page-spinner/.test(className)?30:0),
    invoke:(action,args)=>{commands.push({action,...args});return true;},setStatus(){},renderSelects(){},renderFilterActivity(){},t:key=>key,number:String,date:String,
    invalidateCardFlow(){},clear:node=>node.children.slice().forEach(child=>node.removeChild(child)),stageFeedContext(){},
    ordered:items=>items,layoutBattleCards(){},queueResize(){resizes++;},pinnedFilterHeight:()=>50,
    cancelBattleNavigation(){state.battleJump=null;},clearBattleTarget(){dismissed++;},
    resetViewScroll(){state.scrollTarget=0;scroll.scrollTop=0;},updatePinnedFilters(){},
    createCardPage(index,items,feed){const section=context.pageBoundary(feed,index,false);section.height=1000;groups.appendChild(section);
      return {index,section,columns:new Node(),items,cards:[],lanes:[new Node(),new Node()]};},
    appendGroupBatch(count,page){page.cards=page.items.slice(0,count).map(()=>new Node('ss-group',20));state.groupCards=state.groupCards.concat(page.cards);},
    render(){context.renderGroups(scope);}};
  vm.createContext(context);
  for(const name of ['feedCollectionIdentity','feedIdentity','feedContextIdentity','cancelUITimer','retireFeed','captureFeedAnchor','finishFeedAnchor',
    'revealFeedTop','pageBoundary','showFeedPending','requestFeedPage','prepareFeed','updateFeedControls','renderGroups','loadNearEdges','onScrollIntent','changePage'])
    vm.runInContext(sourceFunction(source,name),context);
  const topStart=source.indexOf("    if (nodes['scroll-top']) { nodes['scroll-top'].onclick = function () {",source.indexOf('    function changePage('));
  const topEnd=source.indexOf('    function switchXP(',topStart);assert(topStart>=0&&topEnd>topStart);
  vm.runInContext(source.slice(topStart,topEnd),context);
  const flush=()=>{for(let count=0;scheduled.length&&count<100;count++)scheduled.shift()();assert(scheduled.length===0);};
  const reply=(index,request)=>{scope.battles=rows(index);scope.pagination={battles:{page:index,pages:6,page_size:40,total:205}};
    if(request)scope.pagination.battles.request_id=request.id;context.renderGroups(scope);flush();};
  const start=()=>{context.retireFeed();groups.children.slice().forEach(child=>groups.removeChild(child));state.renderedFeed=null;state.groupCards=[];state.cardPages=[];
    state.scrollTarget=null;scroll.scrollTop=400;scope.data_revision++;reply(3);scroll.scrollTop=200;state.scrollTarget=null;};
  start();const original=state.cardPages[0],position=original.section.getBoundingClientRect().top;
  context.loadNearEdges();flush();let request=state.feed.pending;
  assert.strictEqual(request.page,2,'The upper edge of page four requests page three');
  assert.strictEqual(original.section.getBoundingClientRect().top,position,'An upper loading boundary preserves the visible result');
  context.loadNearEdges();flush();assert.strictEqual(state.feed.pending,request,'Repeated upper scroll events coalesce the request');
  reply(2,request);
  assert.strictEqual(state.feed.start,2);assert.strictEqual(state.cardPages.length,2);
  assert.strictEqual(state.cardPages[1],original,'Prepending retains the original page and selected card nodes');
  assert.strictEqual(original.section.getBoundingClientRect().top,position,'Earlier results preserve the current viewport');
  assert.strictEqual(state.groupCards.length,80);
  // The upper edge remains reachable using either wheel or the scrollbar.
  state.feed.prependAnchor=null;state.scrollTarget=null;scroll.scrollTop=200;
  context.loadNearEdges();flush();request=state.feed.pending;assert.strictEqual(request.page,1);
  timers.get(request.timer)();assert.strictEqual(state.feed.error,1,'Failed earlier pages retain a retry state');
  const retry=groups.querySelector('.ss-page-status').children[0];retry.onclick();flush();
  const retried=state.feed.pending;assert.notStrictEqual(retried.id,request.id,'Earlier-page Retry owns a fresh request identity');
  reply(1,retried);assert.strictEqual(state.feed.start,1);assert.strictEqual(state.groupCards.length,120);
  // Start afresh to put Top in a race with an already-sent earlier-page fetch.
  start();context.loadNearEdges();flush();const retired=state.feed.pending;
  nodes['scroll-top'].onclick();flush();const top=state.feed.pending;
  assert.strictEqual(top.page,0,'Top requests the real first page from a mid-history window');
  assert.notStrictEqual(top.id,retired.id);assert(!timers.has(retired.timer),'Top retires the superseded request timeout');
  reply(2,retired);assert.strictEqual(state.feed.pending,top,'A late previous-page response cannot replace the Top request');
  reply(0,top);assert.strictEqual(state.feed.start,0);assert.strictEqual(state.feed.last,0);
  assert.strictEqual(state.cardPages.length,1);assert.strictEqual(state.cardPages[0].index,0);
  assert.strictEqual(scroll.scrollTop,0,'Top settles at the complete summary and first result page');
  assert.strictEqual(scope.ordering.battles.chronology,'newest','Top preserves the selected ordering');
  reply(2,retired);assert.strictEqual(state.cardPages[0].index,0);assert.strictEqual(scroll.scrollTop,0,'Late replies do not revive the retired destination');
  // The cancelled direct jump may cache page zero without joining a gap.
  start();nodes['scroll-top'].onclick();flush();const cancelled=state.feed.pending;
  context.onScrollIntent({type:'wheel'});state.scrollTarget=null;scroll.scrollTop=370;
  const cancelledPosition=state.cardPages[0].section.getBoundingClientRect().top;reply(0,cancelled);
  assert.strictEqual(state.feed.start,3);assert.strictEqual(state.feed.last,3);
  assert.strictEqual(state.cardPages[0].section.getBoundingClientRect().top,cancelledPosition,'Newer scroll intent cancels a pending Top destination');
  assert(state.feed.cache[0],'The cancelled destination can still populate its owned cache');
  // Reusing page zero needs no second backend request.
  const before=commands.length;nodes['scroll-top'].onclick();flush();assert.strictEqual(commands.length,before);assert.strictEqual(state.cardPages[0].index,0);
  assert.strictEqual(scroll.scrollTop,0);assert(dismissed>=3);assert(resizes>0);
  let pinnedWrites=0;context.updatePinnedFilters=()=>{pinnedWrites++;};state.destroyed=true;
  context.loadNearEdges();flush();assert.strictEqual(commands.length,before);assert.strictEqual(pinnedWrites,0,'A retained scroll listener cannot fetch or repaint after teardown');
  assert(source.includes("nodes.scroll.removeEventListener('scroll', queueScrollEdges);"),'Cleanup removes its exact deferred edge-loading listener');
}

const frames=page=>page.evaluate(()=>new Promise(resolve=>{let left=10;function next(){if(--left)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);}));
module.exports=async({browser,nativeHost,check})=>{
  assertBidirectionalSource();check('Actual-source midfeed paging, anchor, Retry and Top-race regressions pass',true);
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:2400,height:1800},viewport:{width:2400,height:1800,scale}});
    const label=' at '+(scale*100)+'%',requests=()=>page.evaluate(()=>__grzCommands.filter(item=>item.action==='page'));
    const emit=async(index,request)=>{await page.evaluate(({index,request})=>{
      const payload=JSON.parse(model.payload),scope=payload.scopes.launch;scope.battles=Array.from({length:index===5?5:40},(_,offset)=>({
        ...__midfeedSample,id:'synthetic-midfeed-'+(index*40+offset),name:'Synthetic battle '+(index*40+offset),started_at:1900000000-index*40-offset}));
      scope.pagination.battles={page:index,pages:6,page_size:40,total:205};if(request)scope.pagination.battles.request_id=request.request_id;
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
    },{index,request});await frames(page);};
    try{
      await page.evaluate(scale=>{const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
        window.__midfeedSample=JSON.parse(JSON.stringify(scope.battles[0]));payload.account_key='synthetic-midfeed-'+scale;
        payload.window_size=[900,700];payload.viewport={width:2400,height:1800,scale};scope.period_id='synthetic-midfeed-period';
        scope.data_revision='midfeed:1';scope.summary.battles=205;scope.pagination={battles:{page:3,pages:6,page_size:40,total:205}};
        scope.ordering={battles:{metric:'off',statistic:'avg',direction:'desc',chronology:'newest'}};delete scope.battle_focus;
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();document.getElementById('ss-group-battles').onclick();
      },scale);
      // The acknowledged native battle selection enters the fourth page.
      await page.evaluate(()=>{const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
        window.__grzCommands=[];window.__midfeedReady=payload;
        const button=document.querySelector('#ss-groups .ss-group');
        // A new period owns its native initial page, as a selected result does.
        scope.period_id='synthetic-midfeed-selected';model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      });await emit(3);
      check('A native mid-history snapshot starts with page four'+label,await page.locator('.ss-continuous-page[data-page-index="3"] .ss-group').count()===40);
      const original=page.locator('.ss-continuous-page[data-page-index="3"]');
      await page.evaluate(()=>{const first=document.querySelector('.ss-continuous-page[data-page-index="3"]'),scroll=document.getElementById('ss-scroll');
        scroll.scrollTop+=first.getBoundingClientRect().top-scroll.getBoundingClientRect().top-document.getElementById('ss-filter-panel').getBoundingClientRect().height+80;
        scroll.dispatchEvent(new Event('scroll'));});await frames(page);
      let sent=await requests(),request=sent[sent.length-1];
      check('Scrolling upward from page four requests the preceding page'+label,request&&request.page==='2');
      const before=await original.evaluate(node=>node.getBoundingClientRect().top);
      await emit(2,request);
      const after=await original.evaluate(node=>node.getBoundingClientRect().top);
      check('Prepending forty earlier battles preserves the visible result and unique rows'+label+': '+JSON.stringify({before,after}),
        Math.abs(after-before)<=1 && await page.locator('#ss-groups .ss-group').count()===80 &&
        await page.locator('#ss-groups .ss-group').evaluateAll(cards=>new Set(cards.map(card=>card.dataset.groupId)).size)===80);
      await page.evaluate(()=>{const first=document.querySelector('.ss-continuous-page[data-page-index="2"]'),scroll=document.getElementById('ss-scroll');
        scroll.scrollTop+=first.getBoundingClientRect().top-scroll.getBoundingClientRect().top-document.getElementById('ss-filter-panel').getBoundingClientRect().height+80;
        scroll.dispatchEvent(new Event('scroll'));});await frames(page);
      sent=await requests();const previous=sent[sent.length-1];check('The next upward boundary requests page two'+label,previous.page==='1');
      await page.evaluate(()=>document.getElementById('ss-scroll-top').onclick());await frames(page);
      sent=await requests();request=sent[sent.length-1];check('Top supersedes an earlier-page request with the real page one'+label,request.page==='0'&&request.request_id!==previous.request_id);
      await emit(1,previous);check('A late earlier-page reply leaves the Top destination pending'+label,await page.locator('.ss-continuous-page[data-page-index="0"].ss-page-pending').count()===1);
      await emit(0,request);check('Top displays page one and the complete summary without changing Newest first'+label,
        await page.locator('.ss-continuous-page[data-page-index="0"] .ss-group').count()===40 &&
        await page.locator('.ss-continuous-page[data-page-index="3"]').count()===0 &&
        await page.locator('#ss-scroll').evaluate(node=>Math.abs(node.scrollTop)<=1) &&
        await page.locator('#ss-sort-chronology .ss-select-trigger').textContent()==='Newest first');
      await emit(1,previous);check('A retired reply cannot move the viewport after Top'+label,await page.locator('#ss-scroll').evaluate(node=>Math.abs(node.scrollTop)<=1));
    }finally{await page.close();}
  }
};
module.exports.assertBidirectionalSource=assertBidirectionalSource;
if(require.main===module){assertBidirectionalSource();console.log('Actual-source bidirectional paging, stable prepend, Retry and Top ownership regressions passed.');}
