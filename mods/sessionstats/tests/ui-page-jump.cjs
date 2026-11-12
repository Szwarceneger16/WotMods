/* Explicit page controls retain their divider through delayed native layout. */
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
const shipped=()=>fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8');
function actualFunction(source,name){
  const start=source.indexOf('    function '+name+'('),end=source.indexOf('\n    }\n',start);
  assert(start>=0&&end>start,'Exercise actual shipped '+name);return source.slice(start,end+7);
}
function geometry(source=shipped()){
  let clock=1000,offset=0,physical=0,position=1500,missing=false,busy=false,validContext=true;
  let lag=false,pendingOffset=null,nextTimer=1,pinnedUpdates=0,resizes=0;
  const timers=new Map(),owner={account_key:'synthetic-page-jump',scope:'launch',period_id:'synthetic-period'};
  const feed={context:owner,key:'synthetic-page-order',collectionKey:'synthetic-page-order',group:'maps',
    start:0,last:2,current:0,pages:5,navigationPage:2,topRequested:false,prependAnchor:null,pending:null};
  const scroll={get scrollTop(){return offset;},set scrollTop(value){const next=Math.max(0,Math.min(4000,value));
      if(lag==='drop'){lag=false;return;}
      if(lag){pendingOffset=next;if(lag==='getter')physical=next;if(lag==='rect')offset=next;}
      else{offset=next;physical=next;}},clientHeight:500,scrollHeight:4500,
    getBoundingClientRect:()=>({top:100,bottom:600,width:700,height:500})};
  const section={get offsetTop(){return position;},offsetParent:scroll,
    getBoundingClientRect:()=>missing?{top:0,width:0,height:0}:
      ({top:100+position-physical,bottom:250+position-physical,width:700,height:150})};
  const groups={offsetTop:300,offsetParent:scroll,getAttribute:()=>busy?'true':'false',
    contains:node=>node===section,getBoundingClientRect:()=>({top:400-physical,bottom:4600-physical,width:700,height:4200})};
  const state={destroyed:false,bound:true,group:'maps',nativeScale:1,feed,renderedFeed:feed,
    cardPages:[],groupCards:[],cardFlowQueued:false,groupMinHeight:false,feedStaging:false,
    scrollTarget:null,pageJump:null,pageJumpTimer:null,battleJump:null};
  const context={state,nodes:{scroll,groups,'scroll-top':{}},Date:{now:()=>clock},Math,
    hasNumber:value=>typeof value==='number'&&Number.isFinite(value),sameContext:()=>validContext,
    cancelUITimer:id=>timers.delete(id),window:{setTimeout(callback,delay){const id=nextTimer++;timers.set(id,{callback,delay});return id;}},
    document:{documentElement:{contains:()=>true}},pinnedFilterHeight:()=>60,
    scrollbarMetrics:()=>({maximum:4000}),queueResize(){resizes++;},
    updatePinnedFilters(){pinnedUpdates++;},updateFeedControls(){},syncScrollbar(){},
    cancelBattleNavigation(){state.battleJump=null;},clearBattleTarget(){},
    resetViewScroll(){state.scrollTarget=0;scroll.scrollTop=0;}};
  vm.createContext(context);
  const names=['beginPageJump','cancelPageJump','retryPageJump','finishPageJump','battleLayoutOffset','battleScrollPending','onScrollIntent','retireFeed'];
  if(source.includes('    function pageScrollPending('))names.push('pageScrollPending');
  vm.runInContext(names.map(name=>actualFunction(source,name)).join('\n'),context);
  function tick(delta=100){clock+=delta;const next=[...timers].find(([,timer])=>timer.delay>0&&timer.delay<=100);
    if(next){timers.delete(next[0]);next[1].callback();}}
  return{context,state,scroll,section,timers,feed,begin(){context.beginPageJump(feed,2);context.finishPageJump();},
    tick,settle(){for(let index=0;index<12&&state.pageJump;index++)tick(100);},
    show(){state.cardPages=[{index:2,section}];},missing(value){missing=value;},busy(value){busy=value;},
    move(value){position=value;},setContext(value){validContext=value;},lag(value){lag=value;},
    flush(){lag=false;if(pendingOffset!==null){offset=pendingOffset;physical=pendingOffset;pendingOffset=null;}},
    pinnedUpdates:()=>pinnedUpdates,resizes:()=>resizes};
}
function retainedTimer(view){const timer=[...view.timers.values()].find(value=>value.delay===100);
  assert(timer,'The unsettled page schedules an owned geometry retry');return timer.callback;}
function assertFreshPageDeadline(source){
  const renewed=geometry(source),context=renewed.context,state=renewed.state,old=renewed.feed;
  state.nativeSession=true;state.feedForceStart=null;
  old.revision='1';old.cache={};old.signatures={};old.navigationPage=2;old.navigationDeadline=999;
  const scope={data_revision:2,summary:{battles:200},maps:[{id:'revision-page-two'}],
    pagination:{maps:{page:2,pages:5,total:200,page_size:40}}};
  Object.assign(context,{feedIdentity:()=>old.key,feedCollectionIdentity:()=>old.collectionKey,
    feedContextIdentity:()=>JSON.stringify(old.context),viewContext:()=>old.context,
    requestFeedPage(feed,page,navigate){feed.pending={page,id:'fill-'+page,navigate,timer:null};},
    captureFeedAnchor(){throw Error('Explicit page reply must not become an automatic prepend anchor');},
    revealFeedTop(){throw Error('A page reply must not request Back to top');}});
  vm.runInContext(actualFunction(source,'prepareFeed'),context);
  const staged=context.prepareFeed(scope);
  assert.notStrictEqual(staged,old,'A changed result revision rebuilds its feed');
  assert.strictEqual(staged.navigationPage,2,'The revision rebuild stages the existing page destination while prefix pages reload');
  assert.strictEqual(staged.navigationDeadline,999,'The staged revision retains its original navigation deadline');
  context.onScrollIntent({type:'wheel',target:renewed.scroll});
  assert.strictEqual(staged.navigationPage,null,'New user movement retires the staged revision destination');
  // Complete the ordinary prefix cache, then accept a later, separately owned
  // Next request. Its lifetime starts now instead of inheriting the old 999.
  staged.cache[0]=[];staged.cache[1]=[];staged.signatures[0]='[]';staged.signatures[1]='[]';
  staged.pending={page:3,id:'fresh-page-request',navigate:true,timer:null};
  scope.maps=[{id:'fresh-page-three'}];scope.pagination.maps={page:3,pages:5,total:200,page_size:40,request_id:'fresh-page-request'};
  const accepted=context.prepareFeed(scope);
  assert.strictEqual(accepted,staged,'The separately owned reply fills the current revision cache');
  assert(state.pageJump&&state.pageJump.page===3,'The fresh async reply owns its requested page');
  assert.strictEqual(state.pageJump.deadline,11000,'A new async page reply receives a full lifetime after cancellation, not expired deadline 999');
  state.renderedFeed=accepted;state.cardPages=[{index:3,section:renewed.section}];
  context.finishPageJump();assert(renewed.scroll.scrollTop>1000,'The fresh async destination aligns instead of expiring immediately');
  renewed.settle();assert.strictEqual(state.pageJump,null,'The fresh async destination settles normally');
}
function assertPageJumpSource(source=shipped()){
  assertFreshPageDeadline(source);
  for(const mode of ['cached','accepted-reply']){
    const late=geometry(source);if(mode==='cached'){late.show();late.missing(true);}else late.busy(true);
    late.begin();late.tick(3000);
    assert(late.state.pageJump,'A '+mode+' page still owns its divider after several seconds of native layout');
    assert.strictEqual(late.scroll.scrollTop,0,'Missing or staged '+mode+' geometry does not move the viewport');
    late.show();late.missing(false);late.busy(false);late.tick();
    const first=late.scroll.scrollTop;
    assert(first>1000,'The mounted '+mode+' page is reached below the pinned filters');
    assert(late.state.pageJump,'The first non-zero page paint does not consume navigation');
    late.move(1900);late.tick();
    assert(late.scroll.scrollTop>first+300,'A later lane/font layout shift corrects the divider position');
    const aligned=late.section.getBoundingClientRect().top;
    assert(aligned>=159&&aligned<=181,'The divider sits immediately below the 60px pinned filter bar');
    late.settle();assert.strictEqual(late.state.pageJump,null,'Stable '+mode+' geometry retires its correction');
    assert.strictEqual(late.timers.size,0,'No page retry survives stable '+mode+' alignment');
  }

  for(const phase of ['getter','rect']){
    const async=geometry(source);async.show();async.lag(phase);async.begin();
    const requested=async.state.pageJump.requestedOffset;
    assert(requested>1000,'The '+phase+'-late page setter has an owned destination');
    for(let index=0;index<3;index++)async.tick();
    assert.strictEqual(async.state.pageJump.requestedOffset,requested,'Mixed '+phase+' samples cannot change the requested divider offset');
    assert.strictEqual(async.pinnedUpdates(),0,'Mixed '+phase+' samples do not enter ordinary pinned-filter clamping');
    const pinned=vm.runInContext('('+actualFunction(source,'updatePinnedFilters')+')',async.context);
    async.context.nodes['filter-panel']={getBoundingClientRect(){throw Error('Mixed '+phase+' page samples reached normal-flow clamping');}};
    pinned();async.flush();async.tick();
    assert.strictEqual(async.scroll.scrollTop,requested,'The acknowledged '+phase+' setter retains its original destination');
    assert(async.pinnedUpdates()>0,'Pinned filters refresh after '+phase+' acknowledgement');
    async.settle();assert.strictEqual(async.state.pageJump,null,'Acknowledged '+phase+' geometry settles');
  }

  const dropped=geometry(source);dropped.show();dropped.lag('drop');dropped.begin();
  const requested=dropped.state.pageJump.requestedOffset;
  assert(requested>1000&&dropped.scroll.scrollTop===0,'An early native range can drop the first page scroll setter');
  dropped.tick();
  assert.strictEqual(dropped.state.pageJump.requestedOffset,requested,'A dropped setter retries the same owned divider offset');
  assert.strictEqual(dropped.scroll.scrollTop,requested,'The page retry reissues the dropped setter without manual native acknowledgement');
  dropped.settle();assert.strictEqual(dropped.state.pageJump,null,'The reissued page setter settles without a manual flush');

  const final=geometry(source);final.show();final.move(4200);final.begin();final.settle();
  assert.strictEqual(final.scroll.scrollTop,4000,'A short final page clamps to the actual scroll range');
  assert.strictEqual(final.state.pageJump,null,'An unalignable final divider still settles at the scroll end');

  for(const kind of ['wheel','mousedown','keydown']){
    const moved=geometry(source);moved.begin();const retained=retainedTimer(moved);
    moved.feed.navigationPage=2;moved.feed.navigationDeadline=999;
    moved.context.onScrollIntent({type:kind,key:'ArrowDown',target:moved.scroll});
    moved.state.scrollTarget=null;moved.scroll.scrollTop=350;moved.show();retained();
    assert.strictEqual(moved.state.pageJump,null,'Newer '+kind+' retires an outstanding page destination');
    assert.strictEqual(moved.feed.navigationPage,null,'Newer '+kind+' clears a staged revision destination');
    assert.strictEqual(moved.feed.navigationDeadline,null,'Newer '+kind+' cannot leave an expired deadline for the next asynchronous destination');
    assert.strictEqual(moved.scroll.scrollTop,350,'A retained page callback cannot undo newer '+kind);
  }
  for(const reason of ['feed','context','deadline','attempts','cleanup']){
    const retired=geometry(source);retired.begin();const retained=retainedTimer(retired);
    if(reason==='feed')retired.state.feed={context:retired.feed.context};
    else if(reason==='context')retired.setContext(false);
    else if(reason==='deadline')retired.tick(10000);
    else if(reason==='attempts')for(let index=0;index<105&&retired.state.pageJump;index++)retired.tick(0);
    else retired.context.retireFeed();
    retired.context.finishPageJump();retired.show();retained();
    assert.strictEqual(retired.state.pageJump,null,reason+' retires explicit page navigation');
    assert.strictEqual(retired.scroll.scrollTop,0,'A retained callback cannot revive navigation after '+reason);
    assert.strictEqual(retired.timers.size,0,'No page retry survives '+reason);
  }

  const top=geometry(source);top.begin();const retained=retainedTimer(top);
  const start=source.indexOf("    if (nodes['scroll-top']) { nodes['scroll-top'].onclick = function () {");
  const end=source.indexOf('\n    function switchXP(',start);assert(start>=0&&end>start,'Exercise the shipped Back to top handler');
  vm.runInContext(source.slice(start,end),top.context);top.context.nodes['scroll-top'].onclick();
  top.show();retained();assert.strictEqual(top.state.pageJump,null,'Back to top supersedes the pending page divider');
  assert.strictEqual(top.scroll.scrollTop,0,'A retained page callback cannot undo Back to top');
}
module.exports={assertPageJumpSource};
if(require.main===module){assertPageJumpSource();console.log('Actual-source page divider navigation, delayed geometry, native acknowledgement and cancellation passed.');}
