# RH Volume Spike Bot

Pings you on Telegram when any coin on Robinhood Chain has a sudden
volume increase. Watches every token on the chain automatically - no
manual list to maintain.

## How the spike detection actually works
Robinhood Chain's free explorer only gives a running 24-hour volume
number per token, not a live "last 15 minutes" figure. So every check,
the bot:
1. Grabs every token's current 24h volume
2. Subtracts the last reading to estimate volume in just this cycle
3. Compares that to the token's average cycle-volume over the last
   several checks (2 hours by default)
4. Alerts if this cycle is 5x+ that average (and the average itself is
   above a small noise floor, so near-dead tokens don't false-alarm)

It needs a few checks to build up history before it can flag anything
- expect it to go quiet for the first ~2 hours after you start it while
it learns each token's normal baseline.

## What's in this project
```
tg_rh_volume_bot/
  .env.example      <- template, only needs your Telegram bot token
  config.py          <- check frequency, spike sensitivity - tune anytime
  requirements.txt
  state.py            <- saves subscribers + volume history to a file
  blockscout.py         <- pulls every token's volume from Robinhood Chain's explorer
  spike_detector.py      <- the actual spike math
  bot.py                  <- run this - handles Telegram + the recurring check
```

## Deploying (Railway, free tier)

1. Create a **new** bot with @BotFather on Telegram (separate from your
   scanner bot, so alerts don't get mixed up in one chat) - you'll get
   a token.

2. Create a new GitHub repo, upload this whole `tg_rh_volume_bot` folder
   (leave `.env.example` blank - don't upload real keys).

3. On railway.app: New Project → Deploy from GitHub repo → pick this repo.

4. In the project's **Variables** tab, add one variable:
   `TELEGRAM_BOT_TOKEN` = your real token from step 1.

5. Under Settings → Deploy, set the Start Command to:
   ```
   python bot.py
   ```

6. Check Deployments → Logs for `Bot starting...` with no errors.

7. In Telegram, message your new bot `/start`. That's it - you'll get
   alerts pushed to that chat automatically from now on. `/status`
   shows how many tokens are tracked; `/stop` unsubscribes.

## Tuning
All in `config.py`:
- `CHECK_INTERVAL_MINUTES` - how often it checks (default 20)
- `SPIKE_MULTIPLIER` - how big a jump counts as "sudden" (default 5x)
- `MIN_BASELINE_VOLUME_USD` - ignores near-dead tokens below this
- `MAX_TOKEN_PAGES` - safety cap on tokens checked per cycle

## Known untested piece
The token list parsing (`blockscout.py`) is written from Blockscout's
documented API shape but hasn't been run against the live Robinhood
Chain explorer yet. If it errors out or `volume_24h` comes back empty
once deployed, send me the error/logs and I'll fix the parsing.
