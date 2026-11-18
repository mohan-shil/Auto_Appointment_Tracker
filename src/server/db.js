import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import Database from 'better-sqlite3';

const platformData=process.env.LOCALAPPDATA?path.join(process.env.LOCALAPPDATA,'AutoAppointmentTrackerV3'):process.platform==='darwin'?path.join(os.homedir(),'Library','Application Support','AutoAppointmentTrackerV3'):path.join(process.env.XDG_DATA_HOME||path.join(os.homedir(),'.local','share'),'AutoAppointmentTrackerV3');
export const ROOT=process.env.V3_DATA_DIR||platformData;
fs.mkdirSync(ROOT,{recursive:true,mode:0o700});
try{fs.chmodSync(ROOT,0o700);}catch{}
export const db=new Database(path.join(ROOT,'metadata.sqlite'));
try{fs.chmodSync(path.join(ROOT,'metadata.sqlite'),0o600);}catch{}
db.pragma('journal_mode = WAL');
db.exec(`CREATE TABLE IF NOT EXISTS documents(slot INTEGER PRIMARY KEY, name TEXT NOT NULL, path TEXT NOT NULL, size INTEGER NOT NULL, updated_at TEXT NOT NULL); CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, type TEXT NOT NULL, message TEXT NOT NULL, created_at TEXT NOT NULL);`);
export function saveDocumentMeta(doc){db.prepare('INSERT OR REPLACE INTO documents VALUES(?,?,?,?,?)').run(doc.slot,doc.name,doc.path,doc.size,new Date().toISOString());}
export function deleteDocumentMeta(slot){db.prepare('DELETE FROM documents WHERE slot=?').run(slot);}
export function listDocumentMeta(){return db.prepare('SELECT slot,name,size,updated_at as updatedAt FROM documents ORDER BY slot').all();}
export function listDocumentRecords(){return db.prepare('SELECT slot,name,path,size FROM documents ORDER BY slot').all();}
export function addEvent(type,message){db.prepare('INSERT INTO events(type,message,created_at) VALUES(?,?,?)').run(type,message,new Date().toISOString());}
