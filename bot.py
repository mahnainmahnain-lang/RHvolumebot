"""
Run this file to start the bot (after filling in your .env).

Usage in Telegram:
  /start  - subscribe to alerts
  /stop   - unsubscribe
  /status - see how many tokens are being tracked

The bot then checks all Robinhood Chain tokens every
CHECK_INTERVAL_MINUTES (see config.py) and messages every subscriber
when it finds a volume spike.
"""
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import TELEGRAM_BOT_TOKEN, CHECK_INTERVAL_MINUTES
from state import load_state, save_state, add_subscriber, remove_subscriber
from blockscout import get_all_tokens
from spike_detector import check_for_spikes

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("rh_volume_bot")

# httpx logs the full request URL at INFO level, which for Telegram's API
# includes your bot token - quiet it down so the token never hits the logs
logging.getLogger("httpx").setLevel(logging.WARNING)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    added = add_subscriber(state, update.effective_chat.id)
    if added:
        await update.message.reply_text(
            f"✅ Subscribed. I'll check every {CHECK_INTERVAL_MINUTES} minutes and ping you here "
            "when any Robinhood Chain coin's volume suddenly jumps."
        )
    else:
        await update.message.reply_text("You're already subscribed.")


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    removed = remove_subscriber(state, update.effective_chat.id)
    if removed:
        await update.message.reply_text("Unsubscribed - you won't get any more alerts.")
    else:
        await update.message.reply_text("You weren't subscribed.")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    tracked = len(state["token_history"])
    subs = len(state["subscribers"])
    await update.message.reply_text(
        f"Tracking {tracked} token(s). {subs} subscriber(s). "
        f"Checking every {CHECK_INTERVAL_MINUTES} minutes."
    )


async def check_job(context: ContextTypes.DEFAULT_TYPE):
    state = load_state()

    try:
        tokens = await get_all_tokens()
    except Exception as e:
        log.exception("Failed to fetch tokens")
        return

    spikes = check_for_spikes(state, tokens)
    save_state(state)

    if not spikes:
        log.info("Check complete - no spikes, %d tokens tracked", len(tokens))
        return

    for spike in spikes:
        if spike["multiplier"] is not None:
            message = (
                f"🚨 *Volume spike*: {spike['name']} ({spike['symbol']})\n"
                f"~${spike['cycle_volume']:,.0f} traded this cycle vs a normal "
                f"~${spike['baseline_avg']:,.0f} ({spike['multiplier']}x)\n"
                f"`{spike['address']}`"
            )
        else:
            message = (
                f"🚨 *New activity*: {spike['name']} ({spike['symbol']})\n"
                f"~${spike['cycle_volume']:,.0f} traded this cycle - previously little/no volume\n"
                f"`{spike['address']}`"
            )
        for chat_id in state["subscribers"]:
            try:
                await context.bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
            except Exception:
                log.exception("Failed to message subscriber %s", chat_id)


def main():
    if not TELEGRAM_BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set - fill in your .env file first.")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CommandHandler("status", status))

    app.job_queue.run_repeating(check_job, interval=CHECK_INTERVAL_MINUTES * 60, first=15)

    log.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
