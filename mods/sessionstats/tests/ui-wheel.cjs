/* Targeted wheel regression on shipped sources, using trusted Chrome input.
 * Gameface direction is from WoT InfoView.js #977; this is not a live WoT test.
 */
const fs = require('fs');
const path = require('path');
const assert = require('assert');
const {chromium} = require('playwright');
const root = path.resolve(__dirname, '..');
const fixtures = JSON.parse(fs.readFileSync(path.join(root, 'preview/demo_snapshot.json'), 'utf8'));
const checks = [], errors = [];
const check = (name, pass) => { assert(pass, name); checks.push(name); };

async function makePage(browser, native) {
    const page = await browser.newPage({viewport:{width:1440,height:950}});
    page.on('pageerror', error => errors.push(String(error)));
    const snapshot = JSON.parse(JSON.stringify(fixtures.normal));
    snapshot.viewport = {width:1440,height:950,scale:1};
    snapshot.window_size = [700,900];
    snapshot.appearance = snapshot.appearance || {};
    snapshot.appearance.window_settings = {background_transparency:0,maximized:false,restored_width:700,restored_height:900};
    for (const scope of Object.values(snapshot.scopes)) {
        const sample = scope.battles[0];
        scope.battles = Array.from({length:95}, (_, index) => ({...sample,id:'wheel-'+index,started_at:1700000000-index}));
        // This suite exercises legacy client batching, not native page replies.
        if(scope.pagination)delete scope.pagination.battles;
    }
    if (native) {
        await page.addInitScript(snapshot => {
            window.isDomBuilt = true;
            window.__events = {};
            window.model = {payload:JSON.stringify(snapshot),onAction:function(){}};
            window.engine = {whenReady:Promise.resolve(),on:function(name,fn){window.__events[name]=fn;},off:function(){}};
            window.viewEnv = {addDataChangedCallback:function(){return 1;},removeDataChangedCallback:function(){},resizeViewPx:function(){}};
        }, snapshot);
    }
    await page.route('http://grz-wheel.test/**', async route => {
        const name = new URL(route.request().url()).pathname.slice(1);
        if (!['SessionStats.html','session_stats.css','session_stats.js','session_stats_camo.png'].includes(name)) { await route.abort(); return; }
        await route.fulfill({status:200,contentType:name.endsWith('.js')?'text/javascript':name.endsWith('.css')?'text/css':name.endsWith('.png')?'image/png':'text/html',body:fs.readFileSync(path.join(root,'ui',name))});
    });
    await page.goto('http://grz-wheel.test/SessionStats.html');
    await page.waitForFunction(native => window.GRZSessionStats && window.GRZSessionStats.getState().nativeBound === native, native);
    if (!native) { await page.evaluate(snapshot => window.GRZSessionStats.update(snapshot), snapshot); }
    await page.locator('#ss-group-battles').click();
    await twoFrames(page);
    await page.evaluate(() => {
        window.__wheelAudit = [];
        document.getElementById('grz-session-stats').addEventListener('wheel', function(event) {
            window.__wheelAudit.push({trusted:event.isTrusted,prevented:event.defaultPrevented,deltaY:event.deltaY});
        }, false);
    });
    return page;
}

async function twoFrames(page) {
    await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}

async function wheel(page, deltaY, start, deltaX=0, selector='#ss-scroll') {
    // Finish navigation's deferred logical scroll restoration before choosing
    // the programmatic baseline used by this isolated trusted-input probe.
    await twoFrames(page);
    if (start !== undefined) { await page.locator('#ss-scroll').evaluate((el,start) => { el.scrollTop=start; }, start); }
    const baseline = await page.locator('#ss-scroll').evaluate(el=>({
        scrollTop:el.scrollTop,rows:document.querySelectorAll('#ss-groups .ss-group').length}));
    const count = await page.evaluate(()=>window.__wheelAudit.length);
    const rect = await page.locator(selector).boundingBox();
    await page.mouse.move(rect.x+rect.width/2, rect.y+Math.min(40,rect.height/2));
    await page.mouse.wheel(deltaX,deltaY);
    await page.waitForFunction(count=>window.__wheelAudit.length>count, count);
    await twoFrames(page);
    return page.evaluate(baseline=>{
        const node=document.getElementById('ss-scroll');
        return {before:baseline.scrollTop,after:node.scrollTop,max:node.scrollHeight-node.clientHeight,page:node.clientHeight,
            rowsBefore:baseline.rows,rowsAfter:document.querySelectorAll('#ss-groups .ss-group').length,
            audit:window.__wheelAudit[window.__wheelAudit.length-1]};
    }, baseline);
}

async function synthetic(page, values) {
    return page.evaluate(values=>{
        const node=document.getElementById('ss-scroll');
        node.scrollTop=400;
        const before=node.scrollTop;
        const event=new WheelEvent('wheel',{bubbles:true,cancelable:true,...values});
        node.dispatchEvent(event);
        return {before,after:node.scrollTop,prevented:event.defaultPrevented,page:node.clientHeight};
    }, values);
}

(async function() {
    const localChrome=path.resolve(root,'../.wot-design-tools/chrome-testing/chrome-headless-shell-linux64/chrome-headless-shell');
    const browser=await chromium.launch({executablePath:process.env.GRZ_CHROME || localChrome,headless:true,args:['--no-sandbox']});
    try {
        const native=await makePage(browser,true);
        let result=await wheel(native,-120,400);
        check('Trusted native down moves one quarter of the visible list and cancels the browser default',Math.abs(result.after-result.before-result.page/4)<=1 && result.audit.trusted && result.audit.prevented);
        result=await wheel(native,120,400);
        check('Trusted native up moves the same readable step in the opposite direction',Math.abs(result.before-result.after-result.page/4)<=1 && result.audit.prevented);
        result=await wheel(native,-1,400);
        check('A normalized native delta of -1 still moves a readable portion of the list',result.after-result.before>=80 && Math.abs(result.after-result.before-result.page/4)<=1 && result.audit.prevented);
        result=await wheel(native,1,400);
        check('A normalized native delta of +1 retains the correct upward direction',Math.abs(result.before-result.after-result.page/4)<=1 && result.audit.prevented);
        result=await wheel(native,-0.75,400);
        check('Fractional native deltas do not regress to subpixel crawling',Math.abs(result.after-result.before-result.page/4)<=1 && result.audit.prevented);
        for (let i=0;i<3;i++) { result=await wheel(native,-40,i===0?400:undefined); }
        check('Three native wheel events traverse three quarters of the view without duplicate movement',Math.abs(result.after-400-result.page*3/4)<=3);

        const fullListHeight=result.page;
        // Resize through the same saved settings path as the native host.
        // Both heights fit the viewport and respect the logical minimum.
        await native.evaluate(()=>{
            const snapshot=JSON.parse(model.payload);snapshot.window_size=[700,730];
            snapshot.appearance.window_settings.restored_height=730;
            model.payload=JSON.stringify(snapshot);__events['viewEnv.onDataChanged']();
        });
        result=await wheel(native,-1,400);
        const shortPanel=await native.locator('#grz-session-stats').evaluate(el=>el.getBoundingClientRect().height);
        check('The wheel step follows the shorter visible list after a supported panel resize: '+JSON.stringify({shortPanel,fullListHeight,...result}),
            shortPanel===730 && result.page===fullListHeight-170 &&
            Math.abs(result.after-result.before-result.page/4)<=1 && result.audit.prevented);
        await native.evaluate(()=>{
            const snapshot=JSON.parse(model.payload);snapshot.window_size=[700,900];
            snapshot.appearance.window_settings.restored_height=900;
            model.payload=JSON.stringify(snapshot);__events['viewEnv.onDataChanged']();
        });
        await twoFrames(native);
        check('Restoring the panel height restores the visible list used by subsequent wheel probes',
            await native.locator('#ss-scroll').evaluate(el=>el.clientHeight)===fullListHeight);

        result=await synthetic(native,{deltaY:-3,deltaMode:1});
        check('Line-mode native input uses the same readable wheel step',Math.abs(result.after-result.before-result.page/4)<=1 && result.prevented);
        result=await synthetic(native,{deltaY:-1,deltaMode:2});
        check('Page-mode native input advances by the visible scroll height',result.after===result.before+result.page && result.prevented);

        result=await wheel(native,5,400,120);
        check('Dominantly horizontal input does not move the vertical list',result.after===400 && result.audit.prevented);
        result=await wheel(native,0,400,120);
        check('Pure horizontal input remains vertical-neutral',result.after===400 && result.audit.prevented);
        await native.keyboard.down('Shift');
        result=await wheel(native,-120,400);
        await native.keyboard.up('Shift');
        check('Shift-wheel does not turn into vertical scrolling',result.after===400 && result.audit.prevented);
        result=await wheel(native,-120,400,0,'#ss-titlebar');
        check('Wheel over the titlebar does not control the content scroller',result.after===400 && !result.audit.prevented);

        await native.locator('#ss-scope-manual').click();
        await native.locator('#ss-reset').click();
        result=await wheel(native,-120,400,0,'#ss-reset-overlay');
        check('The reset dialog consumes wheel input without moving its background',result.after===400 && result.audit.prevented);
        await native.locator('#ss-reset-cancel').click();
        await native.locator('#ss-scope-launch').click();
        await twoFrames(native);
        check('Long history starts with a bounded batch',await native.locator('#ss-groups .ss-group').count()===40);
        let nearEnd=await native.locator('#ss-scroll').evaluate(el=>el.scrollHeight-el.clientHeight-201);
        result=await wheel(native,-1,nearEnd);
        const batchCount=await native.locator('#ss-groups .ss-group').count();
        check('Native wheel toward the end exposes the next history batch'+
            (batchCount>=80 ? '' : ' '+JSON.stringify({nearEnd,batchCount,...result})),batchCount>=80);
        nearEnd=await native.locator('#ss-scroll').evaluate(el=>el.scrollHeight-el.clientHeight-201);
        await wheel(native,-1,nearEnd);
        const end=await native.locator('#ss-scroll').evaluate(el=>el.scrollHeight-el.clientHeight);
        result=await wheel(native,-1,end-1);
        check('The last row is reachable and downward input clamps at the bottom',await native.locator('#ss-groups .ss-group').count()===95 && result.after===result.max && result.audit.prevented);
        result=await wheel(native,1,1);
        check('Upward input clamps at zero and remains consumed',result.after===0 && result.audit.prevented);

        const preview=await makePage(browser,false);
        result=await wheel(preview,120,400);
        check('The unbound browser preview keeps ordinary trusted downward scrolling',result.after===520 && result.audit.trusted && !result.audit.prevented);
        result=await wheel(preview,-120,400);
        check('The unbound browser preview keeps ordinary upward scrolling',result.after===280 && !result.audit.prevented);

        await native.evaluate(()=>window.GRZSessionStats.destroy());
        result=await wheel(native,-120,400);
        check('Cleanup removes the adapter; the original native-sign/browser-default mismatch is reproduced as a negative control',result.after===280 && result.audit.trusted && !result.audit.prevented);
        check('No JavaScript errors',errors.length===0);
        console.log(JSON.stringify({version:fs.readFileSync(path.join(root,'VERSION'),'utf8').trim(),checked_at_utc:new Date().toISOString(),passed:checks.length,checks,errors,live_client_tested:false,
            fixture:'Trusted Chrome wheel input with the sign and proportional quarter-view step used by WoT InfoView.js #977. Synthetic events are limited to line/page modes. This does not execute Gameface C++.'},null,2));
    } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
