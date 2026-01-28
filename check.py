from telethon import TelegramClient, events
import os
import asyncio
import colorama
import shutil
from datetime import datetime
from colorama import Fore, Back, Style
colorama.init()

valid = 0
nevalid = 0

DEST_DIR = '/root/snos/sessions'


def find_sessions():
    return [
        os.path.join(root, file)
        for root, _, files in os.walk('.')
        for file in files if file.endswith('.session')
    ]



current_datetime = datetime.now()

h = current_datetime.hour
m = current_datetime.minute
s = current_datetime.second

async def check_session(session_file):
    if "portal" in session_file:
        return
    global valid
    global nevalid

    session_name = os.path.splitext(session_file)[0]
    client = TelegramClient(session_name, api_id, api_hash)
    is_valid = None
    try:
        await client.connect()
        if not await client.is_user_authorized():
            nevalid += 1
            is_valid = False
            print(Fore.YELLOW, f"[-] [{os.path.basename(session_name)}] Аккаунт невалидный")
            
        else:
            valid += 1
            is_valid = True
            print(Fore.GREEN, f"[+] [{os.path.basename(session_name)}] Аккаунт валидный")

    except Exception as e:
        print(Fore.RED, f"[!] [{os.path.basename(session_name)}] Ошибка: {e}")
        is_valid = False
    finally:
        await client.disconnect()
        try:
            if is_valid is False:
                try:
                    os.remove(session_file)
                except:
                    pass
                for extra in (session_file + '-wal', session_file + '-journal'):
                    if os.path.exists(extra):
                        try:
                            os.remove(extra)
                        except:
                            pass
            elif is_valid is True and not "52547225077" in session_name:
                os.makedirs(DEST_DIR, exist_ok=True)
                dest_file = os.path.join(DEST_DIR, os.path.basename(session_file))
                if os.path.exists(dest_file):
                    base = os.path.splitext(os.path.basename(session_file))[0]
                    dest_file = os.path.join(DEST_DIR, base + f"_{int(datetime.now().timestamp())}.session")
                try:
                    shutil.move(session_file, dest_file)
                except:
                    pass
                for extra in (session_file + '-wal', session_file + '-journal'):
                    if os.path.exists(extra):
                        try:
                            shutil.move(extra, os.path.join(DEST_DIR, os.path.basename(extra)))
                        except:
                            pass
        except:
            pass

async def main():
    sessions_folder = ''
    session_files = find_sessions()
    tasks = []

    for session_file in session_files:
        if session_file.endswith('.session'):
            task = asyncio.create_task(check_session(os.path.join(sessions_folder, session_file)))
            tasks.append(task)
    await asyncio.gather(*tasks)

    print()
    print(Fore.WHITE, f'[{h}:{m}:{s}] Результаты проверки:')
    print(Fore.GREEN, f"[{h}:{m}:{s}]   Валидных сессий: {valid}")
    print(Fore.YELLOW, f"[{h}:{m}:{s}]   Невалидных сессий: {nevalid}")
    print(Fore.GREEN, f"[{h}:{m}:{s}] Выполнение задачи завершено!")

if __name__ == '__main__':
    api_id = 25874957  # брать тут my.telegram.org/apps
    api_hash = 'c89ef6fd9ba5c8a479abb1f4d2de248d' # брать тут my.telegram.org/apps
    asyncio.run(main())
