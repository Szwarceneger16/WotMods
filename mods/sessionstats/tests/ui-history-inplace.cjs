/* History paging updates natural-height rows within the outer scroll area. */
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let remaining=6;
  function next(){if(--remaining)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}));
module.exports=async ({browser,nativeHost,check})=>{
  const page=await nativeHost(browser,{initialViewport:{width:1600,height:1200},viewport:{width:1600,height:1200,scale:1}});
  try {
    for(const group of ['maps','vehicles']) for(const width of [680,1100]) {
      await page.evaluate(({group,width})=>{
        const payload=JSON.parse(model.payload),scope=payload.scopes.launch,sample=scope[group][0];
        payload.account_key='synthetic-stable-history-'+group+'-'+width;payload.window_size=[width,950];
        scope.period_id='synthetic-stable-period-'+group;
        scope[group]=Array.from({length:8},(_,index)=>({...sample,id:'history-'+index,name:'Synthetic group '+index}));
        scope[group].forEach(item=>delete item.battle_list);
        scope.pagination[group]={page:0,pages:1,total:8,page_size:40};
        delete scope.battle_focus;
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      },{group,width});
      await page.locator('#ss-scope-launch').click();await page.locator('#ss-group-'+group).click();await frames(page);
      await page.locator('[data-group-id="history-0"] .ss-map-more-button').click();await frames(page);
      const historyPages=()=>page.evaluate(group=>__grzCommands.filter(item=>
        item.action===(group==='vehicles'?'vehicle_battles':'map_battles') &&
        (item.vehicle_id||item.map_id)==='history-0').map(item=>item.page),group);
      async function runTimeout(delay) {
        await page.evaluate(delay=>{
          const owner=[...__grzTimers.entries()].find(([,timer])=>timer.delay===delay);
          if(!owner) throw new Error('No owned history timer at '+delay+' ms');
          const [id,timer]=owner;
          if(delay===10000) window.__retiredHistoryTimer=timer.callback;
          __grzTimers.delete(id);timer.callback();
        },delay);
        await frames(page);
      }
      if(width===680) {
        const before=await historyPages();
        check('An expanded '+group+' card remount retires its original request before deferring the replacement',await page.evaluate(group=>{
          const card=document.querySelector('[data-group-id="history-0"]');
          const pending=[...__grzTimers.entries()].find(([,timer])=>timer.delay===10000);
          const commandCount=__grzCommands.length, payload=JSON.parse(model.payload);
          payload.appearance={...payload.appearance,panel_css:'/* Synthetic '+group+' history remount */'};
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
          const updated=document.querySelector('[data-group-id="history-0"]');
          return pending && updated!==card && updated.querySelector('.ss-map-more-button').getAttribute('aria-expanded')==='true' &&
            __grzCommands.length===commandCount && !__grzTimers.has(pending[0]);
        },group));
        await runTimeout(0);
        check('The remounted '+group+' card requests its initial page after rendering',JSON.stringify(await historyPages())===
          JSON.stringify([...before,'0']));
      }
      await page.evaluate(()=>{
        const card=document.querySelector('[data-group-id="history-0"]');
        window.__historyNodes={card,summary:document.getElementById('ss-summary'),more:card.querySelector('.ss-map-more-button'),
          panel:card.querySelector('.ss-map-battles'),body:card.querySelector('.ss-history-body'),
          previous:card.querySelector('.ss-map-page-previous'),next:card.querySelector('.ss-map-page-next')};
        __historyNodes.loadingHeight=__historyNodes.panel.getBoundingClientRect().height;
      });
      async function publish(pageNumber, revision=0, pages=2) {
        await page.evaluate(({group,pageNumber,revision,pages})=>{
          const payload=JSON.parse(model.payload),scope=payload.scopes.launch,item=scope[group][0];
          scope.history_navigation_revision=(scope.history_navigation_revision || 0)+1;
          payload.generated_at=(payload.generated_at || 0)+1;
          item.battle_list={page:pageNumber,pages,total:pages===3?23:13,page_size:10,
            items:Array.from({length:pageNumber===pages-1 ? 3 : 10},(_,index)=>({id:'history-battle-'+(pageNumber*10+index),
              name:'Synthetic vehicle '+('long name '.repeat(15))+index,
              map:'Synthetic map '+('long name '.repeat(15))+index,
              started_at:1794000000-index*600,outcome:'win',wn8:1700+revision+index}))};
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
        },{group,pageNumber,revision,pages});await frames(page);
      }
      if(width===680) {
        await runTimeout(10000);
        check('The initial '+group+' timeout replaces the loading indicator with Retry',await page.evaluate(()=>{
          const n=__historyNodes, loading=n.body.querySelector('.ss-map-empty'), retry=n.panel.querySelector('.ss-history-retry');
          return n.panel.getAttribute('aria-busy')==='false' && getComputedStyle(loading).display==='none' &&
            retry.getBoundingClientRect().height>0 && retry.parentNode.textContent==='Could not load this page.Retry';
        }));
        const before=await historyPages();
        await page.evaluate(()=>{const retry=__historyNodes.panel.querySelector('.ss-history-retry');retry.focus();retry.click();});
        check('Retry requests the same initial '+group+' page and keeps keyboard focus in the card',JSON.stringify(await historyPages())===
          JSON.stringify([...before,'0']) && await page.evaluate(()=>document.activeElement===__historyNodes.more));
      }
      await publish(0);
      check('Loaded '+group+' history expands the same panel to every battle at '+width+'rem',await page.evaluate(twoColumns=>{
        const n=__historyNodes,card=document.querySelector('[data-group-id="history-0"]');
        const rows=[...n.body.querySelectorAll('.ss-map-battle-row')], body=n.body.getBoundingClientRect();
        return card===n.card && n.panel===card.querySelector('.ss-map-battles') && n.body===card.querySelector('.ss-history-body') &&
          n.panel.getBoundingClientRect().height>n.loadingHeight && getComputedStyle(n.body).overflowY==='visible' &&
          card.classList.contains('ss-history-two-columns')===twoColumns && rows.length===10 &&
          rows.every(row=>row.getBoundingClientRect().bottom<=body.bottom+1);
      },width===1100));
      check('A native wheel event over an open '+group+' history scrolls the main panel at '+width+'rem',await page.evaluate(()=>{
        const n=__historyNodes,scroll=document.getElementById('ss-scroll');
        const previous=scroll.scrollTop;
        n.body.querySelector('.ss-map-battle-row').dispatchEvent(new WheelEvent('wheel',{bubbles:true,cancelable:true,deltaY:-1}));
        n.globalScroll=scroll.scrollTop;
        return n.globalScroll>previous && n.body.scrollTop===0;
      }));
      await publish(0,20);
      check('Refreshing '+group+' history preserves main scroll and controls',await page.evaluate(()=>{
        const n=__historyNodes,card=document.querySelector('[data-group-id="history-0"]');
        return card===n.card && n.previous===card.querySelector('.ss-map-page-previous') &&
          n.next===card.querySelector('.ss-map-page-next') && n.more===card.querySelector('.ss-map-more-button') &&
          n.body.scrollTop===0 && document.getElementById('ss-scroll').scrollTop===n.globalScroll;
      }));
      await page.evaluate(()=>{
        const n=__historyNodes;
        window.__retiredHistoryOpen=n.body.querySelector('.ss-map-battle-open').onclick;
        window.__earlierNestedPage=JSON.parse(model.payload);
        n.next.scrollIntoView({block:'center'});n.next.focus();n.next.click();
        n.nextTop=n.next.getBoundingClientRect().top;n.panelHeight=n.panel.getBoundingClientRect().height;
      });
      await publish(1);
      check('The shorter last '+group+' page keeps the visible pager in place and focuses Previous',await page.evaluate(()=>{
        const n=__historyNodes,card=document.querySelector('[data-group-id="history-0"]');
        return card===n.card && document.getElementById('ss-summary')===n.summary &&
          card.querySelector('.ss-map-page-next')===n.next && card.querySelector('.ss-map-page-previous')===n.previous &&
          n.body.querySelectorAll('.ss-map-battle-row').length===3 && n.next.disabled && !n.previous.disabled &&
          document.activeElement===n.previous && n.panel.getBoundingClientRect().height<n.panelHeight &&
          Math.abs(n.next.getBoundingClientRect().top-n.nextTop)<2;
      }));
      for (const partial of [true,false]) {
        check('A superseded '+group+' history page cannot rewind '+(partial?'an inline update':'a full redraw'),
          await page.evaluate(({group,partial})=>{
            const stale=JSON.parse(JSON.stringify(__earlierNestedPage)), scope=stale.scopes.launch;
            // Wall time alone cannot establish navigation order. Include a
            // case where the old patch would otherwise cause a full redraw.
            stale.generated_at=JSON.parse(model.payload).generated_at+1;
            if (!partial) {
              stale.appearance={...stale.appearance,panel_css:'/* stale history */'};
              const row=scope[group][0];
              scope.battle_history={kind:group,id:row.id,battle_list:row.battle_list};
              delete row.battle_list;
            }
            GRZSessionStats.update(stale);
            const n=__historyNodes;
            return n.card.isConnected && n.next.disabled && !n.previous.disabled &&
              n.body.firstChild.getAttribute('data-battle-id')==='history-battle-10';
          },{group,partial}));
      }
      check('Retired '+group+' history row actions cannot navigate after a page replacement',await page.evaluate(()=>{
        const before=__grzCommands.filter(item=>item.action==='battle_select').length;
        __retiredHistoryOpen();return __grzCommands.filter(item=>item.action==='battle_select').length===before;
      }));
      await page.evaluate(()=>{__historyNodes.previous.click();});
      check('The persistent '+group+' Previous control uses the newest page number',await page.evaluate(group=>{
        const action=group==='vehicles'?'vehicle_battles':'map_battles';
        return __grzCommands.filter(item=>item.action===action).pop().page==='0';
      },group));
      await publish(0);
      if(width===680) {
        await publish(1,0,3);
        await page.evaluate(()=>{
          const n=__historyNodes;
          n.visibleRow=n.body.firstChild;n.next.focus();n.next.click();
        });
        await runTimeout(10000);
        check('A later '+group+' timeout preserves the displayed row, pager and active control',await page.evaluate(()=>{
          const n=__historyNodes;
          return n.body.firstChild===n.visibleRow && !n.previous.disabled && !n.next.disabled &&
            document.activeElement===n.next && n.panel.getAttribute('aria-busy')==='false' &&
            n.panel.querySelector('.ss-history-retry').getBoundingClientRect().height>0;
        }));
        await page.evaluate(()=>{__historyNodes.previous.click();__retiredHistoryTimer();});
        await publish(2,0,3);
        check('A late '+group+' reply for a different page leaves the newer request and displayed row intact',await page.evaluate(()=>{
          const n=__historyNodes;
          return n.panel.getAttribute('aria-busy')==='true' && n.body.firstChild===n.visibleRow;
        }) && (await historyPages()).at(-1)==='0');
        await runTimeout(10000);
        await page.evaluate(()=>__historyNodes.next.click());
        check('The stale '+group+' reply did not change the base page used by Next',(await historyPages()).at(-1)==='2');
        await publish(2,0,3);
        await page.evaluate(()=>__historyNodes.previous.click());
        await runTimeout(10000);
        await page.evaluate(()=>__historyNodes.panel.querySelector('.ss-history-retry').focus());
        await publish(1,0,3);
        check('A matching '+group+' reply arriving after timeout still recovers the panel',await page.evaluate(()=>{
          const n=__historyNodes, retry=n.panel.querySelector('.ss-history-retry');
          return n.panel.getAttribute('aria-busy')==='false' && retry.getBoundingClientRect().height===0 &&
            document.activeElement===n.previous && n.body.firstChild.getAttribute('data-battle-id')==='history-battle-10';
        }));
        check('Collapsing '+group+' history retires an outstanding request timer',await page.evaluate(()=>{
          const n=__historyNodes;n.next.click();
          const owner=[...__grzTimers.entries()].find(([,timer])=>timer.delay===10000);
          n.more.click();
          if(owner) owner[1].callback();
          return owner && !__grzTimers.has(owner[0]) && n.panel.getAttribute('aria-busy')==='false' &&
            n.more.getAttribute('aria-expanded')==='false';
        }));
      }
      await page.evaluate(()=>{
        window.__retiredHistoryUpdate=__historyNodes.card._ssHistoryUpdate;
        const payload=JSON.parse(model.payload);payload.account_key+='-replaced';
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      });await frames(page);
      check('A retired '+group+' history setter rejects a replacement account',await page.evaluate(()=>
        __retiredHistoryUpdate({id:'history-0',battle_list:{page:0,pages:1,items:[]}})===false));
      for(const failure of ['action','snapshot','bridge']) {
        const status=await page.evaluate(failure=>{
          window.__historyRecoveryStatus=document.getElementById('ss-status').textContent;
          window.__historyRecoveryPayload=model.payload;
          const command=model.onAction,fallback=GRZSessionStats.onAction;
          try {
            if(failure==='snapshot')GRZSessionStats.update('{synthetic invalid JSON');
            else {
              model.onAction=failure==='action' ? function(){throw Error('Synthetic action failure');} : undefined;
              GRZSessionStats.onAction=undefined;document.getElementById('ss-refresh').onclick();
            }
          } finally {model.onAction=command;GRZSessionStats.onAction=fallback;}
          return {before:__historyRecoveryStatus,error:document.getElementById('ss-status').textContent,
            samePayload:model.payload===__historyRecoveryPayload};
        },failure);
        const errors={action:'Could not complete the action. Try again.',snapshot:'Could not read statistics data.',bridge:'No connection to the game.'};
        check('The '+group+' '+failure+' recovery scenario displays its real error without replacing data: '+JSON.stringify(status),
          status.samePayload && status.error===errors[failure] && status.error!==status.before);
        await page.evaluate(()=>{model.payload=__historyRecoveryPayload;__grzEvents['viewEnv.onDataChanged']();});await frames(page);
        check('An identical healthy '+group+' payload clears the recovered '+failure+' error',
          await page.locator('#ss-status').textContent()===status.before && await page.locator('#ss-groups .ss-group').count()===8);
      }
    }
  } finally {await page.close();}
};
