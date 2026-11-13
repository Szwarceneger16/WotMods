/* Decorative thumbnail pixels reach the frame; tactical map edges stay intact. */
module.exports=async({browser,nativeHost,check})=>{
  const page=await nativeHost(browser,{});
  try{
    await page.evaluate(()=>{
      const snapshot=JSON.parse(model.payload),scope=snapshot.scopes.launch,sample=scope.battles[0];
      scope.battles=[{...sample,id:'thumbnail-frame',outcome:'win',
        outcome_visual:{kind:'outcome',src:'img://gui/maps/icons/library/BgBattleResultIconVictory-1.png'},
        map_visual:{kind:'map',src:'img://gui/maps/icons/map/small/synthetic.png',alt:'Synthetic map'}}];
      model.payload=JSON.stringify(snapshot);GRZSessionStats.update(model.payload);
      document.getElementById('ss-group-battles').click();
      const image=(width,height)=>'url("data:image/svg+xml,'+encodeURIComponent(
        '<svg xmlns="http://www.w3.org/2000/svg" width="'+width+'" height="'+height+'"><rect width="100%" height="100%" fill="#e6a933"/></svg>')+'")';
      document.querySelector('.ss-battle-map-thumb').style.backgroundImage=image(100,60);
      document.querySelectorAll('.ss-outcome-image-layer').forEach(node=>{node.style.backgroundImage=image(288,167);});
    });
    for(const [selector,label] of [['.ss-battle-map-thumb','Map photo'],['.ss-outcome-image','Outcome artwork']]){
      const raster=await page.locator(selector).screenshot();
      const edges=await page.evaluate(encoded=>new Promise(resolve=>{
        const image=new Image();image.onload=()=>{
          const canvas=document.createElement('canvas');canvas.width=image.width;canvas.height=image.height;
          const context=canvas.getContext('2d');context.drawImage(image,0,0);
          resolve([1,image.width-2].map(x=>Array.from(context.getImageData(x,Math.floor(image.height/2),1,1).data)));
        };image.onerror=()=>resolve([]);image.src='data:image/png;base64,'+encoded;
      }),raster.toString('base64'));
      check(label+' reaches both inner frame edges without black containment bands',
        edges.length===2&&edges.every(pixel=>pixel[0]===230&&pixel[1]===169&&pixel[2]===51&&pixel[3]===255));
    }
    const sourcePolicy=await page.evaluate(()=>{
      const snapshot=JSON.parse(model.payload),scope=snapshot.scopes.launch,sample=scope.maps[0];
      scope.maps=['small/photo.png','screen/photo.dds','synthetic.png','future/map.dds'].map((file,index)=>({...sample,
        id:'thumbnail-policy-'+index,visual:{kind:'map',src:'img://gui/maps/icons/map/'+file}}));
      model.payload=JSON.stringify(snapshot);GRZSessionStats.update(model.payload);document.getElementById('ss-group-maps').click();
      return Array.from(document.querySelectorAll('.ss-group-thumb')).map(node=>getComputedStyle(node).backgroundSize);
    });
    check('Only recognized map photo branches crop thumbnails; tactical and unknown sources retain full containment',
      sourcePolicy.join('|')==='cover|cover|contain|contain');
  }finally{await page.close();}
};
