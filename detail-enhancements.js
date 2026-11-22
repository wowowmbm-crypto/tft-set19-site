(function () {
  var profiles = {
    ap: {
      artifact: [
        { name: '枯死の宝石', key: 'blightingjewel' },
        { name: 'ゾーニャの遡時計', key: 'zhonyasparadox' }
      ],
      radiant: [
        { name: 'レディアント ブルーバフ', key: 'bluebuff' },
        { name: 'レディアント ハンド オブ ジャスティス', key: 'handofjustice' }
      ],
      emblem: [
        { name: 'プロディジーの紋章', key: 'prodigy' },
        { name: 'K/DAの紋章', key: 'kda' }
      ]
    },
    ad: {
      artifact: [
        { name: 'ゴールド コレクター', key: 'goldcollector' },
        { name: 'ウィッツ エンド', key: 'witsend' }
      ],
      radiant: [
        { name: 'レディアント ストライカー フレイル', key: 'strikersflail' },
        { name: 'レディアント ジャイアント スレイヤー', key: 'giantslayer' }
      ],
      emblem: [
        { name: 'スレイヤーの紋章', key: 'mosher' },
        { name: '早業の紋章', key: 'swiftstriker' }
      ]
    },
    tank: {
      artifact: [
        { name: 'ライトシールドのクレスト', key: 'lightshieldcrest' },
        { name: '不滅の協定', key: 'eternalpact' }
      ],
      radiant: [
        { name: 'レディアント ステラックの篭手', key: 'steraksgage' },
        { name: 'レディアント ガーゴイル ストーンプレート', key: 'gargoylestoneplate' }
      ],
      emblem: [
        { name: 'ボディーガードの紋章', key: 'bodyguard' },
        { name: 'ジャガーノートの紋章', key: 'juggernaut' }
      ]
    }
  };

  var apCarryNames = [
    'ジグス', 'レナータ', 'マルザハール', 'アルーン', 'オーロラ',
    'ティーモ', 'セラフィーン', 'タリヤ', 'ケイル', 'ニーコ', 'グウェン'
  ];

  function itemUrl(type, key) {
    if (type === 'artifact') {
      return 'https://tftraits.com/assets/set19/items/da_artifact_' + key + '.png';
    }
    if (type === 'radiant') {
      return 'https://tftraits.com/assets/set19/items/da_' + key + 'radiant.png';
    }
    return 'https://tftraits.com/assets/set19/emblems/da_' + key + '19_emblem.png';
  }

  function matchesAny(name, candidates) {
    return (candidates || []).some(function (candidate) {
      return champKey(candidate) === champKey(name);
    });
  }

  function roleForUnit(comp, unit) {
    var roles = carryRoles[comp.id] || { main: [], sub: [] };
    if (matchesAny(unit, (roles.main || []).concat(roles.sub || []))) {
      return matchesAny(unit, apCarryNames) ? 'ap' : 'ad';
    }
    var formation = formations[comp.id] || { front: [] };
    if (matchesAny(unit, formation.front || [])) return 'tank';
    return '';
  }

  function renderSpecialItems(role) {
    if (!role || !profiles[role]) return '';
    var profile = profiles[role];
    var groups = [
      ['artifact', 'Artifact'],
      ['radiant', 'Radiant'],
      ['emblem', 'Emblem']
    ];
    return '<div class="special-item-options" aria-label="追加アイテム候補">' +
      groups.map(function (group) {
        var items = profile[group[0]] || [];
        return '<div class="special-item-group"><small>' + group[1] + '</small>' +
          '<div class="special-item-list">' + items.map(function (item) {
            return '<span class="special-item-chip" title="' + item.name + '">' +
              imageTag(itemUrl(group[0], item.key), item.name) +
              '<span>' + item.name + '</span></span>';
          }).join('') + '</div></div>';
      }).join('') + '</div>';
  }

  function renderDetailedBuilds(comp) {
    var rows = (comp.items || []).map(function (item) {
      var role = roleForUnit(comp, item[0]);
      var roleLabel = role === 'tank' ? 'タンク' : role ? 'キャリー' : '';
      return '<tr><td><div class="unit-with-items">' +
        imageTag(champUrl(item[0]), item[0], 'unit-portrait') +
        '<div><b>' + item[0] + '</b>' +
        (roleLabel ? '<br><span class="unit-role-badge">' + roleLabel + '</span>' : '') +
        '</div></div></td><td><div class="item-list">' + itemChips(item[1]) + '</div>' +
        renderSpecialItems(role) + '</td></tr>';
    }).join('');
    return '<div class="tablewrap"><table class="unit-build-table"><thead><tr>' +
      '<th>チャンピオン</th><th>通常アイテム・追加候補</th></tr></thead><tbody>' +
      rows + '</tbody></table></div>' +
      '<p class="special-data-note">追加候補はMetaTFTのSet 19・直近3日アイテム統計を参考に、キャリー／タンクの役割別に選んでいます。構成ごとの個別成績ではないため、盤面や特性に合わせて選んでください。</p>' +
      '<div class="special-data-sources">' +
      '<a href="https://www.metatft.com/items/artifact?set=TFTSet19" target="_blank" rel="noopener">MetaTFT Artifact ↗</a>' +
      '<a href="https://www.metatft.com/items/radiant?set=TFTSet19" target="_blank" rel="noopener">Radiant ↗</a>' +
      '<a href="https://www.metatft.com/items/emblem?set=TFTSet19" target="_blank" rel="noopener">Emblem ↗</a>' +
      '</div>';
  }

  var renderOriginalDetail = showDetail;
  showDetail = function (id) {
    renderOriginalDetail(id);
    var comp = comps.find(function (entry) { return entry.id === id; });
    var detail = document.getElementById('detail');
    var panel = detail && detail.querySelector('.panel');
    if (!comp || !panel) return;

    var sections = Array.from(panel.querySelectorAll('.detail-section'));
    var augmentSection = sections.find(function (section) {
      var heading = section.querySelector('h3');
      return heading && heading.textContent.trim() === '最優先オーグメント';
    });
    if (augmentSection) {
      var augments = comp.aug || [];
      var first = augments[0];
      augmentSection.innerHTML = '<h3>おすすめオーグメント</h3>' +
        (first
          ? '<div class="augment-primary"><b>最優先</b><span class="augment-chip">◈ ' + first + '</span></div>'
          : '<p>おすすめオーグメントは未登録です。</p>') +
        (augments.length > 1
          ? '<div class="augment-candidates"><strong>追加候補</strong><div class="augment-list">' +
            augments.slice(1).map(function (name) {
              return '<span class="augment-chip">◈ ' + name + '</span>';
            }).join('') + '</div></div>'
          : '');
    }

    var buildSection = sections.find(function (section) {
      var heading = section.querySelector('h3');
      return heading && heading.textContent.trim() === 'ユニット別ビルド';
    });
    if (buildSection) {
      buildSection.innerHTML = '<h3>ユニット別ビルド</h3>' + renderDetailedBuilds(comp);
    }
    detail.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };
})();
