/* Coverage is one result headline plus one badge per incomplete aggregate. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let left=6;function next(){if(--left)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);}));
module.exports=async({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const page=await nativeHost(browser,{initialViewport:{width:1920,height:1300},viewport:{width:1920,height:1300,scale:1}});
  try{
    for(const [language,messages]of Object.entries(languages))for(const fixture of ['partial','zero','known','legacy']){
      await page.evaluate(({language,messages,fixture})=>{
        const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
        payload.account_key='synthetic-coverage-'+language+'-'+fixture;
        payload.localization={language,selected:language,messages};payload.window_size=[1200,1000];payload.warnings=[];
        const stats=JSON.parse(JSON.stringify(scope.summary)),known=fixture==='zero'?0:fixture==='known'?5:3;
        stats.battles=known;stats.observed_battles=5;stats.missing_results=5-known;stats.partial_results=1;
        stats.wins=known?known-1:0;stats.losses=known?1:0;stats.draws=0;stats.win_rate=known?100*(known-1)/known:null;
        stats.wn8=known?1332:null;stats.wn8_count=known?1:0;
        for(const metric of ['xp_base','xp_received','free_xp','battle_wn8']){
          const count=metric==='xp_base'?0:metric==='xp_received'?known:Math.min(known,2);
          stats[metric]={count,min:count?30:null,avg:count?50:null,max:count?70:null,sum:count?50*count:null};
        }
        stats.currencies.credits={income_base:null,net_base:null,income_base_count:0,net_base_count:0,
          income:known?1000:null,costs:known?500:null,net:known?500:null,
          income_count:Math.min(known,2),costs_count:known,net_count:Math.min(known,1)};
        for(const currency of ['bonds','gold'])stats.currencies[currency]={income:0,costs:0,net:0,income_count:known,costs_count:known,net_count:known};
        // Historical snapshots can omit the observed total and split-credit
        // counters. Missing data remains missing; the UI must not invent x/y.
        if(fixture==='legacy'){
          delete stats.observed_battles;delete stats.missing_results;
          for(const field of ['income_base','net_base','income_base_count','net_base_count','income_count','costs_count','net_count'])delete stats.currencies.credits[field];
        }
        scope.summary=stats;scope.pending=2;
        for(const group of ['maps','vehicles','tiers']){
          const original=JSON.parse(JSON.stringify(scope[group][0]));
          scope[group]=[stats,Object.assign(JSON.parse(JSON.stringify(stats)),{battles:5,observed_battles:5})].map((itemStats,index)=>{
            const item=JSON.parse(JSON.stringify(original));item.id='coverage-'+group+'-'+index;item.name='Synthetic '+group+' '+index;
            item.stats=JSON.parse(JSON.stringify(itemStats));item.sort_value=item.stats.xp_received.sum;delete item.extrema_battles;
            return item;
          });
          scope.ordering[group]={metric:'xp_received',statistic:'sum',direction:'desc',chronology:'newest'};
          scope.pagination[group]={page:0,pages:1,total:2,page_size:40};
        }
        const battleSample=JSON.parse(JSON.stringify(scope.battles[0]));
        scope.battles=[0,1].map(index=>{
          const item=JSON.parse(JSON.stringify(battleSample)),single=JSON.parse(JSON.stringify(stats)),count=fixture==='zero'?0:1;
          item.id='coverage-battle-'+index;item.name='Synthetic battle '+index;single.battles=count;single.observed_battles=1;
          single.wn8_count=0;single.wn8=null;
          for(const metric of ['xp_base','xp_received','free_xp','battle_wn8']){
            single[metric]={count:metric==='xp_received'?count:0,min:count?50:null,avg:count?50:null,max:count?50:null,sum:count?50:null};
          }
          for(const currency of ['credits','bonds','gold'])for(const field of ['income','costs','net'])single.currencies[currency][field+'_count']=count;
          item.stats=single;return item;
        });
        scope.pagination.battles={page:0,pages:1,total:2,page_size:40};
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();document.getElementById('ss-scope-launch').onclick();
      },{language,messages,fixture});
      for(const group of ['maps','vehicles','tiers','battles']){
        await page.locator('#ss-group-'+group).click();await frames(page);
        const result=await page.evaluate(()=>{
          const panel=document.getElementById('grz-session-stats'),summary=document.getElementById('ss-summary'),cards=[...document.querySelectorAll('#ss-groups .ss-group')];
          const ratios=node=>{const matches=[],walker=document.createTreeWalker(node,NodeFilter.SHOW_TEXT);let text;
            while((text=walker.nextNode())){if(text.parentElement.closest('.ss-group-subtitle'))continue;const range=document.createRange();range.selectNodeContents(text);if(!range.getBoundingClientRect().width)continue;
              for(const match of text.textContent.matchAll(/\b\d[\d\s\u00a0]*\s*\/\s*\d[\d\s\u00a0]*\b/g))matches.push({value:match[0].replace(/\s/g,''),owner:text.parentElement.className});
            }return matches;};
          return {global:ratios(summary),forbidden:panel.querySelectorAll('.ss-cell-coverage,.ss-count-coverage,.ss-wn8-coverage,.ss-count-observed').length,
            status:document.getElementById('ss-status').textContent,statusRatios:ratios(document.getElementById('ss-status')),
            rows:[...summary.querySelectorAll('.ss-metric-row')].map(row=>({metric:row.getAttribute('data-ss-metric'),aria:row.getAttribute('aria-label')})),
            cards:cards.map(card=>({ratios:ratios(card),badges:[...card.querySelectorAll('.ss-group-coverage')].map(badge=>({text:badge.textContent.replace(/\s/g,''),aria:badge.getAttribute('aria-label'),upperLeft:!!badge.closest('.ss-group-heading')})),
              battles:card.querySelector('.ss-group-count .ss-kpi-value')?.textContent.replace(/\s/g,'')||null,freeXP:card.querySelector('.ss-free-xp').getAttribute('aria-label'),
              finance:[...card.querySelectorAll('.ss-money-row .ss-money-value')].map(cell=>cell.getAttribute('aria-label')),
              help:card.querySelector('.ss-info-button').getAttribute('data-ss-help')}))};
        });
        const partial=fixture==='partial'||fixture==='zero',aggregate=group!=='battles',count=fixture==='zero'?0:fixture==='known'?5:3;
        const expectedRatio=count+'/5',caption=language+'/'+fixture+'/'+group;
        const valueText=n=>messages['coverage.value'].replace('{0}',String(n)).replace('{1}',fixture==='legacy'?'3':'5');
        check('Visible coverage appears only in the overview and one partial-card name badge '+caption+': '+JSON.stringify(result),
          result.forbidden===0&&result.global.length===(partial?1:0)&&(!partial||result.global[0].value===expectedRatio)&&
          result.cards.length===2&&result.cards.every((card,index)=>card.ratios.length===(aggregate&&partial&&index===0?1:0)&&
            card.badges.length===(aggregate&&partial&&index===0?1:0)&&(!card.badges.length||card.badges[0].upperLeft&&card.badges[0].text===expectedRatio)&&
            card.battles===(aggregate?String(fixture==='legacy'&&index===0?3:5):null))&&result.statusRatios.length===0&&
          result.status===messages['status.pending'].replace('{0}','2'));
        check('Hidden metric availability remains labeled and accessible without repeated badges '+caption,
          result.rows.find(row=>row.metric==='xp_base').aria===messages['xp.base']+' '+valueText(0)&&
          (!aggregate||result.cards[0].help.includes(messages['xp.base']+' '+valueText(0)))&&
          (!aggregate||!partial||result.cards[0].badges[0].aria===messages['metric.confirmed']+' '+valueText(count))&&
          (!aggregate||fixture==='legacy'||result.cards[0].finance.some(text=>text&&text.includes(valueText(Math.min(count,2)))))&&
          (!aggregate||fixture==='legacy'||result.cards[0].freeXP===messages['xp.free']+' '+valueText(Math.min(count,2))));
      }
    }
  }finally{await page.close();}
};
