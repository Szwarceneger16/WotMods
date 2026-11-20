/* Each wrapped row centers its visible controls; pinning survives late native frames. */
const fs=require('fs'),path=require('path');
const frames=(page,count=6)=>page.evaluate(count=>new Promise(resolve=>{
  function next(){if(--count)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}),count);
module.exports=async({browser,nativeHost,check})=>{
  await require('./ui-pinned-raf.cjs')({browser,nativeHost,check});
  await require('./ui-filter-wide-center.cjs')({browser,nativeHost,check});
  require('./ui-pinned-filters.cjs').assertPinnedFilterSource();
  check('Actual-source pinning survives mixed scroll frames without learning a translated origin',true);
  const catalogs=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const scaleResults=await Promise.allSettled([1,2].map(async scale=>{
    const page=await nativeHost(browser,{initialViewport:{width:3840,height:2400},viewport:{width:3840,height:2400,scale}});
    try{
      const rowBaselines=new Map();
      for(const [language,messages]of Object.entries(catalogs))for(const width of [365,550,700,780,845,846,912])
        for(const group of width===780?['vehicles','maps','tiers','battles']:['vehicles','battles'])
          for(const metric of group==='battles'?['off','xp_base']:['off','win_rate','xp_base']){
          await page.evaluate(({scale,language,messages,width,group,metric})=>{
            const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
            payload.account_key='synthetic-filter-position-'+scale+'-'+language;
            payload.localization={language,messages};payload.window_size=[width,850];
            payload.viewport={width:width<625?width*scale+20:3840,height:2400,scale};
            payload.appearance={window_settings:{background_transparency:0,maximized:false,restored_width:width,restored_height:850}};
            scope.ordering[group]={metric,statistic:'avg',direction:'desc',chronology:'newest'};
            model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();document.getElementById('ss-group-'+group).onclick();
          },{scale,language,messages,width,group,metric});await frames(page);
          const rows=await page.evaluate(()=>{
            const bar=document.getElementById('ss-list-controls'),box=bar.getBoundingClientRect(),rows=[];
            const frame=document.getElementById('ss-sorting'),field=frame.querySelector('.ss-sort-statistic');
            for(const child of bar.children){
              if(child.id==='ss-filter-loading')continue;
              const rect=child.getBoundingClientRect();if(rect.width<=0||rect.height<=0)continue;
              const controls=child.id==='ss-sorting'?[...child.querySelectorAll('[role=combobox]')].map(node=>node.getBoundingClientRect()).filter(rect=>rect.width>0):[rect];
              const left=Math.min(...controls.map(rect=>rect.left)),right=Math.max(...controls.map(rect=>rect.right));
              let row=rows.find(row=>Math.abs(row.bottom-rect.bottom)<=1);if(!row){row={bottom:rect.bottom,left,right};rows.push(row);}
              row.left=Math.min(row.left,left);row.right=Math.max(row.right,right);
            }
            return {mode:bar.getAttribute('data-filter-layout'),width:Number(bar.getAttribute('data-filter-width')),
              center:box.left+box.width/2,height:box.height,sortingWidth:frame.getBoundingClientRect().width,statisticWidth:field.getBoundingClientRect().width,
              rows:rows.map(row=>({...row,center:(row.left+row.right)/2}))};
          });
          const hasStatistic=group!=='battles'&&metric!=='win_rate';
          const expected=hasStatistic?294:width===365?235:229;
          const key=[language,width,group].join('/');
          if(!rowBaselines.has(key))rowBaselines.set(key,rows);
          const baseline=rowBaselines.get(key);
          check('Wrapped controls compact and center in '+language+' '+group+'/'+metric+' '+width+'px at '+scale+'x: '+JSON.stringify(rows),
            rows.mode==='wrapped'&&rows.width===width-38&&rows.rows.length>0&&rows.rows.every(row=>Math.abs(row.center-rows.center)<=4*scale)&&
            Math.abs(rows.sortingWidth/scale-expected)<=0.5&&(rows.statisticWidth>0)===hasStatistic);
          check('Only the available width changes the number of filter rows '+key+'/'+metric+'/'+scale+'x',
            rows.rows.length===baseline.rows.length&&Math.abs(rows.height-baseline.height)<=1&&
            (width>=846?rows.rows.length===1:rows.rows.length>=2));
        }
      await page.evaluate(scale=>{
        const payload=JSON.parse(model.payload),scope=payload.scopes.launch,sample=scope.vehicles[0];
        payload.account_key='synthetic-fast-pin-'+scale;payload.window_size=[700,1000];
        payload.appearance={window_settings:{background_transparency:0,maximized:false,restored_width:700,restored_height:1000}};
        scope.period_id='synthetic-fast-pin';scope.data_revision=1;
        scope.vehicles=Array.from({length:40},(_,index)=>({...sample,id:'synthetic-fast-pin-'+index}));
        scope.pagination.vehicles={page:0,pages:1,total:40,page_size:40};
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();document.getElementById('ss-group-vehicles').onclick();
        window.__pinCards=[...document.querySelectorAll('#ss-groups .ss-group')];
      },scale);await frames(page);
      await page.evaluate(scale=>{
        const scroll=document.getElementById('ss-scroll');scroll.scrollTop=700*scale;scroll.dispatchEvent(new Event('scroll'));
      },scale);await frames(page);
      const initial=await page.evaluate(()=>{const a=document.getElementById('ss-filter-panel').getBoundingClientRect(),b=document.getElementById('ss-scroll').getBoundingClientRect();return a.top-b.top;});
      check('The filter pins to the top before a fast native scroll at '+scale+'x',Math.abs(initial)<=scale);
      await page.evaluate(async scale=>{
        const scroll=document.getElementById('ss-scroll'),descriptor=Object.getOwnPropertyDescriptor(Element.prototype,'scrollTop');
        descriptor.set.call(scroll,1200*scale);window.__pinLateGetter=900*scale;
        Object.defineProperty(scroll,'scrollTop',{configurable:true,get(){return __pinLateGetter;},set(value){descriptor.set.call(scroll,value);}});
        scroll.dispatchEvent(new Event('scroll'));window.dispatchEvent(new Event('resize'));
        // Release the stale getter after three browser frames, even if the
        // test host is busy and takes longer to send another browser command.
        await new Promise(resolve=>{let remaining=3;function next(){if(--remaining)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);});
        __pinLateGetter=descriptor.get.call(scroll);
      },scale);
      await frames(page,12);
      const pinned=await page.evaluate(()=>{
        const scroll=document.getElementById('ss-scroll'),box=document.getElementById('ss-filter-panel').getBoundingClientRect(),viewport=scroll.getBoundingClientRect();
        delete scroll.scrollTop;
        return {delta:box.top-viewport.top,top:scroll.scrollTop,
          sameCards:__pinCards.length===document.querySelectorAll('#ss-groups .ss-group').length&&__pinCards.every(node=>node.isConnected)};
      });
      check('A late native scroll getter settles at the top without another input or rebuilding cards at '+scale+'x: '+JSON.stringify(pinned),
        Math.abs(pinned.delta)<=scale&&Math.abs(pinned.top-1200*scale)<=scale&&pinned.sameCards);
    }finally{await page.close();}
  }));
  const rejectedScale=scaleResults.find(result=>result.status==='rejected');
  if(rejectedScale)throw rejectedScale.reason;
};
