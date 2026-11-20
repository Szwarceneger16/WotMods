/* Floating-window headers use logical widths, including retained feed cards. */
const fs=require('fs'),path=require('path');
const {spawnSync}=require('child_process');
const root=path.join(__dirname,'..');
const frames=(page,count=8)=>page.evaluate(count=>new Promise(resolve=>{
  function next(){if(--count)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);
}),count);
module.exports=async({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  // The game applies the generated Python stylesheet over the fallback.
  const compiled=spawnSync(process.env.GRZ_PYTHON3||'python3',['-c',
    "from grz_session_stats.appearance import build_presentation, default_config; print(build_presentation(default_config())['panel_css'])"],
    {cwd:root,encoding:'utf8',env:{...process.env,PYTHONPATH:path.join(root,'src')}});
  if(compiled.status!==0)throw Error('Unable to compile native appearance: '+compiled.stderr);
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:3840,height:2800},viewport:{width:3840,height:2800,scale}});
    try{
      await page.evaluate(()=>{window.__responsiveHeaderFixture=JSON.parse(model.payload);});
      let sequence=0;
      async function publish(language,width,{paged=false,fresh=false,largeFinance=false,richVehicle=false,vehicleNames,selectedGroup='maps',sort}={}){
        await page.evaluate(({language,messages,width,scale,sequence,paged,fresh,largeFinance,richVehicle,vehicleNames,selectedGroup,sort,panelCSS})=>{
          const payload=JSON.parse(JSON.stringify(__responsiveHeaderFixture)),scope=payload.scopes.launch;
          payload.account_key='synthetic-responsive-header-'+scale+'-'+language;payload.window_size=[width,1100];
          payload.viewport={width:width<625?width*scale+20:3840,height:2800,scale};payload.localization={language,messages};
          payload.appearance={panel_css:panelCSS,window_settings:{maximized:false,background_transparency:15,restored_width:width,restored_height:1100}};
          scope.period_id='responsive-header-period';scope.data_revision='header-'+sequence;
          for(const group of ['maps','vehicles','tiers','battles']){
            const sample=scope[group][0];scope[group]=[0,1].map(index=>{
              const item=JSON.parse(JSON.stringify(sample)),stats=item.stats,total=index?8:7;
              item.id=(fresh?'fresh-':'')+'responsive-'+group+'-'+index;item.name=group==='maps'?(index?'Klondike':'Cliff'):'Synthetic vehicle '+index;
              if(group==='vehicles'&&vehicleNames)item.name=vehicleNames[index];
              if(group==='maps')item.visual={kind:'map',src:'img://gui/maps/icons/map/small/synthetic-header.png',alt:'Synthetic map'};
              if(group==='vehicles'||group==='battles')item.visual={kind:'vehicle',src:'img://gui/maps/icons/vehicle/contour/synthetic-header.png',alt:'Synthetic vehicle'};
              if(group==='battles')item.map_visual={kind:'map',src:'img://gui/maps/icons/map/small/synthetic-header.png',alt:'Synthetic map'};
              Object.assign(stats,{battles:total,observed_battles:total,wn8:index?1676:1601,wn8_count:total,win_rate:42.9});
              const vehicle=richVehicle&&group==='vehicles';
              if(vehicle){
                item.tier=9;
                item.vehicle_meta={class:'mediumTank',elite:true,class_icon:{kind:'vehicle_class',src:'img://gui/maps/icons/vehicleTypes/24x24_metal/mediumTank_elite.png'},
                  role:{key:'role_MT_universal',icon:{kind:'vehicle_role',src:'img://gui/maps/icons/roleExp/roles/24x24/role_MT_universal.png'}}};
                Object.assign(stats,{battles:2,observed_battles:3,wn8_count:2});
              }
              const values={xp_base:[132,549,1403],xp_received:[426,2372,8737],battle_wn8:[245,2288,6779],credits_net_base:[1000,index?5481:6343,9444]};
              if(largeFinance)values.credits_income_received=[123456789,234567890,345678901];
              if(vehicle)values.credits_net_received=[77465,96055,116055];
              item.extrema_battles={};
              for(const [metric,[min,avg,max]]of Object.entries(values)){
                stats[metric]={count:metric==='credits_net_base'?3:total,min,avg,max,sum:avg*total};item.extrema_battles[metric]={};
                for(const statistic of ['min','max'])item.extrema_battles[metric][statistic]={id:'responsive-result-'+index,metric,statistic,
                  value:stats[metric][statistic],name:'Synthetic vehicle',map:'Cliff',started_at:1794000000};
              }
              stats.free_xp={count:total,min:10,avg:100,max:200,sum:vehicle?1252:index?3228:929};
              stats.currencies={credits:{income_base:null,income_base_count:3,net_base:null,net_base_count:3,
                income:445295,income_count:total,costs:375711,costs_count:total,net:69584,net_count:total},
                bonds:{income:65,income_count:total,costs:0,costs_count:total,net:65,net_count:total}};
              item.battle_list={page:0,pages:1,total:1,page_size:10,items:[{id:'responsive-result-'+index,name:'Synthetic vehicle',map:'Cliff',started_at:1794000000,outcome:'win',wn8:1601}]};
              return item;
            });
            scope.ordering[group]={metric:group==='battles'?'off':richVehicle&&group==='vehicles'?'credits_net_received':largeFinance?'credits_income_received':'credits_net_base',statistic:'avg',direction:'desc',chronology:'newest'};
            if(sort&&group===selectedGroup)Object.assign(scope.ordering[group],sort);
            scope.pagination[group]={page:0,pages:paged&&group==='maps'?2:1,total:paged&&group==='maps'?4:2,page_size:2};
          }
          payload.scopes.timeline=JSON.parse(JSON.stringify(scope));
          payload.scopes.timeline.from_point=payload.scopes.timeline.to_point='';payload.scopes.timeline.time_points=[];
          model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
          document.getElementById('ss-scope-manual').click();document.getElementById('ss-group-'+selectedGroup).click();
        },{language,messages:languages[language],width,scale,sequence:++sequence,paged,fresh,largeFinance,richVehicle,vehicleNames,selectedGroup,sort,panelCSS:compiled.stdout.trim()});
        await frames(page);
      }
      async function resize(width,height=1100){
        await page.evaluate(({width,height})=>{
          const grip=document.getElementById('ss-resize-grip'),box=grip.getBoundingClientRect();
          grip.dispatchEvent(new MouseEvent('mousedown',{button:0,clientX:box.left+1,clientY:box.top+1,bubbles:true,cancelable:true}));
          const request=__grzCommands.filter(command=>command.action==='resize_begin').pop();
          if(!request)throw Error('Expected an owned native resize gesture');
          GRZSessionStats.update({resize_gesture:{token:request.token,width,height,active:true}});
          GRZSessionStats.update({resize_gesture:{token:request.token,width,height,active:false}});
        },{width,height});await frames(page,10);
      }
      async function audit(){return page.evaluate(scale=>{
        const rect=node=>{const b=node.getBoundingClientRect();return {left:b.left/scale,right:b.right/scale,top:b.top/scale,bottom:b.bottom/scale,width:b.width/scale,height:b.height/scale};},
          inside=(a,b)=>a.left>=b.left-1&&a.right<=b.right+1&&a.top>=b.top-1&&a.bottom<=b.bottom+1,
          overlapY=(a,b)=>Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1,
          overlap=(a,b)=>Math.min(a.right,b.right)-Math.max(a.left,b.left)>1&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1,
          ink=node=>{const range=document.createRange();range.selectNodeContents(node);return [...range.getClientRects()].filter(b=>b.width>0&&b.height>0)
            .map(b=>({left:b.left/scale,right:b.right/scale,top:b.top/scale,bottom:b.bottom/scale}));};
        const panel=rect(document.getElementById('grz-session-stats')),titlebar=rect(document.getElementById('ss-titlebar')),timeline=rect(document.getElementById('ss-timeline')),
          controls=['#ss-time-point-controls','.ss-background-control','.ss-language-row'].map(selector=>rect(document.querySelector(selector))),
          language=rect(document.querySelector('#ss-language .ss-select-trigger')),actions=rect(document.getElementById('ss-title-actions')),
          compactTitle=panel.width>=550&&panel.width<700,stackedTitle=compactTitle&&panel.width<594,
          rowsOK=!compactTitle||(Math.abs(actions.height-(stackedTitle?60:30))<=0.5&&
            (stackedTitle||Math.max(...controls.map(box=>box.top))-Math.min(...controls.map(box=>box.top))<=0.5)&&
            rect(document.getElementById('ss-time-point-name')).width>=119.5),
          topOK=controls.every(box=>inside(box,titlebar)&&!overlap(box,timeline))&&controls.every((box,index)=>controls.slice(index+1).every(other=>!overlap(box,other)))&&
            language.width>=85&&language.height>=28&&inside(language,titlebar)&&rowsOK;
        const two=document.getElementById('ss-groups').classList.contains('ss-two-columns'),cards=[...document.querySelectorAll('#ss-groups .ss-group')].map(card=>{
          const bounds=rect(card),header=rect(card.querySelector('.ss-group-header')),name=card.querySelector('.ss-group-name'),identity=rect(name),
            title=card.querySelector('.ss-group-title'),titleBox=rect(title),titleInk=ink(title),stats=card.querySelector('.ss-group-stats'),more=card.querySelector('.ss-more-button'),
            button=more&&rect(more),expectedDock=!two&&bounds.width<680,docked=card.classList.contains('ss-card-border-more'),failures=[];
          const titleFits=titleInk.every(part=>inside(part,titleBox)),titleStyle=getComputedStyle(title),
            titleEllipsis=titleBox.width>20&&title.classList.contains('ss-caption-ellipsis')&&titleStyle.textOverflow==='ellipsis'&&titleStyle.overflowX==='hidden'&&titleStyle.whiteSpace==='nowrap'&&
              title.getAttribute('data-ss-help')===title.textContent&&title.getAttribute('tabindex')==='0';
          if(identity.width<72||!titleInk.length||(!titleFits&&!titleEllipsis))failures.push('squeezed-identity');
          if(['Cliff','Klondike'].includes(title.textContent)&&titleInk.some(part=>Math.abs(part.top-titleInk[0].top)>1))failures.push('vertical-short-name');
          const image=card.querySelector('.ss-group-header .ss-group-thumb'),xp=card.querySelector('.ss-group-header .ss-free-xp');
          const imageBox=image&&rect(image),xpBox=xp&&rect(xp);
          if(!inside(header,bounds)||!inside(identity,header)||[imageBox,xpBox].filter(Boolean).some(box=>!inside(box,header)||
              box.top<bounds.top+2||box.width<=0||box.height<=0))failures.push('identity-outside-header');
          const headingExtras=[...name.querySelectorAll('.ss-group-heading > .ss-group-coverage,.ss-group-heading > .ss-info-button')],
            metadata=name.querySelector('.ss-vehicle-meta'),twoIdentityRows=headingExtras.length===2&&headingExtras.every(node=>overlapY(rect(node),titleBox))&&
              !!metadata&&!!xpBox&&overlapY(rect(metadata),xpBox)&&ink(xp.querySelector('strong')).every(part=>inside(part,xpBox));
          let sortNumber=null,sortWidth=null,sortCaptionFits=null,inline=null,rating=null,activeHeadline=null;
          if(stats){
            const statsBox=rect(stats),kpis=[...stats.querySelectorAll('.ss-group-kpi')].map(rect);
            const identityBox=rect(card.querySelector('.ss-group-identity'));
            inline=identityBox.right<=statsBox.left+1&&overlapY(identityBox,statsBox);
            if(!inline&&identityBox.bottom>statsBox.top+1)failures.push('identity-statistics-overlap');
            if(kpis.length!==3||kpis.some(box=>!inside(box,statsBox))||!inside(statsBox,header)||
              kpis.slice(1).some((box,index)=>box.left<kpis[index].right-1||!overlapY(box,kpis[index])))failures.push('statistics-stacked-or-outside');
            const wn8Kpi=stats.querySelector('.ss-group-wn8-kpi'),activeKpi=stats.querySelector('.ss-group-kpi[data-ss-sort-active]');
            if(activeKpi)activeHeadline=activeKpi.getAttribute('data-ss-sort-active');
            if(wn8Kpi){
              const wn8=wn8Kpi.querySelector('.ss-kpi-label');
              const labelBox=rect(wn8),labelInk=ink(wn8);
              rating={kind:wn8Kpi.getAttribute('data-wn8-kind'),width:rect(wn8Kpi).width,text:wn8.textContent,
                visible:wn8.scrollWidth<=wn8.clientWidth+1&&labelInk.length>0&&
                labelInk.every(part=>inside(part,labelBox)&&Math.abs(part.top-labelInk[0].top)<=1)};
            }
            const badge=stats.querySelector('.ss-group-sort-value');
            if(badge){
              const badgeBox=rect(badge),caption=badge.querySelector('.ss-group-sort-caption-text'),value=badge.querySelector('.ss-group-sort-number');
              const captionBox=rect(caption),captionStyle=getComputedStyle(caption),captionInk=ink(caption);
              sortNumber=value.textContent.replace(/\s/g,'');
              sortWidth=badgeBox.width;
              sortCaptionFits=caption.scrollWidth<=caption.clientWidth+1;
              const fullHelp=badge.getAttribute('data-ss-help');
              const readableCaption=captionInk.length>0&&captionInk.every(part=>Math.abs(part.top-captionInk[0].top)<=1)&&(captionInk.every(part=>inside(part,captionBox))||
                captionStyle.whiteSpace==='nowrap'&&captionStyle.textOverflow==='ellipsis'&&captionStyle.overflowX==='hidden'&&caption.scrollWidth>caption.clientWidth&&
                fullHelp&&fullHelp===badge.getAttribute('aria-label')&&badge.getAttribute('aria-controls')==='ss-help-tooltip');
              if(!inside(badgeBox,statsBox)||kpis.some(box=>overlap(box,badgeBox))||!inside(captionBox,badgeBox)||
                !readableCaption||ink(value).length!==1||ink(value).some(part=>!inside(part,badgeBox)))failures.push('clipped-statistic-badge');
            }
          }
          if(more){
            if(docked!==expectedDock)failures.push('dock-scope');
            if(button.width<=0||button.height<=0||button.left<bounds.left-1||button.right>bounds.right+1)failures.push('action-outside-card');
            if(expectedDock){
              if(more.parentNode!==card||getComputedStyle(more).position!=='absolute'||Math.abs(button.width-82)>0.5||Math.abs(button.height-20)>0.5||
                Math.abs((button.top+button.bottom)/2-bounds.top)>2||Math.abs(bounds.right-button.right-6)>2||header.top<button.bottom+2)failures.push('border-dock');
            }else if(!card.querySelector('.ss-group-header').contains(more)||getComputedStyle(more).position==='absolute'||!inside(button,header))failures.push('ordinary-action-moved');
            if(!ink(more.querySelector('.ss-control-label')).every(part=>inside(part,button)))failures.push('clipped-action');
          }
          const banner=card.querySelector('.ss-battle-selection-banner'),back=card.querySelector('.ss-battle-return'),label=card.querySelector('.ss-battle-selection-label');
          let selected=null;
          if(banner&&back&&label){const b=rect(banner),a=rect(back),l=rect(label);
            const labelInk=ink(label);
            selected={text:label.textContent,backLabel:back.getAttribute('aria-label'),contained:inside(a,b)&&inside(l,b)&&
              b.left>=bounds.left-1&&b.right<=bounds.right+1&&label.scrollWidth<=label.clientWidth+1&&labelInk.length>0&&
              labelInk.every(part=>inside(part,l)&&Math.abs(part.top-labelInk[0].top)<=1),
              order:docked?l.right<=a.left+1:a.right<=l.left+1,
              adjacent:!docked||(button.left-a.right>=2&&button.left-a.right<=24&&Math.abs((a.top+a.bottom-button.top-button.bottom)/2)<=2&&!overlap(b,button))};
            if(docked){
              const visuals=[...card.querySelectorAll('.ss-battle-outcome,.ss-battle-map-visual')].map(rect);
              if(visuals.length!==2||visuals.some(visual=>[b,button].some(control=>overlap(control,visual))))failures.push('selection-overlaps-battle-header');
            }
          }
          return {id:card.getAttribute('data-group-id'),title:title.textContent,titleFits,titleEllipsis,twoIdentityRows,bounds,header,identity,button,expectedDock,docked,failures,selected,sortNumber,sortWidth,sortCaptionFits,inline,rating,activeHeadline,imageBox,xpBox,
            more:more&&more.textContent,expanded:more&&more.getAttribute('aria-expanded')};
        });
        return {panel,titlebar,timeline,controls,language,actions,rowsOK,topOK,two,cards};
      },scale);}
      const valid=result=>result.topOK&&result.cards.length>=2&&result.cards.every(card=>!card.failures.length),
        selectedValid=(result,messages)=>valid(result)&&result.cards.some(card=>card.selected&&card.selected.contained&&card.selected.order&&card.selected.adjacent&&
          card.selected.text===messages['battle.selected']&&card.selected.backLabel===messages['battle.return']);
      for(const [language,messages]of Object.entries(languages)){
        for(const width of [625,780]){
          await publish(language,width);const result=await audit();
          check('Language controls stay enclosed above Timeline and both short map identities remain readable '+language+'/'+width+'/'+scale+'x: '+JSON.stringify(result),valid(result));
          const more=page.locator('#ss-groups .ss-more-button').first();await more.evaluate(node=>{window.__headerMore=node;window.__headerMoreParent=node.parentNode;});
          await more.click();await frames(page);const open=await audit();
          check('Localized More/Less preserves its node, parent and scoped border position '+language+'/'+width+'/'+scale+'x: '+JSON.stringify(open),valid(open)&&
            open.cards[0].more===messages['more.less']&&open.cards[0].expanded==='true'&&await more.evaluate(node=>node===__headerMore&&node.parentNode===__headerMoreParent));
          await more.click();await frames(page);
        }
        await page.locator('#ss-groups .ss-metric-battle-link[data-ss-source-metric="xp_received"][data-ss-extreme="max"]').first().click();
        await page.evaluate(()=>{
          const request=__grzCommands.filter(command=>command.action==='battle_select').pop(),payload=JSON.parse(model.payload),scope=payload.scopes[request.scope],sample=scope.battles[0];
          scope.battles=[{...sample,id:request.id},{...sample,id:'responsive-neighbor'}];scope.pagination.battles={page:0,pages:1,total:2,page_size:2};
          scope.battle_focus={id:request.id,request_id:request.request_id};model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
        });await frames(page,12);
        await page.evaluate(()=>{window.__selectedHeaderCard=document.querySelector('#ss-groups .ss-battle-target');window.__selectedHeaderMore=__selectedHeaderCard.querySelector('.ss-more-button');});
        for(const width of [625,780,1320]){
          await resize(width);const result=await audit();
          check('Back remains beside Selected while only narrow single-column More uses the border '+language+'/'+width+'/'+scale+'x: '+JSON.stringify(result),selectedValid(result,messages)&&
            await page.evaluate(()=>document.querySelector('#ss-groups .ss-battle-target')===__selectedHeaderCard&&__selectedHeaderCard.querySelector('.ss-more-button')===__selectedHeaderMore));
          if(width===625){
            const more=page.locator('#ss-groups .ss-battle-target .ss-more-button');await more.click();await frames(page);const open=await audit();
            check('Selected, Back and localized Less coexist without moving their shared border controls '+language+'/'+scale+'x: '+JSON.stringify(open),
              selectedValid(open,messages)&&open.cards.some(card=>card.selected&&card.expanded==='true'&&card.more===messages['more.less']));
            await more.click();await frames(page);
            if(language==='en'){
              const before=await audit();await resize(625,900);const shorter=await audit();
              check('A height-only resize preserves the selected card and border actions at '+scale+'x: '+JSON.stringify(shorter),selectedValid(shorter,messages)&&
                await page.evaluate(()=>document.querySelector('#ss-groups .ss-battle-target')===__selectedHeaderCard)&&
                shorter.cards.every((card,index)=>Math.abs(card.bounds.width-before.cards[index].bounds.width)<=0.25&&
                  Math.abs(card.bounds.height-before.cards[index].bounds.height)<=0.25&&
                  Math.abs((card.button.top-card.bounds.top)-(before.cards[index].button.top-before.cards[index].bounds.top))<=0.25));
              await resize(625);
            }
          }
        }
      }
      await publish('en',625);await page.evaluate(()=>{window.__retainedHeaderCards=[...document.querySelectorAll('#ss-groups .ss-group')];window.__retainedHeaderActions=__retainedHeaderCards.map(card=>card.querySelector('.ss-more-button'));});
      for(const width of [550,640,700,1320,1800,625]){
        await resize(width);const result=await audit();
        check('The same map headers recover correct rows and action scope through live resize at '+width+'/'+scale+'x: '+JSON.stringify(result),valid(result)&&
          await page.evaluate(()=>[...document.querySelectorAll('#ss-groups .ss-group')].every((card,index)=>card===__retainedHeaderCards[index]&&card.querySelector('.ss-more-button')===__retainedHeaderActions[index])));
        check('The normal viewport honors the 625px floor during resize at '+width+'/'+scale+'x',
          Math.abs(result.panel.width-Math.max(625,width))<=1);
      }
      for(const width of [360,480,625]){
        await publish('ru',width,{largeFinance:true,selectedGroup:'vehicles'});const result=await audit();
        const failures=result.cards.flatMap(card=>card.failures);
        check('Narrow aggregate headers contain all KPIs and a long localized finance statistic at '+width+'/'+scale+'x: '+JSON.stringify(failures),
          Math.abs(result.panel.width-width)<=1&&result.cards.length===2&&failures.length===0&&
          result.cards.every(card=>card.sortNumber==='234567890'&&card.sortWidth<=132&&card.imageBox&&card.xpBox&&card.inline===(width===625)));
        if(width===625){
          await page.evaluate(()=>{
            const payload=JSON.parse(model.payload);
            for(const scope of ['launch','timeline'])payload.scopes[scope].ordering.vehicles.metric='off';
            model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
          });await frames(page);
          const unsorted=await audit();
          check('A long localized finance caption keeps the identity and statistics on the same row at the normal minimum '+scale+'x: '+JSON.stringify(result.cards),
            valid(unsorted)&&unsorted.cards.every((card,index)=>card.inline&&card.sortNumber===null&&
              Math.abs(card.header.height-result.cards[index].header.height)<=1));
        }
      }
      await publish('en',1300,{largeFinance:true,vehicleNames:['Pz. 55','CAV 71'],selectedGroup:'vehicles'});
      const sortedTwoLane=await audit();
      await page.evaluate(()=>{
        const payload=JSON.parse(model.payload);
        for(const scope of ['launch','timeline'])payload.scopes[scope].ordering.vehicles.metric='off';
        model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
      });await frames(page);
      const unsortedTwoLane=await audit();
      check('An ordinary two-column card keeps a short vehicle identity level with the sort result at '+scale+'x: '+JSON.stringify(sortedTwoLane.cards),
        sortedTwoLane.two&&valid(sortedTwoLane)&&valid(unsortedTwoLane)&&sortedTwoLane.cards.every((card,index)=>
          card.inline&&card.sortNumber==='234567890'&&card.rating.width===72&&unsortedTwoLane.cards[index].rating.width===104&&
          Math.abs(card.header.height-unsortedTwoLane.cards[index].header.height)<=1));
      for(const group of ['vehicles','maps','tiers']){
        const shortMetrics=['win_rate','off','xp_received','battle_wn8'];
        if(group!=='tiers')shortMetrics.push('battles');
        for(const metric of shortMetrics){
          await publish('en',1300,{richVehicle:true,vehicleNames:['Pz. 55','CAV 71'],selectedGroup:group,sort:{metric}});
          const result=await audit();
          const kind=metric==='battle_wn8'?'avg':'combined';
          const active=['win_rate','battles','battle_wn8'].includes(metric)?metric:null;
          check('Ordinary two-column cards use the spare header width for WN8 '+group+'/'+metric+'/'+scale+'x',
            valid(result)&&result.two&&result.cards.every(card=>card.inline&&card.sortNumber===null&&card.activeHeadline===active&&
              card.rating.kind===kind&&card.rating.visible&&card.rating.width===104));
        }
      }
      await publish('pl',1300,{richVehicle:true,vehicleNames:['Zaćmienie','Bardzo długa nazwa pojazdu testowego'],selectedGroup:'vehicles'});
      const ordinary=await audit();
      check('Ordinary wide vehicle cards fit the name and metadata beside the thumbnail in two rows at '+scale+'x: '+JSON.stringify(ordinary.cards),
        valid(ordinary)&&ordinary.two&&ordinary.cards.every(card=>card.twoIdentityRows&&card.sortWidth<=100)&&
        ordinary.cards[0].titleFits&&!ordinary.cards[1].titleFits&&ordinary.cards[1].titleEllipsis);
      await resize(1800);const ultra=await audit();
      check('Ultra-wide vehicle cards show the full Polish sort caption beside the same number at '+scale+'x: '+JSON.stringify(ultra.cards),
        valid(ultra)&&ultra.two&&ultra.cards.every((card,index)=>card.bounds.width>=700&&card.inline&&card.sortWidth>=160&&
          card.sortCaptionFits&&card.twoIdentityRows&&card.sortNumber===ordinary.cards[index].sortNumber));
      await resize(1300);const returned=await audit();
      check('Resizing back restores the ordinary header widths and two identity rows at '+scale+'x: '+JSON.stringify(returned.cards),
        valid(returned)&&returned.cards.every((card,index)=>card.twoIdentityRows&&Math.abs(card.sortWidth-ordinary.cards[index].sortWidth)<=1));
      for(const language of ['en','es']){
        await publish(language,1800,{selectedGroup:'vehicles'});const result=await audit();
        check('Wide vehicle cards show the full localized Combined WN8 caption at '+language+'/'+scale+'x: '+JSON.stringify(result.cards),
          valid(result)&&result.two&&result.cards.every(card=>card.bounds.width>=700&&card.inline&&card.imageBox&&
            card.rating&&card.rating.kind==='combined'&&card.rating.visible&&card.rating.text===languages[language]['metric.combined_wn8']));
      }
      await publish('en',625,{paged:true});await page.evaluate(()=>{window.__firstHeaderFeedCard=document.querySelector('#ss-groups .ss-group');});
      await page.locator('#ss-page-next').click();await frames(page);
      await page.evaluate(()=>{
        const request=__grzCommands.filter(command=>command.action==='page'&&command.group==='maps').pop(),payload=JSON.parse(model.payload),scope=payload.scopes.timeline;
        scope.maps=scope.maps.map((item,index)=>({...item,id:'appended-responsive-'+index,name:index?'Klondike':'Cliff'}));
        scope.pagination.maps={page:1,pages:2,total:4,page_size:2,request_id:request.request_id};model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
      });await frames(page,12);const appended=await audit();
      check('First cards in both infinite-feed pages retain full identities and docked actions at '+scale+'x: '+JSON.stringify(appended),valid(appended)&&appended.cards.length===4&&
        await page.evaluate(()=>document.querySelector('#ss-groups .ss-group')===__firstHeaderFeedCard));
      await publish('en',625,{fresh:true});const fresh=await audit();
      check('A new snapshot lays out the first Cliff header correctly at '+scale+'x: '+JSON.stringify(fresh),valid(fresh)&&fresh.cards[0].id==='fresh-responsive-maps-0');
      const squeezed=await page.addStyleTag({content:'#ss-groups .ss-group:first-child .ss-group-name { flex:0 0 8rem !important; width:8rem !important; }'});
      check('The first-card guard rejects a letter-wide map identity at '+scale+'x',!valid(await audit()));
      await squeezed.evaluate(node=>node.remove());await frames(page);
      check('Removing the squeezed identity restores the complete first map name at '+scale+'x',valid(await audit()));
      const droppedLanguage=await page.addStyleTag({content:'.ss-language-row { transform:translateY(30rem) !important; }'});
      check('The title-control guard rejects Language dropping toward Timeline at '+scale+'x',!valid(await audit()));
      await droppedLanguage.evaluate(node=>node.remove());await frames(page);
      check('Restoring Language recovers the enclosed one-row controls at '+scale+'x',valid(await audit()));
    }finally{await page.close();}
  }
};
