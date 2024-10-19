from telethon import TelegramClient
from telethon.tl.functions.messages import RequestAppWebViewRequest
from telethon.tl.types import InputBotAppShortName
import urllib.parse
import asyncio
import os
from dotenv import load_dotenv
import requests
import json
import random
import time
import datetime
import aiohttp

load_dotenv()

api_id = os.getenv('API_ID')
api_hash = os.getenv('API_HASH')

class Headers:
    @staticmethod
    def get_headers(init_data):
        return {
            "accept": "application/json, text/plain, */*",
            "accept-encoding": "gzip, deflate, br, zstd",
            "accept-language": "en-US,en;q=0.9",
            "cache-control": "no-cache",
            "origin": "https://app.notpx.app",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": "https://app.notpx.app/",
            "sec-ch-ua": '"Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
            "Authorization": init_data
        }

class QueryGenerator:
    def __init__(self):
        self.api_id = api_id
        self.api_hash = api_hash

    async def generate_query(self, session: str, peer: str, bot: str, start_param: str, shortname: str):
        client = None
        try:
            client = TelegramClient(session=f'notpixelsession/{session}', api_id=self.api_id, api_hash=self.api_hash)
            await client.connect()
            print(f"Successfully connected to session {session}")

            webapp_response = await client(RequestAppWebViewRequest(
                peer=peer,
                app=InputBotAppShortName(bot_id=await client.get_input_entity(bot), short_name=shortname),
                platform='ios',
                write_allowed=True,
                start_param=start_param
            ))

            query_url = webapp_response.url

            query = urllib.parse.unquote(query_url.split('tgWebAppData=')[1].split('&tgWebAppVersion')[0])
            print("Query decoded")

            # Convert query to init_data format
            init_data = f"initData {query}"
            return init_data

        except Exception as e:
            print(f"Error: {str(e)}")
            raise e
        finally:
            if client:
                await client.disconnect()
                print(f"Disconnected from session {session}")

    @staticmethod
    def list_sessions():
        session_folder = 'notpixelsession'
        if os.path.exists(session_folder):
            sessions = [f for f in os.listdir(session_folder) if f.endswith('.session')]
            return sessions
        else:
            return []

class ApiRequests:
    @staticmethod
    def request_with_retry(func, max_retries=3):
        for attempt in range(max_retries):
            result = func()
            if result is not None:
                return result
            print(f"Attempt {attempt + 1} failed. Retrying...")
            time.sleep(0.2)
        print(f"All {max_retries} attempts failed.")
        return None

    @staticmethod
    def request_user_info(headers):
        url = CONFIG['api_urls']['user_info']
        
        def make_request():
            session = requests.Session()
            try:
                response = session.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                log_with_timestamp(f"Error making request: {e}")
                return None
            finally:
                session.close()
        
        return ApiRequests.request_with_retry(make_request)

    @staticmethod
    def request_mining_status(headers):
        url = CONFIG['api_urls']['mining_status']
        
        def make_request():
            session = requests.Session()
            try:
                response = session.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                print(f"Error making request: {e}")
                return None
            finally:
                session.close()
        
        return ApiRequests.request_with_retry(make_request)

    @staticmethod
    def subscribe_to_template(headers):
        subscribe_url = CONFIG['api_urls']['template_subscribe']
        
        def make_request():
            session = requests.Session()
            try:
                subscribe_response = session.put(subscribe_url, headers=headers)
                print(f"Template subscribe status code: {subscribe_response.status_code}")
                return subscribe_response.status_code == 204
            except requests.exceptions.RequestException as e:
                print(f"Error subscribing to template: {e}")
                return False
            finally:
                session.close()
        
        return ApiRequests.request_with_retry(make_request, max_retries=3)

    @staticmethod
    async def request_repaint_start(headers, swapped_pixel_id, previous_balance):
        url = CONFIG['api_urls']['repaint_start']
        payload = {"pixelId": swapped_pixel_id, "newColor": CONFIG['repaint_color']}
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    result = await response.json()
                
                current_balance = result['balance']
                balance_increase = current_balance - previous_balance
                
                return balance_increase, current_balance
            except aiohttp.ClientError as e:
                log_with_timestamp(f"Error making repaint request: {e}")
                return None, previous_balance

    @staticmethod
    async def get_current_balance(headers):
        url = CONFIG['api_urls']['user_info']
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(url, headers=headers) as response:
                    response.raise_for_status()
                    user_info = await response.json()
                    return user_info['balance']
            except aiohttp.ClientError as e:
                log_with_timestamp(f"Error getting current balance: {e}")
                return None

    @staticmethod
    def request_mining_claim(headers):
        url = CONFIG['api_urls']['mining_claim']
        
        def make_request():
            session = requests.Session()
            try:
                response = session.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                print(f"Error making request: {e}")
                return None
            finally:
                session.close()
        
        return ApiRequests.request_with_retry(make_request)

    @staticmethod
    def request_task_check(headers, task_type, name):
        url = f"https://notpx.app/api/v1/mining/task/check/{task_type}"
        payload = {"name": name}
        
        def make_request():
            session = requests.Session()
            try:
                response = session.get(url, headers=headers, params=payload)
                response.raise_for_status()
                return response.json()
            except requests.exceptions.RequestException as e:
                print(f"Error making request: {e}")
                return None
            finally:
                session.close()
        
        return ApiRequests.request_with_retry(make_request)

    @staticmethod
    async def get_swapped_pixel_id():
        ranges = CONFIG['ranges']
        selected_range = random.choice(ranges)
        original_pixel_id = random.randint(selected_range[0], selected_range[1])
        
        original_str = str(original_pixel_id).zfill(6)
        swapped_str = original_str[-3:] + original_str[:3]
        return int(swapped_str)

# Kode warna ANSI
BLUE = '\033[94m'
GREEN = '\033[92m'
RESET = '\033[0m'

def load_config():
    config_url = "https://raw.githubusercontent.com/krazybrazy19xx/notpixel/refs/heads/main/config.json"
    response = requests.get(config_url)
    return json.loads(response.text)

CONFIG = load_config()

def log_with_timestamp(message):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"{BLUE}[{timestamp}]{RESET} - {message}")

def format_balance(balance):
    return f"{GREEN}${balance:.4f}{RESET}"

async def process_session(session, peer, bot, start_param, shortname):
    query_generator = QueryGenerator()
    session_name = session[:-8]  # Remove '.session'
    try:
        init_data = await query_generator.generate_query(session_name, peer, bot, start_param, shortname)
        headers = Headers.get_headers(init_data)
        
        user_info = ApiRequests.request_user_info(headers)
        if user_info:
            log_with_timestamp(f"ID: {user_info['id']} [+] First Name: {user_info['firstName']} [+] Balance: {format_balance(user_info['balance'])}")
        
        mining_status = ApiRequests.request_mining_status(headers)
        if mining_status:
            log_with_timestamp(f"Claim: ${mining_status['claimed']}")
            charges = mining_status['charges']
            log_with_timestamp(f"Remaining charges: {charges}")
            
            current_balance = user_info['balance']

            for i in range(charges):
                swapped_pixel_id = await ApiRequests.get_swapped_pixel_id()
                log_with_timestamp(f"Starting id: {swapped_pixel_id}")
                
                balance_increase, new_balance = await ApiRequests.request_repaint_start(headers, swapped_pixel_id, current_balance)
                if balance_increase is not None:
                    log_with_timestamp(f"Completed. Balance added: {format_balance(balance_increase)}")
                    current_balance = new_balance
                else:
                    log_with_timestamp(f"Failed to complete repaint {i+1}")
                await asyncio.sleep(1)  # Menambahkan jeda kecil antara repaint

            log_with_timestamp(f"Current Balance: [{format_balance(current_balance)}]")

    except Exception as e:
        log_with_timestamp(f"Error processing session {session_name}: {str(e)}")

async def main():
    while True:
        query_generator = QueryGenerator()
        sessions = query_generator.list_sessions()
        if sessions:
            peer = "notpixel"
            bot = "notpixel"
            start_param = "f6160661591_s628001"
            shortname = "app"

            for session in sessions:
                await process_session(session, peer, bot, start_param, shortname)
                print(f"Finished processing session: {session[:-8]}")
                print("Moving to the next session...\n")
        else:
            print("No sessions found in the notpixelsession folder.")
        
        print("Waiting for 30 minutes before restarting...")
        start_time = time.time()
        while time.time() - start_time < 1800:  # 30 minutes in seconds
            elapsed = time.time() - start_time
            minutes, seconds = divmod(int(elapsed), 60)
            milliseconds = int((elapsed - int(elapsed)) * 1000)
            print(f"\rTime elapsed: {minutes:02d}:{seconds:02d}.{milliseconds:03d}", end="", flush=True)
            await asyncio.sleep(0.1)
        print("\nRestarting...")

if __name__ == "__main__":
    asyncio.run(main())
