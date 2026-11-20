/* Base-credit sources follow received coverage, independently per field. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let count=4;
  function next(){if(--count)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}));
module.exports=async({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const scenarios=[{name:'absent',income:0,net:0},{name:'partial',income:2,net:1},
    {name:'independent',income:4,net:2},{name:'complete',income:4,net:4}];
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:3840,height:2400},viewport:{width:3840,height:2400,scale}});
    try{
      await page.evaluate(()=>{window.__baseCreditFixture=JSON.parse(model.payload);});
      let sequence=0;
      async function publish(language,scenario,options={}){
        const revision=++sequence;
        await page.evaluate(({language,messages,scenario,options,scale,revision})=>{
          const payload=JSON.parse(JSON.stringify(__baseCreditFixture)),scope=payload.scopes.launch,total=options.total||4,
            period=options.period||'base-availability-'+revision;
          payload.account_key=options.account||'synthetic-base-availability-'+scale+'-'+revision;
          payload.window_size=[1320,1100];payload.viewport={width:3840,height:2400,scale};
          payload.appearance={window_settings:{maximized:false,background_transparency:0,restored_width:1320,restored_height:1100}};
          payload.localization={language,messages};scope.period_id=period;scope.data_revision='base-availability-'+revision;
          function fill(stats,owner){
            Object.assign(stats,{battles:total,observed_battles:total+(options.pending||0),wn8:2100,wn8_count:total,win_rate:50});
            const ranges={xp_base:[154,558,1403],xp_received:[266,3111,13415],battle_wn8:[78,2016,8834],
              credits_income_base:[10000,25000,40000],credits_net_base:[-5000,12500,25000],
              credits_income_received:[20000,50000,80000],credits_net_received:[10000,37500,60000],credits_costs:[5000,12500,20000]},references={};
            for(const [metric,[min,avg,max]]of Object.entries(ranges)){
              const count=metric==='credits_income_base'?scenario.income:metric==='credits_net_base'?scenario.net:total;
              stats[metric]={count,min,avg,max,sum:avg*count};references[metric]={};
              for(const statistic of ['min','max'])references[metric][statistic]={id:owner+'-'+period+'-'+metric+'-'+statistic,
                metric,statistic,value:statistic==='min'?min:max,name:'Synthetic source vehicle',map:'Synthetic source map',started_at:1794000000};
            }
            stats.currencies={credits:{income_base:options.nullBase?null:100000,income_base_count:scenario.income,
              net_base:options.nullBase?null:50000,net_base_count:scenario.net,income:200000,income_count:total,
              costs:50000,costs_count:total,net:150000,net_count:total},
              bonds:{income:50,income_count:total,costs:0,costs_count:total,net:50,net_count:total}};
            if(options.noBaseReferences)for(const metric of ['credits_income_base','credits_net_base'])delete references[metric];
            return references;
          }
          scope.extrema_battles=fill(scope.summary,'summary');
          for(const group of ['maps','vehicles','tiers']){
            const item=scope[group][0];item.id='base-availability-'+group;item.extrema_battles=fill(item.stats,group);
            scope[group]=[item];scope.pagination[group]={page:0,pages:1,total:1,page_size:40};
            scope.ordering[group]={metric:options.sortMetric||'off',statistic:options.statistic||'min',direction:'desc',chronology:group==='tiers'?'tier_desc':'newest'};
          }
          if(options.timeline){
            payload.scopes.timeline=JSON.parse(JSON.stringify(scope));payload.scopes.timeline.from_point=options.from||'';
            payload.scopes.timeline.to_point='';payload.scopes.timeline.time_points=[];
          }
          delete scope.battle_focus;model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
          document.getElementById(options.timeline?'ss-scope-manual':'ss-scope-launch').onclick();
          document.getElementById('ss-group-'+(options.group||'maps')).onclick();
        },{language,messages:languages[language],scenario,options,scale,revision});
        await frames(page);
        return options.period||'base-availability-'+revision;
      }
      async function inspect(language,scenario,options={}){
        return page.evaluate(({messages,scenario,options,scale})=>{
          const total=options.total||4,format=(key,args)=>String(messages[key]).replace(/\{(\d+)\}/g,(whole,index)=>args[index]),
            normalize=text=>text.replace(/\s/g,'');
          function panel(owner,prefix){
            const problems=[],base=[];
            for(const [metric,count]of [['credits_income_base',scenario.income],['credits_net_base',scenario.net]]){
              const available=count>0&&count===total&&(!options.nullBase||options.pending),buttons=[...owner.querySelectorAll('.ss-metric-battle-link[data-ss-source-metric="'+metric+'"]')],
                expectedCount=available&&options.noBaseReferences?0:2;
              if(buttons.length!==expectedCount)problems.push(metric+':count:'+buttons.length);
              for(const button of buttons){
                const statistic=button.getAttribute('data-ss-extreme'),caption=messages['metric.'+statistic],
                  reason=format('sort.base_extrema_unavailable',[messages['sort.'+metric],String(count),String(total)]),
                  label=button.querySelector('.ss-metric-action-label'),css=getComputedStyle(button),box=button.getBoundingClientRect();
                if(!['min','max'].includes(statistic)||!button.classList.contains('ss-metric-extreme-action')||!label||label.textContent!==caption||box.width/scale<20||box.height/scale<18)problems.push(metric+':caption-or-size');
                if(available){
                  if(button.disabled||button.getAttribute('aria-disabled')==='true'||button.classList.contains('ss-metric-action-disabled')||
                    button.getAttribute('data-battle-id')!==prefix+'-'+options.period+'-'+metric+'-'+statistic||typeof button.onclick!=='function')problems.push(metric+':enabled-source');
                }else{
                  if(!button.disabled||button.getAttribute('aria-disabled')!=='true'||!button.classList.contains('ss-metric-action-disabled')||
                    button.getAttribute('data-battle-id')!==null||button.onclick!==null||button.getAttribute('data-ss-help')!==reason||
                    button.getAttribute('aria-label')!==caption+': '+reason||button.getAttribute('aria-controls')!=='ss-help-tooltip'||
                    button.getAttribute('aria-expanded')!=='false'||button.classList.contains('ss-sort-active-value')||button.hasAttribute('data-ss-sort-active'))problems.push(metric+':disabled-contract');
                  if(css.color!=='rgb(150, 156, 150)'||css.borderTopColor!=='rgb(70, 76, 70)'||css.backgroundColor!=='rgb(43, 48, 43)'||
                    css.outlineStyle!=='none'||css.boxShadow!=='none'||css.cursor!=='default'||
                    Math.abs(Number(css.opacity)-0.45)>0.01||getComputedStyle(label).color!=='rgb(150, 156, 150)')problems.push(metric+':disabled-paint');
                }
                base.push({metric,statistic,disabled:button.disabled});
              }
            }
            const others=[...owner.querySelectorAll('.ss-metric-battle-link')].filter(button=>!/^credits_(income|net)_base$/.test(button.getAttribute('data-ss-source-metric')));
            if(others.length!==12||!others.every(button=>!button.disabled&&button.getAttribute('aria-disabled')!=='true'&&typeof button.onclick==='function'&&
              button.getAttribute('data-battle-id')===prefix+'-'+options.period+'-'+button.getAttribute('data-ss-source-metric')+'-'+button.getAttribute('data-ss-extreme')))problems.push('unrelated-sources');
            const value=metric=>normalize(owner.querySelector('.ss-money-value[data-ss-metric="'+metric+'"] > .ss-cell-value').textContent),
              expected=[scenario.income===total&&(!options.nullBase||options.pending)?'100000':'—','200000','-50000',
                scenario.net===total&&(!options.nullBase||options.pending)?'+50000':'—','+150000'],
              values=['credits_income_base','credits_income_received','credits_costs','credits_net_base','credits_net_received'].map(value);
            if(values.join('|')!==expected.join('|'))problems.push('amounts:'+values.join('|'));
            return {problems,base,otherSources:others.length,values};
          }
          return {summary:panel(document.getElementById('ss-summary'),'summary'),
            card:panel(document.querySelector('#ss-groups .ss-group'),options.group||'maps')};
        },{messages:languages[language],scenario,options,scale});
      }
      const valid=result=>[result.summary,result.card].every(owner=>!owner.problems.length);
      for(const language of Object.keys(languages))for(const scenario of scenarios){
        for(const group of language==='en'?['maps','vehicles','tiers']:['maps']){
          const period=await publish(language,scenario,{group}),result=await inspect(language,scenario,{group,period});
          check('Base income/net Min/Max follow independent whole-period counts while other sources and totals survive '+language+'/'+scenario.name+'/'+group+'/'+scale+'x: '+JSON.stringify(result),valid(result));
          if(language==='en'&&group==='maps'&&scenario.name==='partial'){
            const disabled=page.locator('#ss-groups .ss-metric-action-disabled[data-ss-source-metric="credits_income_base"][data-ss-extreme="min"]'),
              tooltip=page.locator('#ss-help-tooltip'),reason=await disabled.getAttribute('data-ss-help');
            await page.locator('#ss-titlebar h1').hover();await page.locator('#ss-close').focus();
            await disabled.hover();
            const timers=await page.evaluate(()=>[...__grzTimers].filter(([,timer])=>String(timer.callback).includes('helpPending'))
              .map(([id,timer])=>({id,delay:timer.delay})));
            check('Disabled base-source hover retains the owned 500ms help delay at '+scale+'x: '+JSON.stringify(timers),
              timers.length===1&&timers[0].delay===500&&await tooltip.isHidden());
            await page.evaluate(id=>{const timer=__grzTimers.get(id);__grzTimers.delete(id);timer.callback();},timers[0].id);
            check('Disabled base-source hover exposes its complete localized reason and tooltip ownership at '+scale+'x',
              await tooltip.isVisible()&&await tooltip.textContent()===reason&&await disabled.getAttribute('aria-expanded')==='true'&&
              await disabled.getAttribute('aria-describedby')==='ss-help-tooltip');
            await page.locator('#ss-titlebar h1').hover();await page.locator('#ss-close').focus();
            const inert=await page.evaluate(()=>{const before=__grzCommands.filter(command=>command.action==='battle_select').length,
              buttons=[...document.querySelectorAll('#ss-summary .ss-metric-action-disabled,#ss-groups .ss-metric-action-disabled')];
              for(const button of buttons){button.click();button.dispatchEvent(new MouseEvent('click',{bubbles:true}));}
              return {buttons:buttons.length,commands:__grzCommands.filter(command=>command.action==='battle_select').length-before};});
            check('Disabled base sources ignore native and dispatched clicks in summary and cards at '+scale+'x: '+JSON.stringify(inert),inert.buttons===8&&inert.commands===0);
          }
        }
      }
      for(const [scenario,options]of [[scenarios[3],{nullBase:true}],[scenarios[3],{noBaseReferences:true}],[scenarios[1],{noBaseReferences:true}]]){
        const period=await publish('en',scenario,options),result=await inspect('en',scenario,{...options,period});
        check('Base availability and source validity stay independent at '+scale+'x/'+scenario.name+'/'+JSON.stringify(options)+': '+JSON.stringify(result),valid(result));
      }
      for(const group of ['maps','vehicles','tiers']){
        for(const scenario of [scenarios[2],scenarios[3]]){
          const options={group,pending:3,nullBase:true,sortMetric:'credits_income_base',statistic:'sum'};
          const period=await publish('en',scenario,options),result=await inspect('en',scenario,{...options,period});
          check('Pending battles preserve known base sums and sources in older '+group+' projections at '+scale+'x: '+JSON.stringify(result),
            valid(result)&&!await page.locator('#ss-sort-data-warning').isVisible()&&
            await page.locator('#ss-groups [data-ss-sort-active="credits_income_base"]').count()===1);
        }
      }
      const partial=scenarios[1],period=await publish('en',partial,{sortMetric:'credits_income_base'}),sorted=await inspect('en',partial,{period});
      check('Sorting an incomplete base metric never highlights its disabled source placeholder at '+scale+'x: '+JSON.stringify(sorted),valid(sorted));
      const account='synthetic-base-range-'+scale;
      await publish('en',partial,{account,timeline:true,period:'timeline:all',from:''});
      const beforeRange=await inspect('en',partial,{period:'timeline:all'});
      check('The full Timeline range starts with unavailable base extrema at '+scale+'x: '+JSON.stringify(beforeRange),valid(beforeRange));
      const complete={name:'narrow-range',income:1,net:1},rangeOptions={account,timeline:true,period:'timeline:complete',from:'synthetic-start',total:1,pending:3};
      await publish('en',complete,rangeOptions);const afterRange=await inspect('en',complete,rangeOptions);
      check('A narrower complete Timeline range enables newly owned base extrema at '+scale+'x: '+JSON.stringify(afterRange),valid(afterRange));
      const commandsBefore=await page.evaluate(()=>__grzCommands.filter(command=>command.action==='battle_select').length);
      await page.locator('#ss-summary .ss-metric-battle-link[data-ss-source-metric="credits_income_base"][data-ss-extreme="max"]').click();
      const commands=await page.evaluate(()=>__grzCommands.filter(command=>command.action==='battle_select')),
        command=commands[commands.length-1];
      check('Enabled base extrema navigate using the new Timeline range ownership at '+scale+'x: '+JSON.stringify(command),
        commands.length===commandsBefore+1&&command.id==='summary-timeline:complete-credits_income_base-max'&&command.scope==='timeline'&&
        command.period_id==='timeline:complete'&&command.account_key===account);
    }finally{await page.close();}
  }
};
