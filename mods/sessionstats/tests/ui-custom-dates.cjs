/* Typed local dates are validated before requesting an account-owned range. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let left=10;
  function next(){if(--left)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}));
const requests=page=>page.evaluate(()=>__grzCommands.filter(command=>command.action==='timeline_range'));
async function choose(page,field,value) {
  await page.locator('#ss-timeline-'+field+' .ss-select-trigger').click();
  await page.locator('#ss-timeline-'+field+' [data-value="'+value+'"]').click();await frames(page);
}
async function update(page,values) {
  await page.evaluate(values=>{const payload=JSON.parse(model.payload);Object.assign(payload.scopes.timeline,values);
    model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},values);await frames(page);
}
module.exports=async ({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const page=await nativeHost(browser,{initialViewport:{width:1800,height:1200},viewport:{width:1800,height:1200,scale:1}});
  try {
    for(const [language,messages] of Object.entries(languages)) {
      const epochs=await page.evaluate(({language,messages})=>{
        const payload=JSON.parse(model.payload);payload.account_key='synthetic-dates-'+language;
        payload.window_size=[1200,950];payload.localization={language,messages};
        const scope=payload.scopes.timeline=JSON.parse(JSON.stringify(payload.scopes.manual));
        const early=new Date(2026,9,1).getTime()/1000,late=new Date(2026,11,1).getTime()/1000;
        scope.period_id='synthetic-date-period-'+language;scope.time_points=[['early',early],['late',late]];
        scope.time_point_names={early:'Synthetic early point',late:'Synthetic late point'};
        scope.from_point=scope.to_point='';scope.from_date=scope.to_date=null;
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
        return {from:new Date(2026,10,1,9,15).getTime()/1000,to:new Date(2026,10,8,18,45).getTime()/1000};
      },{language,messages});await page.locator('#ss-scope-manual').click();await frames(page);
      const before=(await requests(page)).length;
      await choose(page,'from','__custom__');
      const from=page.locator('#ss-custom-date-from'),applyFrom=page.locator('#ss-custom-date-apply-from');
      check('Custom From opens a localized editor without changing the range in '+language,
        await from.isVisible() && await from.getAttribute('placeholder')===messages['timeline.custom_placeholder'] &&
        await applyFrom.textContent()===messages['timeline.custom_apply'] && (await requests(page)).length===before);
      for(const invalid of language==='en' ? ['2026-02-30 11:15','2026-13-01 10:00','2026-11-01 24:00','01/11/2026 10:00'] : ['2026-02-30 11:15']) {
        await from.fill(invalid);await applyFrom.click();
        check('Invalid local calendar input cannot dispatch in '+language+': '+invalid,
          (await requests(page)).length===before &&
          await page.locator('.ss-custom-date-error[data-field="from"]').textContent()===messages['timeline.custom_invalid'] &&
          await page.locator('#ss-status').textContent().then(text=>text.includes(messages['timeline.custom_invalid'])));
      }
      await from.fill('2026-11-01 09:15');
      await update(page,{pending:0});
      check('A same-range live refresh preserves the typed custom draft in '+language,await from.inputValue()==='2026-11-01 09:15');
      await from.press('Enter');await frames(page);
      let sent=await requests(page),command=sent[sent.length-1];
      check('Enter submits the exact local From epoch with only its custom date in '+language+': '+JSON.stringify(command),
        sent.length===before+1 && command.account_key==='synthetic-dates-'+language && command.from_point==='__custom__' &&
        command.to_point==='' && command.from_date===String(epochs.from) && command.to_date===undefined);
      await update(page,{from_point:'__custom__',from_date:epochs.from});
      await choose(page,'to','__custom__');const to=page.locator('#ss-custom-date-to'),applyTo=page.locator('#ss-custom-date-apply-to');
      for(const reversed of ['2026-10-31 23:59','2026-11-01 09:15']) {
        await to.fill(reversed);await applyTo.click();
        check('Reversed or equal custom bounds cannot dispatch in '+language+': '+reversed,
          (await requests(page)).length===before+1 &&
          await page.locator('.ss-custom-date-error[data-field="to"]').textContent()===messages['timeline.custom_order']);
      }
      await to.fill('2026-11-08 18:45');await applyTo.click();await frames(page);
      sent=await requests(page);command=sent[sent.length-1];
      check('Apply retains both exact custom epochs in '+language+': '+JSON.stringify(command),
        sent.length===before+2 && command.from_point==='__custom__' && command.to_point==='__custom__' &&
        command.from_date===String(epochs.from) && command.to_date===String(epochs.to));
      await update(page,{to_point:'__custom__',to_date:epochs.to});
      await choose(page,'from','early');sent=await requests(page);command=sent[sent.length-1];
      check('Selecting a saved point clears only its custom epoch in '+language,
        command.from_point==='early' && command.from_date===undefined && command.to_point==='__custom__' && command.to_date===String(epochs.to));
      await update(page,{from_point:'early',from_date:null});
      await choose(page,'to','');sent=await requests(page);command=sent[sent.length-1];
      check('Selecting Now clears the remaining custom epoch in '+language,
        command.from_point==='early' && command.to_point==='' && command.from_date===undefined && command.to_date===undefined);
      await update(page,{to_point:'',to_date:null});
      await choose(page,'from','__custom__');await from.fill('2026-11-03');await applyFrom.click();
      sent=await requests(page);command=sent[sent.length-1];
      const midnight=await page.evaluate(()=>new Date(2026,10,3).getTime()/1000);
      check('A date without a time uses local midnight in '+language,command.from_date===String(midnight));
      if(language==='en') {
        await from.fill('2026-11-03 12:34');await applyFrom.click();sent=await requests(page);command=sent[sent.length-1];
        const noon=await page.evaluate(()=>new Date(2026,10,3,12,34).getTime()/1000);
        check('A typed noon time retains its local24-hour meaning',command.from_date===String(noon));
      }
    }
    await update(page,{from_point:'',to_point:'',from_date:null,to_date:null});
    await choose(page,'from','__custom__');await page.locator('#ss-custom-date-from').fill('2026-11-25 17:31');
    const beforeAccount=(await requests(page)).length;
    await page.evaluate(()=>{window.__retiredCustomDateApply=document.getElementById('ss-custom-date-apply-from').onclick;
      window.__retiredCustomDateKey=document.getElementById('ss-custom-date-from').onkeydown;});
    await page.evaluate(()=>{const payload=JSON.parse(model.payload);payload.account_key='synthetic-dates-new-account';
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();});await frames(page);
    check('Account changes retire an unfinished custom date editor',await page.locator('#ss-custom-date-from').isHidden());
    await page.evaluate(()=>{__retiredCustomDateApply();__retiredCustomDateKey({key:'Enter',preventDefault(){},stopPropagation(){}});});
    check('Retained custom date click and Enter callbacks cannot act for a replacement account',(await requests(page)).length===beforeAccount);
    await choose(page,'from','__custom__');
    check('A new account cannot inherit another account\'s typed date',await page.locator('#ss-custom-date-from').inputValue()!=='2026-11-25 17:31');
    await page.setViewportSize({width:470,height:1000});
    await page.evaluate(()=>{const payload=JSON.parse(model.payload);payload.viewport={width:470,height:1000,scale:1};
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();});await frames(page);
    check('The custom date input and Apply stay inside a narrow floating window',await page.evaluate(()=>{
      const root=document.getElementById('grz-session-stats').getBoundingClientRect();
      return ['ss-custom-date-from','ss-custom-date-apply-from'].every(id=>{const box=document.getElementById(id).getBoundingClientRect();
        return box.width>0 && box.left>=root.left-1 && box.right<=root.right+1;});
    }));
  } finally {await page.close();}
};
