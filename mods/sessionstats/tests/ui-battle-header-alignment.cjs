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
      Object.assign(sample.stats,{battles:1,observed_battles:1,wn8:389,wn8_count:1,
        xp_base:{count:1,min:205,avg:205,max:205,sum:205},xp_received:{count:1,min:508,avg:508,max:508,sum:508},
        free_xp:{count:1,min:1252,avg:1252,max:1252,sum:1252},
        currencies:{credits:{income_base:123456,income_base_count:1,income:987654,income_count:1,costs:765432,costs_count:1,
          net_base:-641976,net_base_count:1,net:222222,net_count:1},bonds:{income:0,costs:0,net:0}}});
      snapshot.scopes.launch.battles=['win','loss','draw','unknown'].map((outcome,index)=>{
        const [name,kind,key]=[['IS-4','heavyTank','role_HT_break'],['Conqueror GC','SPG','role_SPG'],
          ['CAV 71','heavyTank','role_HT_support'],['Bat.-Châtillon 25 t édition spéciale','mediumTank','role_MT_universal']][index];
        return {...sample,id:'aligned-'+outcome,outcome,map:names[index],name,
          vehicle_meta:{class:kind,elite:true,class_icon:{kind:'vehicle_class',src:'img://gui/maps/icons/vehicleTypes/24x24_metal/'+kind+'_elite.png'},
            role:{key,icon:{kind:'vehicle_role',src:'img://gui/maps/icons/roleExp/roles/'+(kind==='SPG'?'22x22/':'24x24/')+key+'.png'}}},
          visual:{kind:'vehicle',src:'img://gui/maps/icons/vehicle/synthetic.png',alt:'Synthetic vehicle'},
          outcome_visual:index<3?{kind:'outcome',src:'img://gui/maps/icons/library/BgBattleResultIcon'+['Victory','Defeat','Draw'][index]+'-1.png'}:null,
          map_visual:{kind:'map',src:'img://gui/maps/icons/map/small/synthetic-'+index+'.png',preview_src:'img://gui/maps/icons/map/screen/synthetic-'+index+'.dds',alt:names[index]}};
      });
      model.payload=JSON.stringify(snapshot);GRZSessionStats.update(model.payload);document.getElementById('ss-group-battles').click();
    },{scale,language,messages,width,names:names[language]});
    await frames(page);
    const expectedOutcomes={};for(const outcome of ['win','loss','draw','unknown'])expectedOutcomes[outcome]=messages['outcome.'+outcome].toUpperCase();
    const geometry=await page.locator('#ss-groups .ss-group').evaluateAll((cards,{scale,width,language,expectedOutcomes})=>{
      const relative=(node,origin)=>{const r=node.getBoundingClientRect();return {left:(r.left-origin.left)/scale,right:(r.right-origin.left)/scale,top:(r.top-origin.top)/scale,bottom:(r.bottom-origin.top)/scale,width:r.width/scale,height:r.height/scale};};
      const rows=cards.map(card=>{
        const origin=card.querySelector('.ss-group-header').getBoundingClientRect(),failures=[];
        const parts={outcome:'.ss-battle-outcome',map:'.ss-battle-map-visual',mapArt:'.ss-battle-map-thumb',action:'.ss-more-button'};
        const positions={};for(const [key,selector] of Object.entries(parts))positions[key]=relative(card.querySelector(selector),origin);
        const image=card.querySelector('.ss-outcome-image');if(image)positions.resultArt=relative(image,origin);
        const action=card.querySelector('.ss-more-button').getBoundingClientRect(),actionCenter=(action.top+action.bottom)/2;
        for(const [container,art,caption]of [['.ss-battle-outcome','.ss-outcome-image','.ss-outcome-label'],['.ss-battle-map-visual','.ss-battle-map-thumb','.ss-battle-map-label']]){
          const slot=card.querySelector(container),range=document.createRange();range.selectNodeContents(slot.querySelector(caption));
          const ink=[...range.getClientRects()].filter(box=>box.width>0&&box.height>0),picture=slot.querySelector(art);
          if(picture)ink.push(picture.getBoundingClientRect());
          const center=(Math.min(...ink.map(box=>box.top))+Math.max(...ink.map(box=>box.bottom)))/2;
          if(!ink.length||Math.abs(center-actionCenter)>scale)failures.push('visible-content-center:'+container+':'+((center-actionCenter)/scale));
        }
        const resultLabel=card.querySelector('.ss-outcome-label').textContent;
        const resultKind=['win','loss','draw','unknown'].find(kind=>card.querySelector('.ss-battle-outcome').classList.contains('ss-outcome-'+kind));
        if(resultLabel!==expectedOutcomes[resultKind])failures.push('outcome-not-localized-uppercase');
        const children=Array.from(card.querySelector('.ss-group-header').children).map(node=>relative(node,origin));
        for(let i=0;i<children.length;i++)for(let j=i+1;j<children.length;j++){
          const a=children[i],b=children[j];if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>1&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1)failures.push('overlap');
        }
        const identity=card.querySelector('.ss-group-name'),title=identity.querySelector('.ss-group-title'),info=identity.querySelector('.ss-info-button'),
          date=identity.querySelector('.ss-group-meta > .ss-group-subtitle:first-child'),metadata=identity.querySelector('.ss-vehicle-meta'),
          role=metadata?.querySelector('.ss-vehicle-role-icon'),xp=identity.querySelector('.ss-free-xp > strong');
        const sameLine=(a,b)=>{
          if(!a||!b)return false;
          const range=a.getBoundingClientRect(),other=b.getBoundingClientRect();
          return Math.min(range.bottom,other.bottom)-Math.max(range.top,other.top)>scale;
        };
        if(!sameLine(title,info)||!sameLine(date,metadata)||!sameLine(date,xp)||xp.textContent.replace(/\s/g,'')!=='1252')failures.push('two-identity-rows:'+title.textContent);
        if(!role||(title.textContent==='Conqueror GC'&&(role.dataset.vehicleRole!=='role_SPG'||!role.style.backgroundImage.includes('/22x22/role_SPG.png'))))failures.push('vehicle-role:'+title.textContent);
        for(const node of card.querySelectorAll('.ss-group-title,.ss-group-subtitle,.ss-free-xp > span,.ss-free-xp > strong,.ss-outcome-label,.ss-battle-map-label,.ss-more-button .ss-control-label')){
          const bounds=node.getBoundingClientRect(),range=document.createRange();range.selectNodeContents(node);
          const clipped=Array.from(range.getClientRects()).some(text=>text.width>0&&(text.left<bounds.left-scale||text.right>bounds.right+scale||text.top<bounds.top-scale||text.bottom>bounds.bottom+scale));
          if(!clipped)continue;
          const xpCaption=node.matches('.ss-free-xp > span'),owner=xpCaption?node.parentElement:node,
            full=xpCaption?node.textContent+' '+xp.textContent:node.textContent,style=getComputedStyle(node);
          if(!(xpCaption||node.classList.contains('ss-caption-ellipsis'))||node.clientWidth<=0||node.scrollWidth<=node.clientWidth||
            style.whiteSpace!=='nowrap'||style.textOverflow!=='ellipsis'||style.overflowX!=='hidden'||
            owner.getAttribute('data-ss-help')?.split('\n')[0]!==full||owner.getAttribute('tabindex')!=='0')failures.push('clipped:'+node.textContent);
        }
        const received=card.querySelector('.ss-battle-measure[data-ss-metric="xp_received"]');
        const addedMetricHeight=received?(received.getBoundingClientRect().height+parseFloat(getComputedStyle(received).marginTop))/scale:0;
        const baseCredits=card.querySelector('.ss-credit-income-column .ss-money-value[data-ss-credit-row="base"]'),
          receivedCredits=card.querySelector('.ss-credit-income-column .ss-money-value[data-ss-credit-row="received"]');
        const addedBaseCreditHeight=baseCredits.getBoundingClientRect().height/scale,
          receivedCreditWrapHeight=Math.max(0,receivedCredits.getBoundingClientRect().height/scale-30);
        const finance=card.querySelector('.ss-economy'),creditPair=finance.querySelector('.ss-credit-pair');
        const expectedAmounts=['123456','987654','-765432','-641976','+222222'];
        const metrics=['credits_income_base','credits_income_received','credits_costs','credits_net_base','credits_net_received'];
        for(const [index,metric]of metrics.entries()){
          const cell=creditPair.querySelector('[data-ss-metric="'+metric+'"]'),value=cell.querySelector('.ss-cell-value'),range=document.createRange();range.selectNodeContents(value);
          const box=cell.getBoundingClientRect(),ink=range.getBoundingClientRect(),css=getComputedStyle(cell);
          if(value.textContent.replace(/\s/g,'')!==expectedAmounts[index]||ink.left<box.left-scale||ink.right>box.right+scale||
            ink.top<box.top-scale||ink.bottom>box.bottom+scale||parseFloat(css.fontSize)/scale<13)failures.push('complete-six-digit-amount:'+metric);
        }
        if(width===500&&['en','pl'].includes(language)){
          const performance=card.querySelector('.ss-battle-performance');
          if(performance.getBoundingClientRect().width/scale>160||finance.getBoundingClientRect().width/scale<320||card.getBoundingClientRect().height/scale>190)failures.push('compact-card');
          for(const label of creditPair.querySelectorAll('.ss-credit-label-text')){
            const range=document.createRange();range.selectNodeContents(label);const ink=[...range.getClientRects()].filter(box=>box.width>0);
            if(ink.length!==1||ink[0].height>20*scale)failures.push('single-line-credit-caption:'+label.textContent);
          }
          if(addedBaseCreditHeight>30||receivedCredits.getBoundingClientRect().height/scale>30)failures.push('compact-credit-row-height');
        }
        for(const row of card.querySelectorAll('.ss-money-row:not(.ss-credit-pair),.ss-credit-income-column > .ss-money-value')){
          const inlineCaptionHeight=row.querySelector('.ss-credit-inline-label')?.getBoundingClientRect().height||0;
          if((row.getBoundingClientRect().height-inlineCaptionHeight)/scale>(row===baseCredits||row===receivedCredits?48:30))failures.push('row-height');
        }
        // Preserve the original 165px budget after the additional XP/Base
        // credit rows and the Received credit label's extra text line.
        if(!received||card.querySelectorAll('.ss-battle-measure').length!==3||
          Math.abs(card.getBoundingClientRect().width/scale-width)>1||origin.height/scale>64||
          card.getBoundingClientRect().height/scale-addedMetricHeight-addedBaseCreditHeight-receivedCreditWrapHeight>165)failures.push('dimensions');
        return {positions,headerHeight:origin.height/scale,cardHeight:card.getBoundingClientRect().height/scale,addedMetricHeight,addedBaseCreditHeight,receivedCreditWrapHeight,failures};
      });
      for(const [index,row] of rows.entries())for(const [key,box] of Object.entries(row.positions)){
        const reference=rows.find(other=>other.positions[key]).positions[key];
        const axes=['mapArt','resultArt'].includes(key)?['left','right']:['left','right','top','bottom'];
        if(axes.some(axis=>Math.abs(box[axis]-reference[axis])>1))row.failures.push('column-drift:'+key+':'+index);
      }
      return {passed:rows.length===4&&rows.every(row=>!row.failures.length),rows};
    },{scale,width,language,expectedOutcomes});
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
  // Stacking can free enough space for a caption column at 400px. At 320px
  // captions move above the values. The numeric columns stay aligned in both
  // modes and after the tables return to side by side at 550px.
  for(const scale of [1,2]){
    await page.evaluate(({scale,messages})=>{
      const payload=JSON.parse(JSON.stringify(__headerAlignmentFixture)),scope=payload.scopes.launch,item=scope.battles[0];
      payload.account_key='synthetic-battle-width-transition-'+scale;payload.window_size=[1200,1050];
      payload.appearance={window_settings:{maximized:false,background_transparency:0,restored_width:1200,restored_height:1050}};
      payload.localization={language:'pl',messages};
      Object.assign(item.stats,{battles:1,observed_battles:1,wn8:12345,wn8_count:1,
        xp_base:{count:1,sum:123456},xp_received:{count:1,sum:234567},
        currencies:{credits:{income_base:12345678,income_base_count:1,income:24691356,income_count:1,costs:12345678,costs_count:1,
          net_base:0,net_base_count:1,net:12345678,net_count:1},bonds:{income:50,costs:0,net:50}}});
      item.id='synthetic-battle-width-transition';scope.battles=[item];scope.pagination.battles={page:0,pages:1,total:1,page_size:40};
      window.__narrowBattleFixture=payload;window.__narrowBattleCard=null;
    },{scale,messages:languages.pl});
    for(const width of [320,400,550]){
      await page.setViewportSize({width:(width+20)*scale,height:2600});
      await page.evaluate(({width,scale})=>{
        const payload=JSON.parse(JSON.stringify(__narrowBattleFixture));payload.viewport={width:(width+20)*scale,height:2600,scale};
        model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);document.getElementById('ss-group-battles').onclick();
      },{width,scale});await frames(page);
      const result=await page.locator('#ss-groups .ss-group').evaluate((card,{width,scale})=>{
        const failures=[],economy=card.querySelector('.ss-economy'),pair=economy.querySelector('.ss-credit-pair');
        const heads=[...economy.querySelectorAll('.ss-money-head > .ss-money-value')].map(node=>node.getBoundingClientRect());
        const aligned=cells=>cells.length===3&&cells.every((cell,index)=>{const box=cell.getBoundingClientRect();
          return Math.abs(box.left-heads[index].left)<=scale&&Math.abs(box.right-heads[index].right)<=scale;});
        const bonds=[...economy.querySelectorAll('.ss-money-row:not(.ss-credit-pair) > .ss-money-value')];
        if(heads.length!==3||!aligned(bonds))failures.push('bonds-header-columns');
        for(const basis of ['base','received'])if(!aligned(['credits_income_'+basis,'credits_costs','credits_net_'+basis].map(metric=>pair.querySelector('[data-ss-metric="'+metric+'"]'))))failures.push('credit-header-columns:'+basis);
        for(const value of card.querySelectorAll('.ss-money-row .ss-cell-value,.ss-battle-value')){
          const range=document.createRange();range.selectNodeContents(value);const ink=range.getBoundingClientRect(),box=value.getBoundingClientRect();
          const minimum=value.classList.contains('ss-battle-value')?18:13;
          if(ink.left<box.left-scale||ink.right>box.right+scale||ink.top<box.top-scale||ink.bottom>box.bottom+scale||parseFloat(getComputedStyle(value).fontSize)/scale<minimum)failures.push('complete-readable-number:'+value.textContent);
        }
        const compact=economy.classList.contains('ss-credit-compact');
        const stacked=card.querySelector('.ss-battle-details').classList.contains('ss-battle-tables-stacked');
        if(stacked!==(width<550))failures.push('table-layout');
        if(compact!==(width===320))failures.push('compact-mode');
        const label=pair.querySelector('.ss-credit-label-column'),inline=pair.querySelector('.ss-credit-inline-label');
        if((label.getBoundingClientRect().width>0)===compact||(inline.getBoundingClientRect().width>0)!==compact)failures.push('caption-mode');
        if(width!==320&&window.__narrowBattleCard!==card)failures.push('lost-card-identity');
        window.__narrowBattleCard=card;
        return {failures,compact,stacked,financeWidth:economy.getBoundingClientRect().width/scale,cardWidth:card.getBoundingClientRect().width/scale};
      },{width,scale});
      check('Narrow battle tables retain full numbers and matching columns through '+width+'px at '+scale+'x: '+JSON.stringify(result),result.failures.length===0);
    }
  }
  await page.close();
};
