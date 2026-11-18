import { describe,it,expect,afterEach } from 'vitest';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { DocumentStore } from '../../src/documents/store.js';

describe('local PDF storage',()=>{
  const roots=[];afterEach(async()=>{await Promise.all(roots.splice(0).map(p=>fs.rm(p,{recursive:true,force:true})));});
  it('validates, persists outside the repository, replaces and deletes synthetic PDFs',async()=>{
    const root=await fs.mkdtemp(path.join(os.tmpdir(),'ivac-v3-test-'));roots.push(root);const store=new DocumentStore(root);const bytes=Buffer.from('%PDF-1.7\nsynthetic\n%%EOF');
    const doc=await store.save(0,'synthetic-primary.pdf',bytes);expect(await fs.readFile(doc.path)).toEqual(bytes);expect(doc.path).not.toContain(process.cwd());
    await expect(store.save(1,'bad.pdf',Buffer.from('not pdf'))).rejects.toThrow();
    const replacement=await store.save(0,'replacement.pdf',bytes);expect(await fs.stat(doc.path).catch(()=>null)).toBeNull();expect(replacement.name).toBe('replacement.pdf');
    await store.remove(0);expect(store.list()[0]).toBeNull();
  });
  it('restores a saved slot from local metadata while rejecting paths outside its managed folder',async()=>{const root=await fs.mkdtemp(path.join(os.tmpdir(),'ivac-v3-restore-'));roots.push(root);const first=new DocumentStore(root);const doc=await first.save(0,'synthetic.pdf',Buffer.from('%PDF-1.7\nprivate bytes'));const restored=new DocumentStore(root);await restored.restore([{slot:0,name:'synthetic.pdf',size:doc.size,path:doc.path},{slot:1,name:'outside.pdf',size:1,path:path.join(root,'private.pdf')}]);expect(restored.list()[0].name).toBe('synthetic.pdf');expect(restored.list()[1]).toBeNull();});
});
