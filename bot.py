"""
Run this file to start the bot (after filling in your .env).

Usage in Telegram:
  /start    - subscribe to alerts
  /stop     - unsubscribe
  /status   - see how many tokens are being tracked
  /checknow - run a check right now and see the result immediately
              (doesn't wait for the scheduled interval - useful for
              testing without waiting CHECK_INTERVAL_MINUTES)

The bot also checks all Robinhood Chain tokens automatically every
CHECK_INTERVAL_MINUTES (see config.py) and messages every subscriber
when it finds a volume spike. Each coin only ever alerts once.
"""
import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from config import TELEGRAM_BOT_TOKEN, CHECK_INTERVAL_MINUTES
from state import load_state, save_state, add_subscriber, remove_subscriber
from blockscout import get_all_token_addresses
from dexscreener import enrich_with_volume
from spike_detector import check_for_spikes

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("rh_volume_bot")

# httpx logs the full request URL at INFO level, which for Telegram's API
# includes your bot token - quiet it down so the token never hits the logs
logging.getLogger("httpx").setLevel(logging.WARNING)


def format_spike_message(spike: dict) -> str:
    if spike["multiplier"] is not None:
        return (
            f"🚨 *Volume spike*: {spike['name']} ({spike['symbol']})\n"
            f"~${spike['cycle_volume']:,.0f} traded this cycle vs a normal "
            f"~${spike['baseline_avg']:,.0f} ({spike['multiplier']}x)\n"
            f"`{spike['address']}`"
        )
    return (
        f"🚨 *New activity*: {spike['name']} ({spike['symbol']})\n"
        f"~${spike['cycle_volume']:,.0f} traded this cycle - previously little/no volume\n"
        f"`{spike['address']}`"
    )


async def run_check() -> tuple[list[dict], int]:
    """
    Does the actual work: pull every token address, get real volume for
    each, check for spikes. Returns (spikes_found, tokens_checked).
    Raises on failure - callers decide how to report that.
    """
    state = load_state()
    tokens = await get_all_token_addresses()
    tokens = await enrich_with_volume(tokens)
    spikes = check_for_spikes(state, tokens)
    save_state(state)
    return spikes, len(tokens)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = load_state()
    added = add_subscriber(state, update.effective_chat.id)
    if added:
        await update.message.reply_text(
            f"✅ Subscribed. I'll check every {CHECK_INTERVAL_MINUTES} minutes and ping you here "
            "when any Robinhood Chain coin's volume suddenly jumps. "
            "Send /checknow anytime to run a check immediately instead of waiting."
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
    alerted = len(state.get("alerted_tokens", []))
    subs = len(state["subscribers"])
    await update.message.reply_text(
        f"Tracking {tracked} token(s). {alerted} have already alerted (won't repeat). "
        f"{subs} subscriber(s). Checking every {CHECK_INTERVAL_MINUTES} minutes."
    )


async def checknow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 Checking now...")
    try:
        spikes, tokens_checked = await run_check()
    except Exception as e:
        log.exception("Manual check failed")
        await update.message.reply_text(f"❌ Check failed: {e}")
        return

    if not spikes:
        await update.message.reply_text(f"No new spikes right now. {tokens_checked} tokens checked.")
        return

    for spike in spikes:
        await update.message.reply_text(format_spike_message(spike), parse_mode="Markdown")


async def check_job(context: ContextTypes.DEFAULT_TYPE):
    try:
        spikes, tokens_checked = await run_check()
    except Exception:
        log.exception("Scheduled check failed")
        return

    if not spikes:
        log.info("Check complete - no spikes, %d tokens tracked", tokens_checked)
        return

    state = load_state()
    for spike in spikes:
        message = format_spike_message(spike)
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
    app.add_handler(CommandHandler("checknow", checknow))

    app.job_queue.run_repeating(check_job, interval=CHECK_INTERVAL_MINUTES * 60, first=15)

    log.info("Bot starting...")
    app.run_polling()


if __name__ == "__main__":
    main()
