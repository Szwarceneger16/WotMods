/* Navigation owns its scroll intent even while Gameface returns stale offsets. */
module.exports=async({browser,nativeHost,check})=>{
  const page=await nativeHost(browser,{
    initialViewport:{width:1800,height:1100},viewport:{width:1800,height:1100,scale:1},
  });
  const frames=()=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))));
  const top=()=>page.locator('#ss-scroll').evaluate(node=>node.scrollTop);
  const position=async value=>{
    await page.locator('#ss-scroll').evaluate((node,value)=>{node.scrollTop=value;},value);
    await frames();
    return top();
  };
  const summaryAtTop=()=>page.evaluate(()=>{
    const scroll=document.getElementById('ss-scroll'),main=document.querySelector('#ss-summary .ss-summary-main');
    const viewport=scroll.getBoundingClientRect(),box=main.getBoundingClientRect();
    return Math.abs(scroll.scrollTop)<=1 && box.top>=viewport.top-1 && box.top<viewport.bottom;
  });
  const render=()=>page.evaluate(()=>GRZSessionStats.update(model.payload));
  try {
    await page.evaluate(()=>{
      const payload=JSON.parse(model.payload);
      payload.account_key='synthetic-scroll-account';
      payload.window_size=[900,620];
      payload.scopes.timeline=JSON.parse(JSON.stringify(payload.scopes.manual));
      payload.scopes.timeline.from_point=payload.scopes.timeline.to_point='';
      payload.scopes.timeline.time_points=[['synthetic-point',100]];
      payload.scopes.instance=JSON.parse(JSON.stringify(payload.scopes.manual));
      for(const [name,scope] of Object.entries(payload.scopes)) {
        scope.period_id='synthetic-scroll-'+name;
        scope.loading=false;scope.load_error='';
        scope.pagination=scope.pagination||{};
        for(const group of ['vehicles','maps','tiers','battles']) {
          const sample=scope[group][0];
          scope[group]=Array.from({length:40},(_,index)=>{
            const row=JSON.parse(JSON.stringify(sample));
            row.id='synthetic-'+group+'-'+index;
            row.name='Synthetic '+group+' '+index;
            if(group==='battles') row.details={pass_points:{credited:3,battle:3},missions:{},bonuses:{}};
            return row;
          });
          scope.pagination[group]={page:0,page_size:40,total:80,pages:2};
        }
      }
      model.payload=JSON.stringify(payload);GRZSessionStats.update(model.payload);
      window.__scrollResetFocuses=0;
      document.getElementById('ss-reset').focus=()=>{__scrollResetFocuses++;};
    });
    await frames();
    check('Synthetic scroll fixture starts with its complete summary visible',await summaryAtTop());
    check('Synthetic history has room to exercise retained scroll offsets',await position(550)>500);

    await page.evaluate(()=>{
      const scroll=document.getElementById('ss-scroll');
      let prototype=scroll,descriptor;
      while(prototype && !descriptor) {descriptor=Object.getOwnPropertyDescriptor(prototype,'scrollTop');prototype=Object.getPrototypeOf(prototype);}
      // Model a native getter which still exposes the previous layout's offset
      // after assigning zero. Writes retain their real browser effect.
      Object.defineProperty(scroll,'scrollTop',{configurable:true,get:()=>550,
        set(value){descriptor.set.call(this,value);}});
      document.getElementById('ss-scope-manual').onclick();
      delete scroll.scrollTop;
    });
    await frames();
    check('Switching to Timeline ignores a stale native scroll getter and shows the summary',await summaryAtTop());
    check('Changing scope does not focus a reset control when no dialog was open',
      await page.evaluate(()=>__scrollResetFocuses===0));

    await position(500);
    await page.evaluate(()=>{
      document.getElementById('ss-scope-launch').onclick();
      // Model focus/scroll anchoring applied after the synchronous render.
      document.getElementById('ss-scroll').scrollTop=130;
    });
    await frames();
    check('Scope navigation reapplies its top intent after deferred layout or focus movement',await summaryAtTop());
    await position(500);
    await page.evaluate(()=>{document.getElementById('ss-group-maps').onclick();document.getElementById('ss-scroll').scrollTop=130;});
    await frames();
    check('Changing result grouping also returns to the complete summary after layout',await summaryAtTop());

    const retained=await position(450);
    await render();await frames();
    check('An ordinary data refresh preserves the current result position',Math.abs(await top()-retained)<=1);
    await page.evaluate(()=>{
      GRZSessionStats.update(model.payload);
      const scroll=document.getElementById('ss-scroll');
      let prototype=scroll,descriptor;
      while(prototype && !descriptor) {descriptor=Object.getOwnPropertyDescriptor(prototype,'scrollTop');prototype=Object.getPrototypeOf(prototype);}
      Object.defineProperty(scroll,'scrollTop',{configurable:true,get:()=>0,set(value){descriptor.set.call(this,value);}});
      GRZSessionStats.update(model.payload);
      delete scroll.scrollTop;
    });
    await frames();
    check('Repeated data updates preserve their pending position while native offsets are stale',Math.abs(await top()-retained)<=1);

    const sortedAt=await position(150);
    await page.evaluate(()=>{
      document.querySelector('#ss-sort-metric [data-value="xp_base"]').onclick();
      const command=__grzCommands.filter(item=>item.action==='sort').pop();
      const payload=JSON.parse(model.payload),scope=payload.scopes[command.scope];
      scope.ordering[command.group]={metric:command.metric,statistic:command.statistic,direction:command.direction,chronology:command.chronology};
      model.payload=JSON.stringify(payload);GRZSessionStats.update(model.payload);
    });
    await frames();
    check('Sorting the current page preserves the result position instead of jumping to the summary',Math.abs(await top()-sortedAt)<=1);

    await page.evaluate(()=>document.getElementById('ss-group-battles').onclick());await frames();
    const moreAt=await page.evaluate(()=>{
      const scroll=document.getElementById('ss-scroll'),card=document.querySelector('#ss-groups .ss-group');
      scroll.scrollTop+=card.getBoundingClientRect().top-scroll.getBoundingClientRect().top-20;
      return scroll.scrollTop;
    });
    await page.evaluate(()=>document.querySelector('#ss-groups .ss-more-button').onclick());await frames();
    check('Opening battle details preserves the visible battle position',Math.abs(await top()-moreAt)<=1);

    await position(400);
    await page.evaluate(()=>{
      const payload=JSON.parse(model.payload);payload.account_key='synthetic-other-account';
      model.payload=JSON.stringify(payload);GRZSessionStats.update(model.payload);
    });
    await frames();
    check('Changing accounts starts at the summary rather than inheriting another account offset',await summaryAtTop());
    await position(400);
    await page.evaluate(()=>document.getElementById('ss-scope-manual').onclick());await frames();
    await position(400);
    await page.evaluate(()=>{
      const payload=JSON.parse(model.payload);
      payload.scopes.timeline.from_point='synthetic-point';
      payload.scopes.timeline.period_id='synthetic-filtered-period';
      model.payload=JSON.stringify(payload);GRZSessionStats.update(model.payload);
    });
    await frames();
    check('A newly selected timeline period starts at the summary',await summaryAtTop());

    const wheelAt=await page.evaluate(()=>{
      document.getElementById('ss-group-vehicles').onclick();
      const scroll=document.getElementById('ss-scroll');
      let prototype=scroll,descriptor;
      while(prototype && !descriptor) {descriptor=Object.getOwnPropertyDescriptor(prototype,'scrollTop');prototype=Object.getPrototypeOf(prototype);}
      Object.defineProperty(scroll,'scrollTop',{configurable:true,get:()=>550,set(value){descriptor.set.call(this,value);}});
      scroll.dispatchEvent(new WheelEvent('wheel',{deltaY:-1,bubbles:true,cancelable:true}));
      delete scroll.scrollTop;
      return scroll.clientHeight/4;
    });
    await frames();
    check('A native wheel after navigation starts from the logical top instead of a stale offset',Math.abs(await top()-wheelAt)<=1);

    await page.evaluate(()=>{
      document.getElementById('ss-group-vehicles').onclick();
      const scroll=document.getElementById('ss-scroll');
      scroll.dispatchEvent(new MouseEvent('mousedown',{bubbles:true}));
      scroll.scrollTop=120;
    });
    await frames();
    check('A newer user scrollbar movement cancels an older queued navigation correction',Math.abs(await top()-120)<=1);
    await page.evaluate(()=>{
      document.getElementById('ss-group-maps').onclick();
      GRZSessionStats.destroy();
      document.getElementById('ss-scroll').scrollTop=120;
    });
    await frames();
    check('A retained layout callback cannot reset scrolling after teardown',Math.abs(await top()-120)<=1);
  } finally {await page.close();}
};
