/** Publicly attributable real sonar samples; no procedural image generator. */
import catalog from '../public/real-demo/catalog.json';
export const DEMO_SCENARIOS=catalog;
export function nextDemoScenario(current?:string,seed=crypto.getRandomValues(new Uint32Array(1))[0]){
 const choices=DEMO_SCENARIOS.filter(s=>s.id!==current);return choices[seed%choices.length].id;
}
