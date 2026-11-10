/* Panel-fit sorting controls and an owned loading indicator retain their geometry. */
const assert=require('assert'),fs=require('fs'),path=require('path'),vm=require('vm');
function assertFilterStateSource(source=fs.readFileSync(path.join(__dirname,'../ui/session_stats.js'),'utf8')){
  const actual=name=>{const start=source.indexOf('    function '+name+'('),line=source.indexOf('\n',start);
    const end=source.slice(start,line).endsWith('}')?line:source.indexOf('\n    }\n',start)+7;
    assert(start>=0&&end>start,'Exercise actual shipped '+name);return source.slice(start,end);};
  class Node{
    constructor(){this.style={};this.attributes={};this.disabled=false;this.textContent='';this.label=null;const names=new Set();
      this.classList={add:name=>names.add(name),remove:name=>names.delete(name),contains:name=>names.has(name)};}
    setAttribute(name,value){this.attributes[name]=String(value);}getAttribute(name){return this.attributes[name]||null;}
    querySelector(selector){if(selector==='.ss-control-label')return this.label||(this.label=new Node());return null;}
  }
  const controls={'ss-sort-off':new Node(),'ss-filter-loading':new Node(),'ss-sorting':new Node()},statistic=new Node();
  const scope={period_id:'synthetic-filter-period',loading:false,load_error:'',pagination:{},ordering:{
    vehicles:{metric:'xp_received',statistic:'avg',direction:'desc',chronology:'newest'},
    battles:{metric:'off',statistic:'avg',direction:'desc',chronology:'newest'},
    maps:{metric:'off',statistic:'avg',direction:'desc',chronology:'newest'}}};
  const state={payload:{account_key:'synthetic-filter-account',loading:false,load_error:'',scopes:{launch:scope,instance:scope}},
    scope:'launch',group:'vehicles',nativeSession:true,orders:{},orderIntent:null,wideFilters:true,feed:null};
  const commands=[],selects={},context={state,selects,Object,String,JSON,
    document:{getElementById:id=>controls[id]||(controls[id]=new Node()),querySelector:selector=>selector==='.ss-sort-statistic'?statistic:null},
    t:key=>key,currentScope:()=>scope,scopeName:()=>state.scope,
    viewContext:()=>({account_key:state.payload.account_key,scope:state.scope,period_id:scope.period_id}),
    sameContext:owner=>owner.account_key===state.payload.account_key&&owner.scope===state.scope&&owner.period_id===scope.period_id,
    cancelBattleNavigation(){},retireFeed(){state.feed=null;},render(){},
    invoke:(action,args)=>{commands.push({action,...JSON.parse(JSON.stringify(args))});return true;}};
  vm.createContext(context);
  const declarations=source.slice(source.indexOf('    var defaultOrder ='),source.indexOf('    function orderKey('));
  assert(declarations.includes('selectOptions'));vm.runInContext(declarations,context);
  for(const field of ['chronology','statistic','metric','direction']){
    selects[field]={trigger:new Node(),label:new Node(),menu:new Node(),options:context.selectOptions[field].map(()=>new Node())};
  }
  for(const name of ['orderKey','getOrder','groupSortValue','ordered','orderingUnavailable','changeOrder','rememberedMetric','toggleMetricOrder','renderSelects','renderFilterActivity'])
    vm.runInContext(actual(name),context);
  context.hasNumber=value=>typeof value==='number'&&Number.isFinite(value);
  const render=()=>context.renderSelects(scope),ack=()=>{const command=commands[commands.length-1];scope.ordering[state.group]={metric:command.metric,statistic:command.statistic,direction:command.direction,chronology:command.chronology};state.orderIntent=null;render();};
  render();assert.strictEqual(controls['ss-sort-off'].getAttribute('aria-pressed'),'true');
  assert.strictEqual(selects.chronology.trigger.disabled,true,'Metric sorting disables the saved date ordering');
  const chronologicalBefore=commands.length;context.changeOrder('chronology','oldest');
  assert.strictEqual(commands.length,chronologicalBefore,'A retained chronology callback cannot reorder an active metric');
  assert.strictEqual(controls['ss-sort-off'].querySelector('.ss-control-label').textContent,'sort.on','An active metric uses the localized On label');
  controls['ss-sort-off'].onclick();assert.strictEqual(commands.at(-1).metric,'off');ack();
  assert.strictEqual(selects.metric.label.textContent,'sort.xp_received','Off retains the last active metric label in the wide dropdown');
  assert.strictEqual(selects.metric.options[0].style.display,'none','Wide mode removes Off from the dropdown');
  assert.strictEqual(controls['ss-sort-off'].getAttribute('aria-pressed'),'false');
  assert.strictEqual(controls['ss-sort-off'].querySelector('.ss-control-label').textContent,'sort.off','An inactive metric uses the localized Off label');
  assert.strictEqual(controls['ss-sort-off'].getAttribute('aria-label'),'sort.label');
  assert.strictEqual(selects.metric.trigger.disabled,true,'Wide Off disables the remembered metric dropdown');
  assert.strictEqual(selects.direction.trigger.disabled,true);
  assert.strictEqual(selects.chronology.trigger.disabled,false,'Off restores the independent date preference');
  controls['ss-sort-off'].onclick();assert.strictEqual(commands.at(-1).metric,'xp_received','Metric On restores the last non-Off metric');ack();
  const before=commands.length;scope.loading=true;render();controls['ss-sort-off'].onclick();context.changeOrder('metric','xp_base');
  assert.strictEqual(commands.length,before,'Busy retained toggle and selector callbacks cannot sort an unavailable projection');
  context.renderFilterActivity(scope);assert.strictEqual(controls['ss-filter-loading'].style.visibility,'visible','A rebuilding projection displays its filter spinner');
  assert.strictEqual(controls['ss-sorting'].getAttribute('aria-busy'),'true');
  scope.load_error='Synthetic filter failure';context.renderFilterActivity(scope);
  assert.strictEqual(controls['ss-filter-loading'].style.visibility,'hidden','A failed projection stops its spinner');
  scope.loading=false;scope.load_error='';state.orderIntent={context:context.viewContext(),group:state.group,options:scope.ordering.vehicles};
  context.renderFilterActivity(scope);assert.strictEqual(controls['ss-filter-loading'].style.visibility,'visible','A pending native sort owns the spinner before loading data arrives');
  state.orderIntent=null;state.feed={pending:{id:'synthetic-page'}};context.renderFilterActivity(scope);
  assert.strictEqual(controls['ss-filter-loading'].style.visibility,'visible','An owned page fetch uses the reserved filter spinner');
  state.feed=null;context.renderFilterActivity(scope);assert.strictEqual(controls['ss-filter-loading'].style.visibility,'hidden');
  state.payload.loading=true;context.renderFilterActivity(scope);assert.strictEqual(controls['ss-filter-loading'].style.visibility,'visible');
  state.scope='instance';context.renderFilterActivity(scope);assert.strictEqual(controls['ss-filter-loading'].style.visibility,'hidden','Account history loading does not mark a ready installation scope busy');
  state.scope='launch';state.payload.loading=false;state.group='battles';render();
  const battleBefore=commands.length;context.changeOrder('statistic','max');
  assert.strictEqual(commands.length,battleBefore,'Battles rejects stale aggregate-statistic callbacks');
  assert.strictEqual(statistic.style.display,'none');assert.strictEqual(selects.statistic.trigger.disabled,true);
  context.changeOrder('metric','battles');assert.strictEqual(commands.length,battleBefore,'Battles rejects the aggregate count metric');
  state.group='vehicles';scope.ordering.vehicles.metric='battles';render();
  assert.strictEqual(statistic.style.display,'none','Recorded counts do not expose an average/minimum/maximum selector');
  const countBefore=commands.length;context.changeOrder('statistic','max');assert.strictEqual(commands.length,countBefore);
  const tied=[{id:'early',started_at:1,first_started_at:0,stats:{xp_base:{avg:10}}},
    {id:'late',started_at:2,first_started_at:0,stats:{xp_base:{avg:10}}}];
  assert.strictEqual(context.ordered(tied,{metric:'xp_base',statistic:'avg',direction:'desc',chronology:'oldest'})[0].id,'late');
  assert.strictEqual(context.ordered(tied,{metric:'off',statistic:'avg',direction:'desc',chronology:'oldest'})[0].id,'early');
  const counts=[{id:'received',started_at:1,stats:{battles:4,observed_battles:4}},{id:'pending',started_at:2,stats:{battles:3,observed_battles:5}}];
  assert.strictEqual(context.ordered(counts,{metric:'battles',statistic:'avg',direction:'desc',chronology:'oldest'})[0].id,'pending');
  scope.ordering.vehicles.metric='xp_received';
  state.group='vehicles';state.wideFilters=false;render();const narrowBefore=commands.length;controls['ss-sort-off'].onclick();
  assert.strictEqual(commands.length,narrowBefore,'A hidden wide-only toggle cannot act in narrow mode');assert.strictEqual(selects.metric.options[0].style.display,'');
  state.wideFilters=true;render();const stale=controls['ss-sort-off'].onclick;
  state.payload.account_key='synthetic-filter-other-account';scope.ordering.vehicles.metric='off';render();stale();
  assert.strictEqual(commands.length,narrowBefore,'A retained Off callback cannot sort another account');
  controls['ss-sort-off'].onclick();assert.strictEqual(commands.at(-1).metric,'xp_base','Another account starts with its own metric preference');
  assert.strictEqual(commands.at(-1).account_key,state.payload.account_key);ack();
  state.group='maps';render();controls['ss-sort-off'].onclick();assert.strictEqual(commands.at(-1).metric,'xp_base','Groups keep independent remembered metric preferences');ack();
  state.destroyed=true;const destroyed=commands.length;controls['ss-sort-off'].onclick();context.changeOrder('metric','xp_received');context.renderFilterActivity(scope);
  assert.strictEqual(commands.length,destroyed);assert.strictEqual(controls['ss-filter-loading'].style.visibility,'hidden','Teardown retires callbacks and the activity indicator');
  // Native fit decisions must include the candidate Off width before choosing
  // a layout, reserve the spinner space, and measure this panel rather than
  // the much wider game viewport. The dimensions here model one candidate row.
  const bar=controls['ss-list-controls']=new Node(),meta=new Node(),pagination=new Node();
  const sorting=controls['ss-sorting'],slot=controls['ss-filter-loading'];slot.id='ss-filter-loading';
  bar.children=[meta,pagination,sorting,slot];let panelWidth=800,sortingBottom=50;
  const bounds=(left,right,bottom=50,height=30)=>({left:(20+left)*state.nativeScale,right:(20+right)*state.nativeScale,
    top:(bottom-height)*state.nativeScale,bottom:bottom*state.nativeScale,width:(right-left)*state.nativeScale,height:height*state.nativeScale});
  bar.getBoundingClientRect=()=>bounds(0,panelWidth,50,50);
  meta.getBoundingClientRect=()=>bounds(0,100);
  pagination.getBoundingClientRect=()=>bounds(108,448);
  sorting.getBoundingClientRect=()=>bounds(456,750+(controls['ss-sort-off'].style.display==='none'?0:48),sortingBottom);
  // The absolute activity slot has an independent baseline. It does not
  // participate in the row; its 28 logical pixels are reserved separately.
  slot.getBoundingClientRect=()=>bounds(panelWidth-24,panelWidth,65,24);
  context.closeSelect=()=>{};vm.runInContext(actual('layoutFilterControls'),context);
  state.destroyed=false;state.group='vehicles';state.payload.viewport={width:3840,height:2400};
  for(const scale of [1,2]){
    state.nativeScale=scale;state.wideFilters=false;panelWidth=800;sortingBottom=50;render();
    for(let attempt=0;attempt<5;attempt++){
      context.layoutFilterControls();
      assert.strictEqual(state.wideFilters,false,'A candidate Off button is measured before fitting at '+scale+'x');
      assert.strictEqual(bar.classList.contains('ss-filters-wide'),false,'A near-threshold panel must not alternate wide and narrow layouts');
      assert.strictEqual(controls['ss-sort-off'].style.display,'none');
    }
    panelWidth=810;context.layoutFilterControls();
    assert.strictEqual(state.wideFilters,false,'The candidate reserves 28 logical pixels for activity at '+scale+'x');
    panelWidth=830;context.layoutFilterControls();
    assert.strictEqual(state.wideFilters,true,'A truly fitting candidate uses wide controls at '+scale+'x');
    assert.strictEqual(bar.classList.contains('ss-filters-wide'),true);assert.strictEqual(controls['ss-sort-off'].style.display,'flex');
    sortingBottom=52;context.layoutFilterControls();
    assert.strictEqual(state.wideFilters,false,'Candidate controls must share the same bottom edge at '+scale+'x');
    sortingBottom=50;context.layoutFilterControls();assert.strictEqual(state.wideFilters,true,'A stable aligned row can become wide again');
  }
}
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let remaining=10;function next(){if(--remaining)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);}));
module.exports=async({browser,nativeHost,check})=>{
  assertFilterStateSource();check('Actual-source Off memory, readiness, context ownership and loading-state regressions pass',true);
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:3840,height:2400},viewport:{width:3840,height:2400,scale}});
    const caption=' at '+(scale*100)+'%',count=()=>page.evaluate(()=>__grzCommands.filter(command=>command.action==='sort').length);
    const acknowledge=async()=>{await page.evaluate(()=>{const command=__grzCommands.filter(item=>item.action==='sort').pop();
      const payload=JSON.parse(model.payload),scope=payload.scopes[command.scope];
      scope.ordering=scope.ordering||{};scope.ordering[command.group]={metric:command.metric,statistic:command.statistic,direction:command.direction,chronology:command.chronology};
      if(scope.pagination&&scope.pagination[command.group])scope.pagination[command.group].page=0;
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();});await frames(page);};
    const choose=async(field,value)=>{await page.locator('#ss-sort-'+field+' .ss-select-trigger').click();
      await page.locator('#ss-sort-'+field+' [data-value="'+value+'"]').click();await acknowledge();};
    const width=async value=>{await page.evaluate(value=>{const payload=JSON.parse(model.payload);payload.window_size=[value,850];
      payload.appearance=payload.appearance||{};payload.appearance.window_settings={background_transparency:0,maximized:false,restored_width:value,restored_height:850};
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},value);await frames(page);};
    const geometry=()=>page.evaluate(()=>{const rect=node=>{const box=node.getBoundingClientRect();return {top:box.top,bottom:box.bottom,left:box.left,right:box.right,width:box.width,height:box.height};};
      return {filters:rect(document.getElementById('ss-filter-panel')),slot:rect(document.getElementById('ss-filter-loading')),
        sorting:rect(document.getElementById('ss-sorting')),scroll:document.getElementById('ss-scroll').scrollTop};});
    try{
      await page.evaluate(scale=>{const payload=JSON.parse(model.payload);payload.account_key='synthetic-filter-ux-'+scale;
        payload.viewport={width:3840,height:2400,scale};payload.window_size=[1500,850];payload.localization={language:'en',messages:{}};
        payload.appearance=payload.appearance||{};payload.appearance.window_settings={background_transparency:0,maximized:false,restored_width:1500,restored_height:850};
        payload.scopes.timeline=JSON.parse(JSON.stringify(payload.scopes.manual));payload.scopes.timeline.period_id='synthetic-filter-timeline';
        payload.scopes.timeline.from_point=payload.scopes.timeline.to_point='';payload.scopes.timeline.loading=false;payload.scopes.timeline.load_error='';
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();});await frames(page);
      check('A fitting wide panel exposes the adjacent Off toggle'+caption,
        await page.locator('#ss-sort-off').isVisible()&&await page.locator('.ss-list-controls').evaluate(node=>node.classList.contains('ss-filters-wide')));
      if(await page.locator('#ss-sort-off').getAttribute('aria-pressed')==='false'){
        check('Inactive wide sorting labels its toggle Off and disables its metric dropdown'+caption,
          await page.locator('#ss-sort-off').textContent()==='Off'&&await page.locator('#ss-sort-metric .ss-select-trigger').isDisabled());
        await page.locator('#ss-sort-off').click();await acknowledge();
      }
      await page.locator('#ss-sort-metric .ss-select-trigger').click();
      check('A wide metric menu removes Off from its visible choices'+caption,!await page.locator('#ss-sort-metric [data-value="off"]').isVisible());
      await page.keyboard.press('Escape');
      await choose('metric','xp_received');
      check('An active metric disables newest/oldest and rejects its retained option callback'+caption,
        await page.locator('#ss-sort-chronology .ss-select-trigger').isDisabled()&&await page.evaluate(()=>{
          const before=__grzCommands.filter(item=>item.action==='sort').length;
          document.querySelector('#ss-sort-chronology [data-value="oldest"]').onclick();
          return __grzCommands.filter(item=>item.action==='sort').length===before;
        }));
      await page.locator('#ss-sort-off').click();await acknowledge();
      check('Off keeps the last active metric visible beside the toggle'+caption,
        await page.locator('#ss-sort-off').getAttribute('aria-pressed')==='false'&&await page.locator('#ss-sort-off').textContent()==='Off'&&
        await page.locator('#ss-sort-metric .ss-select-trigger').textContent()==='Received XP'&&
        await page.locator('#ss-sort-direction .ss-select-trigger').isDisabled()&&await page.locator('#ss-sort-metric .ss-select-trigger').isDisabled());
      await page.locator('#ss-sort-off').click();await acknowledge();
      check('Re-enabling metric sorting restores the last active metric'+caption,await page.evaluate(()=>{
        const command=__grzCommands.filter(item=>item.action==='sort').pop();return command.metric==='xp_received'&&command.account_key===JSON.parse(model.payload).account_key;
      })&&await page.locator('#ss-sort-off').getAttribute('aria-pressed')==='true'&&await page.locator('#ss-sort-off').textContent()==='On');
      await page.locator('#ss-sort-metric .ss-select-trigger').focus();await page.keyboard.press('ArrowDown');await page.keyboard.press('Home');await page.keyboard.press('Enter');
      check('Wide keyboard navigation skips the removed Off option'+caption,await page.evaluate(()=>__grzCommands.filter(item=>item.action==='sort').pop().metric==='xp_base'));
      await acknowledge();
      const row=await page.locator('.ss-list-controls').evaluate(node=>{const controls=[...node.children].filter(child=>{
        const box=child.getBoundingClientRect();return box.width>0&&box.height>0;}).map(child=>child.getBoundingClientRect()),box=node.getBoundingClientRect();
        return {bounded:controls.every(child=>child.left>=box.left-1&&child.right<=box.right+1),row:Math.min(...controls.map(child=>child.bottom))-Math.max(...controls.map(child=>child.top))>0};});
      check('The wide result controls and reserved loading slot share one bounded row'+caption,row.bounded&&row.row);
      await width(500);
      check('A narrow panel retains the original metric dropdown despite the wide game viewport'+caption,
        !await page.locator('#ss-sort-off').isVisible()&&!await page.locator('.ss-list-controls').evaluate(node=>node.classList.contains('ss-filters-wide')));
      await page.locator('#ss-sort-metric .ss-select-trigger').click();
      check('The narrow metric menu still exposes Off'+caption,await page.locator('#ss-sort-metric [data-value="off"]').isVisible());
      await page.keyboard.press('Home');await page.keyboard.press('Enter');
      check('Narrow keyboard selection retains Off as the first option'+caption,await page.evaluate(()=>__grzCommands.filter(item=>item.action==='sort').pop().metric==='off'));
      await acknowledge();
      await page.locator('#ss-group-battles').click();await frames(page);
      const beforeBattleStatistic=await count();
      await page.evaluate(()=>document.querySelector('#ss-sort-statistic [data-value="max"]').onclick());
      check('Battles hides aggregate statistics and rejects retained aggregate callbacks'+caption,
        !await page.locator('.ss-sort-statistic').isVisible()&&(await count())===beforeBattleStatistic);
      await width(1500);await page.locator('#ss-scope-manual').click();await frames(page);
      await page.evaluate(()=>{window.__filterReady=JSON.parse(model.payload);window.__filterCards=[...document.querySelectorAll('#ss-groups .ss-group')];
        const scroll=document.getElementById('ss-scroll');scroll.scrollTop=250;});await frames(page);
      const before=await geometry();
      await page.evaluate(()=>{const payload=JSON.parse(model.payload);payload.scopes.timeline.loading=true;payload.scopes.timeline.load_error='';
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();});await frames(page);
      const loading=await geometry();
      check('A rebuilding range exposes the localized spinner in its reserved slot'+caption,
        await page.locator('#ss-filter-loading').isVisible()&&await page.locator('#ss-filter-loading').getAttribute('role')==='status'&&
        await page.locator('#ss-filter-loading').getAttribute('aria-label')==='Loading page…');
      check('The loading indicator keeps filter geometry and the retained result position'+caption+': '+JSON.stringify({before,loading}),
        Math.abs(before.filters.height-loading.filters.height)<=1&&Math.abs(before.slot.width-loading.slot.width)<=1&&Math.abs(before.scroll-loading.scroll)<=1&&
        await page.evaluate(()=>__filterCards.length>0&&__filterCards.every((node,index)=>node===document.querySelectorAll('#ss-groups .ss-group')[index])));
      const busyBefore=await count();await page.evaluate(()=>document.getElementById('ss-sort-off').onclick());
      check('The busy Off toggle and retained callback obey the projection readiness guard'+caption,
        await page.locator('#ss-sort-off').isDisabled()&&(await count())===busyBefore);
      await page.evaluate(()=>{const payload=JSON.parse(model.payload);payload.scopes.timeline.loading=false;payload.scopes.timeline.load_error='Synthetic filter failure';
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();});await frames(page);
      check('A failed projection stops the spinner while leaving sorting unavailable'+caption,
        !await page.locator('#ss-filter-loading').isVisible()&&await page.locator('#ss-sort-metric .ss-select-trigger').isDisabled());
      await page.evaluate(()=>{model.payload=JSON.stringify(__filterReady);__grzEvents['viewEnv.onDataChanged']();});await frames(page);
      check('A completed projection hides the spinner and restores ordering'+caption,
        !await page.locator('#ss-filter-loading').isVisible()&&await page.locator('#ss-sort-off').isEnabled()&&await page.locator('#ss-sort-chronology .ss-select-trigger').isEnabled());
      if(await page.locator('#ss-sort-off').getAttribute('aria-pressed')==='false'){await page.locator('#ss-sort-off').click();await acknowledge();}
      await page.locator('#ss-sort-metric .ss-select-trigger').click();await page.locator('#ss-sort-metric [data-value="credits_net"]').click();await frames(page);
      check('An unacknowledged native sort immediately owns the filter spinner'+caption,await page.locator('#ss-filter-loading').isVisible());
      await acknowledge();check('The matching native sort acknowledgement clears its spinner'+caption,!await page.locator('#ss-filter-loading').isVisible());
    }finally{await page.close();}
  }
};
module.exports.assertFilterStateSource=assertFilterStateSource;
if(require.main===module){assertFilterStateSource();console.log('Actual-source filter Off memory, projection readiness, account ownership and spinner regressions passed.');}
