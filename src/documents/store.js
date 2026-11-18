import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';

export const MAX_BYTES = 15 * 1024 * 1024;
const platformData = process.env.LOCALAPPDATA ? path.join(process.env.LOCALAPPDATA,'AutoAppointmentTrackerV3') : process.platform === 'darwin' ? path.join(os.homedir(),'Library','Application Support','AutoAppointmentTrackerV3') : path.join(process.env.XDG_DATA_HOME||path.join(os.homedir(),'.local','share'),'AutoAppointmentTrackerV3');
export const DATA_DIR = process.env.V3_DATA_DIR || platformData;
export class DocumentStore {
  constructor(root=DATA_DIR) { this.root=root; this.docs=Array(4).fill(null); }
  async restore(records) { const allowed=path.resolve(this.root,'documents');for(const rec of records){if(rec.slot<0||rec.slot>3)continue;try{const target=path.resolve(rec.path);if(path.dirname(target)!==allowed)continue;await fs.access(target);this.docs[rec.slot]={slot:rec.slot,name:path.basename(rec.name),size:rec.size,path:target,valid:true};}catch{}} }
  async init() { await fs.mkdir(path.join(this.root,'documents'),{recursive:true,mode:0o700}); try { await fs.chmod(this.root,0o700); await fs.chmod(path.join(this.root,'documents'),0o700); } catch {} }
  async save(slot, originalName, bytes) {
    if (!Number.isInteger(slot)||slot<0||slot>3) throw new Error('Choose one of four applicant slots.');
    if (slot===0 && !bytes?.length) throw new Error('Primary applicant PDF is required.');
    if (!Buffer.isBuffer(bytes)||!bytes.length||bytes.length>MAX_BYTES||!bytes.subarray(0,1024).includes(Buffer.from('%PDF-'))) throw new Error('Choose a valid PDF under 15 MB.');
    await this.init(); const name=`${crypto.randomUUID()}.pdf`, file=path.join(this.root,'documents',name);
    await fs.writeFile(file,bytes,{flag:'wx',mode:0o600});
    if (this.docs[slot]) await fs.rm(this.docs[slot].path,{force:true});
    this.docs[slot]={slot,name:path.basename(originalName),size:bytes.length,path:file,valid:true}; return this.docs[slot];
  }
  async remove(slot) { if (this.docs[slot]) await fs.rm(this.docs[slot].path,{force:true}); this.docs[slot]=null; }
  async clear() { await Promise.all(this.docs.map((_,i)=>this.remove(i))); }
  list() { return this.docs.map(d=>d&&({slot:d.slot,name:d.name,size:d.size,valid:d.valid})); }
}
