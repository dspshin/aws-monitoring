import telegram
import psutil
import asyncio
import os
import logging
import sys
from dotenv import load_dotenv
from datetime import datetime
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
    log_filename = 'latest_run.log'
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info("Logging initialized.")

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
    sent_mb = net_io.bytes_sent / (1024 * 1024)
    recv_mb = net_io.bytes_recv / (1024 * 1024)
    
    network_info = (
        f"<b>🌐 Network Info</b>\n"
        f"Sent: <code>{sent_mb:.2f} MB</code>\n"
        f"Received: <code>{recv_mb:.2f} MB</code>\n"
    )
    return network_info

def get_running_processes():
    process_list = []
    logging.info(f"Filtering processes with keyword: '{PROCESS_FILTER}'")
    
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
        try:
            process_info = proc.info
            name = process_info['name']
            
            if PROCESS_FILTER.lower() in name.lower():
                cpu_percent = process_info['cpu_percent']
                memory_mb = process_info['memory_info'].rss / (1024 * 1024) 
                
                process_info_str = (
                    f"• <b>{name}</b> (PID: {process_info['pid']})\n"
                    f"  CPU: {cpu_percent}% | Mem: {memory_mb:.2f} MB"
                )
                process_list.append(process_info_str)
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
        
        server_name_str = f"Alias: <code>{SERVER_NAME}</code>\n" if SERVER_NAME else ""

        return (
            f"<b>🖥️ Device Info</b>\n"
            f"{server_name_str}"
            f"Name: <code>{node_name}</code>\n"
            f"OS: {system_info}\n"
        )
    except Exception:
        return "<b>🖥️ Device Info</b>\nUnavailable\n"

async def send_message_to_telegram(message, token, chat_id):
    bot = telegram.Bot(token=token)
    try:
        await bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML')
        logging.info("Message sent to Telegram successfully.")
    except Exception as e:
        logging.error(f"Failed to send message to Telegram: {e}")

async def main():
    setup_logging()
    logging.info("Starting monitoring script...")
    
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
        
        # Validate Configuration
        if not TELEGRAM_BOT_TOKEN or not CHAT_ID:
            logging.error("Missing TELEGRAM_BOT_TOKEN or CHAT_ID in environment variables.")
            return

        # Send the information to Telegram
        await send_message_to_telegram(full_info, TELEGRAM_BOT_TOKEN, CHAT_ID)
        
    except Exception as e:
        logging.exception("An error occurred during execution.")

if __name__ == "__main__":
    asyncio.run(main())