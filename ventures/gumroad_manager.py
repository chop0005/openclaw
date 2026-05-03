"""
OpenClaw — Gumroad Manager
Auto-creates product listings on Gumroad via API.
Gumroad is simpler than Etsy — no OAuth dance, just an access token.
Products are created as unpublished drafts until you activate.

Setup:
1. Create account at gumroad.com
2. Go to gumroad.com/settings/advanced → Applications → Generate access token
3. Add GUMROAD_ACCESS_TOKEN to Railway variables
"""

import aiohttp
import logging
import discord
from datetime import datetime
from config.settings import settings

logger = logging.getLogger("openclaw.gumroad")

GUMROAD_BASE = "https://api.gumroad.com/v2"


class GumroadClient:
    def __init__(self):
        self.token = settings.GUMROAD_ACCESS_TOKEN or ""

    def is_configured(self) -> bool:
        return bool(self.token)

    async def create_product(self, product: dict) -> dict:
        """Creates a product on Gumroad. Published=false means it's a draft."""
        async with aiohttp.ClientSession() as session:
            payload = {
                "access_token":  self.token,
                "name":          product.get("name", "")[:255],
                "description":   product.get("description", ""),
                "price":         int(float(product.get("price", 9)) * 100),  # cents
                "published":     False,  # draft until you activate
                "tags":          ",".join(product.get("tags", [])[:10]),
            }
            async with session.post(
                f"{GUMROAD_BASE}/products",
                data=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                data = await resp.json()
                if data.get("success"):
                    logger.info(f"Gumroad product created: {data['product']['id']}")
                return {"success": data.get("success", False), "data": data}

    async def publish_product(self, product_id: str) -> dict:
        """Makes a draft product live."""
        async with aiohttp.ClientSession() as session:
            async with session.put(
                f"{GUMROAD_BASE}/products/{product_id}",
                data={"access_token": self.token, "published": True},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                data = await resp.json()
                return {"success": data.get("success", False), "data": data}

    async def get_products(self) -> list:
        """Gets all products."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{GUMROAD_BASE}/products",
                params={"access_token": self.token},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                data = await resp.json()
                return data.get("products", [])

    async def get_sales(self) -> dict:
        """Gets recent sales data."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{GUMROAD_BASE}/sales",
                params={"access_token": self.token},
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                data = await resp.json()
                return data


class GumroadApprovalView(discord.ui.View):
    def __init__(self, product_data: dict, listing_data: dict, bot_ref):
        super().__init__(timeout=None)
        self.product_data = product_data
        self.listing_data = listing_data
        self.bot_ref      = bot_ref
        self.gumroad      = GumroadClient()

    @discord.ui.button(label="📦 Create Draft on Gumroad", style=discord.ButtonStyle.primary)
    async def create_draft(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.gumroad.is_configured():
            await interaction.response.send_message(
                "⚠️ Add `GUMROAD_ACCESS_TOKEN` to Railway variables first.\n"
                "Get it at: gumroad.com/settings/advanced → Applications",
                ephemeral=False
            )
            return

        await interaction.response.send_message("📦 Creating Gumroad product...", ephemeral=False)

        result = await self.gumroad.create_product({
            "name":        self.listing_data.get("title", self.product_data.get("product_name", ""))[:255],
            "description": self.listing_data.get("gumroad_description", self.listing_data.get("description", "")),
            "price":       self.listing_data.get("price", 9),
            "tags":        self.listing_data.get("tags", [])[:10],
        })

        if result["success"]:
            prod = result["data"]["product"]
            pid  = prod["id"]
            url  = prod.get("short_url", f"https://gumroad.com/l/{pid}")
            await interaction.followup.send(
                f"✅ **Draft created on Gumroad!**\n"
                f"Product ID: `{pid}`\n"
                f"URL (live after publish): {url}\n"
                f"Upload your product file at gumroad.com/products/{pid}/edit\n"
                f"Then tap Publish to go live.",
                ephemeral=False
            )
            # Store for tracking
            if hasattr(self.bot_ref, 'active_ventures'):
                for v in self.bot_ref.active_ventures:
                    if v.get('niche') == self.product_data.get('niche'):
                        v['gumroad_product_id'] = pid
                        v['gumroad_url']         = url
        else:
            error = result["data"].get("message", "Unknown error")
            await interaction.followup.send(f"❌ Gumroad error: {error}", ephemeral=False)

    @discord.ui.button(label="🚀 Create + Publish Now", style=discord.ButtonStyle.success)
    async def publish_now(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.gumroad.is_configured():
            await interaction.response.send_message(
                "⚠️ Add `GUMROAD_ACCESS_TOKEN` to Railway variables first.",
                ephemeral=False
            )
            return

        await interaction.response.send_message("🚀 Creating and publishing on Gumroad...", ephemeral=False)

        result = await self.gumroad.create_product({
            "name":        self.listing_data.get("title", self.product_data.get("product_name", ""))[:255],
            "description": self.listing_data.get("gumroad_description", self.listing_data.get("description", "")),
            "price":       self.listing_data.get("price", 9),
            "tags":        self.listing_data.get("tags", [])[:10],
        })

        if result["success"]:
            prod = result["data"]["product"]
            pid  = prod["id"]

            # Publish immediately
            pub = await self.gumroad.publish_product(pid)
            url = prod.get("short_url", f"https://gumroad.com/l/{pid}")

            if pub["success"]:
                await interaction.followup.send(
                    f"🎉 **Product is LIVE on Gumroad!**\n"
                    f"URL: {url}\n"
                    f"⚠️ Upload your product file at gumroad.com/products/{pid}/edit\n"
                    f"Share the URL to start getting sales!",
                    ephemeral=False
                )
            else:
                await interaction.followup.send(
                    f"✅ Draft created (ID: {pid}) but publish failed.\n"
                    f"Publish manually at gumroad.com/products/{pid}/edit",
                    ephemeral=False
                )
        else:
            error = result["data"].get("message", "Unknown error")
            await interaction.followup.send(f"❌ Gumroad error: {error}", ephemeral=False)

    @discord.ui.button(label="⏭️ Skip", style=discord.ButtonStyle.secondary)
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("⏭️ Skipped Gumroad.", ephemeral=False)
        self.stop()


GUMROAD_SETUP = """**📦 Gumroad Setup — 2 Minutes**

1. Go to **gumroad.com** → sign up free
2. Go to **gumroad.com/settings/advanced**
3. Scroll to **Applications** → tap **Generate Access Token**
4. Copy the token
5. In Railway → Variables → add:
   `GUMROAD_ACCESS_TOKEN` = your token

That's it. Gumroad is much simpler than Etsy — no OAuth, no shop ID needed."""
