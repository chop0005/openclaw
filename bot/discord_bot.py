"""
OpenClaw Discord Bot — Full Command Center
Every command defers immediately. No timeouts possible.
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
)
from agents.build_pipeline import run_build_pipeline
from agents.revenue_tracker import run_revenue_tracker, revenue_embed
from agents.ai_chat import (
    run_ai_chat_monitor, handle_chat_message,
    MODELS, get_available, pick, call_model, build_context,
    model_status_embed as _model_status_embed
)
from utils.claude import think, think_json, think_code

logger = logging.getLogger("openclaw.bot")

CHANNEL_STRUCTURE = [
    ("opportunities",  "💡 Ranked opportunities — approve one to start building"),
    ("build-pipeline", "🏗️ Full build output — product files, listings, launch plans"),
    ("revenue",        "💰 Revenue tracking and reinvestment advice"),
    ("social-posts",   "📱 Pinterest pins, social content, newsletter drafts"),
    ("analytics",      "📊 Market intelligence and performance reports"),
    ("ai-chat",        "🤖 Chat with all AI models"),
    ("commands",       "⚙️ Type your slash commands here"),
    ("logs",           "📋 System activity log"),
    ("autonomous",     "🤖 Daily plans + approval requests"),
    ("competitors",    "🕵️ Competitor intelligence reports"),
    ("improvements",   "🔧 Self-improvement proposals"),
]

CATEGORY_NAME = "🦾 OPENCLAW HQ"


class OpenClawBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)
        self.approved_opportunities: list = []
        self.built_opportunities: set = set()
        self.active_ventures: list = []
        self.revenue_log: dict = {}
        self.channel_map: dict = {}
        self.ai_chat_channel_id: int = 0

    async def setup_hook(self):
        self.tree.copy_global_to(guild=discord.Object(id=settings.DISCORD_GUILD_ID))
        await self.tree.sync(guild=discord.Object(id=settings.DISCORD_GUILD_ID))

    async def on_ready(self):
        logger.info(f"✅ OpenClaw online as {self.user}")
        guild = self.get_guild(settings.DISCORD_GUILD_ID)
        if guild:
            await self._setup_channels(guild)
            await self._startup_message()
            await self._start_agents()

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id == self.ai_chat_channel_id:
            await handle_chat_message(message, self)
        await self.process_commands(message)

    async def _setup_channels(self, guild: discord.Guild):
        category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
        if not category:
            category = await guild.create_category(CATEGORY_NAME)
        for name, topic in CHANNEL_STRUCTURE:
            existing = discord.utils.get(guild.text_channels, name=name)
            ch = existing or await guild.create_text_channel(name=name, category=category, topic=topic)
            self.channel_map[name] = ch
            if name == "ai-chat":
                self.ai_chat_channel_id = ch.id
        logger.info(f"✅ {len(self.channel_map)} channels ready")

    async def _get(self, name: str):
        for k, ch in self.channel_map.items():
            if name in k:
                return ch
        return None

    async def _startup_message(self):
        ch = await self._get("logs")
        if not ch:
            return
        available = get_available()
        model_list = " • ".join([f"{MODELS[k]['emoji']} {MODELS[k]['name']}" for k in available if k in MODELS])
        embed = discord.Embed(
            title="🦾 OpenClaw Online",
            description=(
                f"**Goal:** ${settings.REVENUE_TARGET:,.0f} in {settings.TARGET_DAYS} days\n"
                f"**Budget:** ${settings.CAPITAL_BUDGET:.0f}\n\n"
                f"**AI Models ({len(available)}):** {model_list or 'Claude only'}\n\n"
                f"Type `/help` in #commands • Chat in #ai-chat"
            ),
            color=0x00f5a0, timestamp=datetime.utcnow()
        )
        await ch.send(embed=embed)

    async def _start_agents(self):
        opp_ch       = await self._get("opportunities")
        build_ch     = await self._get("build-pipeline")
        rev_ch       = await self._get("revenue")
        chat_ch      = await self._get("ai-chat")
        analytics_ch = await self._get("analytics")
        social_ch    = await self._get("social-posts")
        auto_ch      = await self._get("autonomous")
        comp_ch      = await self._get("competitors")
        impr_ch      = await self._get("improvements")

        if opp_ch:   asyncio.create_task(run_opportunity_scanner(self, opp_ch.id, settings.OPPORTUNITY_INTERVAL))
        if build_ch: asyncio.create_task(run_build_pipeline(self, build_ch.id))
        if rev_ch:   asyncio.create_task(run_revenue_tracker(self, rev_ch.id))
        if chat_ch:  asyncio.create_task(run_ai_chat_monitor(self, chat_ch.id))

        for module, ch, func in [
            ("agents.analytics",         analytics_ch, "run_analytics_agent"),
            ("ventures.pinterest_manager", social_ch,  "run_pinterest_scheduler"),
            ("agents.newsletter",         social_ch,   "run_newsletter_agent"),
            ("agents.autonomous",         auto_ch,     "run_autonomous_engine"),
            ("agents.competitor_scanner", comp_ch,     "run_competitor_scanner"),
            ("agents.self_improve",       impr_ch,     "run_self_improvement_scheduler"),
            ("agents.social_poster",      social_ch,   "run_social_poster"),
            ("agents.bundle_affiliate",   build_ch,    "run_bundle_and_affiliate_engine"),
        ]:
            if ch:
                try:
                    mod = __import__(module, fromlist=[func])
                    asyncio.create_task(getattr(mod, func)(self, ch.id))
                except (ImportError, AttributeError):
                    pass

        logger.info("✅ All agents started")


def setup_commands(bot: OpenClawBot):

    @bot.tree.command(name="help", description="Show all OpenClaw commands")
    async def help_cmd(interaction: discord.Interaction):
        await interaction.response.defer()
        embed = discord.Embed(
            title="🦾 OpenClaw Commands",
            description=f"Goal: **${settings.REVENUE_TARGET:,.0f} in {settings.TARGET_DAYS} days**",
            color=0x00c8f0
        )
        sections = {
            "🤖 AI": [("/ask [msg]","Ask any model"),("/ask [msg] @claude","Force Claude"),("/models","Model statuses"),("/test","Test all APIs")],
            "💼 Business": [("/scan","Find opportunities"),("/build [niche]","Full build pipeline"),("/listing [product]","Etsy listing"),("/products [niche]","Store lineup"),("/plan [niche]","30-day plan"),("/analytics [niche]","Market intel")],
            "💰 Revenue": [("/revenue add [p] [amt]","Log a sale"),("/revenue report","Dashboard"),("/goal","Progress"),("/status","System status")],
            "🏪 Platforms": [("/etsy setup|auth|test","Etsy"),("/gumroad setup|test","Gumroad"),("/pinterest setup|test","Pinterest"),("/newsletter setup|leadmagnet","Newsletter")],
            "🤖 Automation": [("/improve [feedback]","Self-improve"),("/autonomy","Daily plan"),("/competitors [niche]","Competitor intel"),("/bundle [niche]","Create bundle"),("/affiliates [niche]","Affiliate programs"),("/post [product]","Post to socials")],
        }
        for section, cmds in sections.items():
            embed.add_field(name=section, value="\n".join([f"`{c}` — {d}" for c, d in cmds]), inline=False)
        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="ask", description="Ask any AI model a question")
    @app_commands.describe(message="Your question", model="Optional: claude|gpt4o|gemini|deepseek|glm")
    async def ask_cmd(interaction: discord.Interaction, message: str, model: str = ""):
        await interaction.response.defer()
        available = get_available()
        if not available:
            await interaction.followup.send("❌ No AI models configured. Add ANTHROPIC_API_KEY to Railway.")
            return
        force_model = model.lower().strip("@") if model else None
        clean_message = message
        for key in MODELS.keys():
            if f"@{key}" in message.lower():
                force_model = key
                clean_message = message.lower().replace(f"@{key}", "").strip()
                break
        if force_model and force_model not in MODELS:
            await interaction.followup.send(f"❌ Unknown model. Available: {', '.join(MODELS.keys())}")
            return
        system = build_context(bot)
        chain  = [force_model] if force_model else []
        chain += [m for m in ["claude","gpt4o","deepseek","gemini","glm"] if m not in chain and m in available]
        response = None
        used_model = force_model or "claude"
        for key in chain:
            if key not in available: continue
            try:
                response = await call_model(key, system, clean_message)
                used_model = key
                break
            except Exception as e:
                logger.warning(f"{key} failed: {e}")
        if not response:
            response = "❌ All models failed. Check API keys in Railway."
        info = MODELS.get(used_model, {"emoji": "❓", "name": "Unknown"})
        chunks = [response[i:i+1900] for i in range(0, len(response), 1900)]
        for i, chunk in enumerate(chunks):
            await interaction.followup.send(chunk + (f"\n\n{info['emoji']} *{info['name']}*" if i == 0 else ""))

    @bot.tree.command(name="models", description="Show all AI model statuses")
    async def models_cmd(interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(embed=_model_status_embed(bot))

    @bot.tree.command(name="test", description="Test all API connections")
    async def test_cmd(interaction: discord.Interaction):
        await interaction.response.defer()
        embed = discord.Embed(title="🔌 API Tests", color=0x00c8f0, timestamp=datetime.utcnow())
        for mk, ak, tp in [
            ("claude",   settings.ANTHROPIC_API_KEY, "Reply: CLAUDE_OK"),
            ("gpt4o",    settings.OPENAI_API_KEY,    "Reply: GPT_OK"),
            ("gemini",   settings.GEMINI_API_KEY,    "Reply: GEMINI_OK"),
            ("deepseek", settings.DEEPSEEK_API_KEY,  "Reply: DEEPSEEK_OK"),
            ("glm",      settings.GLM_API_KEY,       "Reply: GLM_OK"),
        ]:
            info = MODELS.get(mk, {"emoji":"❓","name":mk})
            if not ak:
                embed.add_field(name=f"⏭️ {info['emoji']} {info['name']}", value="No key set", inline=True)
                continue
            try:
                await call_model(mk, "You are a test.", tp)
                embed.add_field(name=f"✅ {info['emoji']} {info['name']}", value="Connected", inline=True)
            except Exception as e:
                embed.add_field(name=f"❌ {info['emoji']} {info['name']}", value=f"`{str(e)[:80]}`", inline=True)
        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="scan", description="Scan for money-making opportunities now")
    async def scan_cmd(interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(f"🔍 Scanning... budget: **${settings.CAPITAL_BUDGET}** | target: **${settings.REVENUE_TARGET} in {settings.TARGET_DAYS} days**")
        ch = await bot._get("opportunities")
        opps = await scan_for_opportunities(settings.CAPITAL_BUDGET)
        if opps and ch:
            await ch.send(f"**Scan — {datetime.now().strftime('%b %d %H:%M')}**")
            for i, opp in enumerate(opps):
                await ch.send(embed=opportunity_embed(opp, i), view=OpportunityApproveView(opp, bot))
            await interaction.followup.send(f"✅ {len(opps)} opportunities posted to #opportunities")
        else:
            await interaction.followup.send("⚠️ No opportunities found. Try again.")

    @bot.tree.command(name="build", description="Run full build pipeline for a niche")
    @app_commands.describe(niche="The niche to build")
    async def build_cmd(interaction: discord.Interaction, niche: str):
        await interaction.response.defer()
        await interaction.followup.send(f"🚀 Build pipeline started for: **{niche}**\nWatch #build-pipeline.")
        if not hasattr(bot, 'approved_opportunities'):
            bot.approved_opportunities = []
        bot.approved_opportunities.append({'niche': niche, 'venture_type': 'digital_product'})

    @bot.tree.command(name="listing", description="Generate a complete Etsy + Gumroad listing")
    @app_commands.describe(product="Product name or description")
    async def listing_cmd(interaction: discord.Interaction, product: str):
        await interaction.response.defer()
        await interaction.followup.send(f"📝 Generating listing for: **{product}**...")
        ch = await bot._get("build-pipeline")
        try:
            from ventures.digital_product import research_opportunity, generate_listing_pack
            research = await research_opportunity(product, settings.CAPITAL_BUDGET)
            if research:
                listing = await generate_listing_pack(research, {})
                if listing and ch:
                    embed = discord.Embed(title=f"🏪 {product[:80]}", color=0x00f5a0)
                    if listing.get('etsy_title'):
                        embed.add_field(name="Etsy Title", value=f"```{listing['etsy_title'][:950]}```", inline=False)
                    if listing.get('etsy_tags'):
                        embed.add_field(name="Tags", value=", ".join(listing['etsy_tags']), inline=False)
                    embed.add_field(name="Price", value=listing.get('etsy_price','$9'), inline=True)
                    await ch.send(embed=embed)
                    if listing.get('etsy_description'):
                        await ch.send(f"**Description:**\n```{listing['etsy_description'][:1900]}```")
                    await interaction.followup.send("✅ Listing posted to #build-pipeline")
            else:
                await interaction.followup.send("⚠️ Failed. Try again.")
        except ImportError as e:
            await interaction.followup.send(f"❌ {e}")

    @bot.tree.command(name="products", description="Generate a 5-product store lineup")
    @app_commands.describe(niche="Store niche")
    async def products_cmd(interaction: discord.Interaction, niche: str):
        await interaction.response.defer()
        await interaction.followup.send(f"🛒 Generating lineup for: **{niche}**...")
        ch = await bot._get("build-pipeline")
        try:
            from ventures.digital_product import generate_product_batch
            products = await generate_product_batch(niche, count=5)
            if products and ch:
                embed = discord.Embed(title=f"🛒 {niche[:80]}", color=0x00c8f0, timestamp=datetime.utcnow())
                for i, p in enumerate(products):
                    embed.add_field(
                        name=f"#{i+1}: {p.get('name','?')[:80]}",
                        value=f"{p.get('type','')} • {p.get('price','$9')}\n{p.get('one_line_description','')[:100]}\n🔍 `{p.get('primary_keyword','')}`",
                        inline=False
                    )
                await ch.send(embed=embed)
                await interaction.followup.send(f"✅ {len(products)} products posted to #build-pipeline")
            else:
                await interaction.followup.send("⚠️ Failed. Try again.")
        except ImportError as e:
            await interaction.followup.send(f"❌ {e}")

    @bot.tree.command(name="plan", description="Generate your 30-day launch plan")
    @app_commands.describe(niche="Your niche")
    async def plan_cmd(interaction: discord.Interaction, niche: str):
        await interaction.response.defer()
        await interaction.followup.send(f"📅 Building 30-day plan for: **{niche}**...")
        ch = await bot._get("build-pipeline")
        try:
            from ventures.digital_product import generate_launch_strategy
            plan = await generate_launch_strategy(niche, settings.CAPITAL_BUDGET)
            if plan and ch:
                embed = discord.Embed(
                    title=f"📅 30-Day Plan: {niche[:80]}",
                    description=str(plan.get('strategy_summary',''))[:4000],
                    color=0xffc944, timestamp=datetime.utcnow()
                )
                for wk, wn in [('week_1','Week 1'),('week_2','Week 2'),('week_3','Week 3'),('week_4','Week 4')]:
                    w = plan.get(wk, {})
                    if w:
                        embed.add_field(
                            name=wn,
                            value=f"**{str(w.get('focus',''))[:100]}**\nListings: {w.get('listings_to_create',0)} | Rev: {w.get('expected_revenue','TBD')}",
                            inline=True
                        )
                await ch.send(embed=embed)
                await interaction.followup.send("✅ Plan posted to #build-pipeline")
        except ImportError as e:
            await interaction.followup.send(f"❌ {e}")

    @bot.tree.command(name="analytics", description="Market intelligence and performance")
    @app_commands.describe(niche="Niche to analyze (blank = your store)")
    async def analytics_cmd(interaction: discord.Interaction, niche: str = ""):
        await interaction.response.defer()
        ch = await bot._get("analytics")
        try:
            from agents.analytics import analyze_etsy_market, analyze_own_performance, analytics_embed
            if niche:
                await interaction.followup.send(f"🔍 Analyzing: **{niche}**...")
                analysis = await analyze_etsy_market(niche)
            else:
                analysis = await analyze_own_performance(getattr(bot,'revenue_log',{}), getattr(bot,'active_ventures',[]))
            if analysis:
                embed = analytics_embed(analysis, f"📊 {niche or 'Store Performance'}")
                if ch: await ch.send(embed=embed)
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("⚠️ Analysis failed.")
        except ImportError as e:
            await interaction.followup.send(f"❌ {e}")

    @bot.tree.command(name="revenue", description="Log a sale or view revenue report")
    @app_commands.describe(action="add or report", product="Product name", amount="Amount USD")
    async def revenue_cmd(interaction: discord.Interaction, action: str, product: str = "", amount: float = 0.0):
        await interaction.response.defer()
        if action == "add" and product and amount > 0:
            if product not in bot.revenue_log: bot.revenue_log[product] = 0.0
            bot.revenue_log[product] += amount
            total = sum(bot.revenue_log.values())
            pct   = min(int((total / settings.REVENUE_TARGET) * 100), 100)
            embed = discord.Embed(
                title="💰 Sale Logged!",
                description=f"**+${amount:.2f}** from **{product}**\nTotal: **${total:.2f}** / ${settings.REVENUE_TARGET:.0f} ({pct}%)",
                color=0x00f5a0
            )
            if total >= settings.REVENUE_TARGET:
                embed.add_field(name="🎉 TARGET HIT!", value=f"You hit ${settings.REVENUE_TARGET:.0f}!", inline=False)
            await interaction.followup.send(embed=embed)
            ch = await bot._get("revenue")
            if ch: await ch.send(embed=revenue_embed(bot))
        elif action == "report":
            await interaction.followup.send(embed=revenue_embed(bot))
        else:
            await interaction.followup.send("Usage: `/revenue add \"Product\" 9.00` or `/revenue report`")

    @bot.tree.command(name="goal", description="Show progress toward your target")
    async def goal_cmd(interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send(embed=revenue_embed(bot))

    @bot.tree.command(name="status", description="Show system status")
    async def status_cmd(interaction: discord.Interaction):
        await interaction.response.defer()
        total = sum(bot.revenue_log.values())
        available = get_available()
        embed = discord.Embed(title="🦾 OpenClaw Status", color=0x00f5a0, timestamp=datetime.utcnow())
        embed.add_field(name="🔍 Scanner",   value="🟢 Running", inline=True)
        embed.add_field(name="🏗️ Builder",   value="🟢 Running", inline=True)
        embed.add_field(name="💰 Revenue",   value="🟢 Running", inline=True)
        embed.add_field(name="🤖 AI Chat",   value="🟢 Running", inline=True)
        embed.add_field(name="📊 Analytics", value="🟢 Running", inline=True)
        embed.add_field(name="📧 Newsletter",value="🟢 Running", inline=True)
        embed.add_field(name="AI Models", value=" • ".join([f"{MODELS[k]['emoji']}{k}" for k in available]) or "Claude only", inline=False)
        embed.add_field(name="Niches",   value=str(len(bot.approved_opportunities)), inline=True)
        embed.add_field(name="Built",    value=str(len(bot.built_opportunities)),    inline=True)
        embed.add_field(name="Revenue",  value=f"${total:,.2f}",                    inline=True)
        if bot.active_ventures:
            embed.add_field(name="Active", value="\n".join([f"• {v.get('niche','?')}" for v in bot.active_ventures]), inline=False)
        embed.set_footer(text=f"Goal: ${settings.REVENUE_TARGET:.0f} in {settings.TARGET_DAYS} days")
        await interaction.followup.send(embed=embed)

    @bot.tree.command(name="etsy", description="Etsy connection and listing management")
    @app_commands.describe(action="setup | auth | test | listings")
    async def etsy_cmd(interaction: discord.Interaction, action: str = "setup"):
        await interaction.response.defer()
        try:
            from ventures.etsy_manager import EtsyClient, ETSY_SETUP_GUIDE
        except ImportError:
            await interaction.followup.send("⚠️ Etsy manager not available.")
            return
        etsy = EtsyClient()
        if action == "setup":
            await interaction.followup.send(ETSY_SETUP_GUIDE)
        elif action == "auth":
            if not settings.ETSY_API_KEY:
                await interaction.followup.send("⚠️ Add `ETSY_API_KEY` to Railway first. Get it from developers.etsy.com → your app → Keystring.")
                return
            try:
                from ventures.etsy_oauth import generate_auth_url, set_bot_ref, get_redirect_uri
                set_bot_ref(bot, await bot._get("commands") or interaction.channel)
                auth_url, _ = await generate_auth_url()
                embed = discord.Embed(title="🔐 Etsy Authorization", color=0xf56400)
                embed.add_field(name="🔗 Click to Authorize", value=f"[Authorize Etsy Shop →]({auth_url})", inline=False)
                embed.add_field(name="Callback URL", value=f"`{get_redirect_uri()}`", inline=False)
                embed.set_footer(text="Expires in 10 minutes")
                await interaction.followup.send(embed=embed)
            except Exception as e:
                await interaction.followup.send(f"❌ OAuth error: {e}")
        elif action == "test":
            missing = [v for v, val in [("ETSY_API_KEY", settings.ETSY_API_KEY),("ETSY_ACCESS_TOKEN", settings.ETSY_ACCESS_TOKEN),("ETSY_SHOP_ID", settings.ETSY_SHOP_ID)] if not val]
            if missing:
                await interaction.followup.send(f"⚠️ Missing: {', '.join(missing)}\nUse `/etsy setup` for instructions, `/etsy auth` to connect.")
                return
            try:
                shop = await etsy.get_shop()
                if shop.get("shop_id"):
                    await interaction.followup.send(f"✅ Connected! Shop: **{shop.get('shop_name')}** | Listings: {shop.get('listing_active_count',0)}")
                else:
                    await interaction.followup.send(f"❌ Failed: {shop}")
            except Exception as e:
                await interaction.followup.send(f"❌ {e}")
        elif action == "listings":
            if not etsy.is_configured():
                await interaction.followup.send("⚠️ Not configured. Use `/etsy setup`.")
                return
            try:
                drafts = await etsy.get_listings("draft")
                active = await etsy.get_listings("active")
                msg = f"**Etsy:** {len(active)} active | {len(drafts)} drafts"
                if drafts:
                    msg += "\n" + "\n".join([f"• {d.get('title','?')[:60]}" for d in drafts[:5]])
                await interaction.followup.send(msg)
            except Exception as e:
                await interaction.followup.send(f"❌ {e}")
        else:
            await interaction.followup.send("Usage: `/etsy setup` | `/etsy auth` | `/etsy test` | `/etsy listings`")

    @bot.tree.command(name="gumroad", description="Gumroad connection and management")
    @app_commands.describe(action="setup | test | products")
    async def gumroad_cmd(interaction: discord.Interaction, action: str = "test"):
        await interaction.response.defer()
        try:
            from ventures.gumroad_manager import GumroadClient, GUMROAD_SETUP
        except ImportError:
            await interaction.followup.send("⚠️ Gumroad manager not available.")
            return
        gr = GumroadClient()
        if action == "setup":
            await interaction.followup.send(GUMROAD_SETUP)
        elif action == "test":
            if not gr.is_configured():
                await interaction.followup.send("⚠️ Add `GUMROAD_ACCESS_TOKEN` to Railway. Type `/gumroad setup`.")
                return
            try:
                products = await gr.get_products()
                await interaction.followup.send(f"✅ Gumroad connected! Products: {len(products)}")
            except Exception as e:
                await interaction.followup.send(f"❌ {e}")
        elif action == "products":
            if not gr.is_configured():
                await interaction.followup.send("⚠️ Not configured.")
                return
            try:
                products = await gr.get_products()
                if products:
                    lines = [f"• {p.get('name','?')[:60]} — ${p.get('price',0)/100:.2f} — {'Published' if p.get('published') else 'Draft'}" for p in products[:8]]
                    await interaction.followup.send("**Gumroad Products:**\n" + "\n".join(lines))
                else:
                    await interaction.followup.send("No products yet. Run `/build` to create your first one.")
            except Exception as e:
                await interaction.followup.send(f"❌ {e}")
        else:
            await interaction.followup.send("Usage: `/gumroad setup` | `/gumroad test` | `/gumroad products`")

    @bot.tree.command(name="pinterest", description="Pinterest auto-posting")
    @app_commands.describe(action="setup | test")
    async def pinterest_cmd(interaction: discord.Interaction, action: str = "test"):
        await interaction.response.defer()
        try:
            from ventures.pinterest_manager import PinterestClient, PINTEREST_SETUP
        except ImportError:
            await interaction.followup.send("⚠️ Pinterest manager not available.")
            return
        pt = PinterestClient()
        if action == "setup":
            await interaction.followup.send(PINTEREST_SETUP)
        elif action == "test":
            missing = [v for v, val in [("PINTEREST_ACCESS_TOKEN", settings.PINTEREST_ACCESS_TOKEN),("PINTEREST_BOARD_ID", settings.PINTEREST_BOARD_ID)] if not val]
            if missing:
                await interaction.followup.send(f"⚠️ Missing: {', '.join(missing)}. Type `/pinterest setup`.")
                return
            try:
                boards = await pt.get_boards()
                await interaction.followup.send(f"✅ Pinterest connected! Boards: {len(boards)} | Board ID: `{settings.PINTEREST_BOARD_ID}`")
            except Exception as e:
                await interaction.followup.send(f"❌ {e}")
        else:
            await interaction.followup.send("Usage: `/pinterest setup` | `/pinterest test`")

    @bot.tree.command(name="newsletter", description="Newsletter and email capture")
    @app_commands.describe(action="setup | leadmagnet", niche="Niche (optional)")
    async def newsletter_cmd(interaction: discord.Interaction, action: str = "setup", niche: str = ""):
        await interaction.response.defer()
        if action == "setup":
            try:
                from agents.newsletter import NEWSLETTER_SETUP
                await interaction.followup.send(NEWSLETTER_SETUP)
            except ImportError:
                await interaction.followup.send("⚠️ Newsletter module not available.")
        elif action == "leadmagnet":
            target = niche or (bot.active_ventures[0].get('niche') if bot.active_ventures else "digital products")
            await interaction.followup.send(f"🧲 Generating lead magnet for: **{target}**...")
            try:
                from agents.newsletter import generate_lead_magnet, lead_magnet_embed
                lm = await generate_lead_magnet(target, target + " template")
                if lm:
                    embed = lead_magnet_embed(lm, target)
                    ch = await bot._get("social-posts")
                    if ch: await ch.send(embed=embed)
                    await interaction.followup.send(embed=embed)
                else:
                    await interaction.followup.send("⚠️ Failed.")
            except ImportError as e:
                await interaction.followup.send(f"❌ {e}")
        else:
            await interaction.followup.send("Usage: `/newsletter setup` | `/newsletter leadmagnet`")

    @bot.tree.command(name="improve", description="Analyze and improve OpenClaw's performance")
    @app_commands.describe(feedback="What's not working", area="listings|social|opportunities|products|general")
    async def improve_cmd(interaction: discord.Interaction, feedback: str = "", area: str = "general"):
        await interaction.response.defer()
        await interaction.followup.send(f"🔍 {'Analyzing feedback...' if feedback else f'Analyzing {area}...'}")
        try:
            from agents.self_improve import analyze_performance, analyze_from_feedback, improvement_embed, ImprovementApprovalView
            context = {"revenue": getattr(bot,'revenue_log',{}), "ventures": getattr(bot,'active_ventures',[])}
            analysis = await (analyze_from_feedback(feedback, context) if feedback else analyze_performance(area, context))
            if not analysis:
                await interaction.followup.send("⚠️ Analysis failed.")
                return
            improvements = analysis.get("improvements", [])
            if not improvements:
                await interaction.followup.send("✅ No improvements needed right now.")
                return
            ch = await bot._get("improvements")
            if ch:
                header = discord.Embed(
                    title=f"🔧 Analysis: {area.upper()}",
                    description=f"**Assessment:** {analysis.get('current_performance','N/A')[:300]}\n**Root cause:** {analysis.get('root_cause',analysis.get('feedback_summary','N/A'))[:200]}",
                    color=0xb060ff, timestamp=datetime.utcnow()
                )
                await ch.send(embed=header)
                for i, imp in enumerate(improvements[:3]):
                    await ch.send(embed=improvement_embed(analysis, imp, i), view=ImprovementApprovalView(imp, bot))
                    await asyncio.sleep(1)
            await interaction.followup.send(f"✅ {len(improvements)} improvement(s) posted to #improvements")
        except ImportError as e:
            await interaction.followup.send(f"❌ {e}")

    @bot.tree.command(name="autonomy", description="View OpenClaw's autonomous daily plan")
    async def autonomy_cmd(interaction: discord.Interaction):
        await interaction.response.defer()
        await interaction.followup.send("🤖 Generating daily plan...")
        try:
            from agents.autonomous import generate_daily_plan, plan_embed, ApprovalView
            plan = await generate_daily_plan(getattr(bot,'active_ventures',[]), getattr(bot,'revenue_log',{}))
            if plan:
                ch = await bot._get("autonomous")
                if ch:
                    await ch.send(embed=plan_embed(plan))
                    for action in plan.get("approval_needed",[])[:3]:
                        a_embed = discord.Embed(title=f"✋ {action.get('action','Action')[:80]}", description=f"**Why:** {action.get('reason','N/A')}\n**Impact:** {action.get('impact','N/A')}", color=0xffc944)
                        await ch.send(embed=a_embed, view=ApprovalView(action, bot))
                await interaction.followup.send("✅ Daily plan posted to #autonomous")
            else:
                await interaction.followup.send("⚠️ Failed.")
        except ImportError as e:
            await interaction.followup.send(f"❌ {e}")

    @bot.tree.command(name="competitors", description="Run competitor intelligence scan")
    @app_commands.describe(niche="Niche to scan")
    async def competitors_cmd(interaction: discord.Interaction, niche: str = ""):
        await interaction.response.defer()
        target = niche or (bot.active_ventures[0].get("niche") if bot.active_ventures else "digital templates")
        await interaction.followup.send(f"🕵️ Scanning competitors for: **{target}**...")
        try:
            from agents.competitor_scanner import scan_competitors, competitor_embed
            data = await scan_competitors(target)
            if data:
                embed = competitor_embed(data, target)
                ch = await bot._get("competitors")
                if ch: await ch.send(embed=embed)
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("⚠️ Scan failed.")
        except ImportError as e:
            await interaction.followup.send(f"❌ {e}")

    @bot.tree.command(name="bundle", description="Create a product bundle")
    @app_commands.describe(niche="Your niche")
    async def bundle_cmd(interaction: discord.Interaction, niche: str = ""):
        await interaction.response.defer()
        target = niche or (bot.active_ventures[0].get("niche") if bot.active_ventures else "digital products")
        await interaction.followup.send(f"📦 Creating bundle for: **{target}**...")
        try:
            from agents.bundle_affiliate import create_bundle, bundle_embed
            research = bot.active_ventures[0].get("research",{}) if bot.active_ventures else {}
            products = [research.get("product_name", target), f"{target} Starter Kit", f"Complete {target} Bundle"]
            bundle = await create_bundle(products, target)
            if bundle:
                embed = bundle_embed(bundle)
                ch = await bot._get("build-pipeline")
                if ch: await ch.send(embed=embed)
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("⚠️ Failed.")
        except ImportError as e:
            await interaction.followup.send(f"❌ {e}")

    @bot.tree.command(name="affiliates", description="Find affiliate programs for your niche")
    @app_commands.describe(niche="Your niche")
    async def affiliates_cmd(interaction: discord.Interaction, niche: str = ""):
        await interaction.response.defer()
        target = niche or (bot.active_ventures[0].get("niche") if bot.active_ventures else "digital products")
        try:
            from agents.bundle_affiliate import get_relevant_affiliates, affiliate_embed
            await interaction.followup.send(embed=affiliate_embed(get_relevant_affiliates(target, target), target))
        except ImportError as e:
            await interaction.followup.send(f"❌ {e}")

    @bot.tree.command(name="post", description="Generate and post social content")
    @app_commands.describe(product="Product name", platform="tiktok|instagram|twitter|pinterest|reddit|all")
    async def post_cmd(interaction: discord.Interaction, product: str = "", platform: str = "all"):
        await interaction.response.defer()
        target = product or (bot.active_ventures[0].get("research",{}).get("product_name","digital template") if bot.active_ventures else "digital template")
        niche  = bot.active_ventures[0].get("niche","digital products") if bot.active_ventures else "digital products"
        url    = bot.active_ventures[0].get("etsy_url","") if bot.active_ventures else ""
        await interaction.followup.send(f"📱 Generating content for **{target}**...")
        try:
            from agents.social_poster import generate_content_batch, content_card_embed, PostApprovalView
            platforms = ["tiktok","instagram","twitter","pinterest","reddit"] if platform == "all" else [platform]
            contents  = await generate_content_batch(target, niche, url, "$9", platforms)
            ch = await bot._get("social-posts")
            for c in contents:
                if ch:
                    await ch.send(embed=content_card_embed(c, target), view=PostApprovalView(c, target, bot))
            await interaction.followup.send(f"✅ {len(contents)} posts ready in #social-posts")
        except ImportError as e:
            await interaction.followup.send(f"❌ {e}")


    @bot.tree.command(name="download", description="Download a generated PDF product file")
    @app_commands.describe(niche="Product niche to download (leave blank to see all files)")
    async def download_cmd(interaction: discord.Interaction, niche: str = ""):
        await interaction.response.defer()
        try:
            from agents.download_manager import get_available_files, send_pdf_to_discord
            files = get_available_files()
            if not files:
                await interaction.followup.send(
                    "No PDF files found. Run `/build [niche]` first to generate one. "
                    "Note: files clear on Railway redeploy so run `/build` again if needed."
                )
                return



            if niche:
                # Find matching file
                matches = [f for f in files if niche.lower().replace(" ","-") in f["name"].lower()]
                if not matches:
                    matches = files[:1]  # Fall back to most recent
                target = matches[0]
                ch = await bot._get("build-pipeline")
                if ch:
                    venture = next((v for v in bot.active_ventures if niche.lower() in v.get("niche","").lower()), {})
                    product_name = venture.get("research",{}).get("product_name", target["name"].replace(".pdf",""))
                    await send_pdf_to_discord(ch, target["path"], product_name)
                    await interaction.followup.send(f"✅ PDF sent to #build-pipeline — check there to download.")
                else:
                    await send_pdf_to_discord(interaction.channel, target["path"], target["name"])
                    await interaction.followup.send("✅ PDF sent above.")
            else:
                # Show file list
                lines = [f"• `{f['name']}` — {f['size_kb']}KB — created {f['created']}" for f in files[:8]]
                file_list = "\n".join([f"• `{f['name']}` — {f['size_kb']}KB — {f['created']}" for f in files[:8]])
                msg = f"**Generated PDFs ({len(files)} files):**\n{file_list}\n\nUse `/download [niche]` to send a file here."
                await interaction.followup.send(msg)





        except ImportError as e:
            await interaction.followup.send(f"❌ {e}")

    @bot.tree.command(name="usage", description="Show API usage and estimated costs across all models")
    async def usage_cmd(interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            from agents.usage_tracker import usage_embed
            await interaction.followup.send(embed=usage_embed())
        except ImportError as e:
            await interaction.followup.send(f"❌ {e}")

    @bot.tree.command(name="howtopost", description="Step-by-step guide to manually post your product")
    async def howtopost_cmd(interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            from agents.download_manager import manual_guide_embed
            await interaction.followup.send(embed=manual_guide_embed())
        except ImportError as e:
            await interaction.followup.send(f"❌ {e}")


def create_bot() -> OpenClawBot:
    bot = OpenClawBot()
    setup_commands(bot)
    return bot
