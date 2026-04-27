"""
OpenClaw — AI Chat Agent
Handles the #ai-chat channel and /ask command.
Routes messages to the best model automatically.
Maintains conversation history per thread.
"""

import asyncio
import logging
import discord
from datetime import datetime, timedelta
from collections import defaultdict
from utils.ai_router import route, pick_model, get_available_models, MODELS, build_system_prompt

logger = logging.getLogger("openclaw.ai_chat")

# Conversation history per channel/thread (last 10 messages)
_history: dict[int, list[dict]] = defaultdict(list)
MAX_HISTORY = 10


def get_bot_context(bot) -> dict:
    """Extracts live context from bot state for AI awareness."""
    return {
        "revenue":   getattr(bot, 'revenue_log', {}),
        "ventures":  getattr(bot, 'active_ventures', []),
        "target":    500,
        "days_left": 30,
    }


def add_to_history(channel_id: int, role: str, content: str):
    history = _history[channel_id]
    history.append({"role": role, "content": content[:2000]})
    if len(history) > MAX_HISTORY:
        history.pop(0)


def model_status_embed(bot) -> discord.Embed:
    """Shows status of all configured AI models."""
    available = get_available_models()
    embed = discord.Embed(
        title="🤖 AI Models — OpenClaw",
        description="Your full AI stack. Use `/ask` or chat in #ai-chat.",
        color=0x00c8f0,
        timestamp=datetime.utcnow()
    )
    for key, model in MODELS.items():
        status = "✅ Connected" if key in available else "⚠️ No API key"
        embed.add_field(
            name=f"{model['emoji']} {model['name']}",
            value=f"{status}\n{model['description']}",
            inline=True
        )
    embed.add_field(
        name="🔀 Auto-routing",
        value=(
            "🟣 Claude → listings, copy, strategy\n"
            "🟢 GPT-4o → general chat\n"
            "🔵 Gemini → research, trends\n"
            "🟡 DeepSeek → analysis, reasoning\n"
            "⚪ GLM → code generation"
        ),
        inline=False
    )
    embed.set_footer(text="Use /ask @model to force a specific model")
    return embed


async def handle_chat_message(message: discord.Message, bot):
    """
    Handles a message in #ai-chat.
    Auto-routes to best model, maintains history, streams response.
    """
    if message.author.bot:
        return

    content = message.content.strip()
    if not content:
        return

    channel = message.channel
    channel_id = channel.id

    # Show typing indicator
    async with channel.typing():
        # Add to history
        add_to_history(channel_id, "user", content)

        # Build context
        context = get_bot_context(bot)

        # Pick model
        model_key = pick_model(content)
        model_info = MODELS.get(model_key, MODELS["claude"])

        try:
            # Route to best model
            response, used_model = await route(
                prompt=content,
                bot_context=context,
                max_tokens=1500
            )

            # Add response to history
            add_to_history(channel_id, "assistant", response)

            # Format response
            used_info = MODELS.get(used_model, model_info)

            # Split long responses
            chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]

            for i, chunk in enumerate(chunks):
                if i == 0:
                    # First chunk gets model attribution
                    footer = f"\n\n{used_info['emoji']} *{used_info['name']}*"
                    await channel.send(chunk + footer)
                else:
                    await channel.send(chunk)

        except Exception as e:
            logger.error(f"Chat error: {e}")
            await channel.send(f"❌ Error: {e}")


async def run_ai_chat_monitor(bot, channel_id: int):
    """
    Monitors the #ai-chat channel and responds to messages.
    """
    await bot.wait_until_ready()
    channel = bot.get_channel(channel_id)

    if not channel:
        logger.error(f"AI chat channel {channel_id} not found")
        return

    logger.info(f"AI Chat monitor running on #{channel.name}")

    # Post welcome message
    available = get_available_models()
    model_list = " • ".join([
        f"{MODELS[k]['emoji']} {MODELS[k]['name']}"
        for k in available
        if k in MODELS
    ])

    embed = discord.Embed(
        title="🤖 AI Assistant Ready",
        description=(
            f"Chat with your full AI stack right here.\n\n"
            f"**Active models:** {model_list}\n\n"
            f"Just type a message — I'll route it to the best model automatically.\n"
            f"Or use `/ask` to chat from anywhere in the server.\n\n"
            f"**I know your store data** — ask me anything about your products, "
            f"revenue, strategy, or what to build next."
        ),
        color=0x00c8f0,
        timestamp=datetime.utcnow()
    )
    await channel.send(embed=embed)

    # Listen for messages via bot's on_message event
    # (wired up in discord_bot.py)
    while not bot.is_closed():
        await asyncio.sleep(60)  # Keep alive
