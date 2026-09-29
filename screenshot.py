import telegram
import psutil
import asyncio
import os
import logging
import sys
import time
from html import escape
from telegram.error import BadRequest, NetworkError, RetryAfter
from dotenv import load_dotenv
from datetime import datetime, timedelta
import platform

# Load environment variables
load_dotenv()

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
PROCESS_FILTER = os.getenv('PROCESS_FILTER', 'NS')
SERVER_NAME = os.getenv('SERVER_NAME')

# Setup Logging
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    # HTTP request URLs contain the bot token; keep them out of INFO logs.
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.info("Logging initialized.")

def html_text(value):
    # Keep each dynamic field on one line and bound its size before escaping.
    text = ' '.join(str(value).splitlines())
    if len(text) > 200:
        text = text[:197] + '...'
    return escape(text)

def get_system_performance():
    cpu_usage = psutil.cpu_percent(interval=1)
    memory_info = psutil.virtual_memory()
    disk_usage = psutil.disk_usage('/')

    # HTML formatted string
    performance_info = (
        f"<b>📊 System Performance</b>\n"
        f"CPU Usage: <code>{cpu_usage}%</code>\n"
        f"Memory Usage: <code>{memory_info.percent}%</code> (Available: {memory_info.available / (1024**3):.2f} GB)\n"
        f"Disk Usage: <code>{disk_usage.percent}%</code> (Free: {disk_usage.free / (1024**3):.2f} GB)\n"
    )
    return performance_info

def get_network_info():
    net_io = psutil.net_io_counters()
    if net_io is None:
        return "<b>🌐 Network Info (Cumulative)</b>\nUnavailable\n"
    sent_mb = net_io.bytes_sent / (1024 * 1024)
    recv_mb = net_io.bytes_recv / (1024 * 1024)

    network_info = (
        f"<b>🌐 Network Info (Cumulative)</b>\n"
        f"Sent: <code>{sent_mb:.2f} MB</code>\n"
        f"Received: <code>{recv_mb:.2f} MB</code>\n"
    )
    return network_info

def get_running_processes():
    process_list = []
    sampled_processes = []
    logging.info(f"Filtering processes with keyword: '{PROCESS_FILTER}'")

    for proc in psutil.process_iter(['pid', 'name']):
        try:
            name = proc.info.get('name')
            if not name or PROCESS_FILTER.lower() not in name.lower():
                continue
            # Prime every matching process before waiting once for all of them.
            proc.cpu_percent(interval=None)
            sampled_processes.append((proc, name))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if sampled_processes:
        time.sleep(1)
    for proc, name in sampled_processes:
        try:
            cpu_percent = proc.cpu_percent(interval=None)
            memory_info = proc.memory_info()
            memory_text = (
                f"{memory_info.rss / (1024 * 1024):.2f} MB"
                if memory_info is not None else "Unavailable"
            )
            process_list.append(
                f"• <b>{html_text(name)}</b> (PID: {proc.pid})\n"
                f"  CPU: {cpu_percent}% | Mem: {memory_text}"
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    if not process_list:
        return "No matching processes found."
    return "<b>⚙️ Running Processes</b>\n" + "\n".join(process_list)

def get_device_info():
    try:
        uname = platform.uname()
        node_name = uname.node
        system_info = f"{uname.system} {uname.release}"

        server_name_str = f"Alias: <code>{html_text(SERVER_NAME)}</code>\n" if SERVER_NAME else ""

        return (
            f"<b>🖥️ Device Info</b>\n"
            f"{server_name_str}"
            f"Name: <code>{html_text(node_name)}</code>\n"
            f"OS: {html_text(system_info)}\n"
        )
    except Exception:
        return "<b>🖥️ Device Info</b>\nUnavailable\n"

def split_message(message):
    # Generated report lines contain complete HTML tags. Counting raw UTF-16
    # units (including tags/entities) keeps each part conservatively under 4096.
    parts = []
    lines = []
    size = 0
    for line in message.splitlines(keepends=True):
        line_size = len(line.encode('utf-16-le')) // 2
        if line_size > 4096:
            raise ValueError("A report line exceeds the Telegram message limit.")
        if size + line_size > 4096:
            parts.append(''.join(lines))
            lines = []
            size = 0
        lines.append(line)
        size += line_size
    if lines:
        parts.append(''.join(lines))
    return parts

async def send_message_to_telegram(message, token, chat_id):
    parts = split_message(message)
    async with telegram.Bot(token=token) as bot:
        for part in parts:
            for attempt in range(3):
                try:
                    await bot.send_message(chat_id=chat_id, text=part, parse_mode='HTML')
                    break
                except BadRequest:
                    raise
                except RetryAfter as error:
                    if attempt == 2:
                        raise
                    delay = error.retry_after
                    if isinstance(delay, timedelta):
                        delay = delay.total_seconds()
                except NetworkError:
                    if attempt == 2:
                        raise
                    delay = 2 ** attempt
                logging.warning("Telegram send interrupted; retrying in %s seconds.", delay)
                await asyncio.sleep(delay)
    logging.info("Report sent to Telegram successfully (%s message(s)).", len(parts))

async def main():
    setup_logging()
    logging.info("Starting monitoring script...")

    if not TELEGRAM_BOT_TOKEN or not CHAT_ID:
        logging.error("Missing TELEGRAM_BOT_TOKEN or CHAT_ID in environment variables.")
        return 1

    try:
        # Collect system performance info
        performance_info = get_system_performance()

        # Collect network info
        network_info = get_network_info()

        # Collect running processes info
        running_processes_info = get_running_processes()

        # Collect device info
        device_info = get_device_info()

        # Combine all information
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_info = (
            f"📅 <b>Report Time:</b> {timestamp}\n\n"
            f"{device_info}\n"
            f"{performance_info}\n"
            f"{network_info}\n"
            f"{running_processes_info}"
        )

        # Send the information to Telegram
        await send_message_to_telegram(full_info, TELEGRAM_BOT_TOKEN, CHAT_ID)
        return 0

    except Exception:
        logging.exception("An error occurred during execution.")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
