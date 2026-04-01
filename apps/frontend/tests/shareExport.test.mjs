import test from "node:test";
import assert from "node:assert/strict";

import {
  buildShareUrl,
  buildWeiboShareUrl,
  buildDouyinShareLink,
  buildQrCodeUrl,
  buildEmbedCode,
  createShareKit,
  EXPORT_FORMATS
} from "../src/lib/shareExport.mjs";

test("share url and embed code are generated consistently", () => {
  const shareUrl = buildShareUrl("http://localhost:8000/", "proj_123");
  assert.equal(shareUrl, "http://localhost:8000/share/proj_123");
  assert.match(buildEmbedCode(shareUrl, '作品 "A"'), /iframe/);
});

test("social links are generated for weibo and douyin", () => {
  const shareUrl = "http://localhost:8000/share/proj_123";
  assert.match(buildWeiboShareUrl(shareUrl, "测试作品"), /service\.weibo\.com/);
  assert.match(buildDouyinShareLink(shareUrl, "测试作品"), /^snssdk1128:\/\//);
  assert.match(buildQrCodeUrl(shareUrl), /api\.qrserver\.com/);
});

test("share kit exposes all required formats", () => {
  const kit = createShareKit({
    baseUrl: "http://localhost:8000",
    projectId: "proj_123",
    title: "测试作品"
  });

  assert.equal(EXPORT_FORMATS.length, 4);
  assert.ok(kit.platforms.wechat);
  assert.ok(kit.platforms.weibo);
  assert.ok(kit.platforms.douyin);
  assert.match(kit.embedCode, /iframe/);
});
