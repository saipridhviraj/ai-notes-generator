"""Telegram bot for AI Notes Generator.

Commands:
  /start   — welcome message
  /generate <topic> — kick off note generation, poll status, approve/reject
              tutor review inline, and send rendered PDFs when done.

Environment variables:
  TELEGRAM_BOT_TOKEN  — from BotFather
  RAILWAY_API_URL     — e.g. https://ai-notes-generator-production.up.railway.app
  APP_API_KEY         — same key set on the Railway service
"""
import asyncio
import io
import logging
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from api_client import get_result, get_status, start_generation, tutor_respond
from pdf_utils import markdown_to_pdf

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
POLL_INTERVAL = 6  # seconds between status polls

logging.basicConfig(
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Status helpers ─────────────────────────────────────────────────────────────

_EMOJI = {
    "running": "⏳",
    "awaiting_tutor": "👨‍🏫",
    "completed": "✅",
    "failed": "❌",
    "rejected": "🚫",
    "max_retries_reached": "⚠️",
    "cancelled": "🚫",
}


def _progress_bar(pct: float) -> str:
    filled = round(pct / 10)
    return "█" * filled + "░" * (10 - filled)


def _status_text(status_data: dict, topic: str) -> str:
    status = status_data.get("status", "running")
    emoji = _EMOJI.get(status, "⏳")
    node = status_data.get("node_label") or status_data.get("current_node") or "…"
    pct = float(status_data.get("progress_percent") or 0)
    bar = _progress_bar(pct)
    return (
        f"{emoji} *Generating notes*\n"
        f"Topic: `{topic}`\n"
        f"Step: {node}\n"
        f"`[{bar}]` {pct:.0f}%"
    )


async def _safe_edit(bot, chat_id: int, message_id: int, text: str, **kwargs):
    """Edit a message, ignoring 'message is not modified' errors."""
    try:
        await bot.edit_message_text(
            chat_id=chat_id, message_id=message_id, text=text, **kwargs
        )
    except BadRequest as e:
        if "not modified" not in str(e).lower():
            raise


# ── Handlers ───────────────────────────────────────────────────────────────────


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *AI Notes Generator*\n\n"
        "Generate structured student & tutor notes on any topic.\n\n"
        "*Commands*\n"
        "• `/generate <topic>` — start generating\n\n"
        "*Example*\n"
        "`/generate Python Decorators`",
        parse_mode="Markdown",
    )


async def cmd_generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    topic = " ".join(context.args).strip()
    if not topic:
        await update.message.reply_text(
            "Please provide a topic.\n_Example:_ `/generate Python Decorators`",
            parse_mode="Markdown",
        )
        return

    msg = await update.message.reply_text(
        f"🚀 Starting generation for: *{topic}*…", parse_mode="Markdown"
    )

    try:
        data = await start_generation(topic)
        session_id = data["session_id"]
    except Exception as e:
        await msg.edit_text(f"❌ Failed to start: {e}")
        return

    # Stash session metadata so callbacks can find it
    context.bot_data.setdefault("sessions", {})[session_id] = {
        "chat_id": update.effective_chat.id,
        "message_id": msg.message_id,
        "topic": topic,
    }

    asyncio.create_task(
        _poll_loop(
            context.application,
            session_id,
            topic,
            update.effective_chat.id,
            msg.message_id,
        )
    )


async def btn_tutor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action, session_id = query.data.split(":", 1)
    approved = action == "approve"
    sessions = context.bot_data.get("sessions", {})
    meta = sessions.get(session_id, {})
    topic = meta.get("topic", session_id)

    label = "✅ Approved" if approved else "❌ Rejected"
    await query.edit_message_text(f"{label} — continuing…", parse_mode="Markdown")

    try:
        await tutor_respond(session_id, approved=approved)
    except Exception as e:
        await query.edit_message_text(f"❌ Failed to submit response: {e}")
        return

    if not approved:
        await query.edit_message_text("🚫 Generation rejected.")
        return

    # Resume polling after approval
    asyncio.create_task(
        _poll_loop(
            context.application,
            session_id,
            topic,
            query.message.chat_id,
            query.message.message_id,
        )
    )


# ── Polling loop ───────────────────────────────────────────────────────────────


async def _poll_loop(
    app: Application,
    session_id: str,
    topic: str,
    chat_id: int,
    message_id: int,
):
    while True:
        await asyncio.sleep(POLL_INTERVAL)

        try:
            status_data = await get_status(session_id)
        except Exception as e:
            logger.warning("Poll error for %s: %s", session_id, e)
            continue

        status = status_data.get("status", "running")

        if status == "awaiting_tutor":
            question = status_data.get("tutor_question") or "Review the plan and approve or reject."
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("✅ Approve", callback_data=f"approve:{session_id}"),
                        InlineKeyboardButton("❌ Reject", callback_data=f"reject:{session_id}"),
                    ]
                ]
            )
            await _safe_edit(
                app.bot,
                chat_id,
                message_id,
                f"👨‍🏫 *Tutor review needed*\n\n{question}",
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
            return  # wait for callback to resume

        if status in ("completed", "failed", "rejected", "max_retries_reached", "cancelled"):
            await _handle_final(app, session_id, status, chat_id, message_id, topic)
            return

        # Still running — update progress bar
        await _safe_edit(
            app.bot,
            chat_id,
            message_id,
            _status_text(status_data, topic),
            parse_mode="Markdown",
        )


# ── Final result ───────────────────────────────────────────────────────────────


async def _handle_final(
    app: Application,
    session_id: str,
    status: str,
    chat_id: int,
    message_id: int,
    topic: str,
):
    if status != "completed":
        emoji = _EMOJI.get(status, "❌")
        await _safe_edit(
            app.bot,
            chat_id,
            message_id,
            f"{emoji} Generation ended with status: *{status}*",
            parse_mode="Markdown",
        )
        return

    await _safe_edit(
        app.bot, chat_id, message_id, "✅ *Notes ready!* Rendering PDFs…", parse_mode="Markdown"
    )

    try:
        result = await get_result(session_id)
    except Exception as e:
        await _safe_edit(app.bot, chat_id, message_id, f"❌ Failed to fetch result: {e}")
        return

    topic_str = result.get("topic") or topic
    slug = topic_str.replace(" ", "_")

    pairs = [
        ("Student Notes", result.get("student_markdown") or ""),
        ("Tutor Notes", result.get("tutor_markdown") or ""),
    ]

    sent = False
    for label, md_text in pairs:
        if not md_text:
            continue
        filename_base = f"{slug}_{label.replace(' ', '_')}"
        try:
            pdf_bytes = await asyncio.get_event_loop().run_in_executor(
                None, markdown_to_pdf, md_text, f"{label} — {topic_str}"
            )
            await app.bot.send_document(
                chat_id=chat_id,
                document=io.BytesIO(pdf_bytes),
                filename=f"{filename_base}.pdf",
                caption=f"📄 *{label}* — {topic_str}",
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error("PDF generation failed for %s: %s — falling back to .md", label, e)
            await app.bot.send_document(
                chat_id=chat_id,
                document=io.BytesIO(md_text.encode()),
                filename=f"{filename_base}.md",
                caption=f"📝 *{label}* (markdown fallback) — {topic_str}",
                parse_mode="Markdown",
            )
        sent = True

    if not sent:
        await app.bot.send_message(chat_id=chat_id, text="⚠️ No note content was returned.")

    await _safe_edit(
        app.bot, chat_id, message_id, f"✅ *Done!* {topic_str}", parse_mode="Markdown"
    )


# ── Entry point ────────────────────────────────────────────────────────────────


def main():
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set")

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("generate", cmd_generate))
    application.add_handler(CallbackQueryHandler(btn_tutor, pattern=r"^(approve|reject):"))

    logger.info("Bot polling…")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
