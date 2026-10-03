function stripHtml(text) {
  if (!text) return '';
  return text
    .replace(/<[^>]+>/g, '')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .replace(/&#x27;/g, "'")
    .replace(/&#x2F;/g, '/')
    .replace(/&#39;/g, "'")
    .replace(/&quot;/g, '"')
    .trim();
}

// ─── Web results formatter ─────────────────────────────────────────────────────

function formatResults(data, extraSnippets, showDecorations, showSpellcheckInfo) {
  const results = data.web?.results || [];
  const q = data.query || {};
  const lines = [];

  if (showSpellcheckInfo && q.altered && q.altered !== q.original) {
    lines.push(`🔍 Query corrected: "${q.original}" → "${q.altered}"\n`);
  }

  if (results.length === 0) {
    lines.push('No web results found.');
    return lines.join('\n');
  }

  lines.push(`Found ${results.length} web result(s) for: ${q.original || ''}`);
  if (q.more_results_available) lines.push(` *(More results — increase the offset parameter)*`);
  lines.push('');

  for (let i = 0; i < results.length; i++) {
    const r = results[i];
    const title = showDecorations ? (r.title || '') : stripHtml(r.title);
    const desc  = showDecorations ? (r.description || '') : stripHtml(r.description);

    lines.push(`${i + 1}. **${title}**`);
    lines.push(`   URL: ${r.url}`);
    if (desc) lines.push(`   ${desc}`);
    if (extraSnippets && r.extra_snippets?.length) {
      lines.push('   Additional context:');
      for (const s of r.extra_snippets) {
        lines.push(`   - ${showDecorations ? s : stripHtml(s)}`);
      }
    }
    lines.push('');
  }

  return lines.join('\n');
}

// ─── Discussions formatter ────────────────────────────────────────────────────

function formatDiscussions(data) {
  const threads = data.discussions?.results || [];
  if (threads.length === 0) return null;

  const lines = ['## Discussions\n'];
  for (let i = 0; i < threads.length; i++) {
    const t = threads[i];
    lines.push(`${i + 1}. **${stripHtml(t.title || t.question || '')}**`);
    lines.push(`   URL: ${t.url}`);
    if (t.description) lines.push(`   ${stripHtml(t.description)}`);
    if (t.meta_url?.forum_name) lines.push(`   Source: ${t.meta_url.forum_name}`);
    lines.push('');
  }
  return lines.join('\n');
}

// ─── FAQ formatter ────────────────────────────────────────────────────────────

function formatFAQ(data) {
  const faqs = data.faq?.results || [];
  if (faqs.length === 0) return null;

  const lines = ['## FAQ\n'];
  for (let i = 0; i < faqs.length; i++) {
    const f = faqs[i];
    const title = stripHtml(f.title || f.question || '');
    lines.push(`${i + 1}. **${title}**`);
    if (f.url) lines.push(`   URL: ${f.url}`);
    const body = f.description || f.answer || '';
    if (body) lines.push(`   ${stripHtml(body)}`);
    lines.push('');
  }
  return lines.join('\n');
}

// ─── Infobox formatter ───────────────────────────────────────────────────────

function formatInfobox(data) {
  const entries = data.infobox?.results || [];
  if (entries.length === 0) return null;

  const lines = [];
  for (const entry of entries) {
    lines.push(`## ${stripHtml(entry.title || entry.name || 'Infobox')}\n`);
    if (entry.long_desc) {
      lines.push(`${stripHtml(entry.long_desc).slice(0, 500)}${entry.long_desc.length > 500 ? '…' : ''}\n`);
    } else if (entry.description) {
      lines.push(`${stripHtml(entry.description)}\n`);
    }
    if (entry.profiles?.length) {
      lines.push('**Profiles:**');
      for (const p of entry.profiles) lines.push(`- [${p.name}](${p.url})`);
    }
    if (entry.attributes?.length) {
      lines.push('**Attributes:**');
      for (const [key, val] of entry.attributes) {
        lines.push(`- **${stripHtml(key)}**: ${stripHtml(val)}`);
      }
    }
    lines.push('');
  }
  return lines.join('\n');
}

// ─── News formatter ───────────────────────────────────────────────────────────

function formatNews(data) {
  const articles = data.news?.results || [];
  if (articles.length === 0) return null;

  const lines = ['## News\n'];
  for (let i = 0; i < Math.min(articles.length, 5); i++) {
    const n = articles[i];
    lines.push(`${i + 1}. **${stripHtml(n.title || '')}**`);
    lines.push(`   URL: ${n.url}`);
    if (n.description) lines.push(`   ${stripHtml(n.description)}`);
    if (n.page_age) lines.push(`   Age: ${n.page_age}`);
    if (n.profile?.name) lines.push(`   Source: ${n.profile.name}`);
    lines.push('');
  }
  return lines.join('\n');
}

// ─── Video formatter ────────────────────────────────────────────────────────────

function formatVideos(data) {
  const videos = data.videos?.results || [];
  if (videos.length === 0) return null;

  const lines = ['## Videos\n'];
  for (let i = 0; i < Math.min(videos.length, 5); i++) {
    const v = videos[i];
    lines.push(`${i + 1}. **${stripHtml(v.title || '')}**`);
    lines.push(`   URL: ${v.url}`);
    if (v.video?.duration) lines.push(`   Duration: ${v.video.duration}`);
    if (v.publisher) lines.push(`   Publisher: ${v.publisher}`);
    if (v.meta_url?.netloc) lines.push(`   Source: ${v.meta_url.netloc}`);
    lines.push('');
  }
  return lines.join('\n');
}

// ─── Summary formatter ────────────────────────────────────────────────────────

function formatSummary(data) {
  if (!data || data.status === 'failed') return null;
  const lines = [];
  if (data.title) lines.push(`## ${data.title}\n`);
  if (data.summary?.length) {
    lines.push(data.summary.map(s => s.data || '').join(''));
  }
  if (data.followups?.length) {
    lines.push('\n**Related questions:**');
    for (const q of data.followups) lines.push(`- ${q}`);
  }
  return lines.join('\n');
}

// ─── Main ─────────────────────────────────────────────────────────────────────

function formatSuggestions(data, rich) {
  const results = data.results || [];
  if (results.length === 0) {
    return 'No suggestions found.';
  }

  const lines = [`Got ${results.length} suggestion(s) for: ${data.query?.original || ''}\n`];

  if (rich) {
    for (let i = 0; i < results.length; i++) {
      const r = results[i];
      lines.push(`${i + 1}. **${r.query}**`);
      if (r.is_entity) {
        lines.push(`   [Entity: ${r.title || r.query}]`);
      }
      if (r.title) {
        lines.push(`   Title: ${r.title}`);
      }
      if (r.description) {
        lines.push(`   ${r.description}`);
      }
      if (r.img) {
        lines.push(`   Image: ${r.img}`);
      }
      lines.push('');
    }
  } else {
    for (let i = 0; i < results.length; i++) {
      lines.push(`${i + 1}. ${results[i].query}`);
    }
  }

  return lines.join('\n');
}

function formatSpellcheck(data) {
  const original = data.query?.original || '';
  const results = data.results || [];

  // If no results, or every result is identical to the original — no correction needed
  const hasCorrection = results.length > 0 && results.some(r => r.query !== original);

  if (!hasCorrection) {
    return `Spellcheck for "${original}": no correction needed. ✓`;
  }

  const lines = [`Did you mean:`];
  for (let i = 0; i < results.length; i++) {
    lines.push(`  ${i + 1}. ${results[i].query}`);
  }
  return lines.join('\n');
}

function parseCitations(text) {
  const sources = [];
  const seen = new Set();

  const citationRegex = /<citation>([\s\S]*?)<\/citation>/g;
  let match;
  while ((match = citationRegex.exec(text)) !== null) {
    try {
      const citation = JSON.parse(match[1]);
      if (citation.url && !seen.has(citation.url)) {
        seen.add(citation.url);
        sources.push({
          url: citation.url,
          title: citation.title || citation.url,
          snippet: citation.snippet || '',
          number: citation.number,
        });
      }
    } catch {
      // ignore malformed citation
    }
  }

  const cleanText = text
    .replace(/<citation>[\s\S]*?<\/citation>/g, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();

  return { cleanText, sources };
}

function parseEntities(text) {
  const entities = [];
  const entityRegex = /<enum_item>([\s\S]*?)<\/enum_item>/g;
  let match;
  while ((match = entityRegex.exec(text)) !== null) {
    try {
      const entity = JSON.parse(match[1]);
      if (entity.name) {
        entities.push({
          name: entity.name,
          href: entity.href || '',
          originalTokens: entity.original_tokens || '',
          citations: entity.citations || [],
        });
      }
    } catch {
      // ignore malformed entity
    }
  }
  return entities;
}


export { formatResults, formatDiscussions, formatFAQ, formatInfobox, formatNews, formatVideos, formatSummary, formatSuggestions, formatSpellcheck, parseCitations, parseEntities };
