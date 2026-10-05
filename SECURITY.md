# セキュリティ方針・開発チェックリスト

このアプリは個人PC上で動く、Googleカレンダーの読み取り専用クライアントです。
以下はOWASPとGoogleの推奨事項から、本アプリに必要な項目を選んだ開発基準です。
認証取得・専門家による侵入試験・OWASP全項目への準拠を保証するものではありません。

## 保護するものと前提

- 保護対象: Googleの更新トークン、アクセストークン、予定の内容。
- 想定する脅威: 認証情報の公開混入、悪意あるリンク・設定ファイル、ディスクからの認証情報持ち出し、依存パッケージ・CIの変更。
- 限界: 同じWindowsユーザー権限で実行されるマルウェアや管理者からは、DPAPIでも守り切れません。OS・ブラウザの更新とアカウント保護が別途必要です。
- 認証情報はAPI送信に使用します。予定内容はメモリ上で表示し、履歴・テレメトリー・クラッシュ送信は行いません。

## 実装・レビュー時のホワイトルール

### 認証と権限

- [ ] OAuthの要求スコープを `calendar.readonly` に限定する。
- [ ] 外部の既定ブラウザ、ループバックIP `127.0.0.1`、動的ポートを使用する。
- [ ] PKCE（S256）とstateの照合を公式ライブラリで行う。
- [ ] OAuthクライアントJSONの接続先をGoogle公式の認証・トークンURLに限定する。
- [ ] トークン・認可コード・認証URL全体をログ、エラー、スクリーンショット、Gitへ出さない。
- [ ] 既存MCP認証のインポートは利用者が明示した場合だけ行う。元の権限を継承するため、より広い権限の場合があると説明する。

### 保存・入力・通信

- [ ] Windowsはユーザー単位のDPAPIで認証ファイルを暗号化する。暗号化失敗時は保存しない。
- [ ] 旧Windows版の平文トークンは初回読み込みで原子的に暗号化し、置換成功までは元を保持する。
- [ ] Linuxは設定ディレクトリ700・認証ファイル600で保存する。OSのディスク暗号化は別途管理する。
- [ ] 「カレンダーで開く」はHTTPSのGoogleカレンダーURLだけを許可する。
- [ ] 予定のタイトルや場所はプレーンテキストとして描画する。HTML・スクリプトとして解釈しない。
- [ ] シェルにURLや利用者入力を連結しない。WindowsブラウザへはURLを標準入力のデータとして渡す。
- [ ] Google APIへの通信はTLS検証を有効にし、タイムアウトを設ける。サーバー例外の本文を画面へ出さない。

### 依存・CI・公開

- [ ] `uv.lock` をレビューし、`uv sync --locked` で再現する。
- [ ] 全ロック済み依存を、Windows専用・ビルド用を含めて既知脆弱性DBと照合する。
- [ ] Actionsは公式リポジトリの完全なコミットSHAに固定し、権限を `contents: read` にする。
- [ ] チェックアウト時の認証情報をワークツリーに残さない。
- [ ] Git履歴の秘密情報パターン検査と、配布対象の確認を実施する。
- [ ] 公開前に、Git作者メール・画像・ドキュメントの個人情報も確認する。作者情報の公開を望まない場合はGitHub noreplyを使用する。
- [ ] exeはCIのクリーン環境で生成する。認証ファイルを同梱しない。
- [ ] Windowsのテストと、生成exeそのものの起動検査を実行する。
- [ ] SHA-256チェックサムと配布元を確認する。チェックサムはコード署名の代わりではない。
- [ ] 未署名exeであること、実施していない試験を監査結果に明記する。

## 検査コマンド

```bash
uv sync --locked --dev --group security
uv run python scripts/check_security.py
uv run --group security bandit -r src scripts
uv run --group security python scripts/audit_dependencies.py
QT_QPA_PLATFORM=offscreen uv run pytest
```

Securityワークフローはpush・PR・週次で検査します。指摘を一律除外せず、原因を調べます。
Banditの `nosec` は、固定コマンドのシェルなし起動と公開トークンエンドポイントの誤検出について、該当行に理由を記載したものだけを許可します。
秘密情報パターン検査や脆弱性DBには検出限界があります。「指摘ゼロ」を「完全に安全」と表現しません。

## 問題の連絡・認証失効

認証情報が漏れた場合は、Googleアカウントの接続済みアプリから権限を取り消し、再認証してください。
トークン・認可コード・個人の予定を公開Issueに貼らないでください。
脆弱性の報告は、利用可能な場合はGitHubの非公開脆弱性報告機能を使用してください。

## 参照基準

- [OWASP Desktop App Security Top 10](https://owasp.org/projects/desktop-app-security-top-10)
- [OWASP Thick Client Application Security Verification Standard](https://owasp.org/projects/thick-client-application-security-verification-standard)
- [Google OAuth Best Practices](https://developers.google.com/identity/protocols/oauth2/resources/best-practices)
- [Google OAuth for Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Windows CryptProtectData](https://learn.microsoft.com/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata)
- [GitHub Actions Security Hardening](https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions)
