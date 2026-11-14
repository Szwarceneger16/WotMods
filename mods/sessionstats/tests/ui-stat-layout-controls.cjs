/* Statistic text is centered as one readable block; table rows share the finance height. */
const frames=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
module.exports=async({browser,nativeHost,check})=>{
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:3840,height:2560},viewport:{width:3840,height:2560,scale}});
    let sequence=0;
    try{
      await page.evaluate(scale=>{
        const payload=JSON.parse(model.payload),scope=payload.scopes.launch,item=scope.maps[0],stats=item.stats;
        payload.account_key='synthetic-stat-layout-'+scale;payload.window_size=[1800,1100];
        payload.localization={language:'en',messages:{}};
        item.id='synthetic-stat-layout';item.name='Synthetic map';stats.battles=stats.observed_battles=4;
        stats.wn8=750;stats.wn8_count=4;
        const ranges={xp_base:[100,250,400,1000],xp_received:[200,500,800,2000],battle_wn8:[300,750,1200,3000],
          credits_income_base:[10000,12500,15000,50000],credits_income_received:[15000,22500,30000,90000],
          credits_net_base:[6000,7500,9000,30000],credits_net_received:[11000,17500,24000,70000],
          credits_costs:[4000,5000,6000,20000]};
        item.extrema_battles={};
        for(const [metric,[min,avg,max,sum]]of Object.entries(ranges)){
          stats[metric]={count:4,min,avg,max,sum};item.extrema_battles[metric]={};
          for(const statistic of ['min','max'])item.extrema_battles[metric][statistic]={
            id:'synthetic-layout-'+metric+'-'+statistic,name:'Synthetic tank',map:'Synthetic map',started_at:1700000000,
            metric,statistic,value:stats[metric][statistic]};
        }
        stats.currencies={credits:{income_base:50000,income_base_count:4,net_base:30000,net_base_count:4,
          income:90000,income_count:4,costs:20000,costs_count:4,net:70000,net_count:4},
          bonds:{income:4,income_count:4,costs:0,costs_count:4,net:4,net_count:4},
          gold:{income:0,income_count:4,costs:0,costs_count:4,net:0,net_count:4}};
        scope.maps=[item];scope.pagination.maps={page:0,pages:1,total:1,page_size:40};
        scope.summary=JSON.parse(JSON.stringify(stats));
        window.__statLayoutFixture=JSON.parse(JSON.stringify(payload));
      },scale);
      async function publish(metric,statistic,options={}){
        await page.evaluate(({metric,statistic,options,sequence})=>{
          const payload=JSON.parse(JSON.stringify(__statLayoutFixture)),scope=payload.scopes.launch,item=scope.maps[0];
          scope.ordering.maps={metric,statistic,direction:'desc',chronology:'newest'};scope.data_revision='stat-layout-'+sequence;
          if(options.partial)item.stats.credits_net_received.count=2;
          if(options.pending)item.stats.observed_battles=6;
          if(options.noSources)delete item.extrema_battles;
          if(options.large){
            item.stats.observed_battles=6;
            const amount=-1234567890,stats=item.stats;
            stats.credits_net_received={count:4,min:amount,avg:amount,max:amount,sum:amount*4};
            stats.currencies.credits.income=61728440;stats.currencies.credits.costs=5000000000;
            stats.currencies.credits.net=amount*4;stats.currencies.credits.income_base=40000000;
            stats.currencies.credits.net_base=-4960000000;
            for(const statistic of ['min','max'])item.extrema_battles.credits_net_received[statistic].value=amount;
          }
          model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
        },{metric,statistic,options,sequence:++sequence});
        await page.locator('#ss-group-maps').click();await frames(page);
      }
      let baseline;
      for(const [metric,statistic,options]of [['credits_costs','max',{}],['credits_income_received','min',{}],
        ['credits_income_received','avg',{}],['credits_net_received','max',{partial:true}],['xp_received','sum',{}],
        ['xp_received','min',{}],['battle_wn8','avg',{}],['off','avg',{}]]){
        await publish(metric,statistic,options);
        const geometry=await page.locator('#ss-groups .ss-group').evaluate((card,scale)=>{
          const header=card.querySelector('.ss-group-header').getBoundingClientRect(),badge=card.querySelector('.ss-group-sort-value');
          const result={header:header.height/scale,card:card.getBoundingClientRect().height/scale,badge:null};
          if(badge){
            const caption=badge.querySelector('.ss-group-sort-caption'),value=badge.querySelector('.ss-group-sort-number'),box=badge.getBoundingClientRect();
            const ink=node=>{const range=document.createRange();range.selectNodeContents(node);return {box:range.getBoundingClientRect(),lines:[...range.getClientRects()]};};
            const title=ink(caption),number=ink(value),top=Math.min(title.box.top,number.box.top),bottom=Math.max(title.box.bottom,number.box.bottom);
            result.badge={height:box.height/scale,captionLines:title.lines.length,partial:caption.textContent.endsWith(' *'),
              captionHeight:caption.getBoundingClientRect().height/scale,valueHeight:value.getBoundingClientRect().height/scale,
              centered:Math.abs((top+bottom)/2-(box.top+box.bottom)/2)<=1.5*scale,
              separate:title.box.bottom<=number.box.top+scale,
              fits:title.lines.concat(number.lines).every(rect=>rect.left>=box.left-scale&&rect.right<=box.right+scale&&rect.top>=box.top-scale&&rect.bottom<=box.bottom+scale)};
          }
          return result;
        },scale);
        if(!baseline)baseline=geometry;
        check('Statistic choices retain the same card and headline height '+metric+'/'+statistic+'/'+scale,
          Math.abs(geometry.header-baseline.header)<=0.5&&Math.abs(geometry.card-baseline.card)<=0.5);
        if(geometry.badge){
          const b=geometry.badge;
          check('Statistic caption and value form one centered, unclipped 64px block '+metric+'/'+statistic+'/'+scale+': '+JSON.stringify(b),
            Math.abs(b.height-64)<=0.5&&b.centered&&b.separate&&b.fits&&b.valueHeight<=20&&b.captionHeight<=b.captionLines*13+1);
          if(metric==='credits_costs')check('A short statistic caption uses one centered line at '+scale,b.captionLines===1);
          if(metric==='credits_income_received')check('A longer statistic caption remains centered on two lines at '+scale,b.captionLines===2);
          if(options.partial)check('A partial statistic keeps its marker inside the centered block at '+scale,b.partial);
        }
      }
      await publish('credits_net_received','max',{large:true});
      const large=await page.locator('#ss-groups .ss-group-sort-value').evaluate((badge,scale)=>{
        const box=badge.getBoundingClientRect(),caption=badge.querySelector('.ss-group-sort-caption'),value=badge.querySelector('.ss-group-sort-number');
        const ink=node=>{const range=document.createRange();range.selectNodeContents(node);return [...range.getClientRects()];};
        const title=ink(caption),number=ink(value),text=title.concat(number),top=Math.min(...text.map(r=>r.top)),bottom=Math.max(...text.map(r=>r.bottom));
        return {captionLines:title.length,valueLines:number.length,partial:caption.textContent.endsWith(' *'),height:box.height/scale,
          value:value.textContent.replace(/\s/g,''),centered:Math.abs((top+bottom)/2-(box.top+box.bottom)/2)<=1.5*scale,
          fits:text.every(rect=>rect.left>=box.left-scale&&rect.right<=box.right+scale&&rect.top>=box.top-scale&&rect.bottom<=box.bottom+scale)};
      },scale);
      check('A signed ten-digit value and partial two-line caption remain fully visible in the 64px badge at '+scale+': '+JSON.stringify(large),
        large.captionLines===2&&large.valueLines===2&&large.partial&&large.value==='-1234567890'&&Math.abs(large.height-64)<=0.5&&large.centered&&large.fits);
      await publish('credits_costs','max');
      const table=await page.locator('#ss-groups .ss-group').evaluate((card,scale)=>{
        const performance=card.querySelector('.ss-performance'),economy=card.querySelector('.ss-economy'),
          left=performance.getBoundingClientRect(),right=economy.getBoundingClientRect(),rows=[...performance.querySelectorAll('.ss-metric-head,.ss-metric-row')].map(node=>node.getBoundingClientRect());
        const gaps=rows.slice(1).map((row,index)=>(row.top-rows[index].bottom)/scale),top=(rows[0].top-left.top)/scale,bottom=(left.bottom-rows[rows.length-1].bottom)/scale;
        return {fill:Math.abs(left.top-right.top)<=scale&&Math.abs(left.bottom-right.bottom)<=scale&&left.right<=right.left+scale,
          gaps,top,bottom,rows:rows.length,distributed:getComputedStyle(performance).justifyContent==='space-around',
          contained:rows.every(row=>row.top>=left.top-scale&&row.bottom<=left.bottom+scale&&row.left>=left.left-scale&&row.right<=left.right+scale),
          coverage:card.querySelectorAll('.ss-cell-coverage,.ss-count-coverage,.ss-wn8-coverage').length,height:card.getBoundingClientRect().height/scale};
      },scale);
      check('Performance fills the adjacent financial table height without overlapping columns at '+scale+': '+JSON.stringify(table),table.fill&&table.contained&&table.rows===4);
      check('Performance rows distribute their available space evenly at '+scale,
        table.distributed&&table.gaps.every(gap=>gap>=0)&&Math.max(...table.gaps)-Math.min(...table.gaps)<=1.5&&
        Math.abs(table.top-table.bottom)<=1.5&&Math.abs(table.gaps[1]-(table.top+table.bottom))<=1.5);
      check('Metric coverage adds no repeated visible rows or counters at '+scale,table.coverage===0);
      await publish('credits_costs','max',{pending:true});
      check('One upper-left partial-results badge does not increase the card height at '+scale,
        await page.locator('#ss-groups .ss-group').evaluate((card,{height,scale})=>
          card.querySelectorAll('.ss-group-coverage').length===1&&Math.abs(card.getBoundingClientRect().height/scale-height)<=0.5&&
          card.querySelectorAll('.ss-cell-coverage,.ss-count-coverage,.ss-wn8-coverage').length===0,{height:table.height,scale}));
      await publish('credits_costs','max',{noSources:true});
      check('Missing financial source references leave no empty extrema action slots at '+scale,
        await page.locator('#ss-groups .ss-group').evaluate(card=>card.querySelectorAll('.ss-credit-extreme-actions').length===0&&
          [...card.querySelectorAll('.ss-credit-cell')].every(cell=>cell.children.length===1&&cell.firstElementChild.classList.contains('ss-cell-value'))));
    }finally{await page.close();}
  }
};
