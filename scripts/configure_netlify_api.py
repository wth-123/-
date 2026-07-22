from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import urlparse


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/configure_netlify_api.py https://your-api.onrender.com")

    api_url = sys.argv[1].rstrip("/")
    parsed = urlparse(api_url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise SystemExit("API URL must be an HTTPS URL")

    target = Path("app/templates/config.js")
    target.write_text(
        "// Public API endpoint. Do not place secrets in this file.\n"
        f"window.API_BASE = {api_url!r};\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
