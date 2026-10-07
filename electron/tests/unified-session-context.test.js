const {test} = require('node:test')
const assert = require('node:assert/strict')
const fs = require('node:fs'), vm = require('node:vm'), path = require('node:path')
const scope = vm.createContext({})
vm.runInContext(fs.readFileSync(path.join(__dirname, '../../apps/web/js/unified-session.js'), 'utf8'), scope)
const {UnifiedSessionContext} = scope

test('Terraform concurrency resolves the observed lock homophone without changing logging questions', () => {
 const context = new UnifiedSessionContext()
 const spoken = 'Two engineers run Terraform at the same time and encounter a state log. What should they do?'
 context.observe({text:spoken,source:'mic'})
 assert.match(context.interpretSpeech(spoken), /encounter a state lock/)
 assert.equal(context.turns[0].text, spoken)
 const logs = 'How do we inspect the Terraform state log for concurrent runs?'
 assert.equal(context.interpretSpeech(logs), logs)
})

test('speech from both sources and commitments remain available during answer generation', () => {
 let now = 1000
 const context = new UnifiedSessionContext(() => now)
 context.observe({type:'utterance',source:'system',text:'We decided to use Redis.',session_id:'s',utterance_id:1})
 context.observe({type:'utterance',source:'mic',text:'I will send the benchmark on Friday.',session_id:'m',utterance_id:1})
 assert.equal(context.turns.length, 2)
 assert.equal(context.ledger.length, 2)
 assert.match(context.prompt('Why that choice?'), /We decided to use Redis/)
 assert.equal(context.observe({type:'utterance',source:'system',text:'Duplicate',session_id:'s',utterance_id:1}), false)
 assert.equal(context.turns.length, 2)
})
test('partials are provisional and never become saved decisions', () => {
 const context = new UnifiedSessionContext()
 context.observe({type:'partial',source:'system',text:'We decided to'})
 assert.equal(context.turns.length, 0)
 assert.equal(context.ledger.length, 0)
 assert.equal(context.export().partials, undefined)
})
test('an interrupting question can use ongoing candidate speech without saving it as a final transcript', () => {
 let now=1000;const context=new UnifiedSessionContext(()=>now)
 context.observe({type:'partial',source:'tab',text:'I would roll back the application while preserving the database changes.'})
 assert.match(context.prompt('What if the migration cannot be reversed?'),/preserving the database changes/)
 assert.equal(context.transcript.length,0)
 now+=5001
 assert.doesNotMatch(context.prompt('What if the migration cannot be reversed?'),/preserving the database changes/)
})
test('long sessions retain bounded speech and retrieve relevant older context', () => {
 let now = 1000
 const context = new UnifiedSessionContext(() => now)
 context.observe({text:'We chose Kafka for event delivery.',source:'system'})
 now += 181000
 context.observe({text:'The new topic is budgeting.',source:'mic'})
 assert.equal(context.workingContext('What about Kafka?').conversation.length, 2)
 assert.equal(context.workingContext('What about budgeting?').conversation.length, 1)
 for (let i=0; i<500; i++) context.observe({text:'x'.repeat(6000),source:'system'})
 assert.ok(context.turns.length <= 200)
 assert.ok(context.turns.reduce((n,t)=>n+t.text.length,0) <= 32000)
})
test('saved context excludes screenshots and expires stale screen observations', () => {
 let now = 1000
 const context = new UnifiedSessionContext(() => now)
 context.observe({text:'Please send the notes.',source:'system'})
 context.setScreen({text:'Terminal error',image:'private-image'})
 assert.equal(context.export().screen, undefined)
 assert.equal(context.workingContext().screen.text, 'Terminal error')
 now += 15001
 assert.equal(context.workingContext().screen, null)
 const restored = new UnifiedSessionContext(() => now)
 restored.restore(context.export())
 assert.equal(restored.turns[0].source, 'remote')
 assert.equal(restored.turns[0].at, 1000)
 assert.equal(restored.ledger[0].text, 'Please send the notes.')
 restored.reset()
 assert.equal(restored.turns.length, 0)
})
test('thumbnail diff suppresses noise and recognizes changed frames', () => {
 const original = new Uint8Array(100)
 assert.equal(UnifiedSessionContext.changed(null, original), true)
 assert.equal(UnifiedSessionContext.changed(original, new Uint8Array(100).fill(10)), false)
 const changed = new Uint8Array(100); changed.set([100,100,100])
 assert.equal(UnifiedSessionContext.changed(original, changed), true)
})

test('older source quotations survive working-buffer eviction and history reload', () => {
 const context = new UnifiedSessionContext()
 context.observe({text:'We chose Kafka for delivery.',source:'system'})
 for(let i=0;i<40;i++) context.observe({text:'Other discussion '.repeat(350),source:'mic'})
 assert.ok(context.episodes.length > 0 && context.episodes.length <= 30)
 assert.match(context.prompt('Going back to Kafka, why?'),/We chose Kafka/)
 const restored = new UnifiedSessionContext()
 restored.restore(context.export())
 assert.match(restored.prompt('Going back to Kafka, why?'),/We chose Kafka/)
 assert.doesNotThrow(()=>restored.restore({version:1,turns:[{text:''},{}]}))
})

test('DevOps speech normalization is explicit and never fabricates acronym expansions',()=>{
 const context=new UnifiedSessionContext()
 context.observe({source:'system',text:'Do you know Kubernetes, Docker, and CI/CD pipelines?'})
 assert.equal(context.interpretSpeech('C I C D pipeline'),'CI/CD pipeline')
 assert.match(context.interpretSpeech('CACD pipeline'),/assuming you mean CI\/CD/)
 assert.match(context.interpretSpeech('C E C A').clarification,/Did you mean CI\/CD/)
 assert.equal(new UnifiedSessionContext().interpretSpeech('CECA'),'CECA')
})
test('general technology questions exclude unrelated screen text even with a wrapped resume prompt',()=>{
 const context=new UnifiedSessionContext()
 context.observe({text:'Explain Kubernetes.',source:'system'})
 context.setScreen({text:'Unrelated architecture document'})
 assert.doesNotMatch(context.prompt('Resume instructions mention a screenshot. Explain Kubernetes.','Explain Kubernetes.'),/Unrelated architecture document/)
 assert.match(context.prompt('Explain this error.'),/Unrelated architecture document/)
})
test('saved participant transcript outlives working context and excludes assistant entries', () => {
 const context = new UnifiedSessionContext()
 for(let i=0;i<240;i++) context.observe({type:'utterance',source:i%2?'system':'mic',text:`Participant line ${i}`})
 const saved=context.export()
 assert.equal(saved.turns.length,200)
 assert.equal(saved.transcript.length,240)
 saved.transcript.push({source:'assistant',text:'AI answer must not appear'})
 const restored=new UnifiedSessionContext()
 restored.restore(saved)
 assert.equal(restored.transcript.length,240)
 assert.equal(restored.transcript[0].text,'Participant line 0')
 assert.ok(!restored.transcript.some(t=>t.text.includes('AI answer')))
})
