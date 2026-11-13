/* Both XP totals keep their independent data and reserve native caption/value rows. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
async function settledSummary(page,width,scale){
  await page.waitForFunction(({width,scale})=>{
    const panel=document.getElementById('grz-session-stats'),summary=document.getElementById('ss-summary');
    return window.__nativeSize&&__nativeSize[0]===Math.ceil(width*scale)&&
      Math.abs(panel.getBoundingClientRect().width-width*scale)<=scale&&
      summary.classList.contains('ss-narrow-summary')===(width-34<350);
  },{width,scale});
  await frames(page);
}
module.exports=async({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:3840,height:2400},viewport:{width:3840,height:2400,scale}});
    try{
      for(const [language,messages] of Object.entries(languages))for(const width of [320,550,1200]){
        await page.evaluate(({language,messages,width,scale})=>{
          const payload=JSON.parse(model.payload);
          payload.account_key='synthetic-xp-total-'+language+'-'+width+'-'+scale;
          payload.window_size=[width,1000];payload.localization={language,messages};
          payload.viewport={width:Math.min(3840,width*scale+20),height:2400,scale};
          payload.appearance=payload.appearance||{};
          payload.appearance.window_settings={background_transparency:0,maximized:false,restored_width:width,restored_height:1000};
          const stats=payload.scopes.launch.summary;
          stats.battles=3;stats.observed_battles=4;
          stats.xp_base={count:3,min:100,avg:200,max:300,sum:600};
          stats.xp_received={count:2,min:18,avg:6172839,max:12345660,sum:12345678};
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
        },{language,messages,width,scale});
        await page.locator('#ss-scope-launch').click();await settledSummary(page,width,scale);
        const heights=[];
        for(const type of ['base','received']){
          await page.locator('#ss-xp-'+type).click();await frames(page);
          const audit=await page.locator('#ss-summary').evaluate((summary,scale)=>{
            const root=summary.getBoundingClientRect(),wrapper=summary.querySelector('.ss-summary-xp-totals').getBoundingClientRect();
            const footer=summary.querySelector('.ss-summary-coverage')?.getBoundingClientRect()||summary.querySelector('.ss-summary-meta > .ss-free-xp').getBoundingClientRect();
            const totals=[...summary.querySelectorAll('.ss-summary-xp-total')].map(total=>{
              const value=total.querySelector('.ss-xp-total-value'),box=total.getBoundingClientRect(),range=document.createRange();
              range.selectNodeContents(value);const ink=range.getBoundingClientRect();
              const labels=[...total.querySelectorAll('.ss-xp-total-label,.ss-count-coverage')];
              return {metric:total.getAttribute('data-xp-metric'),label:total.querySelector('.ss-xp-total-label').textContent,
                value:value.textContent.replace(/\s/g,''),coverage:total.querySelector('.ss-count-coverage')?.textContent.replace(/\s/g,''),
                top:box.top/scale,width:box.width/scale,
                bottom:box.bottom/scale,inkBottom:ink.bottom/scale,
                fits:box.left>=root.left-1&&box.right<=root.right+1&&ink.left>=box.left-1&&ink.right<=box.right+1&&ink.top>=box.top-1&&ink.bottom<=box.bottom+1&&
                  labels.every(node=>{const text=document.createRange();text.selectNodeContents(node);return [...text.getClientRects()].every(r=>r.left>=box.left-1&&r.right<=box.right+1&&r.top>=box.top-1&&r.bottom<=box.bottom+1);})};
            });
            return {totals,height:wrapper.height/scale,narrow:summary.classList.contains('ss-narrow-summary'),
              ordered:totals.every(total=>total.inkBottom<=footer.top/scale+1)&&footer.top>=wrapper.bottom-1,
              columns:summary.querySelectorAll('.ss-performance .ss-metric-head .ss-metric-number').length,
              rows:summary.querySelectorAll('.ss-performance .ss-metric-row').length};
          },scale);
          heights.push(audit.height);
          const caption=language+' '+width+'rem '+scale+'x '+type;
          check('Both XP totals stay visible with independent sums and coverage: '+caption+': '+JSON.stringify(audit),
            audit.totals.length===2&&audit.totals.every((item,index)=>item.metric==='xp_'+['base','received'][index]&&
              item.label===messages['xp.'+['base','received'][index]+'_total']&&
              item.value===(index===0?'600':'12345678')&&item.coverage===(index===0?'(3/4)':'(2/4)')));
          check('Both XP totals fit aligned columns without adding a WN8 sum: '+caption,
            audit.totals.every(item=>item.fits)&&audit.columns===3&&audit.rows===2&&audit.ordered&&audit.height<=(audit.narrow?52:35)&&
            Math.abs(audit.totals[0].top-audit.totals[1].top)<=1&&Math.abs(audit.totals[0].width-audit.totals[1].width)<=1);
        }
        check('Switching XP keeps both totals and the row height stable in '+language+' at '+width+'rem/'+scale+'x',Math.abs(heights[0]-heights[1])<=1);
        // Model the observed native intrinsic-size error: a two-line wrapping
        // flex child can report only17rem. Explicit row minima must win over it.
        const collapse=await page.addStyleTag({content:'.ss-summary-xp-totals { height:17rem; }'});
        await frames(page);
        const nativeRows=await page.locator('#ss-summary').evaluate((summary,scale)=>{
          const totals=summary.querySelector('.ss-summary-xp-totals'),box=totals.getBoundingClientRect();
          const footer=summary.querySelector('.ss-summary-coverage')||summary.querySelector('.ss-summary-meta > .ss-free-xp');
          const following=footer.getBoundingClientRect();
          const values=[...totals.querySelectorAll('.ss-xp-total-value,.ss-count-coverage')].map(node=>{
            const range=document.createRange();range.selectNodeContents(node);return range.getBoundingClientRect();
          });
          return {height:box.height/scale,followingTop:following.top/scale,totalBottom:box.bottom/scale,
            contained:values.every(ink=>ink.top>=box.top-1&&ink.bottom<=box.bottom+1&&ink.bottom<=following.top+1),
            narrow:summary.classList.contains('ss-narrow-summary')};
        },scale);
        check('Native one-line intrinsic collapse cannot overlap totals and coverage in '+language+' '+width+'rem/'+scale+'x: '+JSON.stringify(nativeRows),
          nativeRows.height>=(nativeRows.narrow?51:34)&&nativeRows.contained&&nativeRows.followingTop>=nativeRows.totalBottom-1);
        await collapse.evaluate(node=>node.remove());
      }
      for(const [count,sum,expected] of [[2,0,'0'],[0,0,'—'],[0,null,'—']]){
        await page.evaluate(({count,sum})=>{const payload=JSON.parse(model.payload);
          payload.scopes.launch.summary.xp_received={count,min:null,avg:null,max:null,sum};
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},{count,sum});await frames(page);
        const value=await page.locator('.ss-summary-xp-total[data-xp-metric="xp_received"] .ss-xp-total-value').textContent();
        const missing=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages.uk['format.missing'];
        check('Summary total distinguishes known zero from unavailable XP at '+scale+'x count='+count+' sum='+sum,
          value===(expected==='—'?missing:expected));
      }
    }finally{await page.close();}
  }
};
