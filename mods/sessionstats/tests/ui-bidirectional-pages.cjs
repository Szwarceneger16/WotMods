/* Mid-history entry supports earlier pages, stable prepends and a true Top. */
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
const shipped=()=>fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8').replace(/\r\n/g,'\n');
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
    pageJump:null,pageJumpTimer:null,battleJump:null,scrollTarget:null,xp:'base',language:'en',appearanceCSS:'',payload:{account_key:'synthetic-midfeed',scopes:{}},cardPages:[],groupCards:[],list:[]};
  let scope={period_id:'synthetic-midfeed-period',data_revision:1,summary:{battles:205},ordering:{battles:{metric:'off',statistic:'avg',direction:'desc',chronology:'newest'}}};
  const rows=index=>Array.from({length:index===5?5:40},(_,offset)=>({id:'synthetic-midfeed-'+(index*40+offset)}));
  const context={state,nodes,Date,Math,Object,JSON,Number,String,hasNumber:value=>typeof value==='number'&&isFinite(value),
    document:{getElementById:id=>controls[id]||(controls[id]=new Node())},
    window:{requestAnimationFrame:fn=>scheduled.push(fn),setTimeout(fn){const id=++nextTimer;timers.set(id,fn);return id;},clearTimeout:id=>timers.delete(id)},
    currentScope:()=>scope,scopeName:()=>state.scope,getOrder:()=>state.orderIntent?state.orderIntent.options:scope.ordering.battles,
    viewContext:()=>({account_key:state.payload.account_key,scope:state.scope,period_id:scope.period_id}),
    sameContext:owned=>!state.destroyed&&owned.account_key===state.payload.account_key&&owned.scope===state.scope&&owned.period_id===scope.period_id,
    append:(parent,node)=>parent.appendChild(node),element:(tag,className)=>new Node(className,/ss-page-divider/.test(className)?20:/ss-page-spinner/.test(className)?30:0),
    invoke:(action,args)=>{commands.push({action,...args});return true;},setStatus(){},renderSelects(){},renderFilterActivity(){},t:key=>key,number:String,date:String,
    invalidateCardFlow(){},clear:node=>node.children.slice().forEach(child=>node.removeChild(child)),stageFeedContext(){},
    ordered:items=>items,layoutBattleCards(){},queueResize(){resizes++;},pinnedFilterHeight:()=>50,
    scrollbarMetrics:()=>({maximum:Math.max(0,scroll.scrollHeight-scroll.clientHeight)}),battleLayoutOffset:()=>null,
    startBattleJump(target,revealOnly){state.battleJump={target,revealOnly};},
    cancelBattleNavigation(){state.battleJump=null;},clearBattleTarget(){dismissed++;},
    resetViewScroll(){state.scrollTarget=0;scroll.scrollTop=0;},updatePinnedFilters(){},
    createCardPage(index,items,feed){const section=context.pageBoundary(feed,index,false);section.height=1000;groups.appendChild(section);
      return {index,section,columns:new Node(),items,cards:[],lanes:[new Node(),new Node()]};},
    appendGroupBatch(count,page){page.cards=page.items.slice(0,count).map(item=>{
      const card=new Node('ss-group',20);card.setAttribute('data-group-id',item.id);return page.section.appendChild(card);
    });state.groupCards=state.groupCards.concat(page.cards);},
    render(){context.renderGroups(scope);}};
  vm.createContext(context);
  for(const name of ['feedCollectionIdentity','feedIdentity','feedContextIdentity','battleOwnsViewport','retainBattleTargetAfterResize','cancelUITimer','cancelPageJump','beginPageJump','retireFeed','captureFeedAnchor','finishFeedAnchor',
    'revealFeedTop','pageBoundary','showFeedPending','includeFeedPage','requestFeedPage','captureRefreshAnchor','visibleRefreshPage','retargetFeedRefresh','deferFeedRefresh',
    'battleScrollPending','finishRefreshAnchor','prepareFeed','updateFeedControls','retireHistoryCards','renderGroups',
    'suspendResizePrefetch','loadNearEdges','onScrollIntent','changePage'])
    vm.runInContext(sourceFunction(source,name),context);
  const topStart=source.indexOf("    if (nodes['scroll-top']) { nodes['scroll-top'].onclick = function () {",source.indexOf('    function changePage('));
  const topEnd=source.indexOf("    document.getElementById('ss-scope-launch')",topStart);assert(topStart>=0&&topEnd>topStart);
  vm.runInContext(source.slice(topStart,topEnd),context);
  const flush=()=>{for(let count=0;scheduled.length&&count<100;count++)scheduled.shift()();assert(scheduled.length===0);};
  const reply=(index,request)=>{scope.battles=rows(index);scope.pagination={battles:{page:index,pages:6,page_size:40,total:205}};
    if(request)scope.pagination.battles.request_id=request.id;context.renderGroups(scope);flush();};
  const start=()=>{context.retireFeed();groups.children.slice().forEach(child=>groups.removeChild(child));state.renderedFeed=null;state.groupCards=[];state.cardPages=[];
    state.scrollTarget=null;scroll.scrollTop=400;scope.data_revision++;reply(3);scroll.scrollTop=200;state.scrollTarget=null;};
  start();const confirmedFeed=state.feed,confirmedCards=state.groupCards.slice(),beforeSortRender=commands.length;
  state.orderIntent={group:state.group,context:context.viewContext(),options:{...scope.ordering.battles,direction:'asc'},timer:1};
  context.renderGroups(scope);flush();
  assert.strictEqual(state.feed,confirmedFeed,'A redraw before the native sort acknowledgement keeps the confirmed feed');
  assert.deepStrictEqual(state.groupCards,confirmedCards);
  assert.strictEqual(commands.length,beforeSortRender,'A redraw while sorting does not start a page request under the optimistic order');
  state.orderIntent=null;
  start();context.loadNearEdges();const waiting=state.feed.pending,beforeFrame=commands.length;
  assert(timers.has(waiting.timer),'The page spinner has a watchdog before the native frame callback runs');
  const watchdog=timers.get(waiting.timer);timers.delete(waiting.timer);watchdog();
  assert.strictEqual(state.feed.pending,null);assert.strictEqual(state.feed.error,2,'A missing frame ends loading and exposes Retry');
  flush();assert.strictEqual(commands.length,beforeFrame,'A late frame does not send the expired native page request');

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
  context.onScrollIntent({type:'wheel',deltaY:1,target:scroll});state.scrollTarget=null;scroll.scrollTop=370;
  const cancelledPosition=state.cardPages[0].section.getBoundingClientRect().top;reply(0,cancelled);
  assert.strictEqual(state.feed.start,3);assert.strictEqual(state.feed.last,3);
  assert.strictEqual(state.cardPages[0].section.getBoundingClientRect().top,cancelledPosition,'Newer scroll intent cancels a pending Top destination');
  assert(state.feed.cache[0],'The cancelled destination can still populate its owned cache');
  // Reusing page zero needs no second backend request.
  const before=commands.length;nodes['scroll-top'].onclick();flush();assert.strictEqual(commands.length,before);assert.strictEqual(state.cardPages[0].index,0);
  assert.strictEqual(scroll.scrollTop,0);assert(dismissed>=3);assert(resizes>0);
  start();scope.data_revision++;reply(5);
  const ordinary=state.feed.pending;
  context.onScrollIntent({type:'wheel',deltaY:1,target:scroll});
  assert(state.feed.refreshInput,'A scroll waits for the painted viewport during an ordinary revision');
  nodes['scroll-top'].onclick();flush();
  const explicitTop=state.feed.pending;
  assert(!state.feed.refreshInput&&explicitTop.page===0,'A newer explicit Top skips the retired scroll settlement');
  reply(3,ordinary);reply(0,explicitTop);
  assert.deepStrictEqual(Array.from(state.cardPages,page=>page.index),[0]);
  assert.strictEqual(scroll.scrollTop,0,'The old refresh cannot retarget an explicit Top');
  start();context.changePage(1);flush();scope.data_revision++;reply(5);
  assert.strictEqual(groups.getAttribute('aria-busy'),'true');
  const stalledDestination=state.feed.pending;
  timers.get(stalledDestination.timer)();
  assert.strictEqual(groups.getAttribute('aria-busy'),'false','The watchdog ends a stalled destination spinner');
  assert.deepStrictEqual(Array.from(state.cardPages,page=>page.index),[3]);
  groups.querySelector('.ss-page-status').children[0].onclick();flush();
  assert.strictEqual(groups.getAttribute('aria-busy'),'true','Retry starts a fresh owned request');
  for(const destination of [4,0]){
    start();
    if(destination===4)context.changePage(1);else nodes['scroll-top'].onclick();
    flush();
    assert.strictEqual(state.feed.pending.page,destination);
    scope.data_revision++;reply(5);
    const stagedDestination=state.feed.pending;
    assert.strictEqual(stagedDestination.page,destination);
    assert.deepStrictEqual(Array.from(state.cardPages,page=>page.index),[3]);
    context.onScrollIntent({type:'wheel',deltaY:1,target:scroll});scroll.scrollTop=320;
    const anchor=state.cardPages[0].cards[11],offset=anchor.getBoundingClientRect().top;
    reply(destination,stagedDestination);
    assert(groups.contains(anchor),'A cancelled staged destination cannot replace the page the user scrolled');
    assert.strictEqual(state.feed.pending.page,3,'Cancellation refreshes the mounted page under the new revision');
    reply(3,state.feed.pending);
    for(let measurement=0;measurement<3;measurement++)context.finishRefreshAnchor();
    assert.deepStrictEqual(Array.from(state.cardPages,page=>page.index),[3]);
    assert.strictEqual(state.cardPages[0].cards[11].getBoundingClientRect().top,offset,'The refresh uses the later wheel position');
    assert.strictEqual(state.pageJump,null);
  }
  nodes['scroll-top'].onclick();flush();
  if(state.feed.pending)reply(0,state.feed.pending);
  for(let index=1;index<6;index++){context.includeFeedPage(state.feed,index,true);reply(index);}
  assert.deepStrictEqual(Array.from(state.cardPages,page=>page.index),[3,4,5],'A long feed mounts only its last three neighbouring pages');
  assert.strictEqual(state.groupCards.length,85);
  assert(Object.keys(state.feed.cache).length<=5,'Rows and signatures from distant pages leave the cache');
  state.feed.current=3;scroll.scrollTop=350;
  const visibleCard=state.cardPages[0].cards.find(card=>{
    const box=card.getBoundingClientRect();return box.bottom>50&&box.top<500;
  });
  const visibleID=visibleCard.getAttribute('data-group-id'),visibleTop=visibleCard.getBoundingClientRect().top;
  const beforeRevision=commands.length;
  scope.data_revision++;reply(5);
  const refresh=state.feed.pending;
  assert.strictEqual(refresh.page,3,'Refresh requests the visible page instead of replaying visited pages');
  assert.strictEqual(state.feed.start,3);assert.strictEqual(state.feed.last,3);
  assert(groups.contains(visibleCard),'The old view stays mounted until the visible page is ready');
  scope.data_revision++;reply(5);
  assert.strictEqual(state.feed.pending,refresh,'A newer result cannot restart the same visible-page request');
  reply(3,refresh);
  const updatedCard=state.cardPages[0].cards.find(card=>card.getAttribute('data-group-id')===visibleID);
  for(let measurement=0;measurement<3;measurement++)context.finishRefreshAnchor();
  assert.strictEqual(state.cardPages.length,1);
  assert.strictEqual(updatedCard.getBoundingClientRect().top,visibleTop,'Replacing a long feed preserves the visible card offset');
  assert.strictEqual(commands.length,beforeRevision+1,'Only one page is requested across multiple rapid revisions');
  context.loadNearEdges();flush();
  assert.strictEqual(commands.length,beforeRevision+1,'Anchor correction cannot cause an unsolicited edge fetch');

  // The displayed status may still say page four when a new gesture has
  // already painted page five. Let page four reply before that paint occurs.
  for(const intent of [{type:'wheel',deltaY:1},{type:'keydown',key:'PageDown'},{type:'scrollbar'}]){
    start();state.feed.last=4;reply(4);
    state.feed.current=3;scroll.scrollTop=600;
    scope.data_revision++;reply(5);
    const outdated=state.feed.pending,requestedBefore=commands.length;
    assert.strictEqual(outdated.page,3);
    const oldCards=state.cardPages.slice();
    const target=intent.type==='keydown'?{tagName:'BUTTON',parentNode:scroll}:scroll;
    if(intent.type==='keydown'){
      context.onScrollIntent({type:'keydown',key:' ',target});
      assert(!state.feed.refreshInput,'Space activates a focused result button instead of starting scroll ownership');
    }
    context.onScrollIntent({...intent,target});
    scope.battles=rows(3);scope.pagination.battles={page:3,pages:6,page_size:40,total:205,request_id:outdated.id};
    context.renderGroups(scope);
    assert.deepStrictEqual(state.cardPages,oldCards,'Page four cannot claim the viewport before the scroll paints');
    scheduled.shift()();scheduled.shift()();
    scroll.scrollTop=1330;
    const expectedPage=oldCards[1],expectedCard=expectedPage.cards.find(card=>card.getBoundingClientRect().bottom>50);
    const expectedTop=expectedCard.getBoundingClientRect().top;
    flush();
    assert.strictEqual(state.feed.pending.page,4,'The current page follows the painted viewport for '+intent.type);
    assert.strictEqual(commands.length,requestedBefore+1,'One follow-up request is sufficient for '+intent.type);
    const current=state.feed.pending;
    reply(3,outdated);
    assert.strictEqual(state.feed.pending,current,'A retired page-four response cannot supersede page five');
    reply(4,current);
    for(let measurement=0;measurement<3;measurement++)context.finishRefreshAnchor();
    assert.deepStrictEqual(Array.from(state.cardPages,page=>page.index),[4]);
    const replacement=state.cardPages[0].cards.find(card=>card.getAttribute('data-group-id')===expectedCard.getAttribute('data-group-id'));
    assert.strictEqual(replacement.getBoundingClientRect().top,expectedTop,'The visible result stays put after retargeting');
  }

  // At capacity a new edge can be mounted without changing the visible
  // coordinates, even after its opposite page and DOM handlers are removed.
  nodes['scroll-top'].onclick();flush();
  if(state.feed.pending)reply(0,state.feed.pending);
  for(let index=1;index<=2;index++){context.includeFeedPage(state.feed,index,true);reply(index);}
  state.feed.prependAnchor=null;state.scrollTarget=null;scroll.scrollTop=2450;
  const leaving=state.cardPages[0],forwardAnchor=state.cardPages[2];
  const forwardTop=forwardAnchor.section.getBoundingClientRect().top;
  let disposed=0;leaving.cards[0]._ssHistoryDispose=()=>{disposed++;};
  context.requestFeedPage(state.feed,3,false);flush();reply(3,state.feed.pending);
  assert.deepStrictEqual(Array.from(state.cardPages,page=>page.index),[1,2,3]);
  assert.strictEqual(forwardAnchor.section.getBoundingClientRect().top,forwardTop,'Removing the first page adjusts scroll by its height');
  assert.strictEqual(disposed,1,'Leaving pages retire their history handlers');
  state.feed.prependAnchor=null;state.scrollTarget=null;scroll.scrollTop=250;
  const backwardAnchor=state.cardPages[0],backwardTop=backwardAnchor.section.getBoundingClientRect().top;
  context.requestFeedPage(state.feed,0,false);flush();
  if(state.feed.pending)reply(0,state.feed.pending);
  assert.deepStrictEqual(Array.from(state.cardPages,page=>page.index),[0,1,2]);
  assert.strictEqual(backwardAnchor.section.getBoundingClientRect().top,backwardTop,'Removing the last page keeps the old viewport during a prepend');
  // Restore the focused page used by the following delayed layout test.
  start();context.includeFeedPage(state.feed,4,true);reply(4);
  state.feed.current=4;scroll.scrollTop=1300;

  state.highlightedBattle={id:state.groupCards[0].getAttribute('data-group-id'),context:context.viewContext(),request_id:'selection-before-wheel',followViewport:true};
  context.onScrollIntent({type:'wheel',deltaY:1,target:scroll});
  context.retainBattleTargetAfterResize();
  const requestsBeforeLate=commands.length;
  scope.data_revision++;scope.battles=rows(4).map(row=>({...row,live:42}));
  scope.pagination.battles={page:4,pages:6,page_size:40,total:206,request_id:refresh.id};
  context.renderGroups(scope);flush();
  assert.strictEqual(state.feed.total,206);
  assert.strictEqual(state.feed.cache[4][0].live,42,'After wheel and resize, fresh stats with the last acknowledged page token still update the list');
  assert.strictEqual(commands.length,requestsBeforeLate,'A fresh acknowledgement never requests a stale page');
  let pinnedWrites=0;context.updatePinnedFilters=()=>{pinnedWrites++;};state.destroyed=true;
  context.loadNearEdges();flush();assert.strictEqual(commands.length,requestsBeforeLate);assert.strictEqual(pinnedWrites,0,'A retained scroll listener cannot fetch or repaint after teardown');
  assert(source.includes("nodes.scroll.removeEventListener('scroll', queueScrollEdges);"),'Cleanup removes its exact deferred edge-loading listener');
}

const frames=page=>page.evaluate(()=>new Promise(resolve=>{let left=10;function next(){if(--left)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);}));

async function checkBattleMovingToTheNextPage(browser,nativeHost,check) {
  const viewport={width:645,height:750,scale:1};
  const page=await nativeHost(browser,{viewport,initialViewport:viewport});
  try {
    await page.evaluate(()=>{
      const payload=JSON.parse(model.payload),scope=payload.scopes.launch,sample=scope.battles[0];
      payload.window_size=[625,730];
      payload.appearance={...payload.appearance,window_settings:{maximized:false,restored_width:625,restored_height:730}};
      scope.data_revision='moving-battle:1';
      scope.battles=Array.from({length:40},(_,index)=>({...sample,id:'moving-battle-'+index,details:null}));
      const anchor=scope.battles[39];
      anchor.details={missions:Array.from({length:40},(_,index)=>({id:'mission-'+index,kind:'daily',status:'completed',
        name:'Practice mission '+index,description:'Complete the objective to collect the reward.'}))};
      window.__movingBattle=anchor;
      scope.pagination.battles={page:0,pages:2,page_size:40,total:79};
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      document.getElementById('ss-group-battles').click();
      document.querySelector('[data-group-id="moving-battle-39"] .ss-more-button').click();
    });
    await frames(page);
    const battle=page.locator('#ss-groups [data-group-id="moving-battle-39"]');
    await battle.evaluate(node=>{
      const scroll=document.getElementById('ss-scroll'),filter=document.getElementById('ss-filter-panel');
      scroll.scrollTop+=node.getBoundingClientRect().top-scroll.getBoundingClientRect().top-filter.getBoundingClientRect().height+80;
    });
    await frames(page);
    const offset=()=>battle.evaluate(node=>node.getBoundingClientRect().top-document.getElementById('ss-scroll').getBoundingClientRect().top);
    const before=await offset();
    await page.evaluate(()=>{
      const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
      scope.battles.unshift({...scope.battles[0],id:'latest-battle'});scope.battles.pop();
      scope.data_revision='moving-battle:2';scope.pagination.battles.total=80;
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
    });
    await frames(page);
    const request=await page.evaluate(()=>__grzCommands.find(command=>command.anchor_id==='moving-battle-39'));
    check('A live result holds the viewed battle on screen while requesting its new page by ID',
      request&&request.page==='0'&&await battle.count()===1);

    await page.evaluate(request=>{
      const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
      scope.battles=[__movingBattle,...scope.battles.slice(1,40).map(row=>({...row,id:'older-'+row.id}))];
      Object.assign(scope.pagination.battles,{page:1,request_id:request.request_id});
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
    },request);
    await frames(page);
    check('The battle stays expanded at its previous offset after its page changes',
      await battle.evaluate(node=>node.closest('[data-page-index]').getAttribute('data-page-index')==='1')&&
      await battle.locator('.ss-more-button').getAttribute('aria-expanded')==='true'&&Math.abs(await offset()-before)<=2);
  } finally { await page.close(); }
}

module.exports=async({browser,nativeHost,check})=>{
  assertBidirectionalSource();check('Actual-source midfeed paging, anchor, Retry and Top-race regressions pass',true);
  await checkBattleMovingToTheNextPage(browser,nativeHost,check);
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:2400,height:1800},viewport:{width:2400,height:1800,scale}});
    const label=' at '+(scale*100)+'%',requests=()=>page.evaluate(()=>__grzCommands.filter(item=>item.action==='page'));
    const emit=async(index,request,{revision,wheel=false}={})=>{await page.evaluate(({index,request,revision,wheel})=>{
      const payload=JSON.parse(model.payload),scope=payload.scopes.launch;scope.battles=Array.from({length:index===5?5:40},(_,offset)=>({
        ...__midfeedSample,id:'synthetic-midfeed-'+(index*40+offset),name:'Synthetic battle '+(index*40+offset),started_at:1900000000-index*40-offset}));
      if(revision)scope.data_revision=revision;
      scope.pagination.battles={page:index,pages:6,page_size:40,total:205};if(request)scope.pagination.battles.request_id=request.request_id;
      if(wheel)document.getElementById('ss-scroll').dispatchEvent(new WheelEvent('wheel',{deltaY:-1,bubbles:true,cancelable:true}));
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
    },{index,request,revision,wheel});await frames(page);};
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

      await page.evaluate(()=>document.getElementById('ss-page-next').onclick());await frames(page);
      sent=await requests();await emit(1,sent[sent.length-1]);
      const newPage='.ss-continuous-page[data-page-index="1"]:not(.ss-page-pending)';
      await page.locator(newPage).evaluate(section=>{
        const scroll=document.getElementById('ss-scroll'),edge=scroll.getBoundingClientRect().top+document.getElementById('ss-filter-panel').getBoundingClientRect().height;
        scroll.dispatchEvent(new WheelEvent('wheel',{deltaY:-1,bubbles:true,cancelable:true}));
        scroll.scrollTop+=section.getBoundingClientRect().top-edge-scroll.clientHeight/8;
        window.__midfeedPageBeforeRefresh=section;
      });await frames(page);
      await emit(2,null,{revision:'midfeed:2'});
      sent=await requests();const originalRefresh=sent[sent.length-1];
      check('An ordinary revision stages the page above the next divider'+label,originalRefresh.page==='0');
      await emit(0,originalRefresh,{wheel:true});
      await page.waitForFunction(count=>__grzCommands.filter(command=>command.action==='page').length>count,sent.length);
      const retargeted=(await requests()).slice(sent.length);
      const oldVisible=await page.locator(newPage).evaluate(section=>{
        const scroll=document.getElementById('ss-scroll').getBoundingClientRect(),edge=scroll.top+document.getElementById('ss-filter-panel').getBoundingClientRect().height;
        const card=[...section.querySelectorAll('.ss-group')].find(node=>node.getBoundingClientRect().bottom>edge&&node.getBoundingClientRect().top<scroll.bottom);
        return {old:section===__midfeedPageBeforeRefresh,id:card&&card.dataset.groupId,offset:card&&card.getBoundingClientRect().top-scroll.top};
      });
      check('A wheel movement across the divider retargets a delayed refresh once'+label,retargeted.length===1&&retargeted[0].page==='1'&&oldVisible.old&&!!oldVisible.id);
      await emit(1,retargeted[0]);
      const card=page.locator(newPage+' [data-group-id="'+oldVisible.id+'"]');
      const refreshedOffset=await card.evaluate(node=>node.getBoundingClientRect().top-document.getElementById('ss-scroll').getBoundingClientRect().top);
      check('The revised cards replace the painted page and keep its visible card in position'+label,
        await page.locator('.ss-continuous-page:not(.ss-page-pending)').count()===1&&Math.abs(oldVisible.offset-refreshedOffset)<=2*scale);
      const completedCount=(await requests()).length;
      await emit(0,originalRefresh,{revision:'midfeed:1'});
      check('An older response after retarget completion does not restart or move the refreshed feed'+label,
        (await requests()).length===completedCount&&await card.count()===1&&
        Math.abs(refreshedOffset-await card.evaluate(node=>node.getBoundingClientRect().top-document.getElementById('ss-scroll').getBoundingClientRect().top))<=2*scale);

      if(scale===1){
        await page.evaluate(()=>{
          const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
          payload.account_key='synthetic-feed-window';scope.period_id='synthetic-feed-window-period';
          scope.data_revision='window:1';scope.pagination.battles={page:0,pages:6,page_size:40,total:205};
          delete scope.battle_focus;window.__grzCommands=[];
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
        });
        await emit(0);
        async function step(id,index){
          const before=(await requests()).length;
          await page.evaluate(id=>document.getElementById(id).onclick(),id);await frames(page);
          const requested=(await requests()).slice(before).filter(command=>command.page===String(index)).at(-1);
          if(requested) await emit(index,requested);
        }
        for(let index=1;index<=4;index++) await step('ss-page-next',index);
        const mounted=()=>page.locator('.ss-continuous-page:not(.ss-page-pending)').evaluateAll(pages=>pages.map(node=>Number(node.dataset.pageIndex)));
        check('Visiting five battle pages keeps three mounts and absolute accessible positions',
          JSON.stringify(await mounted())==='[2,3,4]' &&
          await page.locator('.ss-continuous-page[data-page-index="4"] [data-list-index="160"]').getAttribute('aria-posinset')==='161');
        const beforeEdge=(await requests()).length;
        await page.evaluate(()=>{
          const scroll=document.getElementById('ss-scroll');
          scroll.dispatchEvent(new WheelEvent('wheel',{deltaY:-1,bubbles:true,cancelable:true}));
          scroll.scrollTop=scroll.scrollHeight;
          scroll.dispatchEvent(new Event('scroll'));
        });await frames(page);
        const edge=(await requests()).slice(beforeEdge).find(command=>command.page==='5');
        check('The tail of the bounded feed automatically requests its next page',!!edge);
        const retained=page.locator('.ss-continuous-page[data-page-index="4"]'),offset=()=>retained.evaluate(node=>
          node.getBoundingClientRect().top-document.getElementById('ss-scroll').getBoundingClientRect().top);
        const beforeOffset=await offset();await emit(5,edge);
        check('Appending at capacity retains the same battle viewport and evicts the opposite boundary',
          Math.abs(await offset()-beforeOffset)<=2 && JSON.stringify(await mounted())==='[3,4,5]' &&
          await page.locator('#ss-groups .ss-group').count()===85);
        await step('ss-page-next',5);
        for(let index=4;index>0;index--) await step('ss-page-previous',index);
        check('Previous can revisit evicted pages without mounting the complete history',
          JSON.stringify(await mounted())==='[1,2,3]' &&
          await page.locator('.ss-continuous-page[data-page-index="1"] .ss-group').count()===40);
      }
    }finally{await page.close();}
  }
};
module.exports.assertBidirectionalSource=assertBidirectionalSource;
if(require.main===module){assertBidirectionalSource();console.log('Actual-source bidirectional paging, stable prepend, Retry and Top ownership regressions passed.');}
