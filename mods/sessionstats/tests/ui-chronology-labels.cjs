/* Native fonts need words for both the battle boundary and date direction. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let left=5;
  function next(){if(--left)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}));
const choices=[['newest','sort.last_newest.description'],['last_asc','sort.last_oldest.description'],
  ['first_desc','sort.first_newest.description'],['oldest','sort.first_oldest.description']];
const geometry=page=>page.evaluate(()=>{
  const holder=document.getElementById('ss-sort-chronology'),trigger=holder.querySelector('.ss-select-trigger'),
    menu=holder.querySelector('.ss-select-options'),panel=document.getElementById('grz-session-stats'),
    scale=parseFloat(document.documentElement.style.fontSize)||1;
  function box(node){const r=node.getBoundingClientRect();return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,width:r.width,height:r.height};}
  function textFits(node){const r=box(node),range=document.createRange();range.selectNodeContents(node);
    return Array.from(range.getClientRects()).every(text=>text.left>=r.left-1&&text.right<=r.right+1&&
      text.top>=r.top-1&&text.bottom<=r.bottom+1);}
  const label=trigger.querySelector('.ss-control-label'),options=Array.from(menu.querySelectorAll('.ss-select-option'))
    .filter(node=>node.style.display!=='none').map(node=>({value:node.getAttribute('data-value'),text:node.textContent,
      fits:textFits(node.querySelector('.ss-control-label'))}));
  return {caption:label.textContent,captionFits:textFits(label),label:box(label),trigger:box(trigger),
    menu:box(menu),panel:box(panel),options,pagination:box(document.getElementById('ss-pagination')),
    mode:document.getElementById('ss-list-controls').getAttribute('data-filter-layout'),scale};
});
module.exports=async({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  for(const {width,scale} of [{width:550,scale:1},{width:960,scale:1},{width:550,scale:2},{width:960,scale:2}]){
    const game={width:3840,height:2400,scale},page=await nativeHost(browser,{initialViewport:game,viewport:game,realTimers:true});
    try{
      for(const [language,messages] of Object.entries(languages)){
        await page.evaluate(({width,language,messages})=>{
          const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
          payload.account_key='synthetic-chronology-caption-'+language;payload.window_size=[width,1100];
          payload.appearance=payload.appearance||{};payload.appearance.window_settings={
            background_transparency:0,maximized:false,restored_width:width,restored_height:1100};
          payload.localization={language,selected:language,messages};scope.loading=false;scope.load_error='';
          for(const group of ['vehicles','maps','tiers'])scope.ordering[group]={metric:'off',statistic:'avg',direction:'desc',chronology:'newest'};
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
        },{width,language,messages});await frames(page);
        await page.locator('#ss-group-maps').click();await frames(page);
        const label=language+' at '+width+'rem/'+scale+'x';
        for(const [value,key] of choices){
          await page.locator('#ss-sort-chronology .ss-select-trigger').click();
          const opened=await geometry(page);
          check('All four chronology choices use complete distinct words in '+label,
            opened.options.length===4&&new Set(opened.options.map(option=>option.text)).size===4&&
            opened.options.every((option,index)=>option.text===messages[choices[index][1]]&&!/[\u2190-\u21ff]/.test(option.text)));
          check('The full chronology menu fits inside the panel in '+label+': '+JSON.stringify(opened.options),
            opened.options.every(option=>option.fits)&&opened.menu.left>=opened.panel.left-1&&opened.menu.right<=opened.panel.right+1);
          await page.locator('#ss-sort-chronology [data-value="'+value+'"]').click();
          const request=await page.evaluate(()=>__grzCommands.filter(command=>command.action==='sort').pop());
          check('Choosing the complete caption preserves chronology identity '+value+' in '+label,request.chronology===value&&request.group==='maps');
          await page.evaluate(request=>{
            const payload=JSON.parse(model.payload);payload.scopes.launch.ordering.maps={metric:'off',statistic:'avg',direction:'desc',chronology:request.chronology};
            model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
          },request);await frames(page);
          const selected=await geometry(page);
          check('Selected boundary and direction remain fully visible for '+value+' in '+label+': '+JSON.stringify(selected),
            selected.caption===messages[key]&&selected.captionFits&&selected.label.top>=selected.trigger.top-1&&
            selected.label.bottom<=selected.trigger.bottom+1&&selected.trigger.height<=30*scale+1&&
            Math.abs(selected.pagination.width-340*scale)<=1&&selected.mode===(width===960?'wide':'wrapped'));
        }
        for(const group of ['vehicles','tiers']){
          await page.locator('#ss-group-'+group).click();await frames(page);
          await page.locator('#ss-sort-chronology .ss-select-trigger').click();const menu=await geometry(page);
          check('Grouped chronology captions stay complete in '+group+' '+label,
            menu.options.length===(group==='tiers'?6:4)&&menu.options.slice(0,4).every((option,index)=>
              option.text===messages[choices[index][1]]&&option.fits));
          await page.keyboard.press('Escape');
        }
        await page.locator('#ss-group-battles').click();await frames(page);
        await page.locator('#ss-sort-chronology .ss-select-trigger').click();const battles=await geometry(page);
        check('Individual battles retain their two ordinary date directions in '+label,
          battles.options.length===2&&battles.options[0].text===messages['sort.newest']&&battles.options[1].text===messages['sort.oldest']);
        await page.keyboard.press('Escape');
      }
    }finally{await page.close();}
  }
};
