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
async function pick(page,field,values) {
  await page.locator('#ss-custom-date-calendar-'+field).click();
  const picker=page.locator('#ss-date-picker-'+field);
  for(const part of ['month','year']) {
    await picker.locator('[data-date-part="'+part+'"]').fill(String(values[part]));
    await picker.locator('[data-date-part="'+part+'"]').press('Tab');
  }
  await picker.locator('[data-day="'+values.day+'"]').click();
  for(const part of ['hour','minute'])await picker.locator('[data-date-part="'+part+'"]').fill(String(values[part]));
  return picker;
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
      const local=value=>messages['format.date'].includes('{0}/')?value.replace(/\./g,'/'):value;
      await choose(page,'from','__custom__');
      const from=page.locator('#ss-custom-date-from');
      check('Custom From opens a localized editor without changing the range in '+language,
        await from.isVisible() && await from.getAttribute('placeholder')===messages['timeline.custom_placeholder'] &&
        await from.getAttribute('role')==='combobox' && await from.evaluate(input=>{
          const buttons=input.parentNode.querySelectorAll('button'),a=input.getBoundingClientRect(),b=buttons[0].getBoundingClientRect(),c=buttons[1].getBoundingClientRect();
          return input.parentNode.classList.contains('ss-date-editor') && !input.closest('button') && buttons.length===2 &&
            Math.abs(a.top-b.top)<=1 && Math.abs(a.top-c.top)<=1 && a.right<=b.left+1 && b.right<=c.left+1;
        }) && (await requests(page)).length===before);
      for(const invalid of language==='en' ? ['30.02.2026 11:15','01.13.2026 10:00','01.11.2026 24:00','00.11.2026 10:00','29.02.2025 10:00'] : ['30.02.2026 11:15']) {
        await from.fill(local(invalid));await from.press('Enter');
        check('Invalid local calendar input cannot dispatch in '+language+': '+invalid,
          (await requests(page)).length===before &&
          await page.locator('.ss-custom-date-error[data-field="from"]').textContent()===messages['timeline.custom_invalid'] &&
          await page.locator('#ss-status').textContent().then(text=>text.includes(messages['timeline.custom_invalid'])));
      }
      await from.fill('');await from.pressSequentially('011120260915');
      check('Digit typing inserts the locale date/time mask in '+language,await from.inputValue()===local('01.11.2026 09:15'));
      if(language==='en') {
        await page.evaluate(messages=>{const payload=JSON.parse(model.payload);payload.localization={language:'fr',messages};
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},languages.fr);await frames(page);
        check('A same-account language switch reformats a complete date draft without losing digits',await from.inputValue()==='01/11/2026 09:15');
        await from.fill('01/11/202');
        await page.evaluate(messages=>{const payload=JSON.parse(model.payload);payload.localization={language:'en',messages};
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},languages.en);await frames(page);
        check('A partial date draft survives switching back to the dotted locale',await from.inputValue()==='01.11.202');
        await from.fill('01.11.2026 09:15');
      }
      await update(page,{pending:0});
      check('A same-range live refresh preserves the typed custom draft in '+language,await from.inputValue()===local('01.11.2026 09:15'));
      await from.press('Enter');await frames(page);
      let sent=await requests(page),command=sent[sent.length-1];
      check('Enter submits the exact local From epoch with only its custom date in '+language+': '+JSON.stringify(command),
        sent.length===before+1 && command.account_key==='synthetic-dates-'+language && command.from_point==='__custom__' &&
        command.to_point==='' && command.from_date===String(epochs.from) && command.to_date===undefined);
      await update(page,{from_point:'__custom__',from_date:epochs.from});
      await choose(page,'to','__custom__');const to=page.locator('#ss-custom-date-to');
      for(const reversed of ['31.10.2026 23:59','01.11.2026 09:15']) {
        await to.fill(local(reversed));await to.press('Enter');
        check('Reversed or equal custom bounds cannot dispatch in '+language+': '+reversed,
          (await requests(page)).length===before+1 &&
          await page.locator('.ss-custom-date-error[data-field="to"]').textContent()===messages['timeline.custom_order']);
      }
      await to.fill(local('08.11.2026 18:45'));await to.press('Enter');await frames(page);
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
      await choose(page,'from','__custom__');await from.fill(local('03.11.2026'));await from.press('Enter');
      sent=await requests(page);command=sent[sent.length-1];
      const midnight=await page.evaluate(()=>new Date(2026,10,3).getTime()/1000);
      check('A date without a time uses local midnight in '+language,command.from_date===String(midnight));
      if(language==='en') {
        await from.fill(local('03.11.2026 12:34'));await from.press('Enter');sent=await requests(page);command=sent[sent.length-1];
        const noon=await page.evaluate(()=>new Date(2026,10,3,12,34).getTime()/1000);
        check('A typed noon time retains its local24-hour meaning',command.from_date===String(noon));
      }
      await update(page,{from_point:'',to_point:'',from_date:null,to_date:null});await choose(page,'from','__custom__');
      let picker=await pick(page,'from',{month:2,year:2028,day:29,hour:7,minute:5});
      check('The localized calendar exposes leap-day/month/year/time controls in '+language,
        await picker.getAttribute('role')==='dialog' && await picker.locator('.ss-date-weekday').count()===7 &&
        await picker.locator('.ss-date-picker-title').textContent()===messages['timeline.calendar_months'].split('|')[1]+' 2028' &&
        await picker.locator('[data-day="29"]').getAttribute('aria-selected')==='true');
      if(language==='en') {
        await picker.locator('[data-day="29"]').press('ArrowRight');
        check('Calendar arrows cross a leap-month boundary',await picker.locator('[data-date-part="month"]').inputValue()==='3' && await picker.locator('[data-day="1"]').getAttribute('aria-selected')==='true');
        await picker.locator('[data-day="1"]').press('PageUp');await picker.locator('[data-day="29"]').click();
      }
      await picker.locator('#ss-custom-date-apply-from').click();await frames(page);
      const leap=await page.evaluate(()=>new Date(2028,1,29,7,5).getTime()/1000);command=(await requests(page)).pop();
      check('Calendar Apply sends an exact epoch and the locale-formatted inline text in '+language,
        command.from_date===String(leap) && await from.inputValue()===local('29.02.2028 07:05') && await page.locator('#ss-date-picker-from').count()===0);
      await update(page,{from_point:'__custom__',from_date:leap});await choose(page,'to','__custom__');
      picker=await pick(page,'to',{month:3,year:2028,day:1,hour:16,minute:45});
      await picker.locator('#ss-custom-date-apply-to').click();await frames(page);
      const end=await page.evaluate(()=>new Date(2028,2,1,16,45).getTime()/1000);command=(await requests(page)).pop();
      check('To has the symmetric date/time picker and preserves custom From in '+language,command.from_date===String(leap) && command.to_date===String(end));
      await update(page,{to_point:'__custom__',to_date:end});
      await page.locator('#ss-custom-date-calendar-from').click();await page.locator('#ss-date-picker-from [aria-selected="true"]').press('Escape');
      check('Escape closes the date picker without closing the statistics window in '+language,
        await page.locator('#ss-date-picker-from').count()===0 && await page.evaluate(()=>!__grzCommands.some(command=>command.action==='close')));
      await page.locator('#ss-custom-date-calendar-to').click();await page.locator('.ss-game-mode').click();
      check('An outside click closes the date picker in '+language,await page.locator('#ss-date-picker-to').count()===0);
    }
    await update(page,{from_point:'',to_point:'',from_date:null,to_date:null});
    await choose(page,'from','__custom__');await page.locator('#ss-custom-date-from').fill('25.11.2026 17:31');
    const beforeAccount=(await requests(page)).length;
    await page.evaluate(()=>{window.__retiredCustomDateApply=document.getElementById('ss-custom-date-calendar-from').onclick;
      window.__retiredCustomDateKey=document.getElementById('ss-custom-date-from').onkeydown;});
    await page.evaluate(()=>{const payload=JSON.parse(model.payload);payload.account_key='synthetic-dates-new-account';
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();});await frames(page);
    check('Account changes retire an unfinished custom date editor',await page.locator('#ss-custom-date-from').isHidden());
    await page.evaluate(()=>{__retiredCustomDateApply();__retiredCustomDateKey({key:'Enter',preventDefault(){},stopPropagation(){}});});
    check('Retained custom date click and Enter callbacks cannot act for a replacement account',(await requests(page)).length===beforeAccount);
    await choose(page,'from','__custom__');
    check('A new account cannot inherit another account\'s typed date',await page.locator('#ss-custom-date-from').inputValue()!=='25.11.2026 17:31');
    await page.setViewportSize({width:470,height:1000});
    await page.evaluate(()=>{const payload=JSON.parse(model.payload);payload.viewport={width:470,height:1000,scale:1};
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();});await frames(page);
    check('The inline custom date and calendar action stay inside a narrow floating window',await page.evaluate(()=>{
      const root=document.getElementById('grz-session-stats').getBoundingClientRect();
      return ['ss-custom-date-from','ss-custom-date-calendar-from'].every(id=>{const box=document.getElementById(id).getBoundingClientRect();
        return box.width>0 && box.left>=root.left-1 && box.right<=root.right+1;});
    }));
    await choose(page,'to','__custom__');
    for(const scale of [1,2]) {
      const viewport={width:480*scale,height:900*scale};await page.setViewportSize(viewport);
      await page.evaluate(({viewport,scale})=>{const payload=JSON.parse(model.payload);payload.viewport={...viewport,scale};payload.window_size=[550,730];
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},{viewport,scale});await frames(page);
      for(const field of ['from','to']) {
        await page.locator('#ss-custom-date-calendar-'+field).click();await frames(page);
        check('The complete '+field+' picker fits a viewport-constrained window at'+(scale*100)+'%',await page.evaluate(field=>{
          const root=document.getElementById('grz-session-stats').getBoundingClientRect(),picker=document.getElementById('ss-date-picker-'+field).getBoundingClientRect();
          return picker.width>0 && picker.height>0 && picker.left>=root.left-1 && picker.right<=root.right+1 && picker.top>=root.top-1 && picker.bottom<=root.bottom+1;
        },field));
        // A native settings/model update can resize the panel without firing
        // browser window.resize; the existing open picker must follow it.
        await page.evaluate(()=>{const payload=JSON.parse(model.payload);payload.window_size=[800,800];
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();});await frames(page);
        check('An open picker follows native model-driven panel resizing at'+(scale*100)+'%',await page.evaluate(field=>{
          const root=document.getElementById('grz-session-stats').getBoundingClientRect(),picker=document.getElementById('ss-date-picker-'+field).getBoundingClientRect();
          return picker.left>=root.left-1 && picker.right<=root.right+1 && picker.top>=root.top-1 && picker.bottom<=root.bottom+1;
        },field));
        await page.locator('#ss-date-picker-'+field+' .ss-date-picker-cancel').click();
      }
    }
  } finally {await page.close();}
};
