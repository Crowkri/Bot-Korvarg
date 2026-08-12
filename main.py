import discord
import os
from discord.ext import commands
from dotenv import load_dotenv

# --- 1. CONFIGURAZIONI INIZIALI ---
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# ID dei Canali
CANALE_BENVENUTO_ID = 1536818478957334699   # Canale pubblico per i saluti
CANALE_STATISTICHE_ID = 1536852580146086050 # Canale apposito (privato) dove inviare il resoconto

# ID dei Ruoli
RUOLO_AUTOMATICO_ID = 1536799610826391644   # Ruolo assegnato in automatico all'ingresso
RUOLI_AUTORIZZATI_STATS = ["Capocaccia", "Zanna"] # Chi può usare il comando !stats

# Ruoli selezionabili dall'utente in privato (Selezione Multipla abilitata)
RUOLI_CONFIGURATI = {
    "Scudo": 1536834140685602896,
    "Incantatore": 1536834251771871374,
    "Guaritore": 1536834300295520266,
    "Doppia_Spada": 1536834354943365120,
    "Armatura_Pesante": 1536834732229132478,
    "Lancia": 1536834733672108062,
    "Armatura_Leggera": 1536834823564296353,
    "Armi_a_Distanza": 1536838104009277521
}

# --- 2. SETUP INTENTI E BOT ---
intents = discord.Intents.default()
intents.members = True          
intents.message_content = True  

bot = commands.Bot(command_prefix='!', intents=intents)

# --- 3. CLASSI PER IL MENU INTERATTIVO IN DM ---
class MenuRuoli(discord.ui.Select):
    def __init__(self, bot_instance, guild_id, user_id):
        self.bot_instance = bot_instance
        self.guild_id = guild_id
        self.user_id = user_id
        
        opzioni = [
            discord.SelectOption(label=nome, description=f"Seleziona per ottenere il ruolo {nome}")
            for nome in RUOLI_CONFIGURATI.keys()
        ]
        
        super().__init__(
            placeholder="Scegli i tuoi ruoli nel server...", 
            min_values=1, 
            max_values=len(opzioni), # Permette la selezione multipla
            options=opzioni
        )

    async def callback(self, interaction: discord.Interaction):
        guild = self.bot_instance.get_guild(self.guild_id)
        member = guild.get_member(self.user_id)

        if not member:
            return await interaction.response.send_message("❌ Errore: Impossibile trovare il tuo profilo nel server.", ephemeral=True)

        ruoli_assegnati_nomi = []
        
        for ruolo_scelto in self.values:
            ruolo_id = RUOLI_CONFIGURATI[ruolo_scelto]
            ruolo_obj = guild.get_role(ruolo_id)
            
            if ruolo_obj:
                await member.add_roles(ruolo_obj)
                ruoli_assegnati_nomi.append(ruolo_scelto)
        
        if ruoli_assegnati_nomi:
            ruoli_formattati = ", ".join(f"**{nome}**" for nome in ruoli_assegnati_nomi)
            await interaction.response.send_message(f"✅ Ti sono stati assegnati i seguenti ruoli: {ruoli_formattati} nel server {guild.name}!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Errore durante l'assegnazione. Controlla gli ID.", ephemeral=True)

class VistaRuoli(discord.ui.View):
    def __init__(self, bot_instance, guild_id, user_id):
        super().__init__(timeout=None)
        self.add_item(MenuRuoli(bot_instance, guild_id, user_id))

# --- 3.1 FUNZIONI AUSILIARIE ---
def genera_barra(percentuale, lunghezza=10):
    """Crea una barra di progresso visiva in stile ASCII/Unicode."""
    blocchi_pieni = int(round((percentuale / 100) * lunghezza))
    blocchi_vuoti = lunghezza - blocchi_pieni
    return "█" * blocchi_pieni + "░" * blocchi_vuoti

# --- 4. EVENTI E COMANDI ---
@bot.event
async def on_ready():
    print(f'Bot {bot.user.name} online e pronto!')

@bot.event
async def on_member_join(member):
    # Azione 1: Assegnazione del ruolo automatico
    ruolo_auto = member.guild.get_role(RUOLO_AUTOMATICO_ID)
    if ruolo_auto:
        try:
            await member.add_roles(ruolo_auto)
        except discord.Forbidden:
            print(f"Errore permessi: Impossibile assegnare il ruolo automatico a {member.name}. Controlla la gerarchia ruoli.")

    # Azione 2: Saluto nel canale apposito
    canale_benvenuto = bot.get_channel(CANALE_BENVENUTO_ID)
    if canale_benvenuto:
        await canale_benvenuto.send(f"Benvenuto nel server, {member.mention}! Controlla i tuoi messaggi privati per scegliere i tuoi ruoli.")
    
    # Azione 3: Invia messaggio in privato con il menu
    try:
        messaggio_dm = f"Benvenuto in **{member.guild.name}**! Seleziona i ruoli che assumi all'interno del canale dal menu qui sotto:"
        vista = VistaRuoli(bot, member.guild.id, member.id)
        await member.send(messaggio_dm, view=vista)
    except discord.Forbidden:
        print(f"Impossibile inviare un DM a {member.name}.")

# Comando per le statistiche dei ruoli (Versione con Embed e Progress Bar)
@bot.command(name='stats')
@commands.has_any_role(*RUOLI_AUTORIZZATI_STATS)
async def statistiche_ruoli(ctx):
    guild = ctx.guild
    canale_stats = bot.get_channel(CANALE_STATISTICHE_ID)
    
    if not canale_stats:
        return await ctx.send("❌ Errore: Canale per le statistiche non trovato. Controlla l'ID nel codice.")
        
    totale_membri = guild.member_count
    if totale_membri == 0:
        return await ctx.send("Errore nel calcolo dei membri.")

    # 1. Calcolo degli utenti unici che possiedono almeno uno dei ruoli configurati
    membri_con_almeno_un_ruolo = set()
    totale_assegnazioni = 0

    for ruolo_id in RUOLI_CONFIGURATI.values():
        ruolo_obj = guild.get_role(ruolo_id)
        if ruolo_obj:
            for m in ruolo_obj.members:
                membri_con_almeno_un_ruolo.add(m.id)
                totale_assegnazioni += 1

    membri_configurati_count = len(membri_con_almeno_un_ruolo)
    media_ruoli = (totale_assegnazioni / membri_configurati_count) if membri_configurati_count > 0 else 0

    # 2. Creazione dell'Embed
    embed = discord.Embed(
        title="📊 Resoconto e Statistiche Ruoli",
        description=(
            f"**Totale Membri Server:** {totale_membri}\n"
            f"**Membri Configurati (almeno 1 ruolo):** {membri_configurati_count} ({(membri_configurati_count/totale_membri)*100:.1f}%)\n"
            f"**Media Ruoli per Utente:** {media_ruoli:.2f}\n"
            f"\n*Nota: Le percentuali sono calcolate sui {membri_configurati_count} utenti registrati.*"
        ),
        color=discord.Color.blue()
    )

    # 3. Formattazione di ciascun ruolo con Progress Bar
    testo_ruoli = ""
    for nome_ruolo, ruolo_id in RUOLI_CONFIGURATI.items():
        ruolo_obj = guild.get_role(ruolo_id)
        if ruolo_obj:
            count = len(ruolo_obj.members)
            pct_configurati = (count / membri_configurati_count * 100) if membri_configurati_count > 0 else 0
            
            barra = genera_barra(pct_configurati)
            nome_pulito = nome_ruolo.replace("_", " ")
            
            testo_ruoli += f"**{nome_pulito}**\n`{barra}` **{count}** ({pct_configurati:.1f}%)\n\n"
        else:
            testo_ruoli += f"**{nome_ruolo}**: *Ruolo non trovato*\n\n"

    embed.add_field(name="🛡️ Distribuzione Ruoli", value=testo_ruoli, inline=False)
    embed.set_footer(text="Bot Gestione Ruoli • Aggiornato")

    # Invia l'Embed nel canale dedicato
    await canale_stats.send(embed=embed)
    
    # Se il comando è stato scritto in un canale diverso, avvisa l'utente
    if ctx.channel.id != CANALE_STATISTICHE_ID:
        await ctx.send(f"✅ Le statistiche sono state inviate in {canale_stats.mention}.")

@statistiche_ruoli.error
async def statistiche_error(ctx, error):
    if isinstance(error, commands.MissingAnyRole):
        await ctx.send("❌ Non hai i permessi necessari per utilizzare questo comando.")

# --- 5. AVVIO DEL BOT ---
bot.run(TOKEN)