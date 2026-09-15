import {chromium} from 'playwright';
import fs from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
const catalog=JSON.parse(await fs.readFile(new URL('./public/real-demo/catalog.json',import.meta.url),'utf8'));
const out=process.env.BLUECHO_EVIDENCE||'E:/Hackathon/execution/real_demo_20260915/browser';await fs.mkdir(out,{recursive:true});
const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME||'C:/Program Files/Google/Chrome/Application/chrome.exe'});
const page=await browser.newPage({viewport:{width:1536,height:1050},acceptDownloads:true}),errors=[],requests=[],checks=[];
page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push(r.url()));
const pass=s=>{checks.push(s);console.log('PASS',s)};
async function ready(){await page.waitForFunction(()=>document.querySelector('.surprise-button')&&!document.querySelector('.surprise-button').disabled&&document.querySelector('svg.sonar image'))}
async function download(name,file){await page.getByRole('button',{name:'View inspection report',exact:true}).first().click();const p=page.waitForEvent('download');await page.getByRole('button',{name,exact:true}).click();await(await p).saveAs(path.join(out,file));const bytes=await fs.readFile(path.join(out,file));await page.getByRole('button',{name:'Return to inspection',exact:true}).click();await ready();return bytes;}
try{
 await page.goto(process.env.BLUECHO_URL||'http://127.0.0.1:8010');await page.getByRole('button',{name:'Try demo',exact:true}).click();await ready();
 for(const sample of catalog.filter(s=>s.id!=='noaa0')){
  await page.getByRole('button',{name:'Open '+sample.name,exact:true}).click();await ready();
  const exported=JSON.parse(await download('JSON',sample.id+'.json'));
  assert.equal(exported.demo.synthetic,false);assert.equal(exported.demo.kind,'real_sonar_saved_inference');
  const native=JSON.parse(await fs.readFile(new URL('./public/real-demo/'+sample.id+'/results.json',import.meta.url),'utf8'));
  assert.deepEqual(exported.detections,native.detections);assert.deepEqual(exported.unvalidated_proposals,native.unvalidated_proposals);
  const imageBytes=await page.locator('svg.sonar image').evaluate(async e=>Array.from(new Uint8Array(await(await fetch(e.getAttribute('href'))).arrayBuffer())));
  assert.equal(crypto.createHash('sha256').update(Buffer.from(imageBytes)).digest('hex'),sample.files['original.png']);
  for(const d of exported.detections){assert.ok(d.model_sha256.length===64);assert.equal(d.synthetic,false);assert.notEqual(d.score_type,'simulated_demo_score_0_100');if(!sample.id.startsWith('noaa'))assert.equal(d.coordinates,null);}
  await page.getByRole('button',{name:'Map',exact:true}).click();
  if(sample.id.startsWith('noaa'))await page.getByText('REAL SURVEY METADATA · WGS84',{exact:true}).waitFor();
  else {await page.getByRole('heading',{name:'Location metadata needed'}).waitFor();assert.equal(await page.locator('[data-map-candidate]').count(),0);}
  await page.getByRole('button',{name:'Image',exact:true}).click();await page.locator('svg.sonar').screenshot({path:path.join(out,sample.id+'.png')});
 }
 pass('All eleven featured demos load hash-verified real pixels and exact saved detector outputs');
 pass('NOAA has metadata-derived coordinates; other samples retain unavailable positions');
 await page.getByRole('button',{name:'Open Shampoo-bottle sample',exact:true}).click();await ready();
 await page.getByLabel('Review note',{exact:true}).fill('Real sonar image; label remains unverified');await page.getByRole('button',{name:'Save note',exact:true}).click();await page.getByText('Review saved. This is not field verification.',{exact:true}).waitFor();
 await page.getByRole('dialog',{name:'Note saved'}).getByRole('button',{name:'Close review confirmation'}).click();await page.getByRole('button',{name:'Edit saved review',exact:true}).click();await page.getByText('Correct label or box',{exact:true}).click();await page.getByLabel('Corrected label').fill('Needs field review');await page.getByLabel('Original pixels: x1, y1, x2, y2').fill('100, 100, 250, 250');await page.getByRole('button',{name:'Save correction',exact:true}).click();
 await page.getByRole('dialog',{name:'Correction saved'}).getByRole('button',{name:'Close review confirmation'}).click();await page.waitForFunction(()=>document.querySelector('[data-candidate]')?.getAttribute('x')==='100');
 const edited=JSON.parse(await download('JSON','corrected.json'));assert.equal(edited.review_revision,2);assert.equal(edited.detections[0].coordinates,null);
 assert.ok(edited.detections[0].original_prediction);pass('Review corrections preserve original outputs without fabricating geography');
 await page.reload();await ready();assert.equal(JSON.parse(await download('JSON','reloaded.json')).review_revision,2);pass('Real-demo reviews persist through reload');
 assert.match((await download('CSV','real.csv')).toString(),/false/);await download('GEOJSON','real.geojson');await download('PDF brief','real.pdf');await download('Evidence ZIP','real.zip');await download('Review candidates JSON','reviews.json');pass('All report formats download with real-source provenance');
 await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:path.join(out,'desktop.png'),fullPage:true});await page.setViewportSize({width:390,height:844});assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.screenshot({path:path.join(out,'mobile.png'),fullPage:true});
 let last=await page.locator('.active-scene h2').innerText();for(let i=0;i<3;i++){await page.getByRole('button',{name:'Surprise me',exact:true}).click();await page.waitForFunction(previous=>document.querySelector('.active-scene h2')?.textContent!==previous,last);await ready();const next=await page.locator('.active-scene h2').innerText();assert.notEqual(last,next);last=next;}
 for(let i=0;i<14;i++){await page.getByRole('button',{name:i%2?'Open Shampoo-bottle sample':'Open Pipeline survey',exact:true}).click();await ready();}const revisited=JSON.parse(await download('JSON','revisited.json'));assert.equal(revisited.review_revision,2);
 assert.ok(!requests.some(s=>s.includes('.onnx')));pass('Sample switching is nonrepeating and saved results open without model downloads');
 assert.deepEqual(errors,[]);await fs.writeFile(path.join(out,'receipt.json'),JSON.stringify({status:'PASS',checks,errors},null,2));
}catch(e){await page.screenshot({path:path.join(out,'failure.png'),fullPage:true});throw e}finally{await browser.close()}
