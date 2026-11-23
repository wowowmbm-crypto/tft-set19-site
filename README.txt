TFT Set 19 構成データベース（静的サイト）

公開方法（Vercel）
1. Vercelにログインします。
2. Dashboardの「Add New...」→「Project」へ進みます。
3. 「Deploy」画面でこのZIPを展開したフォルダをアップロードするか、GitHubリポジトリとして取り込みます。
4. Framework Presetは「Other」、Build Commandは空欄、Output Directoryは「.」にします。
5. Deployを実行すると vercel.app の公開URLが発行されます。

このサイトの表示は静的ファイルで動き、公開サイトにAPIキーを置く必要はありません。
統計とSNS情報は、GitHub Actionsから手動更新できます。SNS取得キーはGitHub Secretsにのみ登録します。

更新ボタン（GitHub Actions）
リポジトリの Actions → Update TFT Set 19 site data → Run workflow から手動更新できます。
TFT Ninjaの構成統計と候補構成は、GitHub Actionsの実行枠で取得します。

X・YouTubeのピックアップを更新する設定
Run workflowの実行時に各サービスの公開APIを使います。各APIキーをこのリポジトリの
Settings → Secrets and variables → Actions に、次の名前で登録してください。
  X_BEARER_TOKEN   X APIのBearer Token（読み取り）
  YOUTUBE_API_KEY  YouTube Data API v3のAPI key
キーはGitHub ActionsのSecretsへ直接登録し、サイトやチャットには載せないでください。
どちらか一方のキーだけ設定した場合も、そのサービスの投稿だけ更新します。
直近72時間の情報からX・YouTube各最大3件（合計最大6件）を選び、表示数・いいね数・再生数を掲載します。
キー未設定、またはAPI取得に失敗したサービスは、最後に取得できた情報を保ちます。
