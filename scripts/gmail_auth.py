#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.utils.gmail import GmailSettings, authorize_gmail


def main() -> None:
    settings = GmailSettings.from_env()
    token_path = authorize_gmail(settings)
    print(f"Gmail token saved to {token_path}")


if __name__ == "__main__":
    main()
