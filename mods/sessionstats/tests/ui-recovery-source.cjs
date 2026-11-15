/* Execute the shipped recovery controls without a browser or game dependency. */
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
module.exports=function(){
  const source=fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8');
  const english=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages.en;
  function actual(name){const start=source.indexOf('    function '+name+'('),end=source.indexOf('\n    }\n',start)+7;
    assert(start>=0&&end>start,'Exercise shipped '+name);return source.slice(start,end);}
  class Node{
    constructor(tag,className,text){this.tag=tag;this.className=className||'';this.textContent=text||'';this.children=[];this.attributes={};this.parentNode=null;}
    appendChild(child){child.parentNode=this;this.children.push(child);return child;}
    insertBefore(child,following){child.parentNode=this;const at=this.children.indexOf(following);this.children.splice(at<0?this.children.length:at,0,child);return child;}
    removeChild(child){this.children.splice(this.children.indexOf(child),1);child.parentNode=null;}
    setAttribute(name,value){this.attributes[name]=String(value);}
    getAttribute(name){return this.attributes[name]===undefined?null:this.attributes[name];}
    contains(child){return child===this||this.children.some(node=>node.contains(child));}
    querySelector(selector){const name=selector.slice(1);for(const child of this.children){if(child.className.split(' ').includes(name))return child;const found=child.querySelector(selector);if(found)return found;}return null;}
  }
  const root=new Node('main'),summary=root.appendChild(new Node('div')),card=root.appendChild(new Node('div','ss-group'));
  card.setAttribute('data-group-id','101');card.appendChild(new Node('div','ss-details'));
  summary.appendChild(new Node('span','ss-recovery-summary'));
  const makePayload=()=>({account_key:'EU:fixture',generated_at:10,recovery:{pending:1,in_flight:0},
    scopes:{launch:{period_id:'launch-fixture',summary:{battles:2,partial_results:1,missing_results:1},battles:[]}}});
  const state={scope:'launch',group:'battles',payload:makePayload(),groupCards:[card],list:[],cardPages:[]};
  const commands=[],context={root,state,nodes:{summary},english,helpTarget:null,helpPending:null,hideHelp(){},helpTooltip:new Node('div'),
    t:(key,args)=>{let text=english[key];assert.strictEqual(typeof text,'string','Known translation '+key);(args||[]).forEach((arg,index)=>text=text.split('{'+index+'}').join(String(arg)));return text;},
    number:value=>typeof value==='number'?String(value):'—',integer:String,
    date:value=>typeof value==='number'?'DATE:'+value:'—',
    element:(...args)=>new Node(...args),append:(parent,child)=>parent.appendChild(child),
    viewContext:()=>({account_key:state.payload.account_key,scope:'launch',period_id:state.payload.scopes.launch.period_id}),
    currentScope:()=>state.payload.scopes.launch,
    sameContext:saved=>saved.account_key===state.payload.account_key&&saved.period_id===state.payload.scopes.launch.period_id,
    invoke:(action,args)=>{commands.push({action,...args});return true;}};
  context.helpTooltip.id='help';vm.createContext(context);
  vm.runInContext(['recoverySummary','recoveryData','recoveryLabel','recoveryHelp','updateBattleRecovery','recoveryOnlyUpdate'].map(actual).join('\n'),context);
  const row={id:'101',outcome:null,recovery:{report_state:'never_received',status:'unavailable',reason:'never_received',
    attempts:4,last_attempt:1700000000,next_attempt:1700000300,code:-10,source:'cache',retry_allowed:true}};
  state.payload.scopes.launch.battles=[row];state.list=[row];state.cardPages=[{items:[row]}];
  context.updateBattleRecovery(card,row);
  const status=card.querySelector('.ss-recovery-status'),button=card.querySelector('.ss-recovery-retry');
  assert.strictEqual(status.textContent,'Report unavailable');
  assert(status.getAttribute('data-ss-help').includes('Client code: -10'));
  assert(status.getAttribute('data-ss-help').includes('No report received.'));
  button.onclick();button.onclick();assert.deepStrictEqual(commands,[{action:'retry_result',account_key:'EU:fixture',arena_id:'101'}]);
  const updated=JSON.parse(JSON.stringify(state.payload));updated.generated_at+=5;
  updated.scopes.launch.battles[0].recovery.status='in_flight';updated.scopes.launch.battles[0].recovery.retry_allowed=false;
  assert.strictEqual(context.recoveryOnlyUpdate(updated),true);
  assert.strictEqual(card.querySelector('.ss-recovery-status'),status);assert.strictEqual(card.querySelector('.ss-recovery-retry'),button);
  assert.strictEqual(status.textContent,'Fetching report');assert.strictEqual(button.disabled,true);
  button.onclick();assert.strictEqual(commands.length,1);
  assert.strictEqual(summary.querySelector('.ss-recovery-summary').textContent,'Complete 1 · Partial 1 · Unknown 1 · Fetching (account) 0');
  // A retained infinite-scroll card can be outside the current backend page.
  const offPage=JSON.parse(JSON.stringify(updated));offPage.scopes.launch.battles=[];
  state.payload=offPage;
  const selected=JSON.parse(JSON.stringify(offPage));selected.recovery.selected={id:'101',...row.recovery,status:'cooldown',retry_allowed:false};
  assert.strictEqual(context.recoveryOnlyUpdate(selected),true);
  assert.strictEqual(card.querySelector('.ss-recovery-status'),status);assert.strictEqual(status.textContent,'Client cooldown');
  assert.strictEqual(state.list[0].id,'101');assert.strictEqual(state.list[0].outcome,null);
  assert.strictEqual(state.cardPages[0].items[0].recovery.status,'cooldown');
  assert.strictEqual(card._ssRecoveryBattle.id,'101');
  state.payload=updated;
  const revised=JSON.parse(JSON.stringify(updated));revised.scopes.launch.battles[0].outcome='win';
  assert.strictEqual(context.recoveryOnlyUpdate(revised),false,'A real result requires the ordinary data update path');
  const changedAccount=JSON.parse(JSON.stringify(updated));changedAccount.account_key='NA:fixture';
  assert.strictEqual(context.recoveryOnlyUpdate(changedAccount),false,'Recovery cannot shortcut an account change');
  state.payload.account_key='NA:fixture';button.disabled=false;button.onclick();assert.strictEqual(commands.length,1,'Retained handler rejects another account');
  const known={id:'101',outcome:'win',recovery:{report_state:'partial_report',status:'partial_report',reason:'missing_xp',source:'native_cache',last_attempt:0,next_attempt:0}};
  context.updateBattleRecovery(card,known);
  assert.strictEqual(status.textContent,'Partial report');
  assert(status.getAttribute('data-ss-help').includes('Some XP data is missing.'));
  assert(status.getAttribute('data-ss-help').includes('Observed client read'));
  assert(status.getAttribute('data-ss-help').includes('Last attempt: —'));
  assert(!status.getAttribute('data-ss-help').includes('DATE:0'));
  for(const statusName of ['queued','in_flight','cooldown','rate_limited','not_ready','disconnected','unavailable','rejected','not_returned','outcome_missing']){
    known.recovery.status=statusName;context.updateBattleRecovery(card,known);
    assert.strictEqual(status.textContent,english['recovery.status.'+statusName]);
  }
  known.recovery.reason='<private raw payload>';known.recovery.source='secret';known.recovery.code=123456;
  const safe=context.recoveryHelp(known.recovery);assert(!safe.includes('private'));assert(!safe.includes('secret'));assert(!safe.includes('123456'));
  known.recovery.report_state='complete';context.updateBattleRecovery(card,known);assert.strictEqual(card.querySelector('.ss-recovery'),null);
  state.scope='instance';context.updateBattleRecovery(card,row);assert.strictEqual(card.querySelector('.ss-recovery'),null,'Shared history cannot target the active account');
};
if(require.main===module){module.exports();console.log('Recovery report states, safe diagnostics, guarded retry and stable DOM updates passed.');}
