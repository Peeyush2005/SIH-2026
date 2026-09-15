import {chromium} from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
const out=process.env.BLUECHO_EVIDENCE||'E:/Hackathon/execution/scene_explorer_20260915/scenes';await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe'});
const page=await browser.newPage({viewport:{width:1536,height:1050}}),errors=[],results=[];
page.on('pageerror',e=>errors.push(e.message));
async function ready(){await page.waitForFunction(()=>document.querySelector('.surprise-button')&&!document.querySelector('.surprise-button').disabled&&document.querySelector('svg.sonar image'));}
async function pixels(){return page.locator('svg.sonar image').evaluate(async e=>{const im=new Image();im.src=e.getAttribute('href');await im.decode();const c=document.createElement('canvas');c.width=32;c.height=16;const ctx=c.getContext('2d');ctx.drawImage(im,0,0,32,16);return [...ctx.getImageData(0,0,32,16).data];});}
try{
 await page.goto(process.env.BLUECHO_URL||'http://127.0.0.1:8010');await page.getByRole('button',{name:'Try demo',exact:true}).click();await ready();
 assert.equal(await page.getByRole('button',{name:'Models',exact:true}).count(),0);
 for(const [id,name] of [['pipeline','Pipeline corridor'],['wreck','Wreck silhouette'],['objects','Harbour debris'],['reef','Rocky seabed'],['coverage','Interrupted coverage'],['fls','Forward-looking fan']]){
  await page.getByRole('button',{name:'Open '+name,exact:true}).click();await ready();
  assert.equal(await page.locator('.active-scene h2').innerText(),name);
  assert.equal(await page.locator('svg.sonar').getAttribute('viewBox'),'0 0 1400 680');
  const p=await pixels();results.push({id,pixels:p});
  assert.ok(await page.locator('[data-candidate]').count()>0);
  await page.locator('svg.sonar').screenshot({path:path.join(out,id+'.png')});
 }
 const distances=[];for(let i=0;i<results.length;i++)for(let j=i+1;j<results.length;j++){
  const a=results[i],b=results[j];const distance=a.pixels.reduce((sum,v,k)=>sum+(k%4===3?0:Math.abs(v-b.pixels[k])),0)/(32*16*3);
  assert.ok(distance>8,`${a.id}/${b.id} insufficient visual difference: ${distance}`);distances.push({scenes:[a.id,b.id],meanPixelDifference:distance});
 }
 let current=await page.locator('.active-scene h2').innerText();
 for(let n=0;n<3;n++){await page.getByRole('button',{name:'Surprise me',exact:true}).click();await ready();const next=await page.locator('.active-scene h2').innerText();assert.notEqual(current,next);current=next;}
 await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:path.join(out,'desktop.png'),fullPage:true});
 const viewer=await page.locator('svg.sonar').boundingBox();assert.ok(viewer.y<740,'Viewer should be visible without scrolling through setup');
 await page.setViewportSize({width:390,height:844});await page.evaluate(()=>scrollTo(0,0));assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.screenshot({path:path.join(out,'mobile.png'),fullPage:true});
 await page.getByRole('button',{name:'Open Forward-looking fan',exact:true}).click();await ready();
 assert.equal(await page.locator('.active-scene h2').innerText(),'Forward-looking fan');
 assert.deepEqual(errors,[]);
 await fs.writeFile(path.join(out,'receipt.json'),JSON.stringify({status:'PASS',checks:['Models navigation removed','All six scenes load and show contacts','Each scene opens with complete image geometry','All 15 scene pairs visibly differ after image downsampling','Surprise me never repeats the active environment','Viewer above fold on desktop','Mobile layout and horizontal scene picker usable'],distances,errors},null,2));
 console.log('PASS six distinct scenes, nonrepeating surprise, full-frame view, desktop and mobile');
}catch(e){await page.screenshot({path:path.join(out,'failure.png'),fullPage:true});throw e}finally{await browser.close()}
