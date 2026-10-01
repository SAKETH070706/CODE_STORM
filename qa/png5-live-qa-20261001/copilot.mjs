export default async function(qa) {
  const linkCount=await qa.page.getByRole('button',{name:/AI Copilot/}).count()+await qa.page.getByRole('link',{name:/AI Copilot/}).count();
  qa.record('COPILOT-01','Inspect governor navigation for Copilot switcher','Copilot hidden per selected preference',{switcherCount:linkCount},linkCount===0?'PASS':'FAIL');
  // Explicit direct-route diagnostic, not a claim that a missing switcher was clicked.
  await qa.page.goto('http://localhost:5173/?legacy');
  await qa.page.getByPlaceholder('Ask a question or enter a task prompt...').waitFor();
  qa.record('COPILOT-02','Open retained legacy route directly','Render retained layout and inspect retrieval label',{url:qa.page.url(),label:await qa.page.getByText('AI Copilot Mode (Pinecone RAG + Multimodal)',{exact:true}).innerText(),actualImplementation:'backend/core/rag.py Chroma PersistentClient; backend/config.py CHROMA_DIR'},'FAIL',[await qa.shot('21-copilot-layout')],{severity:'Low',cause:'Retained UI labels Pinecone while configured implementation is ChromaDB.'});
  const prompt='What does the synthetic sales report workflow do?';
  await qa.page.getByPlaceholder('Ask a question or enter a task prompt...').fill(prompt);
  const response=await qa.clickResponse('POST','/api/process',()=>qa.page.getByRole('button',{name:/^Send/}).click());
  await qa.page.getByRole('button',{name:/^Send/}).waitFor();
  qa.record('COPILOT-03','Submit benign query in retained UI','A configured backend response or explicit setup limitation',{response,inputPreserved:await qa.page.getByPlaceholder('Ask a question or enter a task prompt...').inputValue()===prompt,snapshot:await qa.snapshot()},response.status===404?'BLOCKED':response.status===200?'PASS':'FAIL',[await qa.shot('22-copilot-query-error')],{category:'Missing runtime route/service',cause:'Running workspace application does not expose /api/process; live provider/retrieval not reached.'});
  await qa.page.getByRole('button',{name:/Switch to PNG5 Governor Workspace/}).click();await qa.idle();
  const session=(await qa.api('GET','/api/session')).data;
  qa.record('COPILOT-04','Click switch-back from legacy UI','Original governor session and workspace retained',{url:qa.page.url(),session,heading:await qa.page.locator('h1').innerText()},session.organization_id===qa.state.session.organization_id?'PASS':'FAIL',[await qa.shot('23-governor-return')]);
}
