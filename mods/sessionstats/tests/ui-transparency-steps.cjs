/* Five-percent input ticks retain legacy config values until the user acts. */
const frames=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
module.exports=async({browser,nativeHost,check})=>{
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:3840,height:2400},viewport:{width:3840,height:2400,scale},realTimers:true});
    let sequence=0;
    const reset=async()=>{
      const account='synthetic-slider-five-'+scale+'-'+(++sequence);
      await page.evaluate(account=>{
        const payload=JSON.parse(model.payload);payload.account_key=account;
        payload.appearance=payload.appearance||{};payload.appearance.window_settings={
          background_transparency:17,maximized:false,restored_width:700,restored_height:730};
        __grzCommands.length=0;model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      },account);await frames(page);
      return account;
    };
    const slider=page.locator('#ss-background-transparency');
    const saved=()=>page.evaluate(()=>__grzCommands.filter(command=>command.action==='window_settings'));
    try{
      await reset();
      check('Legacy17% remains readable without rewriting settings at '+scale+'x',
        await slider.getAttribute('aria-valuenow')==='17'&&(await saved()).length===0);
      for(const [key,value] of [['ArrowRight',20],['ArrowLeft',15],['ArrowUp',20],['ArrowDown',15],
        ['Shift+ArrowRight',25],['Shift+ArrowLeft',10],['PageUp',25],['PageDown',10],['Home',0],['End',100]]){
        const account=await reset();await slider.focus();await slider.press(key);
        check('Legacy17% keyboard '+key+' lands on '+value+'% at '+scale+'x',await slider.getAttribute('aria-valuenow')===String(value));
        await page.waitForFunction(()=>__grzCommands.some(command=>command.action==='window_settings'));
        const commands=await saved();
        check('Keyboard saves one snapped account-owned value for '+key+' at '+scale+'x',
          commands.length===1&&commands[0].background_transparency===String(value)&&commands[0].account_key===account&&value%5===0);
      }
      for(const [percent,value] of [[0,0],[2,0],[3,5],[17,15],[48,50],[52,50],[53,55],[98,100],[100,100]]){
        const account=await reset(),box=await page.locator('#ss-background-transparency-track').boundingBox();
        await page.mouse.move(box.x+box.width*percent/100,box.y+box.height/2);await page.mouse.down();
        check('Pointer'+percent+'% previews the nearest five-percent tick at '+scale+'x',
          await slider.getAttribute('aria-valuenow')===String(value)&&(await saved()).length===0);
        await page.mouse.up();await page.waitForFunction(()=>__grzCommands.some(command=>command.action==='window_settings'));
        const commands=await saved();
        check('Pointer release persists snapped'+value+'% once at '+scale+'x',
          commands.length===1&&commands[0].background_transparency===String(value)&&commands[0].account_key===account);
      }
      await reset();const box=await page.locator('#ss-background-transparency-track').boundingBox();
      await page.mouse.move(box.x+box.width/2,box.y+box.height/2);await page.mouse.down();
      await page.mouse.move(0,box.y+box.height/2);
      check('Dragging below the track clamps to0 at '+scale+'x',await slider.getAttribute('aria-valuenow')==='0');
      await page.mouse.move(3839,box.y+box.height/2);
      check('Dragging above the track clamps to100 without an early save at '+scale+'x',
        await slider.getAttribute('aria-valuenow')==='100'&&(await saved()).length===0);
      await page.mouse.up();
    }finally{await page.close();}
  }
  const mixed=await nativeHost(browser,{viewport:{width:1600,height:1100,scale:1}});
  try {
    check('A numbered scrollbar gesture excludes the transparency slider, and the release permits its next gesture',
      await mixed.evaluate(()=>{
        const rail=document.getElementById('ss-scrollbar'),thumb=document.getElementById('ss-scrollbar-thumb');
        const slider=document.getElementById('ss-background-transparency'),track=document.getElementById('ss-background-transparency-track');
        const railPoint=thumb.getBoundingClientRect(),sliderPoint=track.getBoundingClientRect();
        const send=(target,type,pointerId,x,y)=>target.dispatchEvent(new PointerEvent(type,{pointerId,button:0,
          buttons:type==='pointerup'?0:1,clientX:x,clientY:y,bubbles:true,cancelable:true}));
        const before=slider.getAttribute('aria-valuenow'),railX=railPoint.left+2,railY=railPoint.top+2;
        const sliderX=sliderPoint.left+sliderPoint.width*.75,sliderY=sliderPoint.top+sliderPoint.height/2;
        send(thumb,'pointerdown',11,railX,railY);
        const railStarted=rail.classList.contains('is-dragging');
        send(slider,'pointerdown',12,sliderX,sliderY);
        document.dispatchEvent(new MouseEvent('mouseup',{button:0,bubbles:true}));
        send(document,'pointerup',12,sliderX,sliderY);
        const exclusive=rail.classList.contains('is-dragging')&&slider.getAttribute('aria-valuenow')===before;
        send(document,'pointerup',11,railX,railY);
        send(slider,'pointerdown',12,sliderX,sliderY);
        send(document,'pointerup',12,sliderX,sliderY);
        const settings=__grzCommands.filter(command=>command.action==='window_settings');
        return railStarted&&exclusive&&!rail.classList.contains('is-dragging')&&settings.length===1&&
          settings[0].background_transparency==='75';
      }));
  }finally{await mixed.close();}
  const mouseOnly=await nativeHost({newPage:async options=>{
    const page=await browser.newPage(options);
    await page.addInitScript(()=>{window.PointerEvent=undefined;});
    return page;
  }},{viewport:{width:1600,height:1000,scale:1}});
  try {
    check('A mouse-only slider ignores right release and saves the last left position after a missed release',
      await mouseOnly.evaluate(()=>{
        const slider=document.getElementById('ss-background-transparency');
        const track=document.getElementById('ss-background-transparency-track').getBoundingClientRect();
        const events=(target,type,value,button,buttons)=>target.dispatchEvent(new MouseEvent(type,{button,buttons,
          clientX:track.left+track.width*value/100,clientY:track.top+track.height/2,bubbles:true,cancelable:true}));
        const saves=()=>__grzCommands.filter(command=>command.action==='window_settings');
        events(slider,'mousedown',25,0,1);
        events(document,'mouseup',75,2,1);
        const stillHeld=slider.getAttribute('aria-valuenow')==='25'&&saves().length===0;
        events(document,'mousemove',50,0,0);
        events(document,'mouseup',75,2,0);
        return stillHeld&&slider.getAttribute('aria-valuenow')==='25'&&saves().length===1&&
          saves()[0].background_transparency==='25';
      }));
  }finally{await mouseOnly.close();}
};
