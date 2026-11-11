/* Native artwork stays unchanged while opaque compositing removes its built-in fade. */
module.exports = async ({browser,nativeHost,check}) => {
  const page = await nativeHost(browser,{});
  await page.evaluate(()=>{
    const snapshot=JSON.parse(model.payload), scope=snapshot.scopes.launch;
    const sample=scope.battles[0];
    scope.battles=['win','loss','draw'].map((outcome,index)=>({
      ...sample,id:'outcome-'+outcome,started_at:1800000000-index,outcome,
      outcome_visual:{kind:'outcome',src:'img://gui/maps/icons/library/BgBattleResultIcon'+
        ['Victory','Defeat','Draw'][index]+'-1.png'},
      map_visual:{kind:'map',src:'img://gui/maps/icons/map/small/synthetic-'+outcome+'.png',
        preview_src:'img://gui/maps/icons/map/screen/synthetic-'+outcome+'.dds',preview_mode:'image',alt:'Synthetic '+outcome+' map'}
    }));
    snapshot.localization={language:'pl',messages:{
      'outcome.win':'Zwycięstwo','outcome.loss':'Porażka','outcome.draw':'Remis'}};
    model.payload=JSON.stringify(snapshot);GRZSessionStats.update(model.payload);
    document.getElementById('ss-group-battles').click();
  });
  check('All three battle results composite their exact native artwork on opaque frames',await page.evaluate(()=>
    ['Victory','Defeat','Draw'].every((name,index)=>{
      const node=document.querySelectorAll('.ss-outcome-image')[index], style=node&&getComputedStyle(node);
      const layers=node&&Array.from(node.querySelectorAll('.ss-outcome-image-layer'));
      return style && style.opacity==='1' && style.backgroundColor.startsWith('rgb(') &&
        layers.length===12 && layers.every(layer=>{const paint=getComputedStyle(layer);
          return paint.backgroundImage.includes('/BgBattleResultIcon'+name+'-1.png') &&
            paint.backgroundSize==='contain' && paint.position==='absolute' && paint.opacity==='1' && paint.filter==='none';
        }) && node.textContent==='';
    })));
  check('WG-localized captions sit beside the unchanged composited image',await page.evaluate(()=>
    Array.from(document.querySelectorAll('.ss-outcome-label')).map(n=>n.textContent).join('|')===
      'Zwycięstwo|Porażka|Remis' && Array.from(document.querySelectorAll('.ss-outcome-art')).every(node=>{
        const image=node.querySelector('.ss-outcome-image'),label=node.querySelector('.ss-outcome-label');
        return image.getAttribute('aria-hidden')==='true' &&
          label.getBoundingClientRect().left>=image.getBoundingClientRect().right-1 &&
          label.getBoundingClientRect().top<image.getBoundingClientRect().bottom &&
          node.getBoundingClientRect().height<=40;
      })));
  // A real raster check with a synthetic 20%-alpha texel: one layer is red=51,
  // twelve layers are red~=238. No native WG raster is copied into test inputs.
  const painted=page.locator('.ss-outcome-image').first();
  await painted.evaluate(node=>{
    const layers=Array.from(node.children);
    window.__outcomePaintRestore={node,background:node.style.background,layers:layers.map(layer=>layer.style.backgroundImage)};
    node.style.background='#000000';
    const pixel='data:image/svg+xml,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"><rect width="10" height="10" fill="red" fill-opacity="0.2"/></svg>');
    layers.forEach(layer=>{layer.style.backgroundImage='url("'+pixel+'")';});
  });
  const raster=await painted.screenshot();
  const pixel=await page.evaluate(encoded=>new Promise(resolve=>{
    const image=new Image();image.onload=()=>{const canvas=document.createElement('canvas');canvas.width=image.width;canvas.height=image.height;
      const context=canvas.getContext('2d');context.drawImage(image,0,0);resolve(Array.from(context.getImageData(Math.floor(image.width/2),Math.floor(image.height/2),1,1).data));};
    image.onerror=()=>resolve([]);image.src='data:image/png;base64,'+encoded;
  }),raster.toString('base64'));
  check('Opaque result-frame compositing makes a faded texel vivid without editing its texture',
    pixel.length===4&&pixel[0]>=235&&pixel[1]===0&&pixel[2]===0&&pixel[3]===255);
  await page.evaluate(()=>{const saved=__outcomePaintRestore;saved.node.style.background=saved.background;
    Array.from(saved.node.children).forEach((layer,index)=>{layer.style.backgroundImage=saved.layers[index];});delete window.__outcomePaintRestore;});
  const thumb=page.locator('.ss-battle-map-thumb').first();await thumb.hover();
  check('Battle map hover uses the same fourfold high-resolution preview as Maps',await thumb.evaluate(node=>{
    const tile=node.getBoundingClientRect(),preview=document.getElementById('ss-map-preview'),box=preview.getBoundingClientRect();
    return getComputedStyle(preview).display==='block'&&Math.abs(box.width-tile.width*4)<=1&&Math.abs(box.height-tile.height*4)<=1&&
      preview.querySelector('.ss-map-preview-image').style.backgroundImage.includes('/map/screen/synthetic-win.dds');
  }));
  await page.locator('#ss-titlebar h1').hover();
  check('Leaving a battle map miniature immediately closes its preview',!await page.locator('#ss-map-preview').isVisible());
  check('Battle cards keep Free XP above the tables and use compact headers and rows',await page.evaluate(()=>
    Array.from(document.querySelectorAll('#ss-groups .ss-group')).every(group=>{
      const free=group.querySelector('.ss-free-xp'), details=group.querySelector('.ss-details');
      return group.querySelector('.ss-group-header').getBoundingClientRect().height<=48 &&
        free.getBoundingClientRect().bottom<=details.getBoundingClientRect().top+1 &&
        Array.from(group.querySelectorAll('.ss-battle-measure,.ss-money-row')).every(row=>row.getBoundingClientRect().height<=30) &&
        group.getBoundingClientRect().height<=145;
    })));
  for(const width of [320,744]) {
    await page.setViewportSize({width,height:820});
    check('Outcome art and identity fit the panel at width '+width,await page.evaluate(()=>{
      const panel=document.getElementById('grz-session-stats').getBoundingClientRect();
      return Array.from(document.querySelectorAll('.ss-outcome-art,.ss-group-name,.ss-battle-map-thumb')).every(node=>{
        const box=node.getBoundingClientRect();return box.width>0 && box.left>=panel.left && box.right<=panel.right;
      });
    }));
  }
  await page.evaluate(()=>{
    const snapshot=JSON.parse(model.payload), rows=snapshot.scopes.launch.battles;
    rows[0].outcome_visual.src='https://example.invalid/banner.png';
    rows[1].outcome_visual.src='img://gui/maps/icons/library/BgBattleResultIconVictory-1.png';
    delete rows[2].outcome_visual;
    GRZSessionStats.update(snapshot);
  });
  check('Missing, remote and mismatched artwork retain readable localized outcomes',
    await page.locator('.ss-outcome-image').count()===0 &&
    (await page.locator('.ss-outcome-label').allTextContents()).join('|')==='Zwycięstwo|Porażka|Remis');
  await page.close();
};
