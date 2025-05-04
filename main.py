import os
import re
import time
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from subprocess import getstatusoutput
from helper.utils import extract_text, get_video_data, humanbytes
import helper

# Configuration
WEBHOOK = os.getenv("WEBHOOK", "false").lower() == "true"
PORT = int(os.getenv("PORT", 8080))
API_ID = int(os.environ.get("API_ID", 12345))
API_HASH = os.environ.get("API_HASH", "your_api_hash")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_bot_token")

bot = Client("bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Global Variables
count = 0
downloaded_files = []

@bot.on_message(filters.command(["start"]))
async def start(client, message: Message):
    await message.reply_text("Hello! Send me a .txt file containing video links.")

@bot.on_message(filters.document & filters.private)
async def handle_txt_file(client, message: Message):
    global count
    count = 0
    document = message.document

    if not document.file_name.endswith(".txt"):
        await message.reply("Please send a .txt file only.")
        return

    txt_path = await message.download()
    with open(txt_path, "r") as f:
        lines = f.read().splitlines()

    for line in lines:
        if "|" not in line:
            continue

        url, name = line.split("|", 1)
        url = url.strip()
        name = name.strip()

        if not url:
            continue

        # Skip duplicate downloads
        if url in downloaded_files:
            await message.reply_text(f"Skipped (already downloaded): `{url}`")
            continue

        downloaded_files.append(url)
        safe_name = re.sub(r'[\\/*?:"<>|]', "_", name) or "video"
        filename = f"{str(count).zfill(3)}) {safe_name[:60]}.mp4"
        count += 1

        # DRM/MPD Handling
        if "/master.mpd" in url:
            if "https://sec1.pw.live/" in url:
                url = url.replace("https://sec1.pw.live/", "https://d1d34p8vz63oiq.cloudfront.net/")
            key = await helper.get_drm_keys(url)
            await message.reply_text(f"Got DRM keys:\n`{key}`")
            cmd = f'yt-dlp -k --allow-unplayable-formats -f bestvideo+bestaudio --fixup never "{url}" -o "{filename}"'

        # Classplus Links
        elif "vidgyor" in url or "classplusapp" in url:
            try:
                data = await get_video_data(url)
                m3u8_url = data["sources"][0]["file"]
                title = data["title"]
                filename = f"{str(count).zfill(3)}) {title[:60]}.mp4"
                cmd = f'yt-dlp -f best "{m3u8_url}" -o "{filename}"'
            except Exception as e:
                await message.reply(f"Error parsing Classplus link: {e}")
                continue

        # YouTube
        elif "youtu" in url:
            cmd = f'yt-dlp -f best "{url}" -o "{filename}"'

        # VisionIAS/Other .m3u8
        elif url.endswith(".m3u8") or ".m3u8?" in url:
            cmd = f'yt-dlp -f best "{url}" -o "{filename}"'

        # Fallback
        else:
            cmd = f'yt-dlp "{url}" -o "{filename}"'

        await message.reply_text(f"Downloading: `{filename}`")
        status, output = getstatusoutput(cmd)

        if status == 0:
            await message.reply_video(
                video=filename,
                caption=filename,
                supports_streaming=True
            )
            os.remove(filename)
        else:
            await message.reply_text(f"Download failed for `{filename}`:\n\n{output}")

# Login command for alternate accounts
@bot.on_message(filters.command(["Moni"]))
async def handle_moni_command(_, message: Message):
    await message.reply_text("Login not configured in this version.")

# Run bot
if __name__ == "__main__":
    if WEBHOOK:
        bot.run()
    else:
        bot.run()
