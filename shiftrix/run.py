import os
import asyncio
import shutil
from opentele.td import TDesktop
from opentele.tl import TelegramClient
from opentele.api import API, UseCurrentSession, CreateNewSession

RED = "\033[31m"
GREEN = "\033[32m"
CYAN = "\033[36m"
RESET = "\033[0m"

async def telethon_to_tdata(session_file, output_dir, new_session=False, password=None):
  try:
    session_name = os.path.splitext(os.path.basename(session_file))[0]
    tdata_folder = os.path.join(output_dir, session_name)

    client = TelegramClient(session_file)
    api = API.TelegramIOS.Generate()
    tdesk = await client.ToTDesktop(CreateNewSession if new_session else UseCurrentSession, api, password)

    os.makedirs(tdata_folder, exist_ok=True)
    tdesk.SaveTData(tdata_folder)
    
    print(f"{GREEN}Converted {session_file} to {tdata_folder}{RESET}")

  except Exception as e:
    print(f"{RED}Error converting {session_file}: {e}{RESET}")
    if os.path.exists(tdata_folder):
      shutil.rmtree(tdata_folder)

async def tdata_to_telethon(tdata_folder, output_dir, new_session=False, password=None):
  try:
    tdesk = TDesktop(tdata_folder)

    session_name = os.path.basename(tdata_folder)
    session_file = os.path.join(output_dir, f"{session_name}.session")

    api = API.TelegramIOS.Generate()
    client = await tdesk.ToTelethon(session_file, CreateNewSession if new_session else UseCurrentSession, api, password)
    await client.connect()
    await client.PrintSessions()

    print(f"{GREEN}Converted {tdata_folder} to {session_file}{RESET}")

  except Exception as e:
    print(f"{RED}Error converting {tdata_folder}: {e}{RESET}")
    if os.path.exists(session_file):
      os.remove(session_file)

async def main():
  print(f'''{RED}   .dMMMb  dMP dMP dMP dMMMMMP dMMMMMMP dMMMMb  dMP dMP dMP 
  dMP" VP dMP dMP amr dMP        dMP   dMP dMP amr dMK.dMP  
  VMMMb  dMMMMMP dMP dMMMP      dMP   dMMMMK" dMP .dMMMK"   
dP .dMP dMP dMP dMP dMP        dMP   dMP"AMF dMP dMP"AMF    
VMMMP" dMP dMP dMP dMP        dMP   dMP dMP dMP dMP dMP{RESET}\n''')

  mode = input(f"{CYAN}Select mode:\n1) Telethon to tdata\n2) tdata to Telethon\n\n> {RESET}")
  if not mode:
    print(f"{RED}No mode selected. Exiting...{RESET}")
    return
  if mode not in ["1", "2"]:
    print(f"{RED}Invalid mode selected. Exiting...{RESET}")
    return
  input_dir = input(f"{CYAN}Enter the directory containing the {'Telethon session files' if mode=='1' else 'tdata folders'}: {RESET}")
  if not os.path.isdir(input_dir):
    print(f"{RED}Invalid directory!{RESET}")
    return
  output_dir = input(f"{CYAN}Enter the output directory: {RESET}")
  new_session = input(f"{CYAN}Create a new session? (y/n): {RESET}").lower() == 'y'
  password = None
  if new_session:
    password = input(f"{CYAN}Enter password (or leave blank for no password): {RESET}")

  if mode == "1":
    session_files = [f for f in os.listdir(input_dir) if f.endswith(".session")]
    if not session_files:
      print(f"{RED}No .session files found in the directory!{RESET}")
      return

    print(f"{GREEN}Found {len(session_files)} session file(s). Starting conversion...{RESET}")
    os.makedirs(output_dir, exist_ok=True)
    tasks = [telethon_to_tdata(os.path.join(input_dir, session), output_dir, new_session, password) for session in session_files]
    await asyncio.gather(*tasks)

  elif mode == "2":
    tdata_folders = [f for f in os.listdir(input_dir) if os.path.isdir(os.path.join(input_dir, f))]
    if not tdata_folders:
      print(f"{RED}No tdata folders found in the directory!{RESET}")
      return

    print(f"{GREEN}Found {len(tdata_folders)} tdata folder(s). Starting conversion...{RESET}")
    os.makedirs(output_dir, exist_ok=True)
    tasks = [tdata_to_telethon(os.path.join(input_dir, folder), output_dir, new_session, password) for folder in tdata_folders]
    await asyncio.gather(*tasks)

  if not os.listdir(output_dir):
    shutil.rmtree(output_dir)
  else:
    print(f"{CYAN}All conversions completed and saved in {output_dir}{RESET}")


if __name__ == "__main__":
  asyncio.run(main())
