# GCP Telegram Bot - Railway version

This package preserves the original bot logic and browser flow.

## Railway variables

Required:
- `API_ID`
- `API_HASH`
- `TELEGRAM_BOT_TOKEN`

`BOT_TOKEN` is also accepted for compatibility.

Do not add `OPENAI_API_KEY`.

## Important

The bot still expects the original `https://www.skills.google/google_sso...` input handled by the original code.
No `accounts.google.com/AddSession` handler was added.

The browser still runs with `headless=False`; Railway runs it under Xvfb so the original Playwright flow can operate without changing the automation logic.
