import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { compileFromFile } from "json-schema-to-typescript";
import { root, runBackend } from "./backend.js";

const check = process.argv.includes("--check");
const directory = await mkdtemp(resolve(tmpdir(), "haul-hours-contracts-"));
try {
  const schemaPath = resolve(directory, "trip.schema.json");
  const code = await runBackend(["manage.py", "export_schema", "--output", schemaPath]);
  if (code !== 0) throw new Error("Schema export failed");
  const schema = await readFile(schemaPath, "utf8");
  const types = await compileFromFile(schemaPath, {
    bannerComment: "/* Generated from Django API serializers. Run npm run contracts:generate. Do not edit. */",
  });
  const files = [
    [resolve(root, "contracts/trip.schema.json"), schema],
    [resolve(root, "frontend/src/features/trip/contracts.generated.ts"), types],
  ] as const;
  for (const [path, contents] of files) {
    if (check) {
      if (await readFile(path, "utf8") !== contents) throw new Error(`Contract drift: ${path}. Run npm run contracts:generate.`);
    } else {
      await writeFile(path, contents);
    }
  }
  console.log(check ? "Contracts match their serializers." : "Generated JSON Schema and TypeScript contracts.");
} finally {
  await rm(directory, { recursive: true, force: true });
}
