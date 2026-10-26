/* GUI language selection uses the native command; catalogs stay inside the package. */
const fs=require('fs'),path=require('path');
module.exports=async ({browser,nativeHost,check})=>{
 const catalogs=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
 const page=await nativeHost(browser,{});
 await page.evaluate(()=>{const s=JSON.parse(model.payload);s.localization={language:'en',selected:'auto',messages:{}};model.payload=JSON.stringify(s);GRZSessionStats.update(model.payload);});
 check('Language picker defaults to Automatic',await page.locator('#ss-language .ss-select-trigger .ss-control-label').textContent()==='Automatic');
 for(const code of ['pl','fr','de','es','uk','ru','en','auto']){
  await page.locator('#ss-language [role=combobox]').click();
  await page.locator('#ss-language [data-value="'+code+'"]').click();
  check('Language command carries the supported choice and current account: '+code,await page.evaluate(code=>{
   const c=__grzCommands.filter(c=>c.action==='language').pop();
   return c.language===code && c.account_key===JSON.parse(model.payload).account_key;
  },code));
  const resolved=code==='auto'?'pl':code;
  await page.evaluate(({code,resolved,messages})=>{const s=JSON.parse(model.payload);s.localization={selected:code,language:resolved,messages};model.payload=JSON.stringify(s);GRZSessionStats.update(model.payload);},{code,resolved,messages:catalogs[resolved]});
  check('Native language update changes visible captions immediately: '+code,await page.locator('#ss-refresh .ss-control-label').textContent()===catalogs[resolved].refresh);
 }
 for(const width of [320,744]){
  await page.setViewportSize({width,height:820});
  for(const [code,messages] of Object.entries(catalogs)){
   await page.evaluate(({code,messages,width})=>{const s=JSON.parse(model.payload);s.viewport.width=width;s.localization={selected:'auto',language:code,messages};model.payload=JSON.stringify(s);GRZSessionStats.update(model.payload);},{code,messages,width});
   check('Language picker fits '+code+' at '+width,await page.locator('.ss-language-row').evaluate(row=>{
    const box=row.getBoundingClientRect(),button=row.querySelector('[role=combobox]'),b=button.getBoundingClientRect();
    const label=button.querySelector('.ss-control-label'),range=document.createRange();range.selectNodeContents(label);
    return b.left>=box.left && b.right<=box.right+1 && range.getBoundingClientRect().width<=label.getBoundingClientRect().width+1;
   }));
  }
 }
 await page.locator('#ss-language [role=combobox]').focus();await page.keyboard.press('ArrowDown');await page.keyboard.press('End');await page.keyboard.press('Enter');
 check('Language picker supports keyboard selection',await page.evaluate(()=>__grzCommands.filter(c=>c.action==='language').pop().language==='uk'));
 await page.close();
};
