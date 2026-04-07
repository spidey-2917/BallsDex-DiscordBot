from django.contrib import admin

from .models import PackClaim, ShopPackUse, Wallet


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("player", "coins")
    search_fields = ("player__discord_id",)
    ordering = ("-coins",)


@admin.register(PackClaim)
class PackClaimAdmin(admin.ModelAdmin):
    list_display = ("player", "pack_type", "claimed_at")
    list_filter = ("pack_type",)
    search_fields = ("player__discord_id",)
    ordering = ("-claimed_at",)


@admin.register(ShopPackUse)
class ShopPackUseAdmin(admin.ModelAdmin):
    list_display = ("player", "pack_type", "used_at")
    list_filter = ("pack_type",)
    search_fields = ("player__discord_id",)
    ordering = ("-used_at",)
