/* Native artwork stays unchanged while opaque compositing removes its built-in fade. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let remaining=10;
  function next(){if(--remaining)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}));
module.exports = async ({browser,nativeHost,check}) => {
  const page = await nativeHost(browser,{});
  await page.evaluate(()=>{
    const snapshot=JSON.parse(model.payload), scope=snapshot.scopes.launch;
    const sample=scope.battles[0];
    scope.battles=['win','loss','draw'].map((outcome,index)=>({
      ...sample,id:'outcome-'+outcome,started_at:1800000000-index,outcome,
      map:['Himmelsdorf','Granica imperium','Linia Mannerheima'][index],
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
  check('Normal-card captions stack below the unchanged result artwork without a tall banner',await page.evaluate(()=>
    Array.from(document.querySelectorAll('.ss-outcome-label')).map(n=>n.textContent).join('|')===
      'Zwycięstwo|Porażka|Remis' && Array.from(document.querySelectorAll('.ss-outcome-art')).every(node=>{
        const image=node.querySelector('.ss-outcome-image'),label=node.querySelector('.ss-outcome-label');
        return image.getAttribute('aria-hidden')==='true' &&
          label.getBoundingClientRect().top>=image.getBoundingClientRect().bottom &&
          Math.abs((label.getBoundingClientRect().left+label.getBoundingClientRect().right-image.getBoundingClientRect().left-image.getBoundingClientRect().right)/2)<=1 &&
          node.getBoundingClientRect().height<=59;
      })));
  check('Battle map names sit below their own thumbnails instead of repeating in the identity',await page.evaluate(()=>
    Array.from(document.querySelectorAll('.ss-battle-map-visual')).every((node,index)=>{
      const thumb=node.querySelector('.ss-battle-map-thumb'),label=node.querySelector('.ss-battle-map-label'),name=['Himmelsdorf','Granica imperium','Linia Mannerheima'][index];
      return label.textContent===name && label.getBoundingClientRect().top>=thumb.getBoundingClientRect().bottom &&
        !node.closest('.ss-group').querySelector('.ss-group-subtitle').textContent.includes(name);
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
  check('Battle map hover uses the same fourfold-width loading-art preview as Maps',await thumb.evaluate(node=>{
    const tile=node.getBoundingClientRect(),preview=document.getElementById('ss-map-preview'),box=preview.getBoundingClientRect(),
      image=preview.querySelector('.ss-map-preview-image'),content=image.getBoundingClientRect();
    return getComputedStyle(preview).display==='block'&&Math.abs(box.width-tile.width*4)<=1&&
      Math.abs(content.width/content.height-8/5)<0.005&&getComputedStyle(image).backgroundSize==='cover'&&
      image.style.backgroundImage.includes('/map/screen/synthetic-win.dds');
  }));
  await page.locator('#ss-titlebar h1').hover();
  check('Leaving a battle map miniature immediately closes its preview',!await page.locator('#ss-map-preview').isVisible());
  const compactGeometry=await page.evaluate(()=>{
    const groups=Array.from(document.querySelectorAll('#ss-groups .ss-group')).map(group=>{
      const free=group.querySelector('.ss-free-xp'), details=group.querySelector('.ss-details');
      const box=node=>{const r=node.getBoundingClientRect();return {left:r.left,top:r.top,right:r.right,bottom:r.bottom,width:r.width,height:r.height};};
      const geometry={name:group.querySelector('.ss-group-title').textContent,card:box(group),
        header:box(group.querySelector('.ss-group-header')),identity:box(group.querySelector('.ss-group-name')),
        outcome:box(group.querySelector('.ss-battle-outcome')),map:box(group.querySelector('.ss-battle-map-thumb')),
        free:box(free),details:box(details),rows:Array.from(group.querySelectorAll('.ss-battle-measure,.ss-money-row')).map(box)};
      // A separate map miniature can move Free XP onto its own identity line.
      // Reserve one normal text line, retaining compact rows and full captions.
      geometry.passed=geometry.header.height<=64 && geometry.free.bottom<=geometry.details.top+1 &&
        geometry.rows.every(row=>row.height<=30) && geometry.card.height<=165;
      return geometry;
    });
    return {passed:groups.every(group=>group.passed),groups};
  });
  check('Battle cards keep Free XP above the tables and use compact headers and rows'+
    (compactGeometry.passed?'':': '+JSON.stringify(compactGeometry)),compactGeometry.passed);
  for(const width of [320,744]) {
    await page.setViewportSize({width,height:820});
    check('Outcome art and identity fit the panel at width '+width,await page.evaluate(()=>{
      const panel=document.getElementById('grz-session-stats').getBoundingClientRect();
      return Array.from(document.querySelectorAll('.ss-outcome-art,.ss-group-name,.ss-battle-map-thumb')).every(node=>{
        const box=node.getBoundingClientRect();return box.width>0 && box.left>=panel.left && box.right<=panel.right;
      });
    }));
  }
  // The game parent is 570px wide; its 20px safety margin leaves the supported
  // 550px native surface. Browser viewport models that surface, not the parent.
  await page.setViewportSize({width:550,height:730});
  await page.evaluate(()=>{
    const snapshot=JSON.parse(model.payload);snapshot.viewport={width:570,height:900,scale:1};snapshot.window_size=[550,730];
    snapshot.scopes.launch.battles.forEach(row=>{row.visual={kind:'vehicle',src:'img://gui/maps/icons/vehicle/synthetic-'+row.outcome+'.png',alt:row.name};});
    model.payload=JSON.stringify(snapshot);GRZSessionStats.update(model.payload);
  });
  await page.waitForFunction(()=>__nativeSize[0]===550&&__nativeSize[1]===730);
  const minimumGeometry=await page.evaluate(()=>{
    const panel=document.getElementById('grz-session-stats').getBoundingClientRect(),failures=[],groups=[];
    for(const group of document.querySelectorAll('#ss-groups .ss-group')){
      const header=group.querySelector('.ss-group-header').getBoundingClientRect();
      const selectors=['.ss-group-thumb:not(.ss-battle-map-thumb)','.ss-group-name','.ss-battle-outcome','.ss-battle-map-visual','.ss-more-button'];
      const nodes=selectors.map(selector=>({selector,node:group.querySelector(selector)}));
      const boxes=nodes.map(({selector,node})=>{const r=node&&node.getBoundingClientRect();return {selector,left:r&&r.left,top:r&&r.top,right:r&&r.right,bottom:r&&r.bottom,width:r&&r.width,height:r&&r.height};});
      for(const box of boxes)if(!(box.width>0&&box.height>0)||box.left<panel.left-1||box.right>panel.right+1||box.top<header.top-1||box.bottom>header.bottom+1){failures.push({kind:'visual-bounds',box});}
      for(let i=0;i<boxes.length;i++)for(let j=i+1;j<boxes.length;j++){
        const a=boxes[i],b=boxes[j];if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>1&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1){failures.push({kind:'overlap',a,b});}
      }
      for(const node of group.querySelectorAll('.ss-group-title,.ss-group-subtitle,.ss-free-xp,.ss-outcome-label,.ss-battle-map-label,.ss-more-button .ss-control-label')){
        const r=node.getBoundingClientRect(),range=document.createRange();range.selectNodeContents(node);
        if(Array.from(range.getClientRects()).some(text=>text.width>0&&(text.left<r.left-1||text.right>r.right+1||text.top<r.top-1||text.bottom>r.bottom+1))){failures.push({kind:'clipped-text',text:node.textContent});}
      }
      groups.push({name:group.querySelector('.ss-group-title').textContent,headerHeight:header.height,cardHeight:group.getBoundingClientRect().height,boxes});
    }
    return {passed:panel.width===550&&groups.length===3&&failures.length===0,panelWidth:panel.width,groups,failures};
  });
  check('Vehicle, readable outcome, map and actions fit without overlap at the real 550px native minimum'+
    (minimumGeometry.passed?'':': '+JSON.stringify(minimumGeometry)),minimumGeometry.passed);
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const mapNames={en:["Himmelsdorf","Empire's Border","Mannerheim Line"],pl:['Himmelsdorf','Granica imperium','Linia Mannerheima'],
    de:['Himmelsdorf','Grenze des Reichs','Mannerheim-Linie'],fr:['Himmelsdorf','Frontière impériale','Ligne Mannerheim'],
    es:['Himmelsdorf','Frontera del Imperio','Línea Mannerheim'],ru:['Химмельсдорф','Граница империи','Линия Маннергейма'],
    uk:['Хіммельсдорф','Кордон імперії','Лінія Маннергейма']};
  await page.evaluate(()=>{window.__captionFixture=JSON.parse(model.payload);});
  for(const scale of [1,2])for(const [language,messages] of Object.entries(languages))for(const cardWidth of [500,800]){
    await page.setViewportSize({width:2700*scale,height:1300*scale});
    await page.evaluate(({scale,language,messages,cardWidth,names})=>{
      const snapshot=JSON.parse(JSON.stringify(__captionFixture));snapshot.account_key='synthetic-captions-'+scale+'-'+language+'-'+cardWidth;
      snapshot.viewport={width:2700*scale,height:1300*scale,scale};snapshot.window_size=[2000,1000];
      snapshot.appearance={wide_card_widths:{battles:cardWidth},window_settings:{background_transparency:0,maximized:false,restored_width:2000,restored_height:1000}};
      snapshot.localization={language,messages};snapshot.scopes.launch.battles.forEach((row,index)=>{row.map=names[index];row.map_visual.alt=names[index];});
      model.payload=JSON.stringify(snapshot);GRZSessionStats.update(model.payload);
    },{scale,language,messages,cardWidth,names:mapNames[language]});await frames(page);
    const audit=await page.locator('#ss-groups .ss-group').evaluateAll((cards,{scale,cardWidth})=>cards.map(card=>{
      const box=node=>node.getBoundingClientRect(),header=card.querySelector('.ss-group-header'),r=box(card),h=box(header),issues=[];
      const outcome=card.querySelector('.ss-battle-outcome'),image=outcome.querySelector('.ss-outcome-image'),label=outcome.querySelector('.ss-outcome-label');
      const map=card.querySelector('.ss-battle-map-visual'),thumb=map.querySelector('.ss-battle-map-thumb'),name=map.querySelector('.ss-battle-map-label');
      const inline=card.classList.contains('ss-battle-inline-captions');
      const aligned=(art,text)=>inline?box(text).left>=box(art).right-scale:box(text).top>=box(art).bottom;
      if(inline!==(cardWidth>=700)||!aligned(image,label)||!aligned(thumb,name))issues.push('caption-mode');
      const nodes=Array.from(header.children).filter(node=>box(node).width>0&&box(node).height>0);
      for(let i=0;i<nodes.length;i++)for(let j=i+1;j<nodes.length;j++){
        const a=box(nodes[i]),b=box(nodes[j]);if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>scale&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>scale)issues.push('overlap');
      }
      for(const node of card.querySelectorAll('.ss-group-title,.ss-group-subtitle,.ss-free-xp,.ss-outcome-label,.ss-battle-map-label,.ss-more-button .ss-control-label')){
        const bounds=box(node),range=document.createRange();range.selectNodeContents(node);
        if(Array.from(range.getClientRects()).some(text=>text.width>0&&(text.left<bounds.left-scale||text.right>bounds.right+scale||text.top<bounds.top-scale||text.bottom>bounds.bottom+scale)))issues.push('clipped:'+node.textContent);
      }
      if(Math.abs(r.width/scale-cardWidth)>1||h.height/scale>64||r.height/scale>165)issues.push('dimensions');
      return {width:r.width/scale,header:h.height/scale,height:r.height/scale,inline,issues};
    }),{scale,cardWidth});
    check('Battle captions follow the actual '+cardWidth+'px card without extra height or clipped text: '+language+' at'+(scale*100)+'%'+
      (audit.every(card=>!card.issues.length)?'':': '+JSON.stringify(audit)),audit.length===3&&audit.every(card=>!card.issues.length));
  }
  await page.setViewportSize({width:550,height:730});
  await page.evaluate(()=>{model.payload=JSON.stringify(__captionFixture);GRZSessionStats.update(model.payload);delete window.__captionFixture;});await frames(page);
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
  await require('./ui-battle-header-alignment.cjs')({browser,nativeHost,check});
};
