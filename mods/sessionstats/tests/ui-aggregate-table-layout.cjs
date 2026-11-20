/* Ordinary aggregate cards must retain adjacent tables in both timeline lanes.
   The previous single-result checks missed the distributed Min/Avg/Max layout. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let left=6;
  function next(){if(--left)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}));
module.exports=async({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:3840,height:2560},viewport:{width:3840,height:2560,scale}});
    try{
      await page.evaluate(()=>{window.__aggregateTableFixture=JSON.parse(model.payload);});
      let sequence=0;
      async function publish(group,language,width=1320,options={}){
        const viewportWidth=width<625?width*scale+20:3840;
        await page.setViewportSize({width:viewportWidth,height:2560});
        await page.evaluate(({group,language,messages,width,viewportWidth,scale,sequence,options})=>{
          const payload=JSON.parse(JSON.stringify(__aggregateTableFixture)),scope=payload.scopes.launch;
          payload.account_key='synthetic-aggregate-tables-'+scale+'-'+sequence;
          payload.viewport={width:viewportWidth,height:2560,scale};payload.window_size=[width,1100];
          payload.appearance={window_settings:{background_transparency:0,maximized:false,restored_width:width,restored_height:1100}};
          payload.localization={language,messages};
          const sample=scope[group][0];
          scope[group]=[0,1].map(index=>{
            const item=JSON.parse(JSON.stringify(sample)),stats=item.stats;
            item.id='synthetic-adjacent-'+group+'-'+index;item.name='Synthetic '+group+' '+index;
            stats.battles=stats.observed_battles=14;stats.win_rate=42.9;stats.wn8=1808;stats.wn8_count=14;
            const ranges={xp_base:[154,558,1403],xp_received:[266,3111,13415],battle_wn8:[78,2016,8834],
              credits_income_base:[1234,15000,34567],credits_income_received:[4567,25000,45678],
              credits_costs:[1234,15000,23456],credits_net_base:[-22222,-10000,12345],credits_net_received:[-11111,10000,34567]};
            if(options.fiveDigit){
              ranges.xp_base=[13415,22000,33415];ranges.xp_received=[13415,30000,43415];ranges.battle_wn8=[13415,24000,33415];
            }
            if(options.shortValues)for(const metric of ['xp_base','xp_received','battle_wn8'])ranges[metric]=[123,456,789];
            if(options.large)for(const metric of ['xp_base','xp_received','battle_wn8'])ranges[metric]=[12345678,23456789,34567890];
            item.extrema_battles={};
            for(const [metric,[min,avg,max]]of Object.entries(ranges)){
              stats[metric]={count:14,min,avg,max,sum:avg*14};item.extrema_battles[metric]={};
              for(const statistic of ['min','max'])item.extrema_battles[metric][statistic]={
                id:item.id+'-'+metric+'-'+statistic,name:'Synthetic vehicle',map:'Synthetic map',started_at:1794000000,
                metric,statistic,value:stats[metric][statistic]};
            }
            stats.currencies={credits:{income_base:123456,income_base_count:14,income:987654,income_count:14,
              costs:765432,costs_count:14,net_base:-641976,net_base_count:14,net:222222,net_count:14},
              bonds:{income:50,income_count:14,costs:0,costs_count:14,net:50,net_count:14},
              gold:{income:0,income_count:14,costs:0,costs_count:14,net:0,net_count:14}};
            if(options.sevenDigit)Object.assign(stats.currencies.credits,{income:1485270,costs:1417829,net:67441});
            if(options.large)Object.assign(stats.currencies.credits,{income_base:12345678,income:98765432,costs:76543210,net_base:-64197532,net:22222222});
            if(options.shortValues)Object.assign(stats.currencies.credits,{income_base:1234,income:9876,costs:7654,net_base:-6420,net:2222});
            if(options.missingBase){
              stats.currencies.credits.income_base=stats.currencies.credits.net_base=null;
              stats.currencies.credits.income_base_count=stats.currencies.credits.net_base_count=0;
              stats.credits_income_base.count=stats.credits_net_base.count=0;
            }
            return item;
          });
          scope.ordering[group]={metric:'off',statistic:'avg',direction:'desc',chronology:'newest'};
          scope.pagination[group]={page:0,pages:1,total:2,page_size:40};scope.data_revision='adjacent-'+sequence;
          model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
          document.getElementById('ss-scope-launch').onclick();document.getElementById('ss-group-'+group).onclick();
        },{group,language,messages:languages[language],width,viewportWidth,scale,sequence:++sequence,options});
        await frames(page);
      }
      async function audit(){return page.locator('#ss-groups').evaluate((owner,scale)=>{
      // Only a marked caption may intentionally clip; numeric ink and source
      // controls still have to fit their original owning cell in full.
      const captionEllipsis=(text,owner)=>{
        const parent=text.nodeType===3?text.parentElement:text,
          caption=parent&&parent.closest('.ss-caption-ellipsis');
        if(!caption||!owner.contains(caption)||!caption.closest('.ss-aggregate')||
          !caption.closest('.ss-metric-name,.ss-credit-row-label,.ss-credit-inline-label,.ss-money-head > .ss-money-label,.ss-money-row > .ss-money-label,.ss-money-head > .ss-money-value,.ss-metric-head > .ss-metric-number,.ss-group-kpi .ss-kpi-label'))return false;
        const style=getComputedStyle(caption),box=caption.getBoundingClientRect(),cell=owner.getBoundingClientRect(),full=caption.textContent,
          inset=['paddingTop','paddingBottom','borderTopWidth','borderBottomWidth'].reduce((sum,key)=>sum+(parseFloat(style[key])||0),0);
        return full.length>0&&caption.classList.contains('ss-hover-help')&&caption.getAttribute('data-ss-help')===full&&
          caption.getAttribute('aria-label')===full&&caption.getAttribute('aria-controls')==='ss-help-tooltip'&&
          style.whiteSpace==='nowrap'&&style.overflowX==='hidden'&&style.textOverflow==='ellipsis'&&
          caption.scrollWidth>caption.clientWidth&&box.width>0&&box.height>0&&box.height<=parseFloat(style.lineHeight)+inset+scale&&
          box.left>=cell.left-scale&&box.right<=cell.right+scale&&box.top>=cell.top-scale&&box.bottom<=cell.bottom+scale;
      };
        const rect=node=>{const r=node.getBoundingClientRect();return {left:r.left/scale,right:r.right/scale,top:r.top/scale,bottom:r.bottom/scale,width:r.width/scale,height:r.height/scale};};
        const cards=[...owner.querySelectorAll('.ss-group')].map(card=>{
          const header=rect(card.querySelector('.ss-group-header')),identity=rect(card.querySelector('.ss-group-name')),headlineStats=rect(card.querySelector('.ss-group-stats'));
          const bounds=rect(card),details=rect(card.querySelector('.ss-details')),performance=rect(card.querySelector('.ss-performance')),economy=rect(card.querySelector('.ss-economy'));
          const failures=[];
          for(const node of card.querySelectorAll('.ss-metric-row .ss-extreme-number,.ss-metric-row > .ss-metric-number:not(.ss-extreme-cell),.ss-money-value > .ss-cell-value,.ss-metric-name,.ss-money-label,.ss-credit-inline-label,.ss-metric-head > .ss-metric-number,.ss-money-head > .ss-money-value')){
            if(!(node.getBoundingClientRect().width>0))continue;
            const owner=node.parentNode.classList.contains('ss-extreme-cell')||node.classList.contains('ss-cell-value')?node.parentNode:node,
              cell=rect(owner),walker=document.createTreeWalker(node,NodeFilter.SHOW_TEXT);let text;
            while((text=walker.nextNode()))if(text.textContent.trim()&&!captionEllipsis(text,owner)){
              const range=document.createRange();range.selectNodeContents(text);
              for(const ink of range.getClientRects())if(ink.width>0&&(ink.left/scale<cell.left-1||ink.right/scale>cell.right+1||ink.top/scale<cell.top-1||ink.bottom/scale>cell.bottom+1))failures.push({text:text.textContent,cell,ink:{left:ink.left/scale,right:ink.right/scale,top:ink.top/scale,bottom:ink.bottom/scale}});
            }
          }
          for(const button of card.querySelectorAll('.ss-metric-row .ss-metric-battle-link')){
            const action=rect(button),cell=rect(button.parentNode);
            if(action.left<cell.left-1||action.right>cell.right+1||action.top<cell.top-1||action.bottom>cell.bottom+1)failures.push('clipped-source');
            const metric=button.closest('.ss-metric-row').getAttribute('data-ss-metric'),statistic=button.getAttribute('data-ss-extreme'),
              number=button.parentNode.querySelector('.ss-extreme-number').textContent.replace(/\s/g,''),
              description=button.getAttribute('data-ss-help').split('\n')[0].replace(/\s/g,'');
            if(!description.endsWith(':'+number)||button.getAttribute('data-battle-id')!==card.getAttribute('data-group-id')+'-'+metric+'-'+statistic)failures.push('incorrect-source-value:'+metric+'/'+statistic);
          }
          const financialActions=[];
          for(const actions of card.querySelectorAll('.ss-credit-extreme-actions')){
            const group=rect(actions),cell=rect(actions.parentNode),buttons=[...actions.children].map(rect);
            if(!(group.width>0))continue;
            const fits=(inner,outer)=>inner.left>=outer.left-1&&inner.right<=outer.right+1&&inner.top>=outer.top-1&&inner.bottom<=outer.bottom+1;
            const left=Math.min(...buttons.map(button=>button.left)),right=Math.max(...buttons.map(button=>button.right)),
              centered=buttons.length>0&&Math.abs((left+right-group.left-group.right)/2)<=1&&
                buttons.every(button=>Math.abs((button.top+button.bottom-group.top-group.bottom)/2)<=1);
            const contained=fits(group,cell)&&buttons.every(button=>fits(button,group)&&fits(button,cell));
            for(const button of actions.children){
              const bounds=rect(button),range=document.createRange();range.selectNodeContents(button);
              for(const ink of range.getClientRects())if(ink.width>0&&!fits({left:ink.left/scale,right:ink.right/scale,top:ink.top/scale,bottom:ink.bottom/scale},bounds))failures.push('clipped-financial-action-label');
            }
            financialActions.push({metric:actions.parentNode.getAttribute('data-ss-metric'),group,cell,buttons,centered,contained});
            if(!centered||!contained)failures.push('clipped-or-uncentered-financial-actions:'+actions.parentNode.getAttribute('data-ss-metric'));
          }
          const creditValues=['credits_income_base','credits_income_received','credits_costs','credits_net_base','credits_net_received'].map(metric=>
            card.querySelector('.ss-economy [data-ss-metric="'+metric+'"] > .ss-cell-value').textContent.replace(/\s/g,''));
          const performanceValues=[...card.querySelectorAll('.ss-metric-row')].flatMap(row=>[...row.querySelectorAll(':scope > .ss-metric-number')].map(cell=>cell.textContent.replace(/\s/g,'')));
          const creditCaptions=[...card.querySelectorAll('.ss-credit-label-text,.ss-credit-inline-label')].filter(node=>node.getBoundingClientRect().width>0).map(node=>{
            const range=document.createRange();range.selectNodeContents(node);const tops=[];
            for(const ink of range.getClientRects())if(ink.width>0&&!tops.some(top=>Math.abs(top-ink.top)<scale))tops.push(ink.top);
            return {text:node.textContent,lines:tops.length};
          });
          const metricCaptionsInline=[...card.querySelectorAll('.ss-metric-row')].every(row=>{
            const label=rect(row.querySelector('.ss-metric-name')),amount=rect(row.querySelector('.ss-metric-number'));
            return Math.abs(label.top-amount.top)<=1&&label.right<=amount.left+1;
          });
          const financeLane=card.querySelector('.ss-economy'),financeWidth=Number(financeLane.getAttribute('data-ss-finance-content-width')),
            financeNumber=Number(financeLane.getAttribute('data-ss-finance-number-width'));
          return {financialActions,performanceValues,creditCaptions,bounds,details,performance,economy,failures,creditValues,header,identity,headlineStats,
            metricCaptionsInline,financeCompact:financeLane.classList.contains('ss-credit-compact'),financeWidth,financeNumber,
            singleHeadline:identity.right<=headlineStats.left+1&&identity.top<headlineStats.bottom&&headlineStats.top<identity.bottom&&
              header.height<=Math.max(identity.height,headlineStats.height)+4,
            adjacent:economy.left>=performance.right-1&&Math.abs(economy.top-performance.top)<=1,
            contained:[performance,economy].every(box=>box.left>=bounds.left-1&&box.right<=bounds.right+1),
            noBlankBand:details.height<=Math.max(performance.height,economy.height)+9,
            sources:card.querySelectorAll('.ss-metric-row .ss-metric-battle-link').length};
        });
        return {two:owner.classList.contains('ss-two-columns'),cards};
      },scale);}
      for(const language of ['en','pl'])for(const group of ['vehicles','maps','tiers']){
        await publish(group,language);const value=await audit(),caption=group+'/'+language+'/'+scale+'x';
        check('Default two-lane aggregates keep performance and finances adjacent '+caption+': '+JSON.stringify(value),
          value.two&&value.cards.length===2&&value.cards.every(card=>card.adjacent&&card.contained&&card.noBlankBand&&
            Math.abs(card.bounds.width-(group==='tiers'?520:560))<=1));
        check('Unsorted ordinary aggregates keep identity and KPIs in one natural header row '+caption+': '+JSON.stringify(value),
          value.cards.every(card=>card.singleHeadline));
        check('Both aggregate lanes retain full signed six-digit totals and all source arrows '+caption+': '+JSON.stringify(value),
          value.cards.every(card=>!card.failures.length&&card.sources===6&&
            card.creditValues.join('|')==='123456|987654|-765432|-641976|+222222'));
        if(language==='pl'&&group!=='tiers')check('Polish ordinary560px credit captions remain on one line '+caption+': '+JSON.stringify(value),
          value.cards.every(card=>card.creditCaptions.length===2&&card.creditCaptions.every(caption=>caption.lines===1)));
        await publish(group,language,863,{missingBase:true});const single=await audit();
        check('A single aggregate lane preserves adjacent tables with the permanent missing-base row '+caption+': '+JSON.stringify(single),
          !single.two&&single.cards.every(card=>card.adjacent&&card.contained&&card.noBlankBand&&!card.failures.length&&
            card.creditValues.join('|')==='—|987654|-765432|—|+222222'));
      }
      for(const options of [{fiveDigit:true},{sevenDigit:true},{fiveDigit:true,sevenDigit:true}]){
        await publish('vehicles','pl',1320,options);const value=await audit();
        const performance=options.fiveDigit?'13415|22000|33415|13415|30000|43415|13415|24000|33415':'154|558|1403|266|3111|13415|78|2016|8834';
        const credits=options.sevenDigit?'123456|1485270|-1417829|-641976|+67441':'123456|987654|-765432|-641976|+222222';
        check('Asymmetric aggregate columns preserve every original five-digit minimum/maximum and seven-digit total at '+scale+'x/'+JSON.stringify(options)+': '+JSON.stringify(value),
          value.two&&value.cards.every(card=>card.adjacent&&card.contained&&!card.failures.length&&card.sources===6&&
            card.performanceValues.join('|')===performance&&card.creditValues.join('|')===credits));
      }
      await publish('vehicles','pl');
      await page.evaluate(()=>{window.__aggregateResizeCards=[...document.querySelectorAll('#ss-groups .ss-group')];});
      const inset=await page.evaluate(scale=>(document.getElementById('grz-session-stats').getBoundingClientRect().width-
        document.getElementById('ss-groups').getBoundingClientRect().width)/scale,scale);
      const widths=[];
      for(const width of [400,560,720,560]){
        let viewportWidth=Math.round((width+inset+20)*scale),value;
        for(let attempt=0;attempt<2;attempt++){
          await page.setViewportSize({width:viewportWidth,height:2560});
          await page.evaluate(({viewportWidth,scale})=>{const payload=JSON.parse(model.payload);payload.viewport={width:viewportWidth,height:2560,scale};
            model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},{viewportWidth,scale});
          await frames(page);value=await audit();
          // A native viewport below560px has a smaller scroll inset. Resolve
          // that real breakpoint before checking the requested card width.
          const difference=value.cards[0].bounds.width-width;
          if(Math.abs(difference)<=1)break;
          viewportWidth-=Math.round(difference*scale);
        }
        const retained=await page.evaluate(()=>[...document.querySelectorAll('#ss-groups .ss-group')].every((card,index)=>card===__aggregateResizeCards[index]));
        widths.push(value.cards.map(card=>({card:card.bounds.width,performance:card.performance.width,economy:card.economy.width})));
        check('The same aggregate cards discard obsolete column widths through live400→560→720→560 resize at '+width+'/'+scale+'x: '+JSON.stringify(value),
          retained&&value.cards.length===2&&value.cards.every(card=>Math.abs(card.bounds.width-width)<=1&&card.contained&&!card.failures.length&&
            (width<500||card.adjacent)&&card.creditValues.join('|')==='123456|987654|-765432|-641976|+222222'));
      }
      check('Returning to560px restores the original aggregate table allocation at '+scale+'x: '+JSON.stringify(widths),
        widths[1].every((card,index)=>['card','performance','economy'].every(key=>Math.abs(card[key]-widths[3][index][key])<=1)));
      await page.setViewportSize({width:3840,height:2560});
      await publish('vehicles','pl',1320,{large:true});const large=await audit();
      check('Genuinely larger aggregate values retain their full figures in a readable fallback at '+scale+'x: '+JSON.stringify(large),
        large.two&&large.cards.every(card=>card.contained&&!card.failures.length&&card.sources===6&&
          card.creditValues.join('|')==='12345678|98765432|-76543210|-64197532|+22222222'));
      await publish('vehicles','pl');const corrected=await audit();
      const obsolete=await page.addStyleTag({content:
        '#ss-groups .ss-aggregate .ss-details { flex-wrap:wrap !important; }'+
        '#ss-groups .ss-aggregate .ss-performance { flex:1 1 300rem !important; width:auto !important; }'+
        '#ss-groups .ss-aggregate .ss-economy { flex:1 1 296rem !important; width:auto !important; }'});
      const legacy=await audit();
      check('The ordinary aggregate guard reproduces and rejects the previous vertical-table regression at '+scale+'x: '+JSON.stringify(legacy),
        legacy.two&&legacy.cards.every(card=>!card.adjacent&&card.economy.top>=card.performance.bottom-1));
      check('Adjacent tables shorten the Polish aggregate card by at least one complete metric row at '+scale+'x: '+JSON.stringify({corrected,legacy}),
        corrected.cards.every((card,index)=>card.bounds.height<=legacy.cards[index].bounds.height-24));
      await obsolete.evaluate(node=>node.remove());await frames(page);
      check('Removing the obsolete aggregate flex bases restores adjacent tables at '+scale+'x',(await audit()).cards.every(card=>card.adjacent));
      for(const width of [365,525,625]){
        await publish('vehicles','en',width,{shortValues:true});const value=await audit();
        check('Narrow aggregate tables budget captions from their actual lanes at '+width+'/'+scale+'x: '+JSON.stringify(value),
          value.cards.length===2&&value.cards.every(card=>card.adjacent===(width>=525)&&card.metricCaptionsInline&&
            card.financeWidth>0&&card.financeNumber>0&&card.financeCompact===(card.financeWidth-3*card.financeNumber<64)&&
            card.contained&&!card.failures.length&&card.sources===6&&
            card.creditValues.join('|')==='1234|9876|-7654|-6420|+2222'));
      }
      await publish('vehicles','pl',320,{large:true});const veryLarge=await audit();
      check('Exceptionally long figures still fit when their captions need a separate line at '+scale+'x: '+JSON.stringify(veryLarge),
        veryLarge.cards.every(card=>!card.adjacent&&!card.metricCaptionsInline&&card.financeCompact&&card.contained&&
          !card.failures.length&&card.sources===6&&card.creditValues.join('|')==='12345678|98765432|-76543210|-64197532|+22222222'));
    }finally{await page.close();}
  }
};
