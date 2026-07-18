/**
 * Dumps the frontend's static content into seed/content.json so the Django
 * `seed_content` command can import it without parsing TypeScript.
 *
 * Run from the repo root (needs Node 22+ for native type stripping):
 *   node --experimental-strip-types backend/seed/export_frontend_data.mjs
 *
 * This is a one-way migration aid. Once Django owns the content, the static
 * files it reads from become dead and can be deleted.
 */

import {writeFileSync, readFileSync} from 'node:fs';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {dirname, join} from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));
const repoRoot = join(here, '..', '..');

const readJson = (p) => JSON.parse(readFileSync(join(repoRoot, p), 'utf8'));

// Windows absolute paths are not valid ESM specifiers — they must be file:// URLs.
const importSrc = (p) => import(pathToFileURL(join(repoRoot, p)).href);

const {associations} = await importSrc('src/data/associations.ts');
const {news} = await importSrc('src/data/news.ts');
const {socials} = await importSrc('src/data/social.ts');
const {projectLinks} = await importSrc('src/data/projectLinks.ts');

const content = {
  messages: {
    uz: readJson('messages/uz.json'),
    ru: readJson('messages/ru.json'),
    en: readJson('messages/en.json'),
  },
  associations,
  news,
  socials,
  projectLinks,
};

const out = join(here, 'content.json');
writeFileSync(out, JSON.stringify(content, null, 2) + '\n', 'utf8');

console.log(`wrote ${out}`);
console.log(`  associations: ${associations.length}`);
console.log(`  news:         ${news.length}`);
console.log(`  socials:      ${socials.length}`);
console.log(`  locales:      ${Object.keys(content.messages).join(', ')}`);
