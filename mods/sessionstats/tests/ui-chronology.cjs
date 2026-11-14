/* Expanded group histories retain their selected date direction across pages. */
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let left=6;function next(){if(--left)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);}));
module.exports=async({browser,nativeHost,check})=>{
  const page=await nativeHost(browser,{initialViewport:{width:1900,height:1300},viewport:{width:1900,height:1300,scale:1}});
  try{
    for(const group of ['maps','vehicles'])for(const chronology of ['oldest','last_asc','first_desc','newest']){
      const ascending=['oldest','last_asc'].includes(chronology),ids=ascending?['early','late']:['late','early'];
      await page.evaluate(({group,chronology,ids})=>{
        const payload=JSON.parse(model.payload),scope=payload.scopes.launch,sample=scope[group][0];
        payload.account_key='synthetic-more-order-'+group+'-'+chronology;payload.window_size=[1200,1000];
        scope.period_id='synthetic-more-period';scope[group]=[{...sample,id:'chronology-group',name:'Synthetic history',
          battle_list:{page:0,pages:2,total:12,page_size:10,chronology,items:ids.map(id=>({id,name:id,map:id,
            started_at:id==='early'?100:200,outcome:'win',wn8:1000}))}}];
        scope.ordering[group]={metric:'off',statistic:'avg',direction:'desc',chronology};
        scope.pagination[group]={page:0,pages:1,page_size:40,total:1};
        delete scope.battle_history;model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      },{group,chronology,ids});await page.locator('#ss-group-'+group).click();await frames(page);
      const card=page.locator('[data-group-id="chronology-group"]');await card.locator('.ss-map-more-button').click();await frames(page);
      const visible=()=>card.locator('.ss-map-battle-row').evaluateAll(rows=>rows.map(row=>row.getAttribute('data-battle-id')));
      check('Expanded '+group+' history renders '+chronology+' in the same date direction',JSON.stringify(await visible())===JSON.stringify(ids));
      await card.locator('.ss-map-page-next').click();
      const request=await page.evaluate(()=>__grzCommands.filter(command=>/^(map|vehicle)_battles$/.test(command.action)).pop());
      check('Expanded '+group+' pagination carries the exact chronology identity '+chronology,
        request.page==='1'&&request.chronology===chronology&&request.period_id==='synthetic-more-period');
      await page.evaluate(({group,chronology,ids})=>{
        const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
        scope.battle_history={kind:group,id:'chronology-group',battle_list:{page:1,pages:2,total:12,page_size:10,
          chronology:chronology==='newest'?'oldest':'newest',items:[{id:'stale-history',name:'Stale',map:'Stale',started_at:999,outcome:'win',wn8:0}]}};
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      },{group,chronology,ids});await frames(page);
      check('A late '+group+' history reply from another chronology cannot replace cached rows '+chronology,
        JSON.stringify(await visible())===JSON.stringify(ids));
      await page.evaluate(({group,chronology})=>{
        const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
        scope.battle_history={kind:group,id:'chronology-group',battle_list:{page:1,pages:2,total:12,page_size:10,chronology,
          items:[{id:'final-'+chronology,name:'Final',map:'Final',started_at:300,outcome:'win',wn8:1000}]}};
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      },{group,chronology});await frames(page);
      check('The owned '+group+' page reply still replaces the history in '+chronology,
        JSON.stringify(await visible())===JSON.stringify(['final-'+chronology]));
    }
  }finally{await page.close();}
};
