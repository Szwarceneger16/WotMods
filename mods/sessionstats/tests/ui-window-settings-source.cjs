/* Reentrant cleanup must not carry a previous account's native window size. */
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
const shipped=()=>fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8');
function sourceFunction(source,name) {
  const start=source.indexOf('    function '+name+'('),line=source.indexOf('\n',start);
  const end=source.slice(start,line).endsWith('}') ? line : source.indexOf('\n    }\n',start)+7;
  assert(start>=0 && end>start,'Exercise actual shipped '+name);return source.slice(start,end);
}
function assertAccountWindowSource(source=shipped()) {
  const settings={background_transparency:45,maximized:false,restored_width:840,restored_height:680};
  const root={style:{},classList:{add(){},remove(){}},getBoundingClientRect:()=>({width:1780,height:1180})};
  const node=()=>({style:{},attributes:{},setAttribute(key,value){this.attributes[key]=String(value);}});
  const nodes={maximize:node(),'window-background':node(),'background-transparency':node()};
  const state={bound:true,destroyed:false,nativeScale:1,logicalSize:{width:1780,height:1180},
    windowPrefs:{background_transparency:30,maximized:true,restored_width:700,restored_height:620},
    windowPending:{id:'previous-account-maximize'},windowChanges:{maximized:true},groupCards:[],targetSequence:0,
    resizeQueued:false,resizeMeasureToken:0,resizeTimer:null,payload:{account_key:'previous-account',
      viewport:{width:1800,height:1200,scale:1},window_size:[700,620]}};
  const context={state,nodes,root,document:{documentElement:{style:{}}},window:{innerWidth:1800,innerHeight:1200,requestAnimationFrame(){}},
    hasNumber:value=>typeof value==='number' && Number.isFinite(value),t:key=>key,
    closeSelect(){},historyOnlyUpdate(){return false;},showReset(){},cancelWindowCommit(){},finishBackgroundDrag(){},
    cancelUITimer(){},invalidateCardFlow(){},retireFeed(){},resetViewScroll(){},cancelBattleNavigation(){},applyLanguage(){},
    setStatus(message){throw Error(message);},windowSaveFailed(){throw Error('Unexpected rejected window save');},
    render(){context.queueResize();},applyAppearance(appearance){context.applyWindowSettings(appearance.window_settings,appearance.window_settings_result);}};
  vm.createContext(context);
  const names=['unwrap','windowDefaults','copyWindowSettings','mergeWindowSettings','showWindowSettings','resetWindowSettings',
    'applyWindowSettings','clearBattleTarget','windowSizeBounds','resizePanelDimensions','queueResize','update'];
  vm.runInContext(names.map(name=>sourceFunction(source,name)).join('\n'),context);
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
}
module.exports=assertAccountWindowSource;
if(require.main===module) {assertAccountWindowSource();process.stdout.write('Actual-source account window-size reset regression passed.\n');}
