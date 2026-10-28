import {chromium} from '@playwright/test';
const b=await chromium.connectOverCDP('http://127.0.0.1:9223');
try{const p=b.contexts().flatMap(c=>c.pages()).find(p=>/index.html/.test(p.url()));
 await p.addStyleTag({content:'.compact-header .hero-banner::after { opacity: var(--hero-opacity, .55); } .compact-header .controls-strip select, .compact-header .more-trigger, .compact-header .smart-mode-btn, .compact-header .win-btn { background-color: var(--glass-bg); }'});
 console.log(JSON.stringify(await p.evaluate(()=>{const old=opacitySlider.value;updateGlassOpacity(10,true);const min=getComputedStyle(document.querySelector('.hero-banner'),'::after').opacity;updateGlassOpacity(100,true);const max=getComputedStyle(document.querySelector('.hero-banner'),'::after').opacity;updateGlassOpacity(Number(old),true);return {headerMinimum:min,headerMaximum:max,sliderRestored:old};})));
 await p.evaluate(()=>window.api.restartBackend());
 for(let i=0;i<60;i++){const ready=await p.evaluate(async()=>{try{runtimeCatalogCache=null;const c=await getRuntimeModelCatalog();return c?.some(m=>m.id==='google-gemini-3-8-flash'&&m.vision===true)}catch{return false}});if(ready)break;await new Promise(r=>setTimeout(r,1000));}
 console.log(JSON.stringify(await p.evaluate(async()=>({text:await recoveryCandidates('auto',null),screenshot:await recoveryCandidates('auto','test')}))));
}finally{await b.close()}
