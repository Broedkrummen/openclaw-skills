const string = description => ({type:'string',description});
const boolean = (description, value) => ({type:'boolean',description,default:value});
const integer = (minimum,maximum,value) => ({type:'integer',minimum,maximum,default:value});
const enumeration = values => ({type:'string',enum:values});
const common={query:{type:'string',minLength:1,description:'Search query or question'},country:{type:'string',pattern:'^[A-Za-z]{2}$',description:'Two-letter country code'}};
export const schemas={
 search:{...common,count:integer(1,20,10),offset:integer(0,9,0),freshness:string('pd, pw, pm, py, or YYYY-MM-DDtoYYYY-MM-DD'),extra_snippets:boolean('Include additional excerpts',false),summary:boolean('Fetch AI summary',false),result_filter:string('Comma-separated result types: web,news,videos,discussions,faq,infobox,locations,query,summarizer'),search_lang:string('Search language'),ui_lang:string('UI locale'),safesearch:enumeration(['off','moderate','strict']),spellcheck:boolean('Enable spelling correction',true),spellcheck_info:boolean('Show spelling correction information',false),text_decorations:boolean('Preserve text highlights',true),units:enumeration(['metric','imperial']),lat:{type:'number',minimum:-90,maximum:90},long:{type:'number',minimum:-180,maximum:180},timezone:string('Local timezone'),city:string('Local city'),state:string('Local state'),postal_code:string('Local postal code')},
 suggest:{...common,count:integer(1,10,5),rich:boolean('Include rich metadata; requires appropriate Brave plan',false)},
 spellcheck:{...common},
 answers:{...common,enable_citations:boolean('Include source citations',true),enable_research:boolean('Enable multi-search research',false),enable_entities:boolean('Include entities',false),stream:boolean('Use Brave streaming response; required for full feature coverage',true)}
};
export function validate(kind,p) {
 if(!p || typeof p !== 'object' || Array.isArray(p)) throw new Error('Tool parameters must be an object.');
 for(const [key,value] of Object.entries(p)) {
  const s=schemas[kind][key]; if(!s) throw new Error(`Unknown parameter: ${key}`);
  if(s.type==='integer' ? !Number.isInteger(value) : typeof value !== s.type) throw new Error(`Invalid type for ${key}`);
  if(typeof value==='number' && (!Number.isFinite(value) || value<s.minimum || value>s.maximum)) throw new Error(`Out-of-range ${key}`);
  if(s.enum && !s.enum.includes(value)) throw new Error(`Invalid ${key}`);
  if(s.pattern && !new RegExp(s.pattern).test(value)) throw new Error(`Invalid ${key}`);
 }
 if(typeof p.query !== 'string' || !p.query.trim()) throw new Error('query must be a nonempty string.');
 if(p.freshness && !/^(pd|pw|pm|py|\d{4}-\d{2}-\d{2}to\d{4}-\d{2}-\d{2})$/.test(p.freshness)) throw new Error('Invalid freshness filter.');
 if(p.result_filter && p.result_filter.split(',').some(v=>!['web','news','videos','discussions','faq','infobox','locations','query','summarizer'].includes(v.trim()))) throw new Error('Invalid result_filter.');
}
