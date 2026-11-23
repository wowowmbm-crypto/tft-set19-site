(function () {
  'use strict';

  var section = document.querySelector('.sns-pickup');
  if (!section) return;

  var escapeHtml = function (value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (character) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character];
    });
  };

  var allowedUrl = function (value, source) {
    try {
      var url = new URL(value);
      if (url.protocol !== 'https:') return false;
      if (source === 'X') return url.hostname === 'x.com' || url.hostname === 'www.x.com';
      if (source === 'YouTube') return url.hostname === 'youtube.com' || url.hostname === 'www.youtube.com' || url.hostname === 'youtu.be';
    } catch (_) {
      return false;
    }
    return false;
  };

  var ageLabel = function (date) {
    var hours = Math.max(0, Math.floor((Date.now() - date.getTime()) / 3600000));
    if (hours < 1) return '1時間以内';
    if (hours < 24) return hours + '時間前';
    var days = Math.floor(hours / 24);
    return days + '日前';
  };

  var render = function (payload) {
    var cutoff = Date.now() - 72 * 3600000;
    var items = (Array.isArray(payload.items) ? payload.items : []).filter(function (item) {
      var date = new Date(item.published_at);
      return (item.source === 'X' || item.source === 'YouTube') &&
        !Number.isNaN(date.getTime()) && date.getTime() >= cutoff &&
        date.getTime() <= Date.now() + 300000 && allowedUrl(item.url, item.source) &&
        typeof item.title === 'string' && item.title.trim();
    }).sort(function (a, b) {
      return new Date(b.published_at).getTime() - new Date(a.published_at).getTime();
    }).slice(0, 6);

    var sourceData = payload.sources || {};
    var sourceDate = function (source) {
      var date = new Date((sourceData[source] || {}).checked_at || '');
      return Number.isNaN(date.getTime()) ? '未取得' : (date.getMonth() + 1) + '/' + date.getDate();
    };
    var sourceState = function (source) {
      var metadata = sourceData[source] || {};
      var checked = new Date(metadata.checked_at || '');
      var validChecked = !Number.isNaN(checked.getTime());
      var overdue = validChecked && Date.now() - checked.getTime() > 72 * 3600000;
      var freshnessNote = overdue ? ' · 3日超' : '';
      var status = metadata.status || 'unknown';
      if (status === 'manual') return '手動確認対象' + (validChecked ? ' · 掲載データ ' + sourceDate(source) : '') + freshnessNote;
      if (status === 'not_configured') return 'API未設定' + (validChecked ? ' · 最終取得 ' + sourceDate(source) : '') + freshnessNote;
      if (status === 'error') return '取得エラー' + (validChecked ? ' · 最終成功 ' + sourceDate(source) : '') + freshnessNote;
      if (status === 'seed') return '初期掲載データ' + (validChecked ? ' · ' + sourceDate(source) : '') + freshnessNote;
      if (overdue) return '要更新 · 最終成功 ' + sourceDate(source);
      if (status === 'ok') return '取得済' + (validChecked ? ' · ' + sourceDate(source) : '');
      return '状態未確認' + (validChecked ? ' · ' + sourceDate(source) : '');
    };
    var xCount = items.filter(function (item) { return item.source === 'X'; }).length;
    var youtubeCount = items.filter(function (item) { return item.source === 'YouTube'; }).length;
    var countText = 'X ' + xCount + '件（' + sourceDate('X') + '） · YouTube ' + youtubeCount + '件（' + sourceDate('YouTube') + '）';
    var newest = items[0];
    var teaser = newest ? '新着：' + escapeHtml(newest.title) + '（' + escapeHtml(newest.source) + '・' + ageLabel(new Date(newest.published_at)) + '）' : 'X・YouTubeの公開情報を更新ごとに確認';
    var cards = items.map(function (item) {
      var date = new Date(item.published_at);
      var summary = String(item.summary || '').trim();
      var metric = Number(item.metric_count);
      var metricText = Number.isFinite(metric) && metric > 0 ? ' · ' + metric.toLocaleString('ja-JP') + escapeHtml(item.metric_label || '') : '';
      return '<a class="sns-item" href="' + escapeHtml(item.url) + '" target="_blank" rel="noopener noreferrer">' +
        '<span class="sns-item-label">' + escapeHtml(item.source) + ' · ' + ageLabel(date) + '</span>' +
        '<strong>' + escapeHtml(item.title) + '</strong>' +
        '<small>' + escapeHtml(summary) + metricText + '</small></a>';
    }).join('');
    var freshness = '<div class="sns-freshness"><span><b>X:</b> ' + escapeHtml(sourceState('X')) +
      '</span><span><b>YouTube:</b> ' + escapeHtml(sourceState('YouTube')) + '</span></div>';

    section.innerHTML = '<div class="sns-heading"><span class="sns-leading"><span class="sns-yt">SNS</span><strong>SNSのピックアップ情報</strong></span>' +
      '<span class="sns-count">' + countText + '</span><span class="sns-teaser">' + teaser + '</span></div>' +
      '<div class="sns-pickup-grid">' + (cards || '<p class="sns-disclaimer">直近3日以内に取得できる構成紹介はありません。次回の更新時に再確認します。</p>') + '</div>' +
      freshness + '<p class="sns-disclaimer">投稿時刻と取得成功時刻は別に表示しています。表示数・いいね数・再生数は取得時点の参考値で、構成の強さを示す戦績ではありません。投稿内容はPBE調整で変わる場合があります。</p>';
  };

  fetch('./sns_pickups.json', { cache: 'no-store' })
    .then(function (response) {
      if (!response.ok) throw new Error('SNS pickup data unavailable');
      return response.json();
    })
    .then(function (payload) {
      if (payload && Array.isArray(payload.items)) render(payload);
    })
    .catch(function () {
      section.innerHTML = '<div class="sns-heading"><span class="sns-leading"><span class="sns-yt">SNS</span><strong>SNSのピックアップ情報</strong></span><span class="sns-count">最新状態を取得できません</span></div><p class="sns-disclaimer">保存済みの投稿データを読み込めませんでした。ページを再読み込みするか、次回の更新後に確認してください。</p>';
    });
})();
