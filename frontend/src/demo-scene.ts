/** Publicly attributable real sonar samples; no procedural image generator. */
import catalog from '../public/real-demo/catalog.json';
export const REAL_DEMO_SAMPLES=catalog;
export const DEMO_SCENARIOS=catalog.filter(s=>s.id!=='noaa0');
export function nextDemoScenario(current?:string,seed=crypto.getRandomValues(new Uint32Array(1))[0]){
 const choices=DEMO_SCENARIOS.filter(s=>s.id!==current);return choices[seed%choices.length].id;
}
