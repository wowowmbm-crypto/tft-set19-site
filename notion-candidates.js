(function () {
  'use strict';

  var panel = document.getElementById('notionCandidates');
  if (!panel) return;
  var sourceUrl = 'https://busy-ziconium-740.notion.site/1d3859a65b0a80f8adc3c0378eb3b007?v=41a859a65b0a80af8014000c747530dd&p=41b859a65b0a80199190d863429bdd52&pm=s';
  var escapeHtml = function (value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (character) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character];
    });
  };
  var displayDate = function (value) {
    var date = new Date(value);
    return Number.isNaN(date.getTime()) ? '' : (date.getFullYear() + '/' + (date.getMonth() + 1) + '/' + date.getDate());
  };
  var render = function (payload) {
    var items = (Array.isArray(payload.items) ? payload.items : []).filter(function (item) {
      if (!item || typeof item.title !== 'string' || typeof item.url !== 'string') return false;
      try {
        var url = new URL(item.url);
        return url.protocol === 'https:' && (url.hostname === 'notion.site' || url.hostname.endsWith('.notion.site'));
      }
      catch (_) { return false; }
    }).slice(0, 8);
    var status = payload.status || 'unknown';
    var content = items.length ? '<div class="notion-candidate-list">' + items.map(function (item) {
      var metadata = [item.patch, item.author, displayDate(item.published_at)].filter(Boolean).map(escapeHtml).join(' · ');
      return '<a class="notion-candidate" href="' + escapeHtml(item.url) + '" target="_blank" rel="noopener noreferrer">' +
        '<span class="notion-candidate-meta">' + (metadata || '投稿日未確認') + ' · 統計照合待ち</span>' +
        '<b>' + escapeHtml(item.title) + '</b></a>';
    }).join('') + '</div>' : '<p class="notion-empty">' +
      (status === 'not_configured' ? 'Notion連携はまだ未設定です。GitHub Actionsに読み取り専用連携を追加すると、新着記事を週次で候補表示します。' :
        status === 'error' ? 'Notionの最新取得に失敗しました。保存済み候補があればそのまま表示し、次回更新で再試行します。' :
          '新着候補はありません。Notionを直接確認できます。') + '</p>';
    var checked = displayDate(payload.checked_at);
    panel.innerHTML = '<div class="notion-candidates-head"><strong>Notion新着候補</strong><small>記事発見用 · TFT統計との照合前 · ' +
      (checked ? escapeHtml(checked) + '確認' : '取得状態を確認') + '</small></div>' + content +
      '<p class="notion-candidates-foot">Notion記事だけでは構成を確定しません。平均順位・採用率と別ガイドを確認した候補だけ、構成一覧へ反映します。 <a href="' + sourceUrl + '" target="_blank" rel="noopener noreferrer">Notion Set 19記事 ↗</a></p>';
  };

  fetch('./notion_candidates.json', { cache: 'no-store' })
    .then(function (response) { if (!response.ok) throw new Error('Notion candidates unavailable'); return response.json(); })
    .then(render)
    .catch(function () { render({ status: 'not_configured', items: [] }); });
})();
