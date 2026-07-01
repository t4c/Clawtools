#!/usr/bin/env python3
import os
import sys
import re
import time
import random
import argparse
import logging
from playwright.sync_api import sync_playwright

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("sniper.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("amazon_sniper")

def load_dotenv():
    """Loads environment variables from local .env file if it exists."""
    env_path = ".env"
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, val = line.split("=", 1)
                        if key.strip() not in os.environ:
                            os.environ[key.strip()] = val.strip()
        except Exception as e:
            logger.error(f"Error loading .env: {e}")

load_dotenv()

def load_telegram_config():
    """Loads Telegram credentials from environment."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_HOME_CHANNEL")
    return token, chat_id

TELEGRAM_TOKEN, TELEGRAM_CHAT_ID = load_telegram_config()

def send_telegram(text, image_path=None):
    """Sends a message to Telegram (images disabled by user request)."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram configuration missing. Skipping alert.")
        return False
    
    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}
        resp = requests.post(url, json=data, timeout=15)
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False

def check_login_status(page):
    """Checks if the user is currently logged in."""
    try:
        page.goto("https://www.amazon.de", timeout=30000)
        # Check for sign-in link text or account menu
        account_elem = page.query_selector("#nav-link-accountList-nav-line-1")
        if account_elem:
            text = account_elem.inner_text().lower()
            if "anmelden" not in text and "sign in" not in text:
                logger.info(f"Logged in as: {account_elem.inner_text().strip()}")
                return True
        return False
    except Exception as e:
        logger.error(f"Error checking login status: {e}")
        return False

def handle_login(page, email, password):
    """Performs the login flow interactively, handling 2FA / Captchas."""
    logger.info("Navigating to Amazon Sign-In...")
    page.goto("https://www.amazon.de/gp/sign-in.html", timeout=30000)
    time.sleep(2)
    
    # Handle cookie consent banner if present
    cookie_btn = page.query_selector("#sp-cc-accept")
    if cookie_btn:
        logger.info("Accepting cookies...")
        cookie_btn.click()
        time.sleep(1)
        
    # Enter Email
    email_input = page.query_selector("input#ap_email")
    if email_input:
        logger.info("Entering email...")
        email_input.fill(email)
        page.click("input#continue")
        time.sleep(2)
    else:
        logger.info("No email input found, might be on a different page or already logged in.")
        
    # Enter Password
    pwd_input = page.query_selector("input#ap_password")
    if pwd_input:
        logger.info("Entering password...")
        pwd_input.fill(password)
        # Keep me signed in
        keep_signed_in = page.query_selector("input[name='rememberMe']")
        if keep_signed_in:
            keep_signed_in.check()
        page.click("input#signInSubmit")
        time.sleep(3)
        
    # Detect Captcha
    if page.query_selector("img#auth-captcha-image") or page.query_selector("img#ap_captcha_img"):
        logger.warning("⚠️ CAPTCHA detected!")
        screenshot_path = "captcha_challenge.png"
        page.screenshot(path=screenshot_path)
        send_telegram("⚠️ <b>Amazon Sniper CAPTCHA benötigt!</b> Bitte gib das Captcha im Terminal ein.", screenshot_path)
        
        captcha_code = input("Bitte Captcha-Code eingeben: ").strip()
        captcha_input = page.query_selector("input#auth-captcha-guess") or page.query_selector("input#ap_captcha_guess")
        if captcha_input:
            captcha_input.fill(captcha_code)
            # Re-fill password if required
            pwd_input = page.query_selector("input#ap_password")
            if pwd_input:
                pwd_input.fill(password)
            page.click("input#signInSubmit")
            time.sleep(3)
            
    # Detect 2FA / OTP
    if page.query_selector("input#auth-mfa-otpcode") or page.query_selector("input#ap_otp_code") or "approval" in page.url.lower():
        logger.warning("⚠️ Two-Factor Authentication (2FA) / OTP requested!")
        screenshot_path = "otp_challenge.png"
        page.screenshot(path=screenshot_path)
        send_telegram("⚠️ <b>Amazon Sniper 2FA / OTP benötigt!</b> Bitte gib den OTP-Code im Terminal ein.", screenshot_path)
        
        otp_code = input("Bitte 2FA/OTP-Code eingeben: ").strip()
        otp_input = page.query_selector("input#auth-mfa-otpcode") or page.query_selector("input#ap_otp_code") or page.query_selector("input[name='code']")
        if otp_input:
            otp_input.fill(otp_code)
            # Remember this device if option exists
            remember_device = page.query_selector("input#auth-mfa-remember-device") or page.query_selector("input[name='rememberDevice']")
            if remember_device:
                remember_device.check()
            
            # Submit OTP
            submit_btn = page.query_selector("input#auth-signin-button") or page.query_selector("input#submit") or page.query_selector("#cvf-submit-button input")
            if submit_btn:
                submit_btn.click()
            else:
                page.keyboard.press("Enter")
            time.sleep(5)
            
    # Final check
    if check_login_status(page):
        logger.info("🎉 Login successful and verified!")
        send_telegram("🎉 <b>Amazon Sniper Login erfolgreich!</b> Session ist jetzt aktiv.")
        return True
    else:
        logger.error("❌ Login failed. Please check credentials or run again to retry.")
        screenshot_path = "login_failed.png"
        page.screenshot(path=screenshot_path)
        send_telegram("❌ <b>Amazon Sniper Login fehlgeschlagen!</b>", screenshot_path)
        return False

def verify_purchase_success(page):
    """Verifies if the purchase was actually successful by scanning the page."""
    success_keywords = [
        "vielen dank", "thank you", "bestellung aufgegeben", "order placed",
        "bestätigung", "confirmation", "eingegangen"
    ]
    
    # Check URL first
    url = page.url.lower()
    if any(k in url for k in ["thankyou", "thank-you", "confirmation", "checkout-complete"]):
        logger.info(f"Verified success by URL: {page.url}")
        return True
        
    # Check page content
    try:
        body_text = page.inner_text("body").lower()
        for kw in success_keywords:
            if kw in body_text:
                logger.info(f"Verified success by page text match: '{kw}'")
                return True
    except Exception as e:
        logger.error(f"Error reading body text during verification: {e}")
        
    return False

def checkout_and_buy(page, dry_run=False):
    """Handles the buy-now / checkout execution."""
    logger.info("Executing purchase flow...")
    
    # Wait for the checkout page or confirmation to load
    try:
        page.wait_for_load_state("load", timeout=10000)
    except Exception:
        logger.debug("Timeout waiting for load state, continuing anyway")
    
    # Find and click the 'Place your order' button
    # Common Amazon place-order buttons
    place_order_selectors = [
        "input#submitOrderButtonId",
        "input[name='placeYourOrder1']",
        "input[value='Jetzt kaufen']",
        "input[value='Bestellung aufgeben']",
        "#placeYourOrder input",
        "button:has-text('Jetzt kaufen')",
        "button:has-text('Bestellung aufgeben')"
    ]
    
    found_button = None
    for selector in place_order_selectors:
        try:
            element = page.query_selector(selector)
            if element and element.is_visible() and element.is_enabled():
                logger.info(f"Found Place Order button via: {selector}")
                found_button = element
                break
        except Exception as e:
            logger.debug(f"Selector {selector} failed or not present: {e}")
            
    if not found_button:
        # Try generic clicking on elements with specific texts
        try:
            buttons = page.query_selector_all("input, button")
            for btn in buttons:
                val = (btn.get_attribute("value") or "").lower()
                txt = (btn.inner_text() or "").lower()
                if "jetzt kaufen" in val or "jetzt kaufen" in txt or "bestellung aufgeben" in val or "bestellung aufgeben" in txt:
                    logger.info("Found matching buy button by attribute/text.")
                    found_button = btn
                    break
        except Exception as e:
            logger.error(f"Fallback buy button selection failed: {e}")
            
    if not found_button:
        logger.error("Could not find the 'Place Order' button on the checkout page!")
        # Silent failure as per user request
        return False
        
    if dry_run:
        logger.info("🔥 [DRY RUN] Would have clicked 'Place Order' button. Checkout verification succeeded in Dry Run mode!")
        send_telegram("🧪 <b>Sniper Dry-Run erfolgreich!</b> Bestell-Button wurde gefunden und wäre jetzt geklickt worden. Kauf nicht abgeschlossen.")
        return True
        
    # Real click
    logger.info("Clicking Place Order button...")
    found_button.click()
    
    # Wait for confirmation page
    logger.info("Order clicked. Waiting for confirmation page...")
    time.sleep(5)
    try:
        page.wait_for_load_state("load", timeout=10000)
    except Exception:
        logger.debug("Timeout waiting for confirmation load state, continuing anyway")
    
    if verify_purchase_success(page):
        logger.info("🎉 PURCHASE CONFIRMED AND VERIFIED SUCCESSFULLY!")
        send_telegram("🚀🚀🚀 <b>KAUF ERFOLGREICH VERIFIZIERT!</b> Die Midea PortaSplit wurde erfolgreich gekauft!")
        return True
    else:
        logger.error("⚠️ Verification failed! Checkout completed, but confirmation page was not verified. Might have gone out of stock.")
        # Silent failure as per user request
        return False

def monitor_and_snipe(page, asin, max_price, interval, dry_run=False, timeout_mins=0):
    """Monitors the ASIN page and triggers buying if available."""
    url = f"https://www.amazon.de/dp/{asin}"
    logger.info(f"Starting Sniper Loop for ASIN {asin} with max price {max_price}€ and interval {interval}s")
    
    consecutive_captcha_failures = 0
    start_time = time.time()
    max_duration = timeout_mins * 60 if timeout_mins > 0 else float('inf')
    
    while time.time() - start_time < max_duration:
        try:
            logger.info(f"Polling {url}...")
            # Navigate with a cache-busting parameter or randomized user behavior
            page.goto(f"{url}?smid=A3JWKAKR8XB7XF&psc=1" if random.random() > 0.5 else url, timeout=30000)
            
            # Check for Captcha on product page
            if page.query_selector("img#auth-captcha-image") or page.query_selector("img#ap_captcha_img") or "captcha" in page.url.lower():
                consecutive_captcha_failures += 1
                logger.warning(f"Amazon page threw a captcha (Failures: {consecutive_captcha_failures})")
                if consecutive_captcha_failures >= 5:
                    send_telegram("⚠️ <b>Sniper blockiert!</b> Zu viele Captchas hintereinander auf der Produktseite. Pausiere kurz.")
                    time.sleep(300) # Sleep 5 mins to cool down
                time.sleep(random.uniform(10, 20))
                continue
                
            consecutive_captcha_failures = 0
            
            # Extract Title
            title_elem = page.query_selector("#productTitle")
            title = title_elem.inner_text().strip()[:50] if title_elem else "Unknown Product"
            
            # Check Price
            price = None
            price_selectors = [
                "#corePrice_feature_div .a-offscreen",
                "#price_inside_buybox",
                "#corePrice_desktop .a-offscreen",
                ".a-price .a-offscreen"
            ]
            for sel in price_selectors:
                elem = page.query_selector(sel)
                if elem:
                    price_str = elem.inner_text().strip()
                    # Parse price string (e.g. 599,00 € or 599.00)
                    price_match = re.search(r"([\d\.,\s]+)", price_str)
                    if price_match:
                        clean_price = price_match.group(1).replace(" ", "").replace(".", "").replace(",", ".")
                        try:
                            price = float(clean_price)
                            break
                        except ValueError:
                            continue
            
            # Check Availability / Buy Box Buttons
            buy_now_btn = page.query_selector("#buy-now-button")
            add_to_cart_btn = page.query_selector("#add-to-cart-button")
            
            availability_elem = page.query_selector("#availability")
            availability_text = availability_elem.inner_text().strip() if availability_elem else ""
            
            is_available = (buy_now_btn is not None) or (add_to_cart_btn is not None) or ("derzeit nicht verfügbar" not in availability_text.lower() and availability_text != "")
            
            logger.info(f"Product: {title} | Price: {price}€ | Available: {is_available}")
            
            if is_available:
                if price and price > max_price:
                    logger.warning(f"⚠️ Item available, but price ({price}€) exceeds max limit ({max_price}€).")
                else:
                    logger.info("🔥 ITEM IS AVAILABLE AND WITHIN PRICE LIMIT! TRIGGERING BUY FLOW...")
                    
                    if buy_now_btn:
                        logger.info("Clicking Buy Now...")
                        buy_now_btn.click()
                    elif add_to_cart_btn:
                        logger.info("Clicking Add to Cart, then going to checkout...")
                        add_to_cart_btn.click()
                        time.sleep(2)
                        page.goto("https://www.amazon.de/gp/cart/view.html")
                        checkout_btn = page.query_selector("input[name='proceedToRetailCheckout']")
                        if checkout_btn:
                            checkout_btn.click()
                        else:
                            page.goto("https://www.amazon.de/gp/checkout/html/select-shipping-address.html")
                            
                    # Execute purchase
                    success = checkout_and_buy(page, dry_run=dry_run)
                    if success:
                        logger.info("Sniper job completed successfully! Exiting.")
                        break
                    else:
                        logger.warning("Purchase failed or could not be verified. Resuming sniper loop in 5 seconds...")
                        time.sleep(5)
                        continue
                        
        except Exception as e:
            logger.error(f"Error in sniper loop: {e}", exc_info=True)
            
        # Randomize interval slightly to look human
        sleep_time = interval + random.uniform(-1.5, 3.0)
        sleep_time = max(1.0, sleep_time)
        time.sleep(sleep_time)

def run_sniper_once(asin, max_price, dry_run=False, proxy=None, timeout_mins=5):
    """Launches Playwright and runs the sniper loop for a maximum of the specified minutes."""
    user_data_dir = os.path.join(os.getcwd(), "user_data")
    
    with sync_playwright() as p:
        launch_args = {
            "user_data_dir": user_data_dir,
            "headless": True,
            "viewport": {"width": 1280, "height": 800},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        if proxy:
            launch_args["proxy"] = {"server": proxy}
            
        context = p.chromium.launch_persistent_context(**launch_args)
        page = context.new_page()
        page.add_init_script("delete navigator.__proto__.webdriver")
        
        # Check login
        if not check_login_status(page):
            logger.error("Session expired! Please login manually first.")
            send_telegram("❌ <b>Sniper-Start fehlgeschlagen!</b> Die Amazon-Session ist abgelaufen. Bitte führe manuell <code>python sniper.py login</code> aus.")
            context.close()
            return False
            
        # Run monitor loop but with a specified timeout
        start_time = time.time()
        max_duration = timeout_mins * 60
        url = f"https://www.amazon.de/dp/{asin}"
        
        logger.info(f"Starting aggressive sniper loop for ASIN {asin} (Max {max_duration}s)...")
        
        consecutive_captcha_failures = 0
        success = False
        
        while time.time() - start_time < max_duration:
            try:
                # Poll URL
                page.goto(f"{url}?smid=A3JWKAKR8XB7XF&psc=1" if random.random() > 0.5 else url, timeout=30000)
                
                if page.query_selector("img#auth-captcha-image") or page.query_selector("img#ap_captcha_img") or "captcha" in page.url.lower():
                    consecutive_captcha_failures += 1
                    logger.warning(f"Amazon page threw a captcha (Failures: {consecutive_captcha_failures})")
                    if consecutive_captcha_failures >= 5:
                        logger.warning("Too many captchas, cooling down.")
                        time.sleep(60)
                    time.sleep(random.uniform(5, 10))
                    continue
                    
                consecutive_captcha_failures = 0
                
                title_elem = page.query_selector("#productTitle")
                title = title_elem.inner_text().strip()[:50] if title_elem else "Unknown Product"
                
                # Price check
                price = None
                price_selectors = [
                    "#corePrice_feature_div .a-offscreen",
                    "#price_inside_buybox",
                    "#corePrice_desktop .a-offscreen",
                    ".a-price .a-offscreen"
                ]
                for sel in price_selectors:
                    elem = page.query_selector(sel)
                    if elem:
                        price_str = elem.inner_text().strip()
                        price_match = re.search(r"([\d\.,\s]+)", price_str)
                        if price_match:
                            clean_price = price_match.group(1).replace(" ", "").replace(".", "").replace(",", ".")
                            try:
                                price = float(clean_price)
                                break
                            except ValueError:
                                continue
                
                buy_now_btn = page.query_selector("#buy-now-button")
                add_to_cart_btn = page.query_selector("#add-to-cart-button")
                
                availability_elem = page.query_selector("#availability")
                availability_text = availability_elem.inner_text().strip() if availability_elem else ""
                
                is_available = (buy_now_btn is not None) or (add_to_cart_btn is not None) or ("derzeit nicht verfügbar" not in availability_text.lower() and availability_text != "")
                
                logger.info(f"Product: {title} | Price: {price}€ | Available: {is_available}")
                
                if is_available:
                    if price and price > max_price:
                        logger.warning(f"⚠️ Item available, but price ({price}€) exceeds limit ({max_price}€).")
                    else:
                        logger.info("🔥 ITEM IS AVAILABLE! BUYING NOW...")
                        if buy_now_btn:
                            buy_now_btn.click()
                        elif add_to_cart_btn:
                            add_to_cart_btn.click()
                            time.sleep(2)
                            page.goto("https://www.amazon.de/gp/cart/view.html")
                            checkout_btn = page.query_selector("input[name='proceedToRetailCheckout']")
                            if checkout_btn:
                                checkout_btn.click()
                            else:
                                page.goto("https://www.amazon.de/gp/checkout/html/select-shipping-address.html")
                                
                        success = checkout_and_buy(page, dry_run=dry_run)
                        if success:
                            break
                            
            except Exception as e:
                logger.error(f"Error in sniper loop: {e}")
                
            time.sleep(random.uniform(5, 10))
            
        context.close()
        return success

def listen_gmail_trigger(asin, max_price, dry_run=False, proxy=None, timeout_mins=5):
    """Listens to Gmail for trigger emails and starts the sniper run."""
    import imaplib
    import email
    from email.header import decode_header
    
    gmail_user = os.getenv("GMAIL_USER")
    gmail_pass = os.getenv("GMAIL_APP_PASS")
    
    if not gmail_user or not gmail_pass:
        logger.error("Gmail configuration missing (GMAIL_USER or GMAIL_APP_PASS in .env).")
        sys.exit(1)
        
    logger.info(f"Starting Gmail Trigger Listener for {gmail_user}...")
    send_telegram("📡 <b>Gmail Trigger-Listener gestartet!</b> Ich lausche auf Benachrichtigungen von bestell.bar...")
    
    import urllib.parse
    import re

    while True:
        try:
            # Connect to Gmail IMAP
            mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
            mail.login(gmail_user, gmail_pass)
            mail.select("inbox")
            
            # Search for UNREAD emails from support@bestell.bar
            status, messages = mail.search(None, '(UNSEEN FROM "support@bestell.bar")')
            
            triggered = False
            trigger_subject = ""
            active_asin = asin
            
            if messages and messages[0] != b'':
                mail_ids = messages[0].split()
                logger.info(f"Found {len(mail_ids)} unread trigger emails.")
                
                for mail_id in mail_ids:
                    # Fetch subject to verify
                    status, data = mail.fetch(mail_id, "(RFC822.SIZE BODY[HEADER.FIELDS (SUBJECT)])")
                    for response_part in data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            subject, encoding = decode_header(msg["Subject"])[0]
                            if isinstance(subject, bytes):
                                subject = subject.decode(encoding or "utf-8")
                            
                            logger.info(f"Checking email: {subject}")
                            
                            # Check if it matches our product (PortaSplit)
                            if "midea portasplit" in subject.lower():
                                logger.info("🔥 TRIGGER MATCHED! Midea PortaSplit is available!")
                                trigger_subject = subject
                                triggered = True
                                
                                # Fetch full email to parse ASIN from links
                                status, full_data = mail.fetch(mail_id, "(RFC822)")
                                body = ""
                                for part in full_data:
                                    if isinstance(part, tuple):
                                        full_msg = email.message_from_bytes(part[1])
                                        if full_msg.is_multipart():
                                            for subpart in full_msg.walk():
                                                content_type = subpart.get_content_type()
                                                content_disposition = str(subpart.get("Content-Disposition"))
                                                if content_type in ["text/plain", "text/html"] and "attachment" not in content_disposition:
                                                    payload = subpart.get_payload(decode=True)
                                                    if payload:
                                                        body += payload.decode(subpart.get_content_charset() or "utf-8", errors="ignore")
                                        else:
                                            payload = full_msg.get_payload(decode=True)
                                            if payload:
                                                body += payload.decode(full_msg.get_content_charset() or "utf-8", errors="ignore")
                                
                                # Find Amazon links and extract ASIN
                                links = re.findall(r"https?://[^\s\"<>]+", body)
                                extracted_asin = None
                                for link in links:
                                    unquoted = urllib.parse.unquote(link)
                                    if "amazon.de" in unquoted.lower():
                                        match = re.search(r"/(?:dp|gp/product|d)/([A-Z0-9]{10})", unquoted, re.IGNORECASE)
                                        if match:
                                            extracted_asin = match.group(1).upper()
                                            break
                                
                                if extracted_asin:
                                    logger.info(f"Extracted ASIN from email: {extracted_asin}")
                                    active_asin = extracted_asin
                                else:
                                    logger.warning("No Amazon link/ASIN found in email. Skipping trigger (not an Amazon deal).")
                                    triggered = False
                                    # Mark as read so we don't trigger again
                                    mail.store(mail_id, "+FLAGS", "\\Seen")
                                    break
                                
                                # Mark as read so we don't trigger again
                                mail.store(mail_id, "+FLAGS", "\\Seen")
                                break
                    if triggered:
                        break
            
            mail.logout()
            
            if triggered:
                logger.info(f"Triggered by email: {trigger_subject} | ASIN: {active_asin}")
                send_telegram(f"🚨 <b>Trigger empfangen!</b>\nBetreff: <i>{trigger_subject}</i>\nTarget ASIN: <code>{active_asin}</code>\nStarte Amazon Sniper sofort!")
                
                # Start Playwright sniper run
                run_sniper_once(active_asin, max_price, dry_run, proxy, timeout_mins=timeout_mins)
                
                logger.info("Sniper run finished. Returning to listener mode...")
                time.sleep(10) # Cool down before checking again
                
        except Exception as e:
            logger.error(f"Error in Gmail listener loop: {e}")
            
        # Poll every 15 seconds
        time.sleep(15)

def main():
    parser = argparse.ArgumentParser(description="Amazon Sniper Bot using Playwright")
    parser.add_argument("action", choices=["login", "run", "watch-gmail"], help="Action to perform")
    parser.add_argument("--asin", default="B0GXDWTFR5", help="ASIN of the Amazon product")
    parser.add_argument("--email", help="Amazon email (only for login)")
    parser.add_argument("--password", help="Amazon password (only for login)")
    parser.add_argument("--max-price", type=float, default=700.0, help="Maximum price to buy the product (Euro)")
    parser.add_argument("--interval", type=float, default=10.0, help="Monitoring poll interval (seconds)")
    parser.add_argument("--dry-run", action="store_true", help="Navigate to checkout but do NOT click the final purchase button")
    parser.add_argument("--proxy", help="Proxy server to use, e.g. socks5://127.0.0.1:1080")
    parser.add_argument("--timeout-mins", type=int, default=0, help="Duration to run the session in minutes. In passive 'watch-gmail' mode, this governs the triggered run length (default: 5). In active 'run' mode, default is 0 (indefinite/unlimited polling).")
    
    args = parser.parse_args()
    
    # Store user data context in current folder
    user_data_dir = os.path.join(os.getcwd(), "user_data")
    
    if args.action == "watch-gmail":
         # Start Gmail trigger listener directly (it launches Playwright only when triggered)
         # If timeout-mins is 0 (the default), pass 5 (mins) as the fallback for triggered sessions
         t_mins = args.timeout_mins if args.timeout_mins > 0 else 5
         listen_gmail_trigger(args.asin, args.max_price, dry_run=args.dry_run, proxy=args.proxy, timeout_mins=t_mins)
         sys.exit(0)
        
    with sync_playwright() as p:
        # Launch persistent context
        # We mask automation features to look like a standard user
        launch_args = {
            "user_data_dir": user_data_dir,
            "headless": True, # Run headless for CLI operation
            "viewport": {"width": 1280, "height": 800},
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        }
        if args.proxy:
            launch_args["proxy"] = {"server": args.proxy}
            
        context = p.chromium.launch_persistent_context(**launch_args)
        
        page = context.new_page()
        
        # Sneakily bypass basic automation detections
        page.add_init_script("delete navigator.__proto__.webdriver")
        
        if args.action == "login":
            if not args.email or not args.password:
                logger.error("Please provide both --email and --password for login.")
                sys.exit(1)
            handle_login(page, args.email, args.password)
            
        elif args.action == "run":
            # Check if we are already logged in
            logger.info("Checking session validity...")
            if not check_login_status(page):
                logger.warning("⚠️ Session not active or expired. Please run 'login' first to establish cookies.")
                send_telegram("⚠️ <b>Amazon Sniper gestoppt!</b> Bitte logge dich zuerst ein: <code>python sniper.py login</code>")
                sys.exit(1)
                
            # If the user wants a finite active run, they can use --timeout-mins (only if explicitly set or we just let it run indefinitely by default)
            # To be safe and flexible, we respect --timeout-mins if set (or we run indefinitely if they didn't pass it, but wait, having it optional is better).
            # Actually, let's allow run to also support the timeout!
            start_time = time.time()
            max_duration = args.timeout_mins * 60
            
            # Wrap the monitor_and_snipe logic to support manual timeout
            logger.info(f"Starting active sniper. Timeout set to {args.timeout_mins} minutes." if args.timeout_mins > 0 else "Starting active sniper indefinitely.")
            
            # We can modify monitor_and_snipe to accept a timeout or we can just run it
            # Let's adjust monitor_and_snipe signature to support timeout too!
            monitor_and_snipe(page, args.asin, args.max_price, args.interval, dry_run=args.dry_run, timeout_mins=args.timeout_mins)
            
        context.close()

if __name__ == "__main__":
    main()
