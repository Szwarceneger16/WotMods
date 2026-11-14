/* A full pager/sort row centers as one strip within its reserved activity area. */
const fs=require('fs'),path=require('path');
async function settledWide(page,width,scale){
  // Promotion owns an eight-frame/120ms debounce after resize measurement.
  // Await its published mode and width, plus the native size acknowledgement;
  // a fixed number of earlier frames does not establish that it completed.
  await page.waitForFunction(({width,scale})=>{
    const bar=document.getElementById('ss-list-controls');
    return bar.getAttribute('data-filter-layout')==='wide'&&Number(bar.getAttribute('data-filter-width'))===width-38&&
      window.__nativeSize&&__nativeSize[0]===Math.ceil(width*scale);
  },{width,scale});
  await page.evaluate(({width})=>new Promise((resolve,reject)=>{let left=6;
    function next(){
      const bar=document.getElementById('ss-list-controls');
      if(bar.getAttribute('data-filter-layout')!=='wide'||Number(bar.getAttribute('data-filter-width'))!==width-38||
          !bar.classList.contains('ss-filters-wide')||bar.classList.contains('ss-filters-wrapped')){
        reject(Error('An acknowledged full-row layout changed at the same width'));return;
      }
      if(--left)requestAnimationFrame(next);else resolve();
    }requestAnimationFrame(next);
  }),{width});
}
module.exports=async({browser,nativeHost,check})=>{
  const catalogs=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:3840,height:2400},viewport:{width:3840,height:2400,scale}});
    try{
      for(const [language,messages]of Object.entries(catalogs))for(const width of [1200,1489,1800])for(const group of ['vehicles','battles']){
        await page.evaluate(({language,messages,width,group})=>{
          const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
          payload.account_key='synthetic-wide-filter-'+language;payload.localization={language,messages};payload.window_size=[width,850];
          payload.appearance={window_settings:{background_transparency:0,maximized:false,restored_width:width,restored_height:850}};
          scope.ordering[group]={metric:'xp_base',statistic:'avg',direction:'desc',chronology:'newest'};
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();document.getElementById('ss-group-'+group).onclick();
        },{language,messages,width,group});await settledWide(page,width,scale);
        const geometry=await page.evaluate(()=>{
          const bar=document.getElementById('ss-list-controls'),box=bar.getBoundingClientRect(),style=getComputedStyle(bar);
          const rows=[...bar.children].filter(node=>node.id!=='ss-filter-loading').map(node=>node.getBoundingClientRect()).filter(box=>box.width>0&&box.height>0);
          const left=Math.min(...rows.map(box=>box.left)),right=Math.max(...rows.map(box=>box.right));
          return {mode:bar.getAttribute('data-filter-layout'),left,right,
            center:box.left+parseFloat(style.paddingLeft)+(box.width-parseFloat(style.paddingLeft)-parseFloat(style.paddingRight))/2,
            bottoms:rows.map(box=>box.bottom),toggle:getComputedStyle(document.getElementById('ss-sort-off')).display};
        });
        check('The full filter row centers without wrapping in '+language+' '+group+' at '+width+'px/'+scale+'x: '+JSON.stringify(geometry),
          geometry.mode==='wide'&&geometry.toggle!=='none'&&Math.abs((geometry.left+geometry.right)/2-geometry.center)<=scale&&
          Math.max(...geometry.bottoms)-Math.min(...geometry.bottoms)<=scale);
      }
    }finally{await page.close();}
  }
};
