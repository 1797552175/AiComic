const DEFAULT_BASE_URL = "http://localhost:8000";

function trimTrailingSlash(value) {
  return String(value || "").replace(/\/+$/, "");
}

function encode(value) {
  return encodeURIComponent(value);
}

export const EXPORT_FORMATS = [
  { value: "png_sequence", label: "PNG 序列" },
  { value: "mp4", label: "MP4" },
  { value: "pdf", label: "PDF" },
  { value: "gif", label: "GIF" }
];

export function buildShareUrl(baseUrl, projectId) {
  const root = trimTrailingSlash(baseUrl || DEFAULT_BASE_URL);
  return `${root}/share/${projectId}`;
}

export function buildWeiboShareUrl(shareUrl, title) {
  const params = new URLSearchParams({
    url: shareUrl,
    title: title || ""
  });
  return `https://service.weibo.com/share/share.php?${params.toString()}`;
}

export function buildDouyinShareLink(shareUrl, title) {
  const text = `${title || ""} ${shareUrl}`.trim();
  return `snssdk1128://share/text?text=${encode(text)}`;
}

export function buildQrCodeUrl(shareUrl) {
  return `https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=${encode(shareUrl)}`;
}

export function buildEmbedCode(shareUrl, title) {
  const safeTitle = String(title || "AiComic 作品")
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;");

  return `<iframe src="${shareUrl}?embed=1" title="${safeTitle}" loading="lazy" allowfullscreen style="width:100%;min-height:640px;border:0;border-radius:16px;"></iframe>`;
}

export function createShareKit({ baseUrl, projectId, title }) {
  const shareUrl = buildShareUrl(baseUrl, projectId);
  return {
    shareUrl,
    qrCodeUrl: buildQrCodeUrl(shareUrl),
    embedCode: buildEmbedCode(shareUrl, title),
    platforms: {
      wechat: {
        label: "微信",
        shareUrl,
        hint: "复制链接或扫码后分享到微信"
      },
      weibo: {
        label: "微博",
        shareUrl: buildWeiboShareUrl(shareUrl, title),
        hint: "打开微博分享页即可发布"
      },
      douyin: {
        label: "抖音",
        shareUrl: buildDouyinShareLink(shareUrl, title),
        hint: "作为抖音 App 内文本分享入口"
      }
    }
  };
}
