/* Source -> native result -> Back restores the owned view, page and anchor. */
const assert=require('assert'),path=require('path'),readline=require('readline'),{spawn}=require('child_process');
const frames=(page,count=8)=>page.evaluate(count=>new Promise(resolve=>{function next(){if(--count)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);}),count);
function nativeDriver(){
  const root=path.resolve(__dirname,'..'),pending=new Map();let sequence=0,stderr='';
  const child=spawn(process.env.GRZ_PYTHON3||'python3',['-u','-c',`
import copy, json, sys, tempfile, traceback
from test_core import Clock, EXPECTED, result
from grz_session_stats.core import StatsService
from grz_session_stats.projection import DEFAULT_ORDER
with tempfile.TemporaryDirectory(prefix='grz-return-navigation-') as directory:
    clock = Clock(100)
    service = StatsService(directory, 'SYNTHETIC:return-navigation', 'return-launch', EXPECTED, clock, timeline_enabled=True)
    clock.value = 2000
    rows = {}
    for index in range(125):
        row = result('return-row-{0:03d}'.format(index), 110 + index, ended_at=500 + index,
                     xp_base=100 + index, xp_received=12345 if index == 0 else 500 + index,
                     vehicle_name='Synthetic vehicle', map_id='return-map-{0:03d}'.format(index),
                     map_name='Synthetic map {0:03d}'.format(index))
        row.update(_manual_id=service._state['current_manual_id'], _launch_id=service.launch_id,
                   _updated_at=1000, _result_seen=True, revision=1)
        rows[row['arena_id']] = row
    service._state['battles'] = rows
    service._rebuild_indexes()
    def snapshot():
        payload = service.snapshot()
        payload['scopes']['timeline'] = service.timeline_snapshot()
        return copy.deepcopy(payload)
    for line in sys.stdin:
        try:
            request = json.loads(line)
            command = request['command']
            action = command.get('action')
            scope = service.timeline_snapshot()
            period = scope['period_id']
            accepted = True
            if action == 'configure':
                assert service.set_order('timeline', 'battles', dict(DEFAULT_ORDER), period)
                assert service.set_page('timeline', 'battles', 0, period)
                assert service.set_order('timeline', 'maps', dict(DEFAULT_ORDER, metric='xp_base', statistic='max', direction='asc', chronology='oldest'), period)
                assert service.set_page('timeline', 'maps', 0, period)
            elif action == 'revise':
                arena_id = 'return-row-{0:03d}'.format(command.get('index', 60))
                row = copy.deepcopy(service._state['battles'][arena_id])
                row.update(damage=row.get('damage', 1000) + 1, reconcile=True)
                assert service.record_result(row)
            elif action == 'revise_move':
                row = copy.deepcopy(service._state['battles']['return-row-040'])
                row.update(xp_base=220, reconcile=True)
                assert service.record_result(row)
            elif action == 'revise_summary':
                row = copy.deepcopy(service._state['battles']['return-row-124'])
                row.update(xp_received=54321, reconcile=True)
                assert service.record_result(row)
            elif action == 'prepare_nested_map':
                for index in range(10):
                    assert service.record_result(result('return-nested-map-{0}'.format(index), 300 + index,
                        vehicle_id=2, map_id='return-nested-map', map_name='Synthetic nested map', ended_at=420 + index))
                assert service.set_order('timeline', 'maps', dict(DEFAULT_ORDER), period)
                assert service.set_page('timeline', 'maps', 0, period, 'setup-nested-map', 'return-nested-map')
            elif action == 'insert_history_result':
                vehicle = command['group'] == 'vehicles'
                assert service.record_result(result('return-inserted-' + command['group'], 700,
                    vehicle_id=1 if vehicle else 2, map_id='return-nested-map',
                    map_name='Synthetic nested map', ended_at=750))
            elif action == 'revisit_timeline':
                assert service.set_timeline_range('__custom__', '__custom__', 120, 1500)
                assert service.set_timeline_range('', '')
            elif action in ('page', 'sort', 'battle_select', 'vehicle_battles', 'map_battles'):
                accepted = command.get('account_key') == service.account_key
                if accepted and action == 'page':
                    accepted = service.set_page(command['scope'], command['group'], int(command['page']), command['period_id'],
                        command.get('request_id'), command.get('anchor_id'), command.get('order_epoch'), command.get('history_anchor_id'))
                elif accepted and action == 'sort':
                    options = dict((key, command[key]) for key in ('metric', 'statistic', 'direction', 'chronology'))
                    accepted = service.set_order(command['scope'], command['group'], options, command['period_id'], command.get('request_id'), command.get('order_epoch'))
                elif accepted and action == 'vehicle_battles':
                    accepted = service.set_vehicle_battles(command['scope'], command['vehicle_id'], int(command['page']), command['period_id'], command.get('chronology'), command.get('order_epoch'))
                elif accepted and action == 'map_battles':
                    accepted = service.set_map_battles(command['scope'], command['map_id'], int(command['page']), command['period_id'], command.get('chronology'), command.get('order_epoch'))
                elif accepted:
                    accepted = service.select_battle(command['scope'], command['id'], command['period_id'], command['request_id'], command.get('order_epoch'))
            elif action != 'snapshot':
                raise ValueError('Unexpected synthetic bridge command: ' + str(action))
            print(json.dumps({'sequence':request['sequence'], 'accepted':bool(accepted), 'payload':snapshot()}))
        except Exception:
            print(json.dumps({'sequence':request.get('sequence'), 'error':traceback.format_exc()}))
`],{cwd:root,env:{...process.env,PYTHONPATH:[path.join(root,'src'),__dirname].join(path.delimiter)},stdio:['pipe','pipe','pipe']});
  child.stderr.on('data',chunk=>{stderr=(stderr+chunk.toString()).slice(-8000);});
  const rejectAll=error=>{for(const [id,item]of pending){clearTimeout(item.timer);item.reject(error);pending.delete(id);}};
  child.on('error',rejectAll);child.on('exit',(code,signal)=>rejectAll(new Error('Synthetic native driver exited '+code+'/'+signal+' '+stderr)));
  const lines=readline.createInterface({input:child.stdout});
  lines.on('line',line=>{let reply;try{reply=JSON.parse(line);}catch(error){rejectAll(new Error('Invalid synthetic native reply: '+line.slice(0,200)));return;}
    const item=pending.get(reply.sequence);if(!item)return;pending.delete(reply.sequence);clearTimeout(item.timer);
    if(reply.error)item.reject(new Error(reply.error));else item.resolve(reply);});
  return {request(command){return new Promise((resolve,reject)=>{const id=++sequence,timer=setTimeout(()=>{pending.delete(id);reject(new Error('Synthetic native response timed out: '+JSON.stringify(command)+' '+stderr));},10000);
    pending.set(id,{resolve,reject,timer});child.stdin.write(JSON.stringify({sequence:id,command})+'\n');});},close(){lines.close();child.stdin.end();child.kill();rejectAll(new Error('Synthetic native driver closed'));}};
}
module.exports=async({browser,nativeHost,check})=>{
  require('./ui-returned-source.cjs')();check('Returned-source ownership and expiry use the actual shipped marker functions',true);
  const driver=nativeDriver(),page=await nativeHost(browser,{initialViewport:{width:1800,height:1400},viewport:{width:1800,height:1400,scale:1},realTimers:true});
  const sourceCard='return-map-045',mapSource='#ss-groups [data-group-id="'+sourceCard+'"] .ss-metric-battle-link[data-ss-source-metric="xp_received"][data-ss-extreme="max"]';
  const summarySource='#ss-summary .ss-metric-battle-link[data-ss-source-metric="xp_received"][data-ss-extreme="max"]';
  try{
    await page.exposeFunction('__returnNativeCommand',async command=>{const reply=await driver.request(command);if(!reply.accepted)throw new Error('Owned synthetic native command rejected: '+JSON.stringify(command));return reply.payload;});
    await page.evaluate(()=>{
      window.__returnBridgeErrors=[];window.__returnBridgePending=0;
      const previous=model.onAction;
      model.onAction=function(command){previous.call(this,command);if(!['battle_select','page','sort','vehicle_battles','map_battles'].includes(command.action)||window.__returnBridgeFrozen)return;
        __returnBridgePending++;
        __returnNativeCommand(command).then(payload=>{
          if(window.__returnHoldRefresh&&command.action==='page'&&command.group==='maps'&&command.page==='0'){window.__returnHeldRefresh={command,payload};return;}
          if(window.__returnHoldNeighbor&&command.action==='page'&&command.group==='maps'&&!command.anchor_id){window.__returnHeldNeighbor=payload;return;}
          const previousPayload=JSON.parse(model.payload);payload.viewport=previousPayload.viewport;payload.window_size=window.__returnWindowSize||[900,1050];
          if(window.__returnWindowSize){payload.appearance=payload.appearance||{};payload.appearance.window_settings={background_transparency:0,maximized:false,restored_width:__returnWindowSize[0],restored_height:__returnWindowSize[1]};}
          model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
        }).catch(error=>__returnBridgeErrors.push(String(error))).finally(()=>{__returnBridgePending--;});
      };
    });
    async function publish(payload){await page.evaluate(payload=>{payload.viewport=JSON.parse(model.payload).viewport;payload.window_size=window.__returnWindowSize||[900,1050];if(window.__returnWindowSize){payload.appearance=payload.appearance||{};payload.appearance.window_settings={background_transparency:0,maximized:false,restored_width:__returnWindowSize[0],restored_height:__returnWindowSize[1]};}model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);},payload);await frames(page);}
    async function configure(view){await page.evaluate(()=>{window.__returnBridgeFrozen=false;});const reply=await driver.request({action:'configure',view});await publish(reply.payload);await page.locator('#ss-scope-launch').click();await page.locator('#ss-scope-manual').click();await page.locator('#ss-group-'+view).click();await ready(view);await page.locator('#ss-page-next').click();await page.locator('#ss-groups .ss-continuous-page[data-page-index="1"]').waitFor({state:'visible',timeout:5000});await ready(view);await stopAutomaticNavigation();}
    async function stopAutomaticNavigation(){const box=await page.locator('#ss-scroll').boundingBox();await page.mouse.move(box.x+20,box.y+Math.min(100,box.height/2));await page.mouse.wheel(0,1);await frames(page,10);}
    async function opened(){await page.locator('#ss-groups .ss-battle-target .ss-battle-return').waitFor({state:'visible',timeout:5000});await frames(page);}
    async function ready(group,timeout=5000){await page.waitForFunction(group=>document.getElementById('ss-group-'+group).getAttribute('aria-pressed')==='true'&&__returnBridgePending===0&&document.getElementById('ss-groups').getAttribute('aria-busy')!=='true',group,{timeout});await frames(page,12);}
    async function sourceMarker(selector,caption,scale=1){
      await page.locator(selector+'.ss-source-returned').waitFor({state:'visible',timeout:3000});
      const result=await page.locator(selector).evaluate((node,scale)=>{const cue=node.querySelector('.ss-extreme-link-cue'),paint=cue||node,style=getComputedStyle(paint);return{count:document.querySelectorAll('.ss-source-returned').length,focus:document.activeElement===node,color:style.outlineColor,width:parseFloat(style.outlineWidth)/scale,offset:parseFloat(style.outlineOffset)/scale,shadow:style.boxShadow,buttonOutline:getComputedStyle(node).outlineStyle,small:!cue||cue.getBoundingClientRect().width/scale<=18};},scale);
      const financial=selector.includes('ss-credit-extreme-actions');
      check('Back marks only the exact source action with a visible orange frame '+caption,
        result.count===1&&result.focus&&result.color==='rgb(231, 162, 59)'&&result.width===2&&result.small&&
        (financial?result.offset===-2&&result.shadow==='none':result.offset===1&&result.shadow!=='none'));
      if(selector.includes('ss-metric-battle-link')&&!selector.includes('ss-credit-extreme-actions'))check('A numeric return frame belongs only to its small cue '+caption,result.buttonOutline==='none');
    }
    async function geometry(identifier){return page.evaluate(identifier=>{const card=[...document.querySelectorAll('#ss-groups .ss-group')].find(node=>node.getAttribute('data-group-id')===identifier),scroll=document.getElementById('ss-scroll'),box=scroll.getBoundingClientRect();const edge=Math.max(box.top,document.getElementById('ss-filter-panel').getBoundingClientRect().bottom),visible=[...document.querySelectorAll('.ss-continuous-page')].find(section=>{const r=section.getBoundingClientRect();return r.bottom>edge&&r.top<box.bottom;});return {offset:card?card.getBoundingClientRect().top-box.top:null,scroll:scroll.scrollTop,visiblePage:visible?Number(visible.getAttribute('data-page-index')):null,pageLabel:document.getElementById('ss-page-label').textContent,group:document.querySelector('.ss-group-tab[aria-pressed="true"]').id,pages:[...document.querySelectorAll('.ss-continuous-page')].map(node=>Number(node.getAttribute('data-page-index'))),payload:(scope=>({period_id:scope.period_id,data_revision:scope.data_revision,from_point:scope.from_point,to_point:scope.to_point,ordering:scope.ordering,pagination:scope.pagination}))(JSON.parse(model.payload).scopes.timeline)};},identifier);}
    async function surface(width,scale){
      await page.setViewportSize({width:1800*scale,height:1400*scale});
      await page.evaluate(({width,scale})=>{window.__returnWindowSize=[width,1050];const payload=JSON.parse(model.payload);payload.viewport={width:width===550 ? width*scale+20 : 1800*scale,height:1400*scale,scale};payload.window_size=__returnWindowSize;payload.appearance=payload.appearance||{};payload.appearance.window_settings={background_transparency:0,maximized:false,restored_width:width,restored_height:1050};model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);},{width,scale});await frames(page,12);
    }
    // A fresh snapshot may stage a new feed while the old rendered pages
    // remain visible. The summary is fresh and can still open a source result.
    await configure('maps');
    await page.evaluate(()=>{document.getElementById('ss-scroll').scrollTop=40;});await frames(page,12);
    const stagedBefore=await geometry(sourceCard);
    await page.evaluate(()=>{window.__returnHoldRefresh=true;window.__returnHeldRefresh=null;window.__returnStagedCard=document.querySelector('#ss-groups [data-group-id="return-map-020"]');});
    // Select the incoming native page without replacing the existing browser
    // window; any earlier prefetch is free to have changed the server scalar.
    const incomingPage=await driver.request({action:'page',account_key:'SYNTHETIC:return-navigation',scope:'timeline',group:'maps',period_id:'timeline',page:'1',request_id:'staging-incoming-page'});
    assert(incomingPage.accepted,'Synthetic incoming native page is accepted');
    const stagedRevision=await driver.request({action:'revise',index:20}),stagedScope=stagedRevision.payload.scopes.timeline;
    await publish(stagedRevision.payload);
    await page.waitForFunction(()=>!!__returnHeldRefresh&&document.getElementById('ss-groups').getAttribute('aria-busy')==='true',null,{timeout:5000});
    const stagedRating=await page.evaluate(()=>__returnHeldRefresh.payload.scopes.timeline.maps.find(row=>row.id==='return-map-020').stats.wn8);
    const stagedFixture={pages:stagedBefore.pages,incoming:stagedScope.pagination.maps.page,revisionChanged:stagedScope.data_revision!==stagedBefore.payload.data_revision,same:await page.evaluate(()=>!!__returnStagedCard&&document.querySelector('#ss-groups [data-group-id="return-map-020"]')===__returnStagedCard)};
    check('A fresh revision requests the visible page while keeping the old two-page source window visible '+JSON.stringify(stagedFixture),stagedFixture.pages.join(',')==='0,1'&&stagedFixture.incoming===1&&stagedFixture.revisionChanged&&stagedFixture.same);
    await page.locator(summarySource).click();await opened();
    await page.evaluate(()=>{window.__returnHoldRefresh=false;});
    await page.locator('.ss-battle-return').click();await ready('maps');
    await page.waitForFunction(top=>Math.abs(document.getElementById('ss-scroll').scrollTop-top)<=3,stagedBefore.scroll,{timeout:5000});
    const stagedAfter=await geometry(sourceCard);
    check('Back from a staged source restores the visible page without replaying the previous window',stagedAfter.pages.join(',')===String(stagedBefore.visiblePage)&&stagedAfter.visiblePage===stagedBefore.visiblePage&&Math.abs(stagedAfter.scroll-stagedBefore.scroll)<=3);
    check('Back from a staged revision refetches current values instead of reviving the old rendered cache',
      stagedAfter.payload.data_revision===stagedScope.data_revision&&Number((await page.locator('#ss-groups [data-group-id="return-map-020"] .ss-group-wn8-kpi .ss-kpi-value').textContent()).replace(/\s/g,''))===Math.round(stagedRating));
    check('Back from a staged summary source restores that exact action focus',await page.locator(summarySource).evaluate(node=>document.activeElement===node));
    await sourceMarker(summarySource,'staged summary');
    await configure('maps');
    for(const scenario of [{name:'pointer',keyboard:false},{name:'keyboard',keyboard:true},{name:'revised',keyboard:false,revise:true}]){
      const keyboard=scenario.keyboard;
      await stopAutomaticNavigation();
      await page.locator('#ss-groups [data-group-id="'+sourceCard+'"]').scrollIntoViewIfNeeded();await frames(page);
      await page.evaluate(identifier=>{const card=[...document.querySelectorAll('#ss-groups .ss-group')].find(node=>node.getAttribute('data-group-id')===identifier),scroll=document.getElementById('ss-scroll'),filter=document.getElementById('ss-filter-panel');scroll.scrollTop+=card.getBoundingClientRect().top-scroll.getBoundingClientRect().top-filter.getBoundingClientRect().height-50;},sourceCard);await frames(page,12);
      const before=await geometry(sourceCard);
      check('Source anchor is captured from the visible clicked control '+scenario.name,await page.locator(mapSource).evaluate(node=>{const box=node.getBoundingClientRect(),viewport=document.getElementById('ss-scroll').getBoundingClientRect();return box.top>=viewport.top&&box.bottom<=viewport.bottom;}));
      if(keyboard)await page.locator(mapSource).press('Enter');else await page.locator(mapSource).click();
      await opened();
      let revisedRating=null;
      if(scenario.revise){const revised=await driver.request({action:'revise'});
        check('Revision fixture changes the actual native result generation',revised.payload.scopes.timeline.data_revision!==before.payload.data_revision);
        revisedRating=revised.payload.scopes.timeline.maps.find(row=>row.id==='return-map-060').stats.wn8;
        await publish(revised.payload);await opened();}
      const badge=await page.locator('.ss-battle-target .ss-battle-selection-banner').evaluate(banner=>{
        const button=banner.querySelector('.ss-battle-return'),label=banner.querySelector('.ss-battle-selection-label'),
          card=banner.closest('.ss-group'),more=card.querySelector('.ss-more-button'),a=button.getBoundingClientRect(),b=label.getBoundingClientRect(),
          m=more&&more.getBoundingClientRect(),scale=parseFloat(getComputedStyle(document.documentElement).fontSize)||1,
          placed=card.classList.contains('ss-card-border-more')?b.right<=a.left+scale&&m&&m.left-a.right>=2*scale&&
            m.left-a.right<=24*scale&&Math.abs((a.top+a.bottom-m.top-m.bottom)/2)<=2*scale:a.right<=b.left+scale;
        return {tag:button.tagName,caption:button.getAttribute('aria-label'),placed:!!placed,width:a.width,height:a.height};
      });
      check('Selected result offers a keyboard-native Back box beside its label in the scoped layout '+scenario.name,badge.tag==='BUTTON'&&badge.caption==='Back to source'&&badge.placed&&badge.width>=18&&badge.height>=18);
      if(keyboard)await page.locator('.ss-battle-target .ss-battle-return').press('Enter');else await page.locator('.ss-battle-target .ss-battle-return').click();
      await ready('maps');
      try{await page.waitForFunction(({identifier,offset})=>{const card=[...document.querySelectorAll('#ss-groups .ss-group')].find(node=>node.getAttribute('data-group-id')===identifier),scroll=document.getElementById('ss-scroll');return card&&Math.abs(card.getBoundingClientRect().top-scroll.getBoundingClientRect().top-offset)<=3;},{identifier:sourceCard,offset:before.offset},{timeout:5000});}catch(error){throw Error('Source anchor did not return: '+JSON.stringify({scenario:scenario.name,before,after:await geometry(sourceCard),bridge:await page.evaluate(()=>({errors:__returnBridgeErrors,commands:__grzCommands.filter(command=>['page','sort','battle_select'].includes(command.action)).slice(-8),state:GRZSessionStats.getState()}))}));}
      const after=await geometry(sourceCard);
      const expectedPages=scenario.revise?String(before.visiblePage):before.pages.join(',');
      check('Back restores the exact Timeline map order and source page '+scenario.name,after.payload.period_id===before.payload.period_id&&after.payload.from_point===before.payload.from_point&&after.payload.to_point===before.payload.to_point&&JSON.stringify(after.payload.ordering.maps)===JSON.stringify(before.payload.ordering.maps)&&after.payload.pagination.maps.page===before.payload.pagination.maps.page&&after.pages.join(',')===expectedPages);
      check('Back restores the source card anchor instead of resetting the viewport '+scenario.name,before.scroll>100&&Math.abs(after.offset-before.offset)<=3);
      check('Back restores focus to the exact source action '+scenario.name,await page.locator(mapSource).evaluate(node=>document.activeElement===node));
      await sourceMarker(mapSource,scenario.name);
      if(scenario.revise)check('A revised return reloads fresh result values instead of reviving stale source cache',Number((await page.locator('#ss-groups [data-group-id="return-map-060"] .ss-group-wn8-kpi .ss-kpi-value').textContent()).replace(/\s/g,''))===Math.round(revisedRating));
    }
    for(const scenario of ['unchanged','missing neighbor','moved']){
      const moved=scenario==='moved', missing=scenario==='missing neighbor';
      await configure('maps');
      const boundarySource=mapSource.replace(sourceCard,'return-map-040');
      await page.locator(boundarySource).evaluate((button,margin)=>{
        const scroll=document.getElementById('ss-scroll'),viewport=scroll.getBoundingClientRect(),filter=document.getElementById('ss-filter-panel');
        const section=button.closest('.ss-continuous-page');
        scroll.scrollTop+=section.getBoundingClientRect().top-viewport.top-filter.getBoundingClientRect().height-margin;
      },missing?450:80);await frames(page,12);
      const before=await page.locator(boundarySource).evaluate(button=>{
        const scroll=document.getElementById('ss-scroll').getBoundingClientRect(),filter=document.getElementById('ss-filter-panel');
        const first=[...document.querySelectorAll('#ss-groups .ss-group')].find(card=>card.getBoundingClientRect().bottom>filter.getBoundingClientRect().bottom&&card.getBoundingClientRect().top<scroll.bottom);
        const box=button.getBoundingClientRect();
        return {first:first&&Number(first.closest('.ss-continuous-page').dataset.pageIndex),page:Number(button.closest('.ss-continuous-page').dataset.pageIndex),offset:box.top-scroll.top,visible:box.bottom<=scroll.bottom&&box.top>filter.getBoundingClientRect().bottom};
      });
      check('The previous page still supplies the first visible card at the clicked Maps boundary '+scenario+' '+JSON.stringify(before),before.first===0&&before.page===1&&before.visible);
      await page.locator(boundarySource).click();await opened();
      await publish((await driver.request({action:'revise'})).payload);await opened();
      const commandStart=await page.evaluate(()=>__grzCommands.length);
      if(moved||missing)await page.evaluate(()=>{window.__returnHoldNeighbor=true;window.__returnHeldNeighbor=null;});
      if(missing)await page.evaluate(selector=>{
        const scroll=document.getElementById('ss-scroll'),native=Object.getOwnPropertyDescriptor(Element.prototype,'scrollTop');
        window.__returnDroppedClamp=false;
        Object.defineProperty(scroll,'scrollTop',{configurable:true,get(){return native.get.call(this);},set(value){
          if(!__returnDroppedClamp&&value===0&&native.get.call(this)>2&&document.querySelector(selector)){
            window.__returnDroppedClamp=true;return;
          }
          native.set.call(this,value);
        }});
      },boundarySource);
      await page.locator('.ss-battle-return').click();
      let olderNeighbor=null;
      if(moved||missing){
        await page.waitForFunction(()=>!!window.__returnHeldNeighbor);
        olderNeighbor=await page.evaluate(()=>{window.__returnHoldNeighbor=false;return __returnHeldNeighbor;});
        if(moved)await publish((await driver.request({action:'revise_move'})).payload);
      }
      try { await ready('maps',10000); }
      catch (error) {
        throw Error('Map return did not render '+scenario+': '+JSON.stringify(await page.evaluate(start=>({
          status:document.getElementById('ss-status').textContent,busy:document.getElementById('ss-groups').getAttribute('aria-busy'),
          bridgeErrors:__returnBridgeErrors,pending:__returnBridgePending,commands:__grzCommands.slice(start),
          scope:JSON.parse(model.payload).scopes.timeline.pagination.maps,state:GRZSessionStats.getState()
        }),commandStart)));
      }
      try { await sourceMarker(boundarySource,scenario+' boundary source'); }
      catch (error) {
        throw Error('Map return did not mark the source '+scenario+': '+JSON.stringify(await page.evaluate(({selector,start})=>{
          const button=document.querySelector(selector),scroll=document.getElementById('ss-scroll');
          const box=button&&button.getBoundingClientRect(),viewport=scroll.getBoundingClientRect();
          return{alert:document.getElementById('ss-status').textContent,focus:document.activeElement.outerHTML.slice(0,300),
            marker:document.querySelector('.ss-source-returned')?.outerHTML.slice(0,300),
            top:scroll.scrollTop,maximum:scroll.scrollHeight-scroll.clientHeight,hasButton:!!button,offset:box&&box.top-viewport.top,
            buttons:[...document.querySelectorAll('#ss-groups [data-group-id="return-map-040"] button[data-battle-id]')].map(node=>node.outerHTML.slice(0,200)),
            pages:[...document.querySelectorAll('.ss-continuous-page')].map(node=>node.dataset.pageIndex),
            bridgeErrors:__returnBridgeErrors,pending:__returnBridgePending,commands:__grzCommands.slice(start),
            scope:JSON.parse(model.payload).scopes.timeline.pagination.maps};
        },{selector:boundarySource,start:commandStart})));
      }
      if(olderNeighbor)await publish(olderNeighbor);
      const after=await page.locator(boundarySource).evaluate((button,start)=>{
        const scrollNode=document.getElementById('ss-scroll'),scroll=scrollNode.getBoundingClientRect(),box=button.getBoundingClientRect();
        const edge=Math.max(scroll.top,document.getElementById('ss-filter-panel').getBoundingClientRect().bottom);
        return{page:Number(button.closest('.ss-continuous-page').dataset.pageIndex),offset:box.top-scroll.top,
          focused:document.activeElement===button,visible:box.top>=edge-1&&box.bottom<=scroll.bottom+1,top:scrollNode.scrollTop,
          pages:[...document.querySelectorAll('#ss-groups .ss-continuous-page')].map(section=>Number(section.dataset.pageIndex)),
          commands:__grzCommands.slice(start).filter(command=>command.action==='page'&&command.group==='maps')};
      },commandStart);
      const pageNumber=moved?3:1;
      const requestPattern=after.commands.map(command=>command.anchor_id||Number(command.page)).join(',');
      const reanchoredWithoutNeighbor=moved&&requestPattern==='return-map-040,0,return-map-040';
      const pages=missing||reanchoredWithoutNeighbor?[pageNumber]:[pageNumber-1,pageNumber];
      check('Back asks for the clicked group and at most one adjacent page after a revision '+scenario+' '+JSON.stringify(after),
        after.page===pageNumber&&after.pages.join(',')===pages.join(',')&&
        (reanchoredWithoutNeighbor||requestPattern===(moved?'return-map-040,0,return-map-040,2':'return-map-040,0')));
      check('Back keeps the exact boundary source action focused and visible '+scenario+' '+JSON.stringify({before,after}),after.focused&&after.visible);
      if(missing){
        const dropped=await page.evaluate(()=>{delete document.getElementById('ss-scroll').scrollTop;return __returnDroppedClamp;});
        check('Back retries a dropped native setter and clamps the visible source to the available range '+JSON.stringify({before,after,dropped}),
          dropped&&after.top<=1&&after.offset<before.offset-3);
      }else check('Back keeps the exact boundary source action at its original viewport offset '+scenario+' '+JSON.stringify({before:before.offset,after:after.offset}),Math.abs(after.offset-before.offset)<=3);
    }
    for(const reordered of [false,true]){
      await configure('battles');
      await page.evaluate(()=>{document.getElementById('ss-scroll').scrollTop=40;});await frames(page,12);
      const summaryBefore=await geometry('return-row-084');
      await page.locator(summarySource).click();await opened();
      check('Summary source while Battles is open reaches a different native page '+reordered,await page.locator('.ss-battle-target').getAttribute('data-group-id')==='return-row-000');
      if(reordered){
        const sorted=await driver.request({action:'sort',account_key:'SYNTHETIC:return-navigation',scope:'timeline',group:'battles',period_id:'timeline',metric:'xp_received',statistic:'max',direction:'desc',chronology:'newest'});
        assert(sorted.accepted,'Synthetic destination sort is accepted by the real service');await publish(sorted.payload);await opened();
      }
      const commandStart=await page.evaluate(()=>__grzCommands.length);
      await page.locator('.ss-battle-return').click();await ready('battles');
      await page.waitForFunction(top=>Math.abs(document.getElementById('ss-scroll').scrollTop-top)<=3,summaryBefore.scroll,{timeout:5000});
      const summaryAfter=await geometry('return-row-084');
      // The latest native page can be a prefetched successor. The actual
      // origin is the visible cached page beneath the summary, not that scalar.
      const summaryRestored=summaryAfter.payload.pagination.battles.page===summaryBefore.visiblePage&&summaryAfter.visiblePage===summaryBefore.visiblePage&&summaryAfter.pageLabel===summaryBefore.pageLabel&&summaryAfter.pages.join(',')===summaryBefore.pages.join(',')&&Math.abs(summaryAfter.scroll-summaryBefore.scroll)<=3&&JSON.stringify(summaryAfter.payload.ordering.battles)===JSON.stringify(summaryBefore.payload.ordering.battles);
      check('Back from an already-open Battles summary restores its visible page, cached window, order and scroll '+reordered+(summaryRestored?'':': '+JSON.stringify({before:summaryBefore,after:summaryAfter,state:await page.evaluate(()=>GRZSessionStats.getState())})),summaryRestored);
      check('Summary return restores the exact summary source focus '+reordered,await page.locator(summarySource).evaluate(node=>document.activeElement===node));
      await sourceMarker(summarySource,'Battles summary '+reordered);
      if(reordered){const commands=await page.evaluate(start=>__grzCommands.slice(start).filter(command=>['sort','page'].includes(command.action)),commandStart);
        check('Back restores the native origin order before requesting its page',commands.length>=2&&commands[0].action==='sort'&&commands[0].metric==='off'&&commands[0].statistic==='avg'&&commands[0].chronology==='newest'&&commands[1].action==='page'&&commands[1].group==='battles'&&Number(commands[1].page)===summaryBefore.visiblePage);
      }
    }
    await page.evaluate(()=>{const original=Object.getOwnPropertyDescriptor(HTMLElement.prototype,'offsetTop');
      Object.defineProperty(HTMLElement.prototype,'offsetTop',{configurable:true,get(){const value=original.get.call(this);return window.__returnNestedOffsetFault&&this.tagName==='BUTTON'&&this.closest('#ss-summary')&&this.classList.contains('ss-metric-battle-link')?value+__returnNestedOffsetFault:value;}});});
    for(const profile of [{width:1200,scale:1,scroll:0,statistic:'min'},{width:550,scale:1,scroll:120,statistic:'max'},{width:1200,scale:2,scroll:40,statistic:'max'},{width:550,scale:2,scroll:0,statistic:'min'},{width:550,scale:1,scroll:80,statistic:'max',financial:true}]){
      await surface(profile.width,profile.scale);await page.evaluate(()=>{window.__returnBridgeFrozen=false;});const setup=await driver.request({action:'configure'});await publish(setup.payload);
      await page.locator('#ss-scope-manual').click();await page.locator('#ss-group-maps').click();await ready('maps');
      await page.evaluate(({scroll,scale})=>{window.__returnNestedOffsetFault=900*scale;document.getElementById('ss-scroll').scrollTop=scroll*scale;},profile);await frames(page,12);
      const selector=profile.financial?'#ss-summary .ss-credit-extreme-actions .ss-metric-battle-link[data-ss-source-metric="credits_costs"][data-ss-extreme="max"]':summarySource.replace('data-ss-extreme="max"','data-ss-extreme="'+profile.statistic+'"'),caption=profile.width+'px/'+profile.scale+'x/'+(profile.financial?'credits_costs/max':profile.statistic);
      await page.locator(selector).evaluate(node=>{window.__returnRetiredSummaryCell=node.closest('.ss-metric-number,.ss-money-value');node.addEventListener('click',()=>{const cell=node.closest('.ss-metric-number,.ss-money-value'),scroll=document.getElementById('ss-scroll'),viewport=scroll.getBoundingClientRect();window.__returnExpectedSummaryCell={offset:cell.getBoundingClientRect().top-viewport.top,scroll:scroll.scrollTop};},{once:true,capture:true});});
      await page.locator(selector).click();await opened();await page.locator('.ss-battle-return').click();await ready('maps');
      const expected=await page.evaluate(()=>__returnExpectedSummaryCell);
      try{await page.waitForFunction(({selector,offset,tolerance})=>{const node=document.querySelector(selector),cell=node&&node.closest('.ss-metric-number,.ss-money-value'),scroll=document.getElementById('ss-scroll');return cell&&Math.abs(cell.getBoundingClientRect().top-scroll.getBoundingClientRect().top-offset)<=tolerance;},{selector,offset:expected.offset,tolerance:2*profile.scale},{timeout:5000});}
      catch(error){throw Error('Summary source cell did not return to its captured viewport position '+caption+': '+JSON.stringify({expected,actual:await page.locator(selector).evaluate(node=>{const cell=node.closest('.ss-metric-number,.ss-money-value'),scroll=document.getElementById('ss-scroll');return{offset:cell.getBoundingClientRect().top-scroll.getBoundingClientRect().top,scroll:scroll.scrollTop};})}));}
      const restored=await page.locator(selector).evaluate(node=>{const cell=node.closest('.ss-metric-number,.ss-money-value'),scroll=document.getElementById('ss-scroll'),scale=parseFloat(document.documentElement.style.fontSize);return{replaced:cell!==__returnRetiredSummaryCell,scroll:scroll.scrollTop,scale,width:document.getElementById('grz-session-stats').getBoundingClientRect().width/scale};});
      check('A global summary source restores its own upper cell despite stale nested offset geometry '+caption,restored.replaced&&restored.scale===profile.scale&&Math.abs(restored.width-profile.width)<=1&&Math.abs(restored.scroll-expected.scroll)<=2*profile.scale);
      await sourceMarker(selector,'precise summary '+caption,profile.scale);
    }
    await page.evaluate(()=>{window.__returnNestedOffsetFault=0;});await surface(900,1);
    await configure('battles');const oldExtreme=await page.locator(summarySource).getAttribute('data-battle-id');
    await page.locator(summarySource).evaluate(node=>node.addEventListener('click',()=>{window.__returnChangedSummaryCellOffset=node.closest('.ss-metric-number').getBoundingClientRect().top-document.getElementById('ss-scroll').getBoundingClientRect().top;},{once:true,capture:true}));
    await page.locator(summarySource).click();await opened();const newExtreme=await driver.request({action:'revise_summary'});await publish(newExtreme.payload);await opened();
    // The revised summary invalidates the saved pages. Allow the native return
    // deadline for rebuilding the old page window before checking its focus.
    await page.locator('.ss-battle-return').click();await ready('battles',10000);
    await page.waitForFunction(({selector,oldExtreme})=>{
      const source=document.querySelector(selector);
      return source&&source.getAttribute('data-battle-id')!==oldExtreme&&document.activeElement===document.getElementById('ss-group-battles')&&
        document.querySelectorAll('.ss-source-returned').length===0;
    },{selector:summarySource,oldExtreme},{timeout:5000});
    check('A changed extremum uses fallback focus without marking a replacement result or group tab',true);
    check('A changed summary reference still returns to the same upper metric cell',await page.locator(summarySource).evaluate(node=>Math.abs(node.closest('.ss-metric-number').getBoundingClientRect().top-document.getElementById('ss-scroll').getBoundingClientRect().top-__returnChangedSummaryCellOffset)<=2));
    for(const changed of ['account','range','epoch']){
      await configure('battles');await page.locator(summarySource).click();await opened();
      const epoch=changed==='epoch'?(await driver.request({action:'revisit_timeline'})).payload.scopes.timeline.order_epoch:null;
      const retired=await page.evaluate(({changed,epoch})=>{const callback=document.querySelector('.ss-battle-return').onclick,payload=JSON.parse(model.payload),owner={account:payload.account_key,period:payload.scopes.timeline.period_id};
        // The driver owns one account. External replacement views still record
        // commands, while their independent native responses are out of scope.
        window.__returnBridgeFrozen=true;
        if(changed==='account')payload.account_key='SYNTHETIC:return-replacement';
        else if(changed==='range'){payload.scopes.timeline.period_id='timeline:return-other-range';payload.scopes.timeline.from_point='return-other-range';}
        else payload.scopes.timeline.order_epoch=epoch;
        model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);const start=__grzCommands.length;callback();return {start,owner};},{changed,epoch});await frames(page);
      check('A retired Back callback cannot restore an earlier '+changed,await page.evaluate(({start,owner})=>!__grzCommands.slice(start).some(command=>['page','sort','battle_select'].includes(command.action)&&command.account_key===owner.account&&command.period_id===owner.period),retired));
    }
    await page.evaluate(()=>{window.__returnBridgeFrozen=false;});const vehicleSetup=await driver.request({action:'configure'});await publish(vehicleSetup.payload);
    await page.locator('#ss-scope-manual').click();await page.locator('#ss-group-vehicles').click();await ready('vehicles');
    const vehicleId=await page.locator('#ss-groups .ss-group').first().getAttribute('data-group-id');
    await page.locator('#ss-groups .ss-group').first().locator('.ss-vehicle-more-button').click();
    const historySource='#ss-groups [data-group-id="'+vehicleId+'"] .ss-map-battle-open';
    await page.locator(historySource).first().waitFor({state:'visible',timeout:5000});await ready('vehicles');
    const historyBattle=await page.locator(historySource).last().getAttribute('data-battle-id'),historySelector=historySource+'[data-battle-id="'+historyBattle+'"]';
    await page.locator(historySelector).click();await opened();
    await publish((await driver.request({action:'insert_history_result',group:'vehicles'})).payload);await opened();
    await page.locator('.ss-battle-return').click();await ready('vehicles');
    await sourceMarker(historySelector,'vehicle history pointer');
    check('Back keeps the vehicle history expanded around its marked Show battle action',await page.locator('#ss-groups .ss-group').first().locator('.ss-vehicle-more-button').getAttribute('aria-expanded')==='true');
    check('Back requests the moved vehicle history row and renders its new nested page',await page.evaluate(({vehicleId,historyBattle})=>{
      const scope=JSON.parse(model.payload).scopes.timeline, item=scope.vehicles.find(row=>String(row.id)===vehicleId);
      return item&&item.battle_list.page===1&&__grzCommands.some(command=>command.action==='page'&&command.group==='vehicles'&&
        command.anchor_id===vehicleId&&command.history_anchor_id===historyBattle&&command.order_epoch===scope.order_epoch);
    },{vehicleId,historyBattle}));
    const financial='#ss-groups [data-group-id="'+vehicleId+'"] .ss-credit-extreme-actions .ss-metric-battle-link[data-ss-source-metric="credits_income_received"][data-ss-extreme="max"]';
    await page.locator(financial).click();await opened();check('Opening another source retires the previous returned marker',await page.locator('.ss-source-returned').count()===0);
    await page.locator('.ss-battle-return').click();await ready('vehicles');await sourceMarker(financial,'financial Max');
    await publish((await driver.request({action:'prepare_nested_map'})).payload);
    await page.locator('#ss-group-maps').click();await ready('maps');
    const mapCard=page.locator('#ss-groups [data-group-id="return-nested-map"]');
    await mapCard.locator('.ss-map-more-button').click();
    await mapCard.locator('.ss-map-battle-open').first().waitFor({state:'visible',timeout:5000});await ready('maps');
    const mapBattle=await mapCard.locator('.ss-map-battle-open').last().getAttribute('data-battle-id');
    const mapHistorySource='#ss-groups [data-group-id="return-nested-map"] .ss-map-battle-open[data-battle-id="'+mapBattle+'"]';
    await page.locator(mapHistorySource).click();await opened();
    await publish((await driver.request({action:'insert_history_result',group:'maps'})).payload);await opened();
    await page.locator('.ss-battle-return').click();await ready('maps');await sourceMarker(mapHistorySource,'moved map history pointer');
    check('Back restores the new nested map page containing the exact source action',await page.evaluate(mapBattle=>{
      const scope=JSON.parse(model.payload).scopes.timeline, item=scope.maps.find(row=>row.id==='return-nested-map');
      return item&&item.battle_list.page===1&&__grzCommands.some(command=>command.action==='page'&&command.group==='maps'&&
        command.anchor_id==='return-nested-map'&&command.history_anchor_id===mapBattle&&command.order_epoch===scope.order_epoch);
    },mapBattle));
    check('Real native return bridge accepts every owned command without errors',await page.evaluate(()=>__returnBridgeErrors.length===0));
    await page.evaluate(()=>GRZSessionStats.destroy());
    check('Destroying the panel removes the returned-source marker immediately',await page.locator('.ss-source-returned').count()===0);
  }finally{await page.close();driver.close();}
};
