/* Native descriptor metadata provides class/role artwork, with client-localized definitions. */
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
        check('Class labels use the selected UI language while the official definition remains client-localized in '+caption,
          await card.locator('.ss-vehicle-class-icon').getAttribute('aria-label')===messages['vehicle.AT_SPG']&&
          await card.locator('.ss-vehicle-role-icon').getAttribute('data-ss-help')==='Rola klienta\nOryginalny opis klienta.\nDrugi akapit.'&&
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
    check('Missing artwork retains the known class and native definition on the tier tooltip',
      (await page.locator('.ss-vehicle-tier').getAttribute('data-ss-help')).includes('Oryginalny opis klienta.'));
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
  }finally{await page.close();}
};
