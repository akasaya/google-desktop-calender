import argparse
import sys
from pathlib import Path

from .calendar import CalendarClient, CalendarError
from .storage import config_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="今日のGoogleカレンダーをデスクトップに表示")
    parser.add_argument("--demo", action="store_true", help="Google接続なしでサンプル表示")
    parser.add_argument("--login", action="store_true", help="ブラウザでGoogleに接続")
    parser.add_argument("--config-dir", type=Path, default=config_dir())
    parser.add_argument(
        "--import-mcp-tokens", type=Path, help="既存Calendar MCP認証を明示的にコピー"
    )
    parser.add_argument("--client-secret", type=Path)
    parser.add_argument("--account", default="normal")
    args = parser.parse_args()
    if args.login:
        if not args.client_secret:
            parser.error("--client-secret が必要です")
        try:
            CalendarClient(args.config_dir).login(args.client_secret)
        except CalendarError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except Exception:
            print("Googleへの接続を完了できませんでした。再試行してください。", file=sys.stderr)
            return 1
        print("Googleに接続しました。")
        return 0
    if args.import_mcp_tokens:
        if not args.client_secret:
            parser.error("--client-secret が必要です")
        try:
            CalendarClient(args.config_dir).import_mcp(
                args.import_mcp_tokens, args.client_secret, args.account
            )
        except Exception:
            print(
                "認証を取り込めませんでした。ファイル・アカウント・接続を確認してください。",
                file=sys.stderr,
            )
            return 1
        print("認証を取り込みました。元ファイルは変更していません。")
        return 0

    from PySide6.QtWidgets import QApplication

    from .window import CalendarWindow

    app = QApplication(sys.argv[:1])
    app.setApplicationName("Google Desktop Calendar")
    window = CalendarWindow(args.config_dir, demo=args.demo)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
