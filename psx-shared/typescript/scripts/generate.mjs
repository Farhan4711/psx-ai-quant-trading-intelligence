#!/usr/bin/env node
// Regenerate `src/generated.ts` from a running FastAPI OpenAPI spec.
//
// Usage:
//   pnpm --filter @psx/shared gen
//   OPENAPI_URL=http://localhost:8000/openapi.json pnpm --filter @psx/shared gen
//
// Why a script instead of build-time gen?
// - The frontend builds in CI where the API isn't running.
// - Committing `generated.ts` makes the contract reviewable in PRs.
// - When the API surface changes meaningfully, the dev who changed it
//   runs `pnpm gen`, commits the diff, and the rest of the team sees
//   "ah, the BillingService signature changed" as a code-review chunk.

import { writeFile, mkdir } from "node:fs/promises";
import { existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT_PATH = join(HERE, "..", "src", "generated.ts");
const OPENAPI_URL = process.env.OPENAPI_URL ?? "http://localhost:8000/openapi.json";

let openapiTs;
try {
  ({ default: openapiTs } = await import("openapi-typescript"));
} catch (err) {
  console.error(
    "Could not load `openapi-typescript`. Run `pnpm install` in psx-shared/typescript first.",
  );
  console.error(err);
  process.exit(1);
}

console.log(`Fetching OpenAPI spec from ${OPENAPI_URL} ...`);

let spec;
try {
  const res = await fetch(OPENAPI_URL);
  if (!res.ok) {
    throw new Error(`${OPENAPI_URL} returned ${res.status}`);
  }
  spec = await res.json();
} catch (err) {
  console.error(
    `Couldn't reach the API at ${OPENAPI_URL}. Is uvicorn running?`,
  );
  console.error(`  cd psx-api && uvicorn psx_api.main:app --reload`);
  console.error(err);
  process.exit(1);
}

console.log("Generating TypeScript types ...");
const output = await openapiTs(spec);

const banner = `// THIS FILE IS AUTO-GENERATED — do not edit by hand.
// Regenerate with: pnpm --filter @psx/shared gen
//
// Curated, documented types live in ./types.ts; this file is the
// verbose source-of-truth covering every endpoint in the OpenAPI
// surface. Import the curated names where possible.

`;

if (!existsSync(dirname(OUT_PATH))) {
  await mkdir(dirname(OUT_PATH), { recursive: true });
}
await writeFile(OUT_PATH, banner + output, "utf8");
console.log(`✓ Wrote ${OUT_PATH}`);
