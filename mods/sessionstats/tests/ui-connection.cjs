/* Connection lifecycle regressions, executed by the existing panel suite. */
module.exports = async function ({browser,nativeHost,check}) {
  for(const rejectEngine of ['viewEnv.onDataChanged','self.onScaleUpdated']) {
    for(const rejectAfterRegister of [false,true]) {
      const failed=await nativeHost(browser,{pendingEngine:true,rejectEngine,rejectAfterRegister,teardown:'all'});
      await failed.evaluate(async()=>{__grzResolveEngine();await Promise.resolve();await Promise.resolve();});
      check('Rejected engine subscription leaves the panel unbound ('+rejectEngine+', partial='+rejectAfterRegister+')',
        await failed.evaluate(()=>!GRZSessionStats.getState().nativeBound && __grzHelperCalls.callback===0));
      await failed.evaluate(async()=>{__grzRejectEngine=false;await __grzRunRetry();});
      await failed.waitForFunction(()=>GRZSessionStats.getState().nativeBound && __grzCommands.some(x=>x.action==='resize'));
      check('A scheduled retry after normal load renders the initial model ('+rejectEngine+', partial='+rejectAfterRegister+')',
        await failed.evaluate(()=>document.querySelector('#ss-summary .ss-kpi-value').textContent==='16' && __grzHelperCalls.callback===1 && __grzLifecycleEvents.join(',')==='dom,load'));
      check('Partially retained callbacks stay inert after a successful replacement ('+rejectEngine+', partial='+rejectAfterRegister+')',
        await failed.evaluate(()=>{
          const payload=JSON.parse(model.payload);
          Object.assign(payload.scopes.launch.summary,{battles:0,observed_battles:0,missing_results:0,partial_results:0});
          model.payload=JSON.stringify(payload);
          const count=__grzCommands.length;
          __grzStaleCallbacks.forEach(fn=>fn());
          return __grzCommands.length===count && document.querySelector('#ss-summary .ss-kpi-value').textContent==='16';
        }));
      await failed.evaluate(()=>__grzEvents['viewEnv.onDataChanged']());
      check('The recovered engine subscription receives subsequent model changes ('+rejectEngine+', partial='+rejectAfterRegister+')',
        await failed.evaluate(()=>document.querySelector('#ss-summary .ss-kpi-value').textContent==='0'));
      await failed.close();
    }
  }
  const readyRetry=await nativeHost(browser,{pendingEngine:true});
  await readyRetry.evaluate(async()=>{__grzRejectReady(new Error('Readiness rejected'));await Promise.resolve();await Promise.resolve();});
  check('Rejected panel readiness is handled and leaves the panel unbound',
    await readyRetry.evaluate(()=>!GRZSessionStats.getState().nativeBound && __grzHelperCalls.callback===0));
  await readyRetry.evaluate(async()=>{engine.whenReady=Promise.resolve();await __grzRunRetry();});
  await readyRetry.waitForFunction(()=>GRZSessionStats.getState().nativeBound);
  check('A fresh readiness promise can reconnect after rejection',
    await readyRetry.evaluate(()=>document.querySelector('#ss-summary .ss-kpi-value').textContent==='16'));
  await readyRetry.close();
  for(const domSignalOnRegister of [false,true]) {
    const rejectedDom=await nativeHost(browser,{pendingEngine:true,pendingDom:true,
      rejectEngine:'self.onDomBuilt',rejectAfterRegister:true,teardown:'all',domSignalOnRegister});
    await rejectedDom.evaluate(async()=>{__grzResolveEngine();await Promise.resolve();await Promise.resolve();});
    check('Rejected DOM registration cannot commit a synchronous or retained notification (sync='+domSignalOnRegister+')',
      await rejectedDom.evaluate(()=>!GRZSessionStats.getState().nativeBound && __grzHelperCalls.callback===0));
    await rejectedDom.evaluate(async()=>{
      window.__grzRejectedDom=__grzEvents['self.onDomBuilt'];
      window.engine=Object.assign({},engine,{whenReady:new Promise(resolve=>{window.__grzReplacementReady=resolve;})});
      window.viewEnv=Object.assign({},viewEnv);
      __grzRejectEngine=false;window.isDomBuilt=true;
      await __grzRunRetry();
      __grzRejectedDom();
    });
    check('A retained rejected DOM callback cannot bind before replacement readiness (sync='+domSignalOnRegister+')',
      await rejectedDom.evaluate(()=>!GRZSessionStats.getState().nativeBound && __grzHelperCalls.callback===0));
    await rejectedDom.evaluate(async()=>{__grzReplacementReady();await Promise.resolve();await Promise.resolve();});
    await rejectedDom.waitForFunction(()=>GRZSessionStats.getState().nativeBound);
    check('Only the ready replacement owns model subscriptions (sync='+domSignalOnRegister+')',await rejectedDom.evaluate(()=>{
      const calls=__grzEngineOn.length, registrations=__grzHelperCalls.callback, commands=__grzCommands.length;
      __grzRejectedDom();
      return calls===__grzEngineOn.length && registrations===1 && __grzHelperCalls.callback===1 && commands===__grzCommands.length;
    }));
    await rejectedDom.close();
  }
  const lateAutomatic=await nativeHost(browser,{pendingEngine:true,realTimers:true,
    rejectEngine:'self.onScaleUpdated',rejectOnce:true,rejectAfterRegister:true,teardown:'all'});
  await lateAutomatic.evaluate(()=>__grzResolveEngine());
  await lateAutomatic.waitForFunction(()=>GRZSessionStats.getState().nativeBound);
  check('A real timer recovers a late transient subscription failure without another load event',
    await lateAutomatic.evaluate(()=>__grzRejectedCalls===1 && __grzHelperCalls.callback===1 && __grzLifecycleEvents.join(',')==='dom,load'));
  await lateAutomatic.close();

  const backoff=await nativeHost(browser,{pendingEngine:true,rejectEngine:'viewEnv.onDataChanged',teardown:'all',timerCleanupFailure:true});
  await backoff.evaluate(async()=>{__grzResolveEngine();await Promise.resolve();await Promise.resolve();for(let i=0;i<7;i++)await __grzRunRetry();});
  check('Persistent failures keep one retry with capped exponential backoff',await backoff.evaluate(()=>
    __grzTimers.size===1 && __grzRetryDelays.join(',')==='100,200,400,800,1600,2000,2000,2000' && !GRZSessionStats.getState().nativeBound));
  check('Destroy invalidates a queued retry even when native timer cancellation throws',await backoff.evaluate(()=>{
    const retry=__grzTimers.values().next().value.callback, count=__grzEngineOn.length;
    GRZSessionStats.destroy();retry();
    return __grzEngineOn.length===count && __grzCancelledTimers.length===1 && !GRZSessionStats.getState().nativeBound;
  }));
  await backoff.close();

  const awaiting=await nativeHost(browser,{pendingEngine:true,pendingDom:true});
  await awaiting.evaluate(async()=>{for(let i=0;i<3;i++)await __grzRunRetry();});
  check('Retry ticks never attach duplicate handlers to the same unresolved readiness promise',
    await awaiting.evaluate(()=>__grzReadySubscriptions===1 && __grzEngineOn.length===0 && __grzTimers.size===1));
  await awaiting.evaluate(async()=>{
    window.__grzOriginalEngine=engine;
    window.engine=Object.assign({},engine,{whenReady:new Promise((resolve,reject)=>{
      window.__grzNewReady=resolve;window.__grzNewReject=reject;
    })});
    await __grzRunRetry();__grzResolveEngine();await Promise.resolve();await Promise.resolve();
  });
  check('Old readiness resolution cannot subscribe against a replacement bridge',
    await awaiting.evaluate(()=>!GRZSessionStats.getState().nativeBound && __grzEngineOn.length===0));
  await awaiting.evaluate(async()=>{__grzNewReady();await Promise.resolve();await Promise.resolve();});
  check('Replacement readiness installs exactly one current DOM callback',
    await awaiting.evaluate(()=>__grzEngineOn.join(',')==='self.onDomBuilt'));
  await awaiting.evaluate(async()=>{window.isDomBuilt=true;await __grzRunRetry();});
  await awaiting.waitForFunction(()=>GRZSessionStats.getState().nativeBound);
  check('A missed DOM event recovers from the native readiness flag on a scheduled check',
    await awaiting.evaluate(()=>__grzHelperCalls.callback===1 && __grzEngineOff.join(',')==='self.onDomBuilt'));
  await awaiting.close();

  const optionalRetry=await nativeHost(browser,{callback:'throw-once'});
  await optionalRetry.evaluate(async()=>{await __grzRunRetry();await __grzRunRetry();});
  check('Optional model registration recovers automatically without a native update event',
    await optionalRetry.evaluate(()=>__grzHelperCalls.callback===2 && __grzEngineOn.length===2));
  await optionalRetry.close();

  const absent=await nativeHost(browser,{absentBridge:true});
  check('An absent bridge keeps one pending retry after the document has loaded',
    await absent.evaluate(()=>__grzTimers.size===1 && __grzEngineOn.length===0 && __grzLifecycleEvents.join(',')==='dom,load'));
  await absent.evaluate(async()=>{Object.assign(window,__grzSavedBridge);await __grzRunRetry();});
  await absent.waitForFunction(()=>GRZSessionStats.getState().nativeBound);
  check('A bridge that appears later is discovered without another document event',
    await absent.evaluate(()=>__grzHelperCalls.callback===1));
  await absent.close();

  const replacement=await nativeHost(browser,{});
  await replacement.evaluate(async()=>{
    window.__grzOriginalRow=document.querySelector('#ss-groups .ss-group');
    for(let i=0;i<3;i++)await __grzRunRetry();
  });
  check('Successful connection checks do not render again or duplicate subscriptions',
    await replacement.evaluate(()=>__grzOriginalRow===document.querySelector('#ss-groups .ss-group') &&
      __grzEngineOn.length===2 && __grzHelperCalls.callback===1 && __grzTimers.size===1));
  await replacement.evaluate(async()=>{
    window.__grzOldData=__grzEvents['viewEnv.onDataChanged'];
    window.__grzOldScale=__grzEvents['self.onScaleUpdated'];
    window.__grzResizeCount=__grzCommands.filter(x=>x.action==='resize').length;
    window.engine=Object.assign({},engine,{whenReady:Promise.resolve()});
    window.viewEnv=Object.assign({},viewEnv);
    await __grzRunRetry();
  });
  await replacement.waitForFunction(()=>__grzCommands.filter(x=>x.action==='resize').length>__grzResizeCount);
  check('Replacing an already-bound bridge rebinds and sends fresh surface dimensions',
    await replacement.evaluate(()=>__grzHelperCalls.callback===2 && __grzEngineOn.length===4 && __grzRemovedCallbacks.join(',')==='71'));
  check('The previous bridge cannot trigger updates or viewport commands after replacement',await replacement.evaluate(()=>{
    const count=__grzCommands.length;__grzOldData();__grzOldScale();return __grzCommands.length===count;
  }));
  await replacement.close();

  const synchronousFailure=await nativeHost(browser,{pendingEngine:true});
  await synchronousFailure.evaluate(async()=>{
    window.engine=Object.assign({},engine,{whenReady:{then(){throw new TypeError('Readiness API unavailable');}}});
    await __grzRunRetry();
  });
  check('A synchronous readiness-API failure remains unbound with exactly one retry',
    await synchronousFailure.evaluate(()=>!GRZSessionStats.getState().nativeBound && __grzTimers.size===1));
  await synchronousFailure.evaluate(async()=>{engine.whenReady=Promise.resolve();await __grzRunRetry();});
  await synchronousFailure.waitForFunction(()=>GRZSessionStats.getState().nativeBound);
  await synchronousFailure.evaluate(async()=>{__grzRejectReady(new Error('Old readiness rejection'));await Promise.resolve();await Promise.resolve();});
  check('A delayed rejection from the old attempt cannot invalidate its connected replacement',
    await synchronousFailure.evaluate(()=>GRZSessionStats.getState().nativeBound && __grzHelperCalls.callback===1));
  await synchronousFailure.close();

  const disposeDuringRegistration=await nativeHost(browser,{pendingEngine:true});
  await disposeDuringRegistration.evaluate(async()=>{
    const original=viewEnv.addDataChangedCallback;
    viewEnv.addDataChangedCallback=function(){const id=original.apply(this,arguments);GRZSessionStats.destroy();return id;};
    __grzResolveEngine();await Promise.resolve();await Promise.resolve();
  });
  check('Destruction during synchronous model registration removes the returned callback from its original view',
    await disposeDuringRegistration.evaluate(()=>!GRZSessionStats.getState().nativeBound && __grzRemovedCallbacks.join(',')==='71' && __grzTimers.size===0));
  await disposeDuringRegistration.close();

  const retainedControls=await nativeHost(browser,{});
  const retained=await retainedControls.evaluate(()=>{
    document.getElementById('ss-scope-manual').onclick();
    document.getElementById('ss-reset').onclick();
    const confirm=document.getElementById('ss-reset-confirm').onclick;
    const refresh=document.getElementById('ss-refresh').onclick;
    const close=document.getElementById('ss-close').onclick;
    GRZSessionStats.destroy();
    const count=__grzCommands.length;
    confirm();refresh();close();close();
    const escape=new KeyboardEvent('keydown',{key:'Escape',cancelable:true,bubbles:true});
    document.dispatchEvent(escape);
    const nativeInert=__grzCommands.length===count && !escape.defaultPrevented;
    window.model=null;
    const fallback=[];
    GRZSessionStats.onAction=args=>fallback.push(args);
    refresh();close();
    return {nativeInert,fallbackInert:fallback.length===0};
  });
  check('Retained panel controls cannot reset, refresh or close native models after destroy; Escape returns to the host',retained.nativeInert);
  check('Retained panel controls cannot dispatch to a preview/replacement fallback after destroy',retained.fallbackInert);
  await retainedControls.close();
};
