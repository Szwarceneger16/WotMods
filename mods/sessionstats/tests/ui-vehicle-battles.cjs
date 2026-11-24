/* Vehicle drill-down shares the owned battle navigation protocol with maps. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let left=10;function next(){if(--left)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);}));
const commands=(page,action)=>page.evaluate(action=>__grzCommands.filter(item=>item.action===action),action);

async function selectedBattlePaging({browser,nativeHost,check}) {
  const page=await nativeHost(browser,{initialViewport:{width:1600,height:1100},viewport:{width:1600,height:1100,scale:1},realTimers:true});
  const targetId='synthetic-edge-target';
  const target=page.locator('#ss-groups [data-group-id="'+targetId+'"]');
  const visible=card=>{
    const cue=card.querySelector('.ss-battle-selection-banner')?.getBoundingClientRect();
    const viewport=document.getElementById('ss-scroll').getBoundingClientRect();
    const filter=document.getElementById('ss-filter-panel').getBoundingClientRect();
    return cue && cue.top>=Math.max(viewport.top,filter.bottom)-1 && cue.bottom<=viewport.bottom+1;
  };
  async function source(group) {
    await page.evaluate(({group,targetId})=>{
      const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
      payload.account_key='synthetic-edge-'+group;payload.window_size=[740,900];
      scope.period_id='synthetic-edge-period';scope.data_revision='synthetic-edge-revision';
      const item=scope[group][0];scope[group]=[item];
      scope.pagination[group]={page:0,pages:1,total:1,page_size:40};
      scope.pagination.battles={page:0,pages:3,total:9,page_size:3};
      delete scope.battle_focus;
      item.battle_list={page:0,pages:1,total:1,page_size:10,items:[
        {id:targetId,name:'Synthetic tank',map:'Synthetic map',outcome:'win',wn8:1250}
      ]};
      item.stats.xp_received={count:1,min:100,max:100,avg:100,sum:100};
      item.extrema_battles={xp_received:{max:{id:targetId,name:'Synthetic tank',map:'Synthetic map',
        started_at:1794000000,metric:'xp_received',statistic:'max',value:100}}};
      model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
      window.__grzCommands=[];
    },{group,targetId});
    await page.locator('#ss-group-'+group).click();await frames(page);
    if(group==='vehicles') {
      await page.locator('#ss-groups .ss-vehicle-more-button').click();
      return page.locator('#ss-groups .ss-map-battle-open[data-battle-id="'+targetId+'"]');
    }
    return page.locator('#ss-groups .ss-metric-battle-link[data-ss-source-metric="xp_received"][data-ss-extreme="max"]');
  }
  async function deliver(index,request,revision) {
    await page.evaluate(({index,request,targetId,revision})=>{
      const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
      const template=scope.battles[0];
      scope.battles=Array.from({length:3},(_,row)=>({...template,
        id:request.action==='battle_select'&&row===0?targetId:'synthetic-edge-'+index+'-'+row,name:'Synthetic battle '+index+'/'+row}));
      scope.pagination.battles={page:index,pages:3,total:9,page_size:3};
      if(request.action==='battle_select')scope.battle_focus={id:request.id,request_id:request.request_id};
      else {delete scope.battle_focus;scope.pagination.battles.request_id=request.request_id;}
      if(revision)scope.data_revision=revision;
      model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
    },{index,request,targetId,revision});await frames(page);
  }
  async function request(action) {
    return (await commands(page,action)).at(-1);
  }
  try {
    for(const group of ['vehicles','tiers']) {
      const opener=await source(group);await opener.click();
      await deliver(1,await request('battle_select'));
      await target.waitFor({state:'visible'});
      await page.waitForFunction(id=>document.activeElement?.getAttribute('data-group-id')===id,targetId);
      check('The '+group+' source focuses the battle beside a pageable boundary',await target.evaluate(visible));
      // Gameface can report the programmatic scroll after the alignment timer settles.
      await page.waitForTimeout(850);
      await page.evaluate(()=>document.getElementById('ss-scroll').dispatchEvent(new Event('scroll')));
      await frames(page);
      const unsolicited=(await commands(page,'page')).filter(page=>page.group==='battles');
      check('A delayed selection scroll never starts background paging from '+group+': '+JSON.stringify(unsolicited),
        unsolicited.length===0&&await page.locator('#ss-filter-loading').getAttribute('aria-hidden')==='true'&&await target.evaluate(visible));
      await page.locator('#ss-scroll').evaluate(scroll=>scroll.dispatchEvent(new WheelEvent('wheel',{bubbles:true,cancelable:true,deltaY:1})));
      await frames(page);
      const previous=await request('page');
      check('Intentional scrolling still requests the earlier page after '+group+' selection',
        previous?.group==='battles'&&previous.page==='0');
      await deliver(0,previous);
      const loaded=await page.evaluate(id=>({
        count:document.querySelectorAll('.ss-continuous-page[data-page-index="0"] .ss-group').length,
        selected:document.querySelectorAll('.ss-group[data-group-id="'+id+'"] .ss-battle-selection-banner').length,
        pending:document.querySelector('.ss-page-pending')?.getAttribute('data-page-index'),
        commands:__grzCommands.filter(command=>command.action==='page').map(command=>command.page)
      }),targetId);
      check('An acknowledged earlier page keeps the selected card and clears its loading boundary after '+group+' selection: '+JSON.stringify(loaded),
        loaded.count===3&&loaded.selected===1&&loaded.pending!=='0');
    }

    const opener=await source('tiers');
    await page.evaluate(()=>{
      const schedule=window.setTimeout.bind(window);
      window.setTimeout=function(callback,delay) {
        const timer=schedule(callback,delay);
        if(delay===10000)window.__expireBattleSelection=()=>{window.clearTimeout(timer);callback();};
        return timer;
      };
    });
    await opener.click();
    const abandoned=await request('battle_select');
    check('An unanswered battle selection shows its own bounded waiting state',
      await page.locator('#ss-filter-loading').getAttribute('aria-hidden')==='false'&&
      await page.evaluate(()=>typeof window.__expireBattleSelection==='function'));
    await page.evaluate(()=>window.__expireBattleSelection());
    check('Battle selection timeout clears the spinner and leaves the source available',
      await page.locator('#ss-filter-loading').getAttribute('aria-hidden')==='true'&&
      await page.locator('#ss-status').textContent()==='Could not load this page.'&&await opener.isEnabled());
    await deliver(1,abandoned);
    check('A late reply to the retired battle selection cannot replace the source view',
      await page.locator('#ss-group-tiers').getAttribute('aria-pressed')==='true'&&await target.count()===0);
    await opener.click();
    const retry=await request('battle_select');await deliver(1,retry);
    await page.waitForFunction(id=>document.activeElement?.getAttribute('data-group-id')===id,targetId);
    check('A new battle selection reaches the same battle after a timed-out request',
      retry.request_id!==abandoned.request_id&&await target.evaluate(visible));
    await deliver(2,retry,'synthetic-edge-revised');
    check('A history update keeps the selected battle visible when its native page changes',
      await target.evaluate(card=>card.closest('.ss-continuous-page')?.getAttribute('data-page-index'))==='2'&&
      await target.evaluate(visible)&&await page.locator('#ss-filter-loading').getAttribute('aria-hidden')==='true');
    await deliver(0,{action:'page',request_id:'synthetic-retired-page'},'synthetic-edge-stale');
    check('A late response from a superseded feed leaves the selected battle visible without restarting the spinner',
      await target.evaluate(visible)&&await page.locator('.ss-continuous-page[data-page-index="0"]').count()===0&&
      await page.locator('#ss-filter-loading').getAttribute('aria-hidden')==='true');
    await deliver(0,abandoned,'synthetic-edge-old-selection');
    check('A superseded selection reply cannot replace the newer selection',
      await target.evaluate(visible)&&await page.locator('.ss-continuous-page[data-page-index="0"]').count()===0&&
      await page.locator('#ss-filter-loading').getAttribute('aria-hidden')==='true');
  } finally {await page.close();}
}

async function vehicleNavigation({browser,nativeHost,check}){
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
      check('A partial vehicle-history page uses its natural height in '+language+': '+JSON.stringify({fullHistory,partialHistory}),
        partialHistory.bodyHeight>0 && partialHistory.bodyHeight<fullHistory.bodyHeight && partialHistory.height<fullHistory.height);
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
         const outsideBeforeResize=await targetCard.evaluate(card=>{
           const panel=document.getElementById('grz-session-stats'),scroll=document.getElementById('ss-scroll');
           const grip=document.getElementById('ss-resize-grip'),gripBox=grip.getBoundingClientRect();
           scroll.scrollTop=0;
           grip.dispatchEvent(new MouseEvent('mousedown',{bubbles:true,cancelable:true,button:0,clientX:gripBox.left+2,clientY:gripBox.top+2}));
           const {token}=__grzCommands.filter(command=>command.action==='resize_begin').at(-1);
           GRZSessionStats.update({resize_gesture:{token,width:625,height:465,active:true}});
           const clipped=card.getBoundingClientRect().bottom>scroll.getBoundingClientRect().bottom;
           GRZSessionStats.update({resize_gesture:{token,width:625,height:465,active:false}});
           panel.dispatchEvent(new MouseEvent('click',{bubbles:true,button:0}));
           return clipped;
         });
         await page.waitForFunction(id=>{
           const card=document.querySelector('[data-group-id="'+id+'"]'),banner=card?.querySelector('.ss-battle-selection-banner');
           if(!banner)return false;
           const viewport=document.getElementById('ss-scroll').getBoundingClientRect(),cue=banner.getBoundingClientRect();
           const filter=document.getElementById('ss-filter-panel').getBoundingClientRect();
           return !document.getElementById('ss-groups').classList.contains('ss-two-columns') &&
             cue.top>=Math.max(viewport.top,filter.bottom)-1 && cue.bottom<=viewport.bottom+1;
         },target,{timeout:5000});
         check('Release keeps one visible selected-battle cue when resizing from two card lanes to one at '+(scale*100)+'%',
           outsideBeforeResize && await targetCard.locator('.ss-battle-selection-banner').count()===1 &&
           await targetCard.evaluate(card=>card.classList.contains('ss-battle-target')));
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
}
module.exports=async options=>{
  const components=[
    ()=>require('./ui-vehicle-metadata.cjs')(options),
    ()=>vehicleNavigation(options),
    ()=>selectedBattlePaging(options)
  ];
  const settled=await Promise.allSettled(components.map(run=>Promise.resolve().then(run)));
  const rejected=settled.find(result=>result.status==='rejected');
  if(rejected)throw rejected.reason;
};
