/* Native layout may report the previous, stacked finance rectangle after a
   width write. Inspect painted geometry independently of that stale API. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let count=5;
  function next(){if(--count)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}));

function inspectNativeCredits({scale,legacy=false}){
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
  const fault=window.__nativeCreditFault,real=fault.rect,previous=fault.audit;
  const rect=node=>{const r=real.call(node);return {left:r.left/scale,right:r.right/scale,top:r.top/scale,bottom:r.bottom/scale,width:r.width/scale,height:r.height/scale};};
  fault.audit=false;
  const first=document.querySelector('#ss-groups .ss-group'),economy=first.querySelector('.ss-economy'),
    staleWidth=economy.getBoundingClientRect().width/scale,actualWidth=rect(economy).width;
  if(legacy){
    // This is the former width calculation: a stacked rectangle is combined
    // with the new numeric lane, producing a caption wider than its table.
    const css=getComputedStyle(economy),width=staleWidth-((parseFloat(css.paddingLeft)||0)+(parseFloat(css.paddingRight)||0)+
      (parseFloat(css.borderLeftWidth)||0)+(parseFloat(css.borderRightWidth)||0))/scale;
    const number=Number(economy.getAttribute('data-ss-finance-number-width'))||60,caption=width-number*3;
    const labels=economy.querySelector('.ss-credit-label-column');labels.style.width=caption+'rem';labels.style.flex='0 0 '+caption+'rem';
    const head=economy.querySelector('.ss-money-head');
    [...head.children].forEach((cell,index)=>{const value=(index?number:caption)+'rem';cell.style.width=value;cell.style.flex='0 0 '+value;});
  }
  fault.audit=true;
  try{
    const inside=(a,b)=>a.left>=b.left-1&&a.right<=b.right+1&&a.top>=b.top-1&&a.bottom<=b.bottom+1;
    const cards=[...document.querySelectorAll('#ss-groups .ss-group')].map(card=>{
      const bounds=rect(card),performance=rect(card.querySelector('.ss-performance')),economy=card.querySelector('.ss-economy'),table=rect(economy),
        pair=economy.querySelector('.ss-credit-pair'),header=economy.querySelector('.ss-money-head'),failures=[];
      const visible=node=>{const r=rect(node);return r.width>0&&r.height>0;};
      const checkText=(node,owner)=>{
        if(!visible(node))return;
        const cell=rect(owner),walker=document.createTreeWalker(node,NodeFilter.SHOW_TEXT);let text;
        while((text=walker.nextNode()))if(text.textContent.trim()&&!captionEllipsis(text,owner)){
          const range=document.createRange();range.selectNodeContents(text);
          for(const ink of range.getClientRects())if(ink.width>0&&!inside({left:ink.left/scale,right:ink.right/scale,top:ink.top/scale,bottom:ink.bottom/scale},cell))failures.push('text:'+text.textContent);
        }
      };
      for(const cell of header.children)if(visible(cell)){
        if(!inside(rect(cell),table))failures.push('header-outside');checkText(cell,cell);
      }
      for(const cell of pair.querySelectorAll('.ss-money-value')){
        if(!visible(cell)||!inside(rect(cell),table)||!inside(rect(cell),bounds))failures.push('credit-cell-outside:'+cell.getAttribute('data-ss-metric'));
        const figure=cell.querySelector('.ss-cell-value');checkText(figure,cell);
        if(parseFloat(getComputedStyle(figure).fontSize)/scale<13)failures.push('small-credit-figure');
      }
      for(const label of pair.querySelectorAll('.ss-credit-row-label,.ss-credit-inline-label'))checkText(label,label);
      const scope=JSON.parse(model.payload).scopes.launch,input=['vehicles','maps','tiers'].flatMap(group=>scope[group]||[])
        .find(item=>String(item.id)===card.getAttribute('data-group-id')),
        credits=input&&input.stats.currencies.credits,total=input&&input.stats.observed_battles;
      if(!credits)failures.push('missing-credit-input-owner');
      for(const action of pair.querySelectorAll('.ss-metric-battle-link')){
        const cell=action.closest('.ss-money-value'),button=rect(action),row=rect(action.parentElement);
        if(!visible(action)||!inside(button,rect(cell))||!inside(button,table))failures.push('credit-source-outside');
        if(Math.min(button.top-row.top,row.bottom-button.bottom,button.left-row.left,row.right-button.right)<1.5)
          failures.push('credit-action-divider-spacing');
        const metric=action.getAttribute('data-ss-source-metric'),field=metric==='credits_income_base'?'income_base':metric==='credits_net_base'?'net_base':null,
          incompleteBase=credits&&field&&(!(credits[field+'_count']>0)||credits[field+'_count']!==total||!Number.isFinite(credits[field])),
          id=action.getAttribute('data-battle-id');
        if(incompleteBase){
          if(!action.disabled||action.getAttribute('aria-disabled')!=='true'||!action.classList.contains('ss-metric-action-disabled')||
            id!==null||action.onclick!==null)failures.push('incomplete-base-source-contract');
        }else if(!id||!id.startsWith(card.getAttribute('data-group-id')+'-'))failures.push('credit-source-owner');
        checkText(action,action);
      }
      const numericHeaders=[...header.children].slice(1).map(rect),lanes=[pair.querySelector('.ss-credit-income-column'),pair.querySelector('.ss-credit-shared-cost'),pair.querySelector('.ss-credit-net-column')].map(rect);
      const aligned=(a,b)=>Math.abs(a.left-b.left)<=1.5&&Math.abs(a.right-b.right)<=1.5;
      if(!numericHeaders.every((r,index)=>aligned(r,lanes[index])))failures.push('credit-header-columns');
      const ordinary=[...economy.children].filter(node=>node.classList.contains('ss-money-row')&&!node.classList.contains('ss-credit-pair'));
      for(const row of ordinary){
        const values=[...row.children].slice(1);if(values.length!==3)failures.push('ordinary-finance-columns');
        values.forEach((cell,index)=>{if(!inside(rect(cell),table)||!aligned(rect(cell),numericHeaders[index]))failures.push('ordinary-finance-alignment');checkText(cell,cell);});
        checkText(row.children[0],row.children[0]);
      }
      const text=metric=>pair.querySelector('[data-ss-metric="'+metric+'"] .ss-cell-value').textContent.replace(/\s/g,'');
      return {bounds,performance,table,failures,values:['credits_income_base','credits_income_received','credits_costs','credits_net_base','credits_net_received'].map(text),
        costs:pair.querySelectorAll('[data-ss-metric="credits_costs"]').length,sources:pair.querySelectorAll('.ss-metric-battle-link').length,
        adjacent:Math.abs(performance.top-table.top)<=1&&performance.right<=table.left+1};
    });
    return {cards,staleWidth,actualWidth,paired:document.getElementById('ss-groups').classList.contains('ss-two-columns')};
  }finally{fault.audit=previous;}
}

module.exports=async({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:3840,height:2560},viewport:{width:3840,height:2560,scale}});
    try{
      await page.evaluate(()=>{
        window.__nativeCreditFixture=JSON.parse(model.payload);
        const state=window.__nativeCreditFault={rect:Element.prototype.getBoundingClientRect,query:Element.prototype.querySelectorAll,audit:false,stale:false,selectors:false};
        Element.prototype.getBoundingClientRect=function(){
          const result=state.rect.call(this);
          if(state.stale&&!state.audit&&this.classList.contains('ss-economy')&&this.closest('.ss-aggregate')){
            const width=state.rect.call(this.parentNode).width;
            return {x:result.x,y:result.y,left:result.left,right:result.left+width,top:result.top,bottom:result.bottom,width,height:result.height};
          }
          return result;
        };
        Element.prototype.querySelectorAll=function(selector){
          if(state.selectors&&!state.audit&&this.classList.contains('ss-economy')&&selector==='.ss-money-head, .ss-money-row:not(.ss-credit-pair)')return state.query.call(this,'.ss-money-head');
          return state.query.call(this,selector);
        };
      });
      // Explicit native widths do not shrink to conceal an excessive caption.
      await page.addStyleTag({content:'#ss-groups .ss-money-head > div, #ss-groups .ss-money-row:not(.ss-credit-pair) > div { flex-shrink:0 !important; }'});
      let sequence=0;
      async function publish(language,group,mode,width=1320,partial=false){
        await page.evaluate(({language,messages,group,mode,width,partial,scale,sequence})=>{
          const fault=window.__nativeCreditFault;fault.stale=mode==='stale'||mode==='combined';fault.selectors=mode==='selector'||mode==='combined';
          const payload=JSON.parse(JSON.stringify(__nativeCreditFixture)),scope=payload.scopes.launch;
          payload.account_key='synthetic-native-finance-'+scale+'-'+sequence;payload.localization={language,messages};
          payload.viewport={width:3840,height:2560,scale};payload.window_size=[width,1100];
          payload.appearance={window_settings:{background_transparency:0,maximized:false,restored_width:width,restored_height:1100}};
          const sample=scope[group][0];scope[group]=[0,1].map(index=>{
            const item=JSON.parse(JSON.stringify(sample)),stats=item.stats;item.id='native-finance-'+group+'-'+index;item.name='Synthetic native finance '+index;
            stats.battles=stats.observed_battles=14;stats.wn8_count=14;
            const ranges={xp_base:[154,558,1403],xp_received:[266,3111,13415],battle_wn8:[78,2016,8834],
              credits_income_base:[1234,15000,34567],credits_income_received:[4567,25000,45678],credits_costs:[1234,15000,23456],
              credits_net_base:[-22222,-10000,12345],credits_net_received:[-11111,10000,34567]};
            item.extrema_battles={};
            for(const [metric,[min,avg,max]]of Object.entries(ranges)){
              stats[metric]={count:14,min,avg,max,sum:avg*14};item.extrema_battles[metric]={};
              for(const statistic of ['min','max'])item.extrema_battles[metric][statistic]={id:item.id+'-'+metric+'-'+statistic,name:'Synthetic vehicle',map:'Synthetic map',started_at:1794000000,metric,statistic,value:stats[metric][statistic]};
            }
            const seven=index===1;
            stats.currencies={credits:{income_base:123456,income_base_count:14,income:seven?1485270:694213,income_count:14,
              costs:seven?1417829:250235,costs_count:14,net_base:seven?-1294373:-126779,net_base_count:14,net:seven?67441:443978,net_count:14},
              bonds:{income:50,income_count:14,costs:0,costs_count:14,net:50,net_count:14},gold:{income:0,income_count:14,costs:0,costs_count:14,net:0,net_count:14}};
            if(partial){stats.currencies.credits.income_base_count=stats.currencies.credits.net_base_count=5;stats.credits_income_base.count=stats.credits_net_base.count=5;}
            return item;
          });
          scope.ordering[group]={metric:'off',statistic:'avg',direction:'desc',chronology:'newest'};
          scope.pagination[group]={page:0,pages:1,total:2,page_size:40};scope.data_revision='native-finance-'+sequence;
          model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);document.getElementById('ss-scope-launch').onclick();document.getElementById('ss-group-'+group).onclick();
        },{language,messages:languages[language],group,mode,width,partial,scale,sequence:++sequence});
        await frames(page);
      }
      function intact(value,partial=false,adjacent=true){return value.cards.length===2&&value.cards.every((card,index)=>(!adjacent||card.adjacent)&&!card.failures.length&&card.costs===1&&card.sources===10&&
        card.values.join('|')===[partial?'—':'123456',index?'1485270':'694213',index?'-1417829':'-250235',partial?'—':index?'-1294373':'-126779',index?'+67441':'+443978'].join('|'));}
      for(const language of ['en','pl'])for(const mode of ['baseline','stale','selector','combined']){
        await publish(language,'vehicles',mode);const value=await page.evaluate(inspectNativeCredits,{scale});
        check('Native finance budgets keep both 560px lanes, complete totals and source controls contained '+language+'/'+mode+'/'+scale+'x: '+JSON.stringify(value),value.paired&&intact(value));
        if(mode==='stale'||mode==='combined')check('The stale native rectangle model exposes the previous stacked width '+language+'/'+mode+'/'+scale+'x',value.staleWidth>value.actualWidth+100);
      }
      for(const group of ['vehicles','maps','tiers']){
        await publish('pl',group,'combined',1320,true);const value=await page.evaluate(inspectNativeCredits,{scale});
        check('Native partial-base rows preserve adjacent complete finance columns '+group+'/'+scale+'x: '+JSON.stringify(value),value.paired&&intact(value,true));
      }
      for(const width of [550,863,1320]){
        await publish('pl','vehicles','combined',width);const value=await page.evaluate(inspectNativeCredits,{scale});
        check('Native finance reallocates all header, credit and Bonds columns after width changes '+width+'/'+scale+'x: '+JSON.stringify(value),intact(value));
      }
      await publish('pl','vehicles','combined');
      const inset=await page.evaluate(scale=>{
        window.__nativeCreditRetained=[...document.querySelectorAll('#ss-groups .ss-group')];
        return (document.getElementById('grz-session-stats').getBoundingClientRect().width-document.getElementById('ss-groups').getBoundingClientRect().width)/scale;
      },scale);
      for(const width of [400,560,720,560]){
        let viewportWidth=Math.round((width+inset+20)*scale),value;
        for(let attempt=0;attempt<2;attempt++){
          await page.setViewportSize({width:viewportWidth,height:2560});
          await page.evaluate(({viewportWidth,scale})=>{const payload=JSON.parse(model.payload);payload.viewport={width:viewportWidth,height:2560,scale};
            model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},{viewportWidth,scale});
          await frames(page);value=await page.evaluate(inspectNativeCredits,{scale});
          const difference=value.cards[0].bounds.width-width;
          if(Math.abs(difference)<=1)break;
          viewportWidth-=Math.round(difference*scale);
        }
        const retained=await page.evaluate(()=>[...document.querySelectorAll('#ss-groups .ss-group')].every((card,index)=>card===__nativeCreditRetained[index]));
        check('Retained native cards survive stale geometry through400→560→720→560 resize at '+width+'/'+scale+'x: '+JSON.stringify(value),
          retained&&intact(value,false,width>=500)&&value.cards.every(card=>Math.abs(card.bounds.width-width)<=1));
      }
      await page.setViewportSize({width:3840,height:2560});
      await publish('pl','vehicles','combined');
      const obsolete=await page.evaluate(inspectNativeCredits,{scale,legacy:true});
      check('The native guard reproduces and rejects the old stale-width credit overflow '+scale+'x: '+JSON.stringify(obsolete),obsolete.cards[0].failures.some(value=>value.includes('outside')||value.includes('text:')));
      await publish('pl','vehicles','combined');
      check('Rebuilding with the assigned native finance budget restores all columns '+scale+'x',intact(await page.evaluate(inspectNativeCredits,{scale})));
      const flushActions=await page.addStyleTag({content:'.ss-credit-extreme-actions { padding:0 !important; min-height:18rem !important; }'});
      const flush=await page.evaluate(inspectNativeCredits,{scale});
      check('The credit geometry guard rejects Min/Max buttons pasted against divider space '+scale+'x',
        flush.cards.some(card=>card.failures.includes('credit-action-divider-spacing')));
      await flushActions.evaluate(node=>node.remove());
    }finally{await page.close();}
  }
};
