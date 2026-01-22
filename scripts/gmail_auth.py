#!/usr/bin/env python3
from __future__ import annotations

from app.utils.gmail import GmailSettings, authorize_gmail


def main() -> None:
    settings = GmailSettings.from_env()
    token_path = authorize_gmail(settings)
    print(f"Gmail token saved to {token_path}")


if __name__ == "__main__":
    main()
