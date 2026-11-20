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
};
