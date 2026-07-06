import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print("=" * 50)
    print(f"✅ Bot giriş yaptı: {bot.user}")
    print(f"📡 Bağlı sunucu sayısı: {len(bot.guilds)}")
    print("=" * 50)

@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"🏓 Pong! {round(bot.latency * 1000)}ms")

if __name__ == "__main__":
    bot.run(BOT_TOKEN)