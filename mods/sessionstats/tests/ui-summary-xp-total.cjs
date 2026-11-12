/* Summary XP totals use the selected series sum without changing WN8 columns. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
module.exports=async({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:3840,height:2400},viewport:{width:3840,height:2400,scale}});
    try{
      for(const [language,messages] of Object.entries(languages))for(const width of [550,1200]){
        await page.evaluate(({language,messages,width,scale})=>{
          const payload=JSON.parse(model.payload);
          payload.account_key='synthetic-xp-total-'+language+'-'+width+'-'+scale;
          payload.window_size=[width,1000];payload.localization={language,messages};
          payload.viewport={width:3840,height:2400,scale};
          payload.appearance=payload.appearance||{};
          payload.appearance.window_settings={background_transparency:0,maximized:false,restored_width:width,restored_height:1000};
          const stats=payload.scopes.launch.summary;
          stats.battles=3;stats.observed_battles=4;
          stats.xp_base={count:3,min:100,avg:200,max:300,sum:600};
          stats.xp_received={count:2,min:18,avg:6172839,max:12345660,sum:12345678};
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
        },{language,messages,width,scale});
        await page.locator('#ss-scope-launch').click();await frames(page);
        const heights=[];
        for(const type of ['base','received']){
          await page.locator('#ss-xp-'+type).click();await frames(page);
          const audit=await page.locator('#ss-summary').evaluate((summary,scale)=>{
            const total=summary.querySelector('.ss-summary-xp-total'),value=total.querySelector('.ss-xp-total-value');
            const box=total.getBoundingClientRect(),root=summary.getBoundingClientRect(),range=document.createRange();
            range.selectNodeContents(value);const ink=range.getBoundingClientRect();
            const labels=[...total.querySelectorAll('.ss-xp-total-label,.ss-count-coverage')];
            return {metric:total.getAttribute('data-xp-metric'),label:total.querySelector('.ss-xp-total-label').textContent,
              value:value.textContent.replace(/\s/g,''),coverage:total.querySelector('.ss-count-coverage')?.textContent.replace(/\s/g,''),
              height:box.height/scale,fits:box.left>=root.left-1&&box.right<=root.right+1&&ink.left>=box.left-1&&ink.right<=box.right+1&&
                labels.every(node=>{const text=document.createRange();text.selectNodeContents(node);return [...text.getClientRects()].every(r=>r.left>=box.left-1&&r.right<=box.right+1);}),
              columns:summary.querySelectorAll('.ss-performance .ss-metric-head .ss-metric-number').length,
              rows:summary.querySelectorAll('.ss-performance .ss-metric-row').length};
          },scale);
          heights.push(audit.height);
          const caption=language+' '+width+'rem '+scale+'x '+type;
          check('Summary total selects the exact '+type+' XP sum and its own coverage: '+caption+': '+JSON.stringify(audit),
            audit.metric==='xp_'+type&&audit.label===messages['xp.'+type+'_total']&&
            audit.value===(type==='base'?'600':'12345678')&&audit.coverage===(type==='base'?'(3/4)':'(2/4)'));
          check('Full XP total fits without adding a meaningless WN8 sum column: '+caption,
            audit.fits&&audit.columns===3&&audit.rows===2&&audit.height<=35);
        }
        check('Switching XP keeps the total row height stable in '+language+' at '+width+'rem/'+scale+'x',Math.abs(heights[0]-heights[1])<=1);
      }
      for(const [count,sum,expected] of [[2,0,'0'],[0,0,'—'],[0,null,'—']]){
        await page.evaluate(({count,sum})=>{const payload=JSON.parse(model.payload);
          payload.scopes.launch.summary.xp_received={count,min:null,avg:null,max:null,sum};
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},{count,sum});await frames(page);
        const value=await page.locator('.ss-summary-xp-total .ss-xp-total-value').textContent();
        const missing=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages.uk['format.missing'];
        check('Summary total distinguishes known zero from unavailable XP at '+scale+'x count='+count+' sum='+sum,
          value===(expected==='—'?missing:expected));
      }
    }finally{await page.close();}
  }
};
