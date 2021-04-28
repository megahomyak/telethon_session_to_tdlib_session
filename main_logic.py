import asyncio
import functools
import json
import os
import re
from dataclasses import dataclass

import telethon
from telegram.client import Telegram
from telethon.events import NewMessage
from telethon.tl.types import PeerUser

TELEGRAM_SERVICE_NOTIFICATIONS_USER_ID = 777000
# noinspection RegExpAnonymousGroup
LOGIN_CODE_REGEX = re.compile(r".+?(\d+)")

TDLIB_SESSIONS_FOLDER_NAME = "tdlib"
TELETHON_SESSIONS_FOLDER_NAME = "sessions"

with open("config.json", "r") as f:
    CONFIG = json.load(f)


@dataclass
class Context:
    amount_of_accounts_to_process: int


async def check_incoming_tg_message(
        context: Context, this_client: telethon.TelegramClient,
        tdlib_session: Telegram, event: NewMessage.Event):
    message_text = event.message.message
    if (
        type(event.message.peer_id) == PeerUser
        and (
            event.message.peer_id.user_id
            == TELEGRAM_SERVICE_NOTIFICATIONS_USER_ID
        ) and message_text.startswith("Login code")
    ):
        await this_client.disconnect()
        tdlib_session.send_code(
            LOGIN_CODE_REGEX.match(message_text).group(1)
        )
        tdlib_session.stop()
        context.amount_of_accounts_to_process -= 1
        if context.amount_of_accounts_to_process == 0:
            exit()


async def main():
    session_files = [
        session_file_name
        for session_file_name in os.listdir(TELETHON_SESSIONS_FOLDER_NAME)
        if os.path.splitext(session_file_name)[1] == ".session"
    ]
    context = Context(amount_of_accounts_to_process=len(session_files))
    for session_file_name in session_files:
        client = telethon.TelegramClient(
            os.path.join(TELETHON_SESSIONS_FOLDER_NAME, session_file_name),
            api_id=CONFIG["api_id"], api_hash=CONFIG["api_hash"]
        )
        await client.connect()
        try:
            phone = (await client.get_me()).phone
        except AttributeError:  # 'NoneType' object has no attribute 'phone'
            print(f"`{session_file_name}` isn't logged in! Skipping it.")
            continue
        tdlib_session = Telegram(
            api_hash=CONFIG["api_hash"],
            api_id=CONFIG["api_id"],
            database_encryption_key=CONFIG["tdlib_database_encryption_key"],
            files_directory=os.path.join(TDLIB_SESSIONS_FOLDER_NAME, phone),
            phone=phone
        )
        tdlib_session.login(blocking=False)
        client.add_event_handler(
            functools.partial(
                check_incoming_tg_message, context, client, tdlib_session
            ), event=NewMessage()
        )
        # noinspection PyTypeChecker,PyUnresolvedReferences
        await client.start()


# loop = asyncio.get_event_loop()
# loop.create_task(main())
# loop.run_forever()
try:
    asyncio.run(main())
except asyncio.CancelledError:
    print(f"Done. Check \"{TDLIB_SESSIONS_FOLDER_NAME}\" folder.")
