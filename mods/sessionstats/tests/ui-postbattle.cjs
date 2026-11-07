/* Shipped post-battle UI against strict native API doubles in Chromium.
   Container ancestry and seven-cell TableHeader follow the verified client
   document; every displayed battle value and identity below is synthetic. */
const fs=require('fs'),path=require('path');
const root=path.resolve(__dirname,'..');
const widgetSelector='#grz-postbattle-wn8';
const valueSelector='.grz-postbattle-wn8-value';
const spinnerSelector='.grz-postbattle-wn8-spinner';

async function fixture(browser,options,errors) {
  const page=await browser.newPage({viewport:{width:1600,height:900}});
  page.on('pageerror',error=>errors.push(error.message));
  await page.setContent(`<!doctype html><html style="font-size:1px"><head><style>
    body { margin:0; padding:30px; color:#eee; background:#151719; font:16px Arial,sans-serif; }
    .Overview_sourceFixture { width:1450px; }
    [data-name="TableHeader"] [data-name="TableRow"] { display:flex; align-items:center; min-height:72px; }
    .native-cell { flex:0 0 145px; padding:8px; }
    .native-cell button { color:#ddd; background:#292c2d; border:0; padding:8px; }
    .PersonalEfficiency_messagesPanel_sourceFixture { display:flex; flex-direction:column; width:650px; }
    .PersonalEfficiency_messagesPanel_sourceFixture p { margin:0; padding:8px; }
  </style></head><body>
    <section id="native-team" class="TeamScore_totalEfficiencyTable_sourceFixture">
      <div data-name="TableHeader"><div data-name="TableRow"><div id="team-native">Team statistics</div></div></div>
    </section>
    <main id="overview" class="Overview_sourceFixture"></main>
    <aside class="PersonalEfficiency_messagesPanel_wrongScope"><p>Unrelated native explanation</p></aside>
  </body></html>`);
  await page.evaluate(options=>{
    const t=window.__postbattleTest={events:{},eventCalls:[],modelCalls:[],activeCallbacks:new Map(),
      sequence:1000,featureId:41,present:options.feature!==false,wrapped:false,iterator:false,
      model:{rating:JSON.stringify({state:'pending',value:null,label:'must not replace WN8'})},
      clicks:[],warnings:[],observers:[],frames:[],frameRequests:0,emits:0,destroyOnRegister:!!options.destroyOnRegister};
    window.console.warn=message=>t.warnings.push(message);
    t.makeRow=function () {
      const row=document.createElement('div');row.dataset.name='TableRow';
      for(let index=0;index<7;index++) {
        const cell=document.createElement('div');cell.className='native-cell';cell.dataset.nativeCell=String(index);
        const button=document.createElement('button');button.textContent='Native statistic '+(index+1);
        button.onclick=()=>t.clicks.push(index);cell.appendChild(button);row.appendChild(cell);
      }
      return row;
    };
    t.addTable=function () {
      const table=document.createElement('div');table.id='personal-native';
      table.className='PersonalEfficiency_totalEfficiencyTable_sourceFixture';
      const header=document.createElement('div');header.dataset.name='TableHeader';
      const row=t.makeRow();header.appendChild(row);table.appendChild(header);
      document.getElementById('overview').appendChild(table);t.row=row;t.nativeCells=[...row.children];
      return row;
    };
    if(options.anchor!==false) t.addTable();
    const RealObserver=window.MutationObserver;
    window.MutationObserver=options.noObserver ? undefined : function(callback) {
      if(options.observerThrows==='construct') throw Error('Synthetic observer construction failure');
      const owner={callback,disconnected:false,observations:[]};
      const native=new RealObserver(mutations=>callback(mutations,owner));
      owner.observe=(node,settings)=>{
        if(options.observerThrows==='observe') throw Error('Synthetic observer observation failure');
        owner.observations.push(settings);native.observe(node,settings);
      };
      owner.disconnect=()=>{owner.disconnected=true;native.disconnect();};
      t.observers.push(owner);return owner;
    };
    if(options.holdFrames) window.requestAnimationFrame=callback=>{t.frames.push(callback);return ++t.frameRequests;};
    t.drainFrames=function(limit=20) {
      let count=0;while(t.frames.length && count<limit) {t.frames.shift()(0);count++;}return count;
    };
    window.isDomBuilt=!options.pendingDom;
    window.engine={whenReady:Promise.resolve(),
      on(name,callback) {
        if(!['viewEnv.onDataChanged','self.onDomBuilt'].includes(name) || typeof callback!=='function') throw Error('Unexpected engine registration');
        t.eventCalls.push(['on',name]);(t.events[name]||(t.events[name]=[])).push(callback);
      },
      off(name,callback) {
        t.eventCalls.push(['off',name]);t.events[name]=(t.events[name]||[]).filter(fn=>fn!==callback);
      }
    };
    t.makeViewEnv=function(owner) {
      return {
        addDataChangedCallback(name,id,immediate) {
          if(name!=='model' || id!==t.featureId || immediate!==true) throw Error('Unexpected model callback registration');
          const callbackId=++t.sequence;t.activeCallbacks.set(callbackId,{owner,id});
          t.modelCalls.push(['add',owner,callbackId,id]);
          if(t.destroyOnRegister) {t.destroyOnRegister=false;window.GRZPostBattleWn8.destroy();}
          return callbackId;
        },
        removeDataChangedCallback(callbackId,id) {
          const active=t.activeCallbacks.get(callbackId);
          if(!active || active.owner!==owner || active.id!==id) throw Error('Wrong native callback owner');
          t.activeCallbacks.delete(callbackId);t.modelCalls.push(['remove',owner,callbackId,id]);
        }
      };
    };
    window.viewEnv=t.makeViewEnv('original');
    window.subViews={
      ids() {const ids=t.present ? [7,t.featureId] : [7];return t.iterator ? ids[Symbol.iterator]() : ids;},
      get(id) {
        if(id===7) return {model:{nativeUnrelatedModel:{}}};
        if(!t.present || id!==t.featureId) throw Error('Unknown subview requested');
        const model={grzPostBattleWn8:t.wrapped ? {value:t.model} : t.model};
        return t.wrapped ? {value:{model:{value:model}}} : {model};
      }
    };
    t.emit=()=>{t.emits++;[...(t.events['viewEnv.onDataChanged']||[])].forEach(fn=>fn());};
    t.domBuilt=()=>{window.isDomBuilt=true;[...(t.events['self.onDomBuilt']||[])].forEach(fn=>fn());};
  },options);
  // The shipped CSS retains the native coui:// spinner asset URL. Geometry
  // and animation are checked below without requesting external resources.
  await page.addStyleTag({path:path.join(root,'ui/postbattle.css')});
  await page.addScriptTag({path:path.join(root,'ui/postbattle.js')});
  await page.waitForFunction(()=>window.GRZPostBattleWn8);
  if(options.anchor!==false && options.feature!==false && !options.destroyOnRegister && !options.pendingDom) {
    await page.waitForSelector(widgetSelector);
  }
  return page;
}

async function setRating(page,value,wrapped=false) {
  await page.evaluate(({value,wrapped})=>{
    const t=window.__postbattleTest;t.wrapped=wrapped;t.iterator=wrapped;
    const raw=typeof value==='string' ? value : JSON.stringify(value);
    t.model.rating=wrapped ? {value:raw} : raw;t.emit();
  },{value,wrapped});
}

module.exports=async({browser,check:reportCheck})=>{
  const errors=[],failures=[],pages=[];
  const check=(name,pass)=>{if(pass)reportCheck(name,true);else failures.push(name);};
  const open=async options=>{const page=await fixture(browser,options||{},errors);pages.push(page);return page;};
  try {
    const page=await open();
    const widget=page.locator(widgetSelector),value=widget.locator(valueSelector),spinner=widget.locator(spinnerSelector);
    check('Post-battle WN8 appends one cell to the scoped native seven-cell header',await widget.evaluate(node=>{
      const t=window.__postbattleTest,row=node.parentNode;
      return row===t.row && row.children.length===8 && t.nativeCells.every((cell,index)=>row.children[index]===cell) &&
        document.querySelectorAll('#native-team #'+node.id).length===0 &&
        node.getAttribute('data-placement')==='table' && node.getAttribute('role')==='status';
    }));
    check('Pending post-battle state retains WN8 and limits the 18rem spinner to its value slot',
      await widget.locator('.grz-postbattle-wn8-label').textContent()==='WN8' &&
      await widget.getAttribute('aria-busy')==='true' && await spinner.isVisible() &&
      await spinner.evaluate(node=>{
        const style=getComputedStyle(node),slot=node.parentNode.getBoundingClientRect(),box=node.getBoundingClientRect();
        return node.parentNode.classList.contains('grz-postbattle-wn8-slot') && style.width==='18px' && style.height==='18px' &&
          style.backgroundImage.includes('coui://gui/maps/icons/library/spinner.png') &&
          style.animationName==='grz-postbattle-wn8-spin' && style.animationIterationCount==='infinite' &&
          box.left>=slot.left-1 && box.right<=slot.right+1 && box.top>=slot.top-1 && box.bottom<=slot.bottom+1;
      }) && await value.isHidden());
    const nativeBefore=await page.locator('#native-team').innerHTML();
    for(const button of await page.locator('#personal-native .native-cell button').all()) await button.click();
    check('All seven native result cells retain their existing click handlers',
      await page.evaluate(()=>JSON.stringify(__postbattleTest.clicks)==='[0,1,2,3,4,5,6]') &&
      await page.locator('#native-team').innerHTML()===nativeBefore &&
      await widget.evaluate(node=>getComputedStyle(node).pointerEvents==='none'));
    await setRating(page,{state:'ready',value:0,label:'fake-native-label'});
    check('Confirmed zero renders as0 while the label remains exactly WN8',
      await value.textContent()==='0' && await widget.locator('.grz-postbattle-wn8-label').textContent()==='WN8' &&
      await spinner.isHidden() && await widget.getAttribute('aria-busy')==='false');
    await setRating(page,{state:'ready',value:1234567.6,labels:{'format.thousands':'.'}},true);
    check('Wrapped native subviews and rating properties render rounded localized thousands',
      await value.textContent()==='1.234.568' && await widget.getAttribute('aria-label')==='WN8 1.234.568');
    await setRating(page,{state:'pending',value:null,labels:{'footer.processing':'Przetwarzanie wyników'}});
    check('Localized pending text is accessible while only the numeric slot spins',
      await widget.getAttribute('aria-label')==='WN8 Przetwarzanie wyników' && await spinner.isVisible());
    await setRating(page,{state:'unavailable',value:null});
    check('Unavailable data replaces a pending spinner with an honest dash',
      await value.textContent()==='—' && await value.isVisible() && await spinner.isHidden() &&
      await spinner.evaluate(node=>getComputedStyle(node).animationName==='none') &&
      await widget.getAttribute('aria-busy')==='false');
    for(const bad of ['{broken','{"state":"ready","value":1e400}',null,{}, {state:'ready',value:true},{state:'ready',value:-1},
      {state:'ready',value:'1565'},{state:'other',value:1565}]) {
      await setRating(page,bad);
      check('Malformed post-battle rating remains unavailable: '+JSON.stringify(bad),
        await value.textContent()==='—' && await spinner.isHidden() && await widget.getAttribute('aria-busy')==='false');
    }
    await page.evaluate(()=>{delete __postbattleTest.model.rating;__postbattleTest.emit();});
    check('A missing rating property is unavailable rather than indefinitely pending',
      await value.textContent()==='—' && await spinner.isHidden());
    await setRating(page,{state:'ready',value:1565});
    await page.addScriptTag({path:path.join(root,'ui/postbattle.js')});
    check('Loading the shipped script twice keeps one widget and one native model callback',
      await widget.count()===1 && await page.evaluate(()=>__postbattleTest.activeCallbacks.size===1 &&
        __postbattleTest.modelCalls.filter(call=>call[0]==='add').length===1));

    await page.evaluate(()=>{
      const t=__postbattleTest,next=t.makeRow();t.row.replaceWith(next);t.row=next;t.nativeCells=[...next.children];
    });
    await page.waitForFunction(()=>{
      const node=document.getElementById('grz-postbattle-wn8');return node && node.parentNode===__postbattleTest.row;
    });
    check('Native React header replacement automatically reattaches without altering replacement cells',
      await widget.count()===1 && await widget.evaluate(node=>{
        const t=__postbattleTest;return t.row.children.length===8 && t.nativeCells.every((cell,index)=>t.row.children[index]===cell);
      }) && await value.textContent()==='1\u00a0565');
    await page.evaluate(()=>document.getElementById('personal-native').remove());
    await page.waitForFunction(()=>!document.getElementById('grz-postbattle-wn8'));
    check('Leaving the personal-efficiency tab removes its owned WN8 cell',await widget.count()===0);
    await page.evaluate(()=>__postbattleTest.addTable());
    await page.waitForSelector(widgetSelector);
    check('Returning to the native personal-efficiency row reattaches one WN8 cell',await widget.count()===1);
    await page.evaluate(()=>{
      document.getElementById('personal-native').remove();
      const panel=document.createElement('div');panel.className='PersonalEfficiency_messagesPanel_sourceFixture';
      const paragraph=document.createElement('p');paragraph.textContent='Native zero-efficiency explanation';
      paragraph.onclick=()=>__postbattleTest.clicks.push('paragraph');panel.appendChild(paragraph);
      document.getElementById('overview').appendChild(panel);__postbattleTest.emptyPanel=panel;__postbattleTest.paragraph=paragraph;
    });
    await page.waitForFunction(()=>{
      const node=document.getElementById('grz-postbattle-wn8');return node && node.getAttribute('data-placement')==='empty';
    });
    check('A zero-efficiency result preserves the native paragraph and appends its own normal-flow cell',
      await widget.evaluate(node=>{
        const t=__postbattleTest,paragraph=t.paragraph;
        return node.parentNode===t.emptyPanel && t.emptyPanel.children.length===2 && t.emptyPanel.children[0]===paragraph &&
          paragraph.textContent==='Native zero-efficiency explanation' && getComputedStyle(node).position==='static' &&
          node.getBoundingClientRect().top>=paragraph.getBoundingClientRect().bottom-1;
      }));
    await page.locator('.PersonalEfficiency_messagesPanel_sourceFixture p').click();
    check('The zero-efficiency explanation retains its native handler',
      await page.evaluate(()=>__postbattleTest.clicks[__postbattleTest.clicks.length-1]==='paragraph'));

    await page.evaluate(()=>{
      const t=__postbattleTest;t.oldModel=t.model;t.oldCallback=(t.events['viewEnv.onDataChanged']||[])[0];
      t.featureId=77;t.model={rating:JSON.stringify({state:'ready',value:2200})};t.emit();
    });
    check('Replacing a native subview removes the exact old callback ID and registers its new owner',
      await value.textContent()==='2\u00a0200' && await page.evaluate(()=>{
        const t=__postbattleTest,adds=t.modelCalls.filter(call=>call[0]==='add'),removes=t.modelCalls.filter(call=>call[0]==='remove');
        return adds.length===2 && removes.length===1 && removes[0][2]===adds[0][2] &&
          removes[0][3]===41 && adds[1][3]===77 && t.activeCallbacks.size===1;
      }));
    await page.evaluate(()=>{__postbattleTest.oldModel.rating=JSON.stringify({state:'ready',value:9999});__postbattleTest.oldCallback();});
    check('A retained stale native notification reads only the current feature model',await value.textContent()==='2\u00a0200');
    await page.evaluate(()=>{window.viewEnv=__postbattleTest.makeViewEnv('replacement');__postbattleTest.emit();});
    check('Replacing viewEnv removes its callback through the original owner and subscribes the replacement once',
      await page.evaluate(()=>{
        const t=__postbattleTest,calls=t.modelCalls,old= calls.filter(call=>call[0]==='add' && call[3]===77)[0];
        return calls.some(call=>call[0]==='remove' && call[1]==='original' && call[2]===old[2] && call[3]===77) &&
          [...t.activeCallbacks.values()].every(entry=>entry.owner==='replacement') && t.activeCallbacks.size===1;
      }));
    await page.evaluate(()=>{__postbattleTest.present=false;__postbattleTest.emit();});
    check('Removing the feature removes only its widget and native model callback',
      await widget.count()===0 && await page.evaluate(()=>__postbattleTest.activeCallbacks.size===0) &&
      await page.locator('#native-team').innerHTML()===nativeBefore);
    await page.evaluate(()=>{__postbattleTest.present=true;__postbattleTest.emit();});
    await page.waitForSelector(widgetSelector);
    await page.evaluate(()=>{
      const t=__postbattleTest;t.retained=(t.events['viewEnv.onDataChanged']||[]).slice();
      t.retainedObservers=t.observers.map(owner=>owner.callback);GRZPostBattleWn8.destroy();
      t.retained.forEach(callback=>callback());t.retainedObservers.forEach(callback=>callback([]));
      const row=t.addTable();row.appendChild(document.createElement('span'));
    });
    await page.waitForTimeout(50);
    check('Destroy retires observer, engine and exact model callbacks without ghost reappearance',
      await widget.count()===0 && await page.evaluate(()=>{
        const t=__postbattleTest;return t.activeCallbacks.size===0 &&
          Object.values(t.events).every(callbacks=>callbacks.length===0) && t.observers.every(owner=>owner.disconnected);
      }));

    const absent=await open({anchor:false});
    check('A feature with no verified native insertion anchor leaves the document untouched',
      await absent.locator(widgetSelector).count()===0 && await absent.locator('#native-team [data-name="TableRow"]').evaluate(row=>row.children.length===1) &&
      await absent.locator('.PersonalEfficiency_messagesPanel_wrongScope').evaluate(panel=>panel.children.length===1));
    const missing=await open({feature:false});
    check('A native personal table without the owned feature receives no WN8 widget or subscription',
      await missing.locator(widgetSelector).count()===0 && await missing.evaluate(()=>__postbattleTest.activeCallbacks.size===0));
    const delayed=await open({pendingDom:true});
    check('The native DOM-ready event owns initialization when the document is not built yet',
      await delayed.locator(widgetSelector).count()===0 && await delayed.evaluate(()=>(__postbattleTest.events['self.onDomBuilt']||[]).length===1));
    await delayed.evaluate(()=>__postbattleTest.domBuilt());
    await delayed.waitForSelector(widgetSelector);
    await delayed.evaluate(()=>GRZPostBattleWn8.destroy());
    check('Destroy removes both native DOM-ready and data subscriptions',
      await delayed.evaluate(()=>Object.values(__postbattleTest.events).every(callbacks=>callbacks.length===0) && __postbattleTest.activeCallbacks.size===0));
    const synchronous=await open({destroyOnRegister:true});
    check('Synchronous destruction during model registration removes the returned callback through its exact owner',
      await synchronous.locator(widgetSelector).count()===0 && await synchronous.evaluate(()=>{
        const t=__postbattleTest,add=t.modelCalls.find(call=>call[0]==='add'),remove=t.modelCalls.find(call=>call[0]==='remove');
        return add && remove && add[1]===remove[1] && add[2]===remove[2] && add[3]===remove[3] &&
          t.activeCallbacks.size===0 && Object.values(t.events).every(callbacks=>callbacks.length===0);
      }));
    const noObserver=await open({noObserver:true,holdFrames:true,anchor:false});
    const initialDeferred=await noObserver.evaluate(()=>{
      const t=__postbattleTest,first=t.frames.shift();
      const before=!!document.getElementById('grz-postbattle-wn8');
      if(first)first(0);
      t.addTable();const drained=t.drainFrames(8);
      return {before,first:!!first,drained,requests:t.frameRequests,remaining:t.frames.length,emits:t.emits,
        observerAvailable:typeof window.MutationObserver==='function',observers:t.observers.length};
    });
    check('Initial native binding retries delayed DOM placement without MutationObserver or another model event',
      !initialDeferred.before && initialDeferred.first && initialDeferred.drained===1 &&
      initialDeferred.requests===2 && initialDeferred.remaining===0 && initialDeferred.emits===0 &&
      !initialDeferred.observerAvailable && initialDeferred.observers===0 &&
      await noObserver.locator(widgetSelector).count()===1);
    const delayedOverview=await noObserver.evaluate(()=>{
      const t=__postbattleTest,start=t.frameRequests;
      document.getElementById('overview').remove();
      t.model.rating=JSON.stringify({state:'ready',value:2100});
      t.emit();t.emit();t.emit();
      const queued=t.frames.length,first=t.frames.shift();if(first)first(0);
      const overview=document.createElement('main');overview.id='overview';overview.className='Overview_sourceFixture';
      document.body.appendChild(overview);t.addTable();
      const beforeSecond=!!document.getElementById('grz-postbattle-wn8');
      const drained=t.drainFrames(8);
      return {queued,first:!!first,beforeSecond,drained,requests:t.frameRequests-start,remaining:t.frames.length,emits:t.emits};
    });
    check('A model event before delayed Overview creation coalesces into one two-frame placement retry',
      delayedOverview.queued===1 && delayedOverview.first && !delayedOverview.beforeSecond &&
      delayedOverview.drained===1 && delayedOverview.requests===2 && delayedOverview.remaining===0 &&
      delayedOverview.emits===3 && await noObserver.locator(widgetSelector+' '+valueSelector).textContent()==='2\u00a0100');
    const delayedReplacement=await noObserver.evaluate(()=>{
      const t=__postbattleTest,start=t.frameRequests,events=t.emits;
      t.model.rating=JSON.stringify({state:'ready',value:2500});t.emit();t.emit();
      const first=t.frames.shift();if(first)first(0);
      const next=t.makeRow();t.row.replaceWith(next);t.row=next;t.nativeCells=[...next.children];
      const beforeSecond=next.querySelector('#grz-postbattle-wn8');
      const drained=t.drainFrames(8);t.settledFrameRequests=t.frameRequests;
      return {first:!!first,beforeSecond:!!beforeSecond,drained,requests:t.frameRequests-start,
        remaining:t.frames.length,events:t.emits-events};
    });
    check('A native row committed after its data event reattaches without MutationObserver or a later notification',
      delayedReplacement.first && !delayedReplacement.beforeSecond && delayedReplacement.drained===1 &&
      delayedReplacement.requests===2 && delayedReplacement.remaining===0 && delayedReplacement.events===2 &&
      await noObserver.locator(widgetSelector).evaluate(node=>{
        const t=__postbattleTest;return node.parentNode===t.row && t.row.children.length===8 &&
          t.nativeCells.every((cell,index)=>t.row.children[index]===cell);
      }) && await noObserver.locator(widgetSelector+' '+valueSelector).textContent()==='2\u00a0500');
    await noObserver.waitForTimeout(50);
    check('Deferred native placement exhausts its finite queue and does not start recurring frame polling',
      await noObserver.evaluate(()=>__postbattleTest.frames.length===0 &&
        __postbattleTest.frameRequests===__postbattleTest.settledFrameRequests));
    for(const observerThrows of ['construct','observe']) {
      const rejectedObserver=await open({observerThrows,holdFrames:true,anchor:false});
      const recovery=await rejectedObserver.evaluate(()=>{
        const t=__postbattleTest;t.drainFrames(8);
        t.model.rating=JSON.stringify({state:'ready',value:3100});t.emit();
        const first=t.frames.shift();if(first)first(0);
        t.addTable();const drained=t.drainFrames(8);
        return {first:!!first,drained,remaining:t.frames.length,active:t.activeCallbacks.size,
          dataCallbacks:(t.events['viewEnv.onDataChanged']||[]).length,
          partialObserversReleased:t.observers.every(owner=>owner.disconnected)};
      });
      check('Optional observer '+observerThrows+' failure preserves model-driven delayed placement',
        recovery.first && recovery.drained===1 && recovery.remaining===0 && recovery.active===1 &&
        recovery.dataCallbacks===1 && recovery.partialObserversReleased &&
        await rejectedObserver.locator(widgetSelector+' '+valueSelector).textContent()==='3\u00a0100');
    }
    const noObserverQueued=await open({noObserver:true,holdFrames:true});
    const noObserverTeardown=await noObserverQueued.evaluate(()=>{
      const t=__postbattleTest,pending=t.frames.length,requests=t.frameRequests;
      const retained=(t.events['viewEnv.onDataChanged']||[]).slice(),refresh=GRZPostBattleWn8.refresh;
      GRZPostBattleWn8.destroy();const drained=t.drainFrames(8);
      retained.forEach(callback=>callback());refresh();t.addTable();
      return {pending,drained,remaining:t.frames.length,requestsBefore:requests,requestsAfter:t.frameRequests,
        active:t.activeCallbacks.size,observers:t.observers.length,
        events:Object.values(t.events).every(callbacks=>callbacks.length===0)};
    });
    check('Observer-free queued placement and retained data/public callbacks remain inert after teardown',
      noObserverTeardown.pending===1 && noObserverTeardown.drained===1 && noObserverTeardown.remaining===0 &&
      noObserverTeardown.requestsBefore===noObserverTeardown.requestsAfter && noObserverTeardown.active===0 &&
      noObserverTeardown.observers===0 && noObserverTeardown.events && await noObserverQueued.locator(widgetSelector).count()===0);
    const queued=await open({holdFrames:true});
    await queued.waitForTimeout(20);
    await queued.evaluate(()=>{
      const t=__postbattleTest;GRZPostBattleWn8.destroy();
      while(t.frames.length)t.frames.shift()(0);
      t.observers.forEach(owner=>owner.callback([]));t.addTable();
    });
    await queued.waitForTimeout(20);
    check('Queued animation-frame work and retained observer callbacks stay inert after teardown',
      await queued.locator(widgetSelector).count()===0 && await queued.evaluate(()=>__postbattleTest.activeCallbacks.size===0));
    check('Post-battle fixtures raise no JavaScript errors'+(errors.length ? ': '+errors.join(' | ') : ''),errors.length===0);
  } finally {
    await Promise.all(pages.map(page=>page.close()));
  }
  reportCheck('Post-battle browser contracts'+(failures.length ? ': '+failures.join(' | ') : ''),failures.length===0);
};
