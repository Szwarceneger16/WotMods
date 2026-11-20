/* The footer identifies the running backend version, including custom builds. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
module.exports=async({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const page=await nativeHost(browser,{initialViewport:{width:1800,height:1400},viewport:{width:1800,height:1400,scale:1}});
  try {
    for(const scale of [1,2])for(const [language,messages]of Object.entries(languages)){
      await page.evaluate(({scale,language,messages})=>{const data=JSON.parse(model.payload);
        data.viewport={width:1800,height:1400,scale};data.window_size=[720,600];
        data.version='7.8.9';data.localization={language,messages};
        model.payload=JSON.stringify(data);__grzEvents['viewEnv.onDataChanged']();
      },{scale,language,messages});await frames(page);
      const label=language+' at'+(scale*100)+'%';
      check('The bottom-left version follows the running snapshot in '+label,
        await page.locator('#ss-version').textContent()==='v7.8.9' && await page.locator('#ss-version').getAttribute('title')==='Session Stats 7.8.9');
      const geometry=await page.evaluate(()=>{const version=document.getElementById('ss-version').getBoundingClientRect(),
        status=document.getElementById('ss-status').getBoundingClientRect(),footer=document.querySelector('.ss-footer').getBoundingClientRect();
        return {inside:version.left>=footer.left && version.bottom<=footer.bottom && version.right<=status.left+1,width:version.width};});
      check('Version remains separate from the status text inside the left footer in '+label,geometry.inside && geometry.width>0);
    }
    await page.evaluate(()=>{const data=JSON.parse(model.payload);data.version='7.8.10';model.payload=JSON.stringify(data);__grzEvents['viewEnv.onDataChanged']();});
    check('A later backend version replaces the displayed value',await page.locator('#ss-version').textContent()==='v7.8.10');
    await page.evaluate(()=>{const data=JSON.parse(model.payload);delete data.version;model.payload=JSON.stringify(data);__grzEvents['viewEnv.onDataChanged']();});
    check('An older snapshot without version never invents a version string',await page.locator('#ss-version').isHidden() && await page.locator('#ss-version').textContent()==='');
  }finally{await page.close();}
};
