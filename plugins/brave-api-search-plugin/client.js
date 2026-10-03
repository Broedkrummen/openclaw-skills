import * as fmt from './formatters.js';
const BASE = 'https://api.search.brave.com/res/v1';
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
export function createClient(config = {}, { env = process.env, fetchImpl = globalThis.fetch, sleep = pause, now = Date.now } = {}) {
  const cache = new Map();
  function key(kind) {
    const search = config.searchApiKey || env.BRAVE_SEARCH_API_KEY;
    const value = ({search, answers: config.answersApiKey || env.BRAVE_ANSWERS_API_KEY,
      suggest: config.suggestApiKey || env.AUTOSUGGEST_API_KEY || env.BRAVE_AUTOSUGGEST_API_KEY || search,
      spellcheck: config.spellcheckApiKey || env.BRAVE_SPELLCHECK_API_KEY || search})[kind];
    if (!value) throw new Error(`Missing Brave ${kind} API key. Configure the plugin credentials or corresponding environment variable.`);
    return value;
  }
  async function request(path, params, credential, { body, headers = {}, signal } = {}) {
    const url = new URL(BASE + path);
    for (const [k,v] of Object.entries(params)) if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, String(v));
    for (let attempt = 0; ; attempt++) {
      signal?.throwIfAborted();
      let res;
      try {
        res = await fetchImpl(url, { method: body ? 'POST' : 'GET', headers: { Accept: body?.stream ? 'text/event-stream' : 'application/json', 'X-Subscription-Token': credential, ...(body ? {'Content-Type':'application/json'} : {}), ...headers }, ...(body ? { body: JSON.stringify(body) } : {}), signal: signal ? AbortSignal.any([signal, AbortSignal.timeout(120000)]) : AbortSignal.timeout(120000) });
      } catch (error) {
        if (signal?.aborted || attempt >= 3) throw error;
        await sleep(500 * 2 ** attempt); continue;
      }
      if ((res.status === 429 || res.status >= 500) && attempt < 3) {
        const retry = res.headers.get('retry-after');
        const delay = retry ? (Number.isFinite(Number(retry)) ? Number(retry)*1000 : Date.parse(retry)-now()) : res.status === 429 ? 5000 : 500*2**attempt;
        await res.body?.cancel();
        await sleep(Math.max(0, Math.min(Number.isFinite(delay) ? delay : 5000, 60000))); continue;
      }
      if (!res.ok) throw new Error(`Brave API returned HTTP ${res.status}. Check credentials, plan access, and quota.`);
      return res;
    }
  }
  const get = async (path, params, credential, options) => (await request(path, params, credential, options)).json();
  async function search(p, signal) {
    const headers = {};
    for (const [param, header] of Object.entries({lat:'lat',long:'long',timezone:'timezone',city:'city',state:'state',country:'country',postal_code:'postal-code'})) if (p[param] !== undefined) headers['x-loc-'+header] = String(p[param]);
    const data = await get('/web/search', {q:p.query,count:p.count ?? 10,country:p.country ?? 'us',offset:p.offset ?? 0,freshness:p.freshness,result_filter:p.result_filter,search_lang:p.search_lang,ui_lang:p.ui_lang,safesearch:p.safesearch ?? 'moderate',spellcheck:p.spellcheck === false ? 'false' : undefined,text_decorations:p.text_decorations === false ? 'false' : undefined,extra_snippets:p.extra_snippets ? '1' : undefined,summary:p.summary ? '1' : undefined,units:p.units},key('search'),{headers,signal});
    const parts = [fmt.formatResults(data,p.extra_snippets,p.text_decorations !== false,p.spellcheck_info)];
    for (const fn of ['formatDiscussions','formatFAQ','formatInfobox','formatNews','formatVideos']) { const text=fmt[fn](data); if(text) parts.push(text); }
    let summary;
    if(p.summary && data.summarizer?.key) {
      summary=await get('/summarizer/search',{key:data.summarizer.key,inline_references:'true'},key('search'),{headers,signal});
      parts.push('**AI Summary:**\n'+fmt.formatSummary(summary));
    }
    return {text:parts.join('\n\n'),details:{...data,...(summary ? {summary} : {})}};
  }
  async function suggest(p, signal) {
    const credential=key('suggest');
    const params={q:p.query,count:p.count ?? 5,country:(p.country ?? 'US').toUpperCase(),...(p.rich ? {rich:'true'} : {})};
    const id=JSON.stringify(params); const entry=cache.get(id);
    if(entry && entry.expires>now()) return {text:fmt.formatSuggestions(entry.data,p.rich),details:{...entry.data,cached:true}};
    const data=await get('/suggest/search',params,credential,{signal});
    // Bound cache size and keep it scoped to this plugin instance.
    if(cache.size>=256) cache.delete(cache.keys().next().value);
    cache.set(id,{data,expires:now()+60000});
    return {text:fmt.formatSuggestions(data,p.rich),details:{...data,cached:false}};
  }
  async function spellcheck(p, signal) {
    const data=await get('/spellcheck/search',{q:p.query,country:(p.country ?? 'US').toUpperCase()},key('spellcheck'),{signal});
    return {text:fmt.formatSpellcheck(data),details:data};
  }
  async function answers(p, signal) {
    const body={model:'brave',messages:[{role:'user',content:p.query}],stream:p.stream !== false,extra_body:{country:p.country ?? 'us',language:'en',enable_citations:p.enable_citations !== false,enable_research:p.enable_research ?? false,enable_entities:p.enable_entities ?? false}};
    const res=await request('/chat/completions',{},key('answers'),{body,signal});
    let content='',usage;
    if(body.stream) {
      if(!res.body) throw new Error('Brave Answers returned no stream.');
      const reader=res.body.getReader(), decoder=new TextDecoder(); let pending='';
      function consume(line) {
        if(!line.startsWith('data:')) return;
        const value=line.slice(5).trim(); if(!value || value==='[DONE]') return;
        const chunk=JSON.parse(value);
        if(chunk.error) throw new Error('Brave Answers returned a streaming error.');
        content+=chunk.choices?.[0]?.delta?.content ?? '';
        if(chunk.usage) usage=chunk.usage;
      }
      try {
        while(true) { signal?.throwIfAborted(); const {done,value}=await reader.read(); if(done) break;
          pending+=decoder.decode(value,{stream:true}); const lines=pending.split('\n'); pending=lines.pop(); for(const line of lines) consume(line.replace(/\r$/,''));
        }
        pending+=decoder.decode(); if(pending.trim()) consume(pending);
      } finally { await reader.cancel(); reader.releaseLock(); }
    } else { const data=await res.json(); content=data.choices?.[0]?.message?.content ?? ''; usage=data.usage; }
    const {sources}=fmt.parseCitations(content); sources.sort((a,b)=>(a.number ?? 0)-(b.number ?? 0));
    const entities=fmt.parseEntities(content);
    const usageTag=content.match(/<usage>([\s\S]*?)<\/usage>/); if(usageTag) {try {usage=JSON.parse(usageTag[1]);} catch { /* retain API usage */ }}
    const answer=content.replace(/<citation>[\s\S]*?<\/citation>/g,'').replace(/<usage>[\s\S]*?<\/usage>/g,'').replace(/<enum_item>([\s\S]*?)<\/enum_item>/g,(_m,json)=>{try {const e=JSON.parse(json);return e.href ? `[${e.original_tokens || e.name}](${e.href})` : e.original_tokens || e.name || '';} catch{return '';}}).trim();
    const text=[answer || 'No answer returned.',...(sources.length ? ['**Sources:**',...sources.map(s=>`${s.number ?? '?'}. [${s.title}](${s.url})`)] : []),...(entities.length ? ['**Entities mentioned:**',...entities.map(e=>e.href ? `[${e.name}](${e.href})` : e.name)] : []),...(usage ? ['**Usage:** '+JSON.stringify(usage)] : [])].join('\n');
    return {text,details:{answer,sources,entities,...(usage ? {usage} : {})}};
  }
  return {search,suggest,spellcheck,answers};
}
