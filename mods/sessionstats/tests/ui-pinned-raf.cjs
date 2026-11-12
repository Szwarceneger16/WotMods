/* A scheduled pin callback must tolerate removal of the optional RAF helper. */
module.exports=async({browser,nativeHost,check})=>{
  const page=await nativeHost(browser,{}),errors=[];
  page.on('pageerror',error=>errors.push(error.stack||String(error)));
  try{
    await page.evaluate(()=>new Promise(resolve=>{let left=20;
      function next(){if(--left)requestAnimationFrame(next);else resolve();}requestAnimationFrame(next);}));
    const result=await page.evaluate(()=>new Promise((resolve,reject)=>{
      const real=window.requestAnimationFrame;
      function capture(){
        const pending=[];window.requestAnimationFrame=callback=>{pending.push(callback);return pending.length;};
        document.getElementById('ss-scroll').dispatchEvent(new Event('scroll'));
        for(let count=0;pending.length&&count<20;count++){
          const callback=pending.shift();
          if(String(callback).includes('updatePinnedFilters(false, true)'))return callback;
          callback(performance.now());
        }
        return null;
      }
      const retained=capture();
      if(!retained){window.requestAnimationFrame=real;reject(Error('Actual pin callback was not captured'));return;}
      // Execute as a real browser callback, so an uncaught error reaches
      // pageerror independently of the fixture's awaited promise.
      window.requestAnimationFrame=undefined;
      real.call(window,()=>retained(performance.now()));
      real.call(window,()=>real.call(window,()=>{
        window.requestAnimationFrame=real;
        const fresh=capture();window.requestAnimationFrame=real;
        if(fresh)fresh(performance.now());
        resolve({captured:true,recovered:!!fresh});
      }));
    }));
    check('A retained pin callback tolerates optional RAF removal without an asynchronous browser error: '+JSON.stringify(errors),
      result.captured&&errors.length===0);
    check('Restoring RAF lets a new scroll acquire pin ownership after the previous callback retires',result.recovered);
  }finally{await page.close();}
};
