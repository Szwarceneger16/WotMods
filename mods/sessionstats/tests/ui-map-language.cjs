/* Actual Python localization feeds native-model language switches and previews. */
const fs=require('fs'),path=require('path'),{spawnSync}=require('child_process');
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let n=6;function next(){if(--n)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);}));
module.exports=async({browser,nativeHost,check})=>{
  const root=path.resolve(__dirname,'..'),fixture=JSON.parse(fs.readFileSync(path.join(root,'preview/demo_snapshot.json'),'utf8')).normal;
  const seed=JSON.parse(JSON.stringify(fixture)),scope=seed.scopes.launch;
  seed.account_key='synthetic-map-language';seed.window_size=[1200,1100];
  scope.period_id='synthetic-map-language-period';scope.data_revision='unchanged-map-language-revision';
  const id='59_asia_great_wall',saved='Granica imperium',src='img://gui/maps/icons/map/small/'+id+'.png',
    visual={kind:'map',src,preview_src:'img://gui/maps/icons/map/screen/'+id+'.dds',preview_mode:'image',alt:saved};
  const history={page:0,pages:1,total:1,page_size:10,chronology:'newest',items:[{id:'synthetic-battle',name:'Synthetic tank',map_id:id,map:saved,started_at:1791026100,outcome:'win',wn8:1000}]};
  scope.maps=[{...scope.maps[0],id,name:saved,visual,battle_list:history}];
  scope.vehicles=[{...scope.vehicles[0],id:'synthetic-vehicle',battle_list:history}];
  scope.battles=[{...scope.battles[0],id:'synthetic-battle',map_id:id,map:saved,map_visual:visual}];
  for(const group of ['maps','vehicles','battles'])scope.pagination[group]={page:0,pages:1,total:1,page_size:40};
  seed.scopes.timeline=JSON.parse(JSON.stringify(scope));Object.assign(seed.scopes.timeline,{time_points:[],time_point_names:{},from_point:'__custom__',from_date:Date.UTC(2024,9,15,17,45)/1000,to_point:'',to_date:null});
  const python=spawnSync(process.env.GRZ_PYTHON3||'python3',['-c',
    'import copy,json,sys;sys.path.insert(0,sys.argv[1]);from grz_session_stats.localization import Localizer;seed=json.load(sys.stdin);print(json.dumps({language:Localizer(language,client_language="pl",date_settings={"order":"MDY","separator":"/","hour12":False,"first_weekday":0,"months":["Polish native month"]*12,"weekdays":["Polish native day"]*7}).snapshot(copy.deepcopy(seed)) for language in ("pl","en","ru","fr","de","es","uk")}))',
    path.join(root,'src')],{input:JSON.stringify(seed),encoding:'utf8',maxBuffer:8*1024*1024});
  if(python.error||python.status!==0)throw Error(python.error||python.stderr);const payloads=JSON.parse(python.stdout),page=await nativeHost(browser,{initialViewport:{width:1800,height:1400},viewport:{width:1800,height:1400,scale:1}});
  try{
    for(const language of ['pl','en','ru','fr','de','es','uk','en']){
      const payload=payloads[language],messages=payload.localization.messages,expected=payload.scopes.launch.maps[0].name;
      await page.evaluate(payload=>{model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},payload);await frames(page);
      await page.locator('#ss-scope-launch').click();await page.locator('#ss-group-maps').click();await frames(page);
      check('Stable map IDs refresh card names after a same-account language switch to '+language,
        await page.locator('#ss-groups .ss-group-title').first().textContent()===expected);
      const thumb=page.locator('#ss-groups .ss-group-thumb').first();await thumb.hover();
      check('Map thumbnail and hover labels use the selected map language '+language,
        await thumb.getAttribute('aria-label')===expected&&await page.locator('#ss-map-preview').getAttribute('aria-label')===messages['maps.preview'].replace('{0}',expected));
      await page.mouse.move(0,0);await page.locator('#ss-group-battles').click();await frames(page);
      check('Battle map captions and visual labels refresh to '+language,
        await page.locator('.ss-battle-map-label').textContent()===expected&&await page.locator('.ss-battle-map-thumb').getAttribute('aria-label')===expected);
      await page.locator('#ss-group-vehicles').click();await frames(page);const more=page.locator('.ss-vehicle-more-button').first();
      if(await more.getAttribute('aria-expanded')!=='true')await more.click();
      check('An already loaded vehicle history refreshes its map caption to '+language,
        await page.locator('.ss-map-battle-name').first().textContent()===expected);
      await page.locator('#ss-scope-manual').click();await frames(page);
      const input=page.locator('#ss-custom-date-from');
      const entered=await input.inputValue();
      const expectedDate=await page.evaluate(epoch=>{const date=new Date(epoch*1000);return '10/15/2024 '+String(date.getHours()).padStart(2,'0')+':45';},seed.scopes.timeline.from_date);
      check('Selected UI language preserves client numeric date order and 24h clock '+language+': '+entered,
        entered===expectedDate&&await input.getAttribute('placeholder')==='mm/dd/yyyy HH:mm');
      await page.locator('#ss-custom-date-calendar-from').click();const picker=page.locator('#ss-date-picker-from');
      check('Calendar words follow '+language+' while native Sunday-first preference stays active',
        await picker.locator('[data-date-part="month"]').textContent()===messages['timeline.calendar_months'].split('|')[9]&&
        await picker.locator('.ss-date-weekday').first().textContent()===messages['timeline.calendar_weekdays'].split('|')[6]);
      await picker.locator('[aria-selected="true"]').press('Escape');
    }
  }finally{await page.close();}
  const preview=await browser.newPage();try{
    await preview.goto('file://'+path.join(root,'preview/PODGLAD.html'));await preview.locator('#ss-group-maps').click();
    for(const language of ['pl','en']){
      await preview.locator('#ss-language .ss-select-trigger').click();await preview.locator('#ss-language [data-value="'+language+'"]').click();await frames(preview);
      const expected=await preview.evaluate(language=>GRZ_DEMO_LOCALIZED[language].normal.scopes.launch.maps.map(row=>row.name).sort(),language),
        actual=(await preview.locator('#ss-groups .ss-group-title').allTextContents()).sort();
      check('The standalone preview uses the same offline localized map snapshots in '+language,JSON.stringify(actual)===JSON.stringify(expected));
    }
  }finally{await preview.close();}
  const legacy=await browser.newPage(),legacyErrors=[];legacy.on('pageerror',error=>legacyErrors.push(String(error)));
  try{
    await legacy.route('http://grz-language-legacy.test/**',async route=>{
      const name=new URL(route.request().url()).pathname.slice(1);
      if(!['SessionStats.html','session_stats.js','session_stats.css','session_stats_camo.png'].includes(name)){await route.abort();return;}
      await route.fulfill({contentType:name.endsWith('.js')?'text/javascript':name.endsWith('.css')?'text/css':name.endsWith('.png')?'image/png':'text/html',body:fs.readFileSync(path.join(root,'ui',name))});
    });
    await legacy.goto('http://grz-language-legacy.test/SessionStats.html');
    await legacy.waitForFunction(()=>window.GRZSessionStats);
    await legacy.evaluate(fixture=>{
      window.GRZ_DEMO_FIXTURES={normal:fixture,reset:fixture};
      const toolbar=document.createElement('div');toolbar.innerHTML='<button id="demo-reopen">Open</button><button id="demo-restart">Restart</button>';document.body.appendChild(toolbar);
    },fixture);
    await legacy.addScriptTag({path:path.join(root,'preview/controller.js')});
    await legacy.locator('#ss-groups .ss-group').first().waitFor();
    check('Canonical standalone fixtures render without optional localization metadata or variant globals',
      await legacy.locator('#ss-groups .ss-group').count()>0&&legacyErrors.length===0);
    await legacy.locator('#demo-restart').click();await frames(legacy);
    check('The standalone restart fallback retains canonical fixture support',
      await legacy.locator('#ss-groups .ss-group').count()>0&&legacyErrors.length===0);
  }finally{await legacy.close();}
};
