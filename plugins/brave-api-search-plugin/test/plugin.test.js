import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createClient} from '../client.js';
import plugin,{registerTools} from '../index.js';
const json=data=>new Response(JSON.stringify(data),{headers:{'Content-Type':'application/json'}});
const sample={query:{original:'hello'},web:{results:[{title:'Hello',url:'https://example.com',description:'World'}]},results:[{query:'hello world'}]};
test('SDK entry and four tools; errors are recoverable',async()=>{
 assert.equal(plugin.id,'brave-api-search-plugin'); const tools=[];
 registerTools({registerTool:t=>tools.push(t),pluginConfig:{}},{env:{},fetchImpl:()=>{throw new Error('must not fetch');}});
 assert.deepEqual(tools.map(t=>t.name),['brave_search','brave_suggest','brave_spellcheck','brave_answers']);
 for(const t of tools){assert.equal((await t.execute('id',{query:'hello'})).isError,true);assert.equal((await t.execute('id',{query:''})).isError,true);}
 assert.equal((await tools[0].execute('id',{query:'x',count:21})).isError,true);
});
test('search maps options including zero coordinates and summary with web-only filter',async()=>{
 const calls=[];const client=createClient({searchApiKey:'search'},{env:{},fetchImpl:async(u,o)=>{calls.push([u,o]);return json(calls.length===1 ? {...sample,summarizer:{key:'sum'}} : {summary:[{data:'Summary'}]});}});
 const out=await client.search({query:'hello',count:3,offset:2,country:'de',lat:0,long:0,summary:true,result_filter:'web',extra_snippets:true,spellcheck:false,text_decorations:false,search_lang:'de',ui_lang:'de-DE',freshness:'pw',units:'metric'});
 assert.equal(calls.length,2);assert.equal(calls[0][0].searchParams.get('q'),'hello'); assert.equal(calls[0][0].searchParams.get('offset'),'2');assert.equal(calls[0][0].searchParams.get('extra_snippets'),'1');assert.equal(calls[0][1].headers['x-loc-lat'],'0');assert.equal(calls[0][1].headers['X-Subscription-Token'],'search');assert.ok(out.details.summary);assert.match(out.text,/Hello/);
});
test('suggest key precedence, cache parameters and expiration',async()=>{
 let time=0;const calls=[];const c=createClient({}, {env:{AUTOSUGGEST_API_KEY:'first',BRAVE_AUTOSUGGEST_API_KEY:'second',BRAVE_SEARCH_API_KEY:'third'},now:()=>time,fetchImpl:async(u,o)=>{calls.push([u,o]);return json(sample);}});
 assert.equal((await c.suggest({query:'hello',rich:true})).details.cached,false); assert.equal((await c.suggest({query:'hello',rich:true})).details.cached,true);
 assert.equal(calls[0][1].headers['X-Subscription-Token'],'first');assert.equal(calls[0][0].searchParams.get('rich'),'true');
 await c.suggest({query:'hello',count:2,rich:true});time=60001;await c.suggest({query:'hello',rich:true});assert.equal(calls.length,3);
});
test('spellcheck dedicated key and search fallback',async()=>{
 for(const env of [{BRAVE_SPELLCHECK_API_KEY:'dedicated',BRAVE_SEARCH_API_KEY:'search'},{BRAVE_SEARCH_API_KEY:'search'}]){
 const c=createClient({}, {env,fetchImpl:async(u,o)=>{assert.equal(o.headers['X-Subscription-Token'],env.BRAVE_SPELLCHECK_API_KEY || 'search');assert.equal(u.pathname,'/res/v1/spellcheck/search');return json(sample);}});
 assert.match((await c.spellcheck({query:'hello'})).text,/Did you mean/);
 }
});
test('retries 429 Retry-After, 5xx, network failure; does not retry 401',async()=>{
 let count=0;const delays=[];const c=createClient({searchApiKey:'x'},{env:{},sleep:async ms=>delays.push(ms),fetchImpl:async()=>{count++;if(count===1)return new Response('',{status:429,headers:{'retry-after':'2'}});if(count===2)return new Response('',{status:503});if(count===3)throw new Error('network');return json(sample);}});
 await c.search({query:'x'});assert.deepEqual(delays,[2000,1000,2000]);assert.equal(count,4);
 let attempts=0;const failure=createClient({searchApiKey:'secret'},{fetchImpl:async()=>{attempts++;return new Response('secret',{status:401});}});
 await assert.rejects(failure.search({query:'x'}),/HTTP 401/);assert.equal(attempts,1);
});
test('Answers reconstructs UTF-8/SSE and tags across chunk boundaries, deduplicates sources, usage',async()=>{
 const content='Café <enum_item>{"name":"Paris","href":"https://paris.fr"}</enum_item><citation>{"url":"https://example.com","number":1}</citation><citation>{"url":"https://example.com","number":2}</citation><usage>{"X-Request-Total-Cost":"0.01"}</usage>';
 const events=[];for(let i=0;i<content.length;i+=7)events.push('data: '+JSON.stringify({choices:[{delta:{content:content.slice(i,i+7)}}]})+'\r\n\r\n');
 const bytes=new TextEncoder().encode(events.join('')+'data: [DONE]');
 const c=createClient({answersApiKey:'answer'},{env:{},fetchImpl:async(u,o)=>{const body=JSON.parse(o.body);assert.equal(body.extra_body.enable_research,true);assert.equal(body.extra_body.enable_entities,true);return new Response(new ReadableStream({start(controller){for(let i=0;i<bytes.length;i+=3)controller.enqueue(bytes.slice(i,i+3));controller.close();}}));}});
 const out=await c.answers({query:'Paris',enable_research:true,enable_entities:true});assert.equal(out.details.sources.length,1);assert.equal(out.details.entities[0].name,'Paris');assert.match(out.details.answer,/Café/);assert.ok(!out.text.includes('<citation>'));assert.equal(out.details.usage['X-Request-Total-Cost'],'0.01');
});
test('nonstreaming Answers and successful native tool return',async()=>{
 const tools=[];registerTools({pluginConfig:{answersApiKey:'key'},registerTool:t=>tools.push(t)},{env:{},fetchImpl:async()=>json({choices:[{message:{content:'Answer'}}],usage:{total_tokens:7}})});
 const result=await tools[3].execute('id',{query:'x',stream:false});assert.equal(result.details.answer,'Answer');assert.equal(result.content[0].type,'text');assert.equal(result.details.usage.total_tokens,7);
});
test('cancellation prevents request',async()=>{
 const controller=new AbortController();controller.abort();const c=createClient({searchApiKey:'key'},{fetchImpl:()=>{throw new Error('unexpected request');}});await assert.rejects(c.search({query:'x'},controller.signal),{name:'AbortError'});
});
test('suggest remaining fallback routes and configured key',async()=>{
 for(const [config,env,expected] of [[{}, {BRAVE_AUTOSUGGEST_API_KEY:'alias',BRAVE_SEARCH_API_KEY:'search'},'alias'],[{}, {BRAVE_SEARCH_API_KEY:'search'},'search'],[{searchApiKey:'configured-search'},{},'configured-search'],[{suggestApiKey:'configured-suggest'},{AUTOSUGGEST_API_KEY:'env'},'configured-suggest']]){
  const c=createClient(config,{env,fetchImpl:async(_u,o)=>{assert.equal(o.headers['X-Subscription-Token'],expected);return json(sample);}});await c.suggest({query:'x'});
 }
});
test('retry exhaustion and streaming errors return recoverable tool errors',async()=>{
 let attempts=0;const tools=[];registerTools({pluginConfig:{searchApiKey:'key',answersApiKey:'answer'},registerTool:t=>tools.push(t)},{env:{},sleep:async()=>{},fetchImpl:async()=>{attempts++;return new Response('',{status:503});}});
 assert.equal((await tools[0].execute('id',{query:'x'})).isError,true);assert.equal(attempts,4);
 const broken=[];registerTools({pluginConfig:{answersApiKey:'key'},registerTool:t=>broken.push(t)},{env:{},fetchImpl:async()=>new Response('data: {"error":{"message":"failure"}}\n\n')});assert.equal((await broken[3].execute('id',{query:'x'})).isError,true);
});
