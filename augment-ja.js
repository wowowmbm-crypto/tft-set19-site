(() => {
  const names = new Map([
    ['Extra Buckles', '追加のバックル'], ['Missed Connections', 'ミスコネクション'],
    ['Baron’s Lair', 'バロンの巣'], ['Golden Gamble', '黄金の博打'], ['Ascension', 'アセンション'],
    ['Latent Forge', '未来の鍛冶場'], ['Heroic Grab Bag', '英雄のラッキーバッグ'],
    ['Portable Forge', 'ポータブル フォージ'], ['Living Forge', '歩く鍛冶場'],
    ['Feeling Lucky', 'ツイてる気分+'], ['Small Grab Bag', '小さな福袋'],
    ['Verticality II', '垂直性 II'], ['Slammin', '叩きつけ'], ['Upward Mobility', '上方移動'],
    ['Late Game Specialist', 'レイトゲーム スペシャリスト'], ['Capital Gains', 'キャピタルゲイン'],
    ['Birthday Reunion', 'バースデー リユニオン'], ['Money Hungry', '金に飢えし者'],
    ['Level Up!', 'レベルアップ！'], ['Boxing Lessons', 'ボクシングのレッスン'],
    ['Electrocharge', '放電'], ['Slice of Life', '普通の日々'],
    ['Worth the Wait', '待つ価値あり'], ['No Scout No Pivot', '偵察なし、変更なし']
  ]);
  const japanese = value => {
    const match = value.match(/（([^）]+)）$/);
    return match ? (names.get(match[1]) || value.slice(0, match.index)) : value;
  };
  const refresh = () => {
    const detail = document.getElementById('detail');
    if (!detail) return;
    detail.querySelectorAll('.detail-section').forEach(section => {
      if (!section.querySelector('h3')?.textContent.includes('オーグメント')) return;
      section.querySelectorAll('.augment-chip, li').forEach(item => {
        const current = item.textContent.trim();
        const source = item.matches('.augment-chip') ? current.replace(/^◈\s*/, '') : current;
        const label = japanese(source);
        const display = item.matches('.augment-chip') ? '◈ ' + label : label;
        if (current !== display) item.textContent = display;
      });
      if (!section.querySelector('.augment-source-note')) {
        const note = document.createElement('p');
        note.className = 'formation-note augment-source-note';
        note.textContent = 'MetaTFTで照合できた名称は日本語表記に統一しています。MetaTFT側ではSet 19未ランキングのためSet 18一覧が表示され、一覧にないSet 19候補は既存の日本語候補名を表示しています。';
        note.style.cssText = 'display:block;width:100%;max-width:100%;box-sizing:border-box;grid-column:1 / -1;flex:1 1 100%;margin:12px 0 0;line-height:1.6;overflow-wrap:anywhere;';
        const link = document.createElement('a');
        link.href = 'https://www.metatft.com/augments?set=pbe';
        link.target = '_blank';
        link.rel = 'noopener';
        link.textContent = ' MetaTFTの一覧 ↗';
        note.append(link);
        (section.querySelector('.augment-list, ul') || section).after(note);
      }
    });
  };
  new MutationObserver(refresh).observe(document.documentElement, { childList: true, subtree: true });
  refresh();
})();
