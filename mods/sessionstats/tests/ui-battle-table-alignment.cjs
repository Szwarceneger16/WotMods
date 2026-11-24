/* Single-battle tables share exact financial lanes and use bounded wide space. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let count=8;
  function next(){if(--count)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}));
module.exports=async({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:3840,height:2600},viewport:{width:3840,height:2600,scale}});
    try{
      await page.evaluate(()=>{
        window.__battleTableFixture=JSON.parse(model.payload);
        const fault=window.__battleTableFault={rect:Element.prototype.getBoundingClientRect,query:Element.prototype.querySelectorAll,style:window.getComputedStyle,stale:false,audit:false};
        Element.prototype.getBoundingClientRect=function(){
          const result=fault.rect.call(this);
          if(fault.stale&&!fault.audit&&this.classList.contains('ss-economy')&&this.closest('.ss-battle')){
            const width=fault.rect.call(this.parentNode).width;
            return {x:result.x,y:result.y,left:result.left,right:result.left+width,top:result.top,bottom:result.bottom,width,height:result.height};
          }
          return result;
        };
        Element.prototype.querySelectorAll=function(selector){
          if(fault.stale&&!fault.audit&&this.classList.contains('ss-economy')&&this.closest('.ss-battle')&&
            selector==='.ss-money-head, .ss-money-row:not(.ss-credit-pair)')return fault.query.call(this,'.ss-money-head');
          return fault.query.call(this,selector);
        };
        window.getComputedStyle=function(node){
          if(fault.stale&&!fault.audit&&node.classList.contains('ss-economy')&&node.closest('.ss-battle')){
            // Gameface still paints the divider and gutter when computed style omits their dimensions.
            return {paddingLeft:'0px',paddingRight:'0px',borderLeftWidth:'0px',borderRightWidth:'0px'};
          }
          return fault.style.apply(this,arguments);
        };
      });
      // Native flex must not silently shrink an excessive assigned lane.
      await page.addStyleTag({content:'#ss-groups .ss-battle .ss-money-head > div, #ss-groups .ss-battle .ss-money-row:not(.ss-credit-pair) > div { flex-shrink:0 !important; }'});
      let sequence=0;
      async function publish(language,width,{stale=false,large=false}={}){
        await page.evaluate(({language,messages,width,scale,sequence,stale,large})=>{
          const payload=JSON.parse(JSON.stringify(__battleTableFixture)),scope=payload.scopes.launch,sample=scope.battles[0];
          __battleTableFault.stale=stale;
          payload.account_key='synthetic-battle-tables-'+scale+'-'+sequence;payload.window_size=[2000,1100];
          payload.viewport={width:3840,height:2600,scale};payload.localization={language,messages};
          payload.appearance={wide_card_widths:{battles:width},window_settings:{maximized:false,background_transparency:0,restored_width:2000,restored_height:1100}};
          scope.battles=[0,1].map(index=>{
            const item=JSON.parse(JSON.stringify(sample)),stats=item.stats;
            item.id='synthetic-battle-table-'+index;item.name='Synthetic battle vehicle';item.outcome=index?'loss':'win';
            const values={xp_base:large?123456:205,xp_received:large?234567:508,battle_wn8:large?12345:3451};
            Object.assign(stats,{battles:1,observed_battles:1,wn8:values.battle_wn8,wn8_count:1});
            item.extrema_battles={};
            for(const [metric,value]of Object.entries(values)){
              stats[metric]={count:1,min:value,avg:value,max:value,sum:value};
              item.extrema_battles[metric]={min:{id:'synthetic-unused-min',metric,statistic:'min',value},max:{id:'synthetic-unused-max',metric,statistic:'max',value}};
            }
            stats.currencies={credits:{income_base:123456,income_base_count:1,income:1485270,income_count:1,
              costs:1417829,costs_count:1,net_base:-1294373,net_base_count:1,net:67441,net_count:1},
              bonds:{income:50,income_count:1,costs:0,costs_count:1,net:50,net_count:1}};
            if(index)delete item.extrema_battles;
            return item;
          });
          scope.pagination.battles={page:0,pages:1,total:2,page_size:40};
          scope.ordering.battles={metric:'off',statistic:'avg',direction:'desc',chronology:'newest'};scope.data_revision='battle-tables-'+sequence;
          model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);document.getElementById('ss-group-battles').click();
        },{language,messages:languages[language],width,scale,sequence:++sequence,stale,large});
        await frames(page);
      }
      async function audit(){return page.locator('#ss-groups').evaluate((owner,scale)=>{
        const fault=__battleTableFault,first=owner.querySelector('.ss-battle .ss-economy'),staleWidth=first.getBoundingClientRect().width/scale;
        fault.audit=true;
        try{
          const box=node=>{const r=fault.rect.call(node);return {left:r.left/scale,right:r.right/scale,top:r.top/scale,bottom:r.bottom/scale,width:r.width/scale,height:r.height/scale};},
            ink=node=>{const r=document.createRange();r.selectNodeContents(node);return [...r.getClientRects()].filter(part=>part.width>0&&part.height>0)
              .map(part=>({left:part.left/scale,right:part.right/scale,top:part.top/scale,bottom:part.bottom/scale}));},
            inside=(part,owner)=>part.left>=owner.left-1&&part.right<=owner.right+1&&part.top>=owner.top-1&&part.bottom<=owner.bottom+1,
            aligned=(a,b)=>Math.abs(a.left-b.left)<=0.25&&Math.abs(a.right-b.right)<=0.25;
          const cards=[...owner.querySelectorAll('.ss-battle')].map(card=>{
            const bounds=box(card),details=box(card.querySelector('.ss-details')),performance=box(card.querySelector('.ss-battle-performance')),
              economy=card.querySelector('.ss-economy'),finance=box(economy),pair=economy.querySelector('.ss-credit-pair'),failures=[];
            const header=economy.querySelector('.ss-money-head');
            const heads=[...header.children].filter(node=>node.classList.contains('ss-money-value')).map(box),
              lanes=['.ss-credit-income-column','.ss-credit-shared-cost','.ss-credit-net-column'].map(selector=>box(pair.querySelector(selector)));
            if(heads.length!==3||!heads.every((head,index)=>aligned(head,lanes[index])))failures.push('credit-header-columns');
            const content=box(header);
            if(!heads.every(head=>inside(head,content))||Math.abs(heads[2].right-content.right)>0.25)failures.push('finance-content-edge');
            for(const basis of ['base','received']){
              const cells=['credits_income_'+basis,'credits_costs','credits_net_'+basis].map(metric=>pair.querySelector('[data-ss-metric="'+metric+'"]'));
              if(!cells.every((cell,index)=>aligned(box(cell),heads[index])))failures.push('credit-row-columns:'+basis);
            }
            const ordinary=[...economy.children].filter(node=>node.classList.contains('ss-money-row')&&!node.classList.contains('ss-credit-pair'));
            for(const row of ordinary){const cells=[...row.children].filter(node=>node.classList.contains('ss-money-value'));
              if(cells.length!==3||!cells.every((cell,index)=>aligned(box(cell),heads[index])))failures.push('bonds-header-columns');
            }
            const centered=[],metricSlots=[];
            for(const value of card.querySelectorAll('.ss-battle-value,.ss-money-row .ss-cell-value')){
              const cell=value.closest('.ss-money-value')||value,bounds=box(cell),parts=ink(value),isPerformance=value.classList.contains('ss-battle-value');
              if(!parts.length||!parts.every(part=>inside(part,bounds))||parseFloat(getComputedStyle(value).fontSize)/scale<(isPerformance?18:13))failures.push('full-readable-number:'+value.textContent);
              const left=Math.min(...parts.map(part=>part.left)),right=Math.max(...parts.map(part=>part.right));
              centered.push(Math.abs((left+right-bounds.left-bounds.right)/2)<=1.25);
              if(isPerformance){const row=box(value.closest('.ss-battle-measure'));metricSlots.push({box:bounds,row,center:(left+right)/2});}
            }
            const values=[...pair.querySelectorAll('.ss-money-value[data-ss-metric] > .ss-cell-value')].map(node=>node.textContent.replace(/\s/g,'')),
              metrics=[...card.querySelectorAll('.ss-battle-value')].map(node=>node.textContent.replace(/\s/g,''));
            return {bounds,details,performance,finance,heads,lanes,failures,centered,metricSlots,values,metrics,
              spare:details.width-performance.width-finance.width,
              slotsShared:metricSlots.length===3&&metricSlots.every(slot=>
                Math.abs(slot.box.left-metricSlots[0].box.left)<=0.25&&Math.abs(slot.box.right-metricSlots[0].box.right)<=0.25),
              actions:card.querySelectorAll('.ss-metric-battle-link,.ss-credit-extreme-actions').length,
              contained:inside(performance,bounds)&&inside(finance,bounds)&&performance.right<=finance.left+1};
          });
          return {cards,staleWidth,actualWidth:cards[0].finance.width};
        }finally{fault.audit=false;}
      },scale);}
      const valid=value=>value.cards.length===2&&value.cards.every(card=>!card.failures.length&&card.contained&&card.centered.every(Boolean)&&card.slotsShared&&card.actions===0&&
        card.values.join('|')==='123456|1485270|-1417829|-1294373|+67441'&&card.metrics.length===3);
      const wide=value=>valid(value)&&value.cards.every(card=>card.performance.width>=156&&card.performance.width<=200&&
        card.finance.width<=500&&card.spare>=12&&card.metricSlots.every(slot=>slot.box.width>=slot.row.width*0.35));
      for(const language of Object.keys(languages))for(const width of [500,720]){
        await publish(language,width);const result=await audit();
        check('Battle header, credit and Bonds lanes share exact boundaries with complete source-less figures '+language+'/'+width+'/'+scale+'x: '+JSON.stringify(result),
          valid(result)&&result.cards.every(card=>Math.abs(card.bounds.width-width)<=1&&card.metrics.join('|')==='205|508|3451'));
        if(width===720)check('Wide battle numbers use shared centered lanes beside a modestly wider performance table and capped finances '+language+'/'+scale+'x: '+JSON.stringify(result),wide(result));
      }
      for(const width of [500,720]){
        await publish('pl',width,{stale:true,large:true});const result=await audit();
        check('Assigned battle finance lanes stay inside the card with stale rectangles and missing native gutter measurements at '+width+'/'+scale+'x: '+JSON.stringify(result),
          valid(result)&&result.staleWidth>result.actualWidth+100&&result.cards.every(card=>card.metrics.join('|')==='123456|234567|12345')&&
          (width===500||wide(result)));
      }
      await publish('en',720);const before=await audit();
      const card=page.locator('#ss-groups .ss-battle').first();
      await card.locator('.ss-more-button').click();await frames(page);const expanded=await audit();
      check('Expanded battle details preserve bounded centered table geometry at '+scale+'x: '+JSON.stringify(expanded),wide(expanded)&&
        before.cards.every((item,index)=>Math.abs(item.performance.width-expanded.cards[index].performance.width)<=0.25&&Math.abs(item.finance.width-expanded.cards[index].finance.width)<=0.25));
      await card.locator('.ss-more-button').click();await frames(page);
      const packed=await page.addStyleTag({content:'#ss-groups .ss-battle .ss-money-value { text-align:right !important; } #ss-groups .ss-battle .ss-credit-pair .ss-cell-value { align-self:flex-end !important; }'});
      check('The wide centering guard rejects right-aligned financial figures at '+scale+'x',!wide(await audit()));
      await packed.evaluate(node=>node.remove());await frames(page);
      check('Removing right alignment restores centered battle figures at '+scale+'x',wide(await audit()));
      await publish('en',500);const shifted=await page.addStyleTag({content:'#ss-groups .ss-battle .ss-money-row:not(.ss-credit-pair) > .ss-money-value:nth-child(2) { transform:translateX(2rem) !important; }'});
      check('The shared-lane guard rejects a displaced Bonds boundary at '+scale+'x',!valid(await audit()));
      await shifted.evaluate(node=>node.remove());await frames(page);
      check('Removing the displaced Bonds boundary restores shared lanes at '+scale+'x',valid(await audit()));
    }finally{await page.close();}
  }
};
