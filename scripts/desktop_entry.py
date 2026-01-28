import os

import uvicorn

from main import app


def main() -> None:
    host = os.getenv("SFO_HOST", "127.0.0.1")
    port = int(os.getenv("SFO_PORT", "8000"))
    log_level = os.getenv("SFO_LOG_LEVEL", "info")
    uvicorn.run(app, host=host, port=port, log_level=log_level)


if __name__ == "__main__":
    main()
