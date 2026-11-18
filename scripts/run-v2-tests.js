import { existsSync } from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const root=path.resolve(import.meta.dirname,'..');
const venvPython=process.platform==='win32'?path.join(root,'.venv','Scripts','python.exe'):path.join(root,'.venv','bin','python');
let command,args;
if(existsSync(venvPython)){command=venvPython;args=['-m','pytest','-v'];}
else if(process.platform==='win32'){command='py';args=['-3','-m','pytest','-v'];}
else{command='python3';args=['-m','pytest','-v'];}
const result=spawnSync(command,args,{cwd:path.join(root,'legacy','v2'),stdio:'inherit'});
if(result.error){console.error('Could not start Python. Install legacy/v2/requirements.txt and a Python interpreter.');process.exit(1);}
process.exit(result.status??1);
