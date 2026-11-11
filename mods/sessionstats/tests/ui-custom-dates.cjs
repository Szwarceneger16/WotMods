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
  await picker.locator('[data-date-part="year"]').click();
  await picker.locator('[data-year="'+values.year+'"]').click();
  await picker.locator('[data-month="'+values.month+'"]').click();
  await picker.locator('[data-day="'+values.day+'"]').click();
  await picker.locator('[data-date-part="hour"]').click();
  await picker.locator('[data-clock-value="'+values.hour+'"]').click();
  await picker.locator('[data-clock-value="'+values.minute+'"]').click();
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
      let picker=await pick(page,'from',{month:2,year:2024,day:29,hour:7,minute:5});
      check('The localized calendar exposes leap-day/month/year/time controls in '+language,
        await picker.getAttribute('role')==='dialog' && await picker.locator('input').count()===0 && await picker.locator('.ss-date-weekday').count()===7 &&
        await picker.locator('.ss-date-picker-title').textContent()===messages['timeline.calendar_months'].split('|')[1]+' 2024' &&
        await picker.locator('[data-day="29"]').getAttribute('aria-selected')==='true');
      check('Calendar and centered clock remain visible together without a return toggle in '+language,await picker.evaluate(node=>{
        const grid=node.querySelector('.ss-date-picker-body').getBoundingClientRect(),face=node.querySelector('.ss-date-clock').getBoundingClientRect(),holder=node.querySelector('.ss-date-clock-container').getBoundingClientRect();
        return !node.querySelector('.ss-date-return')&&grid.height>0&&face.height>0&&grid.bottom<=face.top&&Math.abs(face.left+face.width/2-holder.left-holder.width/2)<=1;
      }));
      if(language==='en') {
        console.log('GRZ_CALENDAR_QA_V2 '+(await picker.screenshot({type:'png'})).toString('base64'));
        await picker.locator('.ss-date-clock-info').click();
        check('The clock has a small working localized help tooltip',await page.locator('#ss-help-tooltip').isVisible()&&await page.locator('#ss-help-tooltip').textContent()===messages['timeline.calendar_clock_help']);
        await picker.locator('.ss-date-clock-info').click();
        await picker.locator('[data-day="29"]').press('ArrowRight');
        check('Calendar arrows cross a leap-month boundary',await picker.locator('[data-date-part="month"] .ss-control-label').textContent()===messages['timeline.calendar_months'].split('|')[2] && await picker.locator('[data-day="1"]').getAttribute('aria-selected')==='true');
        await picker.locator('[data-day="1"]').press('PageUp');await picker.locator('[data-day="29"]').click();
      }
      await picker.locator('#ss-custom-date-apply-from').click();await frames(page);
      const leap=await page.evaluate(()=>new Date(2024,1,29,7,5).getTime()/1000);command=(await requests(page)).pop();
      check('Calendar Apply sends an exact epoch and the locale-formatted inline text in '+language,
        command.from_date===String(leap) && await from.inputValue()===local('29.02.2024 07:05') && await page.locator('#ss-date-picker-from').count()===0);
      await update(page,{from_point:'__custom__',from_date:leap});await choose(page,'to','__custom__');
      picker=await pick(page,'to',{month:3,year:2024,day:1,hour:16,minute:45});
      await picker.locator('#ss-custom-date-apply-to').click();await frames(page);
      const end=await page.evaluate(()=>new Date(2024,2,1,16,45).getTime()/1000);command=(await requests(page)).pop();
      check('To has the symmetric date/time picker and preserves custom From in '+language,command.from_date===String(leap) && command.to_date===String(end));
      await update(page,{to_point:'__custom__',to_date:end});
      await page.locator('#ss-custom-date-calendar-from').click();await page.locator('#ss-date-picker-from [aria-selected="true"]').press('Escape');
      check('Escape closes the date picker without closing the statistics window in '+language,
        await page.locator('#ss-date-picker-from').count()===0 && await page.evaluate(()=>!__grzCommands.some(command=>command.action==='close')));
      await page.locator('#ss-custom-date-calendar-to').click();await page.locator('.ss-game-mode').click();
      check('An outside click closes the date picker in '+language,await page.locator('#ss-date-picker-to').count()===0);
    }
    await page.evaluate(messages=>{const payload=JSON.parse(model.payload);
      payload.localization={language:'en',messages,date_settings:{order:'MDY',separator:'/',first_weekday:0,hour12:true,
        weekdays:['SystemSu','SystemMo','SystemTu','SystemWe','SystemTh','SystemFr','SystemSa'],
        months:['SystemJan','SystemFeb','SystemMar','SystemApr','SystemMay','SystemJun','SystemJul','SystemAug','SystemSep','SystemOct','SystemNov','SystemDec'],periods:['AM','PM']}};
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},languages.en);await frames(page);
    await update(page,{from_point:'',to_point:'',from_date:null,to_date:null});await choose(page,'from','__custom__');
    const nativeInput=page.locator('#ss-custom-date-from');await nativeInput.fill('');await nativeInput.pressSequentially('022920240705PM');
    check('Native MDY/12-hour settings govern the inline editor independently of English catalog defaults',
      await nativeInput.inputValue()==='02/29/2024 07:05 PM' && await nativeInput.getAttribute('placeholder')==='mm/dd/yyyy hh:mm AM');
    await page.locator('#ss-custom-date-calendar-from').click();let nativePicker=page.locator('#ss-date-picker-from');
    check('Calendar weekdays, month names and Sunday-first layout come from native regional metadata',
      await nativePicker.locator('.ss-date-weekday').first().textContent()==='SystemSu' &&
      await nativePicker.locator('[data-date-part="month"]').textContent()==='SystemFeb' &&
      await nativePicker.locator('.ss-date-week').nth(1).locator('[aria-hidden="true"]').count()===4);
    await nativePicker.locator('[data-date-part="year"]').click();
    const years=await nativePicker.locator('[data-year]').evaluateAll(nodes=>nodes.map(node=>+node.getAttribute('data-year')));
    check('The same popover offers descending years from the current year to 2010',
      years[0]===new Date().getFullYear() && years[years.length-1]===2010 && years.every((year,index)=>index===0||year===years[index-1]-1));
    await nativePicker.locator('[data-year="2024"]').click();
    check('Choosing a year opens a compact twelve-month grid within the original popover',
      await page.locator('#ss-date-picker-from').count()===1 && await nativePicker.locator('[data-month]').count()===12);
    await nativePicker.locator('[data-month="2"]').click();await nativePicker.locator('[data-date-part="hour"]').click();
    check('Hour selection presents a graphical, keyboard-accessible clock instead of numeric fields',
      await nativePicker.locator('.ss-date-clock').getAttribute('role')==='slider' &&
      await nativePicker.locator('[data-clock-value]').count()===12 && await nativePicker.locator('input').count()===0);
    await nativePicker.locator('.ss-date-clock').press('End');await nativePicker.locator('.ss-date-clock').press('ArrowRight');
    check('The hour clock crosses 11 PM to midnight and updates the selected day period',
      await nativePicker.locator('[data-date-part="hour"]').textContent()==='12' && await nativePicker.locator('.ss-date-period[aria-pressed="true"]').textContent()==='AM');
    await nativePicker.locator('.ss-date-clock').press('ArrowLeft');
    check('The hour clock crosses midnight backwards to 11 PM',
      await nativePicker.locator('[data-date-part="hour"]').textContent()==='11' && await nativePicker.locator('.ss-date-period[aria-pressed="true"]').textContent()==='PM');
    await nativePicker.locator('[data-clock-value="7"]').click();
    await nativePicker.locator('.ss-date-clock').press('Home');await nativePicker.locator('.ss-date-clock').press('ArrowLeft');
    check('The minute clock supports every minute using the keyboard, including wraparound to 59',
      await nativePicker.locator('[data-date-part="minute"]').textContent()==='59' && await nativePicker.locator('.ss-date-clock').getAttribute('aria-valuenow')==='59');
    await nativePicker.locator('[data-date-part="year"]').click();await nativePicker.locator('[data-year="2010"]').click();
    await nativePicker.locator('[data-month="1"]').click();await nativePicker.locator('[data-day="1"]').click();
    await nativePicker.locator('[data-day="1"]').press('ArrowLeft');await nativePicker.locator('[data-day="1"]').press('PageUp');
    check('Calendar day/month keyboard navigation cannot cross the January 2010 lower bound',
      await nativePicker.locator('.ss-date-month-previous').isDisabled() && await nativePicker.locator('[data-date-part="year"]').textContent()==='2010' &&
      await nativePicker.locator('[data-day="1"]').getAttribute('aria-selected')==='true');
    await nativePicker.locator('[data-date-part="year"]').click();
    const current=await page.evaluate(()=>{const now=new Date();return {year:now.getFullYear(),month:now.getMonth()+1,day:now.getDate()};});
    await nativePicker.locator('[data-year="'+current.year+'"]').click();
    check('Calendar month choices after the present month are disabled',await nativePicker.locator('[data-month]').evaluateAll((nodes,current)=>nodes.every(node=>+node.getAttribute('data-month')<=current.month||node.disabled),current));
    await nativePicker.locator('[data-month="'+current.month+'"]').click();
    check('Calendar days and next-month navigation cannot enter the future',await nativePicker.locator('.ss-date-month-next').isDisabled()&&await nativePicker.locator('[data-day]').evaluateAll((nodes,current)=>nodes.every(node=>+node.getAttribute('data-day')<=current.day||node.disabled),current));
    await nativePicker.locator('[data-date-part="year"]').click();await nativePicker.locator('[data-year="2024"]').click();
    await nativePicker.locator('[data-month="2"]').click();await nativePicker.locator('[data-day="29"]').click();
    await nativePicker.locator('[data-date-part="hour"]').click();await nativePicker.locator('[data-clock-value="7"]').click();await nativePicker.locator('.ss-date-period').nth(1).click();
    await nativePicker.locator('.ss-date-clock').press('Home');await nativePicker.locator('.ss-date-clock').press('ArrowLeft');
    await nativePicker.locator('#ss-custom-date-apply-from').click();
    const nativeEpoch=await page.evaluate(()=>new Date(2024,1,29,19,59).getTime()/1000);
    check('The native 12-hour graphical picker applies the exact PM epoch and formatted inline value',
      (await requests(page)).pop().from_date===String(nativeEpoch) && await nativeInput.inputValue()==='02/29/2024 07:59 PM');
    await page.evaluate(messages=>{const payload=JSON.parse(model.payload);payload.localization={language:'en',messages};
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},languages.en);await frames(page);
    const range=await page.evaluate(()=>({from:new Date(2024,1,29,20,0).getTime()/1000,to:new Date(2024,2,1,12,0).getTime()/1000}));
    await update(page,{from_point:'__custom__',to_point:'__custom__',from_date:range.from,to_date:range.to});
    await page.locator('#ss-custom-date-calendar-to').click();let bounded=page.locator('#ss-date-picker-to');
    await bounded.locator('[data-date-part="year"]').click();
    check('To year choices before the selected From year are disabled',await bounded.locator('[data-year="2023"]').isDisabled());
    await bounded.locator('[data-year="2024"]').click();
    check('To month choices before the selected From month are disabled',await bounded.locator('[data-month="1"]').isDisabled());
    await bounded.locator('[data-month="2"]').click();
    check('To cannot choose a day before From',await bounded.locator('[data-day="28"]').isDisabled()&&await bounded.locator('[data-day="29"]').isEnabled());
    await bounded.locator('[data-date-part="hour"]').click();
    check('To cannot choose an hour before From on the same day',await bounded.locator('[data-clock-value="19"]').isDisabled());
    await bounded.locator('[data-clock-value="20"]').click();
    check('To cannot choose the same minute as From',await bounded.locator('[data-clock-value="0"]').isDisabled()&&await bounded.locator('[data-clock-value="5"]').isEnabled());
    await bounded.locator('.ss-date-picker-cancel').click();
    await page.locator('#ss-custom-date-calendar-from').click();bounded=page.locator('#ss-date-picker-from');
    await bounded.locator('[data-date-part="month"]').click();await bounded.locator('[data-month="3"]').click();
    check('From cannot choose a day beyond the selected To',await bounded.locator('[data-day="2"]').isDisabled());
    await bounded.locator('[data-day="1"]').click();await bounded.locator('[data-date-part="hour"]').click();
    check('From cannot choose the To hour when no earlier minute remains',await bounded.locator('[data-clock-value="12"]').isDisabled());
    await bounded.locator('.ss-date-picker-cancel').click();
    await update(page,{from_point:'',to_point:'',from_date:null,to_date:null});
    await choose(page,'from','__custom__');
    const beforeFuture=(await requests(page)).length;
    const tomorrow=await page.evaluate(()=>{const day=new Date(Date.now()+86400000);const pad=n=>String(n).padStart(2,'0');return pad(day.getDate())+'.'+pad(day.getMonth()+1)+'.'+day.getFullYear()+' 00:00';});
    await page.locator('#ss-custom-date-from').fill(tomorrow);await page.locator('#ss-custom-date-from').press('Enter');
    check('Manual future dates show an error and never submit',(await requests(page)).length===beforeFuture&&await page.locator('#ss-custom-date-error-from').textContent()===languages.en['timeline.custom_future']);
    await page.locator('#ss-custom-date-from').fill('25.11.2026 17:31');
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
        check('Calendar stays above an explicitly centered clock at'+(scale*100)+'%',await page.locator('#ss-date-picker-'+field).evaluate(node=>{
          const grid=node.querySelector('.ss-date-picker-body').getBoundingClientRect(),face=node.querySelector('.ss-date-clock').getBoundingClientRect(),holder=node.querySelector('.ss-date-clock-container').getBoundingClientRect();
          return grid.height>0&&face.height>0&&grid.bottom<=face.top&&Math.abs(face.left+face.width/2-holder.left-holder.width/2)<=1;
        }));
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
    await page.setViewportSize({width:1800,height:1200});
    const today=await page.evaluate(messages=>{
      const NativeDate=Date,now=new NativeDate(2028,10,11,12,34,45).getTime();
      window.Date=class extends NativeDate {
        constructor(...args){super(...(args.length?args:[now]));}
        static now(){return now;}
      };
      const payload=JSON.parse(model.payload);payload.account_key='synthetic-today-clock';
      payload.viewport={width:1800,height:1200,scale:1};payload.window_size=[1200,950];
      payload.localization={language:'en',messages,date_settings:{order:'DMY',separator:'.',hour12:false}};
      const scope=payload.scopes.timeline;scope.period_id='synthetic-today-clock-period';scope.time_points=[];
      scope.from_point=scope.to_point='';scope.from_date=scope.to_date=null;
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      return {yesterday:new Date(2028,10,10,23,55).getTime()/1000,now:Math.floor(now/60000)*60};
    },languages.en);await frames(page);
    for(const field of ['from','to']) {
      const values={from_point:'',to_point:'',from_date:null,to_date:null};
      values[field+'_point']='__custom__';values[field+'_date']=today.yesterday;
      await update(page,values);await page.locator('#ss-custom-date-calendar-'+field).click();
      const currentPicker=page.locator('#ss-date-picker-'+field);
      await currentPicker.locator('[data-day="11"]').click();
      check('Choosing today clamps a stale later '+field+' clock to the current minute',
        await currentPicker.locator('[data-date-part="hour"]').textContent()==='12' &&
        await currentPicker.locator('[data-date-part="minute"]').textContent()==='34' &&
        await currentPicker.locator('#ss-custom-date-apply-'+field).isEnabled());
      check('Future dates in the '+field+' picker have explicit neutral disabled paint',
        await currentPicker.locator('[data-day="12"]').evaluate(node=>{
          const style=getComputedStyle(node),label=getComputedStyle(node.querySelector('.ss-control-label'));
          return node.disabled && node.getAttribute('aria-disabled')==='true' && node.classList.contains('ss-date-unavailable') &&
            style.opacity==='1' && style.backgroundColor==='rgb(43, 48, 43)' && label.color==='rgb(150, 156, 150)';
        }));
      check('Every future hour is disabled on the '+field+' clock',
        await currentPicker.locator('[data-clock-value]').evaluateAll(nodes=>nodes.every(node=>+node.getAttribute('data-clock-value')<=12 ||
          node.disabled && node.classList.contains('ss-date-unavailable'))));
      await currentPicker.locator('[data-date-part="minute"]').click();
      check('Future minutes in the current hour are visibly disabled for '+field,
        await currentPicker.locator('[data-clock-value="35"]').evaluate(node=>node.disabled&&node.classList.contains('ss-date-unavailable')&&getComputedStyle(node).backgroundColor==='rgb(43, 48, 43)') &&
        await currentPicker.locator('[data-clock-value="30"]').isEnabled());
      const prior=(await requests(page)).length;
      await currentPicker.locator('[data-clock-value="35"]').evaluate(node=>node.onclick());
      check('A retained future-minute callback cannot bypass the clock limit for '+field,
        await currentPicker.locator('[data-date-part="minute"]').textContent()==='34' && (await requests(page)).length===prior);
      if(field==='from')console.log('GRZ_CALENDAR_DISABLED_QA_V1 '+(await currentPicker.screenshot({type:'png'})).toString('base64'));
      await currentPicker.locator('#ss-custom-date-apply-'+field).click();
      check('Applying the clamped '+field+' clock sends exactly the current minute',(await requests(page)).pop()[field+'_date']===String(today.now));
    }
  } finally {await page.close();}
};
