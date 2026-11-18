export async function attachMockDocuments(page, documents) {
  let current;try{current=new URL(page?.url());}catch{}
  if(!current||current.protocol!=='http:'||!['127.0.0.1','localhost','::1'].includes(current.hostname)||current.pathname!=='/mock/book')throw new Error('Mock documents attach only on the mock upload step.');
  let count=0;
  for(const doc of documents){if(!doc)continue;await page.locator('input[type=file]').nth(doc.slot).setInputFiles(doc.path);count++;}
  return count;
}
