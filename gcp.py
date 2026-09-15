import asyncio
import os
import re
from urllib.parse import urlparse, parse_qs
from telethon import TelegramClient, events
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from playwright.async_api import expect
import io
import base64
import json
from telethon.tl.types import DocumentAttributeFilename


# Keep one browser profile for the lifetime of the Railway container so that
# an authorized Google session can be reused between requests.
BROWSER_PROFILE_DIR = os.path.join(os.getcwd(), "browser_profile")
BROWSER_LOCK = asyncio.Lock()



#===============================
API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]

print("STEP 1: Python started", flush=True)

try:
    print("STEP 2: Creating TelegramClient", flush=True)

    client = TelegramClient("railway_bot", API_ID, API_HASH)

    print("STEP 3: Connecting to Telegram", flush=True)

    client.start(bot_token=BOT_TOKEN)

    print("STEP 4: Telegram connected", flush=True)

except Exception:
    print("!!! TELEGRAM CONNECTION ERROR !!!", flush=True)
    import traceback
    traceback.print_exc()
    raise

# ==========================================
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




DARKTUNNEL_BASE_URI = "darktunnel://eyJ0eXBlIjoiVkxFU1MiLCJuYW1lIjoi2KjYr9mI2YYg2LnYsdmI2LYg2KPZiNix2YrYr9mIINis2YrYstmKIiwidmxlc3NUdW5uZWxDb25maWciOnsidjJyYXlDb25maWciOnsiaG9zdCI6Inl0My5nZ3BodC5jb20iLCJwb3J0Ijo0NDMsInV1aWQiOiIyOWViMmEzZS00ODQ3LTQzYzYtYmEyZi1iMWIzMjNiZDM5ZDYiLCJzZXJ2ZXJOYW1lSW5kaWNhdGlvbiI6Inl0My5nZ3BodC5jb20iLCJ3c1BhdGgiOiIvTXVzdGFwaGFfQmFjaGEzNSIsIndzSGVhZGVySG9zdCI6Im11c3RhcGhhMzUtNTk4NDcyOTI5Mzg1LnVzLWNlbnRyYWwxLnJ1bi5hcHAifSwiaW5qZWN0Q29uZmlnIjp7ImVuYWJsZWQiOnRydWUsIm1vZGUiOiJQUk9YWSIsInByb3h5SG9zdCI6IjU3LjE0NC4xMjAuNCIsInBheWxvYWQiOiJDT05ORUNUIFtob3N0X3BvcnRdIEhUVFAvMS4xW2NybGZdVXNlci1BZ2VudDogRkJBVi81NzEuMC4wLjQ0LjczW2NybGZdWC1JT1JHLUJTSUQ6IEludGVybmV0Lm9yZ1tjcmxmXVtjcmxmXSJ9fX0="


# ==========================================
# ==========================================

async def handle_error(page, chat_id, step_name, error_msg):
    """Send a useful error report without masking the original exception."""
    print(f"Error at {step_name}: {error_msg}", flush=True)

    safe_error_msg = str(error_msg)
    if len(safe_error_msg) > 1200:
        safe_error_msg = safe_error_msg[:1200] + "\n..."

    screenshot_path = None

    try:
        if page is not None:
            safe_step = re.sub(r"[^a-zA-Z0-9_-]+", "_", step_name).strip("_") or "error"
            screenshot_path = os.path.abspath(f"error_{safe_step}.png")
            await page.screenshot(path=screenshot_path, full_page=True)

            await client.send_file(
                chat_id,
                file=screenshot_path,
                caption=(
                    f"❌ حدث خطأ في مرحلة:\n**{step_name}**\n\n"
                    f"تفاصيل الخطأ:\n`{safe_error_msg}`"
                )
            )
        else:
            await client.send_message(
                chat_id,
                f"❌ حدث خطأ في مرحلة: **{step_name}**\n\n"
                f"تفاصيل الخطأ:\n`{safe_error_msg}`"
            )
    except Exception as report_error:
        print(f"Failed to send error report: {report_error}", flush=True)
        try:
            await client.send_message(
                chat_id,
                f"❌ حدث خطأ في مرحلة: **{step_name}**\n\n"
                f"تفاصيل الخطأ:\n`{safe_error_msg}`"
            )
        except Exception:
            pass
    finally:
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                os.remove(screenshot_path)
            except OSError:
                pass


# ==========================================
def debug_log(step: str, message: str):
    print(f"[{step}] {message}", flush=True)

async def log_page_state(page, step: str, include_body=False, body_limit=3000):
    try: debug_log(step, f"URL: {page.url}")
    except Exception as e: debug_log(step, f"Could not read URL: {type(e).__name__}: {e}")
    try: debug_log(step, f"Title: {await page.title()}")
    except Exception as e: debug_log(step, f"Could not read title: {type(e).__name__}: {e}")
    if include_body:
        try:
            body=re.sub(r"\s+"," ",(await page.locator("body").inner_text(timeout=5000)).strip())
            debug_log(step, f"Body sample: {body[:body_limit]}")
        except Exception as e: debug_log(step, f"Could not read body: {type(e).__name__}: {e}")

async def save_debug_screenshot(page, step: str):
    try:
        safe=re.sub(r"[^a-zA-Z0-9_-]+","_",step).strip("_") or "debug"
        path=os.path.abspath(f"debug_{safe}.png")
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


def extract_domain_from_service_url(service_url: str) -> str:
    s = (service_url or "").strip()
    if s.startswith("http://") or s.startswith("https://"):
        return urlparse(s).netloc.strip()
    return s.replace("http://", "").replace("https://", "").split("/")[0].strip()

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
    tg_fname = f"ملف يوتوب وملف بدون عروض - {safe_domain}.dark"
    
    bio = io.BytesIO(new_uri.encode("utf-8"))
    bio.name = tg_fname 
    await client.send_file(
        chat_id,
        bio,
        force_document=True,
        attributes=[DocumentAttributeFilename(tg_fname)],
        caption=f"✅ ملفات DarkTunnel جاهزة:\n`{domain}`"
    )


# ==========================================
# ==========================================





def extract_project_id(url):
    match = re.search(r'(qwiklabs-gcp-[\w-]+)', url)
    if match:
        return match.group(1)
    return None

# ==========================================
# ==========================================
# ==========================================

async def step1_welcome_screen(page):
    step="STEP 1"
    debug_log(step,"Waiting for DOM content...")
    await page.wait_for_load_state("domcontentloaded",timeout=30000)
    await page.wait_for_timeout(1500)
    await log_page_state(page,step)
    try:
        button=page.get_by_text("I understand",exact=True).first
        debug_log(step,"Checking for 'I understand'...")
        if await button.is_visible(timeout=3000):
            debug_log(step,"Button visible; clicking...")
            await button.click(); await page.wait_for_timeout(1500)
            debug_log(step,"Welcome button clicked successfully.")
        else: debug_log(step,"Welcome button not visible; continuing.")
    except PlaywrightTimeoutError:
        debug_log(step,"Welcome button did not appear within 3 seconds; continuing.")
    except Exception as ex:
        await log_exception(page,step,ex); raise

async def wait_for_lab_dashboard(page, timeout_ms=120000):
    """Wait for the Skills Boost Lab dashboard while tracking Google redirects."""
    deadline = asyncio.get_running_loop().time() + (timeout_ms / 1000)
    last_url = None
    last_state = None

    while asyncio.get_running_loop().time() < deadline:
        current_url = page.url or ""
        current_url_lower = current_url.lower()

        # The actual successful destination.
        if "/home/dashboard" in current_url_lower:
            if last_state != "dashboard":
                print(f"[AUTH] Lab dashboard reached: {current_url}", flush=True)
            return

        # Read the current page so we can distinguish a Google redirect
        # from the Lab pages without treating every intermediate page as an error.
        try:
            body_text = (await page.locator("body").inner_text(timeout=3000)).strip()
        except Exception:
            body_text = ""

        body_lower = body_text.lower()
        title = ""
        try:
            title = (await page.title()).strip()
        except Exception:
            pass

        # Google authentication / verification pages are intermediate states.
        # Do NOT raise immediately: Google may still redirect to the Lab dashboard
        # when an already-authorized persistent browser session completes the flow.
        google_page = (
            "accounts.google.com" in current_url_lower
            or "sign in" in body_lower
            or "sign in" in title.lower()
            or "verify it's you" in body_lower
            or "verify its you" in body_lower
            or "verify your identity" in body_lower
            or "confirm it's you" in body_lower
            or "confirm its you" in body_lower
            or "verifizieren, dass du es bist" in body_lower
            or "تحقق من هويتك" in body_lower
        )

        if google_page:
            state = "google-auth"
            if state != last_state or current_url != last_url:
                print(
                    f"[AUTH] Google authentication page detected; waiting for "
                    f"the browser session to complete the redirect. "
                    f"URL: {current_url} | Title: {title}",
                    flush=True,
                )
                last_state = state
                last_url = current_url

            await page.wait_for_timeout(1000)
            continue

        # We are no longer on Google, but the final dashboard has not appeared yet.
        # Log the new page and keep waiting because SSO can pass through intermediate
        # Lab/Skills Boost pages before /home/dashboard.
        state = "intermediate"
        if state != last_state or current_url != last_url:
            print(
                f"[AUTH] Intermediate page while waiting for Lab dashboard: "
                f"URL: {current_url} | Title: {title}",
                flush=True,
            )
            last_state = state
            last_url = current_url

        await page.wait_for_timeout(1000)

    # Timeout: report the real final state instead of hiding it behind a generic error.
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
    step="STEP 2"
    debug_log(step,"Starting Terms/country check.")
    await log_page_state(page,step,True)
    agree_btn=page.get_by_role("button",name="Agree and continue")
    try:
        debug_log(step,"Waiting up to 10 seconds for 'Agree and continue'...")
        await agree_btn.wait_for(state="visible",timeout=10000)
        debug_log(step,"'Agree and continue' is visible.")
        checkboxes=page.get_by_role("checkbox")
        count=await checkboxes.count(); debug_log(step,f"Checkbox count: {count}")
        if count<2: raise RuntimeError(f"Expected at least 2 checkboxes, but found {count}.")
        debug_log(step,"Clicking checkbox #1..."); await checkboxes.nth(0).click(); await asyncio.sleep(1)
        debug_log(step,"Clicking checkbox #2..."); await checkboxes.nth(1).click()
        debug_log(step,"Clicking 'Agree and continue'..."); await agree_btn.click(); await page.wait_for_load_state("domcontentloaded")
        debug_log(step,"Terms/country step completed successfully.")
    except PlaywrightTimeoutError as ex:
        debug_log(step,"Optional Terms/country screen did not appear within 10 seconds; continuing.")
        debug_log(step,f"Timeout details: {type(ex).__name__}: {ex}"); await log_page_state(page,step,True)
    except Exception as ex:
        await log_exception(page,step,ex,True); raise

async def step3_enable_api(page, project_id, authuser):
    step="STEP 3"
    api_url=f"https://console.cloud.google.com/apis/library/run.googleapis.com?project={project_id}&authuser={authuser}"
    debug_log(step,f"Opening API page for project: {project_id}"); debug_log(step,f"authuser: {authuser}")
    await page.goto(api_url,wait_until="domcontentloaded"); await page.wait_for_timeout(3000); await log_page_state(page,step,True)
    enable_btn=page.get_by_role("button",name="Enable"); manage_btn=page.get_by_role("button",name="Manage"); disable_btn=page.get_by_text("Disable API")
    try:
        debug_log(step,"Checking Enable / Manage...")
        ev=await enable_btn.is_visible(timeout=5000); mv=await manage_btn.is_visible(timeout=5000)
        debug_log(step,f"Enable visible: {ev}"); debug_log(step,f"Manage visible: {mv}")
        if ev:
            debug_log(step,"Clicking Enable..."); await enable_btn.click(); debug_log(step,"Enable clicked; waiting for Manage/Disable..."); await expect(manage_btn.or_(disable_btn)).to_be_visible(timeout=60000); debug_log(step,"API appears enabled successfully.")
        elif mv: debug_log(step,"API is already enabled.")
        else: raise RuntimeError("Neither 'Enable' nor 'Manage' is visible on the Cloud Run API page.")
    except Exception as ex:
        await log_exception(page,step,ex,True); raise

async def step4_create_cloud_run(page, project_id, authuser):
    step="STEP 4"
    run_url=f"https://console.cloud.google.com/run/create?project={project_id}&authuser={authuser}"
    debug_log(step,f"Opening Cloud Run create page for project: {project_id}"); await page.goto(run_url,wait_until="domcontentloaded"); await page.wait_for_timeout(5000); await log_page_state(page,step,True)
    try:
        debug_log(step,"Looking for Container Image URL..."); label=page.get_by_text("Container Image URL").first; await label.click(); debug_log(step,"Field selected; typing image..."); await page.wait_for_timeout(500); await page.keyboard.type("soshope35/xray-vless:latest",delay=50); debug_log(step,"Container image entered.")
    except Exception as ex:
        await log_exception(page,step,ex,True); raise RuntimeError(f"Container image input failed: {type(ex).__name__}: {ex}") from ex
    await page.wait_for_timeout(3000)
    try:
        debug_log(step,"Selecting Allow public access..."); await page.get_by_role("radio",name="Allow public access").click(); debug_log(step,"Selecting Instance-based..."); await page.get_by_role("radio",name="Instance-based").click()
        try:
            debug_log(step,"Checking optional Hide button..."); await page.get_by_role("button",name="Hide").click(timeout=2000); debug_log(step,"Hide clicked.")
        except PlaywrightTimeoutError: debug_log(step,"Optional Hide button not found; continuing.")
        except Exception as ex: debug_log(step,f"Optional Hide failed: {type(ex).__name__}: {ex}; continuing.")
        await page.keyboard.press("End"); await page.wait_for_timeout(1000); debug_log(step,"Clicking Create..."); await page.get_by_role("button",name="Create").click(force=True); debug_log(step,"Create clicked successfully.")
    except Exception as ex:
        await log_exception(page,step,ex,True); raise RuntimeError(f"Cloud Run settings/Create failed: {type(ex).__name__}: {ex}") from ex

async def step5_get_deployed_url(page):
    step="STEP 5"; debug_log(step,"Waiting up to 120 seconds for deployed run.app URL..."); link_locator=page.locator('a[href*="run.app"]')
    try:
        await link_locator.wait_for(state="visible",timeout=120000); final_url=await link_locator.get_attribute("href"); debug_log(step,f"Detected deployed URL: {final_url}")
        if not final_url: raise RuntimeError("run.app link is visible but its href is empty.")
        return final_url
    except Exception as ex: await log_exception(page,step,ex,True); raise

async def process_sso_link(chat_id, sso_url):
    project_id = extract_project_id(sso_url)
    if not project_id:
        await client.send_message(chat_id, "❌ Project ID في الرابط.")
        return

    await client.send_message(chat_id, "⏳𝙡𝙚𝙩 𝙢𝙚 𝙨𝙚𝙚 𝙬𝙝𝙖𝙩 𝙄 𝙘𝙖𝙣 𝙙𝙤...")

    # Reuse one browser profile so an authorized Google session can be reused
    # between requests. The lock prevents two Playwright instances from using
    # the same Chromium profile at the same time.
    os.makedirs(BROWSER_PROFILE_DIR, exist_ok=True)

    async with BROWSER_LOCK:
        async with async_playwright() as p:
            context = None
            page = None

            try:
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=BROWSER_PROFILE_DIR,
                    channel='chrome',
                    headless=False,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--disable-blink-features=AutomationControlled',
                        '--disable-infobars',
                        '--window-size=1920,1080'
                    ],
                    viewport={'width': 1920, 'height': 1080},
                    locale='en-US'
                )

                page = context.pages[0] if context.pages else await context.new_page()
                await page.goto(sso_url, wait_until="domcontentloaded", timeout=60000)

                await client.send_message(chat_id, "🔄 𝙎𝙩𝙚𝙥 𝙤𝙣𝙚...")
                await step1_welcome_screen(page)

                await client.send_message(
                    chat_id,
                    "⏳ جاري انتظار انتقال المختبر إلى Dashboard..."
                )
                await wait_for_lab_dashboard(page, timeout_ms=120000)

                current_qs = parse_qs(urlparse(page.url).query)
                authuser = current_qs.get('authuser', ['1'])[0]

                await client.send_message(chat_id, "🔄𝙉𝙤𝙬 𝙨𝙩𝙚𝙥 𝙩𝙬𝙤...")
                await step2_tos_and_country(page)

                await client.send_message(
                    chat_id,
                    "🔄 𝙎𝙩𝙚𝙥 𝙩𝙝𝙧𝙚𝙚 𝙖𝙨 𝙛𝙖𝙨𝙩 𝙖𝙨 𝙄 𝙘𝙖𝙣 𝙗𝙧𝙤 ..."
                )
                await step3_enable_api(page, project_id, authuser)

                await client.send_message(
                    chat_id,
                    "🔄 𝙣𝙤𝙬 𝙩𝙝𝙚 𝙧𝙚𝙖𝙡 𝙟𝙤𝙗: 𝙎𝙩𝙚𝙥 𝙛𝙤𝙪𝙧..."
                )
                await step4_create_cloud_run(page, project_id, authuser)

                await client.send_message(
                    chat_id,
                    "⏳𝙬𝙖𝙞𝙩, 𝙟𝙪𝙨𝙩 𝙤𝙣𝙚 𝙘𝙞𝙜𝙖𝙧𝙚𝙩𝙩𝙚..."
                )
                final_url = await step5_get_deployed_url(page)
                if not final_url:
                    raise RuntimeError("Cloud Run deployment finished without a run.app URL.")

                domain = extract_domain_from_service_url(final_url)
                if not domain:
                    raise RuntimeError(f"Could not extract a domain from: {final_url}")

                await client.send_message(
                    chat_id,
                    f"✅ **𝙃𝙚𝙧𝙚 𝙮𝙤𝙪 𝙜𝙤 𝙗𝙧𝙤**\n\n 𝙙𝙤𝙢𝙖𝙞𝙣 :\n {domain}"
                )

                vless_result = VLESS_TEMPLATE.format(domain=domain)
                await client.send_message(
                    chat_id,
                    f"🔗 <pre><code class=\"language-java\">{vless_result}</code></pre>",
                    parse_mode='html'
                )

                json_result = JSON_TEMPLATE.replace("__DOMAIN__", domain)
                await client.send_message(
                    chat_id,
                    f"📄<pre><code class=\"language-json\">{json_result}</code></pre>",
                    parse_mode='html'
                )

                await generate_and_send_dark_file(chat_id, domain)

            except PlaywrightTimeoutError as e:
                print("!!! PLAYWRIGHT TIMEOUT !!!", flush=True)
                import traceback
                traceback.print_exc()
                await handle_error(page, chat_id, "انتهى وقت الانتظار (Timeout)", str(e))
            except Exception as e:
                print("!!! UNHANDLED PROCESS ERROR !!!", flush=True)
                import traceback
                traceback.print_exc()
                await handle_error(page, chat_id, "خطأ عام", str(e))
            finally:
                if context is not None:
                    try:
                        await context.close()
                    except Exception as close_error:
                        print(f"Browser close error: {close_error}", flush=True)


# ==========================================
# ==========================================

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



# ==========================================

@client.on(events.NewMessage(pattern=r'https://www\.skills\.google/google_sso.*'))
async def handler(event):
    sso_url = event.text
    asyncio.create_task(process_sso_link(event.chat_id, sso_url))

print("𝙘𝙤𝙣𝙣𝙚𝙘𝙩𝙚𝙙...")
client.run_until_disconnected()