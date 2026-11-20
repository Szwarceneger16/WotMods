/* Summary financial modes use each currency field's actual samples and scope. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let count=5;
  function next(){if(--count)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}));
const samples={credits:{income_base:[50,500,1500,2350],income:[100,2000,3000],costs:[100,800],net_base:[-10,200,300,810],net:[-100,1600,2500]},
  bonds:{income:[0,5,40],costs:[6],net:[-6,40]},gold:{income:[15],costs:[],net:[15]}};
const cancellationSamples={...samples,credits:{income_base:[100,12345788,0,0],income:[100,12345788,0,0],costs:[12345778,100,0,0],
  net_base:[-12345678,12345688,0,0],net:[-12345678,12345688,0,0]}};
const nearZeroSamples={credits:{income_base:[0,0,0],income:[0,0,2],costs:[0,0,1],net_base:[0,0,-1],net:[0,0,1]},
  bonds:{income:[0,0,0],costs:[0,0,1],net:[0,0,-1]},gold:{income:[0,0,2],costs:[0,0,1],net:[0,0,1]}};
module.exports=async({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:3840,height:2600},viewport:{width:3840,height:2600,scale}});
    try{
      await page.evaluate(()=>{window.__summaryFinanceFixture=JSON.parse(model.payload);});
      let sequence=0;
      async function publish(language,options={}){
        const period=options.period||'summary-finance-'+(++sequence),account=options.account||'synthetic-summary-finance-'+scale+'-'+sequence;
        await page.evaluate(({language,messages,options,samples,period,account,scale})=>{
          const payload=JSON.parse(JSON.stringify(__summaryFinanceFixture)),scope=payload.scopes.launch,total=options.nearZero?3:options.narrow?2:4,width=options.width||980;
          payload.account_key=account;payload.window_size=[width,1100];payload.viewport={width:3840,height:2600,scale};payload.localization={language,messages};
          payload.appearance={window_settings:{maximized:false,background_transparency:0,restored_width:width,restored_height:1100}};
          scope.period_id=period;scope.data_revision=period+'-'+(options.factor||1);delete scope.battle_focus;
          function prepare(stats,owner){
            Object.assign(stats,{battles:total,observed_battles:total+(options.pending||0),wn8:2100,wn8_count:total,win_rate:50});
            const currencies={},distributions={},references={},factor=options.factor||1;
            for(const [currency,fields]of Object.entries(samples)){
              currencies[currency]={};distributions[currency]={};
              for(const [field,original]of Object.entries(fields)){
                let values=(options.narrow?original.slice(0,2):original).map(value=>value*factor);
                if(options.partialBase&&currency==='credits'&&field==='income_base')values=values.slice(0,2);
                if(options.partialBase&&currency==='credits'&&field==='net_base')values=[];
                const count=values.length,sum=count?values.reduce((sum,value)=>sum+value,0):null,
                  data={count,sum,min:count?Math.min(...values):null,avg:count?sum/count:null,max:count?Math.max(...values):null};
                distributions[currency][field]=data;currencies[currency][field]=sum;currencies[currency][field+'_count']=count;
                if(currency==='credits'){
                  const metric=field==='income_base'?'credits_income_base':field==='net_base'?'credits_net_base':
                    field==='income'?'credits_income_received':field==='net'?'credits_net_received':'credits_costs';
                  stats[metric]=JSON.parse(JSON.stringify(data));references[metric]={};
                  for(const statistic of ['min','max'])if(count)references[metric][statistic]={id:owner+'-'+period+'-'+metric+'-'+statistic,
                    metric,statistic,value:data[statistic],name:'Synthetic finance source',map:'Synthetic source map',started_at:1794000000};
                }
              }
            }
            if(options.partialBase||options.pending){currencies.credits.income_base=null;currencies.credits.net_base=null;}
            stats.currencies=currencies;
            if(options.legacySeries)delete stats.currency_series;else stats.currency_series=distributions;
            for(const [metric,values]of Object.entries({xp_base:[154,558,1403],xp_received:[266,3111,13415],battle_wn8:[78,2016,8834]})){
              stats[metric]={count:total,min:values[0],avg:values[1],max:values[2],sum:values[1]*total};references[metric]={};
              for(const statistic of ['min','max'])references[metric][statistic]={id:owner+'-'+period+'-'+metric+'-'+statistic,
                metric,statistic,value:stats[metric][statistic],name:'Synthetic performance source',map:'Synthetic source map',started_at:1794000000};
            }
            return references;
          }
          scope.extrema_battles=prepare(scope.summary,'summary');
          for(const group of ['maps','vehicles','tiers']){
            const item=scope[group][0];item.id='summary-finance-'+group;item.extrema_battles=prepare(item.stats,group);
            item.battle_list={page:0,pages:1,total:1,page_size:10,items:[{id:'synthetic-visible-history',name:'Synthetic history vehicle',map:'Synthetic history map',started_at:1794000000,outcome:'win'}]};
            scope[group]=[item];scope.pagination[group]={page:0,pages:1,total:1,page_size:40};
            scope.ordering[group]={metric:'off',statistic:'avg',direction:'desc',chronology:group==='tiers'?'tier_desc':'newest'};
          }
          if(options.timeline){payload.scopes.timeline=JSON.parse(JSON.stringify(scope));payload.scopes.timeline.from_point=options.narrow?'synthetic-range-start':'';
            payload.scopes.timeline.to_point='';payload.scopes.timeline.time_points=[];}
          model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
          document.getElementById(options.timeline?'ss-scope-manual':'ss-scope-launch').onclick();document.getElementById('ss-group-maps').onclick();
        },{language,messages:languages[language],options,samples:options.nearZero?nearZeroSamples:options.cancellation?cancellationSamples:samples,period,account,scale});
        // Every fixture requests a wide window; let its existing resize promotion
        // finish before menu interactions so the initial layout is not still moving.
        await page.waitForFunction(()=>document.getElementById('ss-list-controls').getAttribute('data-filter-layout')==='wide');
        await frames(page);return {period,account};
      }
      async function capture(){await page.evaluate(()=>{
        const economy=document.querySelector('#ss-summary .ss-economy'),head=economy.querySelector('.ss-money-head');
        window.__summaryFinanceNodes={control:document.getElementById('ss-summary-finance-statistic'),head,
          title:head.querySelector('.ss-summary-table-title'),height:head.getBoundingClientRect().height,
          figures:[...economy.querySelectorAll('.ss-cell-value')],sources:[...document.querySelectorAll('#ss-summary .ss-metric-battle-link')].map(node=>({node,onclick:node.onclick,
            id:node.getAttribute('data-battle-id'),help:node.getAttribute('data-ss-help'),disabled:node.disabled})),
          cards:[...document.querySelectorAll('#ss-groups .ss-group')],more:[...document.querySelectorAll('#ss-groups .ss-map-more-button')],
          rows:[...economy.children].filter(node=>node.classList.contains('ss-money-row')||node.classList.contains('ss-money-head')).length};
      });}
      async function choose(mode){
        await page.locator('#ss-summary-finance-statistic .ss-select-trigger').click();
        await page.locator('#ss-options-summary-finance-statistic [data-value="'+mode+'"]').click();await frames(page);
      }
      async function inspect(language,mode,options={}){return page.evaluate(({messages,mode,scale})=>{
        const economy=document.querySelector('#ss-summary .ss-economy'),control=document.getElementById('ss-summary-finance-statistic'),saved=__summaryFinanceNodes,
          head=economy.querySelector('.ss-money-head'),title=control.closest('.ss-summary-table-title'),trigger=control.querySelector('.ss-select-trigger'),
          box=node=>{const r=node.getBoundingClientRect();return {left:r.left/scale,right:r.right/scale,top:r.top/scale,bottom:r.bottom/scale,width:r.width/scale,height:r.height/scale};},
          inside=(part,owner)=>part.left>=owner.left-1&&part.right<=owner.right+1&&part.top>=owner.top-1&&part.bottom<=owner.bottom+1,
          cells=[...economy.querySelectorAll('[data-ss-finance-field]')].map(cell=>{
            const figure=cell.querySelector(':scope > .ss-cell-value'),range=document.createRange();range.selectNodeContents(figure);
            const bounds=box(cell),ink=[...range.getClientRects()].filter(part=>part.width>0&&part.height>0).map(part=>({left:part.left/scale,right:part.right/scale,top:part.top/scale,bottom:part.bottom/scale}));
            return {currency:cell.getAttribute('data-ss-finance-currency'),field:cell.getAttribute('data-ss-finance-field'),mode:cell.getAttribute('data-ss-finance-statistic'),
              count:Number(cell.getAttribute('data-ss-finance-count')),total:Number(cell.getAttribute('data-ss-finance-total')),raw:figure.textContent,text:figure.textContent.replace(/\s/g,''),
              negative:cell.classList.contains('ss-negative'),positive:cell.classList.contains('ss-positive'),unknown:cell.classList.contains('ss-unknown'),
              help:figure.getAttribute('data-ss-help'),label:figure.getAttribute('aria-label'),controls:figure.getAttribute('aria-controls'),tabindex:figure.getAttribute('tabindex'),
              hovered:figure.classList.contains('ss-hover-help'),contained:ink.length>0&&ink.every(part=>inside(part,bounds))};
          });
        const options=[...control.querySelectorAll('[data-value]')].map(node=>({value:node.getAttribute('data-value'),text:node.textContent,selected:node.getAttribute('aria-selected')})),
          sameNodes=saved.control===control&&saved.head===head&&saved.title===title&&saved.figures.every((node,index)=>node===economy.querySelectorAll('.ss-cell-value')[index])&&
            saved.sources.every(({node,onclick,id,help,disabled})=>document.contains(node)&&node.onclick===onclick&&node.getAttribute('data-battle-id')===id&&node.getAttribute('data-ss-help')===help&&node.disabled===disabled)&&
            saved.cards.every((node,index)=>node===document.querySelectorAll('#ss-groups .ss-group')[index])&&
            saved.more.length>0&&saved.more.every((node,index)=>node===document.querySelectorAll('#ss-groups .ss-map-more-button')[index]);
        return {cells,options,mode:economy.getAttribute('data-ss-finance-statistic'),sameNodes,sourceCount:saved.sources.length,
          panelWidth:document.getElementById('grz-session-stats').getBoundingClientRect().width/scale,
          controlLabel:trigger.querySelector('.ss-control-label').textContent,aria:trigger.getAttribute('aria-label'),valueText:trigger.getAttribute('aria-valuetext'),
          infoCount:title.querySelectorAll('.ss-info-button').length,infoLabel:title.querySelector('.ss-info-button')&&title.querySelector('.ss-info-button').getAttribute('aria-label'),
          role:trigger.getAttribute('role'),menuRole:control.querySelector('.ss-select-options').getAttribute('role'),menuAria:control.querySelector('.ss-select-options').getAttribute('aria-label'),
          closed:trigger.getAttribute('aria-expanded')==='false'&&getComputedStyle(control.querySelector('.ss-select-options')).display==='none',
          noNewRow:head.contains(control)&&title===saved.title&&box(title).height<=27&&box(trigger).height<=27&&inside(box(trigger),box(head))&&
            Math.abs(head.getBoundingClientRect().height-saved.height)<=scale&&
            [...economy.children].filter(node=>node.classList.contains('ss-money-row')||node.classList.contains('ss-money-head')).length===saved.rows};
      },{messages:languages[language],mode,scale});}
      function valid(result,language,mode,options={}){
        const messages=languages[language],caption=messages['finance.statistic_'+(mode==='sum'?'all':mode)],total=options.nearZero?3:options.narrow?2:4,
          expected=[];
        for(const [currency,fields]of Object.entries(options.nearZero?nearZeroSamples:options.cancellation?cancellationSamples:samples))for(const [field,original]of Object.entries(fields)){
          let values=(options.narrow?original.slice(0,2):original).map(value=>value*(options.factor||1));
          if(options.partialBase&&currency==='credits'&&field==='income_base')values=values.slice(0,2);
          if(options.partialBase&&currency==='credits'&&field==='net_base')values=[];
          const count=values.length,sum=values.reduce((sum,value)=>sum+value,0),base=currency==='credits'&&field.endsWith('_base');
          let value=!count||base&&count!==total?null:mode==='sum'?sum:mode==='min'?Math.min(...values):mode==='max'?Math.max(...values):sum/count;
          if(options.legacySeries&&currency!=='credits'&&(mode==='min'||mode==='max'))value=null;
          if(mode==='avg'&&value!==null&&Math.abs(value)<0.5)value=0;
          const digits=value===null?null:Math.round(Math.abs(value)),text=digits===null?'—':field==='costs'?(value===0?'0':'-'+digits):
            field==='net'||field==='net_base'?(value>0?'+':value<0?'-':'')+digits:String(Math.round(value));
          expected.push({currency,field,count,text,value});
        }
        const observed=total+(options.pending||0),
          reason=(count)=>String(messages['finance.statistic_help']).replace('{0}',caption).replace('{1}',String(count)).replace('{2}',String(observed));
        return result.mode===mode&&result.sameNodes&&result.sourceCount===16&&result.noNewRow&&result.closed&&result.role==='combobox'&&result.menuRole==='listbox'&&
          result.infoCount===1&&result.infoLabel===messages['help.info']+': '+messages['finance.period']&&
          result.aria===messages['finance.period']+': '+messages['finance.statistic']&&result.menuAria===result.aria&&result.controlLabel===caption&&result.valueText===caption&&
          result.options.map(option=>option.value).join('|')==='sum|min|avg|max'&&result.options.every(option=>option.text===messages['finance.statistic_'+(option.value==='sum'?'all':option.value)]&&option.selected===String(option.value===mode))&&
          result.cells.length===expected.length&&expected.every(wanted=>{
            const cell=result.cells.find(cell=>cell.currency===wanted.currency&&cell.field===wanted.field);
            return cell&&cell.mode===mode&&cell.count===wanted.count&&cell.total===observed&&cell.text===wanted.text&&cell.unknown===(wanted.value===null)&&cell.contained&&
              (wanted.field!=='net'&&wanted.field!=='net_base'||cell.negative===(wanted.value!==null&&wanted.value<0)&&cell.positive===(wanted.value!==null&&wanted.value>0))&&
              (mode==='sum'?!cell.hovered&&cell.help===null&&cell.tabindex===null:cell.hovered&&cell.help===reason(wanted.count)&&cell.label===cell.raw+': '+cell.help&&cell.controls==='ss-help-tooltip'&&cell.tabindex==='0');
          });
      }
      for(const language of Object.keys(languages)){
        await publish(language);
        if(language==='en')check('Summary finance exposes one mode selector in its existing header at '+scale+'x',await page.locator('#ss-summary-finance-statistic').count()===1);
        await capture();const initial=await inspect(language,'sum');
        check('Summary finance defaults to localized All inside its existing header and retains full totals '+language+'/'+scale+'x: '+JSON.stringify(initial),valid(initial,language,'sum'));
        for(const mode of ['min','avg','max','sum']){
          await choose(mode);const result=await inspect(language,mode);
          check('Summary '+mode+' uses each credit, Bonds and Gold sample/count without replacing source controls or cards '+language+'/'+scale+'x: '+JSON.stringify(result),valid(result,language,mode));
        }
      }
      for(const options of [{partialBase:true},{legacySeries:true},{pending:3},{pending:3,partialBase:true}]){
        await publish('en',options);await capture();
        for(const mode of ['min','avg','max','sum']){
          await choose(mode);const result=await inspect('en',mode,options);
          check('Summary modes preserve received base totals while handling missing fields and older payloads at '+scale+'x/'+mode+'/'+JSON.stringify(options)+': '+JSON.stringify(result),valid(result,'en',mode,options));
        }
      }
      await publish('en',{cancellation:true});await capture();const cancellationAll=await inspect('en','sum');
      check('Small cancelled All net totals coexist with complete long signed source amounts at '+scale+'x: '+JSON.stringify(cancellationAll),
        valid(cancellationAll,'en','sum',{cancellation:true})&&cancellationAll.cells.filter(cell=>cell.currency==='credits'&&['net','net_base'].includes(cell.field)).every(cell=>cell.text==='+10'));
      for(const mode of ['min','avg','max','sum']){
        await choose(mode);const result=await inspect('en',mode,{cancellation:true});
        check('Long signed cancelling extrema stay complete and contained when summary mode changes at '+scale+'x/'+mode+': '+JSON.stringify(result),valid(result,'en',mode,{cancellation:true}));
      }
      await publish('en',{nearZero:true});await capture();
      for(const mode of ['min','avg','max','sum']){
        await choose(mode);const result=await inspect('en',mode,{nearZero:true}),
          neutral=result.cells.filter(cell=>['costs','net','net_base'].includes(cell.field)).every(cell=>cell.text==='0'&&!cell.positive&&!cell.negative&&!cell.unknown);
        check('Tiny fractional averages paint neutral zero while Min/Max and All retain true signed amounts at '+scale+'x/'+mode+': '+JSON.stringify(result),
          valid(result,'en',mode,{nearZero:true})&&(mode!=='avg'||neutral));
      }
      const account='synthetic-summary-finance-range-'+scale;
      await publish('en',{account,timeline:true,period:'summary-mode:all'});await capture();await choose('avg');
      await page.locator('#ss-resize-grip').evaluate(grip=>{for(let index=0;index<34;index++)
        grip.dispatchEvent(new KeyboardEvent('keydown',{key:'ArrowRight',bubbles:true,cancelable:true}));});
      await frames(page);await capture();const widened=await inspect('en','avg');
      check('Live window widening preserves the selected summary finance mode and readable values at '+scale+'x: '+JSON.stringify(widened),
        widened.panelWidth>=1700&&valid(widened,'en','avg'));
      await publish('en',{account,timeline:true,period:'summary-mode:narrow',narrow:true,width:1800});await capture();
      const narrowed=await inspect('en','avg',{narrow:true});
      check('Summary mode survives a wider window and new Timeline range while using its new field samples at '+scale+'x: '+JSON.stringify(narrowed),narrowed.panelWidth>=1700&&valid(narrowed,'en','avg',{narrow:true}));
      await publish('pl',{account,timeline:true,period:'summary-mode:narrow',narrow:true,width:1800,factor:2});await capture();
      const revised=await inspect('pl','avg',{narrow:true,factor:2});
      check('A new same-range snapshot and language update recompute the selected mode from current values at '+scale+'x: '+JSON.stringify(revised),valid(revised,'pl','avg',{narrow:true,factor:2}));
      const before=await page.evaluate(()=>__grzCommands.filter(command=>command.action==='battle_select').length);
      await page.locator('#ss-summary .ss-metric-battle-link[data-ss-source-metric="credits_income_received"][data-ss-extreme="min"]').click();
      const commands=await page.evaluate(()=>__grzCommands.filter(command=>command.action==='battle_select')),
        command=commands[commands.length-1];
      check('The existing financial Min source still navigates its exact battle while Avg is displayed at '+scale+'x: '+JSON.stringify(command),
        commands.length===before+1&&command.id==='summary-summary-mode:narrow-credits_income_received-min'&&command.scope==='timeline'&&command.period_id==='summary-mode:narrow'&&command.account_key===account);
      await choose('sum');const restored=await inspect('pl','sum',{narrow:true,factor:2});
      check('All restores current-range signed totals and removes per-statistic figure focus/help at '+scale+'x: '+JSON.stringify(restored),valid(restored,'pl','sum',{narrow:true,factor:2}));
    }finally{await page.close();}
  }
};
