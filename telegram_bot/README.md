# 🤖 GPT India UPI Telegram Bot

A high-performance Python Telegram Bot that converts ChatGPT Session JSON tokens directly into instant scannable UPI payment QR codes.

---

## 🌟 Key Features

1. **Direct QR Image Sending**: Sends scannable high-resolution QR image directly into the user's Telegram chat.
2. **Customer Key & Credit System**:
   - `/key GPTIND_XXXXXX` to activate license key.
   - Live credit deduction and tracking.
   - **Auto-Refund**: Automatically restores 1 credit if upstream creation fails or times out.
3. **Live Status Tracking**: Live updates in chat ("Logging into ChatGPT session...", "Creating UPI Payment Gateway...", etc.).
4. **Instant Payment Gateway Integration**: Generates payment QR for UPI (`iamubbb@ibl`) when users type `/buy`.
5. **Admin Commands**:
   - `/genkey <credits>` — Generate new customer keys.
   - `/addcredits <key> <amount>` — Top up key balance.
   - `/listkeys` — View all customer keys.
   - `/revoke <key>` — Revoke a key.

---

## 🚀 How to Run Locally

1. Open PowerShell or Terminal in `telegram_bot` directory:
   ```bash
   cd telegram_bot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your Telegram Bot Token in `bot.py` or as an environment variable:
   ```bash
   set TELEGRAM_BOT_TOKEN="your_bot_token_from_botfather"
   ```

4. Run the Bot:
   ```bash
   python bot.py
   ```

---

## ☁️ How to Host 24/7 For Free (No Netlify Limits)

### Option 1: Deploy on Render.com (Recommended Free Hosting)
1. Push `telegram_bot` folder to GitHub.
2. Go to [Render.com](https://render.com) -> New **Background Worker**.
3. Connect your GitHub repository.
4. Set Build Command: `pip install -r requirements.txt`
5. Set Start Command: `python bot.py`
6. Add Environment Variable:
   - `TELEGRAM_BOT_TOKEN`: `your_bot_token`

---

### Option 2: Deploy on VPS or Local Windows Background Service
You can run it in background on any VPS (Ubuntu/Windows):
```bash
nohup python bot.py &
```
