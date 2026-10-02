#!/usr/bin/env node
// Render a conversation page from extract.py's output.
//
//   node build.mjs <work-dir> [--draft]
//
// Reads <work-dir>/events.json, meta.json and images/, fills ../assets/template.html and writes
//   <work-dir>/<title-slug>.html   the page to publish (no doctype; the artifact host adds the skeleton)
//   <work-dir>/preview.html        the same page wrapped in a full document, for a local look
// Refuses to build while meta.json still has TODO values, unless --draft is given.
// Markdown is rendered here, with marked 15.0.12 vendored next to this script, so the page is
// complete without client-side rendering; raw HTML inside messages is escaped, never passed through.

import { createRequire } from 'node:module';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const { Marked } = createRequire(import.meta.url)('./vendor/marked.min.js');

const args = process.argv.slice(2);
const draft = args.includes('--draft');
const dir = args.find((a) => !a.startsWith('--'));
if (!dir) { console.error('usage: node build.mjs <work-dir> [--draft]'); process.exit(2); }

const meta = JSON.parse(fs.readFileSync(path.join(dir, 'meta.json'), 'utf8'));
let events = JSON.parse(fs.readFileSync(path.join(dir, 'events.json'), 'utf8'));
if (!events.some((e) => e.k === 'human' || e.k === 'assistant')) {
  console.error('events.json has no prompts or replies: this transcript holds no conversation.');
  process.exit(1);
}

const todo = Object.entries(meta).filter(([, v]) => JSON.stringify(v).includes('TODO')).map(([k]) => k);
if (todo.length && !draft) {
  console.error(`meta.json still has TODO values: ${todo.join(', ')}. Fill them in, or pass --draft for a look.`);
  process.exit(1);
}

// ---- redactions: every listed string is replaced everywhere it would be published ----
const redact = (s) => (meta.redactions || []).reduce((acc, r) => acc.split(r).join('[redacted]'), s);
const deep = (v) => (typeof v === 'string' ? redact(v) : Array.isArray(v) ? v.map(deep) : v && typeof v === 'object'
  ? Object.fromEntries(Object.entries(v).map(([k, x]) => [redact(k), deep(x)])) : v);
events = deep(events);

// ---- markdown ----
const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const renderer = {
  html(token) { return esc(token.text); },
  link(token) {
    const href = token.href || '';
    const text = this.parser.parseInline(token.tokens);
    if (!/^https?:\/\//.test(href)) return text;
    return `<a href="${esc(href)}" target="_blank" rel="noopener">${text}</a>`;
  },
};
const mdAgent = new Marked({ gfm: true, breaks: false }).use({ renderer });
const mdHuman = new Marked({ gfm: true, breaks: true }).use({ renderer });
const wrapTables = (h) => h.replace(/<table>/g, '<div class="tbl"><table>').replace(/<\/table>/g, '</table></div>');
const render = (s) => wrapTables(mdAgent.parse(s || ''));
const renderHuman = (s) => wrapTables(mdHuman.parse(s || ''));

// ---- time ----
const TZ = meta.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone;
const tzName = (style) => new Intl.DateTimeFormat('en-US', { timeZone: TZ, timeZoneName: style })
  .formatToParts(new Date()).find((p) => p.type === 'timeZoneName')?.value || TZ;
const TZ_SHORT = tzName('shortGeneric');
const TZ_LONG = tzName('longGeneric');
const fTime = new Intl.DateTimeFormat('en-US', { timeZone: TZ, hour: '2-digit', minute: '2-digit', hour12: false });
const fDay = new Intl.DateTimeFormat('en-US', { timeZone: TZ, weekday: 'long', month: 'long', day: 'numeric' });
const fDayKey = new Intl.DateTimeFormat('en-CA', { timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit' });
const fShort = new Intl.DateTimeFormat('en-US', { timeZone: TZ, month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false });
const t = (ts) => fTime.format(new Date(ts));

// ---- helpers ----
const USER = esc(meta.userName || 'You');
const AGENT = esc(meta.agentName || 'Claude');
const imgTag = (img) => {
  const b64 = fs.readFileSync(path.join(dir, img.file)).toString('base64');
  const alt = (meta.imageAlts || {})[img.id] || 'Attached screenshot';
  return `<figure class="shot"><img src="data:${img.mime};base64,${b64}" alt="${esc(alt)}" loading="lazy"><figcaption>Attached screenshot</figcaption></figure>`;
};
const navLine = (text) => {
  const own = text.split('\n').filter((l) => !/^\s*>/.test(l) && !/^\s*\t/.test(l)).join(' ').replace(/\[Image #\d+\]/g, '').replace(/\s+/g, ' ').trim();
  const s = (own || text.replace(/^>\s*/gm, '').replace(/\s+/g, ' ').trim()).replace(/[*`#]/g, '');
  return s.length > 84 ? s.slice(0, 82).trimEnd() + '…' : s;
};
const notifyKind = (s) => {
  let m;
  if ((m = s.match(/^Dynamic workflow "(.*)" (completed|failed|stopped)/s))) return ['Workflow', m[1]];
  if ((m = s.match(/^Background command "(.*)" (completed|failed)/s))) return ['Background task', m[1]];
  if ((m = s.match(/^Agent "(.*)" (finished|completed|failed)/s))) return ['Subagent', m[1]];
  return ['Task', s];
};

// ---- stats ----
const humans = events.filter((e) => e.k === 'human');
const replies = events.filter((e) => e.k === 'assistant').length;
const asks = events.filter((e) => e.k === 'ask').length;
const toolItems = events.filter((e) => e.k === 'activity').flatMap((e) => e.items);
const nWorkflows = toolItems.filter((i) => i.tool === 'Workflow').length;
const nAgents = toolItems.filter((i) => i.tool === 'Subagent').length;
const first = (humans[0] || events[0]).ts;
const last = ([...events].reverse().find((e) => e.k === 'assistant') || events[events.length - 1]).ts;

// ---- log ----
const out = [];
const nav = [];
let day = '';
let pn = 0;
for (const e of events) {
  const k = fDayKey.format(new Date(e.ts));
  if (k !== day) { day = k; out.push(`<div class="day" role="separator"><span>${esc(fDay.format(new Date(e.ts)))}</span></div>`); }
  const time = `<time datetime="${esc(e.ts)}">${t(e.ts)}</time>`;
  switch (e.k) {
    case 'human': {
      const id = `p${++pn}`;
      nav.push(`<li><a href="#${id}"><span class="n">${String(pn).padStart(2, '0')}</span><span class="nt">${esc(navLine(e.text))}</span><span class="ntime">${t(e.ts)}</span></a></li>`);
      const queued = e.source === 'queued' ? '<span class="tag">sent while the agent was working</span>' : '';
      out.push(`<article class="entry human" id="${id}"><div class="gut">${time}<span class="pnum">Prompt ${pn}</span></div><div class="body"><header class="who"><span class="name">${USER}</span>${queued}</header><div class="prose">${renderHuman(e.text)}</div>${(e.imgs || []).map(imgTag).join('')}</div></article>`);
      break;
    }
    case 'assistant':
      out.push(`<article class="entry agent"><div class="gut">${time}</div><div class="body"><div class="prose">${render(e.text)}</div></div></article>`);
      break;
    case 'activity': {
      const counts = {};
      for (const it of e.items) counts[it.tool] = (counts[it.tool] || 0) + 1;
      const top = Object.entries(counts).sort((a, b) => b[1] - a[1]).map(([name, v]) => (v > 1 ? `${name} ×${v}` : name)).join(' · ');
      const n = e.items.length;
      const items = e.items.map((it) => `<li><span class="tool">${esc(it.tool)}</span><span class="lbl">${esc(it.label) || '<span class="dim">no description</span>'}</span></li>`).join('');
      out.push(`<div class="entry act"><div class="gut">${time}</div><details class="body"><summary><span class="count">${n} ${n === 1 ? 'action' : 'actions'}</span><span class="tools">${esc(top)}</span></summary><ol>${items}</ol></details></div>`);
      break;
    }
    case 'ask': {
      const qs = (e.questions || []).map((q) => {
        const ans = (e.answers || {})[q.question];
        const opts = (q.options || []).map((o) => `<li class="${o.label === ans ? 'picked' : ''}"><span class="ol">${esc(o.label)}</span><span class="od">${esc(o.description)}</span></li>`).join('');
        const picked = (q.options || []).some((o) => o.label === ans);
        const custom = !picked && ans ? `<p class="custom"><span class="cl">${USER} wrote</span> ${esc(ans)}</p>` : '';
        const notes = e.annotations?.[q.question]?.notes;
        const note = notes ? `<p class="custom"><span class="cl">Note</span> ${esc(notes)}</p>` : '';
        return `<div class="q"><div class="qh"><span class="chip">${esc(q.header)}</span><p>${esc(q.question)}</p></div><ul class="opts">${opts}</ul>${custom}${note}</div>`;
      }).join('');
      out.push(`<article class="entry ask"><div class="gut">${time}<span class="pnum">Decision</span></div><div class="body"><header class="who"><span class="name agentname">${AGENT} asked</span><span class="tag">answered by ${USER}</span></header>${qs}</div></article>`);
      break;
    }
    case 'notify': {
      const [kind, title] = notifyKind(e.summary || '');
      const st = e.status || 'done';
      const res = e.result ? `<details><summary>Result returned to the ${esc(meta.agentNoun || 'agent')}</summary><pre class="raw">${esc(e.result.length > 4000 ? e.result.slice(0, 4000) + ' …' : e.result)}</pre></details>` : '';
      out.push(`<div class="entry evt"><div class="gut">${time}</div><div class="body"><p class="evline"><span class="kind">${esc(kind)}</span><span class="st st-${esc(st)}">${esc(st)}</span><span class="et">${esc(title)}</span></p>${res}</div></div>`);
      break;
    }
    case 'handback':
      out.push(`<div class="entry evt"><div class="gut">${time}</div><details class="body hb"><summary><span class="kind">Subagent report</span><span class="et">${esc(navLine(e.text.replace(/^#+\s*/, '')))}</span></summary><div class="prose small">${render(e.text)}</div></details></div>`);
      break;
    case 'compact': {
      const pre = e.pre ? ` (${Math.round(e.pre / 1000)}k tokens summarized)` : '';
      out.push(`<div class="entry mark"><div class="gut">${time}</div><details class="body"><summary><span class="kind">Context compacted${esc(pre)}</span><span class="et">The ${esc(meta.agentNoun || 'agent')} continued from this summary</span></summary><div class="prose small">${render(e.text)}</div></details></div>`);
      break;
    }
    case 'command':
      out.push(`<div class="entry mark"><div class="gut">${time}</div><div class="body"><p class="evline"><span class="kind">${USER} ran</span><code>${esc(e.name)}</code>${e.out ? `<span class="et">${esc(e.out)}</span>` : ''}</p></div></div>`);
      break;
    case 'interrupt':
      out.push(`<div class="entry mark"><div class="gut">${time}</div><div class="body"><p class="evline"><span class="kind">Interrupted</span><span class="et">${esc(e.text)}</span></p></div></div>`);
      break;
    case 'away':
      out.push(`<div class="entry mark"><div class="gut">${time}</div><div class="body"><p class="evline"><span class="kind">Recap</span><span class="et">${esc(e.text)}</span></p></div></div>`);
      break;
    case 'pr':
      if (/^https?:\/\//.test(e.url || '')) out.push(`<div class="entry mark"><div class="gut">${time}</div><div class="body"><p class="evline"><span class="kind">PR linked</span><a href="${esc(e.url)}" target="_blank" rel="noopener">#${esc(e.number)} in ${esc(e.repo)}</a></p></div></div>`);
      break;
  }
}
out.push(`<div class="end"><span>End of session · ${esc(fShort.format(new Date(last)))} ${esc(TZ_SHORT)}</span></div>`);

// ---- page ----
const noun = meta.agentNoun || 'Claude';
const note = meta.note || `Every prompt and every ${noun} reply is included, in order. Tool calls are listed by name and description only; their outputs and the agent's private reasoning are left out. Times are in ${TZ_LONG}.`;
const outcome = meta.outcome ? `<p class="outcome">${mdAgent.parseInline(redact(meta.outcome))}</p>` : '';
const tpl = fs.readFileSync(path.join(here, '..', 'assets', 'template.html'), 'utf8');
const html = tpl
  .replaceAll('{{TITLE}}', esc(meta.title))
  .replaceAll('{{DESCRIPTION}}', esc(meta.description))
  .replaceAll('{{EYEBROW}}', esc(meta.eyebrow))
  .replaceAll('{{DEK}}', esc(meta.dek))
  .replaceAll('{{NOTE}}', esc(note))
  .replaceAll('{{AGENT_NOUN}}', esc(noun))
  .replaceAll('{{SPAN}}', `${esc(fShort.format(new Date(first)))} – ${esc(fShort.format(new Date(last)))} ${esc(TZ_SHORT)}`)
  .replaceAll('{{PROMPTS}}', String(humans.length))
  .replaceAll('{{REPLIES}}', String(replies))
  .replaceAll('{{ASKS}}', String(asks))
  .replaceAll('{{WORKFLOWS}}', String(nWorkflows))
  .replaceAll('{{AGENTS}}', String(nAgents))
  .replaceAll('{{ACTIONS}}', String(toolItems.length))
  .replace('{{OUTCOME}}', () => outcome)
  .replace('{{NAV}}', () => nav.join('\n'))
  .replace('{{LOG}}', () => out.join('\n'));

const slug = String(meta.title || 'conversation').toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'conversation';
const pagePath = path.join(dir, `${slug}.html`);
fs.writeFileSync(pagePath, html);
fs.writeFileSync(path.join(dir, 'preview.html'),
  `<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"></head><body>${html}</body></html>`);
console.log(`${pagePath}  ${(Buffer.byteLength(html) / 1024).toFixed(0)} KB · ${humans.length} prompts · ${replies} replies · ${asks} decisions · ${toolItems.length} tool actions${todo.length ? ` · DRAFT (TODO: ${todo.join(', ')})` : ''}`);
if (Buffer.byteLength(html) > 15 * 1024 * 1024) console.warn('warning: the page is over 15 MB; artifacts allow 16 MB');
