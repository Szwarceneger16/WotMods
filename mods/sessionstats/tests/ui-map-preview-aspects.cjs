/* Reviewed preview frames remove photo bars; tactical maps keep the whole image. */
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let left=10;
  function next(){if(--left)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);}));
module.exports=async({browser,nativeHost,check})=>{
  const base='img://gui/maps/icons/map/',small=base+'small/synthetic.png';
  const samples=[
    {name:'loading art',src:base+'screen/synthetic.dds',mode:'image',aspect:8/5,fit:'cover'},
    {name:'small thumbnail fallback',src:small,mode:'image',aspect:5/3},
    {name:'default lobby fallback',src:base+'synthetic.png',mode:'image',aspect:1},
    {name:'tactical minimap',src:base+'synthetic.png',mode:'minimap',aspect:1},
    {name:'unknown future branch',src:base+'future/synthetic.dds',mode:'image',aspect:null}
  ];
  for(const scale of [1,1.25,2]){
    const page=await nativeHost(browser,{initialViewport:{width:2400*scale,height:1400*scale},viewport:{width:2400*scale,height:1400*scale,scale}});
    try{
      let revision=0;
      for(const sample of samples){
        const primary=sample.name==='loading art'||sample.name==='tactical minimap';
        if(scale!==1&&!primary)continue;
        await page.mouse.move(0,0);
        await page.evaluate(({small,sample,scale,revision})=>{
          const payload=JSON.parse(model.payload),scope=payload.scopes.launch;
          payload.account_key='synthetic-preview-aspect-'+scale;payload.window_size=[1800,1100];
          scope.data_revision='preview-aspect-'+revision;
          const visual={kind:'map',src:small,preview_src:sample.src,preview_mode:sample.mode,alt:'Synthetic map'};
          scope.maps[0].visual=visual;scope.battles[0].map_visual=visual;
          model.payload=JSON.stringify(payload);__grzEvents['viewEnv.onDataChanged']();
        },{small,sample,scale,revision:++revision});
        for(const group of primary?['maps','battles']:['maps']){
          await page.locator('#ss-group-'+group).click();
          await page.waitForFunction(scale=>{
            const bar=document.getElementById('ss-list-controls');
            return bar.getAttribute('data-filter-layout')==='wide'&&bar.getAttribute('data-filter-width')==='1762'&&
              __nativeSize[0]===1800*scale&&__nativeSize[1]===1100*scale;
          },scale);
          await frames(page);
          const thumb=page.locator('#ss-groups [data-ss-map-preview]').first(),before=await thumb.locator('xpath=..').boundingBox();
          await thumb.hover();await frames(page);
          const result=await page.evaluate(()=>{
            const preview=document.getElementById('ss-map-preview'),image=preview.querySelector('.ss-map-preview-image'),
              thumb=document.querySelector('#ss-groups [aria-describedby="ss-map-preview"]');
            const popup=preview.getBoundingClientRect(),art=image.getBoundingClientRect(),anchor=thumb.getBoundingClientRect(),
              panel=document.getElementById('grz-session-stats').getBoundingClientRect(),css=getComputedStyle(image);
            return {popup:{left:popup.left,right:popup.right,top:popup.top,bottom:popup.bottom,width:popup.width},
              panel:{left:panel.left,right:panel.right,top:panel.top,bottom:panel.bottom},
              artAspect:art.width/art.height,thumbAspect:anchor.width/anchor.height,thumbWidth:anchor.width,
              fit:css.backgroundSize,source:thumb.getAttribute('data-ss-map-preview'),mode:thumb.getAttribute('data-ss-map-preview-mode')};
          });
          const label=sample.name+' in '+group+' at '+scale+'x',aspect=sample.aspect||result.thumbAspect,fit=sample.fit||'contain';
          check('Preview uses its reviewed frame and preserves photo/tactical fit policy: '+label+' '+JSON.stringify(result),
            Math.abs(result.artAspect-aspect)<0.005&&result.fit===fit&&result.source===sample.src&&result.mode===sample.mode);
          check('Natural-aspect preview keeps fourfold width, panel bounds and unchanged card geometry: '+label,
            Math.abs(result.popup.width-result.thumbWidth*4)<=1&&result.popup.left>=result.panel.left&&result.popup.right<=result.panel.right&&
            result.popup.top>=result.panel.top&&result.popup.bottom<=result.panel.bottom&&
            JSON.stringify(before)===JSON.stringify(await thumb.locator('xpath=..').boundingBox()));
          await page.mouse.move(0,0);
        }
      }
    }finally{await page.close();}
  }
};
