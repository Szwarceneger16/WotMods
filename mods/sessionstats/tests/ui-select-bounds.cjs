/* Keep Gameface's menu choices reachable inside the window and the pinned list. */
const settle=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));

async function loadWindow(page, {width,height,empty=false,timeline=false}) {
  await page.evaluate(({width,height,empty,timeline})=>{
    const data=JSON.parse(model.payload), scope=data.scopes.launch;
    data.window_size=[width,height];
    data.appearance={...data.appearance,window_settings:{maximized:false,restored_width:width,restored_height:height}};
    scope.ordering.vehicles={metric:'xp_received',statistic:'avg',direction:'desc',chronology:'newest'};
    if(empty) {
      scope.vehicles=[];
      scope.summary={battles:0,observed_battles:0};
      scope.pagination.vehicles={page:0,pages:1,total:0,page_size:40};
    }
    if(timeline) {
      data.scopes.timeline={...scope,from_point:'',to_point:'',time_points:
        Array.from({length:18},(_,index)=>['point-'+index,Math.floor(Date.now()/1000)-200+index])};
    }
    model.payload=JSON.stringify(data);
    GRZSessionStats.update(data);
  },{width,height,empty,timeline});
  await settle(page);
}

async function menuState(page,id,inScroll) {
  return page.evaluate(({id,inScroll})=>{
    const list=document.getElementById(id), scroll=document.getElementById('ss-scroll');
    const clip=(inScroll?scroll:document.getElementById('grz-session-stats')).getBoundingClientRect();
    const bounds=list.getBoundingClientRect();
    const options=Array.from(list.querySelectorAll('[role="option"]')).filter(option=>getComputedStyle(option).display!=='none');
    function visible(option) {
      const rect=option.getBoundingClientRect();
      const hit=document.elementFromPoint((rect.left+rect.right)/2,(rect.top+rect.bottom)/2);
      return rect.top>=bounds.top-1&&rect.bottom<=bounds.bottom+1&&option.contains(hit);
    }
    return {
      inBounds:bounds.height>0&&bounds.top>=clip.top-1&&bounds.bottom<=clip.bottom+1&&
        bounds.left>=clip.left-1&&bounds.right<=clip.right+1,
      full:options.length>0&&options.every(visible),
      focus:options.includes(document.activeElement)&&visible(document.activeElement),
      focusedValue:document.activeElement.getAttribute('data-value'),
      outer:scroll.scrollTop, inner:list.scrollTop
    };
  },{id,inScroll});
}

module.exports=async ({browser,nativeHost,check})=>{
  const sizes=[
    {width:625,height:900,scale:1,empty:true},
    {width:365,height:730,scale:2,empty:false}
  ];
  for(const {width,height,scale,empty} of sizes){
    const viewport={width:width*scale+20,height:height*scale+20,scale};
    const page=await nativeHost(browser,{viewport,initialViewport:viewport,realTimers:true});
    try{
      await loadWindow(page,{width,height,empty});
      const trigger=page.locator('#ss-sort-metric .ss-select-trigger');
      if(!empty) {
        await page.locator('#ss-scroll').evaluate(scroll=>{scroll.scrollTop=scroll.scrollHeight;});
        await settle(page);
        check('Compact result filter is pinned before opening its options',
          await page.locator('#ss-filter-panel').evaluate(panel=>panel.classList.contains('is-pinned')));
      }
      await trigger.click();
      const opened=await menuState(page,'ss-options-metric',true);
      check('The metric list is fully clickable inside the '+width+' × '+height+' result viewport',opened.inBounds&&opened.full);
      await page.keyboard.press('End');
      const end=await menuState(page,'ss-options-metric',true);
      check('End focuses the displayed last choice without moving the result list',end.focus&&end.focusedValue==='battles'&&end.outer===opened.outer);
      await page.evaluate(()=>__grzEvents['viewEnv.onDataChanged']());
      await settle(page);
      const refreshed=await menuState(page,'ss-options-metric',true);
      check('Refreshing the results keeps the sort menu and focused choice open',
        refreshed.focus&&refreshed.focusedValue===end.focusedValue&&refreshed.outer===end.outer&&
        await trigger.getAttribute('aria-expanded')==='true');
      if(!empty) {
        const bounds=await page.locator('#ss-options-metric').boundingBox();
        await page.mouse.move(bounds.x+bounds.width/2,bounds.y+bounds.height/2);
        await page.mouse.wheel(0,120);
        await settle(page);
        check('Wheel input over a pinned dropdown does not move its surrounding results',
          (await menuState(page,'ss-options-metric',true)).outer===opened.outer);
      }
      await page.keyboard.press('Escape');
      check('Escape restores focus to the unchanged result trigger',
        await trigger.evaluate(node=>document.activeElement===node&&node.getAttribute('aria-expanded')==='false'));
    }finally{await page.close();}
  }
  const page=await nativeHost(browser,{realTimers:true});
  try {
    await loadWindow(page,{width:625,height:730,timeline:true});
    await page.locator('#ss-scope-manual').click();
    await page.locator('#ss-timeline-from .ss-select-trigger').click();
    await page.keyboard.press('End');
    const end=await menuState(page,'ss-options-timeline-from',false);
    check('End scrolls a long date menu to the last visible option',end.inBounds&&end.focus&&end.focusedValue==='__custom__'&&end.inner>0);
    const box=await page.locator('#ss-options-timeline-from').boundingBox();
    await page.mouse.move(box.x+box.width/2,box.y+box.height/2);
    await page.mouse.wheel(0,120);
    await settle(page);
    const wheeled=await menuState(page,'ss-options-timeline-from',false);
    check('Native wheel input over a bounded menu scrolls just its options',wheeled.inner<end.inner&&wheeled.outer===end.outer);
    await page.keyboard.press('Home');
    const start=await menuState(page,'ss-options-timeline-from',false);
    check('Home makes the first time-range option visible again',start.focus&&start.focusedValue===''&&start.outer===end.outer);
    await page.keyboard.press('Escape');
    await page.locator('#ss-sort-metric .ss-select-trigger').click();
    await page.evaluate(()=>{
      const data=JSON.parse(model.payload);
      data.scopes.timeline.time_points.push(['peer-time-point',Math.floor(Date.now()/1000)-60]);
      model.payload=JSON.stringify(data);__grzEvents['viewEnv.onDataChanged']();
    });
    await settle(page);
    check('A time point arriving from another client keeps timeline sort choices open',
      (await menuState(page,'ss-options-metric',true)).focus);
  }finally{await page.close();}
};
