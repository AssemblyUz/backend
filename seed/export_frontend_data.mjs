/**
 * Dumps the frontend's static content into seed/content.json so the Django
 * `seed_content` command can import it without parsing TypeScript.
 *
 * Run from the repo root (needs Node 22+ for native type stripping):
 *   node --experimental-strip-types backend/seed/export_frontend_data.mjs
 *
 * The backend and frontend are separate repositories. This assumes they are
 * checked out side by side, which is what the default below resolves to:
 *
 *   <workspace>/backend/seed/export_frontend_data.mjs   <- this file
 *   <workspace>/frontend/src/data/                      <- what it reads
 *
 * Pass an explicit path, or set FRONTEND_DIR, when the checkout differs:
 *   node --experimental-strip-types backend/seed/export_frontend_data.mjs ../my-frontend
 *
 * This is a one-way migration aid. Once Django owns the content, the static
 * files it reads from become dead and can be deleted.
 */

import {writeFileSync, readFileSync, existsSync} from 'node:fs';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {dirname, join, resolve} from 'node:path';

const here = dirname(fileURLToPath(import.meta.url));

const frontendDir = resolve(
  process.argv[2] ?? process.env.FRONTEND_DIR ?? join(here, '..', '..', 'frontend'),
);

// Fail with the resolved path rather than a bare ENOENT from the first read.
if (!existsSync(join(frontendDir, 'src', 'data', 'news.ts'))) {
  console.error(`No frontend checkout at: ${frontendDir}`);
  console.error('Pass the path as an argument or set FRONTEND_DIR.');
  process.exit(1);
}

const readJson = (p) => JSON.parse(readFileSync(join(frontendDir, p), 'utf8'));

// Windows absolute paths are not valid ESM specifiers — they must be file:// URLs.
const importSrc = (p) => import(pathToFileURL(join(frontendDir, p)).href);

const {associations} = await importSrc('src/data/associations.ts');
const {news} = await importSrc('src/data/news.ts');
const {socials} = await importSrc('src/data/social.ts');
const {projectLinks} = await importSrc('src/data/projectLinks.ts');
const {site} = await importSrc('src/data/site.ts');

/**
 * The organisation's own details are not in messages/*.json — they live in
 * src/data/site.ts so next-intl does not ship them to the browser. The Django
 * seed command reads them from the `site` and `footer` namespaces, so fold
 * them back in here rather than teaching the backend about a second source.
 */
const withSiteDetails = (locale) => {
  const messages = readJson(`messages/${locale}.json`);
  const details = site[locale];
  return {
    ...messages,
    site: {
      name: details.name,
      short: details.short,
      tagline: details.tagline,
      description: details.description,
    },
    footer: {
      ...messages.footer,
      address: details.address,
      email: details.email,
      phone: details.phone,
    },
  };
};

const content = {
  messages: {
    uz: withSiteDetails('uz'),
    ru: withSiteDetails('ru'),
    en: withSiteDetails('en'),
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
