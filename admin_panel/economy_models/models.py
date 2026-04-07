from django.db import models

from bd_models.models import Player


class Wallet(models.Model):
    player = models.OneToOneField(Player, on_delete=models.CASCADE, related_name="wallet")
    coins = models.BigIntegerField(default=0)

    def __str__(self) -> str:
        return f"{self.player} — {self.coins} coins"

    class Meta:
        db_table = "economy_wallet"


class PackClaim(models.Model):
    PACK_DAILY = "daily"
    PACK_WEEKLY = "weekly"
    PACK_CHOICES = [
        (PACK_DAILY, "Daily"),
        (PACK_WEEKLY, "Weekly"),
    ]

    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="pack_claims")
    pack_type = models.CharField(max_length=16, choices=PACK_CHOICES)
    claimed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.player} claimed {self.pack_type} at {self.claimed_at}"

    class Meta:
        db_table = "economy_packclaim"


class ShopPackUse(models.Model):
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="shop_pack_uses")
    pack_type = models.CharField(max_length=32)
    used_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.player} used {self.pack_type} at {self.used_at}"

    class Meta:
        db_table = "economy_shoppackuse"
