TFT Set 19 構成データベース

更新とデータの扱い

■ 自動更新のタイミング
GitHub Actions の「Update TFT Set 19 site data」は、毎週日曜 09:00（日本時間）に自動実行されます。手動更新する場合は、リポジトリの Actions → Update TFT Set 19 site data → Run workflow を選びます。
変更があれば GitHub Actions がデータを main にコミットし、連携済みの Vercel がサイトを再デプロイします。変更がなければコミットも再デプロイも発生しません。

■ 自動で更新される情報
・TFT Ninja の PBE統計を取得し、登録済み構成は名称が一致した場合だけ数値を更新します。一致しない構成の数値は前回の値を保ちます。
・新しい構成候補は TFT Ninja の統計、Mobalytics の Set 19 PBE Tier一覧、TFT Coach の Set 19構成一覧から自動検出します。別名と思われる候補をまとめ、各サイトの評価・統計・出典リンクを表示します。
・Notionの新着記事メタデータも候補欄に表示します。タイトル、公開URL、投稿日、投稿者、パッチ名のみを読み取り、記事本文は取得しません。構成名と結び付かない記事は記事候補として分けて表示します。
・候補の自動検出はガイドの自動作成ではありません。盤面、装備、オーグメント、配置、プレイ条件は出典を確認してから構成一覧へ追加します。取得に失敗した情報源は前回の結果を保持し、画面に状態を表示します。
・YouTube は YOUTUBE_API_KEY を登録した場合に限り、直近72時間の TFT Set 19 動画を検索し、最大3件のピックアップを更新します。キー未登録や取得失敗時は、前回の表示を保ちます。
・X は自動取得しません。X_BEARER_TOKEN はワークフローから呼び出されず、X API の利用料も発生しません。
・この処理に ChatGPT / OpenAI のAPIキーやトークンは使いません。

■ Notion記事候補の週次取得（任意）
NotionのSet 19データベースから、記事名・投稿日・投稿者・パッチ名・記事URLだけを読み取り、直近90日分を構成候補欄に表示します。本文の自動要約や、候補から構成一覧への自動登録はしません。
自動取得する場合は、Notionで「コンテンツを読み取る」権限だけの内部連携を作り、Set 19データベースに接続を共有します。GitHubリポジトリの Settings → Secrets and variables → Actions → New repository secret に NOTION_API_KEY を登録してください。トークンはチャットやサイトのファイルに貼らないでください。データベースIDが既定値と異なる場合のみ、同じ画面の Variables に NOTION_DATABASE_ID を登録します。
接続前も統計・YouTube更新は通常どおり動作し、Notion候補は未接続と表示します。API取得に失敗した場合は保存済み候補を保持します。

■ YouTube API キーの登録（任意）
GitHub リポジトリの Settings → Secrets and variables → Actions → New repository secret を開き、名前を YOUTUBE_API_KEY として Google Cloud の YouTube Data API v3 キーを登録します。キーは GitHub Secrets にだけ置き、サイトのコードやチャットに貼らないでください。キーがない場合も統計の週次更新は動きます。

■ 構成・ガイドを確認する優先ソース
まず、Set 19 の翻訳記事と構成ガイドがまとまった Notion を確認します。PBE 表記と投稿日が新しい記事を優先し、構成候補、プレイ条件、アイテム・オーグメントの根拠を拾います。
Notion 翻訳まとめ（Set19）: https://busy-ziconium-740.notion.site/1d3859a65b0a80f8adc3c0378eb3b007?v=41a859a65b0a80af8014000c747530dd&p=41b859a65b0a80199190d863429bdd52&pm=s
Notion の「構成紹介場所まとめ（PBE）」: https://busy-ziconium-740.notion.site/PBE-3b3859a65b0a80928f3bd7b2af81dadb?pvs=23

Notion 内の構成紹介・照合先：
・TFTAcademy Set 19: https://tftacademy.com/tierlist/comps/set19
・MetaTFT PBE構成: https://www.metatft.com/pbe-comps
・MetaTFT Pro構成: https://www.metatft.com/pro-comps?set=pbe
・TFT Labs Set 19: https://tftlabs.cc/ko/s19
・DataTFT PBE統計: https://www.datatft.com/explorerForPBE
・TFT Pro Radar: https://tftproradar.com/

Notion の記事だけを根拠に統計ランクを上げたり、構成を自動で追加したりはしません。PBEの最新記事を候補の発見に使い、統計サイトや別の構成ガイドと照合してから一覧へ反映します。日本語オーグメント名、推奨装備、配置、プレイ条件、ガイド文は人が根拠を確認して編集します。
週次更新では Notion 記事のメタデータだけを自動取得します。記事の内容と統計を照合し、配置・装備・オーグメント・プレイ条件を確認してから手動で構成一覧へ反映してください。Notionの記事だけで評価を上げたり、構成を自動登録したりはしません。

■ 実行結果の見方
Actions の実行が Success でも、YouTubeキー未登録、名称照合なし、新規候補なしの場合があります。実行ログで各データ元の取得結果を確認してください。構成ガイドの内容は自動更新されないため、数値更新とガイド更新は別の作業です。

■ 公開方法（Vercel）
このサイトは静的ファイルで動作し、公開ページにAPIキーを置きません。GitHub リポジトリと Vercel プロジェクトを連携し、Framework Preset は Other、Build Command は空欄、Output Directory は . に設定します。設定済みの場合、main のコミットから自動デプロイされます。
