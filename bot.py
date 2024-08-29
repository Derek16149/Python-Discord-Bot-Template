import discord
from discord.ext import commands
from discord.ui import Button, View
from datetime import datetime
import asyncio


# Definisci i tuoi ID e il token
SERVER_ID = 1263427498914349087  # Sostituisci con l'ID del tuo server
MODMAIL_CATEGORY_ID = 1268149112948265021  # Sostituisci con l'ID della tua categoria ModMail
MODERATOR_ROLE_NAME = "Moderation Team"  # Nome del ruolo dei moderatori
TOKEN = os.getenv('DISCORD_TOKEN')  # Carica il token dal file .env
# Configura gli intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.dm_messages = True
intents.message_content = True

# Crea l'istanza del bot
bot = commands.Bot(command_prefix=":", intents=intents)

# Dizionario per memorizzare la lingua degli utenti
user_languages = {}

# Classe per i pulsanti di conferma
class ConfirmationView(View):
    def __init__(self, message):
        super().__init__()
        self.message = message
        self.language = user_languages.get(self.message.author.id, "English")
    
    @discord.ui.button(label="Conferma", style=discord.ButtonStyle.success, custom_id="confirm_ticket")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()  # Risposta deferita per evitare timeout

        guild = bot.get_guild(SERVER_ID)
        category = discord.utils.get(guild.categories, id=MODMAIL_CATEGORY_ID)
        
        # Crea un nuovo canale ModMail
        channel = await guild.create_text_channel(name=f'modmail-{self.message.author.id}', category=category)
        await channel.set_permissions(guild.default_role, read_messages=False)
        moderator_role = discord.utils.get(guild.roles, name=MODERATOR_ROLE_NAME)
        await channel.set_permissions(moderator_role, read_messages=True, send_messages=True)
        
        # Avviso iniziale con pulsanti
        embed = discord.Embed(
            title="New Ticket",
            description=f"Type a message in this channel to reply.\nUser: {self.message.author.mention}\nLanguage: {self.language}",
            color=0x00FF00  # Verde
        )
        view = ModMailView()
        await channel.send(embed=embed, view=view)
        print(f"Created new ModMail channel: {channel.name}")
        
        # Inoltra il messaggio dell'utente
        embed = discord.Embed(
            title="Message Received",
            description=self.message.content,
            color=0x00FF00  # Verde
        )
        avatar_url = self.message.author.avatar.url if self.message.author.avatar else None
        embed.set_author(name=f"{self.message.author} | {self.message.author.id}", icon_url=avatar_url)
        embed.set_footer(text=f"User Name: {self.message.author} • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        await channel.send(embed=embed)
        await self.message.add_reaction("✅")  # Aggiungi reazione ✅
        print(f"Message sent to channel {channel.name}")

        # Risposta automatica all'utente solo al primo messaggio
        try:
            await self.message.author.send(embed=discord.Embed(
                title="Message Sent",
                description=self.message.content,
                color=0xFF4500  # Arancione
            ).set_footer(text=f"Sent on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
            print(f"Sent notification to user {self.message.author.id}")
        except discord.Forbidden:
            print(f"Failed to send DM to user {self.message.author.id}: DM permissions are not allowed.")
        except discord.HTTPException as e:
            print(f"Failed to send DM to user {self.message.author.id}: HTTP Exception - {e}")
        except Exception as e:
            print(f"Failed to send DM to user {self.message.author.id}: {e}")

    @discord.ui.button(label="Annulla", style=discord.ButtonStyle.danger, custom_id="cancel_ticket")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Creazione del ticket annullata.", ephemeral=True)

# Classe per i pulsanti di ModMail
class ModMailView(View):
    def __init__(self):
        super().__init__()
        self.claimed = False  # Track if the ticket is claimed
        self.afk = False  # Track if the ticket is AFK

    @discord.ui.button(label="CLOSE", style=discord.ButtonStyle.danger, custom_id="close_ticket")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        if interaction.user.guild_permissions.manage_channels:
            # Informa l'utente del ticket
            user_id = int(channel.name.split('-')[1])
            user = await bot.fetch_user(user_id)
            if user:
                try:
                    # Messaggio di embed per chiudere il ticket
                    close_embed = discord.Embed(
                        title="Ticket Chiuso",
                        description="Il tuo ticket è stato chiuso. Grazie per averci contattato!",
                        color=0xFF0000  # Rosso
                    )
                    close_embed.set_footer(text="Grazie per aver utilizzato il nostro supporto.")
                    await user.send(embed=close_embed)
                except discord.Forbidden:
                    print(f"Failed to send DM to user {user_id}: DM permissions are not allowed.")
                except discord.HTTPException as e:
                    print(f"Failed to send DM to user {user_id}: HTTP Exception - {e}")

            # Crea un embed per il messaggio di chiusura nel canale
            embed = discord.Embed(
                title="Ticket Chiuso",
                description=f"Il tuo ticket è stato chiuso da {interaction.user.mention}.",
                color=0xFF0000  # Rosso
            )
            embed.set_footer(text="Grazie per aver utilizzato il nostro supporto.")
            
            # Invia il messaggio di chiusura e cancella il canale dopo 1 minuto
            await channel.send(embed=embed)
            await asyncio.sleep(60)
            await channel.delete()
            await interaction.response.send_message("Ticket chiuso.", ephemeral=True)
        else:
            await interaction.response.send_message("Non hai i permessi necessari per chiudere questo ticket.", ephemeral=True)

    @discord.ui.button(label="CLAIM", style=discord.ButtonStyle.primary, custom_id="claim_ticket")
    async def claim_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.claimed:
            await interaction.response.send_message("Questo ticket è già stato reclamato.", ephemeral=True)
            return

        channel = interaction.channel
        # Menziona il moderatore che ha reclamato il ticket
        embed = discord.Embed(
            title="Ticket Reclamato",
            description=f"Il ticket è stato reclamato da {interaction.user.mention}.",
            color=0x00FF00  # Verde
        )
        embed.set_footer(text=f"Reclaimed on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Informa l'utente del ticket
        user_id = int(channel.name.split('-')[1])
        user = await bot.fetch_user(user_id)
        if user:
            try:
                await user.send(embed=embed)
            except discord.Forbidden:
                print(f"Failed to send DM to user {user_id}: DM permissions are not allowed.")
            except discord.HTTPException as e:
                print(f"Failed to send DM to user {user_id}: HTTP Exception - {e}")

        await channel.send(embed=embed)
        await interaction.response.send_message("Ticket reclamato.", ephemeral=True)

        # Disabilita il bottone CLAIM
        self.claimed = True
        button.disabled = True
        await interaction.message.edit(view=self)

    @discord.ui.button(label="AFK", style=discord.ButtonStyle.secondary, custom_id="afk_ticket")
    async def afk_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.afk:
            await interaction.response.send_message("Il ticket è già in modalità AFK.", ephemeral=True)
            return
        
        self.afk = True
        button.disabled = True
        unafk_button = self.children[3]  # Ottiene il pulsante UNAFK
        unafk_button.disabled = False
        await interaction.message.edit(view=self)
        
        # Blocca l'invio di messaggi nel canale
        await interaction.channel.set_permissions(interaction.user, send_messages=False)
        
        # Informa l'utente del ticket
        embed = discord.Embed(
            title="Ticket in Attesa",
            description="Il tuo ticket è stato messo in attesa. Un moderatore arriverà al più presto.",
            color=0xFFFF00  # Giallo
        )
        embed.set_footer(text="Attendere che un moderatore ritorni per rispondere.")
        await interaction.user.send(embed=embed)
        await interaction.response.send_message("Ticket messo in attesa.", ephemeral=True)

    @discord.ui.button(label="UNAFK", style=discord.ButtonStyle.success, custom_id="unafk_ticket")
    async def unafk_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not self.afk:
            await interaction.response.send_message("Il ticket non è in modalità AFK.", ephemeral=True)
            return
        
        self.afk = False
        button.disabled = True
        afk_button = self.children[2]  # Ottiene il pulsante AFK
        afk_button.disabled = False
        await interaction.message.edit(view=self)
        
        # Rende di nuovo possibile inviare messaggi nel canale
        await interaction.channel.set_permissions(interaction.user, send_messages=True)
        
        # Informa l'utente del ticket
        embed = discord.Embed(
            title="Ticket Attivo",
            description="Il tuo ticket è stato rimesso in attività. Un moderatore sarà presto disponibile.",
            color=0xFFFF00  # Giallo
        )
        embed.set_footer(text="Grazie per la pazienza.")
        await interaction.user.send(embed=embed)
        await interaction.response.send_message("Ticket rimesso in attività.", ephemeral=True)

# Comando per cambiare lingua
@bot.command(name='changelanguage')
async def changelanguage(ctx):
    if isinstance(ctx.channel, discord.DMChannel):
        buttons = [
            Button(label="English", custom_id="language_english", style=discord.ButtonStyle.primary),
            Button(label="Español", custom_id="language_spanish", style=discord.ButtonStyle.secondary),
            Button(label="Italiano", custom_id="language_italian", style=discord.ButtonStyle.secondary)
        ]
        view = View()
        for button in buttons:
            view.add_item(button)
        await ctx.send("Please select your preferred language:", view=view)
    else:
        await ctx.send("This command can only be used in DMs.")

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        if interaction.custom_id.startswith("language_"):
            language = interaction.custom_id.split("_")[1]
            user_languages[interaction.user.id] = language
            await interaction.response.send_message(f"Language set to {language.capitalize()}.", ephemeral=True)
        elif interaction.custom_id == "confirm_ticket":
            view = ConfirmationView(interaction.message)
            await view.confirm_button(interaction, interaction.message)
        elif interaction.custom_id == "cancel_ticket":
            view = ConfirmationView(interaction.message)
            await view.cancel_button(interaction, interaction.message)

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        if message.content.lower() == "ticket":
            view = ConfirmationView(message)
            await message.channel.send("Are you sure you want to create a ticket?", view=view)
        return

bot.run(TOKEN)
