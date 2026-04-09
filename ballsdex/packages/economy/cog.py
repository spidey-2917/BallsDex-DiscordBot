from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

import discord
from discord import app_commands
from discord.ext import commands

from ballsdex.core.models import Ball, BallInstance, PackClaim, Player, ShopPackUse, Wallet, balls
from ballsdex.settings import settings

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot

log = logging.getLogger("ballsdex.packages.economy")

SELL_COIN_BASE = 50

# Pengu is a special ball - selling it is restricted and gives a fixed payout
PENGU_NAME = "Pengu"
PENGU_SELL_VALUE = 2000

FREE_DAILY_MIN = 7.0
FREE_DAILY_MAX = 8.0
FREE_WEEKLY_MIN = 2.0
FREE_WEEKLY_MAX = 4.0


@dataclass
class PackType:
    key: str
    name: str
    emoji: str
    cost: int
    rarity_min: float
    rarity_max: float
    max_uses: int
    reset: str  # "daily" or "weekly"

    @property
    def rarity_display(self):
        return f"{self.rarity_min:.0f}–{self.rarity_max:.0f}"


PACKS: list[PackType] = [
    PackType("common", "Common Pack", "<:Common:1487247385896681692>", 1000, 7.0, 8.0, 3, "daily"),
    PackType(
        "stonemask",
        "Stone Mask Pack",
        "<:StoneMask:1489936717711671316>",
        2000,
        5.0,
        7.0,
        3,
        "daily",
    ),
    PackType(
        "steelball",
        "Steel Ball Pack",
        "<:SteelBall:1489936796979826808>",
        4000,
        4.0,
        6.0,
        2,
        "daily",
    ),
    PackType("disc", "Disc Pack", "<:Disc:1489936934141821019>", 6000, 3.0, 5.0, 2, "weekly"),
    PackType(
        "standarrow",
        "Stand Arrow Pack",
        "<:StandArrow:1489937005658767491>",
        8000,
        2.0,
        4.0,
        1,
        "weekly",
    ),
    PackType(
        "gobeyond",
        "Go Beyond! Pack",
        "<:GoBeyond:1489937065448837135>",
        10000,
        1.0,
        3.0,
        1,
        "weekly",
    ),
]

PACK_MAP = {p.key: p for p in PACKS}


def now_utc():
    return datetime.now(tz=timezone.utc)


def day_start():
    n = now_utc()
    return n.replace(hour=0, minute=0, second=0, microsecond=0)


def week_start():
    n = now_utc()
    mon = n - timedelta(days=n.weekday())
    return mon.replace(hour=0, minute=0, second=0, microsecond=0)


def reset_start(reset: str) -> datetime:
    return day_start() if reset == "daily" else week_start()


def next_reset_ts(reset: str) -> int:
    if reset == "daily":
        return int((day_start() + timedelta(days=1)).timestamp())
    return int((week_start() + timedelta(weeks=1)).timestamp())


async def get_wallet(player: Player) -> Wallet:
    wallet, _ = await Wallet.get_or_create(player=player)
    return wallet


def pick_ball(rarity_min: float, rarity_max: float) -> Ball | None:
    pool = [b for b in balls.values() if b.enabled and rarity_min <= b.rarity <= rarity_max]
    if not pool:
        return None
    return random.choices(pool, weights=[b.rarity for b in pool], k=1)[0]


async def give_ball(player: Player, ball_model: Ball) -> BallInstance:
    atk = random.randint(-settings.max_attack_bonus, settings.max_attack_bonus)
    hp = random.randint(-settings.max_health_bonus, settings.max_health_bonus)
    return await BallInstance.create(
        ball=ball_model,
        player=player,
        attack_bonus=atk,
        health_bonus=hp,
        deleted=False,
    )


class Economy(commands.GroupCog, name="economy"):
    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot

    @app_commands.command(name="balance", description="Show your current balance of coins.")
    async def balance(self, interaction: discord.Interaction["BallsDexBot"]):
        player, _ = await Player.get_or_create(discord_id=interaction.user.id)
        wallet = await get_wallet(player)
        embed = discord.Embed(color=discord.Color.gold())
        embed.set_author(
            name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url
        )
        embed.description = f"Balance: **{wallet.coins:,} 🪙**"
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="give", description="Give coins to a user. Admin only.")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(user="Who to give coins to", amount="Amount of coins")
    async def give(
        self,
        interaction: discord.Interaction["BallsDexBot"],
        user: discord.User,
        amount: app_commands.Range[int, 1],
    ):
        player, _ = await Player.get_or_create(discord_id=user.id)
        wallet = await get_wallet(player)
        wallet.coins += amount
        await wallet.save(update_fields=("coins",))
        await interaction.response.send_message(
            f"Gave **{amount:,} 🪙** to {user.mention}. They now have **{wallet.coins:,} 🪙**."
        )
        log.info(f"{interaction.user} gave {amount} coins to {user}")

    @app_commands.command(name="sell", description="Sell a Pengu for coins.")
    @app_commands.describe(countryball="Instance ID of the Pengu to sell")
    async def sell(self, interaction: discord.Interaction["BallsDexBot"], countryball: int):
        await interaction.response.defer(ephemeral=True)
        player, _ = await Player.get_or_create(discord_id=interaction.user.id)

        try:
            inst = await BallInstance.get(id=countryball, player=player)
            await inst.fetch_related("ball")
        except BallInstance.DoesNotExist:
            await interaction.followup.send("That ball isn't in your collection.", ephemeral=True)
            return

        if inst.ball.country.lower() != PENGU_NAME.lower():
            await interaction.followup.send(
                f"Only **{PENGU_NAME}** can be sold. Use `/economy bulk_sell` for Pengus.",
                ephemeral=True,
            )
            return

        if inst.locked:
            await interaction.followup.send("That Pengu is locked in a trade.", ephemeral=True)
            return

        wallet = await get_wallet(player)
        wallet.coins += PENGU_SELL_VALUE
        await wallet.save(update_fields=("coins",))
        await inst.delete()

        await interaction.followup.send(
            f"Sold **{PENGU_NAME}** for **{PENGU_SELL_VALUE:,} \U0001fa99**."
            f" Balance: **{wallet.coins:,} \U0001fa99**",
            ephemeral=True,
        )

    @app_commands.command(
        name="bulk_sell",
        description="Bulk sell multiple Pengus for coins. Separate IDs with spaces.",
    )
    @app_commands.describe(countryball_ids="Space-separated Pengu instance IDs")
    async def bulk_sell(
        self, interaction: discord.Interaction["BallsDexBot"], countryball_ids: str
    ):
        await interaction.response.defer(ephemeral=True)
        player, _ = await Player.get_or_create(discord_id=interaction.user.id)

        ids = []
        for x in countryball_ids.split():
            try:
                ids.append(int(x))
            except ValueError:
                pass

        if not ids:
            await interaction.followup.send("No valid IDs given.", ephemeral=True)
            return

        instances = await BallInstance.filter(
            id__in=ids, player=player, locked__isnull=True
        ).prefetch_related("ball")

        if not instances:
            await interaction.followup.send(
                "None of those IDs matched unlocked balls in your collection.", ephemeral=True
            )
            return

        # filter to Pengu only, skip anything else
        pengu_instances = [i for i in instances if i.ball.country.lower() == PENGU_NAME.lower()]
        skipped = len(instances) - len(pengu_instances)

        if not pengu_instances:
            await interaction.followup.send(
                f"None of those balls are **{PENGU_NAME}**. Only Pengus can be sold.",
                ephemeral=True,
            )
            return

        total = 0
        for inst in pengu_instances:
            total += PENGU_SELL_VALUE
            await inst.delete()

        wallet = await get_wallet(player)
        wallet.coins += total
        await wallet.save(update_fields=("coins",))

        embed = discord.Embed(color=discord.Color.gold())
        embed.title = f"Sold {len(pengu_instances)}x {PENGU_NAME}"
        embed.description = f"Earned **{total:,} 🪙**\nNew balance: **{wallet.coins:,} 🪙**"
        if skipped:
            embed.set_footer(text=f"{skipped} non-Pengu ball(s) were skipped")
        await interaction.followup.send(embed=embed, ephemeral=True)


class Pack(commands.GroupCog, name="pack"):
    def __init__(self, bot: "BallsDexBot"):
        self.bot = bot

    @app_commands.command(name="daily", description="Claim your free daily pack.")
    async def daily(self, interaction: discord.Interaction["BallsDexBot"]):
        await interaction.response.defer(ephemeral=True)
        player, _ = await Player.get_or_create(discord_id=interaction.user.id)

        claimed = await PackClaim.filter(
            player=player, pack_type=PackClaim.PACK_DAILY, claimed_at__gte=day_start()
        ).exists()

        if claimed:
            ts = next_reset_ts("daily")
            await interaction.followup.send(
                f"Already claimed today. Resets <t:{ts}:R>", ephemeral=True
            )
            return

        ball_model = pick_ball(FREE_DAILY_MIN, FREE_DAILY_MAX)
        if not ball_model:
            await interaction.followup.send(
                "No balls available right now, contact an admin.", ephemeral=True
            )
            return

        inst = await give_ball(player, ball_model)
        await PackClaim.create(player=player, pack_type=PackClaim.PACK_DAILY)

        embed = discord.Embed(
            title="⭐ Daily Pack", color=discord.Color.blue()
        )  # update emoji if you get a custom one
        embed.description = (
            f"You got **{ball_model.country}**!\n-# ID: `{inst.pk}` • Rarity `{ball_model.rarity}`"
        )
        embed.set_footer(text="Come back tomorrow for another one")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="weekly", description="Claim your free weekly pack.")
    async def weekly(self, interaction: discord.Interaction["BallsDexBot"]):
        await interaction.response.defer(ephemeral=True)
        player, _ = await Player.get_or_create(discord_id=interaction.user.id)

        claimed = await PackClaim.filter(
            player=player, pack_type=PackClaim.PACK_WEEKLY, claimed_at__gte=week_start()
        ).exists()

        if claimed:
            ts = next_reset_ts("weekly")
            await interaction.followup.send(
                f"Already claimed this week. Resets <t:{ts}:R>", ephemeral=True
            )
            return

        ball_model = pick_ball(FREE_WEEKLY_MIN, FREE_WEEKLY_MAX)
        if not ball_model:
            await interaction.followup.send(
                "No balls available right now, contact an admin.", ephemeral=True
            )
            return

        inst = await give_ball(player, ball_model)
        await PackClaim.create(player=player, pack_type=PackClaim.PACK_WEEKLY)

        embed = discord.Embed(
            title="<:StandArrow:1489937005658767491> Weekly Pack", color=discord.Color.purple()
        )
        embed.description = (
            f"You got **{ball_model.country}**!\n-# ID: `{inst.pk}` • Rarity `{ball_model.rarity}`"
        )
        embed.set_footer(text="Come back next week for another one")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="shop", description="Buy packs with coins.")
    async def shop(self, interaction: discord.Interaction["BallsDexBot"]):
        player, _ = await Player.get_or_create(discord_id=interaction.user.id)
        wallet = await get_wallet(player)

        d_start = day_start()
        w_start = week_start()
        uses: dict[str, int] = {}
        for pack in PACKS:
            since = d_start if pack.reset == "daily" else w_start
            uses[pack.key] = await ShopPackUse.filter(
                player=player, pack_type=pack.key, used_at__gte=since
            ).count()

        embed = discord.Embed(title="Pack Shop", color=0xF0A500)
        embed.description = f"Balance: **{wallet.coins:,} 🪙**\n\u200b"

        for pack in PACKS:
            remaining = max(0, pack.max_uses - uses[pack.key])
            ts = next_reset_ts(pack.reset)
            status = (
                f"**{remaining}/{pack.max_uses}** uses left"
                if remaining > 0
                else f"Resets <t:{ts}:R>"
            )
            embed.add_field(
                name=f"{pack.emoji} {pack.name} — {pack.cost:,} 🪙",
                value=f"Rarity {pack.rarity_display} • {status}",
                inline=False,
            )

        view = ShopView(player, wallet, uses, self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


class ShopView(discord.ui.View):
    def __init__(self, player: Player, wallet: Wallet, uses: dict[str, int], bot: "BallsDexBot"):
        super().__init__(timeout=60)
        self.player = player
        self.wallet = wallet
        self.uses = uses
        self.bot = bot

        for pack in PACKS:
            remaining = max(0, pack.max_uses - uses.get(pack.key, 0))
            btn = discord.ui.Button(
                label=f"{pack.emoji} {pack.name} ({pack.cost:,} 🪙)",
                style=discord.ButtonStyle.primary,
                disabled=remaining == 0,
                custom_id=pack.key,
            )
            btn.callback = self._make_callback(pack)
            self.add_item(btn)

    def _make_callback(self, pack: PackType):
        async def callback(interaction: discord.Interaction):
            wallet = await Wallet.get(player=self.player)
            since = reset_start(pack.reset)

            uses = await ShopPackUse.filter(
                player=self.player, pack_type=pack.key, used_at__gte=since
            ).count()

            if uses >= pack.max_uses:
                ts = next_reset_ts(pack.reset)
                await interaction.response.send_message(
                    f"No uses left for this pack. Resets <t:{ts}:R>", ephemeral=True
                )
                return

            if wallet.coins < pack.cost:
                await interaction.response.send_message(
                    f"You need **{pack.cost:,} 🪙** but only have **{wallet.coins:,} 🪙**.",
                    ephemeral=True,
                )
                return

            ball_model = pick_ball(pack.rarity_min, pack.rarity_max)
            if not ball_model:
                await interaction.response.send_message(
                    "No balls available in that rarity range right now.", ephemeral=True
                )
                return

            wallet.coins -= pack.cost
            await wallet.save(update_fields=("coins",))
            inst = await give_ball(self.player, ball_model)
            await ShopPackUse.create(player=self.player, pack_type=pack.key)

            embed = discord.Embed(title=f"{pack.emoji} {pack.name}", color=discord.Color.green())
            embed.description = (
                f"You got **{ball_model.country}**!\n"
                f"-# ID: `{inst.pk}` • Rarity `{ball_model.rarity}`\n\n"
                f"Balance: **{wallet.coins:,} 🪙**"
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            log.debug(f"{interaction.user} opened {pack.name}, got {ball_model.country}")

        return callback
