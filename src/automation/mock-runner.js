import { CalendarEngine, selectFirstValidTimeSlot } from '../calendar/engine.js';

function dateAfter(days){const d=new Date();d.setHours(0,0,0,0);d.setDate(d.getDate()+days);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
function scenarios(){const d1=dateAfter(1),d2=dateAfter(2),d3=dateAfter(3);return {
  none:{dates:[d1,d2],available:[]}, second:{dates:[d1,d2],available:[d2]},last:{dates:[d1,d2,d3],available:[d3]},
  changing:{dates:[d1],available:[d3],updates:[d2,d3]},expired:{dates:[d1],available:[d1],expired:true},
  navigation_failure:{dates:[],available:[],navigationFailure:true},popup:{dates:[],available:[],popup:true},payment:{dates:[d1],available:[d1],payment:true}
};}
export class MockWorkflowRunner {
  constructor(controller,{intervalMs=1000,maxCycles=2,onEvent=()=>{},waitForManualLogin=null}={}) { this.controller=controller; this.intervalMs=intervalMs; this.maxCycles=maxCycles; this.onEvent=onEvent; this.waitForManualLogin=waitForManualLogin; this.cancelled=false; this.paused=false; this.finished=false; this.engine=new CalendarEngine({intervalMs}); this.attempts=[]; }
  async waitInterval(){let elapsed=0;while(elapsed<this.intervalMs&&!this.cancelled){if(this.paused){await new Promise(resolve=>{this.resumeWaiter=resolve;});continue;}await new Promise(r=>setTimeout(r,20));elapsed+=20;}return !this.cancelled;}
  async run(scenarioName='second') {
    const s=scenarios()[scenarioName]; if(!s) throw new Error('Unknown mock scenario.');
    this.cancelled=false;this.paused=false;this.finished=false;
    const emit=e=>{this.onEvent(e);this.controller.emit('activity',e);};
    if(this.controller.state==='IDLE'||this.controller.state==='STOPPED'||this.controller.state==='ERROR') this.controller.start();
    this.controller.transition('WAITING_FOR_LOGIN','Waiting for manual mock login'); emit({type:'login-required'});
    if(this.waitForManualLogin)await Promise.race([this.waitForManualLogin(),new Promise(resolve=>{this.cancelLogin=resolve;})]);
    if(this.cancelled)return;
    this.controller.transition('AUTHENTICATED','Mock authentication confirmed');
    if(s.expired){this.finished=true;this.paused=true;this.controller.pause('Session expired; log in manually');emit({type:'session-expired'});return;}
    if(s.navigationFailure){this.finished=true;this.controller.recover('Mock navigation error');this.controller.pause('Navigation failed; retry only after review');return;}
    if(s.popup){this.finished=true;this.controller.pause('Unexpected mock popup; applicant review required');emit({type:'unexpected-popup'});return;}
    this.controller.transition('WORKFLOW_DETECTION','Mock appointment workflow detected');
    this.controller.transition('DOCUMENT_STEP','Mock Webfile upload step');
    if(s.payment){this.controller.paymentReached();emit({type:'payment-reached'});return;}
    this.controller.transition('CALENDAR_STEP','Mock calendar step');
    let dates=[...s.dates], updates=[...(s.updates||[])], updated=false, cycle=1;
    while(!this.cancelled){
      const next=this.engine.next(dates,new Date());
      if(!next){if(!updated&&updates.length){dates.push(...updates);updates=[];updated=true;emit({type:'calendar-changed',dates:this.engine.refresh(dates,new Date())});continue;}if(cycle<this.maxCycles){cycle++;this.engine=new CalendarEngine({intervalMs:this.intervalMs});emit({type:'cycle-restarted',cycle});continue;}break;}
      this.currentDate=next;
      emit({type:'date-attempt',date:next,cycle}); if(!await this.waitInterval())return;
      const available=s.available.includes(next); this.engine.record(next,available?'available':'unavailable'); this.attempts.push({date:next,result:available?'available':'unavailable',cycle}); emit({type:'date-result',date:next,result:available?'available':'unavailable',cycle});
      this.currentDate=null;
      if(available){this.finished=true;this.selectedTimeSlot=selectFirstValidTimeSlot([{value:'09:00',available:true},{value:'10:00',available:true}]);this.controller.transition('TIME_SLOT_STEP',`First valid mock time slot selected: ${this.selectedTimeSlot}`);emit({type:'time-slot-selected',date:next,slot:this.selectedTimeSlot});this.controller.paymentReached();emit({type:'payment-reached'});return;}
    }
    if(!this.cancelled){this.finished=true;this.controller.pause('No available mock dates in current calendar.');emit({type:'calendar-exhausted'});}
  }
  pause(){if(this.cancelled||this.paused)return;this.paused=true;this.controller.pause();}
  resume(){if(!this.paused||this.finished)return false;this.paused=false;if(this.controller.state==='PAUSED')this.controller.resume();this.resumeWaiter?.();this.resumeWaiter=null;return true;}
  stop(){this.cancelled=true;this.paused=false;this.resumeWaiter?.();this.cancelLogin?.();this.controller.stop();}
}
export const MOCK_SCENARIOS=Object.keys(scenarios());
