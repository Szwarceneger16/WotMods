/* Summary XP uses one horizontal header row and one independently covered value row. */
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
          stats.battles=3;stats.observed_battles=4;stats.wn8_count=2;
          stats.xp_base={count:3,min:100,avg:200,max:300,sum:600};
          stats.xp_received={count:2,min:18,avg:6172839,max:12345660,sum:12345678};
          stats.free_xp={count:1,min:1234,avg:1234,max:1234,sum:1234};
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
        },{language,messages,width,scale});
        await page.locator('#ss-scope-launch').click();await settledSummary(page,width,scale);
        const audit=await page.locator('#ss-summary').evaluate((summary,scale)=>{
          const root=summary.getBoundingClientRect(),table=summary.querySelector('.ss-summary-xp-totals'),wrapper=table.getBoundingClientRect();
          const totals=[...summary.querySelectorAll('.ss-summary-xp-total')].map(total=>{
            const metric=total.getAttribute('data-xp-metric'),value=total.querySelector('.ss-xp-total-value'),amount=total.querySelector('.ss-xp-total-amount'),
              label=summary.querySelector('.ss-xp-total-label[data-xp-metric="'+metric+'"]')||total.querySelector('.ss-xp-total-label');
            const box=total.getBoundingClientRect(),valueBox=amount.getBoundingClientRect(),labelBox=label.getBoundingClientRect();
            const range=document.createRange();range.selectNodeContents(value);const ink=range.getBoundingClientRect();
            const labelRange=document.createRange();labelRange.selectNodeContents(label);
            const labelFits=[...labelRange.getClientRects()].every(r=>r.left>=labelBox.left-1&&r.right<=labelBox.right+1&&r.top>=labelBox.top-1&&r.bottom<=labelBox.bottom+1);
            const coverage=total.querySelector('.ss-count-coverage');
            const coverageRange=document.createRange();if(coverage)coverageRange.selectNodeContents(coverage);
            const coverageFits=!coverage||[...coverageRange.getClientRects()].every(r=>r.left>=box.left-1&&r.right<=box.right+1&&r.top>=box.top-1&&r.bottom<=box.bottom+1);
            return {metric,label:label.textContent,value:value.textContent.replace(/\s/g,''),coverage:coverage?.textContent.replace(/\s/g,''),
              top:box.top/scale,bottom:box.bottom/scale,left:box.left/scale,right:box.right/scale,width:box.width/scale,
              labelLeft:labelBox.left/scale,labelRight:labelBox.right/scale,labelBottom:labelBox.bottom/scale,
              fits:box.left>=root.left-1&&box.right<=root.right+1&&labelFits&&coverageFits&&ink.left>=box.left-1&&ink.right<=box.right+1&&ink.top>=box.top-1&&ink.bottom<=box.bottom+1&&
                labelBox.bottom<=valueBox.top+1};
          });
          return {totals,height:wrapper.height/scale,rootBottom:root.bottom/scale,
            horizontal:totals.every((item,index)=>Math.abs(item.top-totals[0].top)<=1&&(!index||item.left>=totals[index-1].right-1)),
            contained:totals.every(item=>item.top>=wrapper.top/scale-1&&item.bottom<=wrapper.bottom/scale+1),
            semanticRows:table.querySelectorAll('[role="row"]').length,headers:table.querySelectorAll('[role="columnheader"]').length,
            redundantWN8:summary.querySelectorAll('.ss-wn8-coverage').length,separateFooter:summary.querySelectorAll('.ss-summary-coverage').length};
        },scale);
        const caption=language+' '+width+'rem '+scale+'x';
        const metrics=['xp_base','xp_received','free_xp'],labels=['xp.base_total','xp.received_total','xp.free'];
        check('Horizontal summary retains independent XP totals and coverage: '+caption+': '+JSON.stringify(audit),
          audit.totals.length===3&&audit.totals.every((item,index)=>item.metric===metrics[index]&&item.label===messages[labels[index]]&&
            item.value===['600','12345678','1234'][index]&&item.coverage===['(3/4)','(2/4)','(1/4)'][index]));
        check('All three XP columns stay beside each other with aligned headers and values: '+caption,
          audit.totals.every(item=>item.fits)&&audit.horizontal&&audit.contained&&audit.height<=86&&audit.semanticRows===2&&audit.headers===3&&
          audit.totals.every(item=>Math.abs(item.width-audit.totals[0].width)<=1&&Math.abs(item.left-item.labelLeft)<=1&&Math.abs(item.right-item.labelRight)<=1));
        check('Horizontal totals remove duplicate WN8 coverage and the separate Free XP footer: '+caption,
          audit.redundantWN8===0&&audit.separateFooter===0&&audit.totals.every(item=>item.bottom<=audit.rootBottom+1));
      }
      for(const metric of ['xp_base','xp_received','free_xp'])for(const [count,sum,expected] of [[2,0,'0'],[0,0,'—'],[0,null,'—']]){
        await page.evaluate(({metric,count,sum})=>{const payload=JSON.parse(model.payload);
          payload.scopes.launch.summary[metric]={count,min:null,avg:null,max:null,sum};
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();},{metric,count,sum});await frames(page);
        const value=await page.locator('.ss-summary-xp-total[data-xp-metric="'+metric+'"] .ss-xp-total-value').textContent();
        const missing=languages.uk['format.missing'];
        check('Summary total distinguishes known zero from unavailable '+metric+' at '+scale+'x count='+count+' sum='+sum,
          value===(expected==='—'?missing:expected));
      }
    }finally{await page.close();}
  }
};
