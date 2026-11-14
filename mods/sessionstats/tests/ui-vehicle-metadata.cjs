/* Native role identity/artwork keeps tooltips in the selected mod language. */
const fs=require('fs'),path=require('path');
module.exports=async({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const page=await nativeHost(browser,{initialViewport:{width:3840,height:2560},viewport:{width:3840,height:2560,scale:1}});
  const frames=()=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  try{
    for(const scale of [1,2])for(const [language,messages] of Object.entries(languages)){
      await page.evaluate(({scale,language,messages})=>{
        const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
        payload.account_key='synthetic-class-role-'+language+'-'+scale;
        payload.window_size=[1200,1100];payload.viewport={width:3840,height:2560,scale};payload.localization={language,messages};
        const metadata={class:'AT_SPG',tier:10,elite:true,
          class_icon:{kind:'vehicle_class',src:'img://gui/maps/icons/vehicleTypes/24x24_metal/AT-SPG_elite.png'},
          role:{key:'role_ATSPG_sniper',name:'Rola klienta',group_name:'Rola klienta',
            description:'Oryginalny opis klienta.\nDrugi akapit.',
            icon:{kind:'vehicle_role',src:'img://gui/maps/icons/roleExp/roles/24x24/role_ATSPG_sniper.png'}}};
        scope.vehicles=[{...scope.vehicles[0],id:'257',name:'Synthetic TD',type:null,tier:null,vehicle_meta:metadata}];
        scope.battles=[{...scope.battles[0],id:'synthetic-metadata-battle',name:'Synthetic TD',vehicle_meta:metadata}];
        delete scope.pagination;model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      },{scale,language,messages});
      await page.locator('#ss-scope-launch').click();await page.locator('#ss-group-vehicles').click();await frames();
      for(const grouping of ['vehicles','battles']){
        await page.locator('#ss-group-'+grouping).click();await frames();
        const card=page.locator('.ss-group').first(),caption=grouping+' '+language+' at'+scale;
        check('Original class/role artwork is present and keyboard accessible in '+caption,
          await card.locator('.ss-vehicle-icon').evaluateAll(nodes=>nodes.length===2&&nodes.every(node=>
            node.getAttribute('role')==='img'&&node.tabIndex===0&&node.classList.contains('ss-hover-help')&&
            getComputedStyle(node).backgroundImage.startsWith('url("img://gui/maps/icons/'))));
        check('Class and role definitions follow the selected mod language despite Polish native metadata in '+caption,
          await card.locator('.ss-vehicle-class-icon').getAttribute('aria-label')===messages['vehicle.AT_SPG']&&
          await card.locator('.ss-vehicle-role-icon').getAttribute('data-ss-help')===
            messages['vehicle.role.role_ATSPG_sniper.name']+'\n'+messages['vehicle.role.role_ATSPG_sniper.description']&&
          await card.locator('.ss-vehicle-role-icon').getAttribute('data-vehicle-role')==='role_ATSPG_sniper');
        check('Native class artwork keeps its full 24px canvas while role artwork retains its size in '+caption,
          await card.locator('.ss-vehicle-meta').evaluate((row,{scale,grouping})=>{
            const outer=row.closest('.ss-group-name').getBoundingClientRect();
            const card=row.closest('.ss-group'),header=card.querySelector('.ss-group-header').getBoundingClientRect(),
              details=card.querySelector('.ss-details').getBoundingClientRect();
            return header.height<=(grouping==='vehicles'?66:64)*scale&&outer.bottom<=details.top+1&&
              row.textContent===(grouping==='vehicles'?'X':'')&&[...row.querySelectorAll('.ss-vehicle-icon')].every(node=>{
              const size=node.classList.contains('ss-vehicle-class-icon')?24:16;
              const r=node.getBoundingClientRect();return Math.abs(r.width-size*scale)<0.1&&Math.abs(r.height-size*scale)<0.1&&
                r.left>=outer.left-1&&r.right<=outer.right+1&&r.bottom<=header.bottom+1;
            });
          },{scale,grouping}));
      }
    }
    await page.locator('#ss-group-vehicles').click();
    for(const [elite,filename,present] of [[false,'AT-SPG.png',true],[true,'AT-SPG_elite.dds',true],
      [false,'AT-SPG_elite.png',false],['true','AT-SPG_elite.png',false],[true,'mediumTank_elite.png',false],
      [false,'../24x24_metal/AT-SPG.png',false],[false,'AT-SPG.png?remote=true',false]]){
      await page.evaluate(({elite,filename})=>{
        const payload=JSON.parse(model.payload),meta=payload.scopes.launch.vehicles[0].vehicle_meta;
        meta.elite=elite;meta.class_icon.src='img://gui/maps/icons/vehicleTypes/24x24_metal/'+filename;
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      },{elite,filename});await frames();
      check('Class variant must match the verified class and actual boolean elite state: '+elite+' '+filename,
        await page.locator('.ss-vehicle-class-icon').count()===(present?1:0));
    }
    await page.evaluate(()=>{
      const payload=JSON.parse(model.payload),meta=payload.scopes.launch.vehicles[0].vehicle_meta;
      meta.class_icon.src='https://example.invalid/AT-SPG.png';
      meta.role.icon.src='img://gui/maps/icons/roleExp/roles/24x24/../role_ATSPG_sniper.png';
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
    });await frames();
    check('Unverified artwork cannot become a class or role icon',await page.locator('.ss-group .ss-vehicle-icon').count()===0);
    check('Missing artwork retains the selected-language class and role definition on the tier tooltip',
      (await page.locator('.ss-vehicle-tier').getAttribute('data-ss-help')).includes(languages.uk['vehicle.role.role_ATSPG_sniper.description']));
    await page.evaluate(()=>{
      const payload=JSON.parse(model.payload),item=payload.scopes.launch.vehicles[0];
      item.type='constructor';item.tier=10;delete item.vehicle_meta;
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
    });await frames();
    check('Unknown classes do not invent icons or visible labels',await page.locator('.ss-vehicle-icon').count()===0&&
      await page.locator('.ss-vehicle-meta').textContent()==='X'&&await page.locator('.ss-vehicle-tier').getAttribute('data-ss-help')===null);
    await page.evaluate(()=>{
      const payload=JSON.parse(model.payload),item=payload.scopes.launch.vehicles[0];
      item.tier=9;item.vehicle_meta={class:'AT_SPG',tier:10,role:{key:'constructor',name:'Invented role',description:'Invented description'}};
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
    });await frames();
    check('Presentation metadata does not replace a recorded tier',await page.locator('.ss-vehicle-tier').textContent()==='IX');
    check('Invalid role keys do not become an official-role tooltip',
      !(await page.locator('.ss-vehicle-tier').getAttribute('data-ss-help')).includes('Invented'));
    const roles=['role_HT_assault','role_HT_break','role_HT_universal','role_HT_support',
      'role_MT_assault','role_MT_universal','role_MT_sniper','role_MT_support',
      'role_ATSPG_assault','role_ATSPG_universal','role_ATSPG_sniper','role_ATSPG_support',
      'role_LT_universal','role_LT_scout','role_LT_support','role_SPG'];
    for(const [language,messages]of Object.entries(languages))for(const key of roles){
      await page.evaluate(({language,messages,key})=>{
        const payload=JSON.parse(model.payload),item=payload.scopes.launch.vehicles[0];
        payload.localization={language,messages};
        const kind=key==='role_SPG'?'SPG':{HT:'heavyTank',MT:'mediumTank',ATSPG:'AT_SPG',LT:'lightTank'}[key.split('_')[1]];
        item.type=kind;item.vehicle_meta={class:kind,tier:10,elite:false,
          class_icon:{kind:'vehicle_class',src:'img://gui/maps/icons/vehicleTypes/24x24_metal/'+(kind==='AT_SPG'?'AT-SPG':kind)+'.png'},
          role:{key,name:'Niepoprawny język klienta',group_name:'Polska grupa klienta',description:'Polski opis z pamięci klienta.',
            icon:key==='role_SPG'?{}:{kind:'vehicle_role',src:'img://gui/maps/icons/roleExp/roles/24x24/'+key+'.png'}}};
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      },{language,messages,key});await frames();
      const expected=messages['vehicle.role.'+key+'.name']+'\n'+messages['vehicle.role.'+key+'.description'];
      const target=page.locator(key==='role_SPG'?'.ss-group .ss-vehicle-class-icon':'.ss-group .ss-vehicle-role-icon');
      check('Verified role '+key+' uses its '+language+' catalog tooltip and ignores cached native paragraphs',
        typeof messages['vehicle.role.'+key+'.name']==='string'&&typeof messages['vehicle.role.'+key+'.description']==='string'&&
        await target.getAttribute('data-ss-help').then(text=>text.endsWith(expected)&&!text.includes('klienta'))&&
        await target.getAttribute('title').then(text=>text.endsWith(expected)));
      if(key==='role_SPG')check('SPG role text does not invent a role icon in '+language,await page.locator('.ss-group .ss-vehicle-role-icon').count()===0);
    }
    for(const language of ['pl','en','de','en']){
      await page.evaluate(({language,messages})=>{
        const payload=JSON.parse(model.payload),meta=payload.scopes.launch.vehicles[0].vehicle_meta;
        payload.localization={language,messages};meta.class='AT_SPG';payload.scopes.launch.vehicles[0].type='AT_SPG';
        meta.class_icon.src='img://gui/maps/icons/vehicleTypes/24x24_metal/AT-SPG.png';meta.role.key='role_ATSPG_sniper';
        meta.role.icon={kind:'vehicle_role',src:'img://gui/maps/icons/roleExp/roles/24x24/role_ATSPG_sniper.png'};
        model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
      },{language,messages:languages[language]});await frames();
      check('A live language change re-translates the same cached native role metadata to '+language,
        await page.locator('.ss-group .ss-vehicle-role-icon').getAttribute('data-ss-help')===
          languages[language]['vehicle.role.role_ATSPG_sniper.name']+'\n'+languages[language]['vehicle.role.role_ATSPG_sniper.description']);
    }
    await page.evaluate(()=>{
      const payload=JSON.parse(model.payload);payload.localization={language:'fr',messages:{title:'Partial catalog'}};
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
    });await frames();
    check('An incomplete role catalog falls back to English instead of cached Polish client text',
      await page.locator('.ss-group .ss-vehicle-role-icon').getAttribute('data-ss-help')===
        languages.en['vehicle.role.role_ATSPG_sniper.name']+'\n'+languages.en['vehicle.role.role_ATSPG_sniper.description']);
    await page.evaluate(()=>{
      const payload=JSON.parse(model.payload),role=payload.scopes.launch.vehicles[0].vehicle_meta.role;
      role.key='role_ATSPG_future';role.icon.src='img://gui/maps/icons/roleExp/roles/24x24/role_ATSPG_future.png';
      model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
    });await frames();
    check('An unknown future role keeps its verified artwork without inventing or importing a wrong-language definition',
      await page.locator('.ss-group .ss-vehicle-role-icon').getAttribute('data-ss-help')===languages.en['vehicle.AT_SPG']);
  }finally{await page.close();}
};
