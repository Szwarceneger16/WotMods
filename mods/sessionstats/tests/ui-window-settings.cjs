/* Native window preferences use optimistic UI and account-owned save replies. */
const fs=require('fs'),path=require('path');
const defaults={background_transparency:0,maximized:false,restored_width:700,restored_height:620};
const frames=page=>page.evaluate(()=>new Promise(resolve=>{
  let remaining=10;function next(){if(--remaining)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}));
const commands=page=>page.evaluate(()=>__grzCommands.filter(command=>command.action==='window_settings'));
async function publish(page,settings,ack,account) {
  await page.evaluate(({settings,ack,account})=>{
    const payload=JSON.parse(model.payload);payload.appearance=payload.appearance || {};
    payload.appearance.window_settings=settings;payload.window_size=[settings.restored_width,settings.restored_height];
    if(ack) payload.appearance.window_settings_result=ack;else delete payload.appearance.window_settings_result;
    if(account) payload.account_key=account;
    model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
  },{settings,ack,account});await frames(page);
}
async function paint(page) {
  return page.evaluate(()=>['#grz-session-stats','.ss-titlebar h1','.ss-group-title','.ss-metric-row .ss-metric-number'].map(selector=>{
    const css=getComputedStyle(document.querySelector(selector));
    return {color:css.color,opacity:css.opacity,fontSize:css.fontSize,textShadow:css.textShadow};
  }));
}
module.exports=async ({browser,nativeHost,check})=>{
  require('./ui-window-settings-source.cjs')();
  check('Actual-source account cleanup retires the previous window size before applying new preferences',true);
  const catalogs=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const page=await nativeHost(browser,{initialViewport:{width:1800,height:1200},viewport:{width:1800,height:1200,scale:1},realTimers:true,drag:'supported'});
  let server={...defaults};
  try {
    await publish(page,server,null,'synthetic-window-account');
    const slider=page.locator('#ss-background-transparency');
    for(const [language,messages] of Object.entries(catalogs)) {
      await page.evaluate(({language,messages})=>{
        const payload=JSON.parse(model.payload);payload.localization={language,messages};
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      },{language,messages});await frames(page);
      check('Window controls expose localized labels and slider range in '+language,
        await page.locator('#ss-maximize').getAttribute('aria-label')===messages['window.maximize'] &&
        await slider.getAttribute('aria-label')===messages['window.background_transparency'] &&
        await page.locator('#ss-background-transparency-label').textContent()===messages['window.background'] &&
        await slider.getAttribute('aria-valuemin')==='0' && await slider.getAttribute('aria-valuemax')==='100' &&
        await slider.getAttribute('aria-valuenow')==='0');
      await publish(page,{...server,maximized:true});
      check('Maximized windows expose the localized restore action in '+language,
        await page.locator('#ss-maximize').getAttribute('aria-label')===messages['window.restore'] &&
        await page.locator('#ss-maximize').getAttribute('aria-pressed')==='true');
      await publish(page,server);
    }
    await page.evaluate(()=>{const payload=JSON.parse(model.payload);payload.localization={language:'en',messages:{}};
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();});await frames(page);
    const beforePaint=await paint(page),track=await page.locator('#ss-background-transparency-track').boundingBox();
    await page.mouse.move(track.x+track.width/4,track.y+track.height/2);await page.mouse.down();
    await page.mouse.move(1790,1190);
    check('Dragging transparency beyond the panel clamps at100 without saving early',
      await slider.getAttribute('aria-valuenow')==='100' && (await commands(page)).length===0 &&
      await page.locator('#ss-window-background').evaluate(layer=>getComputedStyle(layer).opacity==='0') &&
      JSON.stringify(beforePaint)===JSON.stringify(await paint(page)));
    await page.mouse.up();await frames(page);
    let saved=await commands(page),first=saved[saved.length-1];
    const allowed=['action','account_key','request_id','background_transparency','maximized','restored_width','restored_height'];
    check('Slider release emits one flat account-owned settings command without dragging the window',
      saved.length===1 && first.background_transparency==='100' && first.account_key==='synthetic-window-account' &&
      /^[A-Za-z0-9_-]{1,64}$/.test(first.request_id) && Object.keys(first).every(key=>allowed.includes(key)) &&
      await page.evaluate(()=>__grzWindowEvents.length===0));
    server={...server,maximized:true,restored_width:910,restored_height:710};
    await publish(page,server,{request_id:'unmatched-external-window-change',saved:true});
    check('A pending background-only save preserves externally updated maximize and restored dimensions',
      await slider.getAttribute('aria-valuenow')==='100' && await page.locator('#ss-maximize').getAttribute('aria-pressed')==='true' &&
      await page.evaluate(()=>__nativeSize[0]===1780 && __nativeSize[1]===1180) && (await commands(page)).length===1);
    server={...server,background_transparency:100};await publish(page,server,{request_id:first.request_id,saved:true});
    server={...server,background_transparency:20};await publish(page,server);
    check('An external configuration refresh updates slider and background opacity',
      await slider.getAttribute('aria-valuenow')==='20' &&
      await page.locator('#ss-window-background').evaluate(layer=>getComputedStyle(layer).opacity==='0.8'));
    await slider.focus();
    const keyboard=await slider.evaluate(node=>[
      ['Home',0],['ArrowRight',5],['Shift+ArrowRight',15],['PageUp',25],['PageDown',15],
      ['ArrowLeft',10],['Shift+ArrowLeft',0],['End',100],['Home',0]
    ].map(([key,value])=>{
      const parts=key.split('+');
      node.dispatchEvent(new KeyboardEvent('keydown',{key:parts[parts.length-1],shiftKey:parts.length>1,bubbles:true,cancelable:true}));
      return {key,value,actual:node.getAttribute('aria-valuenow')};
    }));
    for(const {key,value,actual} of keyboard)check('Transparency keyboard '+key+' produces'+value,actual===String(value));
    check('Rapid keyboard changes remain unsaved until the debounce finishes',(await commands(page)).length===1);
    await page.waitForTimeout(240);saved=await commands(page);first=saved[saved.length-1];
    check('Keyboard debounce commits only its latest value',saved.length===2 && first.background_transparency==='0');
    await slider.press('End');await page.waitForTimeout(240);
    check('A second edit waits behind the outstanding save',(await commands(page)).length===2);
    await publish(page,server,{request_id:'unmatched-synthetic-request',saved:true});
    check('An unmatched acknowledgement cannot replace the latest optimistic edit',await slider.getAttribute('aria-valuenow')==='100' && (await commands(page)).length===2);
    server={...server,background_transparency:0};await publish(page,server,{request_id:first.request_id,saved:true});
    saved=await commands(page);const queued=saved[saved.length-1];
    check('The matching acknowledgement releases one queued latest edit',saved.length===3 && queued.background_transparency==='100' && queued.request_id!==first.request_id);
    server={...server,background_transparency:100};await publish(page,server,{request_id:queued.request_id,saved:true});
    await slider.press('Home');await page.waitForTimeout(240);saved=await commands(page);first=saved[saved.length-1];
    await publish(page,server,{request_id:first.request_id,saved:false});
    check('A failed save restores the authoritative setting and displays the save error',
      await slider.getAttribute('aria-valuenow')==='100' && await page.locator('#ss-status').textContent().then(text=>text.includes(catalogs.en['window.save_error'])));
    await slider.press('Home');await page.waitForTimeout(240);saved=await commands(page);const stale=saved[saved.length-1];
    server={...defaults,background_transparency:30};await publish(page,server,null,'another-synthetic-account');
    await publish(page,server,{request_id:stale.request_id,saved:true});
    check('Account changes retire outstanding settings acknowledgements',await slider.getAttribute('aria-valuenow')==='30');
    await page.locator('#ss-maximize').click();await frames(page);saved=await commands(page);const oldMaximize=saved[saved.length-1];
    server={background_transparency:45,maximized:false,restored_width:840,restored_height:680};
    await publish(page,server,null,'third-synthetic-account');
    await publish(page,server,{request_id:oldMaximize.request_id,saved:true});
    const accountWindow=await page.evaluate(()=>({nativeSize:__nativeSize.slice(),
      maximized:document.getElementById('ss-maximize').getAttribute('aria-pressed'),
      transparency:document.getElementById('ss-background-transparency').getAttribute('aria-valuenow'),
      width:document.getElementById('grz-session-stats').style.width,height:document.getElementById('grz-session-stats').style.height}));
    check('Changing accounts retires the previous maximized logical size and restores the new account dimensions: '+JSON.stringify(accountWindow),
      accountWindow.maximized==='false' && accountWindow.transparency==='45' &&
      accountWindow.nativeSize[0]===840 && accountWindow.nativeSize[1]===730);
  } finally {await page.close();}

  for(const scale of [1,2]) {
    const viewport={width:1800*scale,height:1200*scale,scale};
    const initiallyClamped={width:620,height:500,scale};
    const resized=await nativeHost(browser,{initialViewport:{width:620,height:500},viewport:initiallyClamped,realTimers:true});
    try {
      await publish(resized,defaults,null,'synthetic-maximize-account');
      check('An initially constrained regular window retains its saved preference at'+(scale*100)+'%',
        await resized.evaluate(()=>__nativeSize[0]===600 && __nativeSize[1]===480));
      await resized.locator('#ss-maximize').click();await frames(resized);
      let initialValues=await commands(resized),initialMaximize=initialValues[initialValues.length-1];
      check('Maximizing an initially constrained window saves the desired700x620 size at'+(scale*100)+'%',
        initialMaximize.maximized==='true' && initialMaximize.restored_width==='700' && initialMaximize.restored_height==='620');
      await publish(resized,{...defaults,maximized:true},{request_id:initialMaximize.request_id,saved:true});
      await resized.locator('#ss-maximize').click();await frames(resized);
      initialValues=await commands(resized);const initialRestore=initialValues[initialValues.length-1];
      const initialRestoredSize=await resized.evaluate(()=>__nativeSize.slice());
      const initialRestoreCorrect=initialRestore.maximized==='false' &&
        (initialRestore.restored_width===undefined || initialRestore.restored_width==='700') &&
        (initialRestore.restored_height===undefined || initialRestore.restored_height==='620') &&
        initialRestoredSize[0]===600 && initialRestoredSize[1]===480;
      check('Restoring an initially constrained window preserves the desired dimensions at'+(scale*100)+'%'+
        (initialRestoreCorrect ? '' : ': '+JSON.stringify({command:initialRestore,nativeSize:initialRestoredSize,scale})),initialRestoreCorrect);
      await publish(resized,defaults,{request_id:initialRestore.request_id,saved:true});
      await resized.setViewportSize({width:viewport.width,height:viewport.height});
      await resized.evaluate(viewport=>{const payload=JSON.parse(model.payload);payload.viewport=viewport;
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},viewport);await frames(resized);
      check('Growing the viewport preserves the700x620 preference while displaying the730px minimum at'+(scale*100)+'%',
        await resized.evaluate(scale=>__nativeSize[0]===700*scale && __nativeSize[1]===730*scale,scale));
      await resized.locator('#ss-group-battles').click();
      const ids=await resized.locator('.ss-group').evaluateAll(cards=>cards.slice(0,2).map(card=>card.dataset.groupId));
      for(const id of ids) await resized.locator('[data-group-id="'+id+'"] .ss-more-button').click();
      await frames(resized);
      await resized.locator('#ss-maximize').click();await frames(resized);
      let values=await commands(resized),maximize=values[values.length-1];
      const maximum=await resized.evaluate(()=>__nativeSize);
      check('Maximize fits the physical viewport and keeps two opened panels at'+(scale*100)+'%',
        await resized.locator('#ss-maximize').getAttribute('aria-pressed')==='true' &&
        maximum[0]===viewport.width-20 && maximum[1]===viewport.height-20 &&
        maximize.maximized==='true' && maximize.restored_width==='700' && maximize.restored_height==='620' &&
        await resized.locator('.ss-more-button[aria-expanded="true"]').count()===2);
      await publish(resized,{...defaults,maximized:true},{request_id:maximize.request_id,saved:true});
      const smaller={width:600*scale+20,height:480*scale+20};await resized.setViewportSize(smaller);
      await resized.evaluate(viewport=>{const payload=JSON.parse(model.payload);payload.viewport={...viewport,scale:parseFloat(document.documentElement.style.fontSize)};
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},smaller);await frames(resized);
      await resized.locator('#ss-maximize').click();await frames(resized);
      values=await commands(resized);const restore=values[values.length-1],clamped=await resized.evaluate(()=>__nativeSize);
      check('Restore clamps to a smaller viewport while preserving the desired regular size at'+(scale*100)+'%',
        await resized.locator('#ss-maximize').getAttribute('aria-pressed')==='false' &&
        clamped[0]===600*scale && clamped[1]===480*scale && restore.maximized==='false' &&
        await resized.locator('.ss-more-button[aria-expanded="true"]').count()===2);
      await publish(resized,defaults,{request_id:restore.request_id,saved:true});
      await resized.setViewportSize({width:viewport.width,height:viewport.height});
      await resized.evaluate(viewport=>{const payload=JSON.parse(model.payload);payload.viewport=viewport;
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},viewport);await frames(resized);
      check('A larger viewport restores the saved width and minimum display height at'+(scale*100)+'%',
        await resized.evaluate(scale=>__nativeSize[0]===700*scale && __nativeSize[1]===730*scale,scale));
      const beforeResize=(await commands(resized)).length,grip=await resized.locator('#ss-resize-grip').boundingBox();
      await resized.mouse.move(grip.x+grip.width/2,grip.y+grip.height/2);await resized.mouse.down();
      await resized.mouse.move(grip.x+grip.width/2+20*scale,grip.y+grip.height/2+12*scale);
      await resized.mouse.move(grip.x+grip.width/2+40*scale,grip.y+grip.height/2+24*scale);
      check('Regular resizing does not save intermediate pointer samples at'+(scale*100)+'%',(await commands(resized)).length===beforeResize);
      await resized.mouse.up();await frames(resized);values=await commands(resized);const resizeSave=values[values.length-1];
      check('Regular resize release saves one final logical size at'+(scale*100)+'%',
        values.length===beforeResize+1 && resizeSave.maximized==='false' && resizeSave.restored_width==='740' && resizeSave.restored_height==='754');
      await publish(resized,{...defaults,restored_width:740,restored_height:754},{request_id:resizeSave.request_id,saved:true});
      const beforeKeyboard=(await commands(resized)).length;
      await resized.locator('#ss-resize-grip').focus();await resized.locator('#ss-resize-grip').press('ArrowRight');await frames(resized);
      values=await commands(resized);const keyboardSave=values[values.length-1];
      check('One keyboard resize persists one logical size change at'+(scale*100)+'%',
        values.length===beforeKeyboard+1 && keyboardSave.restored_width==='764' && keyboardSave.restored_height==='754' && keyboardSave.maximized==='false');
      await publish(resized,{...defaults,restored_width:764,restored_height:754},{request_id:keyboardSave.request_id,saved:true});
    } finally {await resized.close();}
  }

  const guarded=await nativeHost(browser,{initialViewport:{width:1600,height:1100},viewport:{width:1600,height:1100,scale:1},realTimers:true});
  try {
    await publish(guarded,defaults,null,'synthetic-timer-account');
    await guarded.evaluate(()=>{
      window.__heldWindowTimers=[];window.__failedWindowTimerClears=0;
      const schedule=window.setTimeout.bind(window),cancel=window.clearTimeout.bind(window);
      window.setTimeout=function(callback,delay,...args) {
        if(delay!==200) return schedule(callback,delay,...args);
        const entry={id:1000000000+__heldWindowTimers.length,callback:()=>callback.apply(window,args)};
        __heldWindowTimers.push(entry);return entry.id;
      };
      window.clearTimeout=function(id) {
        if(__heldWindowTimers.some(entry=>entry.id===id)) {__failedWindowTimerClears++;throw Error('Synthetic window timer cancellation failure');}
        return cancel(id);
      };
    });
    await guarded.locator('#ss-background-transparency').focus();await guarded.locator('#ss-background-transparency').press('End');
    check('Timer retirement regression starts with an unsaved keyboard edit',await guarded.evaluate(()=>__heldWindowTimers.length===1) && (await commands(guarded)).length===0);
    await publish(guarded,{...defaults,background_transparency:37},null,'another-synthetic-timer-account');
    await guarded.evaluate(()=>__heldWindowTimers[0].callback());
    check('Account reset retires a retained debounce callback even when clearTimeout fails',
      await guarded.locator('#ss-background-transparency').getAttribute('aria-valuenow')==='37' && (await commands(guarded)).length===0);
    await guarded.locator('#ss-background-transparency').focus();await guarded.locator('#ss-background-transparency').press('Home');
    await guarded.evaluate(()=>{__heldWindowTimers[0].callback();GRZSessionStats.destroy();__heldWindowTimers.forEach(entry=>entry.callback());});
    check('Cleanup retires both old and current debounce callbacks despite cancellation failure',
      await guarded.evaluate(()=>__heldWindowTimers.length===2 && __failedWindowTimerClears>=2) && (await commands(guarded)).length===0);
  } finally {await guarded.close();}
};
