import os
import discord
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv("DISCORD_TOKEN")

CAPT_ROLE_IDS = {
    1374223820453580800, 1368922573315768332,
    1401988464144023676, 1469029533876224142,
    1511689439959847043, 910405176752492545,
}

APPLICATION_STAFF_ROLE_IDS = {
    1388962793042214942, 910407932200513556,
    1368922573315768332, 1374223820453580800,
    910405176752492545, 910406452114493442,
    1511689439959847043, 1469029533876224142,
    1401988464144023676,
}

ALLOWED_ROLE_IDS = APPLICATION_STAFF_ROLE_IDS
APPLICATION_CATEGORY_ID = 1365588391810564228
RESULTS_CHANNEL_ID = 1505995665069703178
PORTFOLIO_CATEGORY_ID = 1469758643544129690

PORTFOLIO_THREADS = [
    "📋・рп отчёты",
    "⚔️・арена",
    "🎥・откаты с компетитив",
    "💬・чат",
]

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

events = {}
plus_messages = {}
plus_threads = {}


def has_role(member, role_ids):
    return isinstance(member, discord.Member) and any(
        role.id in role_ids for role in member.roles
    )


def is_staff(member):
    return has_role(member, APPLICATION_STAFF_ROLE_IDS)


def get_channel(guild, channel_id, channel_type=None):
    channel = guild.get_channel(channel_id) if guild else None
    if channel_type is None or isinstance(channel, channel_type):
        return channel
    return None


async def deny(interaction, message="У вас нет прав."):
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)


class BaseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)


class ApplicationPanelView(BaseView):
    @discord.ui.button(
        label="Подать заявку",
        style=discord.ButtonStyle.primary,
        custom_id="application:open",
    )
    async def apply(self, interaction, button):
        await interaction.response.send_modal(ApplicationModal())


class PortfolioPanelView(BaseView):
    @discord.ui.button(
        label="Создать портфель",
        emoji="📁",
        style=discord.ButtonStyle.success,
        custom_id="portfolio:create",
    )
    async def create(self, interaction, button):
        await interaction.response.send_modal(PortfolioModal())


class ApplicationModal(discord.ui.Modal, title="Заявка"):
    nickname = discord.ui.TextInput(label="НИК | СТАТИК", max_length=100)
    families = discord.ui.TextInput(
        label="В каких семьях был",
        style=discord.TextStyle.paragraph,
        max_length=1000,
    )
    clips = discord.ui.TextInput(
        label="Скриншот персонажей",
        style=discord.TextStyle.paragraph,
        max_length=1000,
    )

    async def on_submit(self, interaction):
        guild = interaction.guild
        category = get_channel(
            guild, APPLICATION_CATEGORY_ID, discord.CategoryChannel
        )

        if not category:
            await deny(interaction, "Категория заявок не найдена.")
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
            ),
        }

        for role in guild.roles:
            if role.id in APPLICATION_STAFF_ROLE_IDS:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_messages=True,
                )

        try:
            channel = await guild.create_text_channel(
                name=f"заявка-{interaction.user.name}"[:100],
                category=category,
                overwrites=overwrites,
            )

            embed = discord.Embed(
                title="Новая заявка",
                color=discord.Color.blue(),
            )
            embed.add_field(
                name="Пользователь",
                value=interaction.user.mention,
                inline=False,
            )
            embed.add_field(
                name="НИК | СТАТИК",
                value=self.nickname.value,
                inline=False,
            )
            embed.add_field(
                name="В каких семьях был",
                value=self.families.value,
                inline=False,
            )
            embed.add_field(
                name="Скриншот персонажей",
                value=self.clips.value,
                inline=False,
            )

            await channel.send(
                embed=embed,
                view=ApplicationView(interaction.user.id),
            )
            await interaction.followup.send(
                f"Заявка создана: {channel.mention}",
                ephemeral=True,
            )
        except discord.HTTPException as error:
            await interaction.followup.send(
                f"Не удалось создать заявку: {error}",
                ephemeral=True,
            )

class RejectModal(discord.ui.Modal, title="Причина отказа"):
    reason = discord.ui.TextInput(
        label="Причина",
        style=discord.TextStyle.paragraph,
        max_length=1000,
    )

    def __init__(self, applicant_id):
        super().__init__()
        self.applicant_id = applicant_id

    async def on_submit(self, interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        applicant = guild.get_member(self.applicant_id) if guild else None

        if applicant:
            try:
                await applicant.send(
                    f"Ваша заявка отклонена.\nПричина: {self.reason.value}"
                )
            except discord.HTTPException:
                pass

        results = get_channel(guild, RESULTS_CHANNEL_ID, discord.TextChannel)
        if results:
            embed = discord.Embed(
                title="❌ Заявка отклонена",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow(),
            )
            embed.add_field(
                name="👤 Заявитель",
                value=applicant.mention if applicant else f"<@{self.applicant_id}>",
                inline=False,
            )
            embed.add_field(
                name="🛡️ Модератор",
                value=interaction.user.mention,
                inline=False,
            )
            embed.add_field(
                name="📝 Причина отказа",
                value=self.reason.value,
                inline=False,
            )
            embed.set_footer(text="Система рассмотрения заявок")
            await results.send(embed=embed)

        await interaction.followup.send("Заявка отклонена.", ephemeral=True)

        if interaction.channel:
            try:
                await interaction.channel.delete()
            except discord.HTTPException:
                pass


class ApplicationView(BaseView):
    def __init__(self, applicant_id):
        super().__init__()
        self.applicant_id = applicant_id

    async def interaction_check(self, interaction):
        if not is_staff(interaction.user):
            await deny(interaction)
            return False
        return True

    @discord.ui.button(label="Принять", emoji="✅", style=discord.ButtonStyle.success)
    async def accept(self, interaction, button):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        applicant = guild.get_member(self.applicant_id) if guild else None

        if applicant:
            try:
                await applicant.send("✅ Ваша заявка принята!")
            except discord.HTTPException:
                pass

        results = get_channel(guild, RESULTS_CHANNEL_ID, discord.TextChannel)
        if results:
            embed = discord.Embed(
                title="✅ Заявка принята",
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow(),
            )
            embed.add_field(
                name="👤 Заявитель",
                value=applicant.mention if applicant else f"<@{self.applicant_id}>",
                inline=False,
            )
            embed.add_field(
                name="🛡️ Модератор",
                value=interaction.user.mention,
                inline=False,
            )
            embed.set_footer(text="Система рассмотрения заявок")
            await results.send(embed=embed)

        await interaction.followup.send("Заявка принята.", ephemeral=True)

        if interaction.channel:
            try:
                await interaction.channel.delete()
            except discord.HTTPException:
                pass

    @discord.ui.button(label="Отклонить", emoji="❌", style=discord.ButtonStyle.danger)
    async def reject(self, interaction, button):
        await interaction.response.send_modal(RejectModal(self.applicant_id))

    @discord.ui.button(
        label="Вызвать на обзвон",
        emoji="📞",
        style=discord.ButtonStyle.primary,
    )
    async def call(self, interaction, button):
        guild = interaction.guild
        if not guild:
            await deny(interaction, "Сервер не найден.")
            return

        options = [
            discord.SelectOption(label=channel.name[:100], value=str(channel.id))
            for channel in guild.voice_channels[:25]
        ]

        if not options:
            await deny(interaction, "На сервере нет голосовых каналов.")
            return

        view = discord.ui.View(timeout=120)
        select = discord.ui.Select(
            placeholder="Выберите голосовой канал",
            options=options,
        )

        async def select_callback(select_interaction):
            voice = guild.get_channel(int(select.values[0]))
            applicant = guild.get_member(self.applicant_id)

            if applicant and isinstance(voice, discord.VoiceChannel):
                try:
                    await applicant.send(
                        f"📞 Вас вызывают на обзвон в голосовой канал **{voice.name}**."
                    )
                except discord.HTTPException:
                    pass

            await select_interaction.response.send_message(
                "Уведомление отправлено.",
                ephemeral=True,
            )

        select.callback = select_callback
        view.add_item(select)
        await interaction.response.send_message(
            "Выберите голосовой канал:",
            view=view,
            ephemeral=True,
        )

@bot.tree.command(name="zayavka", description="Создать панель подачи заявок")
async def zayavka(interaction):
    if not is_staff(interaction.user):
        await deny(interaction)
        return

    if not interaction.channel:
        await deny(interaction, "Канал не найден.")
        return

    embed = discord.Embed(
        title="Подача заявки",
        description="Нажмите кнопку ниже, чтобы подать заявку.",
        color=discord.Color.blue(),
    )
    await interaction.channel.send(embed=embed, view=ApplicationPanelView())
    await interaction.response.send_message("Панель создана.", ephemeral=True)


@bot.tree.command(name="plus", description="Создать PLUS")
@app_commands.describe(title="Название мероприятия", time="Время мероприятия")
async def plus(interaction, title: str, time: str):
    if not is_staff(interaction.user):
        await deny(interaction, "У вас нет прав на создание PLUS.")
        return

    if not isinstance(interaction.channel, discord.TextChannel):
        await deny(interaction, "Создавать PLUS можно только в текстовом канале.")
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        embed = discord.Embed(
            description=(
                f"> **Мероприятие:** {title}\n"
                f">\n> **Время:** {time}\n\n"
                f"**Основа**\nПока никого нет.\n\n"
                f"**Замены**\nЗамены отсутствуют."
            ),
            color=discord.Color.blue(),
        )

        message = await interaction.channel.send(embed=embed)
        thread = await message.create_thread(
            name=f"{title} | {time}"[:100],
            auto_archive_duration=1440,
        )
        await thread.send(
            "Для записи отправьте сообщение с `+`, затем поставьте реакцию:\n"
            "✅ — Основа\n🕐 — Замены"
        )

        events[message.id] = {
            "message": message,
            "thread": thread,
            "title": title,
            "time": time,
            "joined": {},
            "replacements": {},
        }
        plus_threads[thread.id] = message.id

        await interaction.followup.send(
            f"✅ PLUS создан: {title} | {time}\n{thread.mention}",
            ephemeral=True,
        )
    except discord.HTTPException as error:
        await interaction.followup.send(
            f"Не удалось создать PLUS: {error}",
            ephemeral=True,
        )


async def update_plus(message_id):
    event = events.get(message_id)
    if not event:
        return

    joined = "\n".join(
        f"{i}. <@{uid}>"
        for i, uid in enumerate(event["joined"], 1)
    ) or "Пока никого нет."

    replacements = "\n".join(
        f"{i}. <@{uid}>"
        for i, uid in enumerate(event["replacements"], 1)
    ) or "Замены отсутствуют."

    embed = discord.Embed(
        description=(
            f"> **Мероприятие:** {event['title']}\n"
            f">\n> **Время:** {event['time']}\n\n"
            f"**Основа**\n{joined}\n\n"
            f"**Замены**\n{replacements}"
        ),
        color=discord.Color.blue(),
    )

    try:
        await event["message"].edit(embed=embed)
    except discord.HTTPException:
        pass


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if (
        message.content.strip() == "+"
        and isinstance(message.channel, discord.Thread)
        and message.channel.id in plus_threads
    ):
        plus_messages[message.id] = message.author.id

    await bot.process_commands(message)


async def handle_plus_reaction(payload, adding):
    target_user_id = plus_messages.get(payload.message_id)
    if target_user_id is None:
        return

    event_id = plus_threads.get(payload.channel_id)
    if event_id not in events:
        return

    emoji = str(payload.emoji)
    if emoji not in {"✅", "🕐"}:
        return

    guild = bot.get_guild(payload.guild_id)
    member = guild.get_member(payload.user_id) if guild else None

    if not has_role(member, CAPT_ROLE_IDS):
        return

    event = events[event_id]

    if emoji == "✅":
        selected, other = event["joined"], event["replacements"]
    else:
        selected, other = event["replacements"], event["joined"]

    if adding:
        other.pop(target_user_id, None)
        selected[target_user_id] = True
    else:
        selected.pop(target_user_id, None)

    await update_plus(event_id)


@bot.event
async def on_raw_reaction_add(payload):
    if bot.user and payload.user_id == bot.user.id:
        return
    await handle_plus_reaction(payload, True)


@bot.event
async def on_raw_reaction_remove(payload):
    await handle_plus_reaction(payload, False)


async def create_portfolio_for(guild, user, nickname=None, static=None):
    if guild is None:
        raise ValueError("Сервер не найден.")

    category = get_channel(guild, PORTFOLIO_CATEGORY_ID, discord.CategoryChannel)
    if not category:
        raise ValueError("Категория портфелей не найдена.")

    existing = next(
        (
            channel for channel in category.text_channels
            if channel.topic and f"PORTFOLIO_OWNER:{user.id}" in channel.topic
        ),
        None,
    )
    if existing:
        return existing, []

    portfolio_name = (
        f"{nickname.strip()}-{static.strip()}"
        if nickname and static
        else user.display_name
    )

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            create_public_threads=True,
            send_messages_in_threads=True,
        ),
    }

    for role in guild.roles:
        if role.id in ALLOWED_ROLE_IDS:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                manage_messages=True,
                manage_threads=True,
                send_messages_in_threads=True,
            )

    if guild.me:
        overwrites[guild.me] = discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            manage_channels=True,
            manage_threads=True,
            create_public_threads=True,
            send_messages_in_threads=True,
        )

    channel = await guild.create_text_channel(
        name=f"📁・{portfolio_name}"[:100],
        category=category,
        overwrites=overwrites,
        topic=(
            f"PORTFOLIO_OWNER:{user.id} | "
            f"НИК: {nickname or user.display_name} | "
            f"СТАТИК: {static or 'не указан'}"
        ),
        reason=f"Портфель для {user}",
    )

    created_threads = []

    try:
        for name in PORTFOLIO_THREADS:
            starter = await channel.send(f"Ветка **{name}**.")
            thread = await starter.create_thread(
                name=name,
                auto_archive_duration=1440,
            )
            created_threads.append(thread)
    except discord.HTTPException:
        for thread in created_threads:
            try:
                await thread.delete()
            except discord.HTTPException:
                pass
        try:
            await channel.delete()
        except discord.HTTPException:
            pass
        raise

    return channel, created_threads


class PortfolioModal(discord.ui.Modal, title="Создание портфеля"):
    nickname = discord.ui.TextInput(
        label="Игровой ник",
        placeholder="Введите ник",
        max_length=32,
    )
    static = discord.ui.TextInput(
        label="Статик",
        placeholder="Введите статик",
        max_length=20,
    )

    async def on_submit(self, interaction):
        if not interaction.guild:
            await deny(interaction, "Форма доступна только на сервере.")
            return

        nickname = self.nickname.value.strip()
        static = self.static.value.strip()

        if not nickname or not static:
            await deny(interaction, "Заполните ник и статик.")
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        try:
            channel, created = await create_portfolio_for(
                interaction.guild,
                interaction.user,
                nickname,
                static,
            )

            if not created:
                await interaction.followup.send(
                    f"У тебя уже есть портфель: {channel.mention}",
                    ephemeral=True,
                )
                return

            await interaction.followup.send(
                f"✅ Портфель создан: {channel.mention}\n"
                + "\n".join(thread.mention for thread in created),
                ephemeral=True,
            )
        except (discord.HTTPException, ValueError) as error:
            await interaction.followup.send(
                f"Не удалось создать портфель: {error}",
                ephemeral=True,
            )


@bot.tree.command(name="setup", description="Создать панель портфелей")
async def setup_portfolio(interaction):
    if not is_staff(interaction.user):
        await deny(interaction)
        return

    if not interaction.channel:
        await deny(interaction, "Канал не найден.")
        return

    embed = discord.Embed(
        title="Портфолио",
        description="Нажмите кнопку ниже, чтобы создать портфель.",
        color=discord.Color.blue(),
    )
    await interaction.channel.send(embed=embed, view=PortfolioPanelView())
    await interaction.response.send_message(
        "Панель портфелей создана.",
        ephemeral=True,
    )


@bot.tree.command(
    name="create_portfolio",
    description="Создать портфель пользователю",
)
@app_commands.describe(user="Пользователь, которому создаётся портфель")
async def create_portfolio_command(interaction, user: discord.Member):
    if not is_staff(interaction.user):
        await deny(interaction)
        return

    await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        channel, created = await create_portfolio_for(
            interaction.guild, user
        )

        if not created:
            await interaction.followup.send(
                f"У {user.mention} уже есть портфель: {channel.mention}",
                ephemeral=True,
            )
            return

        await interaction.followup.send(
            f"Портфель для {user.mention}: {channel.mention}\n"
            + "\n".join(thread.mention for thread in created),
            ephemeral=True,
        )
    except (discord.HTTPException, ValueError) as error:
        await interaction.followup.send(
            f"Не удалось создать портфель: {error}",
            ephemeral=True,
        )


async def main():
    if not TOKEN:
        raise RuntimeError(
            "Добавь токен бота в переменную окружения DISCORD_TOKEN."
        )

    async with bot:
        bot.add_view(ApplicationPanelView())
        bot.add_view(PortfolioPanelView())
        await bot.start(TOKEN)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
