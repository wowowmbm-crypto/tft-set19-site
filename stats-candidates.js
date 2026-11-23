(function () {
  var SOURCE_URL = 'https://tft.ninja/comps?e=pbe';
  var escapeHtml = function (value) {
    return String(value).replace(/[&<>"']/g, function (character) {
      return {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
      }[character];
    });
  };

  function addStyle() {
    var style = document.createElement('style');
    style.textContent = [
      '.stats-only-units{display:flex;align-items:center;min-width:145px;color:#aeb8c5;font-size:12px;font-weight:700}',
      '.stats-only-units span{display:inline-flex;align-items:center;gap:6px;padding:7px 10px;border:1px dashed #80642a;border-radius:7px;background:#211c14;color:#f0d690}',
      '.stats-only-detail{max-width:760px}',
      '.stats-only-detail .candidate-metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:9px;margin:16px 0}',
      '.stats-only-detail .candidate-metric{padding:12px 8px;text-align:center;border:1px solid #ffffff15;border-radius:8px;background:#ffffff08}',
      '.stats-only-detail .candidate-metric small{display:block;color:#aeb8c5;font-size:12px}',
      '.stats-only-detail .candidate-metric b{display:block;margin-top:3px;font-size:20px;color:#f1f4f8}',
      '.stats-only-detail .callout{margin:14px 0}',
      '@media(max-width:560px){.stats-only-units{min-width:0;font-size:11px}.stats-only-detail .candidate-metrics{gap:5px}.stats-only-detail .candidate-metric{padding:10px 4px}.stats-only-detail .candidate-metric small{font-size:10px}.stats-only-detail .candidate-metric b{font-size:17px}}'
    ].join('');
    document.head.appendChild(style);
  }

  function compareRows() {
    var body = document.getElementById('compareRows');
    if (!body) return;
    body.innerHTML = comps.map(function (comp) {
      return '<tr><td><b>' + escapeHtml(comp.name) + '</b><br><span class="result">' + escapeHtml(comp.en) +
        '</span></td><td>' + escapeHtml(tierLabel(comp)) + '<br><span class="result">' + escapeHtml(comp.src) +
        '</span></td><td>' + escapeHtml(comp.style) + '</td><td>' + escapeHtml(comp.diff) +
        '</td><td>' + escapeHtml(performanceSummary(comp, 'avp')) + '</td><td>' +
        escapeHtml(performanceSummary(comp, 'win')) + '</td><td>' + escapeHtml(comp.learn) +
        '</td><td>' + escapeHtml(comp.cond) + '</td></tr>';
    }).join('');
  }

  function candidateDetail(comp, payload) {
    var tier = escapeHtml(comp.tier);
    var title = escapeHtml(comp.name);
    var checked = escapeHtml(payload.checked_at || '');
    var stats = performanceStats[comp.id];
    var pick = pickRates[comp.id].pct;
    var detail = document.getElementById('detail');
    detail.innerHTML = '<article class="panel stats-only-detail">' +
      '<button class="btn close" onclick="document.getElementById(\'detail\').innerHTML=\'\'">閉じる ×</button>' +
      '<div class="eyebrow">新着の統計候補 · ' + tier + '評価</div>' +
      '<h2>' + title + '</h2>' +
      '<p class="result">TFT Ninjaの直近1日統計 · ' + checked + '確認</p>' +
      '<div class="candidate-metrics">' +
      '<div class="candidate-metric"><small>平均順位</small><b>' + stats.avp.toFixed(2) + '</b></div>' +
      '<div class="candidate-metric"><small>1位率</small><b>' + stats.win.toFixed(1) + '%</b></div>' +
      '<div class="candidate-metric"><small>Pick率</small><b>' + escapeHtml(pick) + '</b></div>' +
      '</div>' +
      '<div class="callout"><b>統計候補：</b>出典のS/A評価とPick率をもとに掲載しています。構成ガイド、配置、アイテム、オーグメントは未確認です。Notion記事が見つかった場合も、統計・別ガイドとの照合後にのみ確定構成へ反映します。</div>' +
      '<p><a href="https://busy-ziconium-740.notion.site/1d3859a65b0a80f8adc3c0378eb3b007?v=41a859a65b0a80af8014000c747530dd&amp;p=41b859a65b0a80199190d863429bdd52&amp;pm=s" target="_blank" rel="noopener">Notion Set 19記事を照合する ↗</a></p>' +
      '<p><a href="' + SOURCE_URL + '" target="_blank" rel="noopener">TFT NinjaのPBE構成統計を見る ↗</a></p>' +
      '<p class="result">' + escapeHtml(payload.criteria || '') + '</p>' +
      '</article>';
    detail.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function initialize(payload) {
    if (!payload || !Array.isArray(payload.candidates)) return;
    var registered = new Set(comps.map(function (comp) {
      return String(comp.en || comp.name).trim().toLowerCase();
    }));
    var added = [];

    payload.candidates.forEach(function (candidate) {
      if (!candidate || !/^[a-z0-9-]{1,64}$/.test(candidate.slug || '')) return;
      if (!['S', 'A'].includes(candidate.tier)) return;
      if (typeof candidate.title !== 'string' || !candidate.title.trim()) return;
      var avp = Number(candidate.avp);
      var win = Number(candidate.win);
      var playRate = Number(candidate.play_rate);
      if (!(avp >= 1 && avp <= 8 && win >= 0 && win <= 100 && playRate >= 0.3 && playRate <= 100)) return;
      if (registered.has(candidate.title.trim().toLowerCase())) return;

      var id = 'statcandidate-' + candidate.slug;
      if (comps.some(function (comp) { return comp.id === id; })) return;
      var rate = playRate.toFixed(1) + '%';
      var entry = {
        id: id,
        name: candidate.title.trim(),
        en: candidate.title.trim(),
        tier: candidate.tier,
        src: 'TFT Ninja 統計候補',
        style: '統計候補',
        diff: 'ガイド未確認',
        role: '統計のみ',
        learn: '統計候補 · Notion記事照合待ち · Pick率 ' + rate,
        risk: '統計候補',
        cond: 'TFT Ninjaの統計とNotion・別ガイドを照合。統計だけで構成ガイドを確定しません。',
        board: '詳細は主要サイトで未確認',
        items: [],
        aug: [],
        unlock: [],
        prog: [],
        bail: '統計候補です。構成の盤面やガイドが確認できるまで、編成の詳細は掲載しません。',
        evidence: 'TFT Ninjaの直近1日統計から自動検出した候補です。出典の評価・Pick率は更新ごとに変わります。',
        stats: 'ガイド未確認のため、平均順位・1位率・Pick率のみを掲載しています。',
        statsOnly: true
      };
      performanceStats[id] = { avp: avp, win: win, ref: candidate.title, match: '統計候補' };
      pickRates[id] = { pct: rate };
      added.push(entry);
      registered.add(candidate.title.trim().toLowerCase());
    });

    if (!added.length) return;
    addStyle();

    var originalCompIcons = compIcons;
    compIcons = function (comp) {
      if (comp && comp.statsOnly) {
        return '<div class="stats-only-units" aria-label="統計候補。構成ユニット未確認"><span>📊 統計候補 · 編成未確認</span></div>';
      }
      return originalCompIcons(comp);
    };

    var originalShowDetail = showDetail;
    showDetail = function (id) {
      var comp = comps.find(function (entry) { return entry.id === id; });
      if (comp && comp.statsOnly) {
        candidateDetail(comp, payload);
        return;
      }
      return originalShowDetail(id);
    };

    comps.push.apply(comps, added);
    render();
    compareRows();
  }

  fetch('./stats_candidates.json', { cache: 'no-store' })
    .then(function (response) {
      if (!response.ok) throw new Error('Statistics candidate data is unavailable');
      return response.json();
    })
    .then(initialize)
    .catch(function () {
      // The hand-curated guide list remains usable if the updater has not
      // published candidate data yet or the optional data file is unavailable.
    });
})();
