/* Aggregate captions use one painted line while every figure stays complete. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let count=5;
  function next(){if(--count)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}));
module.exports=async({browser,nativeHost,check})=>{
  const catalog=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:3840,height:2560},viewport:{width:3840,height:2560,scale}});
    try{
      await page.evaluate(()=>{window.__aggregateCaptionFixture=JSON.parse(model.payload);});
      let sequence=0;
      async function publish(language,width,options={}){
        await page.evaluate(({language,messages,width,scale,options,sequence})=>{
          const payload=JSON.parse(JSON.stringify(__aggregateCaptionFixture)),scope=payload.scopes.launch;
          payload.account_key='synthetic-caption-'+scale+'-'+sequence;
          payload.viewport={width:3840,height:2560,scale};payload.window_size=[width,1100];
          payload.appearance={window_settings:{maximized:false,background_transparency:0,restored_width:width,restored_height:1100}};
          payload.localization={language,messages};
          if(options.longCaption)payload.localization.messages['xp.received']+=' — Synthetic deliberately extended caption';
          const sample=scope.vehicles[0];
          scope.vehicles=[0,1].map(index=>{
            const item=JSON.parse(JSON.stringify(sample)),stats=item.stats;
            item.id='synthetic-caption-'+index;item.name='Synthetic vehicle '+index;
            stats.battles=stats.observed_battles=3;stats.win_rate=66.7;stats.wn8=2100;stats.wn8_count=3;
            const values={xp_base:[154,558,1403],xp_received:[266,3111,13415],battle_wn8:[78,2016,8834],
              credits_income_base:[1000,40000,60000],credits_income_received:[2000,50000,70000],credits_costs:[1000,30000,50000],
              credits_net_base:[-20000,10000,20000],credits_net_received:[-10000,20000,30000]};
            item.extrema_battles={};
            for(const [metric,[min,avg,max]]of Object.entries(values)){
              stats[metric]={count:3,min,avg,max,sum:avg*3};item.extrema_battles[metric]={};
              for(const statistic of ['min','max'])item.extrema_battles[metric][statistic]={
                id:item.id+'-'+metric+'-'+statistic,name:'Synthetic vehicle',map:'Synthetic map',started_at:1794000000,
                metric,statistic,value:stats[metric][statistic]};
            }
            stats.currencies={credits:{income_base:1234567,income_base_count:3,income:1485270,income_count:3,
              costs:1417829,costs_count:3,net_base:-183262,net_base_count:3,net:67441,net_count:3},
              bonds:{income:50,income_count:3,costs:0,costs_count:3,net:50,net_count:3},
              gold:{income:0,income_count:3,costs:0,costs_count:3,net:0,net_count:3}};
            return item;
          });
          scope.ordering.vehicles={metric:'off',statistic:'avg',direction:'desc',chronology:'newest'};
          scope.pagination.vehicles={page:0,pages:1,total:2,page_size:40};scope.data_revision='caption-'+sequence;
          model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
          document.getElementById('ss-scope-launch').onclick();document.getElementById('ss-group-vehicles').onclick();
        },{language,messages:JSON.parse(JSON.stringify(catalog[language])),width,scale,options,sequence:++sequence});
        await frames(page);
      }
      async function geometry(){return page.locator('#ss-groups').evaluate((owner,scale)=>{
        const box=node=>{const r=node.getBoundingClientRect();return{left:r.left/scale,right:r.right/scale,top:r.top/scale,bottom:r.bottom/scale,width:r.width/scale,height:r.height/scale};};
        const inside=(a,b)=>a.left>=b.left-1.5&&a.right<=b.right+1.5&&a.top>=b.top-1.5&&a.bottom<=b.bottom+1.5;
        const ink=node=>{const range=document.createRange();range.selectNodeContents(node);return[...range.getClientRects()].filter(r=>r.width>0&&r.height>0)
          .map(r=>({left:r.left/scale,right:r.right/scale,top:r.top/scale,bottom:r.bottom/scale,width:r.width/scale,height:r.height/scale}));};
        return[...owner.querySelectorAll('.ss-group')].map(card=>{
          const bounds=box(card),performance=card.querySelector('.ss-performance'),economy=card.querySelector('.ss-economy'),failures=[];
          const labels=[...card.querySelectorAll('.ss-metric-name > .ss-cell-value,.ss-credit-label-text,.ss-credit-inline-label,.ss-group-kpi .ss-kpi-label,.ss-money-head > .ss-money-label,.ss-money-head > .ss-money-value,.ss-money-row:not(.ss-credit-pair) > .ss-money-label')]
            .filter(node=>box(node).width>0&&box(node).height>0&&node.textContent.trim());
          const captions=labels.map(node=>{
            const css=getComputedStyle(node),bounds=box(node),lines=[];
            for(const r of ink(node))if(!lines.some(top=>Math.abs(top-r.top)<1))lines.push(r.top);
            const extra=['paddingTop','paddingBottom','borderTopWidth','borderBottomWidth'].reduce((sum,key)=>sum+(parseFloat(css[key])||0)/scale,0),
              full=node.textContent,contract=node.classList.contains('ss-caption-ellipsis')&&node.classList.contains('ss-hover-help')&&
              css.whiteSpace==='nowrap'&&css.overflowX==='hidden'&&css.textOverflow==='ellipsis'&&
              node.getAttribute('data-ss-help')===full&&node.getAttribute('aria-label')===full&&node.getAttribute('aria-controls')==='ss-help-tooltip'&&node.getAttribute('title')===null;
            return{text:full,contract,lines:lines.length,height:bounds.height,lineHeight:parseFloat(css.lineHeight)/scale+extra,
              clipped:node.scrollWidth>node.clientWidth+1,contained:inside(bounds,box(card))};
          });
          const figures=[...card.querySelectorAll('.ss-metric-row .ss-table-text,.ss-money-row .ss-cell-value')];
          for(const node of figures){const cell=node.closest('.ss-metric-number,.ss-money-value');
            if(!cell||!ink(node).every(r=>inside(r,box(cell))))failures.push('number:'+node.textContent);
          }
          for(const action of card.querySelectorAll('.ss-metric-battle-link')){
            const cell=action.closest('.ss-metric-number,.ss-money-value'),cue=action.querySelector('.ss-extreme-link-cue');
            if(!cell||!inside(box(action),box(cell))||cue&&!inside(box(cue),box(cell)))failures.push('source:'+action.getAttribute('data-ss-source-metric'));
          }
          const first=performance.querySelector('.ss-metric-row'),pair=economy.querySelector('.ss-credit-pair');
          return{bounds,captions,failures,performance:box(performance),economy:box(economy),
            metricWidths:[...first.querySelectorAll(':scope > .ss-metric-number')].map(node=>box(node).width),
            financeWidths:['.ss-credit-income-column','.ss-credit-shared-cost','.ss-credit-net-column'].map(selector=>box(pair.querySelector(selector)).width),
            values:[...card.querySelectorAll('.ss-money-value[data-ss-metric] > .ss-cell-value')].map(node=>node.textContent.replace(/\s/g,'')),
            fonts:[...first.querySelectorAll(':scope > .ss-metric-number')].map(node=>parseFloat(getComputedStyle(node).fontSize)/scale)};
        });
      },scale);}
      const valid=cards=>cards.length===2&&cards.every(card=>!card.failures.length&&card.captions.length>=12&&
        card.captions.every(label=>label.contract&&label.contained&&label.lines===1&&label.height<=label.lineHeight+1.5)&&
        card.values.join('|')==='1234567|1485270|-1417829|-183262|+67441'&&card.fonts.every(size=>size>=16));
      const spreads=(compact,wide)=>wide.every((card,index)=>card.metricWidths.every((width,column)=>width>=compact[index].metricWidths[column]+6)&&
        card.financeWidths.every((width,column)=>width>=compact[index].financeWidths[column]+6));
      for(const language of Object.keys(catalog)){
        await publish(language,1320);const compact=await geometry();
        check('Compact aggregate captions stay on one clipped line with complete help and full figures '+language+'/'+scale+'x: '+JSON.stringify(compact),valid(compact));
        await publish(language,1800);const wide=await geometry();
        check('Wide aggregate captions stay on one line while full figures remain contained '+language+'/'+scale+'x: '+JSON.stringify(wide),valid(wide));
        check('Wide cards expand every performance and finance numeric lane instead of packing spare width into labels '+language+'/'+scale+'x: '+JSON.stringify({compact,wide}),spreads(compact,wide));
      }
      await publish('ru',1320,{longCaption:true});let current=await geometry();
      check('A deliberately long translated label is clipped without a second line at '+scale+'x',valid(current)&&current.some(card=>card.captions.some(label=>label.clipped)));
      const target=page.locator('#ss-groups .ss-group').first().locator('.ss-metric-row[data-ss-metric="xp_received"] .ss-caption-ellipsis');
      const full=await target.textContent();
      await page.locator('#ss-titlebar h1').hover();await page.locator('#ss-close').focus();
      await target.hover({position:{x:5,y:5}});
      const timers=await page.evaluate(()=>[...__grzTimers].filter(([,timer])=>String(timer.callback).includes('helpPending')).map(([id,timer])=>({id,delay:timer.delay})));
      check('A clipped caption schedules the existing custom 500ms help without a native title at '+scale+'x',
        timers.length===1&&timers[0].delay===500&&await page.locator('#ss-help-tooltip').isHidden()&&await target.getAttribute('title')===null);
      await page.evaluate(id=>{const timer=__grzTimers.get(id);__grzTimers.delete(id);timer.callback();},timers[0].id);
      check('Hover reveals the original complete caption through the owned tooltip at '+scale+'x',
        await page.locator('#ss-help-tooltip').isVisible()&&await page.locator('#ss-help-tooltip').textContent()===full&&
        await target.getAttribute('aria-describedby')==='ss-help-tooltip'&&await target.getAttribute('aria-expanded')==='true');
      await page.locator('#ss-titlebar h1').hover();await page.locator('#ss-close').focus();await frames(page);
      // A painted ellipsis differs from a hard clip while retaining identical
      // geometry and source text. This checks browser paint, not just a class.
      const ellipsis=await target.screenshot();
      await target.evaluate(node=>{node.style.textOverflow='clip';});await frames(page);const clipped=await target.screenshot();
      await target.evaluate(node=>{node.style.textOverflow='';});await frames(page);const restored=await target.screenshot();
      check('An overflowing caption paints an ellipsis instead of a hard clip at '+scale+'x',!ellipsis.equals(clipped)&&ellipsis.equals(restored));
      await target.evaluate(node=>{node.style.whiteSpace='normal';node.style.overflow='visible';node.style.textOverflow='clip';});
      check('The caption guard rejects the former wrapped/visible text layout at '+scale+'x',!valid(await geometry()));
      await target.evaluate(node=>{node.style.whiteSpace='';node.style.overflow='';node.style.textOverflow='';});await frames(page);
      check('Restoring caption styles restores the single-line contract at '+scale+'x',valid(await geometry()));
      await publish('ru',1320);const compactBaseline=await geometry();
      await publish('ru',1800);const wide=await geometry();
      check('The wide allocation expands both numeric tables before the packed-layout negative control at '+scale+'x',spreads(compactBaseline,wide));
      const old=await page.addStyleTag({content:[0,1,2].map((index)=>
        '#ss-groups .ss-performance .ss-metric-number:nth-child('+(index+2)+') { width:'+compactBaseline[0].metricWidths[index]+'rem !important; flex:0 0 '+compactBaseline[0].metricWidths[index]+'rem !important; }').join('\n')});
      check('The breathing-space guard rejects fixed packed numeric lanes in a wide card at '+scale+'x',!spreads(compactBaseline,await geometry()));
      await old.evaluate(node=>node.remove());await frames(page);
      check('Removing the packed-layout override restores numeric breathing space at '+scale+'x',spreads(compactBaseline,await geometry()));
      await publish('ru',1800,{longCaption:true});
      await page.evaluate(()=>{window.__aggregateCaptionCards=[...document.querySelectorAll('#ss-groups .ss-group')];});
      const inset=await page.evaluate(scale=>(document.getElementById('grz-session-stats').getBoundingClientRect().width-
        document.getElementById('ss-groups').getBoundingClientRect().width)/scale,scale),resized=[];
      for(const width of [560,720,560]){
        let viewportWidth=Math.round((width+inset+20)*scale),value;
        for(let attempt=0;attempt<2;attempt++){
          await page.setViewportSize({width:viewportWidth,height:2560});
          await page.evaluate(({viewportWidth,scale})=>{const payload=JSON.parse(model.payload);
            payload.viewport={width:viewportWidth,height:2560,scale};model.payload=JSON.stringify(payload);
            __grzEvents['viewEnv.onDataChanged']();},{viewportWidth,scale});
          await frames(page);value=await geometry();
          const difference=value[0].bounds.width-width;
          if(Math.abs(difference)<=1)break;
          viewportWidth-=Math.round(difference*scale);
        }
        const retained=await page.evaluate(()=>[...document.querySelectorAll('#ss-groups .ss-group')]
          .every((card,index)=>card===__aggregateCaptionCards[index]));
        resized.push(value);
        check('Retained cards keep ellipsis and complete help through live 560→720→560 resize at '+width+'/'+scale+'x',
          retained&&valid(value)&&value.every(card=>Math.abs(card.bounds.width-width)<=1));
      }
      check('Live resize expands numeric lanes and restores their original widths at '+scale+'x',
        spreads(resized[0],resized[1])&&resized[0].every((card,index)=>['metricWidths','financeWidths'].every(key=>
          card[key].every((width,column)=>Math.abs(width-resized[2][index][key][column])<=1))));
    }finally{await page.close();}
  }
};
