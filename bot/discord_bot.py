"""
OpenClaw Discord Bot — Full Command Center
Multi-model AI chat + autonomous business agents.
"""

import asyncio
import logging
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime

from config.settings import settings
from agents.opportunity_scanner import (
    run_opportunity_scanner, scan_for_opportunities,
    opportunity_embed, OpportunityApproveView
from agents.build_pipeline import run_build_pipeline
from agents.revenue_tracker import run_revenue_tracker, revenue_embed
from agents.ai_chat import run_ai_chat_monitor, handle_chat_message, model_status_embed
from utils.claude import think, think_json, think_code
from agents.ai_chat import MODELS, get_available, pick, call_model, build_context, model_status_embed as _model_status_embed

logger = logging.getLogger("openclaw.bot"
CHANNEL_STRUCTURE = [
    ("opportunities",  "💡 Ranked opportunities — approve one to start building"),
    ("build-pipeline", "🏗️ Full build output — product files, listings, launch plans"),
    ("revenue",        "💰 Revenue tracking and reinvestment advice"),
    ("social-posts",   "📱 Pinterest pins, social content, newsletter drafts"),
    ("analytics",      "📊 Market intelligence and performance reports"),
    ("ai-chat",        "🤖 Chat with Claude, GPT-4o, Gemini, DeepSeek — all in one place"),
    ("commands",       "⚙️ Type your slash commands here"),
    ("logs",           "📋 System activity log"),
]

CATEGORY_NAME = "🦾 OPENCLAW HQ"


class OpenClawBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default(        intents.message_content = True
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents, help_command=None
        self.approved_opportunities: list[dict] = []
        self.built_opportunities: set[str] = set(        self.active_ventures: list[dict] = []
        self.revenue_log: dict[str, float] = {}
        self.channel_map: dict[str, discord.TextChannel] = {}
        self.ai_chat_channel_id: int = 0

    async def setup_hook(self):
        self.tree.copy_global_to(guild=discord.Object(id=settings.DISCORD_GUILD_ID)        await self.tree.sync(guild=discord.Object(id=settings.DISCORD_GUILD_ID)
    async def on_ready(self):
        logger.info(f"✅ OpenClaw online as {self.user}"        guild = self.get_guild(settings.DISCORD_GUILD_ID        if guild:
            await self._setup_channels(guild            await self._startup_message(            await self._start_agents(
    async def on_message(self, message: discord.Message):
        """Route messages in #ai-chat to the AI handler."""
        if message.author.bot:
            return
        if message.channel.id == self.ai_chat_channel_id:
            await handle_chat_message(message, self        await self.process_commands(message
    async def _setup_channels(self, guild: discord.Guild):
        category = discord.utils.get(guild.categories, name=CATEGORY_NAME        if not category:
            category = await guild.create_category(CATEGORY_NAME        for name, topic in CHANNEL_STRUCTURE:
            existing = discord.utils.get(guild.text_channels, name=name            ch = existing or await guild.create_text_channel(
                name=name, category=category, topic=topic
                        self.channel_map[name] = ch
            if name == "ai-chat":
                self.ai_chat_channel_id = ch.id
        logger.info(f"✅ {len(self.channel_map)} channels ready"
    async def _get(self, name: str):
        for k, ch in self.channel_map.items():
            if name in k:
                return ch
        return None

    async def _startup_message(self):
        ch = await self._get("logs"        if not ch:
            return
        available = get_available(        model_list = " • ".join([
            f"{MODELS[k]['emoji']} {MODELS[k]['name']}"
            for k in available if k in MODELS
        ]        embed = discord.Embed(
            title="🦾 OpenClaw Online",
            description=(
                f"**Goal:** ${settings.REVENUE_TARGET:,.0f} in {settings.TARGET_DAYS} days\n"
                f"**Budget:** ${settings.CAPITAL_BUDGET:.0f}\n\n"
                f"**AI Stack ({len(available)} models):**\n{model_list}\n\n"
                f"**Agents:** Opportunity Scanner • Build Pipeline • Revenue Tracker • AI Chat • Analytics • Newsletter • Pinterest\n\n"
                f"Type `/help` in #commands • Chat freely in #ai-chat"
            ),
            color=0x00f5a0,
            timestamp=datetime.utcnow(                await ch.send(embed=embed
    async def _start_agents(self):
        opp_ch   = await self._get("opportunities"        build_ch = await self._get("build-pipeline"        rev_ch   = await self._get("revenue"        chat_ch  = await self._get("ai-chat"
        analytics_ch = await self._get("analytics"        social_ch    = await self._get("social-posts"
        if opp_ch:
            asyncio.create_task(
                run_opportunity_scanner(self, opp_ch.id, settings.OPPORTUNITY_INTERVAL                    if build_ch:
            asyncio.create_task(run_build_pipeline(self, build_ch.id)        if rev_ch:
            asyncio.create_task(run_revenue_tracker(self, rev_ch.id)        if chat_ch:
            asyncio.create_task(run_ai_chat_monitor(self, chat_ch.id)        if analytics_ch:
            from agents.analytics import run_analytics_agent
            asyncio.create_task(run_analytics_agent(self, analytics_ch.id)        if social_ch:
            from ventures.pinterest_manager import run_pinterest_scheduler
            asyncio.create_task(run_pinterest_scheduler(self, social_ch.id)            from agents.newsletter import run_newsletter_agent
            asyncio.create_task(run_newsletter_agent(self, social_ch.id)
        logger.info("✅ All agents started"

def setup_commands(bot: OpenClawBot):

    # ── /help ─────────────────────────────────────────────────
    @bot.tree.command(name="help", description="Show all OpenClaw commands"    async def help_cmd(interaction: discord.Interaction):
        embed = discord.Embed(
            title="🦾 OpenClaw Commands",
            description=f"Goal: **${settings.REVENUE_TARGET:,.0f} in {settings.TARGET_DAYS} days**",
            color=0x00c8f0
                sections = {
            "🤖 AI Chat": [
                ("/ask [message]",          "Ask any model a question"),
                ("/ask @claude [message]",  "Force Claude specifically"),
                ("/ask @gpt4o [message]",   "Force GPT-4o"),
                ("/ask @gemini [message]",  "Force Gemini"),
                ("/ask @deepseek [message]","Force DeepSeek"),
                ("/models",                 "Show all AI model statuses"),
            ],
            "💼 Business": [
                ("/scan",                   "Find opportunities now"),
                ("/build [niche]",          "Full build pipeline"),
                ("/listing [product]",      "Generate Etsy listing"),
                ("/products [niche]",       "5-product store lineup"),
                ("/plan [niche]",           "30-day launch plan"),
            ],
            "💰 Revenue": [
                ("/revenue add [p] [amt]",  "Log a sale"),
                ("/revenue report",         "Full revenue dashboard"),
                ("/goal",                   "Progress to $500"),
                ("/status",                 "System status"),
            ],
            "🏪 Etsy": [
                ("/etsy setup",             "Setup instructions"),
                ("/etsy test",              "Test connection"),
                ("/etsy listings",          "View your listings"),
            ],
        }
        for section, cmds in sections.items():
            embed.add_field(
                name=section,
                value="\n".join([f"`{c}` — {d}" for c, d in cmds]),
                inline=False
                    await interaction.response.send_message(embed=embed
    # ── /ask ──────────────────────────────────────────────────
    @bot.tree.command(name="ask", description="Ask any AI model a question"    @app_commands.describe(
        message="Your question or request",
        model="Optional: claude | gpt4o | gemini | deepseek | glm (auto-picks if not set)"
        async def ask_cmd(interaction: discord.Interaction, message: str, model: str = ""):
        available = get_available(        if not available:
            await interaction.response.send_message(
                "❌ No AI models configured. Add at least ANTHROPIC_API_KEY to Railway variables."
                        return

        # Parse @model mentions from message
        force_model = model.lower().strip("@") if model else None
        clean_message = message

        # Also support @model in the message itself
        for key in MODELS.keys():
            if f"@{key}" in message.lower():
                force_model = key
                clean_message = message.lower().replace(f"@{key}", "").strip(                break

        # Validate model if forced
        if force_model and force_model not in MODELS:
            await interaction.response.send_message(
                f"❌ Unknown model `{force_model}`. Available: {', '.join(MODELS.keys())}"
                        return

        if force_model and force_model not in available:
            await interaction.response.send_message(
                f"⚠️ `{force_model}` not configured. Add its API key to Railway variables.\n"
                f"Available: {', '.join(available)}"
                        return

        await interaction.response.defer(
        context = {
            "revenue":  getattr(bot, 'revenue_log', {}),
            "ventures": getattr(bot, 'active_ventures', []),
            "target":   settings.REVENUE_TARGET,
            "days_left": settings.TARGET_DAYS,
        }

        try:
            model_key = force_model or pick(clean_message            available = get_available(            chain = [model_key] + [m for m in ["claude","gpt4o","deepseek","gemini","glm"] if m != model_key and m in available]
            system = build_context(bot            response = None
            used_model = model_key
            for key in chain:
                if key not in available: continue
                try:
                    response = await call_model(key, system, clean_message                    used_model = key
                    break
                except Exception: continue
            if not response:
                response = "❌ All models failed. Check API keys in Railway."
            used_info = MODELS.get(used_model, {"emoji": "❓", "name": "Unknown"}            chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
            for i, chunk in enumerate(chunks):
                suffix = f"\n\n{used_info['emoji']} *{used_info['name']}*" if i == 0 else ""
                await interaction.followup.send(chunk + suffix        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}"
    # ── /models ───────────────────────────────────────────────
    @bot.tree.command(name="models", description="Show status of all AI models"    async def models_cmd(interaction: discord.Interaction):
        await interaction.response.send_message(embed=_model_status_embed(bot)
    # ── /test ─────────────────────────────────────────────────
    @bot.tree.command(name="test", description="Test all API connections"    async def test_cmd(interaction: discord.Interaction):
        await interaction.response.defer(        embed = discord.Embed(
            title="🔌 API Connection Tests",
            color=0x00c8f0,
            timestamp=datetime.utcnow(        
        tests = [
            ("claude",   settings.ANTHROPIC_API_KEY,  "You are a test. Reply: CLAUDE_OK"),
            ("gpt4o",    settings.OPENAI_API_KEY,      "You are a test. Reply: GPT_OK"),
            ("gemini",   settings.GEMINI_API_KEY,      "Reply with: GEMINI_OK"),
            ("deepseek", settings.DEEPSEEK_API_KEY,    "You are a test. Reply: DEEPSEEK_OK"),
            ("glm",      settings.GLM_API_KEY,         "You are a test. Reply: GLM_OK"),
        ]

        for model_key, api_key, test_prompt in tests:
            model_info = MODELS[model_key]
            if not api_key:
                embed.add_field(
                    name=f"⏭️ {model_info['emoji']} {model_info['name']}",
                    value="No API key set",
                    inline=True
                                continue
            try:
                resp = await call_model(model_key, 'You are a test.', test_prompt                embed.add_field(
                    name=f"✅ {model_info['emoji']} {model_info['name']}",
                    value="Connected",
                    inline=True
                            except Exception as e:
                embed.add_field(
                    name=f"❌ {model_info['emoji']} {model_info['name']}",
                    value=f"`{str(e)[:80]}`",
                    inline=True
                
        embed.set_footer(text="OpenClaw AI Router"        await interaction.followup.send(embed=embed
    # ── /scan ─────────────────────────────────────────────────
    @bot.tree.command(name="scan", description="Scan for money-making opportunities now"    async def scan_cmd(interaction: discord.Interaction):
        await interaction.response.send_message(
            f"🔍 Scanning... (budget: **${settings.CAPITAL_BUDGET}**, "
            f"target: **${settings.REVENUE_TARGET} in {settings.TARGET_DAYS} days**)"
                ch = await bot._get("opportunities"        opps = await scan_for_opportunities(settings.CAPITAL_BUDGET        if opps and ch:
            await ch.send(f"**Manual scan — {datetime.now().strftime('%b %d %H:%M')}**"            for i, opp in enumerate(opps):
                view = OpportunityApproveView(opp, bot                await ch.send(embed=opportunity_embed(opp, i), view=view            await interaction.followup.send(
                f"✅ {len(opps)} opportunities posted to #opportunities"
                    else:
            await interaction.followup.send("⚠️ No opportunities found. Try again."
    # ── /build ────────────────────────────────────────────────
    @bot.tree.command(name="build", description="Run full build pipeline for a niche"    @app_commands.describe(niche="The niche to build (e.g. 'ADHD planner' or 'Gen Z finance tracker')"    async def build_cmd(interaction: discord.Interaction, niche: str):
        await interaction.response.send_message(
            f"🚀 Starting build pipeline for: **{niche}**\nWatch #build-pipeline for everything."
                if not hasattr(bot, 'approved_opportunities'):
            bot.approved_opportunities = []
        bot.approved_opportunities.append({
            'niche': niche, 'venture_type': 'digital_product'
        }
    # ── /listing ──────────────────────────────────────────────
    @bot.tree.command(name="listing", description="Generate a complete Etsy + Gumroad listing"    @app_commands.describe(product="Product name or description"    async def listing_cmd(interaction: discord.Interaction, product: str):
        await interaction.response.send_message(f"📝 Generating listing for: **{product}**..."        ch = await bot._get("build-pipeline"        research = await research_opportunity(product, settings.CAPITAL_BUDGET        if research:
            listing = await generate_listing_pack(research, {}            if listing and ch:
                embed = discord.Embed(title=f"🏪 Listing: {product}", color=0x00f5a0                title = listing.get('etsy_title', ''                if title:
                    embed.add_field(name="Etsy Title", value=f"```{title[:950]}```", inline=False                tags = listing.get('etsy_tags', []                if tags:
                    embed.add_field(name="Tags", value=", ".join(tags), inline=False                embed.add_field(name="Price", value=listing.get('etsy_price', '$9'), inline=True                await ch.send(embed=embed                desc = listing.get('etsy_description', ''                if desc:
                    await ch.send(f"**Description:**\n```{desc[:1900]}```"                await interaction.followup.send("✅ Listing posted to #build-pipeline"        else:
            await interaction.followup.send("⚠️ Failed. Try again."
    # ── /products ─────────────────────────────────────────────
    @bot.tree.command(name="products", description="Generate a 5-product store lineup"    @app_commands.describe(niche="Store niche"    async def products_cmd(interaction: discord.Interaction, niche: str):
        await interaction.response.send_message(f"🛒 Generating lineup for: **{niche}**..."        ch = await bot._get("build-pipeline"        products = await generate_product_batch(niche, count=5        if products and ch:
            embed = discord.Embed(
                title=f"🛒 Store Lineup: {niche}", color=0x00c8f0,
                timestamp=datetime.utcnow(                        for i, p in enumerate(products):
                embed.add_field(
                    name=f"#{i+1}: {p.get('name','Unknown')}",
                    value=(
                        f"{p.get('type','')} • {p.get('price','$9')}\n"
                        f"{p.get('one_line_description','')[:100]}\n"
                        f"🔍 `{p.get('primary_keyword','')}`"
                    ),
                    inline=False
                            await ch.send(embed=embed            await interaction.followup.send(f"✅ {len(products)} products posted to #build-pipeline"        else:
            await interaction.followup.send("⚠️ Failed. Try again."
    # ── /plan ─────────────────────────────────────────────────
    @bot.tree.command(name="plan", description="Generate your 30-day $500 launch plan"    @app_commands.describe(niche="Your niche"    async def plan_cmd(interaction: discord.Interaction, niche: str):
        await interaction.response.send_message(f"📅 Building 30-day plan for: **{niche}**..."        ch = await bot._get("build-pipeline"        plan = await generate_launch_strategy(niche, settings.CAPITAL_BUDGET        if plan and ch:
            embed = discord.Embed(
                title=f"📅 30-Day Plan: {niche}",
                description=plan.get('strategy_summary', '')[:4000],
                color=0xffc944, timestamp=datetime.utcnow(                        for wk, wn in [('week_1','Week 1'),('week_2','Week 2'),('week_3','Week 3'),('week_4','Week 4')]:
                w = plan.get(wk, {}                if w:
                    embed.add_field(
                        name=wn,
                        value=(
                            f"**{w.get('focus','')[:100]}**\n"
                            f"Listings: {w.get('listings_to_create',0)} | "
                            f"Rev: {w.get('expected_revenue','TBD')}"
                        ),
                        inline=True
                                await ch.send(embed=embed            await interaction.followup.send("✅ Plan posted to #build-pipeline"
    # ── /revenue ──────────────────────────────────────────────
    @bot.tree.command(name="revenue", description="Log a sale or view revenue report"    @app_commands.describe(action="add or report", product="Product name", amount="Amount in USD"    async def revenue_cmd(interaction: discord.Interaction,
                          action: str, product: str = "", amount: float = 0.0):
        if action == "add" and product and amount > 0:
            if product not in bot.revenue_log:
                bot.revenue_log[product] = 0.0
            bot.revenue_log[product] += amount
            total = sum(bot.revenue_log.values()            pct   = min(int((total / settings.REVENUE_TARGET) * 100), 100            embed = discord.Embed(
                title="💰 Sale Logged!",
                description=(
                    f"**+${amount:.2f}** from **{product}**\n"
                    f"Total: **${total:.2f}** / ${settings.REVENUE_TARGET:.0f} ({pct}%)"
                ),
                color=0x00f5a0
                        if total >= settings.REVENUE_TARGET:
                embed.add_field(
                    name="🎉 TARGET HIT!",
                    value=f"You hit ${settings.REVENUE_TARGET:.0f}! Time to scale.",
                    inline=False
                            await interaction.response.send_message(embed=embed            ch = await bot._get("revenue"            if ch:
                await ch.send(embed=revenue_embed(bot)        elif action == "report":
            await interaction.response.send_message(embed=revenue_embed(bot)        else:
            await interaction.response.send_message(
                "Usage:\n"
                "`/revenue add \"Product Name\" 9.00` — log a sale\n"
                "`/revenue report` — view dashboard"
            
    # ── /goal ─────────────────────────────────────────────────
    @bot.tree.command(name="goal", description="Show progress toward your $500 target"    async def goal_cmd(interaction: discord.Interaction):
        await interaction.response.send_message(embed=revenue_embed(bot)
    # ── /status ───────────────────────────────────────────────
    @bot.tree.command(name="status", description="Show system status"    async def status_cmd(interaction: discord.Interaction):
        total     = sum(bot.revenue_log.values()        available = get_available(        embed = discord.Embed(
            title="🦾 OpenClaw Status",
            color=0x00f5a0, timestamp=datetime.utcnow(                embed.add_field(name="🔍 Opportunity Scanner", value="🟢 Running", inline=True        embed.add_field(name="🏗️ Build Pipeline",      value="🟢 Running", inline=True        embed.add_field(name="💰 Revenue Tracker",     value="🟢 Running", inline=True        embed.add_field(name="🤖 AI Chat",             value="🟢 Running", inline=True        embed.add_field(
            name="AI Models",
            value=" • ".join([f"{MODELS[k]['emoji']}{k}" for k in available]),
            inline=False
                embed.add_field(name="Approved Niches", value=str(len(bot.approved_opportunities)), inline=True        embed.add_field(name="Built Ventures",  value=str(len(bot.built_opportunities)),   inline=True        embed.add_field(name="Revenue Earned",  value=f"${total:,.2f}",                   inline=True        if bot.active_ventures:
            embed.add_field(
                name="Active Ventures",
                value="\n".join([f"• {v.get('niche','Unknown')}" for v in bot.active_ventures]),
                inline=False
                    embed.set_footer(text=f"Goal: ${settings.REVENUE_TARGET:.0f} in {settings.TARGET_DAYS} days"        await interaction.response.send_message(embed=embed
    # ── /etsy ─────────────────────────────────────────────────
    @bot.tree.command(name="etsy", description="Etsy connection and listing management"    @app_commands.describe(action="setup | test | listings"    async def etsy_cmd(interaction: discord.Interaction, action: str = "test"):
        etsy = EtsyClient(        if action == "setup":
            await interaction.response.send_message(ETSY_SETUP_GUIDE        elif action == "test":
            if not etsy.is_configured():
                missing = ", ".join([
                    v for v, val in [
                        ("ETSY_API_KEY",      settings.ETSY_API_KEY),
                        ("ETSY_ACCESS_TOKEN", settings.ETSY_ACCESS_TOKEN),
                        ("ETSY_SHOP_ID",      settings.ETSY_SHOP_ID                    ] if not val
                ]                await interaction.response.send_message(
                    f"⚠️ Etsy not configured. Missing: {missing}\n"
                    f"Type `/etsy setup` for instructions."
                                return
            await interaction.response.send_message("🔍 Testing Etsy connection..."            try:
                shop = await etsy.get_shop(                if shop.get("shop_id"):
                    await interaction.followup.send(
                        f"✅ Etsy connected!\n"
                        f"Shop: **{shop.get('shop_name')}**\n"
                        f"Active listings: {shop.get('listing_active_count', 0)}"
                                    else:
                    await interaction.followup.send(f"❌ Connection failed: {shop}"            except Exception as e:
                await interaction.followup.send(f"❌ Error: {e}"        elif action == "listings":
            if not etsy.is_configured():
                await interaction.response.send_message("⚠️ Etsy not configured. Type `/etsy setup`."                return
            await interaction.response.send_message("📋 Fetching listings..."            try:
                drafts = await etsy.get_listings("draft"                active = await etsy.get_listings("active"                msg = (
                    f"**Etsy Shop**\n"
                    f"• Active: {len(active)}\n"
                    f"• Drafts: {len(drafts)}\n"
                                if drafts:
                    msg += "\n**Drafts:**\n" + "\n".join([
                        f"• {d.get('title','?')[:60]} (ID: {d.get('listing_id')})"
                        for d in drafts[:5]
                    ]                await interaction.followup.send(msg            except Exception as e:
                await interaction.followup.send(f"❌ Error: {e}"        else:
            await interaction.response.send_message(
                "Usage: `/etsy setup` | `/etsy test` | `/etsy listings`"
            

    # ── /gumroad ──────────────────────────────────────────────
    @bot.tree.command(name="gumroad", description="Gumroad connection and setup"    @app_commands.describe(action="setup | test | products"    async def gumroad_cmd(interaction: discord.Interaction, action: str = "test"):
        gr = GumroadClient(        if action == "setup":
            await interaction.response.send_message(GUMROAD_SETUP        elif action == "test":
            if not gr.is_configured():
                await interaction.response.send_message(
                    "⚠️ Add `GUMROAD_ACCESS_TOKEN` to Railway variables.\n"
                    "Type `/gumroad setup` for instructions."
                                return
            await interaction.response.send_message("🔍 Testing Gumroad connection..."            try:
                products = await gr.get_products(                await interaction.followup.send(
                    f"✅ Gumroad connected!\n"
                    f"Products: {len(products)} total"
                            except Exception as e:
                await interaction.followup.send(f"❌ Error: {e}"        elif action == "products":
            if not gr.is_configured():
                await interaction.response.send_message("⚠️ Gumroad not configured."                return
            await interaction.response.send_message("📦 Fetching Gumroad products..."            try:
                products = await gr.get_products(                if products:
                    lines = [f"• {p.get('name','?')[:60]} — ${p.get('price',0)/100:.2f} — {'Published' if p.get('published') else 'Draft'}" for p in products[:8]]
                    await interaction.followup.send("**Your Gumroad Products:**\n" + "\n".join(lines)                else:
                    await interaction.followup.send("No products yet. Run `/build` to create your first one."            except Exception as e:
                await interaction.followup.send(f"❌ Error: {e}"
    # ── /pinterest ────────────────────────────────────────────
    @bot.tree.command(name="pinterest", description="Pinterest auto-posting setup and control"    @app_commands.describe(action="setup | test | pin"    async def pinterest_cmd(interaction: discord.Interaction, action: str = "test"):
        pt = PinterestClient(        if action == "setup":
            await interaction.response.send_message(PINTEREST_SETUP        elif action == "test":
            if not pt.is_configured():
                await interaction.response.send_message(
                    "⚠️ Pinterest not configured.\n"
                    "Missing: " + (", ".join([
                        v for v, val in [
                            ("PINTEREST_ACCESS_TOKEN", settings.PINTEREST_ACCESS_TOKEN),
                            ("PINTEREST_BOARD_ID",     settings.PINTEREST_BOARD_ID                        ] if not val
                    ])) + "\nType `/pinterest setup` for instructions."
                                return
            await interaction.response.send_message("🔍 Testing Pinterest connection..."            try:
                boards = await pt.get_boards(                await interaction.followup.send(
                    f"✅ Pinterest connected!\n"
                    f"Boards: {len(boards)}\n"
                    f"Active board ID: `{settings.PINTEREST_BOARD_ID}`"
                            except Exception as e:
                await interaction.followup.send(f"❌ Error: {e}"
    # ── /analytics ────────────────────────────────────────────
    @bot.tree.command(name="analytics", description="Market intelligence and performance analysis"    @app_commands.describe(niche="Niche to analyze (leave blank for your store performance)"    async def analytics_cmd(interaction: discord.Interaction, niche: str = ""):
        await interaction.response.defer(        ch = await bot._get("analytics"
        if niche:
            await interaction.followup.send(f"🔍 Analyzing market for: **{niche}**..."            analysis = await analyze_etsy_market(niche            if analysis:
                embed = analytics_embed(analysis, f"🔍 Market Intel: {niche[:50]}"                if ch:
                    await ch.send(embed=embed                await interaction.followup.send(embed=embed            else:
                await interaction.followup.send("⚠️ Analysis failed. Try again."        else:
            revenue  = getattr(bot, 'revenue_log', {}            ventures = getattr(bot, 'active_ventures', []            analysis = await analyze_own_performance(revenue, ventures            embed = analytics_embed(analysis, "📊 Your Store Performance"            if ch:
                await ch.send(embed=embed            await interaction.followup.send(embed=embed
    # ── /newsletter ───────────────────────────────────────────
    @bot.tree.command(name="newsletter", description="Newsletter and email capture management"    @app_commands.describe(action="setup | leadmagnet | issue"    async def newsletter_cmd(interaction: discord.Interaction, action: str = "setup", niche: str = ""):
        if action == "setup":
            await interaction.response.send_message(NEWSLETTER_SETUP        elif action == "leadmagnet":
            target_niche = niche or (bot.active_ventures[0].get('niche') if bot.active_ventures else "digital products"            await interaction.response.send_message(f"🧲 Generating lead magnet for: **{target_niche}**..."            ch = await bot._get("social-posts"            lm = await generate_lead_magnet(target_niche, target_niche + " template"            if lm:
                embed = lead_magnet_embed(lm, target_niche                if ch:
                    await ch.send(embed=embed                await interaction.followup.send(embed=embed        else:
            await interaction.response.send_message(
                "Usage:\n"
                "`/newsletter setup` — Beehiiv setup guide\n"
                "`/newsletter leadmagnet` — generate email capture freebie\n"
                "`/newsletter issue` — generate next newsletter issue"
            

def create_bot() -> OpenClawBot:
    bot = OpenClawBot(    setup_commands(bot    return bot
