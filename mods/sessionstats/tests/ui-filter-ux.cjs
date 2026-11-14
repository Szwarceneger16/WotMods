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
    removeAttribute(name){delete this.attributes[name];}
    querySelector(selector){if(selector==='.ss-control-label')return this.label||(this.label=new Node());return null;}
  }
  const controls={'ss-sort-off':new Node(),'ss-filter-loading':new Node(),'ss-sorting':new Node()},statistic=new Node();
  const scope={period_id:'synthetic-filter-period',loading:false,load_error:'',pagination:{},ordering:{
    vehicles:{metric:'xp_received',statistic:'avg',direction:'desc',chronology:'newest'},
    battles:{metric:'off',statistic:'avg',direction:'desc',chronology:'newest'},
    maps:{metric:'off',statistic:'avg',direction:'desc',chronology:'newest'}}};
  const state={payload:{account_key:'synthetic-filter-account',loading:false,load_error:'',scopes:{launch:scope,instance:scope}},
    scope:'launch',group:'vehicles',nativeSession:true,orders:{},orderIntent:null,wideFilters:true,feed:null};
  const commands=[],selects={},context={state,selects,root:new Node(),Object,String,JSON,
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
  for(const name of ['orderKey','canonicalMetric','creditMetric','metricSeries','summableMetric','getOrder','groupSortValue','ordered','orderingUnavailable','changeOrder','rememberedMetric','toggleMetricOrder','renderSelects','renderFilterActivity','renderSortDataWarning'])
    vm.runInContext(actual(name),context);
  context.hasNumber=value=>typeof value==='number'&&Number.isFinite(value);
  const render=()=>context.renderSelects(scope),ack=()=>{const command=commands[commands.length-1];scope.ordering[state.group]={metric:command.metric,statistic:command.statistic,direction:command.direction,chronology:command.chronology};state.orderIntent=null;render();};
  state.group='tiers';render();
  assert.strictEqual(context.getOrder(scope).chronology,'tier_desc','An unconfigured Tiers tab defaults to highest tier first');
  assert.strictEqual(selects.chronology.label.textContent,'sort.tier_desc');
  assert(selects.chronology.options.every(option=>option.style.display===''),'Tiers exposes numeric and chronological choices in its ordinary selector');
  const tiers=[{id:'XI',tier:11,started_at:1},{id:'IX',tier:9,started_at:2},{id:'II',tier:2,started_at:3},{id:'unknown',tier:null,started_at:4}];
  const tierOrder=chronology=>Array.from(context.ordered(tiers,{metric:'off',statistic:'avg',direction:'desc',chronology}),item=>item.id);
  assert.deepStrictEqual(tierOrder('tier_desc'),['XI','IX','II','unknown'],'Numeric ordering keeps XI above IX and unknown last');
  assert.deepStrictEqual(tierOrder('tier_asc'),['II','IX','XI','unknown'],'Unknown remains last when tier order is ascending');
  assert.deepStrictEqual(tierOrder('newest'),['unknown','II','IX','XI'],'Tiers still permits an explicit ordinary date preference');
  state.group='vehicles';render();
  assert(context.selectOptions.chronology.every((choice,index)=>!choice[0].startsWith('tier_')||selects.chronology.options[index].style.display==='none'),'Tier choices are hidden from other tabs');
  const tierRejected=commands.length;context.changeOrder('chronology','tier_desc');
  assert.strictEqual(commands.length,tierRejected,'Another tab rejects a retained tier-order callback');
  render();assert.strictEqual(controls['ss-sort-off'].getAttribute('aria-pressed'),'true');
  assert.strictEqual(selects.chronology.trigger.disabled,true,'Metric sorting disables the saved date ordering');
  assert(selects.chronology.trigger.classList.contains('ss-select-disabled'),'Metric sorting assigns explicit native-safe disabled paint to ordinary ordering');
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
  assert(!selects.chronology.trigger.classList.contains('ss-select-disabled'),'Off clears the disabled paint from ordinary ordering');
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
  assert.strictEqual(controls['ss-filter-loading'].style.visibility,'visible','An owned page fetch displays the panel loading status');
  state.feed=null;context.renderFilterActivity(scope);assert.strictEqual(controls['ss-filter-loading'].style.visibility,'hidden');
  state.payload.loading=true;context.renderFilterActivity(scope);assert.strictEqual(controls['ss-filter-loading'].style.visibility,'visible');
  state.scope='instance';context.renderFilterActivity(scope);assert.strictEqual(controls['ss-filter-loading'].style.visibility,'hidden','Account history loading does not mark a ready installation scope busy');
  state.scope='launch';state.payload.loading=false;state.group='battles';render();
  const battleBefore=commands.length;context.changeOrder('statistic','max');
  assert.strictEqual(commands.length,battleBefore,'Battles rejects stale aggregate-statistic callbacks');
  assert.strictEqual(statistic.style.visibility,'hidden');assert.strictEqual(statistic.getAttribute('aria-hidden'),'true');assert.strictEqual(selects.statistic.trigger.disabled,true);
  context.changeOrder('metric','battles');assert.strictEqual(commands.length,battleBefore,'Battles rejects the aggregate count metric');
  for(const chronology of ['first_desc','last_asc']){context.changeOrder('chronology',chronology);assert.strictEqual(commands.length,battleBefore,'Battles rejects a retained aggregate-date callback');}
  state.group='vehicles';scope.ordering.vehicles.metric='battles';render();
  assert.strictEqual(statistic.style.visibility,'hidden','Recorded counts keep an inaccessible reserved statistic slot');
  assert.strictEqual(statistic.style.display,'');assert.strictEqual(statistic.getAttribute('aria-hidden'),'true');
  const countBefore=commands.length;context.changeOrder('statistic','max');assert.strictEqual(commands.length,countBefore);
  const rateOrders=JSON.parse(JSON.stringify(scope.ordering));
  for(const group of ['vehicles','maps','tiers']){
    state.group=group;scope.ordering[group]={metric:'win_rate',statistic:'max',direction:'desc',chronology:'newest'};render();
    assert.strictEqual(statistic.style.visibility,'hidden','Win rate keeps its inapplicable statistic out of presentation in '+group);
    assert.strictEqual(statistic.style.display,'');assert.strictEqual(statistic.getAttribute('aria-hidden'),'true');
    assert.strictEqual(selects.statistic.trigger.disabled,true);
    const beforeRate=commands.length;context.changeOrder('statistic','min');assert.strictEqual(commands.length,beforeRate,'Retained statistic callbacks cannot alter win-rate sorting');
    const option=context.selectOptions.metric.findIndex(choice=>choice[0]==='win_rate');
    assert(option>=0&&selects.metric.options[option].style.display==='','Win-rate sorting is offered in '+group);
  }
  state.group='battles';scope.ordering.battles={metric:'win_rate',statistic:'max',direction:'asc',chronology:'oldest'};render();
  const rateOption=context.selectOptions.metric.findIndex(choice=>choice[0]==='win_rate');
  assert.strictEqual(selects.metric.options[rateOption].style.display,'none','Battles hides the meaningless per-result win-rate metric');
  assert.strictEqual(context.getOrder(scope).metric,'off','A legacy native Battles win-rate snapshot falls back to ordinary chronology');
  const rejectedRate=commands.length;context.changeOrder('metric','win_rate');
  assert.strictEqual(commands.length,rejectedRate,'A retained hidden win-rate callback cannot sort Battles');
  context.rememberedMetric(scope,'win_rate');controls['ss-sort-off'].onclick();
  assert.strictEqual(commands.at(-1).metric,'xp_base','The Battles toggle replaces a remembered legacy win-rate metric with XP');ack();
  state.nativeSession=false;state.orders[context.orderKey(scope)]={metric:'win_rate',statistic:'min',direction:'desc',chronology:'newest'};
  assert.strictEqual(context.getOrder(scope).metric,'off','A legacy preview Battles win-rate preference also falls back safely');
  state.nativeSession=true;scope.ordering=rateOrders;state.group='vehicles';
  const rates=[{id:'unknown',stats:{win_rate:null}},{id:'loss',stats:{win_rate:0}},{id:'win',stats:{win_rate:100}}];
  assert.deepStrictEqual(Array.from(context.ordered(rates,{metric:'win_rate',statistic:'min',direction:'desc',chronology:'newest'}),item=>item.id),['win','loss','unknown']);
  assert.deepStrictEqual(Array.from(context.ordered(rates,{metric:'win_rate',statistic:'max',direction:'asc',chronology:'newest'}),item=>item.id),['loss','win','unknown']);
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
  // A fixed full-row budget must ignore both stale native rectangles and
  // selected metrics. Widening is coalesced; shrinking and cleanup retire it.
  const bar=controls['ss-list-controls']=new Node();let panelWidth=900,queued=0;
  const raf=[];context.window={requestAnimationFrame:callback=>raf.push(callback)};
  context.resizePanelDimensions=()=>({width:panelWidth+38});
  context.scrollContentInset=()=>{throw Error('Filter mode must not read a live native gutter');};
  context.queueResize=()=>queued++;context.closeSelect=()=>{};
  context.Date={now:()=>0};
  bar.getBoundingClientRect=()=>{throw Error('Visible filter layout must never be probed');};
  vm.runInContext(['filterLayoutWidth','cancelFilterLayout','applyFilterLayout','layoutFilterControls'].map(actual).join('\n'),context);
  const flush=()=>{let count=0;while(raf.length){assert(count++<30,'Filter debounce is bounded');raf.shift()();}};
  state.destroyed=false;state.group='vehicles';state.payload.viewport={width:3840,height:2400};
  for(const scale of [1,2]){
    state.nativeScale=scale;state.wideFilters=undefined;state.filterLayoutWidth=null;panelWidth=900;render();
    context.layoutFilterControls();assert.strictEqual(state.wideFilters,false);
    for(const metric of ['off','xp_base','win_rate','battles']){
      scope.ordering.vehicles.metric=metric;render();
      for(let attempt=0;attempt<5;attempt++)context.layoutFilterControls();
      assert.strictEqual(state.wideFilters,false,'Metric/statistic visibility cannot alter the breakpoint');
      assert.strictEqual(bar.classList.contains('ss-filters-wide'),false);
      assert.strictEqual(controls['ss-sort-off'].style.display,'none');
    }
    panelWidth=903;context.layoutFilterControls();
    assert.strictEqual(state.wideFilters,false,'Promotion waits until resizing settles');
    assert.strictEqual(raf.length,1);
    for(let attempt=0;attempt<5;attempt++)context.layoutFilterControls();
    assert.strictEqual(raf.length,1,'Same-width measurements do not restart owned work');
    for(let frame=0;frame<6;frame++)raf.shift()();
    assert.strictEqual(state.wideFilters,false,'Six fast frames do not acknowledge the owned eight-frame promotion');
    assert.strictEqual(bar.getAttribute('data-filter-layout'),'wrapped');
    flush();assert.strictEqual(state.wideFilters,true);assert.strictEqual(bar.getAttribute('data-filter-layout'),'wide');
    panelWidth=800;context.layoutFilterControls();panelWidth=904;context.layoutFilterControls();
    const retained=raf.shift(),scheduler=context.window.requestAnimationFrame;
    context.window.requestAnimationFrame=undefined;retained();
    assert.strictEqual(state.wideFilters,true,'A retained promotion completes through the no-RAF fallback');
    assert.strictEqual(state.filterLayoutQueued,false,'Losing optional RAF releases promotion ownership');
    context.window.requestAnimationFrame=scheduler;
    panelWidth=800;context.layoutFilterControls();panelWidth=904;context.layoutFilterControls();flush();
    assert.strictEqual(state.wideFilters,true,'Restored RAF supports a fresh narrow-to-wide promotion');
    panelWidth=800;context.layoutFilterControls();panelWidth=904;context.layoutFilterControls();
    const shrinking=raf.shift();context.window.requestAnimationFrame=undefined;panelWidth=800;shrinking();
    assert.strictEqual(state.wideFilters,false,'Losing RAF cannot bypass the current narrow-width guard');
    assert.strictEqual(state.filterLayoutQueued,false);context.window.requestAnimationFrame=scheduler;
    panelWidth=904;context.layoutFilterControls();const resizing=raf.shift();state.resize={};
    context.window.requestAnimationFrame=undefined;resizing();
    assert.strictEqual(state.wideFilters,false,'Losing RAF cannot promote during an active resize');
    assert.strictEqual(state.filterLayoutQueued,false);context.window.requestAnimationFrame=scheduler;state.resize=null;
    context.layoutFilterControls();flush();
    const before=queued;for(let attempt=0;attempt<5;attempt++)context.layoutFilterControls();
    assert.strictEqual(queued,before,'A settled mode cannot recursively schedule layout');
    panelWidth=902;context.layoutFilterControls();assert.strictEqual(state.wideFilters,false,'Shrinking falls back immediately');
    panelWidth=904;context.layoutFilterControls();assert.strictEqual(raf.length,1);
    panelWidth=800;context.layoutFilterControls();flush();assert.strictEqual(state.wideFilters,false,'Stale promotion cannot undo a newer shrink');
    panelWidth=904;context.layoutFilterControls(true);assert.strictEqual(state.wideFilters,true,'Gesture release flushes the final mode');
    panelWidth=800;context.layoutFilterControls();panelWidth=904;context.layoutFilterControls();
    state.destroyed=true;context.cancelFilterLayout();flush();assert.strictEqual(state.wideFilters,false,'Destroyed views retire queued layout work');
    state.destroyed=false;
  }
}
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let remaining=10;function next(){if(--remaining)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);}));
async function retainedPromotion(browser,nativeHost,check){
  const page=await nativeHost(browser,{initialViewport:{width:1800,height:1400},viewport:{width:1800,height:1400,scale:1}}),errors=[];
  page.on('pageerror',error=>errors.push(error.stack||String(error)));
  try{
    const result=await page.evaluate(()=>new Promise((resolve,reject)=>{
      const realRAF=window.requestAnimationFrame,realNow=Date.now,frozen=Date.now();let pending=[];
      Date.now=()=>frozen;window.requestAnimationFrame=callback=>{pending.push(callback);return pending.length;};
      const bar=document.getElementById('ss-list-controls');
      function publish(width){const payload=JSON.parse(model.payload);payload.account_key='synthetic-retained-promotion';
        payload.window_size=[width,850];payload.appearance={window_settings:{background_transparency:0,maximized:false,restored_width:width,restored_height:850}};
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();}
      function drain(findPromotion){
        for(let count=0;pending.length&&count<100;count++){
          const callback=pending.shift();
          if(findPromotion&&String(callback).includes('state.filterLayoutFrames'))return callback;
          callback(performance.now());
        }
        return null;
      }
      publish(700);drain(false);publish(1200);const retained=drain(true);
      if(!retained){Date.now=realNow;window.requestAnimationFrame=realRAF;reject(Error('Actual filter promotion was not captured'));return;}
      const before=bar.getAttribute('data-filter-layout');window.requestAnimationFrame=undefined;
      realRAF.call(window,()=>retained(performance.now()));
      realRAF.call(window,()=>realRAF.call(window,()=>{
        try{
          const completed=bar.getAttribute('data-filter-layout');
          window.requestAnimationFrame=callback=>{pending.push(callback);return pending.length;};
          publish(700);drain(false);const narrow=bar.getAttribute('data-filter-layout');
          publish(1200);drain(false);
          resolve({before,completed,narrow,restored:bar.getAttribute('data-filter-layout'),width:bar.getAttribute('data-filter-width')});
        }catch(error){reject(error);}finally{Date.now=realNow;window.requestAnimationFrame=realRAF;}
      }));
    }));
    check('A retained filter promotion completes without an asynchronous error when optional RAF disappears: '+JSON.stringify({result,errors}),
      errors.length===0&&result.before==='wrapped'&&result.completed==='wide');
    check('Restored RAF can own a fresh narrow-to-wide filter transition',
      result.narrow==='wrapped'&&result.restored==='wide'&&result.width==='1162');
  }finally{await page.close();}
}
module.exports=async({browser,nativeHost,check})=>{
  assertFilterStateSource();check('Actual-source Off memory, readiness, context ownership and loading-state regressions pass',true);
  await retainedPromotion(browser,nativeHost,check);
  await require('./ui-filter-completeness.cjs')({browser,nativeHost,check});
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
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},scale);await frames(page);
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
      check('Disabled ordinary ordering explicitly dims its label, arrow and background'+caption,
        await page.locator('#ss-sort-chronology .ss-select-trigger').evaluate(node=>{
          const css=getComputedStyle(node),label=getComputedStyle(node.querySelector('.ss-control-label')),
            arrow=getComputedStyle(node.querySelector('.ss-select-arrow')),
            active=getComputedStyle(document.querySelector('#ss-sort-metric .ss-control-label'));
          return node.classList.contains('ss-select-disabled')&&node.getAttribute('aria-disabled')==='true'&&
            parseFloat(css.opacity)<0.9&&css.backgroundImage==='none'&&label.color!==active.color&&
            arrow.borderRightColor===label.color&&arrow.borderBottomColor===label.color;
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
      check('The wide result controls share one bounded row independently of the loading overlay'+caption,row.bounded&&row.row);
      await width(500);
      check('A narrow panel retains the original metric dropdown despite the wide game viewport'+caption,
        !await page.locator('#ss-sort-off').isVisible()&&!await page.locator('.ss-list-controls').evaluate(node=>node.classList.contains('ss-filters-wide')));
      const centeredRows=await page.locator('.ss-list-controls').evaluate((node,scale)=>{
        const box=node.getBoundingClientRect(),rows=[];
        for(const child of node.children){
          if(child.id==='ss-filter-loading')continue;
          const rect=child.getBoundingClientRect();if(!(rect.width>0&&rect.height>0))continue;
          let row=rows.find(row=>Math.abs(row.bottom-rect.bottom)<=scale);
          if(!row)rows.push(row={bottom:rect.bottom,left:rect.left,right:rect.right});
          else{row.left=Math.min(row.left,rect.left);row.right=Math.max(row.right,rect.right);}
        }
        return {wrapped:node.classList.contains('ss-filters-wrapped'),count:rows.length,
          offsets:rows.map(row=>Math.abs((row.left+row.right-box.left-box.right)/2)/scale)};
      },scale);
      check('Every wrapped filter row stays centered in the panel'+caption+': '+JSON.stringify(centeredRows),
        centeredRows.wrapped&&centeredRows.count>=2&&centeredRows.offsets.every(offset=>offset<=5));
      await page.locator('#ss-sort-metric .ss-select-trigger').click();
      check('The narrow metric menu still exposes Off'+caption,await page.locator('#ss-sort-metric [data-value="off"]').isVisible());
      await page.keyboard.press('Home');await page.keyboard.press('Enter');
      check('Narrow keyboard selection retains Off as the first option'+caption,await page.evaluate(()=>__grzCommands.filter(item=>item.action==='sort').pop().metric==='off'));
      await acknowledge();
      check('Narrow Off keeps a selectable dropdown and an explicit gray diagonal state'+caption,
        await page.locator('#ss-sort-metric .ss-select-trigger').evaluate(node=>{
          const option=node.parentNode.querySelector('[data-value="off"]'),css=getComputedStyle(node);
          return !node.disabled&&node.getAttribute('aria-disabled')==='false'&&node.classList.contains('ss-sort-off-choice')&&
            css.backgroundImage.includes('linear-gradient')&&option.classList.contains('ss-sort-off-choice')&&
            getComputedStyle(option).backgroundImage.includes('linear-gradient');
        }));
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
      check('A rebuilding range exposes the localized full-panel loading status'+caption,
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
      await page.locator('#ss-sort-metric .ss-select-trigger').click();await page.locator('#ss-sort-metric [data-value="credits_net_received"]').click();await frames(page);
      check('An unacknowledged native sort immediately owns the filter spinner'+caption,await page.locator('#ss-filter-loading').isVisible());
      await acknowledge();check('The matching native sort acknowledgement clears its spinner'+caption,!await page.locator('#ss-filter-loading').isVisible());
      await require('./ui-loading-overlay.cjs')({page,check,caption,scale,width,acknowledge,frames});
    }finally{await page.close();}
  }
};
module.exports.assertFilterStateSource=assertFilterStateSource;
module.exports.retainedPromotion=retainedPromotion;
if(require.main===module){assertFilterStateSource();console.log('Actual-source filter Off memory, projection readiness, account ownership and spinner regressions passed.');}
