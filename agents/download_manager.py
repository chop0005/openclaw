"""
OpenClaw — Download Manager
Sends generated PDFs to Discord + manual posting guide.
"""

import os
import logging
import discord
from datetime import datetime

logger = logging.getLogger("openclaw.downloads")
PDF_DIR = "/tmp/openclaw-products"


def get_available_files() -> list:
    if not os.path.exists(PDF_DIR):
        return []
    files = []
    for fname in sorted(os.listdir(PDF_DIR)):
        if fname.endswith('.pdf'):
            fpath = os.path.join(PDF_DIR, fname)
            files.append({
                "name":    fname,
                "path":    fpath,
                "size_kb": os.path.getsize(fpath) // 1024,
                "created": datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%b %d %H:%M"),
            })
    return sorted(files, key=lambda x: x["created"], reverse=True)


async def send_pdf_to_discord(channel: discord.TextChannel, filepath: str, product_name: str):
    if not os.path.exists(filepath):
        await channel.send(f"❌ File not found: `{os.path.basename(filepath)}`\nThe PDF may have been cleared. Run `/build` again to regenerate.")
        return
    size = os.path.getsize(filepath)
    if size > 8 * 1024 * 1024:
        await channel.send(f"⚠️ PDF is {size//1024}KB — too large for Discord (8MB limit).\nFile: `{filepath}`\nAccess it via Railway volume.")
        return
    try:
        await channel.send(
            content=f"📥 **{product_name}** ({size//1024}KB)\nDownload → upload to Gumroad/Etsy:",
            file=discord.File(filepath, filename=os.path.basename(filepath))
        )
    except Exception as e:
        await channel.send(f"❌ Send failed: {e}")


def manual_guide_embed() -> discord.Embed:
    embed = discord.Embed(
        title="📋 Manual Posting Guide",
        description="How to list your product on each platform while Etsy API is pending.",
        color=0xffc944,
        timestamp=datetime.utcnow()
    )
    embed.add_field(
        name="🟢 Gumroad — Do This NOW (zero fees, instant)",
        value=(
            "1. Go to **gumroad.com/products/new**\n"
            "2. Name → copy product name from #build-pipeline\n"
            "3. Description → copy Gumroad pitch from #build-pipeline\n"
            "4. Price → set as recommended\n"
            "5. Content → upload your PDF (use `/download` to get it)\n"
            "6. Hit **Publish** ✅\n"
            "7. Share link on social media immediately"
        ),
        inline=False
    )
    embed.add_field(
        name="🟠 Etsy — Manual Until API Approved",
        value=(
            "1. **etsy.com/sell** → your shop → Add a listing\n"
            "2. Title → copy from #build-pipeline\n"
            "3. Tags → copy all 13 tags, add one by one\n"
            "4. Description → copy full description\n"
            "5. Price → set as recommended\n"
            "6. Digital file → upload your PDF\n"
            "7. Category: Digital downloads → Templates\n"
            "8. Hit **Publish** ✅"
        ),
        inline=False
    )
    embed.add_field(
        name="📌 Pinterest — Free Traffic (do today)",
        value=(
            "1. **pinterest.com** → Create Pin\n"
            "2. Upload a mockup image (Canva → free mockup)\n"
            "3. Title + description → copy from #social-posts\n"
            "4. Link → paste your Gumroad URL\n"
            "5. Pin to your niche board\n"
            "6. Repeat 3x/day for compounding traffic"
        ),
        inline=False
    )
    embed.add_field(
        name="🔴 Reddit — First Sales Fastest",
        value=(
            "1. Find your subreddit (r/sidehustle, r/Entrepreneur, r/digitalnomad)\n"
            "2. Copy the Reddit post from #social-posts\n"
            "3. Post it — be authentic, not salesy\n"
            "4. Reply to every comment\n"
            "**Reddit → Gumroad is the fastest path to your first sale.**"
        ),
        inline=False
    )
    embed.add_field(
        name="⚡ Fastest Path to First Sale",
        value="**Today:** List on Gumroad (5 min) → Post on Reddit → Pin on Pinterest\n**This week:** $9-27 coming in before Etsy even approves.",
        inline=False
    )
    embed.set_footer(text="OpenClaw • Etsy auto-listing activates once API is approved")
    return embed
