/* DOM contract check with a mocked native model, not a live-client test. */
const { chromium } = require('playwright');
const path = require('path');
const assert = require('assert');
const fs = require('fs');

// A documented Gameface difference exposed by the user's in-game screenshot:
// currentColor is not accepted as a background color. Chrome would accept it.
function gamefaceBackgrounds(css) {
  return css.replace(/\bbackground(?:-color)?\s*:\s*currentcolor\s*;/gi, '');
}

(async () => {
  const localChrome = path.resolve(__dirname, '../../.wot-design-tools/chrome-testing/chrome-headless-shell-linux64/chrome-headless-shell');
  const executablePath = process.env.GRZ_CHROME || process.env.GRZ_CHROME_EXECUTABLE || (fs.existsSync(localChrome) ? localChrome : undefined);
  const browser = await chromium.launch({executablePath, headless:true, args:['--no-sandbox']});
  try {
    const page = await browser.newPage({viewport:{width:720,height:160}});
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    await page.setContent(`<html style="font-size:1px"><head><style>
      body {margin:0;background:#121413;font:14px Arial,sans-serif;color:#999;}
      .App_footer_verified {display:flex;align-items:center;justify-content:flex-end;height:64px;padding:0 20px;background:linear-gradient(#262823,#171916);}
      .Footer_controls {display:flex;align-items:center;gap:4px;}
      .SessionStats_base_test {display:flex;align-items:center;width:54rem;height:36rem;gap:6rem;}
      .native-test-icon {position:relative;display:block;width:18rem;height:22rem;}
      .native-test-icon i {position:absolute;bottom:0;width:4rem;background:#929797;}
      .native-test-icon i:nth-child(1) {left:0;height:10rem;}
      .native-test-icon i:nth-child(2) {left:6rem;height:15rem;}
      .native-test-icon i:nth-child(3) {left:12rem;height:22rem;}
      #native-count {font-size:14rem;}
      #original-other {border:0;border-left:1px solid #404440;background:transparent;color:#aaa;font:13px Arial,sans-serif;height:36px;padding:0 18px;}
      </style></head><body><div class="App_footer_verified"><div class="Footer_controls"><div class="SessionStats_base_test"><span class="native-test-icon"><i></i><i></i><i></i></span><span id="native-count">19</span></div><button id="original-other">EU III</button></div></div></body></html>`);
    await page.evaluate(() => {
      window.testActions = [];
      window.testCallbacks = [];
      window.nativeClicks = 0;
      document.querySelector('.SessionStats_base_test').onclick = () => { window.nativeClicks += 1; };
      window.testSubviewID = 41;
      window.nativeHandlers = {};
      window.isDomBuilt = true;
      window.engine = {
        whenReady:Promise.resolve(),
        on(name, callback) { window.nativeHandlers[name] = callback; },
        off(name) { delete window.nativeHandlers[name]; }
      };
      window.viewEnv = {
        addDataChangedCallback(name,id){window.testCallbacks.push(['add',id]);return id+100;},
        removeDataChangedCallback(callback,id){window.testCallbacks.push(['remove',id]);}
      };
      window.subViews = {
        ids(){return window.testSubviewID === null ? [] : [window.testSubviewID];},
        get(){return {model:{grzSessionFooter:{onAction(args){window.testActions.push(args);}}}};}
      };
    });
    const footerCSS = fs.readFileSync(path.join(__dirname,'../ui/footer.css'), 'utf8');
    await page.addStyleTag({content:gamefaceBackgrounds(footerCSS)});
    await page.addScriptTag({path:path.join(__dirname,'../ui/footer.js')});
    await page.waitForSelector('#grz-session-stats-footer-button');
    const button = page.getByRole('button', {name:'Session statistics: battles, win rate and WN8', exact:true});
    assert.strictEqual(await button.count(), 1);
    assert.strictEqual((await button.innerText()).trim(), 'WN8');
    assert.strictEqual(await button.getAttribute('title'), 'Session statistics: battles, win rate and WN8');
    assert.strictEqual(await button.locator('.grz-session-footer-icon[aria-hidden="true"]').count(), 1);
    assert.strictEqual(await button.locator('.grz-session-footer-rating[aria-hidden="true"]').count(), 1);
    assert.strictEqual(await button.locator('.grz-session-footer-bar').count(), 3);
    const geometry = await button.evaluate(element => {
      const box = node => { const r=node.getBoundingClientRect(); return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom}; };
      return {button:box(element),icon:box(element.querySelector('.grz-session-footer-icon')),
        badge:box(element.querySelector('.grz-session-footer-rating')),
        bars:Array.from(element.querySelectorAll('.grz-session-footer-bar')).map(box),
        barColors:Array.from(element.querySelectorAll('.grz-session-footer-bar')).map(bar => getComputedStyle(bar).backgroundColor),
        background:getComputedStyle(element).backgroundImage};
    });
    assert.strictEqual(geometry.button.width, 44);
    assert.strictEqual(geometry.button.height, 36);
    assert.strictEqual(geometry.background, 'none');
    assert.ok(geometry.badge.y < geometry.icon.y, 'WN8 must sit above the bars');
    assert.ok(geometry.badge.x > geometry.icon.x, 'WN8 must sit toward the upper right');
    assert.ok(geometry.badge.bottom <= geometry.icon.y, 'badge must not cover the tallest bar');
    assert.ok(geometry.badge.right <= geometry.button.right, 'badge must fit inside the compact button');
    assert.deepStrictEqual(geometry.bars.map(bar => bar.height), [9,13,18]);
    assert.deepStrictEqual(geometry.barColors, ['rgb(150, 154, 157)','rgb(150, 154, 157)','rgb(150, 154, 157)'],
      'bars must remain painted when Gameface rejects currentColor backgrounds');
    assert.ok(geometry.bars.every(bar => bar.bottom === geometry.icon.bottom));
    assert.ok(geometry.bars[0].right < geometry.bars[1].x && geometry.bars[1].right < geometry.bars[2].x);
    if (process.env.GRZ_FOOTER_SCREENSHOT) {
      await page.locator('.App_footer_verified').screenshot({path:process.env.GRZ_FOOTER_SCREENSHOT});
    }
    await page.click('#grz-session-stats-footer-button');
    assert.deepStrictEqual(await page.evaluate(() => window.testActions), [{action:'open'}]);
    await button.focus();
    assert.strictEqual(await button.evaluate(element => getComputedStyle(element).outlineStyle), 'solid');
    await page.keyboard.press('Enter');
    await page.keyboard.press('Space');
    assert.deepStrictEqual(await page.evaluate(() => window.testActions), [{action:'open'},{action:'open'},{action:'open'}]);
    assert.strictEqual(await page.evaluate(() => window.nativeClicks), 0);
    await page.click('.SessionStats_base_test');
    assert.strictEqual(await page.evaluate(() => window.nativeClicks), 1);
    assert.strictEqual(await page.locator('#original-other').count(), 1);
    assert.strictEqual(await page.locator('#native-count').textContent(), '19');
    assert.strictEqual(await button.locator('#native-count').count(), 0);
    await page.evaluate(() => { document.documentElement.style.fontSize = '1.5px'; });
    assert.strictEqual((await button.boundingBox()).width, 66);
    await page.evaluate(() => { document.documentElement.style.fontSize = '1px'; });
    await page.addScriptTag({path:path.join(__dirname,'../ui/footer.js')});
    assert.strictEqual(await page.locator('#grz-session-stats-footer-button').count(), 1);
    await page.evaluate(() => {
      window.testSubviewID = null;
      window.GRZSessionFooter.refresh();
    });
    assert.strictEqual(await page.locator('#grz-session-stats-footer-button').count(), 0);
    await page.evaluate(() => {
      document.querySelector('.SessionStats_base_test').remove();
      window.testSubviewID = 57;
      window.GRZSessionFooter.refresh();
    });
    assert.strictEqual(await page.locator('.App_footer_verified > #grz-session-stats-footer-button').count(), 1);
    assert.strictEqual(await page.locator('#original-other').count(), 1);
    assert.deepStrictEqual(await page.evaluate(() => window.testCallbacks), [['add',41],['remove',41],['add',57]]);
    await page.evaluate(() => {
      document.querySelector('.App_footer_verified').remove();
      window.GRZSessionFooter.refresh();
    });
    assert.strictEqual(await page.locator('#grz-session-stats-footer-button').count(), 0);
    await page.evaluate(() => window.GRZSessionFooter.destroy());
    assert.deepStrictEqual(await page.evaluate(() => window.testCallbacks), [['add',41],['remove',41],['add',57],['remove',57]]);
    const preview = fs.readFileSync(path.join(__dirname,'../preview/footer-icon.html'), 'utf8');
    assert.ok(preview.includes(fs.readFileSync(path.join(__dirname,'../ui/footer.css'), 'utf8')),
      'standalone preview must contain the actual footer stylesheet');
    assert.ok(!/<script\b/i.test(preview), 'static icon preview must not bind to a native or demo model');
    await page.setContent(preview);
    const staticButton = page.getByRole('button', {name:'Session statistics: battles, win rate and WN8', exact:true});
    assert.strictEqual((await staticButton.innerText()).trim(), 'WN8');
    assert.strictEqual(await staticButton.locator('.grz-session-footer-bar').count(), 3);
    assert.strictEqual((await staticButton.boundingBox()).width, 44);
    assert.deepStrictEqual(errors, []);
    console.log('PASS: 44px icon with three painted bars when currentColor backgrounds are unsupported, superscript WN8, accessible label and keyboard activation, rem scaling, isolated command bridge, native counter/handlers retained, duplicate guard, fallback, disappearance, subview resubscription, cleanup and standalone static preview.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
