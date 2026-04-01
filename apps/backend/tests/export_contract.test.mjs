import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const routesSource = readFileSync("/workspace/apps/backend/api/routes.py", "utf8");
const compositorSource = readFileSync("/workspace/apps/backend/services/video_compositor.py", "utf8");
const schemasSource = readFileSync("/workspace/apps/backend/models/schemas.py", "utf8");

test("export routes are declared in backend router", () => {
  assert.match(routesSource, /@router\.post\("\/projects\/\{project_id\}\/exports"/);
  assert.match(routesSource, /@router\.get\("\/exports\/\{task_id\}"/);
  assert.match(routesSource, /@router\.get\("\/projects\/\{project_id\}\/share"/);
});

test("export service supports required formats and progress callbacks", () => {
  assert.match(compositorSource, /EXPORT_FORMATS = \["png_sequence", "mp4", "pdf", "gif"/);
  assert.match(compositorSource, /async def export_pdf\(/);
  assert.match(compositorSource, /async def export_gif_from_images\(/);
  assert.match(compositorSource, /progress_callback/);
});

test("schemas expose export and share payloads", () => {
  assert.match(schemasSource, /class ExportRequest\(BaseModel\):/);
  assert.match(schemasSource, /class ExportResponse\(BaseModel\):/);
  assert.match(schemasSource, /class ShareKitResponse\(BaseModel\):/);
});
