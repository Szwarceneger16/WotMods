/* Pending/processing model and CSS animation; native Gameface is not emulated. */
const {chromium} = require('playwright');
const path = require('path');
const fs = require('fs');
const assert = require('assert');
const root = path.resolve(__dirname, '..');
const checks = [];
const errors = [];
function check(name, condition) { assert(condition, name); checks.push(name); }

async function fixture(browser, retained = false) {
  const page = await browser.newPage({viewport:{width:640, height:120},deviceScaleFactor:2});
  page.on('pageerror', error => errors.push(error.message));
  await page.setContent(`<html style="font-size:1px"><head><style>
    body {margin:0;background:#121413;font:14px Arial,sans-serif;color:#aaa;}
    .App_footer_verified {display:flex;align-items:center;justify-content:flex-end;height:64px;padding:0 20px;background:linear-gradient(#262823,#171916);}
    .Footer_controls {display:flex;align-items:center;}
    .SessionStats_base_original {display:flex;align-items:center;width:54rem;height:36rem;}
    #native-button {border:0;background:transparent;color:#aaa;font:13px Arial,sans-serif;height:36px;}
  </style></head><body><div class="App_footer_verified"><div class="Footer_controls"><div class="SessionStats_base_original">19</div><button id="native-button">EU III</button></div></div></body></html>`);
  await page.evaluate(retained => {
    window.testActions = [];
    window.testEvents = {};
    window.testWarnings = [];
    window.testFrames = [];
    window.testCallbacks = [];
    window.testID = 41;
    window.testWrapped = false;
    window.testModel = {activity:JSON.stringify({pending:0,processing:false}),onAction:args => testActions.push(args)};
    window.console.warn = message => testWarnings.push(message);
    if (retained) window.requestAnimationFrame = callback => { testFrames.push(callback); return testFrames.length; };
    window.isDomBuilt = true;
    window.engine = {
      whenReady:Promise.resolve(),
      on(name, callback) { (testEvents[name] || (testEvents[name] = [])).push(callback); },
      off(name, callback) {
        if (retained) throw new TypeError('injected cleanup failure');
        testEvents[name] = (testEvents[name] || []).filter(fn => fn !== callback);
      }
    };
    window.viewEnv = {
      addDataChangedCallback(name, id) { testCallbacks.push(['add',id]); return id + 100; },
      removeDataChangedCallback(callback, id) {
        testCallbacks.push(['remove',id]);
        if (retained) throw new TypeError('injected cleanup failure');
      }
    };
    window.subViews = {
      ids() { return testID === null ? [] : [testID]; },
      get() { return {model:{grzSessionFooter:testWrapped ? {value:testModel} : testModel}}; }
    };
    window.emitChange = () => (testEvents['viewEnv.onDataChanged'] || []).slice().forEach(fn => fn());
  }, retained);
  await page.addStyleTag({path:path.join(root,'ui/footer.css')});
  await page.addScriptTag({path:path.join(root,'ui/footer.js')});
  await page.waitForSelector('#grz-session-stats-footer-button');
  return page;
}

async function setActivity(page, pending, processing, wrapped = false) {
  await page.evaluate(({pending,processing,wrapped}) => {
    const value=JSON.stringify({pending,processing});
    testModel.activity = wrapped ? {value} : value;
    testWrapped = wrapped;
    emitChange();
  }, {pending,processing,wrapped});
}

(async function () {
  const localChrome = path.resolve(root,'../.wot-design-tools/chrome-testing/chrome-headless-shell-linux64/chrome-headless-shell');
  const browser = await chromium.launch({executablePath:process.env.GRZ_CHROME || localChrome,headless:true,args:['--no-sandbox']});
  try {
    const page = await fixture(browser);
    const button = page.locator('#grz-session-stats-footer-button');
    const spinner = button.locator('.grz-session-footer-spinner');
    check('Idle model keeps the original label and hidden, non-animating spinner',
      await button.getAttribute('title') === 'Session statistics: battles, win rate and WN8' &&
      await button.getAttribute('aria-busy') === 'false' &&
      await spinner.evaluate(el => getComputedStyle(el).display === 'none' && getComputedStyle(el).animationName === 'none'));

    await setActivity(page,3,false);
    check('Known pending results show the spinner through a native model event',
      await spinner.isVisible() && await button.getAttribute('aria-busy') === 'true' &&
      (await button.getAttribute('title')).includes('Waiting for results: 3'));
    check('Active indicator uses one CSS rotation without a script animation loop',
      await spinner.evaluate(el => getComputedStyle(el).animationName === 'grz-session-footer-spin' &&
        getComputedStyle(el).animationIterationCount === 'infinite' && el.getAnimations().length === 1));
    const transformBefore = await spinner.evaluate(el => getComputedStyle(el).transform);
    await page.waitForTimeout(180);
    const transformAfter = await spinner.evaluate(el => getComputedStyle(el).transform);
    check('The visible spinner actually changes rotation with time', transformBefore !== transformAfter);

    await spinner.evaluate(el => {el.getAnimations().forEach(a => {a.pause();a.currentTime=0;});});
    const geometry = await button.evaluate(el => {
      const box = node => {const r=node.getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height};};
      return {button:box(el),spinner:box(el.querySelector('.grz-session-footer-spinner')),
        icon:box(el.querySelector('.grz-session-footer-icon')),badge:box(el.querySelector('.grz-session-footer-rating')),
        bars:el.querySelectorAll('.grz-session-footer-bar').length,text:el.textContent.trim(),
        pointer:getComputedStyle(el.querySelector('.grz-session-footer-spinner')).pointerEvents};
    });
    check('Busy button retains its 44 x 36 footprint, all bars and superscript WN8',
      geometry.button.width===44 && geometry.button.height===36 && geometry.bars===3 && geometry.text==='WN8');
    check('Spinner fits above the bar glyph and left of WN8 without overlap or native clipping',
      geometry.spinner.x>=geometry.button.x && geometry.spinner.y>=geometry.button.y &&
      geometry.spinner.bottom<=geometry.icon.y && geometry.spinner.right<geometry.badge.x &&
      geometry.spinner.right<=geometry.button.right && geometry.spinner.bottom<=geometry.button.bottom);
    check('Spinner cannot intercept native button input',geometry.pointer==='none');
    if (process.env.GRZ_ACTIVITY_SCREENSHOT) {
      await page.locator('.App_footer_verified').screenshot({path:process.env.GRZ_ACTIVITY_SCREENSHOT});
    }
    await spinner.evaluate(el => {el.getAnimations().forEach(a=>a.play());});
    await button.click({position:{x:15,y:7}});
    await button.focus();
    await page.keyboard.press('Enter');
    check('Mouse over the spinner and keyboard still open statistics exactly once each',
      JSON.stringify(await page.evaluate(()=>testActions))===JSON.stringify([{action:'open'},{action:'open'}]));

    await setActivity(page,2,true,true);
    check('Wrapped native model/property values show processing and pending count',
      (await button.getAttribute('title')).includes('Processing results (Pending: 2)') && await spinner.isVisible());
    await setActivity(page,0,true);
    check('Processing alone remains busy even before a pending count is available',
      await spinner.isVisible() && (await button.getAttribute('title')).includes('Processing results.'));
    for (const scale of [1.5,2]) {
      await page.evaluate(scale=>{document.documentElement.style.fontSize=scale+'px';},scale);
      check('Spinner and button scale with native rem at '+scale+'x',
        (await button.boundingBox()).width===44*scale &&
        await spinner.evaluate((el,scale)=>parseFloat(getComputedStyle(el).width)===10*scale,scale));
    }
    await page.evaluate(()=>{document.documentElement.style.fontSize='1px';});
    await setActivity(page,0,false);
    check('Completing work restores the exact idle label and removes the CSS animation',
      await button.getAttribute('title')==='Session statistics: battles, win rate and WN8' &&
      await button.getAttribute('aria-busy')==='false' &&
      await spinner.evaluate(el=>getComputedStyle(el).display==='none' && el.getAnimations().length===0));

    await page.evaluate(()=>{delete testModel.activity;emitChange();});
    check('An older model without activity keeps a usable idle button without a warning',
      await button.count()===1 && !(await spinner.isVisible()) && await page.evaluate(()=>testWarnings.length===0));
    const malformed=['{bad',JSON.stringify({pending:-1,processing:false}),JSON.stringify({pending:'2',processing:true}),
      JSON.stringify({pending:2.5,processing:false}),JSON.stringify({pending:1,processing:'false'}),{pending:1,processing:true}];
    for (const value of malformed) {
      await page.evaluate(value=>{testModel.activity=value;emitChange();},value);
      assert.strictEqual(await button.count(),1);
      assert.strictEqual(await spinner.isVisible(),false);
    }
    check('Malformed activity stays idle, preserves the button and logs one diagnostic',
      await page.evaluate(()=>testWarnings.length===1 && testWarnings[0].includes('activity')));
    await setActivity(page,1,false);
    check('Activity recovers on a valid state after a malformed optional property',await spinner.isVisible());

    await page.evaluate(()=>{testID=null;emitChange();});
    check('Removing the native child removes its active spinner with the button',await button.count()===0);
    await page.evaluate(()=>{testID=57;emitChange();});
    check('A recreated native child immediately shows its current waiting state',
      await spinner.isVisible() && (await button.getAttribute('title')).includes('Waiting for results: 1') &&
      await page.evaluate(()=>JSON.stringify(testCallbacks)===JSON.stringify([['add',41],['remove',41],['add',57]])));
    check('Native footer content is preserved throughout activity transitions',
      await page.locator('.SessionStats_base_original').textContent()==='19' && await page.locator('#native-button').count()===1);
    const languages=JSON.parse(fs.readFileSync(path.join(root,'data/languages.json'),'utf8')).languages;
    for(const [language,messages] of Object.entries(languages)) {
      await page.evaluate(messages=>{
        testModel.activity=JSON.stringify({pending:3,processing:true,labels:messages});emitChange();
      },Object.fromEntries(['footer.idle','footer.processing','footer.waiting','status.pending','metric.wn8'].map(key=>[key,messages[key]])));
      const expected=messages['footer.idle']+'. '+messages['footer.processing']+' ('+messages['status.pending'].replace('{0}','3')+').';
      check('Localized active footer tooltip and accessible label for '+language,
        await button.getAttribute('title')===expected && await button.getAttribute('aria-label')===expected &&
        await button.getAttribute('aria-busy')==='true');
    }
    await page.close();

    const late=await fixture(browser,true);
    await setActivity(late,9,true);
    const result=await late.evaluate(()=>{
      const old=document.getElementById('grz-session-stats-footer-button');
      const oldSpinner=old.querySelector('.grz-session-footer-spinner');
      const oldClick=old.onclick;
      GRZSessionFooter.destroy();
      emitChange();
      while(testFrames.length)testFrames.shift()(0);
      oldClick();
      GRZSessionFooter.refresh();
      return {present:!!document.getElementById('grz-session-stats-footer-button'),
        connected:oldSpinner.isConnected,actions:testActions.length,animations:oldSpinner.getAnimations().length};
    });
    check('Cleanup removes the animation even when native unsubscribe fails',!result.present && !result.connected && result.animations===0);
    check('Retained events, queued frames and stale clicks cannot revive the busy indicator',!result.present && result.actions===0);
    await late.close();
    check('No JavaScript errors',errors.length===0);
    console.log(JSON.stringify({checked_at_utc:new Date().toISOString(),passed:checks.length,checks,errors,live_client_tested:false,
      fixture:'Chromium with native-model doubles; checks CSS rotation, unchanged button geometry, bridge states and teardown.'},null,2));
  } finally { await browser.close(); }
})().catch(error=>{console.error(error);process.exitCode=1;});
