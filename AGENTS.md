# 開発ルール

- 日本語で報告し、変更前に README.md と git status を確認する。
- Python 3.12 と、このプロジェクト専用の uv / .venv / uv.lock を使う。
- 依存追加は uv add、再現環境は uv sync --locked --dev。親の仮想環境を変更しない。
- Google カレンダーは読み取り専用。API通信と認証は GUI スレッドから分離する。
- 日付の境界は設定タイムゾーンで計算する。終日予定の終了日は排他的。
- 認証情報、実際の予定、ユーザーのスクリーンショットをログ・Gitに含めない。
- 変更後は uv run ruff check .、uv run ruff format --check .、QT_QPA_PLATFORM=offscreen uv run pytest を実行する。
- GUI変更時はデモ画面も確認する。実Google接続とデモ・モック試験を区別して報告する。
- Agent.md はこのファイルへのリンク。作業方針はここにまとめる。
- セキュリティ変更・公開前は SECURITY.md のチェックリストを適用する。秘密情報検査・Bandit・全ロック依存の脆弱性検査を実行し、未検証範囲を区別する。
- OAuthの接続先・外部リンクは許可リストで制限する。PKCE・state・TLS検証を無効化しない。
- Windowsの認証保存はDPAPIを使用する。暗号化エラー時に平文保存へ切り替えない。
