import os
import threading
import time
import asyncio
import discord
from discord.ext import commands
from discord import app_commands
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

# Cargar variables del entorno de forma segura
load_dotenv()  

# Servidor web para mantener el bot activo 24/7
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive and running!")

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

server_thread = threading.Thread(target=run_server, daemon=True)
server_thread.start()

# Intents necesarios
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
intents.presences = True  
intents.invites = True  

class UltimateBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.invites_cache = {}

    async def setup_hook(self):
        self.add_view(TicketButtonsView())
        self.add_view(PostulacionStaffView())
        self.add_view(PostulacionStreamerView())
        self.add_view(FaccionesSelectView())
        await self.tree.sync()
        print("¡Comandos de barra sincronizados y vistas cargadas con éxito!")

bot = UltimateBot()

@bot.event
async def on_ready():
    print(f"¡Conectado como {bot.user}!")
    for guild in bot.guilds:
        try:
            bot.invites_cache[guild.id] = {invite.code: invite.uses for invite in await guild.invites()}
        except Exception as e:
            print(f"No se pudieron cargar invites en {guild.name}: {e}")


# ==========================================
# CACHÉ DE INVITES EN TIEMPO REAL
# ==========================================
@bot.event
async def on_invite_create(invite):
    if invite.guild.id not in bot.invites_cache:
        bot.invites_cache[invite.guild.id] = {}
    bot.invites_cache[invite.guild.id][invite.code] = invite.uses

@bot.event
async def on_invite_delete(invite):
    if invite.guild.id in bot.invites_cache:
        bot.invites_cache[invite.guild.id].pop(invite.code, None)


# ==========================================
# 1. SISTEMA DE BIENVENIDA E INVITES UNIFICADO
# ==========================================
bienvenidas_recientes = {}

@bot.event
async def on_member_join(member: discord.Member):
    tiempo_actual = time.time()
    if member.id in bienvenidas_recientes and tiempo_actual - bienvenidas_recientes[member.id] < 10:
        return
    bienvenidas_recientes[member.id] = tiempo_actual

    CANAL_BIENVENIDA_ID = 1555483618158059622  
    ROL_CIVIL_ID = 1555483327010578452         
    CANAL_INVITES_ID = 1556075158383632475

    guild = member.guild
    
    rol_civil = guild.get_role(ROL_CIVIL_ID)
    if rol_civil:
        try:
            if rol_civil not in member.roles:
                await member.add_roles(rol_civil)
        except Exception as e:
            print(f"Error al asignar rol civil: {e}")

    channel_bienvenida = guild.get_channel(CANAL_BIENVENIDA_ID)
    if channel_bienvenida:
        total_miembros = guild.member_count
        created_at = member.created_at.strftime("%d/%m/%Y %H:%M")

        embed = discord.Embed(
            title=f"¡Bienvenido a Zona Roja RP!",
            description=f"¡Hola {member.mention}, estamos emocionados de tenerte acá!",
            color=discord.Color.from_rgb(255, 0, 0)
        )
        embed.add_field(name="👤 Usuario", value=member.name, inline=True)
        embed.add_field(name="🆔 ID", value=str(member.id), inline=True)
        embed.add_field(name="📅 Cuenta creada", value=created_at, inline=False)
        
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        else:
            embed.set_thumbnail(url=member.default_avatar.url)

        embed.set_footer(text=f"¡Ahora somos {total_miembros} miembros! • Zona Roja RP")
        await channel_bienvenida.send(content=f"{member.mention}", embed=embed)

    channel_invites = guild.get_channel(CANAL_INVITES_ID)
    if channel_invites:
        inviter_text = "-"
        try:
            old_invites = bot.invites_cache.get(guild.id, {})
            new_invites = await guild.invites()
            bot.invites_cache[guild.id] = {invite.code: invite.uses for invite in new_invites}

            for new_invite in new_invites:
                code = new_invite.code
                if code in old_invites:
                    if new_invite.uses > old_invites[code]:
                        if new_invite.inviter:
                            inviter_text = f"{new_invite.inviter.mention}"
                        break
        except Exception as e:
            print(f"Error rastreando invites: {e}")

        embed_invite = discord.Embed(
            description=f"{member.mention} se unió al servidor.",
            color=discord.Color.from_rgb(43, 45, 49)
        )
        embed_invite.set_author(name=member.name, icon_url=member.display_avatar.url)
        embed_invite.add_field(name="🎫 Invites del invitador", value=inviter_text, inline=True)
        embed_invite.add_field(name="👥 Miembros actuales", value=str(guild.member_count), inline=True)
        embed_invite.set_footer(text=f"Zona Roja RP • Invitaciones")
        embed_invite.timestamp = discord.utils.utcnow()

        await channel_invites.send(embed=embed_invite)


# ==========================================
# 2. SISTEMA DE SUGERENCIAS AUTOMÁTICAS
# ==========================================
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or not message.guild:
        return

    CANAL_SUGERENCIAS_ID = 1555501754651516979  

    if message.channel.id == CANAL_SUGERENCIAS_ID:
        try:
            await message.delete()
        except Exception as e:
            print(f"No se pudo borrar sugerencia: {e}")

        embed = discord.Embed(
            title="Nueva Sugerencia:",
            description=message.content,
            color=discord.Color.from_rgb(0, 229, 255)
        )
        
        if message.author.avatar:
            embed.set_author(name=message.author.name, icon_url=message.author.avatar.url)
        else:
            embed.set_author(name=message.author.name)

        embed.set_footer(text=f"{message.created_at.strftime('%d/%m/%Y %H:%M')} • Zona Roja RP")
        sug_message = await message.channel.send(embed=embed)
        await sug_message.add_reaction("✅")
        await sug_message.add_reaction("❌")

    await bot.process_commands(message)


# ==========================================
# 3. SISTEMA DE TICKETS
# ==========================================
class TicketButtonsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) 

    async def crear_ticket(self, interaction: discord.Interaction, categoria: str, emoji: str):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        member = interaction.user
        ROL_STAFF_ID = 1555486535657193582  
        rol_staff = guild.get_role(ROL_STAFF_ID)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }
        if rol_staff:
            overwrites[rol_staff] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        ticket_channel = await guild.create_text_channel(
            name=f"ticket-{categoria}-{member.name}",
            overwrites=overwrites,
            topic=f"Ticket de {categoria} abierto por {member.name}"
        )

        mencion_staff = rol_staff.mention if rol_staff else "@Staff"
        embed_ticket = discord.Embed(
            title=f"{emoji} Ticket de {categoria.capitalize()}",
            description=f"¡Hola {member.mention}!\nHas abierto un ticket de **{categoria}**.\n\nUn miembro de {mencion_staff} te atenderá lo más rápido posible. Por favor, describe tu consulta o inconveniente detalladamente.",
            color=discord.Color.from_rgb(255, 0, 0)
        )
        embed_ticket.set_footer(text="Zona Roja RP • Sistema de Tickets")

        class CloseTicketView(discord.ui.View):
            @discord.ui.button(label="Cerrar Ticket", style=discord.ButtonStyle.danger, emoji="🔒")
            async def cerrar(self, inter: discord.Interaction, button: discord.ui.Button):
                await inter.response.send_message("🔒 Cerrando canal en 5 segundos...")
                import asyncio
                await asyncio.sleep(5)
                await inter.channel.delete()

        await ticket_channel.send(content=f"{member.mention} {mencion_staff}", embed=embed_ticket, view=CloseTicketView())
        await interaction.followup.send(f"✅ ¡Tu ticket ha sido creado con éxito! Dirígete a {ticket_channel.mention}", ephemeral=True)

    @discord.ui.button(label="Dudas", style=discord.ButtonStyle.primary, emoji="👤", custom_id="ticket_dudas_zr")
    async def dudas_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.crear_ticket(interaction, "dudas", "👤")

    @discord.ui.button(label="Reportes", style=discord.ButtonStyle.danger, emoji="🚨", custom_id="ticket_reportes_zr")
    async def reportes_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.crear_ticket(interaction, "reportes", "🚨")

    @discord.ui.button(label="Apelar", style=discord.ButtonStyle.secondary, emoji="📋", custom_id="ticket_apelar_zr")
    async def apelar_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.crear_ticket(interaction, "apelar", "📋")

    @discord.ui.button(label="Donar", style=discord.ButtonStyle.success, emoji="💳", custom_id="ticket_donar_zr")
    async def donar_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.crear_ticket(interaction, "donaciones", "💳")

    @discord.ui.button(label="Streamer", style=discord.ButtonStyle.primary, emoji="📺", custom_id="ticket_streamer_zr")
    async def streamer_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.crear_ticket(interaction, "streamer", "📺")

    @discord.ui.button(label="Tienda", style=discord.ButtonStyle.blurple, emoji="🛒", custom_id="ticket_tienda_zr")
    async def tienda_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.crear_ticket(interaction, "tienda", "🛒")

@bot.tree.command(name="setup-tickets", description="Envía el panel de tickets oficial")
@app_commands.checks.has_permissions(administrator=True)
async def setup_tickets(interaction: discord.Interaction):
    await interaction.response.send_message("⚙ Generando panel de tickets...", ephemeral=True)
    embed = discord.Embed(
        title="Soporte Técnico de Zona Roja RP",
        description="❓ **¿Necesitas ayuda?**\nSi necesitas ayuda, solo abrí ticket y nuestro Staff te asistirá lo más rápido posible.",
        color=discord.Color.from_rgb(255, 0, 0)
    )
    await interaction.channel.send(embed=embed, view=TicketButtonsView())


# ==========================================
# 4. SISTEMA DE POSTULACIONES
# ==========================================
class DecisionReviewView(discord.ui.View):
    def __init__(self, postulante: discord.User, tipo: str):
        super().__init__(timeout=None)
        self.postulante = postulante
        self.tipo = tipo

    @discord.ui.button(label="Aceptar", style=discord.ButtonStyle.success, emoji="✅", custom_id="post_aceptar")
    async def aceptar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        for i, field in enumerate(embed.fields):
            if "Estado" in field.name:
                embed.set_field_at(i, name="⏳ Estado", value=f"✅ Aceptado por {interaction.user.name}", inline=False)
                break
        await interaction.message.edit(embed=embed, view=self)
        try:
            await self.postulante.send(f"🎉 ¡Felicidades! Tu postulación a **{self.tipo}** ha sido **APROBADA**. Abre ticket en el servidor para continuar.")
        except Exception as e:
            print(f"Error MD: {e}")

    @discord.ui.button(label="Rechazar", style=discord.ButtonStyle.danger, emoji="❌", custom_id="post_rechazar")
    async def rechazar(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        for item in self.children:
            item.disabled = True
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        for i, field in enumerate(embed.fields):
            if "Estado" in field.name:
                embed.set_field_at(i, name="⏳ Estado", value=f"❌ Rechazado por {interaction.user.name}", inline=False)
                break
        await interaction.message.edit(embed=embed, view=self)
        try:
            await self.postulante.send(f"❌ Hola, tu postulación a **{self.tipo}** ha sido **rechazada** en esta ocasión. ¡Gracias por participar!")
        except Exception as e:
            print(f"Error MD: {e}")


class StaffModal(discord.ui.Modal, title="Postulación al Staff"):
    nombre = discord.ui.TextInput(label="Nombre (OOC)", placeholder="Tu nombre real", required=True)
    edad = discord.ui.TextInput(label="Edad", placeholder="Ej: 18", required=True)
    pais = discord.ui.TextInput(label="País", placeholder="Ej: Argentina / Uruguay", required=True)
    sanciones = discord.ui.TextInput(label="¿Tenés sanciones previas?", placeholder="Ninguna / Detallar", required=True)
    motivacion = discord.ui.TextInput(label="Motivación y disponibilidad", style=discord.TextStyle.paragraph, placeholder="¿Por qué querés ser staff?", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        CANAL_REVISION_STAFF = 1556074505330491512 
        channel = interaction.guild.get_channel(CANAL_REVISION_STAFF)

        embed = discord.Embed(
            title="✉️ Postulación al Staff",
            description="Se registró una nueva postulación al Staff.",
            color=discord.Color.from_rgb(241, 196, 15)
        )
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="⏳ Estado", value="Pendiente de revisión", inline=False)
        embed.add_field(name="👤 Usuario", value=interaction.user.mention, inline=True)
        embed.add_field(name="🟡 Nombre (OOC)", value=self.nombre.value, inline=True)
        embed.add_field(name="🌍 País", value=self.pais.value, inline=True)
        embed.add_field(name="🎂 Edad", value=self.edad.value, inline=True)
        embed.add_field(name="⚖️ Sanciones", value=self.sanciones.value, inline=False)
        embed.add_field(name="💼 Motivación y disponibilidad", value=self.motivacion.value, inline=False)
        embed.set_footer(text=f"Zona Roja RP • ID: {interaction.user.id}")
        embed.timestamp = discord.utils.utcnow()

        if channel:
            await channel.send(embed=embed, view=DecisionReviewView(interaction.user, "Staff"))
        await interaction.response.send_message("✅ ¡Tu postulación ha sido enviada con éxito!", ephemeral=True)

class PostulacionStaffView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Postularse a Staff", style=discord.ButtonStyle.danger, emoji="🛡️", custom_id="btn_abrir_modal_staff")
    async def abrir_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(StaffModal())


class StreamerModal(discord.ui.Modal, title="Postulación a Streamer"):
    nombre = discord.ui.TextInput(label="Nombre y Canal", placeholder="Ej: Juan / twitch.tv/tu_canal", required=True)
    plataforma = discord.ui.TextInput(label="Plataforma principal", placeholder="Twitch / Kick / TikTok / YouTube", required=True)
    viewers = discord.ui.TextInput(label="Promedio de Viewers", placeholder="Ej: 15-20 viewers", required=True)
    horarios = discord.ui.TextInput(label="Días y Horarios de Directo", style=discord.TextStyle.paragraph, placeholder="¿Qué días streameas?", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        CANAL_REVISION_STREAMER = 1556074480835502132 
        channel = interaction.guild.get_channel(CANAL_REVISION_STREAMER)

        embed = discord.Embed(
            title="📺 Postulación a Streamer",
            description="Se registró una nueva postulación para Streamer.",
            color=discord.Color.from_rgb(241, 196, 15)
        )
        embed.set_author(name=interaction.user.name, icon_url=interaction.user.display_avatar.url)
        embed.add_field(name="⏳ Estado", value="Pendiente de revisión", inline=False)
        embed.add_field(name="👤 Usuario", value=interaction.user.mention, inline=True)
        embed.add_field(name="🔗 Canal", value=self.nombre.value, inline=True)
        embed.add_field(name="📱 Plataforma", value=self.plataforma.value, inline=True)
        embed.add_field(name="👥 Viewers Promedio", value=self.viewers.value, inline=True)
        embed.add_field(name="🕒 Horarios", value=self.horarios.value, inline=False)
        embed.set_footer(text=f"Zona Roja RP • ID: {interaction.user.id}")
        embed.timestamp = discord.utils.utcnow()

        if channel:
            await channel.send(embed=embed, view=DecisionReviewView(interaction.user, "Streamer"))
        await interaction.response.send_message("✅ ¡Tu postulación a Streamer fue enviada con éxito!", ephemeral=True)

class PostulacionStreamerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Postularse a Streamer", style=discord.ButtonStyle.primary, emoji="🎥", custom_id="btn_abrir_modal_streamer")
    async def abrir_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(StreamerModal())


# ==========================================
# 5. SISTEMA DE FACCIONES
# ==========================================
class FaccionesSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Mafias", description="Organizaciones criminales.", emoji="🔫"),
            discord.SelectOption(label="PFA", description="Policía Federal Argentina.", emoji="👮"),
            discord.SelectOption(label="PROSEGUR", description="Seguridad privada.", emoji="🛡️"),
            discord.SelectOption(label="SAME", description="Atención médica de emergencias.", emoji="🚑")
        ]
        super().__init__(placeholder="Seleccioná una facción...", min_values=1, max_values=1, options=options, custom_id="select_facciones")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"✅ Has seleccionado: **{self.values[0]}**.", ephemeral=True)

class FaccionesSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(FaccionesSelect())

@bot.tree.command(name="facciones", description="Envía el panel oficial de Facciones")
@app_commands.checks.has_permissions(administrator=True)
async def cmd_facciones(interaction: discord.Interaction):
    await interaction.response.send_message("⚙ Generando panel...", ephemeral=True)
    embed = discord.Embed(
        title="💀 Panel de Facciones — Zona Roja RP",
        description="🏙️ **¡Bienvenido al panel oficial de Facciones!**\n👇 Seleccioná la que te interese en el menú de abajo.",
        color=discord.Color.from_rgb(0, 229, 255)
    )
    await interaction.channel.send(embed=embed, view=FaccionesSelectView())


# ==========================================
# 6. SISTEMA DE ENCUESTAS AVANZADO CON TIEMPO
# ==========================================
class EncuestaVotoView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.votos_si = set()
        self.votos_no = set()

    @discord.ui.button(label="SI", style=discord.ButtonStyle.success, emoji="✅", custom_id="encuesta_si")
    async def votar_si(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        if user_id in self.votos_no:
            self.votos_no.remove(user_id)
        if user_id in self.votos_si:
            self.votos_si.remove(user_id)
            await interaction.response.send_message("❌ Has retirado tu voto.", ephemeral=True)
        else:
            self.votos_si.add(user_id)
            await interaction.response.send_message("✅ ¡Has votado **SI**!", ephemeral=True)

    @discord.ui.button(label="NO", style=discord.ButtonStyle.danger, emoji="❌", custom_id="encuesta_no")
    async def votar_no(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        if user_id in self.votos_si:
            self.votos_si.remove(user_id)
        if user_id in self.votos_no:
            self.votos_no.remove(user_id)
            await interaction.response.send_message("❌ Has retirado tu voto.", ephemeral=True)
        else:
            self.votos_no.add(user_id)
            await interaction.response.send_message("✅ ¡Has votado **NO**!", ephemeral=True)


class EncuestaModal(discord.ui.Modal, title="Crear Encuesta"):
    pregunta = discord.ui.TextInput(label="Pregunta de la encuesta", placeholder="¿Estás de acuerdo con la regla?", required=True)
    minutos = discord.ui.TextInput(label="Duración (en minutos)", placeholder="Ej: 2", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            duracion = int(self.minutos.value)
        except ValueError:
            await interaction.response.send_message("❌ Debes ingresar un número válido de minutos.", ephemeral=True)
            return

        await interaction.response.send_message(f"✅ Encuesta creada con éxito. Durará {duracion} minutos.", ephemeral=True)

        view = EncuestaVotoView()
        embed = discord.Embed(
            title="📊 Encuesta Oficial",
            description=f"**{self.pregunta.value}**\n\n⏱️ Tiempo restante: **{duracion} minuto(s)**",
            color=discord.Color.from_rgb(255, 215, 0)
        )
        embed.set_footer(text=f"Creado por {interaction.user.name}")
        
        mensaje = await interaction.channel.send(content="@everyone", embed=embed, view=view)

        await asyncio.sleep(duracion * 60)

        for child in view.children:
            child.disabled = True

        total_si = len(view.votos_si)
        total_no = len(view.votos_no)
        total_votos = total_si + total_no

        if total_votos > 0:
            porc_si = int((total_si / total_votos) * 100)
            porc_no = int((total_no / total_votos) * 100)
        else:
            porc_si, porc_no = 0, 0

        if total_si > total_no:
            ganador = "🏆 Ganador: **SI**"
        elif total_no > total_si:
            ganador = "🏆 Ganador: **NO**"
        else:
            ganador = "🤝 Resultado: **Empate**"

        embed_final = discord.Embed(
            title="📊 Encuesta Finalizada",
            description=f"**{self.pregunta.value}**\n\n{ganador}\n\n✅ **SI:** {total_si} votos ({porc_si}%)\n❌ **NO:** {total_no} votos ({porc_no}%)",
            color=discord.Color.from_rgb(0, 255, 127)
        )
        embed_final.set_footer(text="Encuesta finalizada")

        try:
            await mensaje.edit(embed=embed_final, view=view)
        except Exception as e:
            print(f"Error al editar encuesta final: {e}")

@bot.tree.command(name="encuesta", description="Crea una encuesta interactiva con tiempo personalizado")
@app_commands.checks.has_permissions(administrator=True)
async def cmd_encuesta(interaction: discord.Interaction):
    await interaction.response.send_modal(EncuestaModal())


# ==========================================
# 7. COMANDOS /block Y /unblock (Rol Civil)
# ==========================================
@bot.tree.command(name="block", description="Bloquea el canal actual para que el Rol Civil no pueda escribir")
@app_commands.checks.has_permissions(administrator=True)
async def cmd_block(interaction: discord.Interaction):
    canal = interaction.channel
    ROL_CIVIL_ID = 1555483327010578452
    rol_civil = interaction.guild.get_role(ROL_CIVIL_ID)

    if not rol_civil:
        await interaction.response.send_message("❌ No se encontró el Rol Civil configurado en el servidor.", ephemeral=True)
        return

    try:
        await canal.set_permissions(rol_civil, send_messages=False)
        await interaction.response.send_message("🔒 **Canal bloqueado para Civiles.** Ya no pueden enviar mensajes aquí.", ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error al bloquear el canal: {e}", ephemeral=True)

@bot.tree.command(name="unblock", description="Desbloquea el canal actual para que el Rol Civil vuelva a escribir")
@app_commands.checks.has_permissions(administrator=True)
async def cmd_unblock(interaction: discord.Interaction):
    canal = interaction.channel
    ROL_CIVIL_ID = 1555483327010578452
    rol_civil = interaction.guild.get_role(ROL_CIVIL_ID)

    if not rol_civil:
        await interaction.response.send_message("❌ No se encontró el Rol Civil configurado en el servidor.", ephemeral=True)
        return

    try:
        await canal.set_permissions(rol_civil, send_messages=True)
        await interaction.response.send_message("🔓 **Canal desbloqueado para Civiles.** Pueden volver a escribir.", ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f"❌ Error al desbloquear el canal: {e}", ephemeral=True)


# ==========================================
# 8. COMANDOS DE BARRA DE POSTULACIONES
# ==========================================
@bot.tree.command(name="staff", description="Envía el panel oficial para postularse a Staff")
@app_commands.checks.has_permissions(administrator=True)
async def cmd_staff(interaction: discord.Interaction):
    await interaction.response.send_message("⚙ Generando panel...", ephemeral=True)
    embed = discord.Embed(title="Postulaciones - Staff", description="Haz clic abajo para postularte.", color=discord.Color.red())
    await interaction.channel.send(embed=embed, view=PostulacionStaffView())

@bot.tree.command(name="streamers", description="Envía el panel oficial para postularse a Streamer")
@app_commands.checks.has_permissions(administrator=True)
async def cmd_streamers(interaction: discord.Interaction):
    await interaction.response.send_message("⚙ Generando panel...", ephemeral=True)
    embed = discord.Embed(title="Postulaciones - Streamers", description="Haz clic abajo para postularte.", color=discord.Color.gold())
    await interaction.channel.send(embed=embed, view=PostulacionStreamerView())


# ==========================================
# 9. SISTEMA DE STREAM MANUAL (/vivo)
# ==========================================
class CerrarStreamView(discord.ui.View):
    def __init__(self, streamer: discord.Member, start_time: float, plataforma: str, link: str):
        super().__init__(timeout=None)
        self.streamer = streamer
        self.start_time = start_time
        self.plataforma = plataforma
        self.link = link

    @discord.ui.button(label="Cerrar Directo", style=discord.ButtonStyle.danger, emoji="🔴", custom_id="btn_cerrar_stream")
    async def cerrar_stream(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.streamer.id and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Solo el streamer que inició el directo puede cerrarlo.", ephemeral=True)
            return

        await interaction.response.defer()

        diff_ms = (time.time() - self.start_time) * 1000
        minutes = int((diff_ms / (1000 * 60)) % 60)
        hours = int(diff_ms / (1000 * 60 * 60))
        duration_text = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

        for item in self.children:
            item.disabled = True

        embed = discord.Embed(
            title=f"🟢 {self.plataforma} | STREAM FINALIZADO",
            description=f"[Zona Roja Stream] Sistema\n**{self.streamer.name}** finalizó su transmisión en {self.plataforma}.",
            color=discord.Color.from_rgb(43, 45, 49)
        )
        embed.add_field(name="Streamer", value=self.streamer.name, inline=True)
        embed.add_field(name="Plataforma", value=self.plataforma, inline=True)
        embed.add_field(name="Usuario", value=f"@{self.streamer.name}", inline=True)
        embed.add_field(name="Estado", value="⚫ FINALIZADO", inline=True)
        embed.add_field(name="Servidor", value="Zona Roja RP", inline=True)
        embed.add_field(name="Canal", value=f"[Entrar al stream]({self.link})", inline=True)
        embed.add_field(name="Duración", value=duration_text, inline=False)
        embed.set_footer(text="Zona Roja RP | Sistema de Streamers")
        embed.timestamp = discord.utils.utcnow()

        try:
            await interaction.message.edit(embed=embed, view=self)
        except Exception as e:
            print(f"Error al editar mensaje de fin de stream: {e}")


class VivoModal(discord.ui.Modal, title="Notificar Transmisión en Vivo"):
    plataforma = discord.ui.TextInput(label="Plataforma", placeholder="Twitch / Kick / YouTube / TikTok", required=True)
    link = discord.ui.TextInput(label="Enlace del directo", placeholder="https://twitch.tv/tu_canal", required=True)

    async def on_submit(self, interaction: discord.Interaction):
        CANAL_STREAMERS_ID = 1555483618158059622  
        channel = interaction.guild.get_channel(CANAL_STREAMERS_ID)
        if not channel:
            await interaction.response.send_message("❌ No se encontró el canal de streamers configurado.", ephemeral=True)
            return

        start_time = time.time()
        view = CerrarStreamView(interaction.user, start_time, self.plataforma.value, self.link.value)

        embed = discord.Embed(
            title=f"🟢 {self.plataforma.value} | EN VIVO",
            description=f"[Zona Roja Stream] Sistema\n**{interaction.user.name}** prendió stream en {self.plataforma.value} como @{interaction.user.name}. Entrá a verlo desde el enlace de este embed.",
            color=discord.Color.from_rgb(145, 70, 255) 
        )
        embed.add_field(name="Streamer", value=interaction.user.name, inline=True)
        embed.add_field(name="Plataforma", value=self.plataforma.value, inline=True)
        embed.add_field(name="Usuario", value=f"@{interaction.user.name}", inline=True)
        embed.add_field(name="Estado", value="🔴 EN VIVO", inline=True)
        embed.add_field(name="Servidor", value="Zona Roja RP", inline=True)
        embed.add_field(name="Canal", value=f"[Entrar al stream]({self.link.value})", inline=True)
        embed.set_footer(text="Zona Roja RP | Sistema de Streamers")
        embed.timestamp = discord.utils.utcnow()

        await channel.send(content=f"{interaction.user.mention} ¡Está en directo!", embed=embed, view=view)
        await interaction.response.send_message("✅ ¡Tu directo ha sido notificado con éxito en el canal de streamers!", ephemeral=True)


@bot.tree.command(name="vivo", description="Inicia un aviso de directo (Exclusivo para Streamers)")
async def cmd_vivo(interaction: discord.Interaction):
    ROL_STREAMER_ID = 1556078994804314123
    role = interaction.guild.get_role(ROL_STREAMER_ID)

    if not role or role not in interaction.user.roles:
        await interaction.response.send_message("❌ **No tienes permiso.** Este comando es exclusivo para usuarios con el rango de Streamer.", ephemeral=True)
        return

    await interaction.response.send_modal(VivoModal())


# ==========================================
# 10. INICIO DEL BOT
# ==========================================
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ ERROR CRÍTICO: No se encontró el token en el archivo .env.")
else:
    TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)