import discord
from discord import app_commands
from discord.ext import commands, tasks
import sqlite3
from datetime import datetime, timedelta
import pytz

TOKEN
GUILD_ID

EST = pytz.timezone("US/Eastern")

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- DATABASE ----------
conn = sqlite3.connect("races.db")
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS races (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    time TEXT,
    location TEXT,
    boat TEXT
)
""")
conn.commit()

# ---------- UTIL ----------
def fetch_races():
    c.execute("SELECT * FROM races ORDER BY time ASC")
    return c.fetchall()

def est_now():
    return datetime.now(EST)

def race_embed(race, title="🏁 Race Reminder"):
    race_time = datetime.fromisoformat(race[1]).astimezone(EST)
    return discord.Embed(
        title=title,
        color=0x1abc9c
    ).add_field(
        name="🕒 Time",
        value=race_time.strftime("%B %d, %Y • %I:%M %p EST"),
        inline=False
    ).add_field(
        name="📍 Location",
        value=race[2],
        inline=False
    ).add_field(
        name="🚣 Boat",
        value=race[3],
        inline=False
    )

# ---------- EVENTS ----------
@bot.event
async def on_ready():
    await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
    check_races.start()
    print("Bot online.")

# ---------- BACKGROUND TASK ----------
@tasks.loop(minutes=1)
async def check_races():
    races = fetch_races()
    now = est_now()

    for race in races:
        race_time = datetime.fromisoformat(race[1]).astimezone(EST)

        for days in (3, 2, 1):
            notify_time = (race_time - timedelta(days=days)).replace(
                hour=16, minute=0, second=0
            )

            if now.replace(second=0, microsecond=0) == notify_time:
                channel = discord.utils.get(
                    bot.get_all_channels(), name="announcements"
                )
                if channel:
                    await channel.send(
                        content="@RaceNotify",
                        embed=race_embed(race, f"⏰ {days} Day Race Reminder")
                    )

# ---------- COMMANDS ----------
@bot.tree.command(guild=discord.Object(id=GUILD_ID), name="addrace")
@app_commands.describe(
    date="YYYY-MM-DD",
    time="HH:MM (24h)",
    location="Race location",
    boat="Boat type"
)
async def addrace(interaction: discord.Interaction, date: str, time: str, location: str, boat: str):
    dt = EST.localize(datetime.fromisoformat(f"{date} {time}"))
    c.execute("INSERT INTO races (time, location, boat) VALUES (?, ?, ?)",
              (dt.isoformat(), location, boat))
    conn.commit()
    await interaction.response.send_message("✅ Race added.", ephemeral=True)

@bot.tree.command(guild=discord.Object(id=GUILD_ID), name="nextrace")
async def nextrace(interaction: discord.Interaction):
    races = fetch_races()
    now = est_now()

    for race in races:
        race_time = datetime.fromisoformat(race[1]).astimezone(EST)
        if race_time > now:
            delta = race_time - now
            minutes = int(delta.total_seconds() // 60)
            await interaction.response.send_message(
                embed=race_embed(
                    race,
                    f"⏱ Next Race — {minutes} minutes away"
                )
            )
            return
    await interaction.response.send_message("No upcoming races.")

@bot.tree.command(guild=discord.Object(id=GUILD_ID), name="upcomingraces")
async def upcomingraces(interaction: discord.Interaction):
    races = fetch_races()[:3]
    if not races:
        await interaction.response.send_message("No upcoming races.")
        return

    embed = discord.Embed(title="📅 Upcoming Races", color=0x3498db)
    for race in races:
        rt = datetime.fromisoformat(race[1]).astimezone(EST)
        embed.add_field(
            name=f"Race #{race[0]}",
            value=f"{rt.strftime('%b %d %I:%M %p')} • {race[2]} • {race[3]}",
            inline=False
        )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(guild=discord.Object(id=GUILD_ID), name="allraces")
async def allraces(interaction: discord.Interaction):
    races = fetch_races()
    if not races:
        await interaction.response.send_message("No races saved.")
        return

    embed = discord.Embed(title="🏁 All Races", color=0x95a5a6)
    for race in races:
        rt = datetime.fromisoformat(race[1]).astimezone(EST)
        embed.add_field(
            name=f"ID {race[0]}",
            value=f"{rt.strftime('%b %d %I:%M %p')} • {race[2]} • {race[3]}",
            inline=False
        )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(guild=discord.Object(id=GUILD_ID), name="deleterace")
async def deleterace(interaction: discord.Interaction, race_id: int):
    c.execute("DELETE FROM races WHERE id = ?", (race_id,))
    conn.commit()
    await interaction.response.send_message("🗑️ Race deleted.", ephemeral=True)

@bot.tree.command(guild=discord.Object(id=GUILD_ID), name="editrace")
async def editrace(
    interaction: discord.Interaction,
    race_id: int,
    date: str,
    time: str,
    location: str,
    boat: str
):
    dt = EST.localize(datetime.fromisoformat(f"{date} {time}"))
    c.execute("""
        UPDATE races
        SET time = ?, location = ?, boat = ?
        WHERE id = ?
    """, (dt.isoformat(), location, boat, race_id))
    conn.commit()
    await interaction.response.send_message("✏️ Race updated.", ephemeral=True)

bot.run(TOKEN)


