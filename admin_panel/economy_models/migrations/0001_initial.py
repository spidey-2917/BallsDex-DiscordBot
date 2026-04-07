from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("bd_models", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Wallet",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("coins", models.BigIntegerField(default=0)),
                (
                    "player",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="wallet",
                        to="bd_models.player",
                    ),
                ),
            ],
            options={
                "db_table": "economy_wallet",
            },
        ),
        migrations.CreateModel(
            name="PackClaim",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "pack_type",
                    models.CharField(
                        choices=[("daily", "Daily"), ("weekly", "Weekly")], max_length=16
                    ),
                ),
                ("claimed_at", models.DateTimeField(auto_now_add=True)),
                (
                    "player",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="pack_claims",
                        to="bd_models.player",
                    ),
                ),
            ],
            options={
                "db_table": "economy_packclaim",
            },
        ),
        migrations.CreateModel(
            name="ShopPackUse",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("pack_type", models.CharField(max_length=32)),
                ("used_at", models.DateTimeField(auto_now_add=True)),
                (
                    "player",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="shop_pack_uses",
                        to="bd_models.player",
                    ),
                ),
            ],
            options={
                "db_table": "economy_shoppackuse",
            },
        ),
    ]
