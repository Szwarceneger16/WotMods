/* Map drill-down is paged and resolves a battle through its owned native reply. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let left=10;
  function next(){if(--left)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}));
const commands=(page,action)=>page.evaluate(action=>__grzCommands.filter(command=>command.action===action),action);
async function publishList(page,pageNumber) {
  await page.evaluate(pageNumber=>{
    const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
    scope.maps[0].battle_list={page:pageNumber,pages:2,total:15,page_size:10,
      items:Array.from({length:pageNumber ? 5 : 10},(_,index)=>{
        const number=pageNumber*10+index;
        return {id:'synthetic-map-battle-'+number,name:number===0 ? '<b>Synthetic tank</b>' : 'Synthetic tank '+number,
          started_at:1793514000-number*600,outcome:['win','loss','draw','unknown'][number%4],wn8:number===0 ? 0 : number===1 ? null : 1750+number};
      })};
    model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
  },pageNumber);await frames(page);
}
async function focusReply(page,request,overrides={}) {
  await page.evaluate(({request,overrides})=>{
    const payload=JSON.parse(model.payload),scope=payload.scopes.launch,sample=scope.battles[0];
    if(overrides.account_key)payload.account_key=overrides.account_key;
    if(overrides.period_id)scope.period_id=overrides.period_id;
    scope.battles=Array.from({length:5},(_,index)=>({...sample,id:index===2 ? request.id : 'synthetic-neighbor-'+index,name:'Synthetic selected page '+index}));
    scope.pagination.battles={page:2,pages:3,page_size:40,total:85};
    scope.battle_focus={id:request.id,request_id:overrides.request_id || request.request_id};
    model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
  },{request,overrides});await frames(page);
}
module.exports=async ({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const page=await nativeHost(browser,{initialViewport:{width:1900,height:1300},viewport:{width:1900,height:1300,scale:1}});
  try {
    for(const [language,messages] of Object.entries(languages)) {
      await page.evaluate(({language,messages})=>{
        const payload=JSON.parse(model.payload),scope=payload.scopes.launch,sample=scope.maps[0];
        payload.account_key='synthetic-map-account-'+language;payload.window_size=[1200,1050];payload.localization={language,messages};
        scope.period_id='synthetic-map-period-'+language;
        scope.maps=[{...sample,id:'synthetic-ridge',name:'Synthetic Ridge'},{...sample,id:'synthetic-valley',name:'Synthetic Valley'}];
        scope.maps.forEach(row=>delete row.battle_list);
        scope.pagination={maps:{page:0,pages:2,page_size:40,total:45},battles:{page:0,pages:3,page_size:40,total:85}};
        scope.ordering={battles:{metric:'battle_wn8',statistic:'avg',direction:'asc',chronology:'oldest'}};
        delete scope.battle_focus;
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      },{language,messages});await page.locator('#ss-scope-launch').click();await page.locator('#ss-group-maps').click();await frames(page);
      const map=page.locator('[data-group-id="synthetic-ridge"]'),more=map.locator('.ss-map-more-button');
      check('Collapsed map details use localized More in '+language,await more.textContent()===messages['more.button'] && await more.getAttribute('aria-expanded')==='false');
      await more.click();await frames(page);
      let sent=await commands(page,'map_battles'),request=sent[sent.length-1];
      check('Opening a map requests only its first owned battle page in '+language+': '+JSON.stringify(request),
        request.account_key==='synthetic-map-account-'+language && request.scope==='launch' && request.period_id==='synthetic-map-period-'+language &&
        request.map_id==='synthetic-ridge' && request.page==='0' && await more.textContent()===messages['more.less']);
      await publishList(page,0);
      const firstPage=await map.evaluate(card=>({rows:card.querySelectorAll('.ss-map-battle-row').length,
        buttons:card.querySelectorAll('.ss-map-battle-open').length,
        names:[...card.querySelectorAll('.ss-map-battle-name')].slice(0,2).map(node=>node.textContent),
        ratings:[...card.querySelectorAll('.ss-map-battle-wn8')].slice(0,2).map(node=>node.textContent),
        markup:[...card.querySelectorAll('b,img')].map(node=>node.outerHTML),
        openCaption:card.querySelector('.ss-map-battle-open').textContent}));
      check('A map page renders ten escaped battle rows and honest zero/missing WN8 in '+language+': '+JSON.stringify(firstPage),
        firstPage.rows===10 && firstPage.buttons===10 && firstPage.names[0]==='<b>Synthetic tank</b>' &&
        firstPage.ratings[0]===messages['metric.wn8']+' 0' && firstPage.ratings[1]===messages['metric.wn8']+' '+messages['format.missing'] &&
        firstPage.markup.length===0 && firstPage.openCaption===messages['maps.open_battle']);
      check('Map battle paging disables only the unavailable direction in '+language,
        await map.locator('.ss-map-page-previous').isDisabled() && await map.locator('.ss-map-page-next').isEnabled());
      for(const viewport of [{width:1900,height:1300,scale:1},{width:470,height:1100,scale:1},{width:960,height:1700,scale:2}]) {
        await page.setViewportSize({width:viewport.width,height:viewport.height});
        await page.evaluate(viewport=>{const payload=JSON.parse(model.payload);payload.viewport=viewport;
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},viewport);await frames(page);
        const audit=await map.evaluate(card=>{
          const cardBox=card.getBoundingClientRect(),overflow=[],clipped=[];
          for(const node of card.querySelectorAll('.ss-map-battles *')) {
            const box=node.getBoundingClientRect();if(!box.width || !box.height)continue;
            if(box.left<cardBox.left-1 || box.right>cardBox.right+1)overflow.push(node.className);
          }
          for(const node of card.querySelectorAll('.ss-map-battle-name,.ss-map-battle-date,.ss-map-battle-outcome,.ss-map-battle-wn8,.ss-map-battle-open .ss-control-label')) {
            const box=node.getBoundingClientRect(),range=document.createRange();range.selectNodeContents(node);
            if([...range.getClientRects()].some(text=>text.left<box.left-1 || text.right>box.right+1 || text.top<box.top-1 || text.bottom>box.bottom+1))clipped.push(node.textContent);
          }
          return {overflow,clipped};
        });
        check('Map drill-down preserves full localized text inside its card in '+language+' at'+viewport.width+'px/'+(viewport.scale*100)+'%: '+JSON.stringify(audit),
          audit.overflow.length===0 && audit.clipped.length===0);
      }
      await page.setViewportSize({width:1900,height:1300});
      await page.evaluate(()=>{const payload=JSON.parse(model.payload);payload.viewport={width:1900,height:1300,scale:1};
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();});await frames(page);
      await map.locator('.ss-map-page-next').click();sent=await commands(page,'map_battles');request=sent[sent.length-1];
      check('Map Next carries the same account, period and map ownership in '+language,
        request.page==='1' && request.map_id==='synthetic-ridge' && request.period_id==='synthetic-map-period-'+language && request.account_key==='synthetic-map-account-'+language);
      await publishList(page,1);
      check('The last map page replaces its rows and remains expanded in '+language,
        await map.locator('.ss-map-battle-row').count()===5 && await map.locator('.ss-map-battle-row').first().getAttribute('data-battle-id')==='synthetic-map-battle-10' &&
        await map.locator('.ss-map-page-next').isDisabled() && await map.locator('.ss-map-page-previous').isEnabled() && await more.textContent()===messages['more.less']);
      await page.locator('[data-group-id="synthetic-valley"] .ss-map-more-button').click();await frames(page);
      await more.click();await frames(page);
      check('Map panels close independently and restore localized More in '+language,
        await more.textContent()===messages['more.button'] && await map.locator('.ss-map-battles').isHidden() &&
        await page.locator('[data-group-id="synthetic-valley"] .ss-map-more-button').getAttribute('aria-expanded')==='true');
      await more.click();await frames(page);
      const target='synthetic-map-battle-14';await map.locator('.ss-map-battle-open[data-battle-id="'+target+'"]').click();
      sent=await commands(page,'battle_select');request=sent[sent.length-1];
      check('A map battle waits for an owned selection reply before changing tabs in '+language,
        request.id===target && request.scope==='launch' && request.account_key==='synthetic-map-account-'+language &&
        request.period_id==='synthetic-map-period-'+language && /^[A-Za-z0-9_.:-]{1,64}$/.test(request.request_id) &&
        await page.locator('#ss-group-maps').getAttribute('aria-pressed')==='true');
      await focusReply(page,request,{request_id:'unmatched-synthetic-focus'});
      check('An unmatched battle focus cannot change the current map tab in '+language,await page.locator('#ss-group-maps').getAttribute('aria-pressed')==='true');
      await focusReply(page,request);
      const focus=await page.evaluate(target=>{
        const card=document.querySelector('[data-group-id="'+target+'"]'),scroll=document.getElementById('ss-scroll');
        if(!card)return null;const box=card.getBoundingClientRect(),viewport=scroll.getBoundingClientRect();
        return {focused:document.activeElement===card,tabindex:card.getAttribute('tabindex'),top:box.top,bottom:box.bottom,
          viewportTop:Math.max(viewport.top,document.getElementById('ss-filter-panel').getBoundingClientRect().bottom),viewportBottom:viewport.bottom,page:JSON.parse(model.payload).scopes.launch.pagination.battles.page};
      },target);
      check('The matching reply selects and focuses the exact sorted Battles page in '+language+': '+JSON.stringify(focus),
        await page.locator('#ss-group-battles').getAttribute('aria-pressed')==='true' && focus && focus.focused && focus.tabindex==='-1' &&
        focus.page===2 && focus.top>=focus.viewportTop-1 && focus.top<focus.viewportBottom-1);
      await page.locator('#ss-group-maps').click();await frames(page);
      await focusReply(page,request);
      check('A consumed focus reply cannot pull a user back from Maps or close its details in '+language,
        await page.locator('#ss-group-maps').getAttribute('aria-pressed')==='true' && await more.getAttribute('aria-expanded')==='true');
    }

    const map=page.locator('[data-group-id="synthetic-ridge"]');
    const ensureOpen=async()=>{const button=map.locator('.ss-map-more-button');if(await button.getAttribute('aria-expanded')!=='true')await button.click();await frames(page);};
    await ensureOpen();
    await map.locator('.ss-map-battle-open').first().click();let selected=await commands(page,'battle_select'),request=selected[selected.length-1];
    await focusReply(page,request,{period_id:'synthetic-replacement-map-period'});
    check('A focus from a retired period cannot navigate to Battles',await page.locator('#ss-group-maps').getAttribute('aria-pressed')==='true');
    await ensureOpen();await map.locator('.ss-map-battle-open').first().click();selected=await commands(page,'battle_select');request=selected[selected.length-1];
    await page.evaluate(()=>{window.__retiredMapBattleOpen=document.querySelector('.ss-map-battle-open').onclick;});
    await focusReply(page,request,{account_key:'synthetic-replacement-map-account'});
    await page.evaluate(()=>__retiredMapBattleOpen());
    check('A focus and retained map control from a retired account cannot navigate or request another battle',
      await page.locator('#ss-group-battles').getAttribute('aria-pressed')!=='true' && (await commands(page,'battle_select')).length===selected.length);
    await page.locator('#ss-group-maps').click();await frames(page);await ensureOpen();
    await map.locator('.ss-map-battle-open').first().click();selected=await commands(page,'battle_select');request=selected[selected.length-1];
    await page.locator('#ss-sort-chronology .ss-select-trigger').click();
    await page.locator('#ss-sort-chronology [data-value="oldest"]').click();await focusReply(page,request);
    check('Changing map order retires an outstanding battle jump',await page.locator('#ss-group-maps').getAttribute('aria-pressed')==='true');
    await map.locator('.ss-map-battle-open').first().click();selected=await commands(page,'battle_select');request=selected[selected.length-1];
    await page.locator('#ss-page-next').click();await frames(page);await focusReply(page,request);
    check('Changing the map page retires an outstanding battle jump',await page.locator('#ss-group-maps').getAttribute('aria-pressed')==='true');
    await map.locator('.ss-map-battle-open').first().click();selected=await commands(page,'battle_select');request=selected[selected.length-1];
    await page.locator('#ss-scope-manual').click();await focusReply(page,request);
    check('Changing the scope retires an outstanding battle jump',await page.locator('#ss-scope-manual').getAttribute('aria-pressed')==='true' &&
      await page.locator('#ss-group-battles').getAttribute('aria-pressed')!=='true');
    await page.locator('#ss-scope-launch').click();await frames(page);await ensureOpen();
    await map.locator('.ss-map-battle-open').first().click();selected=await commands(page,'battle_select');request=selected[selected.length-1];
    await page.evaluate(target=>{
      const original=HTMLElement.prototype.getBoundingClientRect;
      window.__restoreJumpRect=()=>{HTMLElement.prototype.getBoundingClientRect=original;};
      window.__jumpGeometry={targetReads:0,containerPlaceholders:0,samples:[]};
      function record(node,kind) {
        const scroll=document.getElementById('ss-scroll'),before=scroll.scrollTop;
        Promise.resolve().then(()=>__jumpGeometry.samples.push({kind,focused:document.activeElement===node,
          targeted:node.classList.contains('ss-battle-target'),before,after:scroll.scrollTop}));
      }
      HTMLElement.prototype.getBoundingClientRect=function() {
        if(this.getAttribute('data-group-id')===target) {
          __jumpGeometry.targetReads++;
          if(__jumpGeometry.targetReads<=4) {record(this,'zero-target');return {left:0,right:0,top:0,bottom:0,width:0,height:0};}
        }
        if(this.id==='ss-scroll' && __jumpGeometry.targetReads===5 && !__jumpGeometry.containerPlaceholders) {
          __jumpGeometry.containerPlaceholders++;record(document.querySelector('[data-group-id="'+target+'"]'),'placeholder-container');
          return {left:0,right:1,top:0,bottom:1,width:1,height:1};
        }
        return original.call(this);
      };
    },request.id);
    await focusReply(page,request);
    const waitingFocus=await page.evaluate(async target=>{
      const card=document.querySelector('[data-group-id="'+target+'"]'),payload=model.payload,
        scroll=document.getElementById('ss-scroll'),before=scroll.scrollTop;
      if(document.activeElement && document.activeElement!==document.body && typeof document.activeElement.blur==='function')document.activeElement.blur();
      // Native mounting may publish root/body focus before its target geometry.
      // Confirm that event without advancing the owned geometry retry timer.
      document.getElementById('grz-session-stats').dispatchEvent(new FocusEvent('focusin',{bubbles:true,relatedTarget:null}));
      await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
      return {samePayload:model.payload===payload,focused:document.activeElement===card,
        targeted:card.classList.contains('ss-battle-target'),outlines:card.querySelectorAll('.ss-battle-target-outline').length,
        before,after:scroll.scrollTop};
    },request.id);
    check('Ambiguous native root/body focus preserves early paint while owned battle geometry is pending: '+JSON.stringify(waitingFocus),
      waitingFocus.samePayload && !waitingFocus.focused && waitingFocus.targeted && waitingFocus.outlines===1 && waitingFocus.before===waitingFocus.after);
    await page.evaluate(async target=>{
      // Drive owned short geometry retries, never a wheel/input event. Keep
      // the long pulse/page/tooltip timers under the host's existing control.
      for(let attempt=0;attempt<12;attempt++) {
        const card=document.querySelector('[data-group-id="'+target+'"]');
        if(__jumpGeometry.targetReads>=6 && document.activeElement===card)return;
        const retry=[...__grzTimers].find(([,timer])=>timer.delay>0 && timer.delay<=100);
        if(retry){__grzTimers.delete(retry[0]);retry[1].callback();}
        await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
      }
    },request.id);
    const deferred=await page.evaluate(target=>{
      __restoreJumpRect();const card=document.querySelector('[data-group-id="'+target+'"]'),box=card.getBoundingClientRect(),
        container=document.getElementById('ss-scroll').getBoundingClientRect();
      return {...__jumpGeometry,focused:document.activeElement===card,targeted:card.classList.contains('ss-battle-target'),
        top:box.top,viewportTop:Math.max(container.top,document.getElementById('ss-filter-panel').getBoundingClientRect().bottom),viewportBottom:container.bottom};
    },request.id);
    check('Battle navigation paints its target and recovers after more than three empty native measurements without input: '+JSON.stringify(deferred),
      deferred.samples.length===5 && deferred.samples.every(sample=>!sample.focused && sample.targeted && sample.before===sample.after) &&
      deferred.focused && deferred.targeted && deferred.top>=deferred.viewportTop-1 && deferred.top<deferred.viewportBottom-1);
    await page.locator('#ss-group-maps').click();await frames(page);await ensureOpen();
    await page.evaluate(()=>{window.__beforeMapCleanup=__grzCommands.length;const button=document.querySelector('.ss-map-battle-open');
      GRZSessionStats.destroy();button.onclick();});
    check('Retained map battle controls cannot dispatch after teardown',await page.evaluate(()=>__grzCommands.length===__beforeMapCleanup));
  } finally {await page.close();}
};
