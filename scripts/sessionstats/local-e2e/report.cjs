'use strict';

const fs = require('node:fs/promises');
const path = require('node:path');

const escape = value => String(value).replace(/[&<>"']/g, character =>
  ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[character]);
const link = (filename, caption) => `<a href="${filename.split('/').map(encodeURIComponent).join('/')}">${escape(caption)}</a>`;

async function writeReport(directory, state) {
  const lines = (await fs.readFile(path.join(directory,'results.ndjson'),'utf8')).trim().split('\n').filter(Boolean);
  const cases = lines.map(line=>JSON.parse(line));
  const entries = cases.map(result=>{
    const failed = result.error || result.shots.some(shot=>shot.visualFailure||shot.missingBaseline);
    const shots = result.shots.map((shot, index)=>{
      const caption=result.phases?`Kółko × ${index}`:path.basename(shot.image,'.png');
      const links=[link(shot.image,caption)];
      if(shot.reference) links.push(link(shot.reference,'Wzorzec'),link(shot.diff,'Różnica'));
      if(shot.difference!==undefined) links.push(`${(shot.difference*100).toFixed(3)}%`);
      if(shot.missingBaseline) links.push('Brak wzorca');
      return `<li>${links.join(' · ')}</li>`;
    }).join('');
    return `<details${failed?' class="failure" open':''}><summary>${escape(result.key)}${failed?' · błąd':''}</summary>`+
      `${result.error?`<p>${escape(result.error)}</p>`:''}<ul>${shots}</ul></details>`;
  });
  const html = `<!doctype html><html lang="pl"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Session Stats E2E</title>
  <style>body{max-width:75rem;margin:2rem auto;padding:0 1rem;font:16px system-ui;background:#171b13;color:#f1edda}a{color:#a6d9fb}details{margin:.4rem 0;padding:.4rem;border:1px solid #45483a}summary{cursor:pointer;overflow-wrap:anywhere}.failure{border-color:#ff8c93}ul{margin:.4rem 0}p{overflow-wrap:anywhere}</style>
  <h1>Session Stats ${escape(state.version)}</h1>
  <p>${escape(state.engine)} · ${escape(state.renderer||'brak renderera')} · ${state.completed}/${state.planned} przypadków · ${state.failed+state.interactionErrors} błędów · ${state.visualFailures} różnic wizualnych</p>
  <p>${link('run.json','Metadane przebiegu')} · ${link('results.ndjson','Pomiary i asercje')}</p>
  ${entries.join('\n')}
  </html>`;
  await fs.writeFile(path.join(directory,'index.html'),html);
}

module.exports={writeReport};
