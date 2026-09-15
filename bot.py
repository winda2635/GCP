import asyncio
import base64
import contextlib
import html
import io
import json
import os
import re
import traceback
from urllib.parse import urlparse, parse_qs

from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeFilename

from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
    expect,
)

# ==========================================================
# Configuration
# ==========================================================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

# ⚠️ مهم لـ Railway: استخدم مساراً قابلاً للكتابة. عادةً ما يكون /tmp آمناً.
# إذا قمت بتركيب Volume على Railway، ضع المسار هنا (مثال: /app/browser_profile)
BROWSER_PROFILE_DIR = os.environ.get("BROWSER_PROFILE_DIR", "/tmp/browser_profile")

# يتم إنشاء القفل داخل main() ليكون مرتبطًا بحلقة الأحداث
BROWSER_LOCK: asyncio.Lock | None = None

print("STEP 1: Python started", flush=True)

client = TelegramClient("railway_bot", API_ID, API_HASH)

# ==========================================================
# Templates
# ==========================================================
VLESS_TEMPLATE = (
    "vless://29eb2a3e-4847-43c6-ba2f-b1b323bd39d6@google.com:443"
    "?path=%2FMustapha_Bacha35&security=tls&encryption=none"
    "&host={domain}&type=ws&sni=youtube.com#%40Mustapha_Bacha35"
)

JSON_TEMPLATE = r'''{
  "dns": {
    "fallbackStrategy": "disabledIfAnyMatch",
    "hosts": {},
    "servers": [
      {
        "address": "tcp://8.8.8.8",
        "fakedns": [
          {
            "ipPool": "198.18.0.0/15",
            "poolSize": 65535
          }
        ],
        "queryStrategy": "UseIPv4"
      }
    ]
  },
  "inbounds": [
    {
      "listen": "0.0.0.0",
      "port": "1080",
      "protocol": "dokodemo-door",
      "settings": {
        "network": "tcp,udp",
        "followRedirect": true
      },
      "tag": "tun-inbound"
    },
    {
      "listen": "127.0.0.1",
      "port": "10808",
      "protocol": "socks",
      "settings": {
        "auth": "noauth",
        "udp": true
      },
      "tag": "socks-inbound"
    }
  ],
  "log": {
    "loglevel": "warning"
  },
  "outbounds": [
    {
      "mux": {
        "enabled": false
      },
      "protocol": "vless",
      "proxySettings": {
        "tag": "Mustapha_Bacha35",
        "transportLayer": true
      },
      "settings": {
        "vnext": [
          {
            "address": "yt3.ggpht.com",
            "port": 443,
            "users": [
              {
                "encryption": "none",
                "flow": "",
                "id": "29eb2a3e-4847-43c6-ba2f-b1b323bd39d6",
                "level": 8
              }
            ]
          }
        ]
      },
      "streamSettings": {
        "network": "ws",
        "security": "tls",
        "tlsSettings": {
          "allowInsecure": true,
          "serverName": "yt3.ggpht.com"
        },
        "wsSettings": {
          "headers": {
            "Host": "__DOMAIN__"
          },
          "path": "/Mustapha_Bacha35"
        }
      },
      "tag": "VLESS"
    },
    {
      "domainStrategy": "AsIs",
      "protocol": "http",
      "settings": {
        "servers": [
          {
            "address": "57.144.120.4",
            "port": 8080
          }
        ],
        "headers": {
          "Host": "yt3.ggpht.com:443",
          "Proxy-Connection": "keep-alive",
          "User-Agent": "FBAV/571.0.0.44.73",
          "X-iorg-bsid": "Internet.org"
        }
      },
      "tag": "Mustapha_Bacha35"
    },
    {
      "protocol": "freedom",
      "tag": "direct"
    },
    {
      "protocol": "blackhole",
      "tag": "block"
    }
  ],
  "policy": {
    "levels": {
      "8": {
        "connIdle": 300,
        "downlinkOnly": 1,
        "handshake": 4,
        "uplinkOnly": 1
      }
    }
  },
  "routing": {
    "domainStrategy": "AsIs",
    "rules": [
      {
        "outboundTag": "direct",
        "protocol": [
          "dns"
        ],
        "type": "field"
      },
      {
        "inboundTag": [
          "tun-inbound",
          "socks-inbound"
        ],
        "outboundTag": "VLESS",
        "type": "field"
      }
    ]
  }
}'''

DARKTUNNEL_BASE_URI = (
    "darktunnel://eyJ0eXBlIjoiVkxFU1MiLCJuYW1lIjoi2KjYr9mI2YYg2LnYsdmI2LYg2KPZiNix2YrYr9mIINis2YrYstmKIiwid"
    "mxlc3NUdW5uZWxDb25maWciOnsidjJyYXlDb25maWciOnsiaG9zdCI6Inl0My5nZ3BodC5jb20iLCJwb3J0Ijo0NDMsInV1aWQiOiIy"
    "OWViMmEzZS00ODQ3LTQzYzYtYmEyZi1iMWIzMjNiZDM5ZDYiLCJzZXJ2ZXJOYW1lSW5kaWNhdGlvbiI6Inl0My5nZ3BodC5jb20iLCJ3c1"
    "BhdGgiOiIvTXVzdGFwaGFfQmFjaGEzNSIsIndzSGVhZGVySG9zdCI6Im11c3RhcGhhMzUtNTk4NDcyOTI5Mzg1LnVzLWNlbnRyYWwxLnJ1"
    "bi5hcHAifSwiaW5qZWN0Q29uZmlnIjp7ImVuYWJsZWQiOnRydWUsIm1vZGUiOiJQUk9YWSIsInByb3h5SG9zdCI6IjU3LjE0NC4xMjAu"
    "NCIsInBheWxvYWQiOiJDT05ORUNUIFtob3N0X3BvcnRdIEhUVFAvMS4xW2NybGZdVXNlci1BZ2VudDogRkJBVi81NzEuMC4wLjQ0Ljcz"
    "W2NybGZdWC1JT1JHLUJTSUQ6IEludGVybmV0Lm9yZ1tjcmxmXVtjcmxmXSJ9fX0="
)


# ==========================================================
# Utility helpers
# ==========================================================
def debug_log(step: str, message: str):
    print(f"[{step}] {message}", flush=True)


def _clean_browser_profile():
    """Remove stale Chrome SingletonLock left by a crashed container."""
    lock = os.path.join(BROWSER_PROFILE_DIR, "SingletonLock")
    if os.path.exists(lock):
        with contextlib.suppress(OSError):
            os.remove(lock)


def extract_domain_from_service_url(service_url: str) -> str:
    s = (service_url or "").strip()
    if s.startswith("http://") or s.startswith("https://"):
        return urlparse(s).netloc.strip()
    return s.replace("http://", "").replace("https://", "").split("/")[0].strip()


def extract_project_id(url: str):
    for pattern in (
        r"(qwiklabs-gcp-[\w-]+)",
        r"project[=/]([\w-]+)",
        r"projects/([\w-]+)",
    ):
        m = re.search(pattern, url or "")
        if m:
            return m.group(1)
    return None


def _b64_pad(s: str) -> str:
    return s + ("=" * ((4 - (len(s) % 4)) % 4)) if s else s


def darktunnel_decode(uri: str) -> dict:
    b64 = _b64_pad(uri.split("darktunnel://", 1)[1].strip())
    return json.loads(base64.b64decode(b64.encode("utf-8")).decode("utf-8"))


def darktunnel_encode(data: dict) -> str:
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "darktunnel://" + base64.b64encode(raw).decode("utf-8")


def build_darktunnel_uri_with_host(new_host: str) -> str:
    data = darktunnel_decode(DARKTUNNEL_BASE_URI)
    stack = [data]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            if "wsHeaderHost" in cur:
                cur["wsHeaderHost"] = new_host
            stack.extend(v for v in cur.values() if isinstance(v, (dict, list)))
        elif isinstance(cur, list):
            stack.extend(v for v in cur if isinstance(v, (dict, list)))
    return darktunnel_encode(data)


async def generate_and_send_dark_file(chat_id: int, domain: str):
    new_uri = build_darktunnel_uri_with_host(domain)
    safe_domain = re.sub(r"[^a-z0-9\.\-]+", "_", domain.lower()).strip("_")
    tg_fname = f"youtube-config-{safe_domain}.dark"

    bio = io.BytesIO(new_uri.encode("utf-8"))
    bio.name = tg_fname
    await client.send_file(
        chat_id,
        bio,
        force_document=True,
        attributes=[DocumentAttributeFilename(tg_fname)],
        caption=f"DarkTunnel files are ready:\n{domain}",
    )


async def handle_error(page, chat_id, step_name, error_msg):
    """Send a useful error report without masking the original exception."""
    print(f"Error at {step_name}: {error_msg}", flush=True)

    safe_error_msg = str(error_msg)
    if len(safe_error_msg) > 1200:
        safe_error_msg = safe_error_msg[:1200] + "\n..."

    screenshot_path = None

    try:
        if page is not None and not page.is_closed():
            safe_step = re.sub(r"[^a-zA-Z0-9_-]+", "_", step_name).strip("_") or "error"
            screenshot_path = os.path.abspath(f"error_{safe_step}.png")
            try:
                await page.screenshot(path=screenshot_path, full_page=True)
                await client.send_file(
                    chat_id,
                    file=screenshot_path,
                    caption=(
                        f"Error in step:\n{step_name}\n\n"
                        f"Error details:\n{safe_error_msg}"
                    ),
                )
            except Exception as shot_err:
                print(f"Screenshot failed: {shot_err}", flush=True)
                await client.send_message(
                    chat_id,
                    f"Error in step: {step_name}\n\n"
                    f"Error details:\n{safe_error_msg}",
                )
        else:
            await client.send_message(
                chat_id,
                f"Error in step: {step_name}\n\n"
                f"Error details:\n{safe_error_msg}",
            )
    except Exception as report_error:
        print(f"Failed to send error report: {report_error}", flush=True)
        with contextlib.suppress(Exception):
            await client.send_message(
                chat_id,
                f"Error in step: {step_name}\n\nError details:\n{safe_error_msg}",
            )
    finally:
        if screenshot_path and os.path.exists(screenshot_path):
            with contextlib.suppress(OSError):
                os.remove(screenshot_path)


async def log_page_state(page, step: str, include_body=False, body_limit=3000):
    try:
        debug_log(step, f"URL: {page.url}")
    except Exception as e:
        debug_log(step, f"Could not read URL: {type(e).__name__}: {e}")
    try:
        debug_log(step, f"Title: {await page.title()}")
    except Exception as e:
        debug_log(step, f"Could not read title: {type(e).__name__}: {e}")
    if include_body:
        try:
            body = re.sub(
                r"\s+",
                " ",
                (await page.locator("body").inner_text(timeout=5000)).strip(),
            )
            debug_log(step, f"Body sample: {body[:body_limit]}")
        except Exception as e:
            debug_log(step, f"Could not read body: {type(e).__name__}: {e}")


async def save_debug_screenshot(page, step: str):
    try:
        safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", step).strip("_") or "debug"
        path = os.path.abspath(f"debug_{safe}.png")
        await page.screenshot(path=path, full_page=True)
        debug_log(step, f"Diagnostic screenshot saved: {path}")
        return path
    except Exception as e:
        debug_log(step, f"Could not save screenshot: {type(e).__name__}: {e}")
        return None


async def log_exception(page, step: str, exc: Exception, include_body=True):
    debug_log(step, f"ERROR: {type(exc).__name__}: {exc}")
    await log_page_state(page, step, include_body)
    await save_debug_screenshot(page, step)


# ==========================================================
# Lab session monitoring
# ==========================================================
async def check_lab_session_status(page, step="LAB CHECK"):
    try:
        current_url = (page.url or "").lower()
    except Exception:
        current_url = ""

    skills_page = (
        "cloudskillsboost.google" in current_url
        or "skills.google" in current_url
    )
    if not skills_page:
        return False

    try:
        body_text = (await page.locator("body").inner_text(timeout=2500)).strip()
    except Exception:
        body_text = ""

    try:
        title = (await page.title()).strip()
    except Exception:
        title = ""

    combined = re.sub(r"\s+", " ", f"{title} {body_text}").strip()
    combined_lower = combined.lower()

    strong_expired_signals = (
        "time's up",
        "times up",
        "lab has ended",
        "lab ended",
        "lab is over",
        "lab has expired",
        "lab expired",
        "session expired",
        "session has expired",
        "access time has expired",
        "access time expired",
        "this lab is no longer active",
        "this lab is no longer available",
        "the lab is no longer active",
        "the lab session has ended",
        "your lab has ended",
        "your lab session has ended",
        "lab wurde beendet",
        "lab ist abgelaufen",
        "sitzung abgelaufen",
        "de lab is beëindigd",
        "lab is verlopen",
        "sessie verlopen",
        "de lab-sessie is beëindigd",
        "de lab is afgelopen",
    )

    matched = next(
        (signal for signal in strong_expired_signals if signal in combined_lower),
        None,
    )

    if matched:
        debug_log(
            step,
            f"Lab expiration detected by signal: {matched!r} | URL: {page.url}",
        )
        raise RuntimeError(
            "Lab session is no longer active or has expired. "
            f"Detected: {matched!r} | URL: {page.url}"
        )

    return True


async def monitor_lab_session(monitor_page, stop_event, expired_event, error_holder):
    step = "LAB MONITOR"

    while not stop_event.is_set():
        try:
            await check_lab_session_status(monitor_page, step)
        except RuntimeError as ex:
            error_holder.append(str(ex))
            expired_event.set()
            debug_log(step, f"Lab session ended: {ex}")
            return
        except Exception as ex:
            debug_log(step, f"Temporary monitor error: {type(ex).__name__}: {ex}")

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=5)
        except asyncio.TimeoutError:
            pass


async def ensure_lab_active(expired_event, error_holder):
    if expired_event.is_set():
        message = (
            error_holder[0]
            if error_holder
            else "Lab session is no longer active or has expired."
        )
        raise RuntimeError(message)


# ==========================================================
# Browser launch (Railway-compatible)
# ==========================================================
async def _launch_browser(p):
    _clean_browser_profile()
    os.makedirs(BROWSER_PROFILE_DIR, exist_ok=True)

    return await p.chromium.launch_persistent_context(
        user_data_dir=BROWSER_PROFILE_DIR,
        headless=True,
        args=[
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--window-size=1920,1080",
            "--disable-gpu",
            "--no-zygote",
            "--single-process",
        ],
        viewport={"width": 1920, "height": 1080},
        locale="en-US",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
    )


async def _wait_for_any_visible(locators, timeout_ms):
    """Compatibility fallback for locator.or_() on older Playwright."""
    deadline = asyncio.get_running_loop().time() + timeout_ms / 1000
    while asyncio.get_running_loop().time() < deadline:
        for loc in locators:
            try:
                if await loc.is_visible(timeout=500):
                    return loc
            except Exception:
                pass
        await asyncio.sleep(0.5)
    return None


# ==========================================================
# Automation steps
# ==========================================================
async def step1_welcome_screen(page):
    step = "STEP 1"
    debug_log(step, "Waiting for DOM content...")
    await page.wait_for_load_state("domcontentloaded", timeout=30000)
    await page.wait_for_timeout(1500)
    await log_page_state(page, step)
    try:
        button = page.get_by_text("I understand", exact=True).first
        debug_log(step, "Checking for 'I understand'...")
        if await button.is_visible(timeout=3000):
            debug_log(step, "Button visible; clicking...")
            await button.click()
            await page.wait_for_timeout(1500)
            debug_log(step, "Welcome button clicked successfully.")
        else:
            debug_log(step, "Welcome button not visible; continuing.")
    except PlaywrightTimeoutError:
        debug_log(step, "Welcome button did not appear within 3 seconds; continuing.")
    except Exception as ex:
        await log_exception(page, step, ex)
        raise


async def wait_for_lab_dashboard(page, timeout_ms=600000):
    step = "LAB DASHBOARD"
    deadline = asyncio.get_running_loop().time() + (timeout_ms / 1000)
    last_url = None
    last_state = None

    while asyncio.get_running_loop().time() < deadline:
        current_url = page.url or ""
        current_url_lower = current_url.lower()

        if "/home/dashboard" in current_url_lower:
            if last_state != "dashboard":
                print(f"[AUTH] Lab dashboard reached: {current_url}", flush=True)
            return

        try:
            body_text = (await page.locator("body").inner_text(timeout=3000)).strip()
        except Exception:
            body_text = ""

        body_lower = body_text.lower()
        try:
            title = (await page.title()).strip()
        except Exception:
            title = ""

        await check_lab_session_status(page, step)

        google_page = (
            "accounts.google.com" in current_url_lower
            or "sign in" in body_lower
            or "sign in" in title.lower()
            or "verify it's you" in body_lower
            or "verify its you" in body_lower
            or "verify your identity" in body_lower
            or "confirm it's you" in body_lower
            or "confirm its you" in body_lower
        )

        if google_page:
            state = "google-auth"
            if state != last_state or current_url != last_url:
                print(
                    f"[AUTH] Google auth page detected; waiting. "
                    f"URL: {current_url} | Title: {title}",
                    flush=True,
                )
                last_state = state
                last_url = current_url
            await page.wait_for_timeout(1000)
            continue

        state = "intermediate"
        if state != last_state or current_url != last_url:
            print(
                f"[AUTH] Intermediate page: URL: {current_url} | Title: {title}",
                flush=True,
            )
            last_state = state
            last_url = current_url

        await page.wait_for_timeout(1000)

    current_url = page.url or ""
    try:
        final_title = (await page.title()).strip()
    except Exception:
        final_title = ""

    raise RuntimeError(
        f"Lab dashboard was not reached within {timeout_ms // 1000} seconds. "
        f"Current URL: {current_url} | Title: {final_title}"
    )


async def step2_tos_and_country(page):
    step = "STEP 2"
    debug_log(step, "Starting Terms/country check.")
    await check_lab_session_status(page, step)
    await log_page_state(page, step, True)
    agree_btn = page.get_by_role("button", name="Agree and continue")
    try:
        debug_log(step, "Waiting up to 10 seconds for 'Agree and continue'...")
        await agree_btn.wait_for(state="visible", timeout=10000)
        debug_log(step, "'Agree and continue' is visible.")
        checkboxes = page.get_by_role("checkbox")
        count = await checkboxes.count()
        debug_log(step, f"Checkbox count: {count}")
        if count < 2:
            raise RuntimeError(
                f"Expected at least 2 checkboxes, but found {count}."
            )
        debug_log(step, "Clicking checkbox #1...")
        await checkboxes.nth(0).click()
        await asyncio.sleep(1)
        debug_log(step, "Clicking checkbox #2...")
        await checkboxes.nth(1).click()
        debug_log(step, "Clicking 'Agree and continue'...")
        await agree_btn.click()
        await page.wait_for_load_state("domcontentloaded")
        debug_log(step, "Terms/country step completed successfully.")
    except PlaywrightTimeoutError as ex:
        debug_log(
            step,
            "Optional Terms/country screen did not appear within 10 seconds; continuing.",
        )
        debug_log(step, f"Timeout details: {type(ex).__name__}: {ex}")
        await log_page_state(page, step, True)
    except Exception as ex:
        await log_exception(page, step, ex, True)
        raise


async def step3_enable_api(page, project_id, authuser):
    step = "STEP 3"
    api_url = (
        f"https://console.cloud.google.com/apis/library/run.googleapis.com"
        f"?project={project_id}&authuser={authuser}"
    )
    debug_log(step, f"Opening API page for project: {project_id}")
    debug_log(step, f"authuser: {authuser}")

    try:
        await page.goto(api_url, wait_until="domcontentloaded", timeout=60000)
    except PlaywrightTimeoutError:
        debug_log(step, "Initial navigation timed out; inspecting the current page.")

    auth_timeout_ms = 900000
    auth_deadline = asyncio.get_running_loop().time() + (auth_timeout_ms / 1000)
    last_url = None
    last_state = None

    while asyncio.get_running_loop().time() < auth_deadline:
        current_url = (page.url or "").lower()

        try:
            title = (await page.title()).strip()
        except Exception:
            title = ""

        try:
            body = (await page.locator("body").inner_text(timeout=3000)).strip()
        except Exception:
            body = ""

        body_lower = body.lower()
        title_lower = title.lower()

        on_google_auth = (
            "accounts.google.com" in current_url
            or "sign in" in body_lower
            or "sign in" in title_lower
            or "verify it's you" in body_lower
            or "verify your identity" in body_lower
            or "confirm it's you" in body_lower
        )

        on_cloud_console = (
            "console.cloud.google.com" in current_url
            and "accounts.google.com" not in current_url
        )

        if on_google_auth:
            state = "google-auth"
            if state != last_state or current_url != last_url:
                debug_log(
                    step,
                    "Google sign-in page detected. Waiting for the flow. "
                    f"URL: {page.url}",
                )
                last_state = state
                last_url = current_url
            await page.wait_for_timeout(1500)
            continue

        if on_cloud_console:
            debug_log(step, f"Cloud Console reached: {page.url}")
            break

        state = "redirecting"
        if state != last_state or current_url != last_url:
            debug_log(
                step,
                f"Waiting for redirect. URL: {page.url} | Title: {title}",
            )
            last_state = state
            last_url = current_url

        await page.wait_for_timeout(1500)
    else:
        raise RuntimeError(
            "Google authentication did not finish within 15 minutes. "
            f"Current URL: {page.url}"
        )

    enable_btn = page.get_by_role("button", name="Enable")
    manage_btn = page.get_by_role("button", name="Manage")
    disable_btn = page.get_by_text("Disable API")

    controls_timeout_ms = 120000
    controls_deadline = (
        asyncio.get_running_loop().time() + (controls_timeout_ms / 1000)
    )

    while asyncio.get_running_loop().time() < controls_deadline:
        try:
            ev = await enable_btn.is_visible(timeout=1500)
        except Exception:
            ev = False
        try:
            mv = await manage_btn.is_visible(timeout=1500)
        except Exception:
            mv = False
        try:
            dv = await disable_btn.is_visible(timeout=1500)
        except Exception:
            dv = False

        debug_log(
            step,
            f"Enable visible: {ev} | Manage visible: {mv} | Disable visible: {dv}",
        )

        if ev:
            debug_log(step, "Clicking Enable...")
            await enable_btn.click()
            debug_log(step, "Enable clicked; waiting for Manage/Disable...")

            found = await _wait_for_any_visible([manage_btn, disable_btn], 120000)
            if not found:
                raise RuntimeError(
                    "Enable clicked but Manage/Disable never appeared within 120s."
                )
            debug_log(step, "API appears enabled successfully.")
            return

        if mv or dv:
            debug_log(step, "API is already enabled.")
            return

        await page.wait_for_timeout(2000)

    await log_page_state(page, step, True)
    raise RuntimeError(
        "Cloud Run API controls did not appear within 120 seconds. "
        f"Current URL: {page.url}"
    )


async def step4_create_cloud_run(page, project_id, authuser):
    step = "STEP 4"
    run_url = (
        f"https://console.cloud.google.com/run/create"
        f"?project={project_id}&authuser={authuser}"
    )
    debug_log(step, f"Opening Cloud Run create page for project: {project_id}")
    await page.goto(run_url, wait_until="domcontentloaded")
    await page.wait_for_timeout(5000)
    await log_page_state(page, step, True)

    try:
        debug_log(step, "Looking for Container Image URL...")
        label = page.get_by_text("Container Image URL").first
        await label.click()
        debug_log(step, "Field selected; typing image...")
        await page.wait_for_timeout(500)
        await page.keyboard.type("soshope35/xray-vless:latest", delay=50)
        debug_log(step, "Container image entered.")
    except Exception as ex:
        await log_exception(page, step, ex, True)
        raise RuntimeError(
            f"Container image input failed: {type(ex).__name__}: {ex}"
        ) from ex

    await page.wait_for_timeout(3000)

    try:
        debug_log(step, "Selecting Allow public access...")
        await page.get_by_role("radio", name="Allow public access").click()

        debug_log(step, "Selecting Instance-based...")
        await page.get_by_role("radio", name="Instance-based").click()

        try:
            debug_log(step, "Checking optional Hide button...")
            await page.get_by_role("button", name="Hide").click(timeout=2000)
            debug_log(step, "Hide clicked.")
        except PlaywrightTimeoutError:
            debug_log(step, "Optional Hide button not found; continuing.")
        except Exception as ex:
            debug_log(step, f"Optional Hide failed: {type(ex).__name__}: {ex}; continuing.")

        await page.keyboard.press("End")
        await page.wait_for_timeout(1000)
        debug_log(step, "Clicking Create...")
        await page.get_by_role("button", name="Create").click(force=True)
        debug_log(step, "Create clicked successfully.")
    except Exception as ex:
        await log_exception(page, step, ex, True)
        raise RuntimeError(
            f"Cloud Run settings/Create failed: {type(ex).__name__}: {ex}"
        ) from ex


async def step5_get_deployed_url(page, expired_event=None, error_holder=None):
    step = "STEP 5"
    debug_log(step, "Waiting up to 120 seconds for deployed run.app URL...")
    link_locator = page.locator('a[href*="run.app"]')
    deadline = asyncio.get_running_loop().time() + 120

    try:
        while asyncio.get_running_loop().time() < deadline:
            if expired_event is not None:
                await ensure_lab_active(expired_event, error_holder or [])

            try:
                if await link_locator.is_visible(timeout=1500):
                    final_url = await link_locator.get_attribute("href")
                    debug_log(step, f"Detected deployed URL: {final_url}")
                    if not final_url:
                        raise RuntimeError(
                            "run.app link is visible but its href is empty."
                        )
                    return final_url
            except PlaywrightTimeoutError:
                pass

            await page.wait_for_timeout(2000)

        raise PlaywrightTimeoutError(
            "run.app URL was not detected within 120 seconds."
        )
    except Exception as ex:
        await log_exception(page, step, ex, True)
        raise


# ==========================================================
# Main pipeline
# ==========================================================
async def _shutdown_monitor(task, stop_event):
    if task is None:
        return
    stop_event.set()
    try:
        await asyncio.wait_for(task, timeout=8)
    except asyncio.TimeoutError:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
    except asyncio.CancelledError:
        pass
    except Exception as ex:
        debug_log(
            "LAB MONITOR",
            f"Shutdown error: {type(ex).__name__}: {ex}",
        )


async def process_sso_link(chat_id, sso_url):
    project_id = extract_project_id(sso_url)
    if not project_id:
        await client.send_message(chat_id, "Invalid project ID in the link.")
        return

    await client.send_message(chat_id, "Starting the request...")

    assert BROWSER_LOCK is not None, "BROWSER_LOCK not initialized"

    async with BROWSER_LOCK:
        async with async_playwright() as p:
            context = None
            page = None
            lab_monitor_page = None
            lab_monitor_task = None
            lab_monitor_stop = asyncio.Event()
            lab_expired_event = asyncio.Event()
            lab_monitor_errors = []

            try:
                context = await _launch_browser(p)
                page = (
                    context.pages[0]
                    if context.pages
                    else await context.new_page()
                )
                await page.goto(
                    sso_url, wait_until="domcontentloaded", timeout=60000
                )

                await client.send_message(chat_id, "Step 1: Starting...")
                await step1_welcome_screen(page)

                await client.send_message(
                    chat_id,
                    "Waiting for the lab to reach the dashboard...",
                )
                await wait_for_lab_dashboard(page, timeout_ms=600000)

                await ensure_lab_active(lab_expired_event, lab_monitor_errors)

                lab_monitor_page = await context.new_page()
                try:
                    await lab_monitor_page.goto(
                        sso_url,
                        wait_until="domcontentloaded",
                        timeout=60000,
                    )
                except PlaywrightTimeoutError:
                    debug_log(
                        "LAB MONITOR",
                        "Initial monitor navigation timed out; retrying on the next cycle.",
                    )

                lab_monitor_task = asyncio.create_task(
                    monitor_lab_session(
                        lab_monitor_page,
                        lab_monitor_stop,
                        lab_expired_event,
                        lab_monitor_errors,
                    )
                )

                current_qs = parse_qs(urlparse(page.url).query)
                authuser = current_qs.get("authuser", ["1"])[0]

                await client.send_message(chat_id, "Step 2: Starting...")
                await ensure_lab_active(lab_expired_event, lab_monitor_errors)
                await step2_tos_and_country(page)
                await ensure_lab_active(lab_expired_event, lab_monitor_errors)

                await client.send_message(
                    chat_id,
                    "Step 3: Waiting for API page...",
                )
                await step3_enable_api(page, project_id, authuser)
                await ensure_lab_active(lab_expired_event, lab_monitor_errors)

                await client.send_message(
                    chat_id,
                    "Step 4: Creating Cloud Run service...",
                )
                await step4_create_cloud_run(page, project_id, authuser)
                await ensure_lab_active(lab_expired_event, lab_monitor_errors)

                await client.send_message(
                    chat_id,
                    "Step 5: Waiting for deployment...",
                )
                final_url = await step5_get_deployed_url(
                    page,
                    lab_expired_event,
                    lab_monitor_errors,
                )
                if not final_url:
                    raise RuntimeError(
                        "Cloud Run deployment finished without a run.app URL."
                    )

                domain = extract_domain_from_service_url(final_url)
                if not domain:
                    raise RuntimeError(
                        f"Could not extract a domain from: {final_url}"
                    )

                await client.send_message(
                    chat_id,
                    f"Deployment completed.\n\nDomain:\n{domain}",
                )

                vless_result = VLESS_TEMPLATE.format(domain=domain)
                await client.send_message(
                    chat_id,
                    f"<pre><code class=\"language-java\">{vless_result}</code></pre>",
                    parse_mode="html",
                )

                safe_domain = html.escape(domain, quote=True)
                json_result = JSON_TEMPLATE.replace("__DOMAIN__", safe_domain)
                await client.send_message(
                    chat_id,
                    f"<pre><code class=\"language-json\">{json_result}</code></pre>",
                    parse_mode="html",
                )

                await generate_and_send_dark_file(chat_id, domain)

            except PlaywrightTimeoutError as e:
                print("!!! PLAYWRIGHT TIMEOUT !!!", flush=True)
                import traceback

                traceback.print_exc()
                await handle_error(page, chat_id, "Timeout", str(e))
            except Exception as e:
                print("!!! UNHANDLED PROCESS ERROR !!!", flush=True)
                import traceback

                traceback.print_exc()
                if "Lab session is no longer active or has expired" in str(e):
                    await handle_error(
                        page,
                        chat_id,
                        "Lab session expired",
                        "The lab session is no longer active. "
                        "Start a new lab and send the new link.",
                    )
                else:
                    await handle_error(page, chat_id, "General error", str(e))
            finally:
                await _shutdown_monitor(lab_monitor_task, lab_monitor_stop)

                if lab_monitor_page is not None:
                    try:
                        await lab_monitor_page.close()
                    except Exception as monitor_page_error:
                        debug_log(
                            "LAB MONITOR",
                            f"Monitor page close error: {type(monitor_page_error).__name__}: {monitor_page_error}",
                        )

                if context is not None:
                    try:
                        await context.close()
                    except Exception as close_error:
                        print(f"Browser close error: {close_error}", flush=True)


# ==========================================================
# Telegram handlers & entry point
# ==========================================================
@client.on(events.NewMessage(pattern=r"^/start$"))
async def start(event):
    welcome_msg = (
        "مرحبا بك في بوت إنشاء Cloud Run \n\n"
        "🕓 **وقت المختبر:** 4 ساعات و 30 دقيقة (4:30 hours)\n"
        "🔗 **المختبر الأول:**\n"
        "https://www.cloudskillsboost.google/focuses/20774?parent=catalog\n\n"
        "🕓 **وقت المختبر:** 3 ساعات (3:00 hours)\n"
        "🔗 **المختبر الثاني:**\n"
        "https://www.skills.google/focuses/82384?parent=catalog\n\n"
        "@Mustapha_Bacha35"
    )
    await event.reply(welcome_msg)


@client.on(events.NewMessage(pattern=r"https://www\.skills\.google/google_sso\S+"))
async def handler(event):
    if not event.text:
        return
    m = re.search(r"https://www\.skills\.google/google_sso\S+", event.text)
    if not m:
        return
    sso_url = m.group(0)

    if BROWSER_LOCK is None or BROWSER_LOCK.locked():
        await event.reply("⏳ هناك طلب قيد المعالجة حالياً، يرجى الانتظار.")
        return

    asyncio.create_task(process_sso_link(event.chat_id, sso_url))


async def main():
    global BROWSER_LOCK
    BROWSER_LOCK = asyncio.Lock()

    print("STEP 2: Creating TelegramClient", flush=True)

    try:
        print("STEP 3: Connecting to Telegram", flush=True)
        await client.start(bot_token=BOT_TOKEN)
        print("STEP 4: Telegram connected", flush=True)
    except Exception:
        print("!!! TELEGRAM CONNECTION ERROR !!!", flush=True)
        traceback.print_exc()
        raise

    print("Connected.", flush=True)
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.run(main())