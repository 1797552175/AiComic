<script>
  import { createShareKit, EXPORT_FORMATS } from "../lib/shareExport.mjs";

  export let projectId = "";
  export let projectTitle = "未命名作品";
  export let baseUrl = "http://localhost:8000";
  export let progress = 0;
  export let status = "idle";
  export let selectedFormat = "mp4";
  export let onExport = () => {};

  let copied = false;

  $: shareKit = createShareKit({
    baseUrl,
    projectId,
    title: projectTitle
  });

  async function copyShareLink() {
    if (!navigator?.clipboard) {
      return;
    }

    await navigator.clipboard.writeText(shareKit.shareUrl);
    copied = true;
    window.setTimeout(() => {
      copied = false;
    }, 1800);
  }
</script>

<section class="share-export-panel" aria-label="分享与导出">
  <header class="panel-header">
    <div>
      <p class="eyebrow">分享与导出</p>
      <h2>{projectTitle}</h2>
    </div>
    <div class="status-pill">{status}</div>
  </header>

  <div class="grid">
    <section class="card">
      <h3>导出格式</h3>
      <div class="format-grid">
        {#each EXPORT_FORMATS as format}
          <button
            type="button"
            class:selected={selectedFormat === format.value}
            on:click={() => selectedFormat = format.value}
          >
            {format.label}
          </button>
        {/each}
      </div>

      <div class="progress-block">
        <div class="progress-label">
          <span>导出进度</span>
          <strong>{progress}%</strong>
        </div>
        <div class="progress-track" aria-hidden="true">
          <div class="progress-fill" style={`width: ${Math.min(Math.max(progress, 0), 100)}%`}></div>
        </div>
      </div>

      <button type="button" class="primary" on:click={() => onExport(selectedFormat)}>
        开始导出
      </button>
    </section>

    <section class="card">
      <h3>社交分享</h3>
      <div class="share-actions">
        <a href={shareKit.platforms.wechat.shareUrl} class="share-link" target="_blank" rel="noreferrer">
          微信
        </a>
        <a href={shareKit.platforms.weibo.shareUrl} class="share-link" target="_blank" rel="noreferrer">
          微博
        </a>
        <a href={shareKit.platforms.douyin.shareUrl} class="share-link" target="_blank" rel="noreferrer">
          抖音
        </a>
        <button type="button" class="share-link" on:click={copyShareLink}>
          {copied ? "已复制" : "复制链接"}
        </button>
      </div>

      <div class="qr-row">
        <img src={shareKit.qrCodeUrl} alt="分享二维码" class="qr-code" />
        <div class="share-meta">
          <p>分享链接</p>
          <code>{shareKit.shareUrl}</code>
        </div>
      </div>
    </section>

    <section class="card full">
      <h3>嵌入代码</h3>
      <textarea readonly rows="5">{shareKit.embedCode}</textarea>
    </section>
  </div>
</section>

<style>
  .share-export-panel {
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 24px;
    padding: 24px;
    background:
      radial-gradient(circle at top left, rgba(92, 168, 255, 0.14), transparent 34%),
      linear-gradient(180deg, rgba(14, 18, 28, 0.98), rgba(8, 10, 16, 0.98));
    color: #edf2ff;
    box-shadow: 0 30px 80px rgba(0, 0, 0, 0.35);
  }

  .panel-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    margin-bottom: 20px;
  }

  .eyebrow {
    margin: 0 0 6px;
    color: #93c5fd;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-size: 12px;
  }

  h2,
  h3,
  p {
    margin: 0;
  }

  h2 {
    font-size: 28px;
    line-height: 1.1;
  }

  .status-pill {
    padding: 8px 12px;
    border-radius: 999px;
    background: rgba(147, 197, 253, 0.14);
    color: #bfdbfe;
    font-size: 13px;
  }

  .grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }

  .card {
    border-radius: 20px;
    padding: 18px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.06);
  }

  .full {
    grid-column: 1 / -1;
  }

  .format-grid,
  .share-actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    margin-top: 14px;
  }

  button,
  .share-link {
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.04);
    color: inherit;
    padding: 10px 14px;
    cursor: pointer;
    text-decoration: none;
    font: inherit;
  }

  button.selected,
  .share-link:hover,
  .primary {
    background: linear-gradient(135deg, #38bdf8, #2563eb);
    border-color: transparent;
  }

  .progress-block {
    margin-top: 18px;
  }

  .progress-label {
    display: flex;
    justify-content: space-between;
    margin-bottom: 8px;
    color: #cbd5e1;
  }

  .progress-track {
    height: 10px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.08);
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    border-radius: inherit;
    background: linear-gradient(90deg, #38bdf8, #a78bfa);
  }

  .primary {
    width: 100%;
    margin-top: 18px;
    font-weight: 600;
  }

  .qr-row {
    display: grid;
    grid-template-columns: 160px 1fr;
    gap: 16px;
    align-items: center;
    margin-top: 16px;
  }

  .qr-code {
    width: 160px;
    height: 160px;
    border-radius: 16px;
    background: #fff;
  }

  .share-meta code,
  textarea {
    display: block;
    width: 100%;
    box-sizing: border-box;
    margin-top: 10px;
    padding: 12px;
    border-radius: 14px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(255, 255, 255, 0.06);
    color: #e2e8f0;
    font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
    font-size: 13px;
    overflow: auto;
  }

  textarea {
    resize: vertical;
    min-height: 120px;
  }

  @media (max-width: 900px) {
    .grid {
      grid-template-columns: 1fr;
    }

    .qr-row {
      grid-template-columns: 1fr;
    }
  }
</style>
