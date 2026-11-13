/* Result/map/action columns stay aligned without measuring localized captions. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>{let count=10;
  function next(){if(--count)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}));
module.exports=async({browser,nativeHost,check})=>{
  const page=await nativeHost(browser,{});
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  const names={en:['Ruinberg',"Empire's Border",'Mannerheim Line','Highway'],
    pl:['Ruinberg','Granica imperium','Linia Mannerheima','Autostrada'],
    de:['Ruinberg','Grenze des Reichs','Mannerheim-Linie','Autobahn'],
    fr:['Ruinberg','Frontière impériale','Ligne Mannerheim','Autoroute'],
    es:['Ruinberg','Frontera del Imperio','Línea Mannerheim','Autopista'],
    ru:['Руинберг','Граница империи','Линия Маннергейма','Хайвей'],
    uk:['Руїнберг','Кордон імперії','Лінія Маннергейма','Хайвей']};
  await page.evaluate(()=>{window.__headerAlignmentFixture=JSON.parse(model.payload);});
  for(const scale of [1,2])for(const [language,messages] of Object.entries(languages))for(const width of [500,720,800]){
    await page.setViewportSize({width:2700*scale,height:1300*scale});
    await page.evaluate(({scale,language,messages,width,names})=>{
      const snapshot=JSON.parse(JSON.stringify(__headerAlignmentFixture)),sample=snapshot.scopes.launch.battles[0];
      snapshot.account_key='header-columns-'+scale+'-'+language+'-'+width;
      snapshot.viewport={width:2700*scale,height:1300*scale,scale};snapshot.window_size=[2000,1000];
      snapshot.appearance={wide_card_widths:{battles:width},window_settings:{background_transparency:0,maximized:false,restored_width:2000,restored_height:1000}};
      snapshot.localization={language,messages};
      snapshot.scopes.launch.battles=['win','loss','draw','unknown'].map((outcome,index)=>({
        ...sample,id:'aligned-'+outcome,outcome,map:names[index],name:'Bat.-Châtillon 25 t',
        visual:{kind:'vehicle',src:'img://gui/maps/icons/vehicle/synthetic.png',alt:'Synthetic vehicle'},
        outcome_visual:index<3?{kind:'outcome',src:'img://gui/maps/icons/library/BgBattleResultIcon'+['Victory','Defeat','Draw'][index]+'-1.png'}:null,
        map_visual:{kind:'map',src:'img://gui/maps/icons/map/small/synthetic-'+index+'.png',preview_src:'img://gui/maps/icons/map/screen/synthetic-'+index+'.dds',alt:names[index]}
      }));
      model.payload=JSON.stringify(snapshot);GRZSessionStats.update(model.payload);document.getElementById('ss-group-battles').click();
    },{scale,language,messages,width,names:names[language]});
    await frames(page);
    const expectedOutcomes={};for(const outcome of ['win','loss','draw','unknown'])expectedOutcomes[outcome]=messages['outcome.'+outcome].toUpperCase();
    const geometry=await page.locator('#ss-groups .ss-group').evaluateAll((cards,{scale,width,expectedOutcomes})=>{
      const relative=(node,origin)=>{const r=node.getBoundingClientRect();return {left:(r.left-origin.left)/scale,right:(r.right-origin.left)/scale,top:(r.top-origin.top)/scale,bottom:(r.bottom-origin.top)/scale,width:r.width/scale,height:r.height/scale};};
      const rows=cards.map(card=>{
        const origin=card.querySelector('.ss-group-header').getBoundingClientRect(),failures=[];
        const parts={outcome:'.ss-battle-outcome',map:'.ss-battle-map-visual',mapArt:'.ss-battle-map-thumb',action:'.ss-more-button'};
        const positions={};for(const [key,selector] of Object.entries(parts))positions[key]=relative(card.querySelector(selector),origin);
        const image=card.querySelector('.ss-outcome-image');if(image)positions.resultArt=relative(image,origin);
        const resultLabel=card.querySelector('.ss-outcome-label').textContent;
        const resultKind=['win','loss','draw','unknown'].find(kind=>card.querySelector('.ss-battle-outcome').classList.contains('ss-outcome-'+kind));
        if(resultLabel!==expectedOutcomes[resultKind])failures.push('outcome-not-localized-uppercase');
        const children=Array.from(card.querySelector('.ss-group-header').children).map(node=>relative(node,origin));
        for(let i=0;i<children.length;i++)for(let j=i+1;j<children.length;j++){
          const a=children[i],b=children[j];if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>1&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1)failures.push('overlap');
        }
        for(const node of card.querySelectorAll('.ss-group-title,.ss-group-subtitle,.ss-free-xp,.ss-outcome-label,.ss-battle-map-label,.ss-more-button .ss-control-label')){
          const bounds=node.getBoundingClientRect(),range=document.createRange();range.selectNodeContents(node);
          if(Array.from(range.getClientRects()).some(text=>text.width>0&&(text.left<bounds.left-scale||text.right>bounds.right+scale||text.top<bounds.top-scale||text.bottom>bounds.bottom+scale)))failures.push('clipped:'+node.textContent);
        }
        if(Math.abs(card.getBoundingClientRect().width/scale-width)>1||origin.height/scale>64||card.getBoundingClientRect().height/scale>165)failures.push('dimensions');
        return {positions,headerHeight:origin.height/scale,cardHeight:card.getBoundingClientRect().height/scale,failures};
      });
      for(const [index,row] of rows.entries())for(const [key,box] of Object.entries(row.positions)){
        const reference=rows.find(other=>other.positions[key]).positions[key];
        if(['left','right','top','bottom'].some(axis=>Math.abs(box[axis]-reference[axis])>1))row.failures.push('column-drift:'+key+':'+index);
      }
      return {passed:rows.length===4&&rows.every(row=>!row.failures.length),rows};
    },{scale,width,expectedOutcomes});
    check('Localized battle result, map and action slots align at '+width+'px, '+language+' '+scale*100+'%'+
      (geometry.passed?'':': '+JSON.stringify(geometry)),geometry.passed);
    if(width===720&&language==='ru'&&scale===1){
      const card=page.locator('#ss-groups .ss-group').first();
      const positions=()=>card.evaluate(node=>{const origin=node.getBoundingClientRect();return ['.ss-battle-outcome','.ss-battle-map-thumb','.ss-more-button'].map(selector=>{const box=node.querySelector(selector).getBoundingClientRect();return [box.left-origin.left,box.width];});});
      const before=await positions();await card.locator('.ss-more-button').click();await frames(page);
      const after=await positions();
      check('Opening More preserves the result/map/action columns when the localized action changes length',
        before.every((box,index)=>box.every((value,axis)=>Math.abs(value-after[index][axis])<=1)));
      await card.locator('.ss-more-button').click();
    }
  }
  await page.close();
};
