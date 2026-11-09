/* History paging updates one fixed viewport without replacing the surrounding UI. */
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let remaining=6;
  function next(){if(--remaining)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}));
module.exports=async ({browser,nativeHost,check})=>{
  const page=await nativeHost(browser,{initialViewport:{width:1600,height:1200},viewport:{width:1600,height:1200,scale:1}});
  try {
    for(const group of ['maps','vehicles']) {
      await page.evaluate(group=>{
        const payload=JSON.parse(model.payload),scope=payload.scopes.launch,sample=scope[group][0];
        payload.account_key='synthetic-stable-history-'+group;payload.window_size=[1100,950];
        scope.period_id='synthetic-stable-period-'+group;
        scope[group]=Array.from({length:8},(_,index)=>({...sample,id:'history-'+index,name:'Synthetic group '+index}));
        scope[group].forEach(item=>delete item.battle_list);
        scope.pagination[group]={page:0,pages:1,total:8,page_size:40};
        delete scope.battle_focus;
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      },group);
      await page.locator('#ss-scope-launch').click();await page.locator('#ss-group-'+group).click();await frames(page);
      await page.locator('[data-group-id="history-0"] .ss-map-more-button').click();await frames(page);
      await page.evaluate(()=>{
        const card=document.querySelector('[data-group-id="history-0"]');
        window.__historyNodes={card,summary:document.getElementById('ss-summary'),more:card.querySelector('.ss-map-more-button'),
          panel:card.querySelector('.ss-map-battles'),body:card.querySelector('.ss-history-body'),
          previous:card.querySelector('.ss-map-page-previous'),next:card.querySelector('.ss-map-page-next'),
          neighbor:document.querySelector('[data-group-id="history-1"]')};
        __historyNodes.loadingHeight=__historyNodes.panel.getBoundingClientRect().height;
      });
      async function publish(pageNumber, revision=0) {
        await page.evaluate(({group,pageNumber,revision})=>{
          const payload=JSON.parse(model.payload),item=payload.scopes.launch[group][0];
          payload.generated_at=(payload.generated_at || 0)+1;
          item.battle_list={page:pageNumber,pages:2,total:13,page_size:10,
            items:Array.from({length:pageNumber ? 3 : 10},(_,index)=>({id:'history-battle-'+(pageNumber*10+index),
              name:'Synthetic vehicle '+('long name '.repeat(15))+index,
              map:'Synthetic map '+('long name '.repeat(15))+index,
              started_at:1794000000-index*600,outcome:'win',wn8:1700+revision+index}))};
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
        },{group,pageNumber,revision});await frames(page);
      }
      await publish(0);
      check('Loading and full '+group+' history use the same nodes and reserved panel height',await page.evaluate(()=>{
        const n=__historyNodes,card=document.querySelector('[data-group-id="history-0"]');
        return card===n.card && n.panel===card.querySelector('.ss-map-battles') && n.body===card.querySelector('.ss-history-body') &&
          Math.abs(n.panel.getBoundingClientRect().height-n.loadingHeight)<1 && n.body.getBoundingClientRect().height===460 &&
          n.body.querySelectorAll('.ss-map-battle-row').length===10;
      }));
      await page.evaluate(()=>{
        const n=__historyNodes,scroll=document.getElementById('ss-scroll');
        n.body.scrollTop=Math.min(80,n.body.scrollHeight-n.body.clientHeight);
        scroll.scrollTop=Math.min(200,scroll.scrollHeight-scroll.clientHeight);
        n.localScroll=n.body.scrollTop;n.globalScroll=scroll.scrollTop;
      });
      await publish(0,20);
      check('Refreshing '+group+' history preserves local and parent scroll without replacing its controls',await page.evaluate(()=>{
        const n=__historyNodes,card=document.querySelector('[data-group-id="history-0"]');
        return card===n.card && n.previous===card.querySelector('.ss-map-page-previous') &&
          n.next===card.querySelector('.ss-map-page-next') && n.more===card.querySelector('.ss-map-more-button') &&
          n.body.scrollTop===n.localScroll && document.getElementById('ss-scroll').scrollTop===n.globalScroll;
      }));
      await page.evaluate(()=>{
        const n=__historyNodes,scroll=document.getElementById('ss-scroll');
        window.__retiredHistoryOpen=n.body.querySelector('.ss-map-battle-open').onclick;
        n.next.focus();n.next.click();n.beforePageScroll=scroll.scrollTop;
        n.neighborTop=n.neighbor.getBoundingClientRect().top;n.panelHeight=n.panel.getBoundingClientRect().height;
      });
      await publish(1);
      check('The partial last '+group+' page keeps the whole UI stable and focuses the enabled previous control',await page.evaluate(()=>{
        const n=__historyNodes,card=document.querySelector('[data-group-id="history-0"]');
        return card===n.card && document.getElementById('ss-summary')===n.summary &&
          card.querySelector('.ss-map-page-next')===n.next && card.querySelector('.ss-map-page-previous')===n.previous &&
          n.body.querySelectorAll('.ss-map-battle-row').length===3 && n.next.disabled && !n.previous.disabled &&
          document.activeElement===n.previous && document.getElementById('ss-scroll').scrollTop===n.beforePageScroll &&
          Math.abs(n.panel.getBoundingClientRect().height-n.panelHeight)<1 &&
          Math.abs(n.neighbor.getBoundingClientRect().top-n.neighborTop)<1;
      }));
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
      await page.evaluate(()=>{
        window.__retiredHistoryUpdate=__historyNodes.card._ssHistoryUpdate;
        const payload=JSON.parse(model.payload);payload.account_key+='-replaced';
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      });await frames(page);
      check('A retired '+group+' history setter rejects a replacement account',await page.evaluate(()=>
        __retiredHistoryUpdate({id:'history-0',battle_list:{page:0,pages:1,items:[]}})===false));
    }
  } finally {await page.close();}
};
