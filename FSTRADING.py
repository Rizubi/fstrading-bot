import os
from binance.client import Client
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ================= ENV VARIABLES =================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# ================= SETTINGS ======================
SYMBOL = "BTCUSDT"

# Amounts (USD)
SPOT_BUY_USD = 10        # Spot BUY amount
FUTURES_SHORT_USD = 5   # Futures SHORT amount
LEVERAGE = 1

# ================= BINANCE CLIENT ================
client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY)

# ================= /start ========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Access Denied")
        return

    keyboard = [
        [InlineKeyboardButton("🚀 BUY", callback_data="buy")],
        [InlineKeyboardButton("❌ CLOSE", callback_data="close")]
    ]

    await update.message.reply_text(
        "✅ FS Trading Bot LIVE (24x7)\n\n"
        "🚀 BUY = Spot BUY + Futures SHORT\n"
        "❌ CLOSE = Spot SELL + Short CLOSE",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ================= BUTTON HANDLER ================
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ Admin only", show_alert=True)
        return

    # ---------- BUY ----------
    if query.data == "buy":
        try:
            # Spot BUY
            client.create_order(
                symbol=SYMBOL,
                side="BUY",
                type="MARKET",
                quoteOrderQty=SPOT_BUY_USD
            )

            # Futures SHORT
            client.futures_change_leverage(
                symbol=SYMBOL,
                leverage=LEVERAGE
            )

            client.futures_create_order(
                symbol=SYMBOL,
                side="SELL",
                type="MARKET",
                positionSide="SHORT",
                quoteOrderQty=FUTURES_SHORT_USD
            )

            await query.edit_message_text(
                "✅ BUY DONE\nSpot BUY + Futures SHORT executed"
            )

        except Exception as e:
            await query.edit_message_text(f"❌ BUY ERROR:\n{e}")

    # ---------- CLOSE ----------
    if query.data == "close":
        try:
            # ---- Spot SELL (full balance) ----
            asset = SYMBOL.replace("USDT", "")
            bal = client.get_asset_balance(asset=asset)
            qty = float(bal["free"])

            if qty > 0:
                client.create_order(
                    symbol=SYMBOL,
                    side="SELL",
                    type="MARKET",
                    quantity=qty
                )

            # ---- Futures SHORT close ----
            positions = client.futures_position_information(symbol=SYMBOL)
            for p in positions:
                if p["positionSide"] == "SHORT" and float(p["positionAmt"]) < 0:
                    client.futures_create_order(
                        symbol=SYMBOL,
                        side="BUY",
                        type="MARKET",
                        positionSide="SHORT",
                        quantity=abs(float(p["positionAmt"]))
                    )

            await query.edit_message_text(
                "❌ CLOSE DONE\nAll positions closed at market"
            )

        except Exception as e:
            await query.edit_message_text(f"❌ CLOSE ERROR:\n{e}")

# ================= RUN BOT =======================
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(button))
app.run_polling()
