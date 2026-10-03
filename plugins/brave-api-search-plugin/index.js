import { definePluginEntry } from 'openclaw/plugin-sdk/plugin-entry';
import { createClient } from './client.js';
import { schemas, validate } from './schemas.js';
const descriptions={search:'Search the web with Brave. Returns ranked links and excerpts, optional AI summary and additional result types.',suggest:'Get Brave query autocomplete suggestions, optionally with rich metadata.',spellcheck:'Get Brave spelling corrections for a search query.',answers:'Get an AI answer grounded in live Brave search, with citations, optional entities and multi-search research.'};
export function registerTools(api, dependencies) {
 const client=createClient(api.pluginConfig ?? {},dependencies);
 for(const kind of Object.keys(schemas)) api.registerTool({
  name:'brave_'+kind,label:'Brave '+kind,description:descriptions[kind],
  parameters:{type:'object',properties:schemas[kind],required:['query'],additionalProperties:false},
  async execute(_id,params,signal) {
   try {validate(kind,params); const result=await client[kind](params,signal);return {content:[{type:'text',text:result.text}],details:result.details};}
   catch(error) {const text=error instanceof Error ? error.message : 'Brave request failed';return {isError:true,content:[{type:'text',text}],details:{error:text}};}
  }
 });
}
export default definePluginEntry({id:'brave-api-search-plugin',name:'Brave API Search',description:'Four native Brave Search API tools, converted from Broedkrummen’s brave-api-search skill v4.2.0.',register:registerTools});
