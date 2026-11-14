/* Summary XP keeps horizontal totals while coverage lives in explicit help. */
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
          for(const currency of Object.values(stats.currencies))for(const field of ['income','costs','net'])currency[field+'_count']=3;
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
              explanation:amount.getAttribute('aria-label'),
              top:box.top/scale,bottom:box.bottom/scale,left:box.left/scale,right:box.right/scale,width:box.width/scale,
              labelLeft:labelBox.left/scale,labelRight:labelBox.right/scale,labelBottom:labelBox.bottom/scale,
              fits:box.left>=root.left-1&&box.right<=root.right+1&&labelFits&&coverageFits&&ink.left>=box.left-1&&ink.right<=box.right+1&&ink.top>=box.top-1&&ink.bottom<=box.bottom+1&&
                labelBox.bottom<=valueBox.top+1};
          });
          const tables=[...summary.querySelectorAll('.ss-summary-details > .ss-performance,.ss-summary-details > .ss-economy')].map(section=>{
            const header=section.querySelector('.ss-metric-head,.ss-money-head'),cell=header.querySelector('.ss-summary-table-heading'),
              title=cell?.querySelector('.ss-detail-title'),text=title?.querySelector('.ss-table-heading-text'),
              body=section.querySelector('.ss-metric-row,.ss-money-row');
            if(!cell||!title||!text)return {valid:false};
            const box=cell.getBoundingClientRect(),titleBox=title.getBoundingClientRect(),headerBox=header.getBoundingClientRect(),
              range=document.createRange();range.selectNodeContents(text);
            const firstNumber=header.querySelector('.ss-metric-number,.ss-money-value'),numberRange=document.createRange();numberRange.selectNodeContents(firstNumber);
            const numberBox=numberRange.getBoundingClientRect(),sameRow=numberBox.top<titleBox.bottom;
            const limit=sameRow?numberBox.left-scale:box.right;
            const fits=titleBox.left>=box.left-1&&titleBox.right<=box.right+1&&
              [...range.getClientRects()].every(r=>r.left>=box.left-1&&r.right<=box.right+1&&r.right<=limit+0.5&&r.top>=titleBox.top-1&&r.bottom<=titleBox.bottom+1);
            const info=title.querySelector('.ss-info-button'),infoBox=info?.getBoundingClientRect();
            const hit=infoBox&&document.elementFromPoint((infoBox.left+infoBox.right)/2,(infoBox.top+infoBox.bottom)/2);
            const headingColumns=[...header.querySelectorAll('.ss-metric-number,.ss-money-value')].map(node=>node.getBoundingClientRect()),
              bodyColumns=[...body.querySelectorAll('.ss-metric-number,.ss-money-value')].map(node=>node.getBoundingClientRect());
            return {valid:true,text:text.textContent,coverage:header.querySelectorAll('.ss-cell-coverage').length,
              outside:[...section.children].filter(node=>node.classList.contains('ss-detail-title')).length,
              fits:fits&&infoBox&&infoBox.left>=box.left-1&&infoBox.right<=box.right+1&&infoBox.right<=limit+0.5&&headerBox.bottom<=body.getBoundingClientRect().top+1,
              aligned:headingColumns.length===bodyColumns.length&&headingColumns.every((column,index)=>Math.abs(column.left-bodyColumns[index].left)<=scale&&Math.abs(column.width-bodyColumns[index].width)<=scale),
              reachable:info&&hit&&(hit===info||info.contains(hit)),help:info?.getAttribute('data-ss-help')};
          });
          return {totals,tables,height:wrapper.height/scale,rootBottom:root.bottom/scale,
            horizontal:totals.every((item,index)=>Math.abs(item.top-totals[0].top)<=1&&(!index||item.left>=totals[index-1].right-1)),
            contained:totals.every(item=>item.top>=wrapper.top/scale-1&&item.bottom<=wrapper.bottom/scale+1),
            semanticRows:table.querySelectorAll('[role="row"]').length,headers:table.querySelectorAll('[role="columnheader"]').length,
            redundantWN8:summary.querySelectorAll('.ss-wn8-coverage').length,separateFooter:summary.querySelectorAll('.ss-summary-coverage').length};
        },scale);
        const caption=language+' '+width+'rem '+scale+'x';
        const metrics=['xp_base','xp_received','free_xp'],labels=['xp.base_total','xp.received_total','xp.free'];
        check('Horizontal summary retains independent XP totals without repeating visible coverage: '+caption+': '+JSON.stringify(audit),
          audit.totals.length===3&&audit.totals.every((item,index)=>item.metric===metrics[index]&&item.label===messages[labels[index]]&&
            item.value===['600','12345678','1234'][index]&&item.coverage===undefined&&
            item.explanation===messages[labels[index]]+' '+messages['coverage.value'].replace('{0}',[3,2,1][index]).replace('{1}',4)));
        check('All three XP columns stay beside each other with aligned headers and values: '+caption,
          audit.totals.every(item=>item.fits)&&audit.horizontal&&audit.contained&&audit.height<=69&&audit.semanticRows===2&&audit.headers===3&&
          audit.totals.every(item=>Math.abs(item.width-audit.totals[0].width)<=1&&Math.abs(item.left-item.labelLeft)<=1&&Math.abs(item.right-item.labelRight)<=1));
        check('Horizontal totals remove duplicate WN8 coverage and the separate Free XP footer: '+caption,
          audit.redundantWN8===0&&audit.separateFooter===0&&audit.totals.every(item=>item.bottom<=audit.rootBottom+1));
        check('Overview table names replace header counts with contained titles and explicit help: '+caption+': '+JSON.stringify(audit.tables),
          audit.tables.length===2&&audit.tables.every((table,index)=>table.valid&&table.fits&&table.aligned&&table.reachable&&table.outside===0&&table.coverage===0&&
            table.text===messages[index?'finance.period':'performance.period']&&table.help));
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
