/* Vehicle drill-down shares the owned battle navigation protocol with maps. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let left=10;function next(){if(--left)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);}));
const commands=(page,action)=>page.evaluate(action=>__grzCommands.filter(item=>item.action===action),action);
module.exports=async ({browser,nativeHost,check})=>{
  await require('./ui-vehicle-metadata.cjs')({browser,nativeHost,check});
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const page=await nativeHost(browser,{initialViewport:{width:3840,height:2560},viewport:{width:3840,height:2560,scale:1},realTimers:true});
  try {
    for(const scale of [1,2])for(const [language,messages] of Object.entries(languages)) {
      await page.evaluate(({language,messages,scale})=>{
        const payload=JSON.parse(model.payload),scope=payload.scopes.launch,sample=scope.vehicles[0];
        payload.account_key='synthetic-vehicle-account-'+language+'-'+scale;payload.window_size=[1400,1100];payload.localization={language,messages};
        payload.viewport={width:3840,height:2560,scale};
        scope.period_id='synthetic-vehicle-period-'+language;
        scope.vehicles=[{...sample,id:'synthetic-heavy',name:'Synthetic Heavy'},{...sample,id:'synthetic-light',name:'Synthetic Light'}];
        scope.vehicles.forEach(vehicle=>delete vehicle.battle_list);delete scope.battle_focus;
        scope.pagination={vehicles:{page:0,pages:1,total:2,page_size:40},battles:{page:0,pages:2,total:43,page_size:40}};
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      },{language,messages,scale});await page.locator('#ss-scope-launch').click();await page.locator('#ss-group-vehicles').click();await frames(page);
      const vehicle=page.locator('[data-group-id="synthetic-heavy"]'),more=vehicle.locator('.ss-vehicle-more-button');
      await more.click();let sent=await commands(page,'vehicle_battles'),request=sent[sent.length-1];
      check('Vehicle More requests its first account-owned page in '+language+': '+JSON.stringify(request),
        request.vehicle_id==='synthetic-heavy' && request.map_id===undefined && request.page==='0' && request.scope==='launch' &&
        request.account_key==='synthetic-vehicle-account-'+language+'-'+scale && request.period_id==='synthetic-vehicle-period-'+language && await more.textContent()===messages['more.less']);
      async function list(pageNumber) {
        await page.evaluate(pageNumber=>{const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
          scope.vehicles[0].battle_list={page:pageNumber,pages:2,total:13,page_size:10,
            items:Array.from({length:pageNumber ? 3 : 10},(_,index)=>({id:'synthetic-vehicle-battle-'+(pageNumber*10+index),
              name:'Synthetic Heavy',map:'Synthetic Map '+(pageNumber*10+index),started_at:1794000000-index*600,outcome:index%2 ? 'loss' : 'win',wn8:index===0 ? 0 : 1750}))};
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},pageNumber);await frames(page);
      }
      await list(0);
      check('Vehicle history exposes ten labeled battle actions in '+language,
        await vehicle.locator('.ss-vehicle-battles').getAttribute('aria-label')===messages['vehicles.battles'] &&
        await vehicle.locator('.ss-map-battle-row').count()===10 && await vehicle.locator('.ss-map-page-previous').isDisabled() &&
        await vehicle.locator('.ss-map-battle-open').first().textContent()===messages['maps.open_battle']);
      const mapLabels=await vehicle.locator('.ss-map-battle-name').evaluateAll(nodes=>nodes.map(node=>{
        const box=node.getBoundingClientRect(),range=document.createRange();range.selectNodeContents(node);
        return {text:node.textContent,fits:box.width>0 && [...range.getClientRects()].every(text=>text.left>=box.left-1 && text.right<=box.right+1)};
      }));
      check('Vehicle history identifies each battle by its readable map name in '+language+': '+JSON.stringify(mapLabels),
        mapLabels.length===10 && mapLabels.every((item,index)=>item.text==='Synthetic Map '+index && item.fits));
      await vehicle.locator('.ss-map-page-next').click();sent=await commands(page,'vehicle_battles');request=sent[sent.length-1];
      check('Vehicle Next retains vehicle and period ownership in '+language,
        request.vehicle_id==='synthetic-heavy' && request.page==='1' && request.period_id==='synthetic-vehicle-period-'+language);
      await frames(page);
      const historyPosition=()=>vehicle.locator('.ss-vehicle-battles').evaluate(panel=>{
        const box=panel.getBoundingClientRect(),body=panel.querySelector('.ss-history-body').getBoundingClientRect(),
          pagination=panel.querySelector('.ss-map-battles-pagination').getBoundingClientRect();
        return {top:box.top,height:box.height,bodyHeight:body.height,paginationTop:pagination.top,scroll:document.getElementById('ss-scroll').scrollTop};
      });
      const fullHistory=await historyPosition();
      await list(1);
      const partialHistory=await historyPosition();
      check('The last vehicle page replaces rows and keeps More open in '+language,
        await vehicle.locator('.ss-map-battle-row').count()===3 && await vehicle.locator('.ss-map-page-next').isDisabled() && await more.getAttribute('aria-expanded')==='true');
      check('A partial vehicle-history page retains its panel height, controls and whole-window position in '+language+': '+JSON.stringify({fullHistory,partialHistory}),
        fullHistory.bodyHeight>0 && Object.keys(fullHistory).every(key=>Math.abs(fullHistory[key]-partialHistory[key])<=1));
      const target='synthetic-vehicle-battle-12';await vehicle.locator('.ss-map-battle-open[data-battle-id="'+target+'"]').click();
      sent=await commands(page,'battle_select');request=sent[sent.length-1];
      check('Vehicle navigation waits for its native battle selection reply in '+language,
        request.id===target && request.account_key==='synthetic-vehicle-account-'+language+'-'+scale && request.period_id==='synthetic-vehicle-period-'+language &&
        await page.locator('#ss-group-vehicles').getAttribute('aria-pressed')==='true');
      await page.evaluate(request=>{const payload=JSON.parse(model.payload),scope=payload.scopes.launch,sample=scope.battles[0];
        scope.battles=Array.from({length:3},(_,index)=>({...sample,id:index===1 ? request.id : 'synthetic-vehicle-neighbor-'+index,name:'Synthetic battle '+index}));
        scope.pagination.battles={page:1,pages:2,total:43,page_size:40};scope.battle_focus={id:request.id,request_id:request.request_id};
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},request);await frames(page);
      const targetCard=page.locator('[data-group-id="'+target+'"]');
      check('Vehicle selection focuses the exact battle with a visible target in '+language,
        await page.locator('#ss-group-battles').getAttribute('aria-pressed')==='true' && await targetCard.evaluate(card=>
          document.activeElement===card && card.classList.contains('ss-battle-target') &&
          parseFloat(getComputedStyle(card.querySelector('.ss-battle-target-outline')).borderTopWidth)>=3));
      await targetCard.evaluate(card=>{
        window.__nativeTargetReflow={card,payload:model.payload};
        const parent=card.parentNode,next=card.nextSibling;
        // Native reparenting may report a temporary focusout without a related
        // target before its programmatic focus restoration has completed.
        card.dispatchEvent(new FocusEvent('focusout',{bubbles:true,relatedTarget:null}));
        parent.appendChild(card);parent.insertBefore(card,next);card.focus();
      });await frames(page);
      check('A temporary native focus loss during reflow preserves the restored battle target in '+language,
        await targetCard.evaluate(card=>card===__nativeTargetReflow.card && model.payload===__nativeTargetReflow.payload &&
          document.activeElement===card && card.classList.contains('ss-battle-target') &&
          card.querySelectorAll('.ss-battle-target-outline').length===1));
      for(const refresh of ['payload','more']) {
        if(refresh==='payload')await page.evaluate(()=>__grzEvents['viewEnv.onDataChanged']());
        if(refresh==='more')await targetCard.locator('.ss-more-button').click();
        await frames(page);
        check('Selected battle highlighting survives '+refresh+' rendering in '+language,await targetCard.evaluate(card=>card.classList.contains('ss-battle-target')));
        check('The selected-battle banner survives '+refresh+' rendering in '+language,
          await targetCard.locator('.ss-battle-selection-banner').count()===1 &&
          await targetCard.locator('.ss-battle-selection-banner').textContent()===messages['battle.selected']);
      }
      if(language==='en') {
        check('A newly selected battle starts its five-second orange pulse',await targetCard.evaluate(card=>card.classList.contains('ss-target-pulsing')));
        await page.waitForTimeout(5100);
        const muted=await targetCard.evaluate(card=>({muted:card.classList.contains('ss-target-muted'),pulse:card.classList.contains('ss-target-pulsing'),
          outlineOpacity:parseFloat(getComputedStyle(card.querySelector('.ss-battle-target-outline')).opacity),cardOpacity:getComputedStyle(card).opacity}));
        check('After five seconds only the target outline becomes thirty percent transparent: '+JSON.stringify(muted),
          muted.muted && !muted.pulse && Math.abs(muted.outlineOpacity-0.7)<0.01 && muted.cardOpacity==='1');
      }
      await targetCard.evaluate(card=>{window.__dismissedTarget=card;window.__targetDismissPayload=model.payload;});
      await page.locator('.ss-game-mode').click();await frames(page);
      check('An inert outside click removes the painted outline without replacing its battle in '+language,
        await targetCard.evaluate(card=>card===__dismissedTarget && model.payload===__targetDismissPayload &&
          !card.classList.contains('ss-battle-target') && card.querySelector('.ss-battle-target-outline')===null) &&
        await page.locator('.ss-battle-target-outline').count()===0 && await page.locator('.ss-battle-selection-banner').count()===0);
      if(language==='en') {
        await page.locator('#ss-group-vehicles').click();await frames(page);
        if(await more.getAttribute('aria-expanded')!=='true')await more.click();
        await vehicle.locator('.ss-map-battle-open[data-battle-id="'+target+'"]').click();sent=await commands(page,'battle_select');
        const repeat=sent[sent.length-1];
        await page.evaluate(request=>{const payload=JSON.parse(model.payload);payload.scopes.launch.battle_focus={id:request.id,request_id:request.request_id};
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},repeat);await frames(page);
        check('Selecting the battle again paints exactly one owned outline at'+(scale*100)+'%',
          await targetCard.locator('.ss-battle-target-outline').count()===1 && await page.locator('.ss-battle-target-outline').count()===1);
        await targetCard.evaluate(card=>{window.__dismissedTarget=card;window.__targetDismissPayload=model.payload;});
        await targetCard.focus();await page.locator('#ss-close').focus();
        await targetCard.evaluate(card=>{
          const root=document.getElementById('grz-session-stats');
          card.dispatchEvent(new FocusEvent('focusout',{bubbles:true,relatedTarget:root}));
          card.dispatchEvent(new FocusEvent('focusout',{bubbles:true,relatedTarget:null}));
          for(const node of [document.body,document.documentElement,root])node.dispatchEvent(new FocusEvent('focusin',{bubbles:true,relatedTarget:null}));
          window.dispatchEvent(new Event('blur'));
        });await frames(page);
        check('Native focus/blur events after a completed vehicle jump preserve its visible frame at'+(scale*100)+'%',
          await targetCard.evaluate(card=>card===__dismissedTarget && model.payload===__targetDismissPayload &&
            card.classList.contains('ss-battle-target') && card.querySelectorAll('.ss-battle-target-outline').length===1 &&
            getComputedStyle(card).borderTopColor==='rgb(231, 162, 59)'));
        await page.locator('.ss-game-mode').click();await frames(page);
        check('An explicit outside click still removes the selected vehicle battle frame at'+(scale*100)+'%',
          await targetCard.evaluate(card=>card===__dismissedTarget && model.payload===__targetDismissPayload &&
            !card.classList.contains('ss-battle-target') && card.querySelector('.ss-battle-target-outline')===null) &&
          await page.locator('.ss-battle-target-outline').count()===0);
      }
      await page.evaluate(()=>{const payload=JSON.parse(model.payload);payload.scopes.launch.period_id+='-new';
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();});await frames(page);
      check('A new period cannot resurrect a dismissed battle highlight in '+language,
        await page.locator('.ss-battle-target').count()===0 && await page.locator('.ss-battle-target-outline').count()===0);
    }
  } finally {await page.close();}
};
