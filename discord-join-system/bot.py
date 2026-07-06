import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

# .env dosyasını yükle (SADECE LOCALHOST İÇİN)
load_dotenv()

# Vercel'de Environment Variables'dan, localhost'ta .env'den okur
BOT_TOKEN = os.getenv('BOT_TOKEN')

print("=" * 50)
print("🔍 Bot Token Kontrolü:")
print(f"BOT_TOKEN: {'✅ VAR' if BOT_TOKEN else '❌ YOK'}")
print("=" * 50)

if not BOT_TOKEN:
    print("❌ HATA: BOT_TOKEN bulunamadı!")
    print("📝 Vercel'de Environment Variables'ları kontrol et!")
    exit(1)

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