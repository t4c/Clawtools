# LurkMaster 🎯

LurkMaster is a lightweight, command-line Amazon stock monitoring and sniper bot powered by Python and Playwright. It runs completely headless, acts like a real human browser to bypass standard detection, and monitors specific product availability (ASIN). Once the target item becomes available and is within your defined price limit, LurkMaster instantly triggers the purchase flow.

Additionally, it can run as an idle background listener that consumes real-time email stock notifications from external services like **bestell.bar** via Gmail IMAP. When a notification is received, the sniper launches immediately to snap up the deal.

---

## Features

- **Headless Browser Automation:** Driven by Playwright, masking automation signatures to behave like a standard browser.
- **Instant Checkout:** Swiftly processes the buy-now or cart-checkout pipeline.
- **Gmail IMAP Listener:** Remains completely idle and only spawns active browser instances when an email notification from `support@bestell.bar` is received.
- **Telegram Notifications:** Sends real-time status alerts, dry-run successes, and purchase confirmations directly to your Telegram channel.
- **Interactive Verification Support:** Pauses and asks for manual CAPTCHA or 2FA/OTP entry in the console if Amazon requests verification during the login process.
- **Dry-Run Mode:** Test your setup safely without placing any actual orders.

---

## Requirements

- Python 3.8+
- A valid Amazon.de account
- A Telegram Bot (optional, for alerts)
- A Gmail account with an App Password (optional, for the mail listener)

---

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/t4c/LurkMaster.git
   cd LurkMaster
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Playwright Chromium Browser:**
   ```bash
   playwright install chromium
   ```

---

## Configuration

Create a `.env` file in the root of the project directory to store your credentials safely:

```ini
# Amazon Credentials (only needed for the initial 'login' command)
AMAZON_EMAIL=your-amazon-email@example.com
AMAZON_PASSWORD=your-secure-amazon-password

# Telegram Notification Settings (Optional)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
TELEGRAM_HOME_CHANNEL=-100123456789

# Gmail Listener Settings (Optional, for bestell.bar triggers)
# WARNING: You must use a Gmail App Password, NOT your master password!
GMAIL_USER=your-gmail-address@gmail.com
GMAIL_APP_PASS=abcd efgh ijkl mnop
```

> ⚠️ **IMPORTANT NOTE ON GMAIL ACCESS:** To allow the listener to read notification emails, you must enable **2-Step Verification** on your Google Account and generate an **App Password** (Select App: *Other*, name it `LurkMaster`). Use this 16-character code as `GMAIL_APP_PASS`.

---

## Usage

### 1. Establish Your Session (Login)
Amazon sessions are saved locally under the `user_data/` directory as browser cookies. Before running the sniper, you must log in once to store these session files:

```bash
python LurkMaster.py login --email "your-email@example.com" --password "your-password"
```

*If Amazon prompts you for a **CAPTCHA** or **Two-Factor Authentication (2FA) / OTP** code, the console will pause and ask you to enter the code directly in your terminal.*

---

### 2. Run the Stock Sniper (Active Polling Mode)
This mode continuously polls the Amazon product page at a regular interval:

```bash
# Run a safe dry-run test (does not click the final buy button)
python LurkMaster.py run --asin B0GXDWTFR5 --max-price 700.0 --interval 10 --dry-run

# Run active production sniper
python LurkMaster.py run --asin B0GXDWTFR5 --max-price 700.0 --interval 10
```

---

### 3. Run the Gmail Trigger Listener (Idle Passive Mode)
Instead of hammering the Amazon servers and risking a block, you can sign up for stock notifications on **[bestell.bar](https://bestell.bar)** for your desired product.

Start the idle Gmail listener:
```bash
python LurkMaster.py watch-gmail --asin B0GXDWTFR5 --max-price 700.0 --dry-run
```

- The script connects to your Gmail inbox via IMAP.
- It stays idle, polling Gmail every 15 seconds.
- As soon as an unread email from `support@bestell.bar` containing the product name (e.g. "Midea PortaSplit") in the subject arrives, the sniper instantly boots up Playwright, utilizes your saved session cookies, navigates to the checkout page, and triggers the buy flow!

---

## Command Line Arguments

- `action`: Choose between `login`, `run`, or `watch-gmail`.
- `--asin`: The 10-character Amazon Standard Identification Number (default: `B0GXDWTFR5`).
- `--email`: Your Amazon login email (only utilized in `login` mode).
- `--password`: Your Amazon login password (only utilized in `login` mode).
- `--max-price`: Maximum purchase price ceiling in Euros (default: `700.0`).
- `--interval`: Amount of seconds to wait between active poll requests (default: `10.0`).
- `--dry-run`: Navigates through the entire purchasing cart flow but stops right before clicking the final checkout/buy button.
- `--proxy`: Route traffic through a SOCKS5 or HTTP proxy (e.g. `socks5://127.0.0.1:1080`).

---

## Disclaimer

This tool is for educational and personal research purposes only. Use it at your own risk. The author is not responsible for any financial loss, account suspensions, or terms of service violations incurred while using this software. Always test your configuration using the `--dry-run` flag first!
