/* Resize ownership: filter mode must depend on available width, not trial DOM
   paint, active metrics, the previous layout or a delayed native rectangle. */
const frames=(page,count=12)=>page.evaluate(count=>new Promise(resolve=>{
  function next(){if(--count)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}),count);
const state=page=>page.evaluate(()=>{
  const bar=document.getElementById('ss-list-controls'),toggle=document.getElementById('ss-sort-off');
  return {mode:bar.getAttribute('data-filter-layout'),width:Number(bar.getAttribute('data-filter-width')),
    wide:bar.classList.contains('ss-filters-wide'),wrapped:bar.classList.contains('ss-filters-wrapped'),
    toggle:getComputedStyle(toggle).display!=='none',scroll:document.getElementById('ss-scroll').scrollTop};
});
async function settled(page,mode){
  await page.waitForFunction(mode=>document.getElementById('ss-list-controls').getAttribute('data-filter-layout')===mode,mode,{timeout:1500});
  await frames(page);
  return state(page);
}
async function resize(page,width){
  await page.evaluate(width=>__filterStableResize([width]),width);
}
module.exports=async({browser,nativeHost,check})=>{
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:3840,height:2400},
      viewport:{width:3840,height:2400,scale},realTimers:true});
    const label=' at '+scale+'x';
    try{
      await page.evaluate(scale=>{
        const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
        payload.account_key='synthetic-filter-stability-'+scale;payload.window_size=[1100,850];
        payload.viewport={width:3840,height:2400,scale};payload.localization={language:'en',messages:{}};
        payload.appearance=payload.appearance||{};payload.appearance.window_settings={
          background_transparency:0,maximized:false,restored_width:1100,restored_height:850};
        scope.period_id='synthetic-stable-period';scope.loading=false;scope.load_error='';
        scope.ordering=scope.ordering||{};scope.pagination=scope.pagination||{};
        for(const group of ['vehicles','maps','tiers','battles']){
          const sample=scope[group][0];scope[group]=Array.from({length:40},(_,index)=>{
            const row=JSON.parse(JSON.stringify(sample));row.id='stable-'+group+'-'+index;return row;
          });
          scope.ordering[group]={metric:'off',statistic:'avg',direction:'desc',chronology:'newest'};
          scope.pagination[group]={page:0,pages:1,page_size:40,total:40};
        }
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
        window.__filterStableResize=function(widths){
          const grip=document.getElementById('ss-resize-grip'),box=grip.getBoundingClientRect();
          grip.dispatchEvent(new MouseEvent('mousedown',{button:0,clientX:box.left+1,clientY:box.top+1,bubbles:true,cancelable:true}));
          const request=__grzCommands.filter(command=>command.action==='resize_begin').pop();
          if(!request)throw Error('Expected a real native resize gesture');
          for(const width of widths)GRZSessionStats.update({resize_gesture:{token:request.token,width,height:850,active:true}});
          GRZSessionStats.update({resize_gesture:{token:request.token,width:widths[widths.length-1],height:850,active:false}});
        };
        const bar=document.getElementById('ss-list-controls');
        window.__filterStableTrace={classes:[],modes:[]};
        window.__filterStableObserver=new MutationObserver(records=>{
          const classes=records.filter(record=>record.attributeName==='class');
          classes.forEach((record,index)=>{
            const after=index+1<classes.length?classes[index+1].oldValue:bar.className;
            if(record.oldValue!==after)__filterStableTrace.classes.push({before:record.oldValue,after});
          });
          const modes=records.filter(record=>record.attributeName==='data-filter-layout');
          modes.forEach((record,index)=>{
            const after=index+1<modes.length?modes[index+1].oldValue:bar.getAttribute('data-filter-layout');
            if(record.oldValue!==after)__filterStableTrace.modes.push({before:record.oldValue,after});
          });
        });
        __filterStableObserver.observe(bar,{attributes:true,attributeOldValue:true,attributeFilter:['class','data-filter-layout']});
      },scale);
      let geometry=await settled(page,'wide');
      check('A comfortably fitting filter row reaches one coherent wide layout'+label,
        geometry.wide&&!geometry.wrapped&&geometry.toggle&&geometry.width>900);
      await resize(page,920);geometry=await settled(page,'wrapped');
      check('A smaller panel falls back promptly without retaining the toggle'+label,
        geometry.wrapped&&!geometry.wide&&!geometry.toggle);

      // A fixed near-boundary width must not change mode when Statistic hides,
      // groups change, or repeated resize events cause another layout pass.
      for(const width of [920,960]){
        await resize(page,width);const expected=width===920?'wrapped':'wide';await settled(page,expected);
        await page.evaluate(()=>{__filterStableTrace.classes=[];__filterStableTrace.modes=[];});
        for(const group of ['vehicles','maps','tiers','battles'])for(const metric of group==='battles'?['off','xp_received']:['off','xp_received','win_rate']){
          await page.evaluate(({group,metric})=>{
            const payload=JSON.parse(model.payload);payload.scopes.launch.ordering[group]={metric,statistic:'avg',direction:'desc',chronology:'newest'};
            model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
            document.getElementById('ss-group-'+group).onclick();
            for(let n=0;n<4;n++)window.dispatchEvent(new Event('resize'));
          },{group,metric});
          geometry=await settled(page,expected);
          check('Fixed-width mode ignores metric/group history: '+width+'px '+group+'/'+metric+label,
            geometry.mode===expected&&geometry.toggle===(expected==='wide')&&geometry.wide!==geometry.wrapped);
        }
        const trace=await page.evaluate(()=>__filterStableTrace);
        check('Repeated fixed-width renders never trial-switch visible filter classes'+label+' at '+width+'px: '+JSON.stringify(trace),
          trace.classes.length===0&&trace.modes.length===0);
      }

      await page.locator('#ss-group-vehicles').click();await resize(page,920);await settled(page,'wrapped');
      await page.evaluate(()=>{
        const scroll=document.getElementById('ss-scroll');scroll.scrollTop=300;
        window.__filterStableCards=Array.from(document.querySelectorAll('#ss-groups .ss-group'));
        __filterStableTrace.classes=[];__filterStableTrace.modes=[];
      });await frames(page);
      await page.evaluate(()=>__filterStableResize([960,920,960,920,960,920]));await settled(page,'wrapped');
      const retained=await page.evaluate(()=>({
        sameCards:__filterStableCards.length===document.querySelectorAll('#ss-groups .ss-group').length&&
          __filterStableCards.every(node=>node.isConnected&&document.getElementById(node.id)===node),
        scroll:document.getElementById('ss-scroll').scrollTop,trace:__filterStableTrace,
      }));
      check('A rapid boundary resize preserves card identity and the existing pixel intent'+label+': '+JSON.stringify(retained),
        retained.sameCards&&Math.abs(retained.scroll-300)<=2);
      check('A narrow-ending resize burst never promotes a trial wide row'+label,
        retained.trace.modes.every(change=>change.after!=='wide')&&
        retained.trace.classes.every(change=>!/(^|\s)ss-filters-wide(\s|$)/.test(change.after)));

      await page.evaluate(()=>__filterStableObserver.disconnect());
    }finally{await page.close();}

    // Use external saved-size acknowledgements without a held resize gesture:
    // promotion must settle by itself and cleanup must retire its pending RAF.
    const deferred=await nativeHost(browser,{initialViewport:{width:3840,height:2400},
      viewport:{width:3840,height:2400,scale},realTimers:true});
    try{
      await settled(deferred,'wrapped');
      await deferred.evaluate(()=>{
        const bar=document.getElementById('ss-list-controls');window.__deferredFilterModes=[];
        window.__deferredFilterObserver=new MutationObserver(records=>{
          for(const record of records)if(record.attributeName==='data-filter-layout')
            __deferredFilterModes.push({before:record.oldValue,after:bar.getAttribute('data-filter-layout')});
        });
        __deferredFilterObserver.observe(bar,{attributes:true,attributeOldValue:true,attributeFilter:['data-filter-layout']});
        window.__externalFilterWidth=function(width){
          const payload=JSON.parse(model.payload);payload.appearance=payload.appearance||{};
          payload.appearance.window_settings={background_transparency:0,maximized:false,restored_width:width,restored_height:850};
          payload.window_size=[width,850];model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
        };
        __externalFilterWidth(1100);
      });
      geometry=await settled(deferred,'wide');
      const promoted=await deferred.evaluate(()=>__deferredFilterModes);
      check('An ordinary upward resize settles once without seconds of retrying'+label+': '+JSON.stringify(promoted),
        geometry.wide&&promoted.length===1&&promoted[0].before==='wrapped'&&promoted[0].after==='wide');
      await deferred.evaluate(()=>__externalFilterWidth(920));await settled(deferred,'wrapped');
      const pending=await deferred.evaluate(async scale=>{
        __externalFilterWidth(1100);
        await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
        const bar=document.getElementById('ss-list-controls');
        const before={mode:bar.getAttribute('data-filter-layout'),nativeWidth:__nativeSize[0]};
        GRZSessionStats.destroy();__deferredFilterModes=[];return before;
      },scale);
      check('The native surface can resize while its wide-filter promotion remains debounced'+label+': '+JSON.stringify(pending),
        pending.mode==='wrapped'&&pending.nativeWidth===1100*scale);
      await frames(deferred,20);
      const retired=await deferred.evaluate(()=>({bound:GRZSessionStats.getState().nativeBound,modes:__deferredFilterModes,
        mode:document.getElementById('ss-list-controls').getAttribute('data-filter-layout')}));
      check('Cleanup retires queued filter promotion before it can mutate the previous view'+label+': '+JSON.stringify(retired),
        !retired.bound&&retired.mode==='wrapped'&&retired.modes.length===0);
      await deferred.evaluate(()=>__deferredFilterObserver.disconnect());
    }finally{await deferred.close();}
  }
};
