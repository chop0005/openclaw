"""
OpenClaw Discord Bot — Money-First Command Center
Goal: $500 in 30 days via digital products.
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
from ventures.digital_product import (
    research_opportunity, generate_listing_pack,
    generate_product_content, generate_launch_strategy,
    generate_product_batch
)

logger = logging.getLogger("openclaw.bot")

CHANNEL_STRUCTURE = [
    ("opportunities",   "💡 Ranked opportunities — approve one to start building"),
    ("build-pipeline",  "🏗️ Full build output — listing packs, specs, launch plans"),
    ("revenue",         "💰 Revenue tracking and reinvestment advice"),
    ("social-posts",    "📱 Ready-to-post social content"),
    ("commands",        "⚙️ Type your commands here"),
    ("logs",            "📋 System activity log"),
]

CATEGORY_NAME = "🦾 OPENCLAW HQ"


class OpenClawBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)

        self.approved_opportunities: list[dict] = []
        self.built_opportunities: set[str] = set()
        self.active_ventures: list[dict] = []
        self.revenue_log: dict[str, float] = {}
        self.channel_map: dict[str, discord.TextChannel] = {}

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

    async def _setup_channels(self, guild: discord.Guild):
        category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
        if not category:
            category = await guild.create_category(CATEGORY_NAME)
        for name, topic in CHANNEL_STRUCTURE:
            existing = discord.utils.get(guild.text_channels, name=name)
            ch = existing or await guild.create_text_channel(name=name, category=category, topic=topic)
            self.channel_map[name] = ch
        logger.info(f"✅ {len(self.channel_map)} channels ready")

    async def _get(self, name: str):
        for k, ch in self.channel_map.items():
            if name in k:
                return ch
        return None

    async def _startup_message(self):
        ch = await self._get("logs")
        if ch:
            embed = discord.Embed(
                title="🦾 OpenClaw Online — Money-First Mode",
                description=(
                    f"**Goal:** ${settings.REVENUE_TARGET:,.0f} in {settings.TARGET_DAYS} days\n"
                    f"**Budget:** ${settings.CAPITAL_BUDGET:.0f}\n"
                    f"**Strategy:** Digital products → Etsy + Gumroad\n\n"
                    f"**Active Agents:**\n"
                    f"• 🔍 Opportunity Scanner — every {settings.OPPORTUNITY_INTERVAL}m\n"
                    f"• 🏗️ Build Pipeline — triggers on approval\n"
                    f"• 💰 Revenue Tracker — daily\n\n"
                    f"Type `/help` in #commands to see all commands.\n"
                    f"Type `/scan` to find opportunities right now."
                ),
                color=0x00f5a0,
                timestamp=datetime.utcnow()
            )
            await ch.send(embed=embed)

    async def _start_agents(self):
        opp_ch  = await self._get("opportunities")
        build_ch = await self._get("build-pipeline")
        rev_ch  = await self._get("revenue")

        if opp_ch:
            asyncio.create_task(run_opportunity_scanner(self, opp_ch.id, settings.OPPORTUNITY_INTERVAL))
        if build_ch:
            asyncio.create_task(run_build_pipeline(self, build_ch.id))
        if rev_ch:
            asyncio.create_task(run_revenue_tracker(self, rev_ch.id))

        logger.info("✅ All agents started")


def setup_commands(bot: OpenClawBot):

    @bot.tree.command(name="help", description="Show all OpenClaw commands")
    async def help_cmd(interaction: discord.Interaction):
        embed = discord.Embed(
            title="🦾 OpenClaw Commands",
            description=f"Goal: **${settings.REVENUE_TARGET:,.0f} in {settings.TARGET_DAYS} days** via digital products",
            color=0x00c8f0
        )
        cmds = [
            ("/scan",                    "Find money-making opportunities right now"),
            ("/build [niche]",           "Run full build pipeline for a niche"),
            ("/listing [product]",       "Generate Etsy+Gumroad listing for a product"),
            ("/products [niche]",        "Generate 5-product store lineup"),
            ("/plan [niche]",            "Generate 30-day $500 launch plan"),
            ("/revenue add [p] [amt]",   "Log a sale (e.g. /revenue add 'Budget Tracker' 9)"),
            ("/revenue report",          "Show full revenue dashboard"),
            ("/status",                  "Show agent status + active ventures"),
            ("/goal",                    "Show progress toward $500 target"),
            ("/help",                    "Show this message"),
        ]
        for cmd, desc in cmds:
            embed.add_field(name=cmd, value=desc, inline=False)
        await interaction.response.send_message(embed=embed)

    @bot.tree.command(name="scan", description="Scan for money-making opportunities now")
    async def scan_cmd(interaction: discord.Interaction):
        await interaction.response.send_message(
            f"🔍 Scanning for opportunities... (budget: **${settings.CAPITAL_BUDGET}**, target: **${settings.REVENUE_TARGET} in {settings.TARGET_DAYS} days**)"
        )
        ch = await bot._get("opportunities")
        opps = await scan_for_opportunities(settings.CAPITAL_BUDGET)
        if opps and ch:
            await ch.send(f"**Manual scan — {datetime.now().strftime('%b %d %H:%M')}**")
            for i, opp in enumerate(opps):
                view = OpportunityApproveView(opp, bot)
                await ch.send(embed=opportunity_embed(opp, i), view=view)
            await interaction.followup.send(f"✅ {len(opps)} opportunities posted to #opportunities")
        else:
            await interaction.followup.send("⚠️ No opportunities found. Try again.")

    @bot.tree.command(name="build", description="Run full build pipeline for a niche")
    @app_commands.describe(niche="The niche to build (e.g. 'ADHD planner' or 'freelancer invoice tracker')")
    async def build_cmd(interaction: discord.Interaction, niche: str):
        await interaction.response.send_message(f"🚀 Starting build pipeline for: **{niche}**\nCheck #build-pipeline for everything.")
        if not hasattr(bot, 'approved_opportunities'):
            bot.approved_opportunities = []
        bot.approved_opportunities.append({'niche': niche, 'venture_type': 'digital_product'})

    @bot.tree.command(name="listing", description="Generate a complete Etsy+Gumroad listing")
    @app_commands.describe(product="Product name or description")
    async def listing_cmd(interaction: discord.Interaction, product: str):
        await interaction.response.send_message(f"📝 Generating listing for: **{product}**...")
        ch = await bot._get("build-pipeline")
        research = await research_opportunity(product, settings.CAPITAL_BUDGET)
        if research:
            content = await generate_product_content(research)
            listing = await generate_listing_pack(research, content or {})
            if listing and ch:
                embed = discord.Embed(
                    title=f"🏪 Listing: {product}",
                    color=0x00f5a0
                )
                title = listing.get('etsy_title', '')
                if title:
                    embed.add_field(name="Etsy Title", value=f"```{title}```", inline=False)
                tags = listing.get('etsy_tags', [])
                if tags:
                    embed.add_field(name="Tags", value=", ".join(tags), inline=False)
                embed.add_field(name="Price", value=listing.get('etsy_price', '$9'), inline=True)
                await ch.send(embed=embed)
                desc = listing.get('etsy_description', '')
                if desc:
                    await ch.send(f"**Description:**\n```{desc[:1900]}```")
                await interaction.followup.send("✅ Listing posted to #build-pipeline")
        else:
            await interaction.followup.send("⚠️ Failed to generate listing. Try again.")

    @bot.tree.command(name="products", description="Generate a 5-product store lineup")
    @app_commands.describe(niche="Store niche (e.g. 'productivity for freelancers')")
    async def products_cmd(interaction: discord.Interaction, niche: str):
        await interaction.response.send_message(f"🛒 Generating product lineup for: **{niche}**...")
        ch = await bot._get("build-pipeline")
        products = await generate_product_batch(niche, count=5)
        if products and ch:
            embed = discord.Embed(
                title=f"🛒 Store Lineup: {niche}",
                color=0x00c8f0,
                timestamp=datetime.utcnow()
            )
            for i, p in enumerate(products):
                embed.add_field(
                    name=f"#{i+1}: {p.get('name', 'Unknown')}",
                    value=f"{p.get('type', '')} • {p.get('price', '$9')}\n{p.get('one_line_description', '')}\n🔍 `{p.get('primary_keyword', '')}`",
                    inline=False
                )
            await ch.send(embed=embed)
            await interaction.followup.send(f"✅ {len(products)} products posted to #build-pipeline")
        else:
            await interaction.followup.send("⚠️ Failed. Try again.")

    @bot.tree.command(name="plan", description="Generate your 30-day $500 launch plan")
    @app_commands.describe(niche="Your niche (e.g. 'Notion templates for students')")
    async def plan_cmd(interaction: discord.Interaction, niche: str):
        await interaction.response.send_message(f"📅 Building 30-day plan for: **{niche}**...")
        ch = await bot._get("build-pipeline")
        plan = await generate_launch_strategy(niche, settings.CAPITAL_BUDGET)
        if plan and ch:
            embed = discord.Embed(
                title=f"📅 30-Day Plan: {niche}",
                description=plan.get('strategy_summary', ''),
                color=0xffc944,
                timestamp=datetime.utcnow()
            )
            for week in ['week_1', 'week_2', 'week_3', 'week_4']:
                w = plan.get(week, {})
                if w:
                    embed.add_field(
                        name=week.replace('_', ' ').title(),
                        value=f"**{w.get('focus', '')}**\nListings: {w.get('listings_to_create', 0)} | Rev: {w.get('expected_revenue', 'TBD')}",
                        inline=True
                    )
            await ch.send(embed=embed)
            await interaction.followup.send("✅ Plan posted to #build-pipeline")

    @bot.tree.command(name="revenue", description="Log a sale or view revenue report")
    @app_commands.describe(action="add or report", product="Product name", amount="Sale amount in USD")
    async def revenue_cmd(interaction: discord.Interaction, action: str, product: str = "", amount: float = 0.0):
        if action == "add" and product and amount > 0:
            if product not in bot.revenue_log:
                bot.revenue_log[product] = 0.0
            bot.revenue_log[product] += amount
            total = sum(bot.revenue_log.values())
            pct = min(int((total / settings.REVENUE_TARGET) * 100), 100)

            embed = discord.Embed(
                title="💰 Sale Logged!",
                description=(
                    f"**+${amount:.2f}** from **{product}**\n"
                    f"Total: **${total:.2f}** / ${settings.REVENUE_TARGET:.0f} ({pct}%)"
                ),
                color=0x00f5a0
            )
            if total >= settings.REVENUE_TARGET:
                embed.add_field(name="🎉 TARGET HIT!", value=f"You hit ${settings.REVENUE_TARGET:.0f}! Time to scale.", inline=False)

            await interaction.response.send_message(embed=embed)

            # Update revenue channel
            ch = await bot._get("revenue")
            if ch:
                await ch.send(embed=revenue_embed(bot))
        elif action == "report":
            await interaction.response.send_message(embed=revenue_embed(bot))
        else:
            await interaction.response.send_message(
                "Usage:\n`/revenue add \"Product Name\" 9.00` — log a sale\n`/revenue report` — view dashboard"
            )

    @bot.tree.command(name="goal", description="Show progress toward your $500 target")
    async def goal_cmd(interaction: discord.Interaction):
        await interaction.response.send_message(embed=revenue_embed(bot))

    @bot.tree.command(name="status", description="Show system status and active ventures")
    async def status_cmd(interaction: discord.Interaction):
        total = sum(bot.revenue_log.values())
        embed = discord.Embed(
            title="🦾 OpenClaw Status",
            color=0x00f5a0,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="🔍 Opportunity Scanner", value="🟢 Running", inline=True)
        embed.add_field(name="🏗️ Build Pipeline",      value="🟢 Running", inline=True)
        embed.add_field(name="💰 Revenue Tracker",     value="🟢 Running", inline=True)
        embed.add_field(name="Approved Niches",   value=str(len(bot.approved_opportunities)), inline=True)
        embed.add_field(name="Built Ventures",    value=str(len(bot.built_opportunities)), inline=True)
        embed.add_field(name="Revenue Earned",    value=f"${total:,.2f}", inline=True)

        if bot.active_ventures:
            ventures_str = "\n".join([f"• {v.get('niche', 'Unknown')}" for v in bot.active_ventures])
            embed.add_field(name="Active Ventures", value=ventures_str, inline=False)

        embed.set_footer(text=f"Goal: ${settings.REVENUE_TARGET:.0f} in {settings.TARGET_DAYS} days")
        await interaction.response.send_message(embed=embed)


    @bot.tree.command(name="test", description="Test Claude and GLM API connections")
    async def test_cmd(interaction: discord.Interaction):
        await interaction.response.send_message("🔍 Testing API connections...")

        embed = discord.Embed(
            title="🔌 API Connection Test",
            color=0x00c8f0,
            timestamp=datetime.utcnow()
        )

        # Test Claude
        try:
            from utils.claude import think
            result = await think("You are a test.", "Reply with exactly: CLAUDE_OK")
            if "CLAUDE_OK" in result:
                embed.add_field(name="✅ Claude Sonnet", value=f"Connected — model: `{settings.CLAUDE_MODEL}`", inline=False)
            else:
                embed.add_field(name="⚠️ Claude Sonnet", value=f"Responded but unexpected: `{result[:50]}`", inline=False)
        except Exception as e:
            embed.add_field(name="❌ Claude Sonnet", value=f"Error: `{str(e)[:80]}`", inline=False)

        # Test GLM
        if settings.GLM_API_KEY:
            try:
                from utils.claude import think_code
                result = await think_code("You are a test.", "Reply with exactly: GLM_OK")
                if "GLM_OK" in result:
                    embed.add_field(name="✅ GLM Code Model", value=f"Connected — model: `{settings.GLM_CODE_MODEL}`", inline=False)
                else:
                    embed.add_field(name="⚠️ GLM Code Model", value=f"Responded but unexpected: `{result[:50]}`", inline=False)
            except Exception as e:
                embed.add_field(name="❌ GLM Code Model", value=f"Error: `{str(e)[:80]}`", inline=False)
        else:
            embed.add_field(
                name="⏭️ GLM Code Model",
                value="No GLM_API_KEY set. Add it in Railway variables to enable cheap code generation.\nFalling back to Claude for code tasks.",
                inline=False
            )

        embed.set_footer(text="OpenClaw API Router — Claude for strategy, GLM for code")
        await interaction.followup.send(embed=embed)


    @bot.tree.command(name="etsy", description="Etsy connection and listing management")
    @app_commands.describe(action="setup | test | listings | auth")
    async def etsy_cmd(interaction: discord.Interaction, action: str = "test"):
        from ventures.etsy_manager import EtsyClient, ETSY_SETUP_GUIDE
        etsy = EtsyClient()

        if action == "setup":
            await interaction.response.send_message(ETSY_SETUP_GUIDE)

        elif action == "test":
            if not etsy.is_configured():
                await interaction.response.send_message(
                    "⚠️ Etsy not configured.\n"
                    "Missing variables: " +
                    (", ".join([
                        v for v, val in [
                            ("ETSY_API_KEY", settings.ETSY_API_KEY),
                            ("ETSY_ACCESS_TOKEN", settings.ETSY_ACCESS_TOKEN),
                            ("ETSY_SHOP_ID", settings.ETSY_SHOP_ID)
                        ] if not val
                    ])) +
                    "\n\nType `/etsy setup` for instructions."
                )
                return
            await interaction.response.send_message("🔍 Testing Etsy connection...")
            try:
                shop = await etsy.get_shop()
                if shop.get("shop_id"):
                    await interaction.followup.send(
                        f"✅ Etsy connected!\n"
                        f"Shop: **{shop.get('shop_name')}**\n"
                        f"ID: `{shop.get('shop_id')}`\n"
                        f"Listings: {shop.get('listing_active_count', 0)} active"
                    )
                else:
                    await interaction.followup.send(f"❌ Connection failed: {shop}")
            except Exception as e:
                await interaction.followup.send(f"❌ Error: {e}")

        elif action == "listings":
            if not etsy.is_configured():
                await interaction.response.send_message("⚠️ Etsy not configured. Type `/etsy setup`.")
                return
            await interaction.response.send_message("📋 Fetching your Etsy drafts...")
            try:
                drafts = await etsy.get_listings("draft")
                active = await etsy.get_listings("active")
                msg = f"**Etsy Shop Status**\n• Active listings: {len(active)}\n• Draft listings: {len(drafts)}\n"
                if drafts:
                    msg += "\n**Drafts:**\n" + "\n".join([f"• {d.get('title','Unknown')[:60]} (ID: {d.get('listing_id')})" for d in drafts[:5]])
                await interaction.followup.send(msg)
            except Exception as e:
                await interaction.followup.send(f"❌ Error: {e}")

        else:
            await interaction.response.send_message("Usage: `/etsy setup` | `/etsy test` | `/etsy listings`")


def create_bot() -> OpenClawBot:
    bot = OpenClawBot()
    setup_commands(bot)
    return bot
