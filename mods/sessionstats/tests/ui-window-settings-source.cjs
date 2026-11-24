/* Reentrant cleanup must not carry a previous account's native window size. */
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
const shipped=()=>fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8').replace(/\r\n/g,'\n');
function sourceFunction(source,name) {
  const start=source.indexOf('    function '+name+'('),line=source.indexOf('\n',start);
  const end=source.slice(start,line).endsWith('}') ? line : source.indexOf('\n    }\n',start)+7;
  assert(start>=0 && end>start,'Exercise actual shipped '+name);return source.slice(start,end);
}
function assertAccountWindowSource(source=shipped()) {
  const settings={background_transparency:45,maximized:false,restored_width:840,restored_height:680};
  const root={style:{},classList:{add(){},remove(){}},getBoundingClientRect:()=>({width:1780,height:1180})};
  const node=()=>({style:{},attributes:{},setAttribute(key,value){this.attributes[key]=String(value);}});
  const nodes={maximize:node(),status:node(),'window-background':node(),'background-transparency':node()};
  const timers=new Map(), commands=[];let nextTimer=0;
  const state={bound:true,destroyed:false,nativeScale:1,scope:'launch',battleReturn:null,battleReturnTimer:null,
    logicalSize:{width:1780,height:1180},
    windowPrefs:{background_transparency:30,maximized:true,restored_width:700,restored_height:620},
    windowPending:{id:'previous-account-maximize'},windowChanges:{maximized:true},groupCards:[],targetSequence:0,
    windowSequence:0,windowTimer:null,windowTimerToken:0,
    resizeQueued:false,resizeMeasureToken:0,resizeTimer:null,payload:{account_key:'previous-account',
      viewport:{width:1800,height:1200,scale:1},window_size:[700,620]}};
  const context={state,nodes,root,document:{documentElement:{style:{}}},window:{innerWidth:1800,innerHeight:1200,requestAnimationFrame(){},
    setTimeout(callback,delay){timers.set(++nextTimer,{callback,delay});return nextTimer;},
    clearTimeout(id){timers.delete(id);}},
    hasNumber:value=>typeof value==='number' && Number.isFinite(value),t:key=>key,
    closeSelect(){},historyOnlyUpdate(){return false;},showReset(){},finishBackgroundDrag(){},
    invalidateCardFlow(){},retireFeed(){},resetViewScroll(){},cancelBattleNavigation(){},applyLanguage(){},
    hasOlderOrderReply(){return false;},hasOlderPageReply(){return false;},
    setActionError(message){assert.notStrictEqual(message,'error.snapshot');state.actionError=message;},
    setStatus(message){nodes.status.textContent=message;},
    invoke(action,args){commands.push({action,...args});return true;},
    render(){context.queueResize();},applyAppearance(appearance){context.applyWindowSettings(appearance.window_settings,appearance.window_settings_result);}};
  vm.createContext(context);
  const names=['unwrap','windowDefaults','copyWindowSettings','mergeWindowSettings','showWindowSettings','resetWindowSettings',
    'retireWindowPending','cancelWindowCommit','cancelUITimer','windowSaveFailed','commitWindowSettings','scheduleWindowCommit',
    'previewWindowSettings','applyWindowSettings','clearBattleTarget','windowSizeBounds','resizePanelDimensions','queueResize',
    'scopeName','currentScope','consumeBattleReturn','clearOrderIntent','hasOlderHistoryReply','update'];
  vm.runInContext(names.map(name=>sourceFunction(source,name)).join('\n'),context);
  const consume=context.consumeBattleReturn;let returnChecks=0;
  context.consumeBattleReturn=function(scope){
    assert.strictEqual(scope,state.payload.scopes.launch,'The return helper receives the updated account scope');
    returnChecks++;return consume(scope);
  };
  const payload={account_key:'new-account',viewport:{width:1800,height:1200,scale:1},window_size:[840,680],
    appearance:{window_settings:settings},scopes:{launch:{},manual:{}}};
  assert.strictEqual(context.update(payload),true);
  assert.strictEqual(state.logicalSize.width,840,'Cleanup resizing cannot retain the previous account\'s requested width');
  assert.strictEqual(state.logicalSize.height,680,'The new account retains its requested height before the display minimum');
  assert.strictEqual(root.style.width,'840rem');assert.strictEqual(root.style.height,'730rem');
  assert.strictEqual(nodes.maximize.attributes['aria-pressed'],'false');
  assert.strictEqual(nodes['background-transparency'].attributes['aria-valuenow'],'45');
  assert.strictEqual(state.windowPending,null,'The previous account\'s pending maximize reply is retired');
  payload.appearance.window_settings_result={request_id:'previous-account-maximize',saved:true};
  assert.strictEqual(context.update(payload),true);
  assert.strictEqual(root.style.width,'840rem');assert.strictEqual(root.style.height,'730rem');
  assert.strictEqual(returnChecks,2,'Both valid snapshots exercise the real inactive return helper');
  assert.strictEqual(state.battleReturn,null);
  assert.strictEqual(state.battleReturnTimer,null);

  context.previewWindowSettings({maximized:true},true);
  const first=state.windowPending, lost=timers.get(first.timer);
  assert.strictEqual(lost.delay,10000);
  context.previewWindowSettings({background_transparency:75},true);
  assert.strictEqual(commands.length,1,'The newer edit remains staged behind the outstanding save');
  lost.callback();
  assert.strictEqual(state.windowPending,null);
  assert.strictEqual(state.windowPrefs.maximized,false,'The unanswered save rolls back with its deadline');
  assert.strictEqual(state.windowPrefs.background_transparency,75,'The newer unsent edit remains visible');
  assert.strictEqual(commands.at(-1).action,'viewport','A single fresh snapshot recovers a committed but unanswered save');
  timers.get(state.windowTimer).callback();
  const second=state.windowPending;
  assert.notStrictEqual(second.id,first.id);
  assert.strictEqual(commands.at(-1).background_transparency,75);
  assert.strictEqual(commands.at(-1).maximized,undefined);
  lost.callback();
  assert.strictEqual(state.windowPending,second,'A retired deadline cannot cancel another write');

  context.previewWindowSettings({restored_width:900},true);
  context.applyWindowSettings(settings,{request_id:second.id,saved:false});
  assert.strictEqual(state.windowPrefs.background_transparency,45,'A rejected save rolls back its own change');
  assert.strictEqual(state.windowPrefs.restored_width,900,'A rejected save leaves a newer size ready to save');
  timers.get(state.windowTimer).callback();
  const third=state.windowPending;
  assert.strictEqual(commands.at(-1).restored_width,900);
  context.applyWindowSettings({...settings,restored_width:900},{request_id:third.id,saved:true});
  assert.strictEqual(state.windowPending,null);
  assert(!timers.has(third.timer),'The matching reply retires the window watchdog');
  state.payload=null;
  const commandCount=commands.length;
  context.previewWindowSettings({background_transparency:90},true);
  assert.strictEqual(state.windowTimer,null,'An edit before account data must not retry in a tight timer loop');
  assert.strictEqual(commands.length,commandCount);
  assert.strictEqual(state.windowPrefs.background_transparency,45);
}
module.exports=assertAccountWindowSource;
if(require.main===module) {assertAccountWindowSource();process.stdout.write('Actual-source account window-size reset regression passed.\n');}
