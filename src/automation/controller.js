import { EventEmitter } from 'node:events';

export const STATES = Object.freeze(['IDLE','BROWSER_STARTING','WAITING_FOR_LOGIN','AUTHENTICATED','WORKFLOW_DETECTION','DOCUMENT_STEP','CALENDAR_STEP','TIME_SLOT_STEP','PAUSED','RECOVERING','PAYMENT_REACHED','STOPPED','ERROR']);
const ALLOWED = {
  IDLE:['BROWSER_STARTING'], BROWSER_STARTING:['WAITING_FOR_LOGIN','ERROR','STOPPED'], WAITING_FOR_LOGIN:['AUTHENTICATED','PAUSED','STOPPED','ERROR'],
  AUTHENTICATED:['WORKFLOW_DETECTION','PAUSED','RECOVERING','STOPPED','ERROR'], WORKFLOW_DETECTION:['DOCUMENT_STEP','CALENDAR_STEP','TIME_SLOT_STEP','PAYMENT_REACHED','PAUSED','RECOVERING','ERROR','STOPPED'],
  DOCUMENT_STEP:['CALENDAR_STEP','PAYMENT_REACHED','PAUSED','RECOVERING','ERROR','STOPPED'], CALENDAR_STEP:['TIME_SLOT_STEP','PAYMENT_REACHED','PAUSED','RECOVERING','ERROR','STOPPED'],
  TIME_SLOT_STEP:['PAYMENT_REACHED','PAUSED','RECOVERING','ERROR','STOPPED'], PAUSED:['WAITING_FOR_LOGIN','AUTHENTICATED','WORKFLOW_DETECTION','DOCUMENT_STEP','CALENDAR_STEP','TIME_SLOT_STEP','RECOVERING','STOPPED','ERROR'],
  RECOVERING:['WORKFLOW_DETECTION','RECOVERING','PAUSED','ERROR','STOPPED'], PAYMENT_REACHED:['STOPPED'], STOPPED:['BROWSER_STARTING'], ERROR:['STOPPED','BROWSER_STARTING']
};

export class WorkflowController extends EventEmitter {
  constructor() { super(); this.state='IDLE'; this.step='Ready'; this.recoveries=0; this.events=[]; this.beforePause='WORKFLOW_DETECTION'; }
  transition(next, detail='') {
    if (!STATES.includes(next) || !ALLOWED[this.state]?.includes(next)) throw new Error(`Invalid state transition: ${this.state} -> ${next}`);
    this.state=next; this.step=detail || next; const event={state:next,step:this.step,at:new Date().toISOString()}; this.events.push(event); this.emit('change',event); return event;
  }
  start() { this.recoveries=0; return this.transition('BROWSER_STARTING'); }
  pause(reason='Paused by applicant') { if (this.state==='PAUSED') return; this.beforePause=this.state; return this.transition('PAUSED',reason); }
  resume() { return this.transition(this.beforePause==='WAITING_FOR_LOGIN'?'WAITING_FOR_LOGIN':this.beforePause,'Resumed'); }
  stop() { if (this.state!=='STOPPED') return this.transition('STOPPED','Stopped by applicant'); }
  paymentReached() { if (this.state!=='PAYMENT_REACHED') return this.transition('PAYMENT_REACHED','Payment stage reached; manual action required'); }
  recover(error) { if (this.recoveries>=3) { this.transition('ERROR','Recovery limit reached; manual intervention required'); return false; } this.recoveries++; this.transition('RECOVERING',`Recovery ${this.recoveries}/3`); this.emit('recovery',String(error)); return true; }
}
