/* Sorting warnings describe missing fields within the selected received history. */
const assert=require('assert'),fs=require('fs'),path=require('path'),{spawnSync}=require('child_process');
const frames=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
module.exports=async({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const metrics=['xp_base','xp_received','credits_income_base','credits_income_received','credits_net_base','credits_net_received','credits_costs','battle_wn8'];
  const page=await nativeHost(browser,{initialViewport:{width:1800,height:1300},viewport:{width:1800,height:1300,scale:1}});
  let serial=0;
  await page.evaluate(()=>{window.__warningFixture=JSON.parse(model.payload);});
  async function publish(options={}){
    await page.evaluate(({options,serial,metrics,languages})=>{
      const payload=JSON.parse(JSON.stringify(__warningFixture)),scope=payload.scopes.launch;
      delete payload.appearance;payload.account_key='DEMO:field-completeness';payload.window_size=[1200,1050];
      payload.generated_at+=serial;payload.loading=!!options.globalLoading;payload.load_error=options.globalError?'Synthetic global read error':'';
      payload.localization={language:options.language||'en',messages:languages[options.language||'en']};
      scope.loading=!!options.loading;scope.load_error=options.error?'Synthetic range read error':'';
      const received=options.received===undefined?4:options.received,observed=options.observed===undefined?6:options.observed;
      scope.summary.battles=received;scope.summary.observed_battles=observed;
      for(const metric of metrics)scope.summary[metric]={count:received,min:0,avg:0,max:0,sum:0};
      const metric=options.metric||'xp_base',count=options.count===undefined?received:options.count;
      if(metrics.includes(metric))scope.summary[metric].count=count;
      if(options.missing)delete scope.summary[metric];
      if(options.legacy){delete scope.summary[metric];scope.summary[options.legacy]={count,min:0,avg:0,max:0,sum:0};}
      const item=scope.maps[0];scope.maps=[item];
      item.stats.battles=item.stats.observed_battles=1;
      for(const metric of metrics)item.stats[metric]={count:options.pageMissing?0:1,min:0,avg:0,max:0,sum:0};
      scope.ordering.maps={metric,statistic:options.statistic||'avg',direction:'desc',chronology:'newest'};
      scope.pagination.maps={page:options.page||0,pages:3,total:85,page_size:40};scope.data_revision='warning-'+serial;
      if(options.empty){scope.maps=[];scope.pagination.maps={page:0,pages:1,total:0,page_size:40};}
      if(options.timeline){
        const timeline=payload.scopes.timeline=JSON.parse(JSON.stringify(scope));
        timeline.from_point=options.from||'';timeline.to_point='';timeline.time_points=[['recent',1794000000],['older',1793000000]];
      }else delete payload.scopes.timeline;
      if(options.appearance)payload.appearance=options.appearance;
      model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
    },{options,serial:++serial,metrics,languages});
    await page.locator(options.timeline?'#ss-scope-manual':'#ss-scope-launch').click();
    await page.locator('#ss-group-maps').click();await frames(page);
  }
  async function warning(){return page.locator('#ss-sort-data-warning').evaluate(node=>({
    visible:getComputedStyle(node).display!=='none',text:node.textContent,title:node.getAttribute('title'),
    hidden:node.getAttribute('aria-hidden'),color:getComputedStyle(node).color,
    role:node.getAttribute('role'),live:node.getAttribute('aria-live')}));}
  try{
    for(const metric of metrics){
      await publish({metric,count:4});let result=await warning();
      check('Complete zero-valued '+metric+' does not confuse pending reports with missing fields',
        !result.visible&&result.text===''&&result.title===null&&result.hidden==='true');
      for(const count of [3,0]){
        await publish({metric,count});result=await warning();
        check('Incomplete '+metric+' warns for '+count+' available fields in four received results',
          result.visible&&result.hidden==='false'&&result.text===languages.en['sort.incomplete']&&
          result.title.includes(languages.en['sort.field_coverage'].replace('{0}',count).replace('{1}',4)));
      }
    }
    for(const metric of ['off','battles','win_rate']){
      await publish({metric,count:0});
      check('An inapplicable field warning stays hidden for '+metric,!(await warning()).visible);
    }
    await publish({metric:'xp_base',count:3});
    const structural=await page.locator('#ss-sort-data-warning').evaluate(node=>{
      const bar=document.getElementById('ss-list-controls'),filter=document.getElementById('ss-filter-panel'),
        box=node.getBoundingClientRect(),controls=bar.getBoundingClientRect(),parent=filter.getBoundingClientRect();
      return node.parentNode===filter&&!bar.contains(node)&&box.top>=controls.bottom-1&&
        box.left>=parent.left-1&&box.right<=parent.right+1&&box.bottom<=parent.bottom+1;
    });
    const active=await warning();
    check('The warning is a readable orange-red live status below the unchanged controls row',
      structural&&active.color==='rgb(230, 115, 69)'&&active.role==='status'&&active.live==='polite');
    const controls=()=>page.locator('#ss-list-controls').evaluate(node=>{const r=node.getBoundingClientRect();return [r.left,r.top,r.width,r.height];});
    const before=await controls();await publish({metric:'xp_base',count:4});const after=await controls();
    check('Showing a field warning does not resize or reposition the sorting controls',before.every((v,i)=>Math.abs(v-after[i])<=0.5));
    for(const options of [{loading:true},{error:true},{globalLoading:true},{globalError:true}]){
      await publish({metric:'xp_base',count:3,...options});const result=await warning();
      check('Unavailable projection clears warning text, title and live visibility '+JSON.stringify(options),
        !result.visible&&result.text===''&&result.title===null&&result.hidden==='true');
    }
    await publish({metric:'xp_base',count:0,received:0,observed:3,empty:true});
    check('An empty received history with three pending reports does not invent incomplete fields',!(await warning()).visible);
    await publish({metric:'xp_base',missing:true});
    check('An absent selected field within received results is reported as unavailable',
      (await warning()).title.includes(languages.en['sort.field_coverage'].replace('{0}',0).replace('{1}',4)));
    await publish({metric:'credits_income_received',legacy:'credits_gross',count:4});
    check('Complete historical received-income aliases do not produce a false warning',!(await warning()).visible);
    await publish({metric:'credits_net_received',legacy:'credits_net',count:3});
    check('Partial historical received-net aliases retain the field warning',(await warning()).visible);
    await publish({metric:'xp_base',count:3,page:1});
    check('The whole selected range warns even when every displayed card has complete values',(await warning()).visible);
    await publish({metric:'xp_base',count:4,page:1,pageMissing:true});
    check('A partial visible card cannot override complete selected-range coverage',!(await warning()).visible);
    await publish({metric:'xp_base',count:3,timeline:true});
    check('Beginning-to-Now timeline coverage uses received results across the entire range',(await warning()).visible);
    await publish({metric:'xp_base',count:2,received:2,observed:5,timeline:true,from:'recent'});
    check('Selecting a complete recent range clears the previous incomplete-history warning',!(await warning()).visible);
    await publish({metric:'xp_base',count:3,timeline:true,from:'older'});
    check('Selecting an older incomplete range restores its own warning',(await warning()).visible);
    for(const [language,messages]of Object.entries(languages)){
      await publish({metric:'xp_base',count:3,language});const result=await warning();
      check('Warning and field coverage follow the selected '+language+' interface language',
        result.text===messages['sort.incomplete']&&result.title.includes(messages['sort.field_coverage'].replace('{0}',3).replace('{1}',4)));
    }
    const python=spawnSync(process.env.GRZ_PYTHON3||'python3',['-c',
      "import json;from grz_session_stats.appearance import default_config,build_presentation;c=default_config();c['colors']['sort_warning_text']='#df602e';c['window'].update(restored_width=1200,restored_height=1050);print(json.dumps(build_presentation(c)))"],
      {encoding:'utf8',env:{...process.env,PYTHONPATH:path.join(__dirname,'../src')}});
    assert.strictEqual(python.status,0,python.stderr);
    await publish({metric:'xp_base',count:3,appearance:JSON.parse(python.stdout)});
    check('The documented sort_warning_text appearance color controls the warning',(await warning()).color==='rgb(223, 96, 46)');
  }finally{await page.close();}
};
