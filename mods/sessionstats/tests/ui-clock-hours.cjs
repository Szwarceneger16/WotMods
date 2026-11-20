/* Midnight and noon retain their epochs across clock rings and input methods. */
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let left=4;function next(){if(--left)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);}));
module.exports=async({browser,nativeHost,check})=>{
  const page=await nativeHost(browser,{initialViewport:{width:1800,height:1200},viewport:{width:1800,height:1200,scale:1}});
  try {
    async function open(hour12,hour,field='from',lower=null) {
      await page.evaluate(({hour12,hour,field,lower})=>{
        const payload=JSON.parse(model.payload),scope=payload.scopes.timeline=JSON.parse(JSON.stringify(payload.scopes.manual));
        payload.account_key='synthetic-clock-'+hour12+'-'+hour+'-'+field;payload.window_size=[1200,1000];
        payload.localization={...payload.localization,date_settings:{order:'DMY',separator:'.',hour12,first_weekday:1}};
        scope.period_id='synthetic-clock-period';scope.time_points=[];scope.from_point=scope.to_point='';scope.from_date=scope.to_date=null;
        scope[field+'_point']='__custom__';scope[field+'_date']=new Date(2024,1,29,hour,0).getTime()/1000;
        if(lower!==null){scope.from_point='__custom__';scope.from_date=new Date(2024,1,29,lower,59).getTime()/1000;}
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      },{hour12,hour,field,lower});
      await page.locator('#ss-scope-manual').click();await frames(page);
      await page.locator('#ss-custom-date-calendar-'+field).click();await frames(page);
      return page.locator('#ss-date-picker-'+field);
    }
    let picker=await open(false,0);
    check('24h puts midnight 00 on the outer ring and noon 12 on the inner ring',await picker.evaluate(node=>{
      const midnight=node.querySelector('[data-clock-value="0"]'),noon=node.querySelector('[data-clock-value="12"]');
      return midnight.textContent==='00'&&midnight.style.top==='10%'&&!midnight.classList.contains('ss-date-clock-inner')&&
        noon.textContent==='12'&&noon.style.top==='25%'&&noon.classList.contains('ss-date-clock-inner');
    }));
    async function selected(hour,inner) {
      return picker.evaluate((node,{hour,inner})=>node.querySelector('[data-date-part="hour"]').textContent===String(hour).padStart(2,'0')&&
        node.querySelector('.ss-date-clock').getAttribute('aria-valuenow')===String(hour)&&
        node.querySelector('[data-clock-value="'+hour+'"]').getAttribute('aria-pressed')==='true'&&
        node.querySelector('.ss-date-clock-hand').style.height===(inner?'25%':'38%'),{hour,inner});
    }
    for(const hour of [12,0,13,1]) {
      await picker.locator('[data-clock-value="'+hour+'"]').click();
      await picker.locator('[data-date-part="hour"]').click();
      check('Clicking 24h hour '+hour+' selects the matching label and hand ring',await selected(hour,hour>=12));
    }
    const face=picker.locator('.ss-date-clock');
    for(const [hour,radius] of [[0,.47],[12,.17]]) {
      const box=await face.boundingBox();
      await face.dispatchEvent('mousedown',{button:0,clientX:box.x+box.width/2,clientY:box.y+box.height/2-box.width*radius});
      check('Face hit testing chooses '+(hour===0?'outer midnight':'inner noon'),await selected(hour,hour===12));
      await page.locator('body').dispatchEvent('mouseup');await picker.locator('[data-date-part="hour"]').click();
    }
    await face.press('Home');check('24h Home selects outer midnight',await selected(0,false));
    await face.press('ArrowLeft');check('24h backward wrap selects inner 23',await selected(23,true));
    await face.press('Home');for(let index=0;index<12;index++)await face.press('ArrowRight');
    check('24h keyboard progression reaches inner noon',await selected(12,true));
    await picker.locator('#ss-custom-date-apply-from').click();
    check('Applying inner noon sends the exact noon epoch',await page.evaluate(()=>{
      const command=__grzCommands.filter(value=>value.action==='timeline_range').pop();
      return command.from_date===String(new Date(2024,1,29,12,0).getTime()/1000);
    }));
    picker=await open(false,0);await picker.locator('[data-clock-value="0"]').click();await picker.locator('#ss-custom-date-apply-from').click();
    check('Applying outer midnight sends the exact midnight epoch',await page.evaluate(()=>{
      const command=__grzCommands.filter(value=>value.action==='timeline_range').pop();
      return command.from_date===String(new Date(2024,1,29,0,0).getTime()/1000);
    }));
    picker=await open(false,12,'to',11);
    check('A noon lower bound disables outer midnight while keeping inner noon available',
      await picker.locator('[data-clock-value="0"]').isDisabled()&&await picker.locator('[data-clock-value="12"]').isEnabled());
    await picker.locator('.ss-date-clock').press('Home');
    check('24h Home skips disabled midnight and selects the available inner noon',await selected(12,true));
    picker=await open(true,0);
    check('12h retains its single ring with 12 at the top and no 00 label',
      await picker.locator('[data-clock-value]').count()===12&&await picker.locator('[data-clock-value="0"]').count()===0&&
      await picker.locator('[data-clock-value="12"]').evaluate(node=>node.style.top==='10%'&&!node.classList.contains('ss-date-clock-inner')));
    for(const period of ['AM','PM']) {
      await picker.locator('.ss-date-period').filter({hasText:period}).click();
      await picker.locator('[data-clock-value="12"]').click();await picker.locator('[data-date-part="hour"]').click();
      check('12h top 12 preserves '+period+' and the outer hand',await picker.evaluate((node,period)=>
        node.querySelector('[data-date-part="hour"]').textContent==='12'&&node.querySelector('.ss-date-period[aria-pressed="true"]').textContent===period&&
        node.querySelector('.ss-date-clock-hand').style.height==='38%',period));
    }
  } finally {await page.close();}
};
