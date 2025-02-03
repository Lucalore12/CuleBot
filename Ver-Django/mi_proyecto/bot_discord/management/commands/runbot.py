# bot_discord/management/commands/runbot.py

from django.core.management.base import BaseCommand
from bot_discord.bot import bot
from django.conf import settings

class Command(BaseCommand):
    help = 'Ejecuta el bot de Discord'

    def handle(self, *args, **options):
        bot.run(settings.DISCORD_TOKEN)
