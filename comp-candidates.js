(function () {
  'use strict';

  var panel = document.getElementById('compCandidates');
  if (!panel) return;

  var escapeHtml = function (value) {
    return String(value == null ? '' : value).replace(/[&<>"']/g, function (character) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character];
    });
  };
  var displayDate = function (value) {
    var date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return new Intl.DateTimeFormat('ja-JP', { timeZone: 'Asia/Tokyo', year: 'numeric', month: 'numeric', day: 'numeric' }).format(date);
  };
  var safeUrl = function (value) {
    try {
      var url = new URL(value);
      var host = url.hostname.toLowerCase();
      var allowed = ['tft.ninja', 'mobalytics.gg', 'tftcoach.com', 'notion.site'];
      return url.protocol === 'https:' && allowed.some(function (domain) { return host === domain || host.endsWith('.' + domain); }) ? url.href : '';
    } catch (_) { return ''; }
  };
  var sourceLabel = function (source) {
    if (source.id === 'tft_ninja') return 'TFT Ninja統計';
    if (source.id === 'mobalytics') return 'Mobalytics' + (source.tier ? ' ' + source.tier + '評価' : '');
    if (source.id === 'tft_coach') return 'TFT Coach提案';
    if (source.id === 'notion') return 'Notion記事';
    return source.name || '情報源';
  };
  var sourceState = function (id, source) {
    var name = source.name || id;
    var checked = displayDate(source.checked_at);
    if (source.status === 'ok') return escapeHtml(name) + (checked ? ' ' + escapeHtml(checked) : '') + '確認';
    if (source.status === 'stale') return '<span class="comp-source-stale">' + escapeHtml(name) + '取得失敗・前回分を表示' + (checked ? '（' + escapeHtml(checked) + '）' : '') + '</span>';
    if (source.status === 'not_configured') return escapeHtml(name) + '未接続';
    if (source.status === 'error') return '<span class="comp-source-stale">' + escapeHtml(name) + '取得失敗</span>';
    if (id === 'notion') return escapeHtml(name) + '未接続';
    return escapeHtml(name) + '状態未確認';
  };

  var carouselControls = function (target, label, count) {
    return '<div class="comp-carousel-tools" data-carousel-target="' + target + '" role="group" aria-label="' + escapeHtml(label) + 'を移動">' +
      '<span class="comp-carousel-status" aria-live="polite">1–' + Math.min(count, 3) + ' / ' + count + '</span>' +
      '<button type="button" class="comp-carousel-prev" aria-label="前へ"><span aria-hidden="true">‹</span></button>' +
      '<button type="button" class="comp-carousel-next" aria-label="次へ"><span aria-hidden="true">›</span></button></div>';
  };

  function render(payload) {
    payload = payload && typeof payload === 'object' ? payload : {};
    var sources = payload.sources && typeof payload.sources === 'object' ? payload.sources : {};
    var candidates = (Array.isArray(payload.candidates) ? payload.candidates : []).filter(function (item) {
      return item && typeof item.name === 'string' && Array.isArray(item.sources) && item.sources.length;
    });
    var articles = (Array.isArray(payload.articles) ? payload.articles : []).filter(function (item) {
      return item && typeof item.title === 'string' && safeUrl(item.url);
    }).slice(0, 6);

    var states = ['tft_ninja', 'mobalytics', 'tft_coach', 'notion'].map(function (id) {
      var source = sources[id] || {};
      return sourceState(id, source);
    }).join('<span class="comp-status-separator">·</span>');

    var candidateCards = candidates.length ? '<div id="comp-candidate-track" class="comp-candidate-strip" tabindex="0" aria-label="構成の追加候補一覧">' + candidates.map(function (candidate) {
      var badges = candidate.sources.map(function (source) {
        return '<span class="comp-candidate-badge">' + escapeHtml(sourceLabel(source)) + '</span>';
      }).join('');
      var stats = candidate.sources.find(function (source) { return source.id === 'tft_ninja'; });
      var metricText = stats ? '平均順位 ' + Number(stats.avp).toFixed(2) + ' · 1位率 ' + Number(stats.win).toFixed(1) + '%' +
        (Number.isFinite(Number(stats.play_rate)) ? ' · Pick ' + Number(stats.play_rate).toFixed(1) + '%' : '') : '統計未照合 · 配置や装備は未確認';
      var links = candidate.sources.map(function (source) {
        var href = safeUrl(source.url);
        if (!href) return '';
        return '<a href="' + escapeHtml(href) + '" target="_blank" rel="noopener noreferrer">' + escapeHtml(sourceLabel(source)) + ' ↗</a>';
      }).join('');
      var agreement = candidate.source_count >= 2 ? '複数サイトに関連候補' : '候補';
      return '<article class="comp-candidate-card"><div class="comp-candidate-badges">' + badges + '</div>' +
        '<strong>' + escapeHtml(candidate.name) + '</strong>' +
        '<small>' + escapeHtml(agreement) + ' · ' + escapeHtml(metricText) + '</small>' +
        '<div class="comp-candidate-links">' + links + '</div></article>';
    }).join('') + '</div>' : '<p class="comp-candidates-empty">未登録の有力候補は見つかりませんでした。取得元の状態を確認してください。</p>';

    var articleSection = articles.length ? '<div class="comp-article-heading"><span>Notionの新着記事候補 <small>構成内容との照合前</small></span>' +
      carouselControls('comp-article-track', 'Notion記事候補', articles.length) + '</div>' +
      '<div id="comp-article-track" class="comp-candidate-strip comp-article-strip" tabindex="0" aria-label="Notion記事候補一覧">' + articles.map(function (item) {
        var metadata = [item.patch, item.author, displayDate(item.published_at)].filter(Boolean).map(escapeHtml).join(' · ');
        return '<a class="comp-article-card" href="' + escapeHtml(safeUrl(item.url)) + '" target="_blank" rel="noopener noreferrer">' +
          '<small>' + (metadata || '投稿日未確認') + '</small><strong>' + escapeHtml(item.title) + '</strong></a>';
      }).join('') + '</div>' : '';

    var checked = displayDate(payload.checked_at);
    panel.innerHTML = '<div class="comp-candidates-head"><span class="comp-candidates-title"><strong>構成の追加候補</strong>' +
      '<small>統計・ガイド・記事から自動発見' + (checked ? ' · ' + escapeHtml(checked) + '確認' : '') + '</small></span>' +
      (candidates.length ? carouselControls('comp-candidate-track', '追加構成', candidates.length) : '') + '</div>' +
      '<div class="comp-source-status">' + states + '</div>' + candidateCards + articleSection +
      '<p class="comp-candidates-foot">候補は出典で確認できます。詳細ガイドは照合後に掲載します。</p>';

    Array.prototype.forEach.call(panel.querySelectorAll('.comp-carousel-tools'), function (tools) {
      var target = tools.getAttribute('data-carousel-target');
      var track = panel.querySelector('#' + target);
      var previous = tools.querySelector('.comp-carousel-prev');
      var next = tools.querySelector('.comp-carousel-next');
      var status = tools.querySelector('.comp-carousel-status');
      if (!track || !previous || !next || !status) return;
      var update = function () {
        var first = track.firstElementChild;
        var gap = parseFloat(window.getComputedStyle(track).columnGap || window.getComputedStyle(track).gap) || 0;
        var step = first ? first.getBoundingClientRect().width + gap : 1;
        var start = Math.min(track.children.length, Math.floor((track.scrollLeft + 2) / step) + 1);
        var visible = Math.max(1, Math.ceil((track.clientWidth + 2) / step));
        var end = Math.min(track.children.length, start + visible - 1);
        status.textContent = start + '–' + end + ' / ' + track.children.length;
        tools.hidden = track.scrollWidth <= track.clientWidth + 2;
        previous.disabled = track.scrollLeft <= 2;
        next.disabled = track.scrollLeft + track.clientWidth >= track.scrollWidth - 2;
      };
      var scrollPage = function (direction) {
        var first = track.firstElementChild;
        var gap = parseFloat(window.getComputedStyle(track).columnGap || window.getComputedStyle(track).gap) || 0;
        var step = first ? first.getBoundingClientRect().width + gap : track.clientWidth;
        var cards = Math.max(1, Math.floor(track.clientWidth / step) - 1);
        track.scrollBy({ left: direction * step * cards, behavior: 'smooth' });
      };
      previous.addEventListener('click', function () { scrollPage(-1); });
      next.addEventListener('click', function () { scrollPage(1); });
      track.addEventListener('scroll', function () { window.requestAnimationFrame(update); });
      window.addEventListener('resize', update);
      update();
    });
  }

  fetch('./comp_candidates.json', { cache: 'no-store' })
    .then(function (response) { if (!response.ok) throw new Error('Candidate data is unavailable'); return response.json(); })
    .then(render)
    .catch(function () { render({ candidates: [], sources: {}, articles: [] }); });
})();
