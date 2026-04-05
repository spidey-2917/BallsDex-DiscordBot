from typing import TYPE_CHECKING

from .cog import Economy, Pack

if TYPE_CHECKING:
    from ballsdex.core.bot import BallsDexBot


async def setup(bot: "BallsDexBot"):
    await bot.add_cog(Economy(bot))
    await bot.add_cog(Pack(bot))
