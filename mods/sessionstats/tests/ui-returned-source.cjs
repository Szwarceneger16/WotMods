/* The five-second source marker owns no scroll, focus or permanent polling. */
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
function extract(source,name){const start=source.indexOf('    function '+name+'('),line=source.indexOf('\n',start),end=source.slice(start,line).endsWith('}')?line:source.indexOf('\n    }\n',start)+7;assert(start>=0&&end>start,name);return source.slice(start,end);}
module.exports=function(){
  const source=fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8').replace(/\r\n/g,'\n');
  let now=1000,sequence=0,lookup=0,scope={data_revision:'one',summary:{}},order={metric:'off',statistic:'avg',direction:'desc',chronology:'newest'};
  let current={account_key:'synthetic-return',scope:'timeline',period_id:'synthetic-range'},replacement=null;
  const timers=new Map(),state={group:'vehicles',returnedSource:null,returnedSourceTimer:null,destroyed:false},groups={contains:node=>node.mounted},summary={contains:()=>false};
  const action=()=>{const classes=new Set(),card={id:'synthetic-vehicle',hasAttribute:key=>key==='data-group-id',getAttribute(key){return key==='data-group-id'?this.id:null;},parentNode:groups},node={tagName:'BUTTON',mounted:true,parentNode:card,hasAttribute:()=>false,getAttribute:key=>key==='data-battle-id'?'synthetic-battle':null,adds:0,
    classList:{add(name){node.adds++;classes.add(name);},remove:name=>classes.delete(name),contains:name=>classes.has(name)},
    getBoundingClientRect(){throw Error('A source marker must not remeasure geometry');},focus(){throw Error('A source marker must not move focus');}};return node;};
  const context={state,nodes:{groups,summary},Date:{now:()=>now},root:{contains:node=>node.mounted},currentScope:()=>scope,getOrder:()=>order,
    canonicalMetric:value=>value,sameContext:saved=>!state.destroyed&&Object.keys(current).every(key=>current[key]===saved[key]),
    findBattleOriginFocus(){lookup++;return replacement;},cancelUITimer:id=>timers.delete(id),
    window:{setTimeout(callback,delay){const id=++sequence;timers.set(id,{callback,at:now+delay});return id;}}};
  vm.createContext(context);vm.runInContext(['sameBattleOriginOrder','clearReturnedSource','returnedSourceMatches','paintReturnedSource','markReturnedSource',
    'discardBattleReturnNeighbor','queueBattleReturn'].map(name=>extract(source,name)).join('\n'),context);
  const origin=()=>({context:{...current},group:'vehicles',source:{summary:false,card:'synthetic-vehicle',battle:'synthetic-battle',metric:null,statistic:null}});
  function advance(ms){const end=now+ms;let turns=0;while(true){let next=null;for(const [id,timer]of timers)if(timer.at<=end&&(!next||timer.at<next[1].at))next=[id,timer];if(!next)break;assert(++turns<1000,'Marker scheduling stays bounded');now=next[1].at;timers.delete(next[0]);next[1].callback();}now=end;}
  const first=action();context.markReturnedSource(origin(),first);
  assert(first.classList.contains('ss-source-returned'));assert.strictEqual(timers.size,1);
  advance(1000);assert.strictEqual(lookup,0,'Mounted source controls need no descriptor query');assert.strictEqual(first.adds,1,'An unchanged marker needs no repeated DOM mutation');
  first.mounted=false;replacement=action();advance(100);
  assert(!first.classList.contains('ss-source-returned'));assert(replacement.classList.contains('ss-source-returned'));assert.strictEqual(lookup,1);
  for(const change of ['group','order','revision','account','range','destroy']){
    const node=action();state.group='vehicles';state.destroyed=false;order={metric:'off',statistic:'avg',direction:'desc',chronology:'newest'};scope={data_revision:'one',summary:{}};
    current={account_key:'synthetic-return',scope:'timeline',period_id:'synthetic-range'};context.markReturnedSource(origin(),node);
    if(change==='group')state.group='maps';else if(change==='order')order={...order,direction:'asc'};else if(change==='revision')scope.data_revision='two';
    else if(change==='account')current.account_key='replacement';else if(change==='range')current.period_id='replacement';else state.destroyed=true;
    advance(100);assert(!node.classList.contains('ss-source-returned'),change);assert.strictEqual(state.returnedSource,null,change);assert.strictEqual(timers.size,0,change);
  }
  state.group='vehicles';state.destroyed=false;current={account_key:'synthetic-return',scope:'timeline',period_id:'synthetic-range'};
  const expires=action();context.markReturnedSource(origin(),expires);advance(4999);assert(expires.classList.contains('ss-source-returned'));advance(1);
  assert(!expires.classList.contains('ss-source-returned'));assert.strictEqual(state.returnedSource,null);assert.strictEqual(state.returnedSourceTimer,null);assert.strictEqual(timers.size,0,'Nothing remains scheduled after expiry');
  const invalid=action();invalid.getAttribute=()=>null;context.markReturnedSource(origin(),invalid);assert.strictEqual(state.returnedSource,null,'A fallback tab never becomes a source marker');
  const wrongCard=action();wrongCard.parentNode.id='another-vehicle';context.markReturnedSource(origin(),wrongCard);assert.strictEqual(state.returnedSource,null,'The same battle under a different card is not the source');
  const wrongMetric=action(),get=wrongMetric.getAttribute;wrongMetric.getAttribute=key=>key==='data-ss-source-metric'?'xp_base':get(key);context.markReturnedSource(origin(),wrongMetric);assert.strictEqual(state.returnedSource,null,'A different metric cannot inherit the source marker');
  const wrongOwner=origin();wrongOwner.source.summary=true;context.markReturnedSource(wrongOwner,action());assert.strictEqual(state.returnedSource,null,'A group control cannot impersonate a summary source');
  const wrongRow=action();wrongRow.tagName='DIV';context.markReturnedSource(origin(),wrongRow);assert.strictEqual(state.returnedSource,null,'The history row cannot impersonate its Show battle button');
  const finance=(statistic)=>{const node=action(),get=node.getAttribute;
    node.getAttribute=key=>key==='data-ss-source-metric'?'credits_income_received':key==='data-ss-extreme'?statistic:get(key);return node;};
  const min=finance('min'),max=finance('max'),financialOrigin=origin();
  Object.assign(financialOrigin.source,{metric:'credits_income_received',statistic:'min'});
  context.markReturnedSource(financialOrigin,max);
  assert.strictEqual(state.returnedSource,null,'Max cannot inherit the returned Min marker for the same battle');
  context.markReturnedSource(financialOrigin,min);
  assert(min.classList.contains('ss-source-returned')&&!max.classList.contains('ss-source-returned'));
  financialOrigin.source={...financialOrigin.source,statistic:'max'};
  context.markReturnedSource(financialOrigin,max);
  assert(!min.classList.contains('ss-source-returned')&&max.classList.contains('ss-source-returned'),'A new exact source replaces the previous marker');
  context.clearReturnedSource();
  let busy=true,finished=0,rendered=0,status=null;
  groups.getAttribute=()=>String(busy);
  context.render=()=>{rendered++;busy=false;};
  context.setActionError=message=>{status=message;};
  context.t=key=>key;
  context.cancelBattleNavigation=()=>{state.battleReturn=null;};
  context.finishBattleReturn=()=>{finished++;};
  const returning={origin:origin(),phase:'restore',page:1,neighbor:0,deadline:now+50,settleDeadline:null};
  state.battleReturn=returning;state.battleReturnTimer=null;
  state.feed={start:0,last:1,cache:{1:[]},pending:{page:0,timer:null}};
  context.queueBattleReturn(returning);advance(100);
  assert.strictEqual(rendered,1,'The overall deadline drops a stalled optional neighbor with the source already available');
  assert.strictEqual(state.feed.pending,null);
  assert.strictEqual(state.feed.start,1);
  assert.strictEqual(state.battleReturn,returning);
  assert.strictEqual(status,null);
  advance(100);
  assert.strictEqual(finished,1,'A newly mounted source can settle and restore focus after the fetch deadline');
  assert.strictEqual(returning.settleDeadline,now+2000);
  advance(2000);context.queueBattleReturn(returning);advance(100);
  assert.strictEqual(status,'page.error','The extra layout interval remains bounded');
  assert.strictEqual(state.battleReturn,null);
};
if(require.main===module){module.exports();process.stdout.write('Actual-source returned-action ownership, replacement and expiry checks passed.\n');}
