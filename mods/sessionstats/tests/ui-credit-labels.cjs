/* Income/cost captions fit fixed slots; full names remain in titles and ARIA. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
module.exports=async({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const labels={credits_net:['sort.credits.caption','sort.credits'],credits_gross:['sort.credits_gross.caption','sort.credits_gross'],credits_costs:['sort.credits_costs','sort.credits_costs']};
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:3840,height:2400},viewport:{width:3840,height:2400,scale}});
    try{
      for(const width of [300,550,1200]){
        await page.setViewportSize({width:width===300?320*scale:3840,height:2400});
        for(const [language,messages]of Object.entries(languages)){
        let baseline;
        for(const [metric,[key,description]]of Object.entries(labels)){
          await page.evaluate(({width,scale,language,messages,metric})=>{
            const payload=JSON.parse(model.payload);payload.window_size=[width,950];
            payload.viewport={width:width===300?320*scale:3840,height:2400,scale};payload.localization={language,messages};
            payload.scopes.launch.ordering.maps={metric,statistic:'sum',direction:'desc',chronology:'newest'};
            model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();document.querySelector('#ss-group-maps').onclick();
          },{width,scale,language,messages,metric});await frames(page);
          const audit=await page.locator('#ss-sort-metric .ss-select-trigger').evaluate((trigger,metric)=>{
            const label=trigger.querySelector('.ss-control-label'),box=label.getBoundingClientRect(),r=trigger.getBoundingClientRect(),range=document.createRange();
            range.selectNodeContents(label);const ink=[...range.getClientRects()].filter(rect=>rect.width>0&&rect.height>0);
            const option=document.querySelector('#ss-sort-metric [data-value="'+metric+'"]');
            return {text:label.textContent,title:trigger.title,option:option.getAttribute('aria-label'),
              labelBox:box.toJSON(),ink:ink.map(rect=>rect.toJSON()),line:getComputedStyle(label).lineHeight,bounds:[r.left,r.top,r.width,r.height],font:parseFloat(getComputedStyle(label).fontSize),
              fits:ink.length>0&&box.height<=26*parseFloat(getComputedStyle(document.documentElement).fontSize)+0.1&&ink.every(rect=>rect.left>=box.left-0.5&&rect.right<=box.right+0.5&&rect.top>=box.top-0.5&&rect.bottom<=box.bottom+0.5&&rect.top>=r.top&&rect.bottom<=r.bottom)};
          },metric);
          if(!baseline)baseline=audit.bounds;
          const fits=audit.text===messages[key]&&audit.title.includes(messages[description])&&audit.option===messages[description]&&
            audit.fits&&audit.font>=11*scale&&audit.bounds.every((part,index)=>Math.abs(part-baseline[index])<=0.1*scale);
          check('Credit metric captions and full descriptions fit unchanged slots '+language+'/'+scale+'x/'+width+'/'+metric+(fits?'':': '+JSON.stringify(audit)),fits);
        }
      }}
    }finally{await page.close();}
  }
};
