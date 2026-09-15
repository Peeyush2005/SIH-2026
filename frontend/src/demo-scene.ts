/** Procedural interface scenes. Never real survey data or model predictions. */
export const DEMO_SCENARIOS=[
 {id:'pipeline',name:'Pipeline corridor',terrain:'Rippling sand',description:'Trace a long pipe-like return across a rippled seabed.',hint:'Select the long return, then try correcting its box.'},
 {id:'wreck',name:'Wreck silhouette',terrain:'Deep-water silt',description:'Explore a large hull-shaped return and its extended shadow.',hint:'Explore the hull outline and inspect nearby fragments.'},
 {id:'objects',name:'Harbour debris',terrain:'Harbour floor',description:'Review scattered drums, angular objects and a coil-shaped return.',hint:'Mark a contact as uncertain or retain it for another look.'},
 {id:'reef',name:'Rocky seabed',terrain:'Natural clutter',description:'Compare rough outcrops, strong shadows and ambiguous contacts.',hint:'Try a false-alert decision on a natural-looking return.'},
 {id:'coverage',name:'Interrupted coverage',terrain:'Broken survey strip',description:'Examine missing bands and an interrupted linear return.',hint:'Open Quality and record a region that needs another scan.'},
 {id:'fls',name:'Forward-looking fan',terrain:'Acoustic sector',description:'Explore isolated returns in a forward-looking sonar sector.',hint:'Switch to Map to explore the simulated contact locations.'},
];
export function nextDemoScenario(current?:string,seed=crypto.getRandomValues(new Uint32Array(1))[0]){
 const choices=DEMO_SCENARIOS.filter(s=>s.id!==current);return choices[seed%choices.length].id;
}
export function demoScene(seed:number,scenario:string,scale=1){
 let state=seed>>>0;const random=()=>{state=(Math.imul(state,1664525)+1013904223)>>>0;return state/4294967296};
 const spec=DEMO_SCENARIOS.find(x=>x.id===scenario)||DEMO_SCENARIOS[0];
 const width=Math.round(1400*scale),height=Math.round(680*scale),c=document.createElement('canvas');c.width=width;c.height=height;const ctx=c.getContext('2d')!;
 const pixels=ctx.createImageData(width,height),phase=random()*20,angle=.15+random()*.6,nadir=630+random()*120;
 const tones:Record<string,number[]>={pipeline:[.72,1,1.02],wreck:[.8,.9,1.13],objects:[1.13,1,.66],reef:[.78,1,.81],coverage:[.75,.87,1],fls:[1.25,.99,.45]};
 const tint=tones[spec.id];
 for(let py=0;py<height;py++)for(let px=0;px<width;px++){
  const x=px/scale,y=py/scale,range=Math.abs(x-nadir)/700;
  const wave=Math.sin(x*.027*Math.cos(angle)+y*.049*Math.sin(angle)+phase);
  let value=52+range*24+wave*12+(random()+random()-1)*55;
  if(spec.id==='pipeline')value+=Math.sin(y*.065+x*.017+phase)*17;
  if(spec.id==='wreck')value=35+Math.sin(x*.008+y*.012+phase)*10+(random()-.5)*34;
  if(spec.id==='reef')value=48+Math.sin(x*.025+phase)*Math.cos(y*.039)*29+(random()-.5)*85;
  if(spec.id==='objects')value+=Math.sin(y*.016+phase)*14;
  if(spec.id==='fls'){
   const dx=x-700,dy=655-y,r=Math.hypot(dx,dy),theta=Math.abs(Math.atan2(dx,dy));
   value=r<610&&r>45&&theta<1.02?49+(random()-.5)*63+Math.sin(r*.052+phase)*9:3;
  }else if(Math.abs(x-nadir)<(spec.id==='coverage'?38:18))value=7+random()*5;
  const i=(py*width+px)*4;pixels.data[i]=Math.max(0,value*tint[0]);pixels.data[i+1]=Math.max(0,value*tint[1]);pixels.data[i+2]=Math.max(0,value*tint[2]);pixels.data[i+3]=255;
 }
 ctx.putImageData(pixels,0,0);ctx.scale(scale,scale);
 const contacts:{box:number[],label:string,score:number}[]=[];
 const add=(b:number[],label:string)=>contacts.push({box:b.map(n=>n*scale),label,score:.55+random()*.4});
 function object(x:number,y:number,w:number,h:number,shape='oval',label='Object-like return',contact=true){
  ctx.save();ctx.translate(x,y);ctx.fillStyle='#03131bd9';ctx.beginPath();ctx.ellipse(w*1.15,h*.8,w*1.65,h*.8,.15,0,Math.PI*2);ctx.fill();
  const g=ctx.createLinearGradient(-w,-h,w,h);g.addColorStop(0,'#f0e9b9');g.addColorStop(.35,'#a8b9ad');g.addColorStop(1,'#304a54');ctx.fillStyle=g;
  if(shape==='angular'){ctx.beginPath();ctx.moveTo(-w,-h*.5);ctx.lineTo(w*.2,-h);ctx.lineTo(w,h*.4);ctx.lineTo(-w*.3,h);ctx.closePath();ctx.fill()}
  else if(shape==='coil'){ctx.strokeStyle='#ccd1a5';ctx.lineWidth=7;for(let i=0;i<3;i++){ctx.beginPath();ctx.ellipse(i*8,0,w*.7,h*.7,0,0,Math.PI*2);ctx.stroke()}}
  else {ctx.beginPath();ctx.ellipse(0,0,w*.75,h*.75,-.2,0,Math.PI*2);ctx.fill()}
  ctx.restore();if(contact)add([x-w-6,y-h-6,x+w+24,y+h+7],label);
 }
 const offset=(random()-.5)*100;
 if(spec.id==='pipeline'){
  const x=250+offset,drift=60+random()*80;
  ctx.strokeStyle='#05121be8';ctx.lineWidth=39;ctx.beginPath();ctx.moveTo(x+28,70);ctx.lineTo(x+drift+34,596);ctx.stroke();
  ctx.strokeStyle='#c4ddcd';ctx.lineWidth=12;ctx.beginPath();ctx.moveTo(x,65);ctx.lineTo(x+drift,598);ctx.stroke();
  add([x-15,59,x+drift+18,610],'Pipe-like return');
  object(1000+offset,180,42,24,'angular');object(1120-offset,470,34,26);object(420-offset,470,30,22);
 }else if(spec.id==='wreck'){
  const x=260+offset,y=230+random()*90;ctx.save();ctx.translate(x,y);
  ctx.fillStyle='#020d17';ctx.beginPath();ctx.moveTo(30,40);ctx.lineTo(520,120);ctx.lineTo(740,270);ctx.lineTo(100,210);ctx.closePath();ctx.fill();
  ctx.fillStyle='#9eaead';ctx.strokeStyle='#e2e5c7';ctx.lineWidth=7;ctx.beginPath();ctx.moveTo(0,20);ctx.lineTo(55,-55);ctx.lineTo(340,-45);ctx.lineTo(465,10);ctx.lineTo(338,80);ctx.lineTo(48,88);ctx.closePath();ctx.fill();ctx.stroke();
  ctx.fillStyle='#30444e';ctx.fillRect(88,-25,233,78);ctx.strokeStyle='#b3c8bd';ctx.lineWidth=5;for(let i=0;i<7;i++){ctx.beginPath();ctx.moveTo(92+i*34,-40);ctx.lineTo(92+i*34,70);ctx.stroke()}
  ctx.fillStyle='#c0c9b8';ctx.fillRect(190,-15,53,47);ctx.restore();add([x-10,y-63,x+476,y+99],'Hull-like silhouette');object(940,160+offset,32,20,'angular','Fragment-like return');object(1100,470-offset,43,18,'angular','Fragment-like return');
 }else if(spec.id==='objects'){
  object(225+offset,185,45,31,'oval','Drum-like return');object(420,390-offset,55,42,'angular','Angular return');object(990-offset,175,65,40,'coil','Coil-like return');object(1140,440+offset,42,29,'oval','Drum-like return');object(850+offset,505,36,24,'angular');
 }else if(spec.id==='reef'){
  for(let i=0;i<24;i++){const x=100+random()*1150,y=90+random()*480,w=20+random()*45,h=15+random()*28;object(x,y,w,h,'angular','Rock-like return',i===5||i===14||i===20)}
 }else if(spec.id==='coverage'){
  const x=360+offset;ctx.strokeStyle='#b2cbd4';ctx.lineWidth=13;ctx.beginPath();ctx.moveTo(x,74);ctx.lineTo(x+250,610);ctx.stroke();
  add([x-15,67,x+268,620],'Interrupted linear return');object(1040+offset,170,40,23);object(1000-offset,520,35,26);
 }else{
  object(430+offset,220,32,20,'oval','Compact return');object(845-offset,195,37,25,'angular','Angular return');object(700+offset,420,28,18,'oval','Compact return');
  ctx.strokeStyle='#d9c16c44';ctx.lineWidth=1;for(const radius of [160,310,460,610]){ctx.beginPath();ctx.arc(700,655,radius,-Math.PI/2-1.02,-Math.PI/2+1.02);ctx.stroke()}
 }
 const regions:any[]=[];
 if(spec.id==='coverage')for(const [y,h]of [[215+offset,46],[414-offset,75]]){ctx.fillStyle='#020911';ctx.fillRect(0,y,1400,h);regions.push({flag:'simulated_dark_band',assessment:'Demo: inspect coverage and try a scan request',evidence:'Generated coverage interruption; not a diagnosed physical dropout.',box_xyxy_pixels:[0,y*scale,width,(y+h)*scale]})}
 ctx.fillStyle='#031a25dc';ctx.fillRect(16,15,350,32);ctx.fillStyle='#c1dcce';ctx.font='12px monospace';ctx.fillText('SIMULATED SONAR / INTERACTIVE DEMO',28,36);
 return {canvas:c,width,height,contacts,regions,spec,seed};
}
