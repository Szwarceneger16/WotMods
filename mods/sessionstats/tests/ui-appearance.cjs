/* Actual Python configuration -> model -> shipped JS/CSS. Native WoT APIs are doubles. */
const {chromium} = require('playwright');
const {spawnSync} = require('child_process');
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const root = path.resolve(__dirname, '..');
const fixtures = JSON.parse(fs.readFileSync(path.join(root, 'preview/demo_snapshot.json'), 'utf8'));
const checks = [], errors = [];
const check = (name, pass) => { assert(pass, name); checks.push(name); };
const python = spawnSync(process.env.GRZ_PYTHON3 || 'python3', ['-c', `
import json
from grz_session_stats.appearance import default_config, build_presentation
c = default_config()
default = build_presentation(c)
c['colors'].update(window_border='#123456', window_background='rgba(17,34,51,0.65)',
    table_row_background='#223344', table_row_following_border_top='#abcdef',
    metric_value_text='#decafe', garage_bars_background='#456789', garage_wn8_text='#fedcba',
    garage_spinner_border='rgba(100,120,140,0.4)', garage_spinner_border_top_color='#aabbcc')
c['radii'].update(window=11, table_row=7, garage_spinner=3)
c['opacity'].update(window=0.8, garage_button=0.7)
c['scroll']['speed_multiplier'] = 2
print(json.dumps({'defaults':default, 'custom':build_presentation(c)}))
`], {cwd:root, encoding:'utf8', env:{...process.env,PYTHONPATH:path.join(root,'src')}});
if (python.status !== 0) throw new Error('Configuration compilation failed: '+python.stderr);
const presentation = JSON.parse(python.stdout);

function snapshot() {
    const data = JSON.parse(JSON.stringify(fixtures.normal));
    data.viewport = {width:1440,height:950,scale:1};
    delete data.appearance;
    for (const scope of Object.values(data.scopes)) {
        const first = scope.battles[0];
        scope.battles = Array.from({length:95}, (_,i)=>({...first,id:'appearance-'+i,started_at:1700000000-i}));
    }
    return data;
}

async function panel(browser) {
    const page = await browser.newPage({viewport:{width:1440,height:950}});
    page.on('pageerror', error=>errors.push(error.message));
    await page.addInitScript(data=>{
        window.testSnapshot=data;
        window.testWarnings=[];
        window.console.warn=message=>testWarnings.push(message);
        window.testEvents={};
        window.isDomBuilt=true;
        window.model={payload:JSON.stringify(data),onAction:()=>{}};
        window.engine={whenReady:Promise.resolve(),on:(name,fn)=>{testEvents[name]=fn;},off:()=>{}};
        window.viewEnv={addDataChangedCallback:()=>1,removeDataChangedCallback:()=>{},resizeViewPx:()=>{}};
        window.pushAppearance=value=>{
            const data=JSON.parse(JSON.stringify(testSnapshot));
            if(value!==null)data.appearance=value;
            model.payload=JSON.stringify(data);
            testEvents['viewEnv.onDataChanged']();
        };
    },snapshot());
    await page.route('http://grz-appearance.test/**',async route=>{
        const name=new URL(route.request().url()).pathname.slice(1);
        if(!['SessionStats.html','session_stats.css','session_stats.js'].includes(name)){await route.abort();return;}
        await route.fulfill({status:200,contentType:name.endsWith('.js')?'text/javascript':name.endsWith('.css')?'text/css':'text/html',
            body:fs.readFileSync(path.join(root,'ui',name))});
    });
    await page.goto('http://grz-appearance.test/SessionStats.html');
    await page.waitForFunction(()=>window.GRZSessionStats && GRZSessionStats.getState().nativeBound);
    await frames(page);
    return page;
}

async function frames(page) {
    await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
}

async function sameRaster(page, before, after, reportDifference = true) {
    // Chromium may round a handful of shadow/antialiasing edge pixels differently
    // after repaint (hosted Chromium 151: 10 pixels, max channel delta 5/255).
    // Layout and computed paint are checked separately, exactly.
    const result = await page.evaluate(async buffers => {
        const decode = encoded => new Promise(resolve => {
            const img = new Image(); img.onload = () => resolve(img);
            img.src = 'data:image/png;base64,' + encoded;
        });
        const images = await Promise.all(buffers.map(decode));
        if (images[0].width !== images[1].width || images[0].height !== images[1].height) return {matches:false,reason:'dimensions'};
        const pixels = images.map(img => {
            const canvas = document.createElement('canvas');
            canvas.width = img.width; canvas.height = img.height;
            const context = canvas.getContext('2d'); context.drawImage(img, 0, 0);
            return context.getImageData(0, 0, canvas.width, canvas.height).data;
        });
        let changed = 0, maxDelta = 0;
        const bounds = [images[0].width, images[0].height, -1, -1];
        for (let i = 0; i < pixels[0].length; i += 4) {
            let delta = 0;
            for (let c = 0; c < 4; c++) delta = Math.max(delta, Math.abs(pixels[0][i+c] - pixels[1][i+c]));
            maxDelta = Math.max(maxDelta, delta);
            if (delta) {
                changed++;
                const x = (i / 4) % images[0].width, y = Math.floor((i / 4) / images[0].width);
                bounds[0] = Math.min(bounds[0], x); bounds[1] = Math.min(bounds[1], y);
                bounds[2] = Math.max(bounds[2], x); bounds[3] = Math.max(bounds[3], y);
            }
        }
        return {matches:changed<=16 && maxDelta<=6,changed,maxDelta,bounds};
    }, [before.toString('base64'), after.toString('base64')]);
    if (!result.matches && reportDifference) console.error('Panel raster comparison:', JSON.stringify(result));
    return result.matches;
}

async function paint(page, selector) {
    return page.locator(selector).evaluateAll(nodes=>nodes.flatMap(node=>[node,...node.querySelectorAll('*')]).map(node=>{
        const css=getComputedStyle(node), rect=node.getBoundingClientRect();
        const properties=['color','backgroundColor','backgroundImage','boxShadow','textShadow','opacity',
            'borderTopColor','borderRightColor','borderBottomColor','borderLeftColor',
            'borderTopWidth','borderRightWidth','borderBottomWidth','borderLeftWidth',
            'borderTopLeftRadius','borderTopRightRadius','borderBottomRightRadius','borderBottomLeftRadius',
            'paddingTop','paddingRight','paddingBottom','paddingLeft','fontSize','lineHeight','display'];
        return {tag:node.tagName,cls:node.className,box:[rect.x,rect.y,rect.width,rect.height],
            style:Object.fromEntries(properties.map(key=>[key,css[key]]))};
    }));
}

async function pushPanel(page,value){await page.evaluate(value=>pushAppearance(value),value);await frames(page);}

async function wheel(page, deltaY, speed, mode=0, extra={}) {
    await page.evaluate(({speed,defaults})=>pushAppearance({...defaults,scroll_speed:speed}),{speed,defaults:presentation.defaults});
    await page.locator('#ss-group-battles').click();
    return page.locator('#ss-scroll').evaluate((node,{deltaY,mode,extra})=>{
        node.scrollTop=800;
        const before=node.scrollTop;
        const event=new WheelEvent('wheel',{bubbles:true,cancelable:true,deltaY,deltaMode:mode,...extra});
        node.dispatchEvent(event);
        return {before,after:node.scrollTop,page:node.clientHeight,prevented:event.defaultPrevented};
    },{deltaY,mode,extra});
}

async function footer(browser) {
    const page=await browser.newPage({viewport:{width:640,height:120}});
    page.on('pageerror',error=>errors.push(error.message));
    await page.setContent('<html style="font-size:1px"><head><style>body{margin:0;background:#121413}.App_footer_test{display:flex;align-items:center;justify-content:flex-end;height:64px;padding:0 20px}.SessionStats_base_test{width:54px;color:#abcdef}#native-button{color:#123456}</style></head><body><div class="App_footer_test"><div class="SessionStats_base_test">19</div><button id="native-button">EU III</button></div></body></html>');
    await page.evaluate(()=>{
        window.testWarnings=[];
        window.console.warn=message=>testWarnings.push(message);
        window.testEvents={};
        window.testID=41;
        window.testModel={activity:'{"pending":0,"processing":false}',onAction:()=>{}};
        window.isDomBuilt=true;
        window.engine={whenReady:Promise.resolve(),on:(name,fn)=>{testEvents[name]=fn;},off:()=>{}};
        window.viewEnv={addDataChangedCallback:()=>1,removeDataChangedCallback:()=>{}};
        window.subViews={ids:()=>testID===null?[]:[testID],get:()=>({model:{grzSessionFooter:{value:testModel}}})};
        window.pushFooter=value=>{testModel.appearance=value;testEvents['viewEnv.onDataChanged']();};
    });
    await page.addStyleTag({path:path.join(root,'ui/footer.css')});
    await page.addScriptTag({path:path.join(root,'ui/footer.js')});
    await page.waitForSelector('#grz-session-stats-footer-button');
    return page;
}

(async()=>{
    const localChrome=path.resolve(root,'../.wot-design-tools/chrome-testing/chrome-headless-shell-linux64/chrome-headless-shell');
    // Grayscale text avoids RGB subpixel repaint artifacts when translated
    // glyphs touch a clipping edge. Keep the exact layout/paint and raster bounds.
    const browser=await chromium.launch({executablePath:process.env.GRZ_CHROME||localChrome,headless:true,args:['--no-sandbox','--disable-lcd-text']});
    try {
        const page=await panel(browser);
        const baseline=await paint(page,'#grz-session-stats');
        const baselineImage=await page.locator('#grz-session-stats').screenshot({animations:'disabled'});
        await pushPanel(page,presentation.defaults);
        check('The compiled default configuration preserves all panel paint and layout measurements',
            JSON.stringify(baseline)===JSON.stringify(await paint(page,'#grz-session-stats')));
        check('Default panel raster matches within 16 antialiasing pixels and 6 channel levels',
            await sameRaster(page, baselineImage, await page.locator('#grz-session-stats').screenshot({animations:'disabled'})));
        check('Exactly one owned panel style node is used',await page.locator('#grz-session-stats-appearance').count()===1);
        await page.evaluate(()=>{
            window.testMutations=0;
            window.testStyle=document.getElementById('grz-session-stats-appearance');
            window.testObserver=new MutationObserver(items=>{testMutations+=items.length;});
            testObserver.observe(testStyle,{childList:true,characterData:true,subtree:true});
        });
        await pushPanel(page,presentation.defaults);
        check('Identical model refreshes do not rewrite or duplicate panel CSS',
            await page.evaluate(()=>testMutations===0 && document.getElementById('grz-session-stats-appearance')===testStyle));
        await page.evaluate(()=>testObserver.disconnect());

        await pushPanel(page,presentation.custom);
        check('The raster comparison rejects a real configured appearance change',
            !await sameRaster(page, baselineImage, await page.locator('#grz-session-stats').screenshot({animations:'disabled'}), false));
        const changed=await page.evaluate(()=>{
            const read=selector=>getComputedStyle(document.querySelector(selector));
            const main=read('#grz-session-stats'),row=read('.ss-metric-row');
            const line=read('.ss-metric-row + .ss-metric-row');
            return {border:main.borderTopColor,background:main.backgroundColor,radius:main.borderTopLeftRadius,opacity:main.opacity,
                rowBackground:row.backgroundColor,rowRadius:row.borderTopLeftRadius,line:line.borderTopColor,
                text:read('.ss-metric-row .ss-metric-number').color,width:main.width,height:main.height};
        });
        check('Configured window border, translucent background and opacity reach the actual panel',
            changed.border==='rgb(18, 52, 86)' && changed.background==='rgba(17, 34, 51, 0.65)' && changed.opacity==='0.8');
        check('Configured table background, separators and numeric text are visible',
            changed.rowBackground==='rgb(34, 51, 68)' && changed.line==='rgb(171, 205, 239)' && changed.text==='rgb(222, 202, 254)');
        check('Configured corner radii preserve the existing panel dimensions',
            changed.radius==='11px' && changed.rowRadius==='7px' && changed.width==='700px' && changed.height==='620px');

        for(const speed of [0.5,1,2]){
            const down=await wheel(page,-120,speed),up=await wheel(page,120,speed);
            check('Native scroll multiplier '+speed+' scales both directions without changing their sign',
                Math.abs(down.after-down.before-down.page*speed/4)<=1 &&
                Math.abs(up.before-up.after-up.page*speed/4)<=1 && down.prevented && up.prevented);
        }
        const pageMode=await wheel(page,-1,2,2);
        check('The configured speed also scales native page-mode scrolling',pageMode.after-pageMode.before===pageMode.page*2 && pageMode.prevented);
        const horizontal=await wheel(page,-1,2,0,{deltaX:8});
        check('Configured speed leaves dominant horizontal gestures vertically inert',horizontal.after===horizontal.before && horizontal.prevented);
        const invalidSpeeds=[0,-1,9,'2',true,null];
        for(const value of invalidSpeeds){
            const result=await wheel(page,-1,value);
            assert(Math.abs(result.after-result.before-result.page/4)<=1);
        }
        check('Invalid optional bridge speed values fall back to the original wheel step',true);

        await page.locator('#ss-group-vehicles').click();
        await pushPanel(page,{...presentation.custom,panel_css:42});
        check('Malformed panel CSS restores static paint while statistics keep rendering',
            await page.locator('#grz-session-stats-appearance').count()===0 &&
            await page.locator('#grz-session-stats').evaluate(el=>getComputedStyle(el).borderTopColor==='rgb(100, 96, 68)') &&
            await page.locator('.ss-group').count()>0);
        await pushPanel(page,presentation.custom);
        await pushPanel(page,null);
        check('A missing appearance payload clears previous overrides and restores the exact default panel',
            await page.locator('#grz-session-stats-appearance').count()===0 &&
            JSON.stringify(baseline)===JSON.stringify(await paint(page,'#grz-session-stats')));
        await page.evaluate(()=>{
            window.realCreateElement=document.createElement;
            document.createElement=function(name){if(name==='style')throw new Error('injected cosmetic failure');return realCreateElement.apply(this,arguments);};
        });
        await pushPanel(page,presentation.custom);
        check('A native style-node failure does not block result rendering',await page.locator('.ss-group').count()>0 && await page.locator('#grz-session-stats-appearance').count()===0);
        await page.evaluate(()=>{document.createElement=realCreateElement;});
        await pushPanel(page,presentation.custom);
        check('A later valid refresh recovers the panel appearance after a DOM failure',await page.locator('#grz-session-stats-appearance').count()===1);
        await page.evaluate(()=>{GRZSessionStats.destroy();testEvents['viewEnv.onDataChanged']();});
        check('Panel cleanup removes its style and retained model events cannot reapply it',await page.locator('#grz-session-stats-appearance').count()===0);
        await page.close();

        const foot=await footer(browser);
        const footBaseline=await paint(foot,'#grz-session-stats-footer-button');
        const footBaselineImage=await foot.locator('#grz-session-stats-footer-button').screenshot({animations:'disabled'});
        await foot.evaluate(value=>pushFooter(value),presentation.defaults.footer_css);
        check('The compiled default configuration preserves all footer icon paint and geometry',
            JSON.stringify(footBaseline)===JSON.stringify(await paint(foot,'#grz-session-stats-footer-button')));
        check('The complete default footer icon screenshot is pixel-identical to its static fallback',
            footBaselineImage.equals(await foot.locator('#grz-session-stats-footer-button').screenshot({animations:'disabled'})));
        await foot.evaluate(()=>{
            window.testMutations=0;
            window.testStyle=document.getElementById('grz-session-footer-appearance');
            window.testObserver=new MutationObserver(items=>{testMutations+=items.length;});
            testObserver.observe(testStyle,{childList:true,characterData:true,subtree:true});
        });
        await foot.evaluate(value=>pushFooter(value),presentation.defaults.footer_css);
        await frames(foot);
        check('Identical footer refreshes do not rewrite or duplicate its stylesheet',
            await foot.evaluate(()=>testMutations===0 && document.querySelectorAll('#grz-session-footer-appearance').length===1 && document.getElementById('grz-session-footer-appearance')===testStyle));
        await foot.evaluate(()=>testObserver.disconnect());
        await foot.evaluate(value=>{testModel.activity='{"pending":2,"processing":false}';pushFooter({value});},presentation.custom.footer_css);
        const footerValues=await foot.evaluate(()=>{
            const read=selector=>getComputedStyle(document.querySelector(selector));
            const spinner=read('.grz-session-footer-spinner'),button=read('#grz-session-stats-footer-button');
            return {bar:read('.grz-session-footer-bar').backgroundColor,rating:read('.grz-session-footer-rating').color,
                spinner:spinner.borderTopColor,track:spinner.borderRightColor,radius:spinner.borderTopLeftRadius,
                animation:spinner.animationName,opacity:button.opacity,width:button.width,height:button.height,
                native:read('#native-button').color,counter:document.querySelector('.SessionStats_base_test').textContent};
        });
        check('Wrapped footer appearance customizes the bar glyph and WN8 text',footerValues.bar==='rgb(69, 103, 137)' && footerValues.rating==='rgb(254, 220, 186)');
        check('Configured spinner colour, track alpha and radius retain its pending animation',
            footerValues.spinner==='rgb(170, 187, 204)' && footerValues.track==='rgba(100, 120, 140, 0.4)' && footerValues.radius==='3px' && footerValues.animation==='grz-session-footer-spin');
        check('Footer opacity does not change button size or native footer controls',
            footerValues.opacity==='0.7' && footerValues.width==='44px' && footerValues.height==='36px' && footerValues.native==='rgb(18, 52, 86)' && footerValues.counter==='19');
        for(const bad of [42,{},'<style>body{color:red}</style>','x'.repeat(65537)]){
            await foot.evaluate(value=>pushFooter(value),bad);
            assert.strictEqual(await foot.locator('#grz-session-footer-appearance').count(),0);
            assert.strictEqual(await foot.locator('#grz-session-stats-footer-button').count(),1);
            assert.strictEqual(await foot.locator('.grz-session-footer-spinner').isVisible(),true);
        }
        check('Malformed footer appearance falls back independently of the button and pending state',true);
        await foot.evaluate(value=>pushFooter(value),presentation.custom.footer_css);
        await foot.evaluate(()=>{testID=null;testEvents['viewEnv.onDataChanged']();});
        check('Losing the native footer child removes the associated stylesheet',await foot.locator('#grz-session-footer-appearance').count()===0);
        await foot.evaluate(()=>{testID=52;testEvents['viewEnv.onDataChanged']();});
        check('A recreated footer child receives the current appearance with its pending state',
            await foot.locator('#grz-session-footer-appearance').count()===1 && await foot.locator('.grz-session-footer-spinner').isVisible());
        await foot.evaluate(()=>{
            delete testModel.appearance;testEvents['viewEnv.onDataChanged']();
            window.realCreateElement=document.createElement;
            document.createElement=function(name){if(name==='style')throw new Error('injected style failure');return realCreateElement.apply(this,arguments);};
        });
        await foot.evaluate(value=>pushFooter(value),presentation.custom.footer_css);
        check('Failure to create a footer stylesheet leaves its button and spinner operational',
            await foot.locator('#grz-session-stats-footer-button').count()===1 && await foot.locator('.grz-session-footer-spinner').isVisible());
        await foot.evaluate(()=>{document.createElement=realCreateElement;});
        await foot.evaluate(value=>pushFooter(value),presentation.custom.footer_css);
        await foot.evaluate(()=>{GRZSessionFooter.destroy();testEvents['viewEnv.onDataChanged']();GRZSessionFooter.refresh();});
        check('Footer teardown removes owned styles and stale events cannot recreate them',
            await foot.locator('#grz-session-footer-appearance').count()===0 && await foot.locator('#grz-session-stats-footer-button').count()===0);
        await foot.close();
        check('No JavaScript errors escape the appearance integration',errors.length===0);
        console.log(JSON.stringify({version:fs.readFileSync(path.join(root,'VERSION'),'utf8').trim(),checked_at_utc:new Date().toISOString(),passed:checks.length,checks,errors,live_client_tested:false,
            fixture:'Actual appearance.py compilation and shipped UI in Chromium; native model doubles and synthetic wheel events. Exact default computed styles are compared with the static fallback.'},null,2));
    } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
