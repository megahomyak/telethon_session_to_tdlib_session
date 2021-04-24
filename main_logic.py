import asyncio
import functools
import json
import re
import time
from typing import Optional

import fastapi
import telethon
import uvicorn
from starlette.status import (
    HTTP_504_GATEWAY_TIMEOUT, HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_401_UNAUTHORIZED
)
from telethon.events import NewMessage
from telethon.tl.types import PeerUser

import response_models

api = fastapi.FastAPI()


TIMEOUT = 90

TELEGRAM_SERVICE_NOTIFICATIONS_USER_ID = 777000
# noinspection RegExpAnonymousGroup
LOGIN_CODE_REGEX = re.compile(r".+?(\d+)")

TIMEOUT_ERROR = {
    HTTP_504_GATEWAY_TIMEOUT: {
        "model": response_models.MyTimeoutError,
        "description": f"Response time is bigger than {TIMEOUT} seconds"
    }
}
BAD_TOKEN_ERROR = {
    **TIMEOUT_ERROR,
    HTTP_401_UNAUTHORIZED: {
        "model": response_models.SimpleError, "description": "Invalid token"
    }
}
BAD_PHONE_NUMBER_ERROR = {
    **BAD_TOKEN_ERROR,
    HTTP_500_INTERNAL_SERVER_ERROR: {
        "model": response_models.SimpleError,
        "description": "Invalid phone number"
    }
}

with open("config.json", "r") as f:
    CONFIG = json.load(f)


auth_codes = {}  # phone_number: code (int)


def make_error_response(
        detail: str, other_data: Optional[dict] = None,
        status_code: int = HTTP_500_INTERNAL_SERVER_ERROR):
    error_dict = {"detail": detail}
    if other_data:
        error_dict.update(other_data)
    return fastapi.responses.JSONResponse(
        error_dict, status_code=status_code
    )


BAD_TOKEN_RESPONSE = make_error_response(
    "Invalid token", status_code=HTTP_401_UNAUTHORIZED
)


@api.middleware("http")
async def timeout_middleware(request: fastapi.Request, call_next):
    start_time = time.time()
    try:
        return await asyncio.wait_for(call_next(request), timeout=TIMEOUT)
    except asyncio.TimeoutError:
        process_time = time.time() - start_time
        return make_error_response(
            "Request processing time excedeed limit", {
                "processing_time": process_time
            }, status_code=HTTP_504_GATEWAY_TIMEOUT
        )


@api.get("/get_auth_code", description=(
    "Gets auth code for telegram account from the specified file"
), response_model=response_models.AuthCode, responses=BAD_PHONE_NUMBER_ERROR)
async def get_auth_code(token: str, phone_number: str):
    if token == CONFIG["api_token"]:
        if phone_number not in auth_codes:
            return make_error_response(
                f"There is no user with phone number \"{phone_number}\""
            )
        while True:
            auth_code = auth_codes[phone_number]
            if auth_code:
                auth_codes[phone_number] = None
                return {"auth_code": auth_code}
            await asyncio.sleep(0)  # Go to the next task
    else:
        return BAD_TOKEN_RESPONSE


@api.get(
    "/get_auth_codes", description="Gets all auth codes",
    response_model=response_models.AuthCodes, responses=BAD_TOKEN_ERROR
)
async def get_auth_codes(token: str):
    if token == CONFIG["api_token"]:
        auth_codes_ = auth_codes.copy()
        for key in auth_codes.keys():
            auth_codes[key] = None
        return {"auth_codes": auth_codes_}
    else:
        return BAD_TOKEN_RESPONSE


async def check_incoming_tg_message(phone_number: str, event: NewMessage.Event):
    message_text = event.message.message
    if (
        type(event.message.peer_id) == PeerUser
        and (
            event.message.peer_id.user_id
            == TELEGRAM_SERVICE_NOTIFICATIONS_USER_ID
        ) and message_text.startswith("Login code")
    ):
        auth_codes[phone_number] = int(
            LOGIN_CODE_REGEX.match(message_text).group(1)
        )


@api.on_event("startup")
async def on_startup():
    for phone_number in CONFIG["phone_numbers"]:
        client = telethon.TelegramClient(
            f"sessions/{phone_number}", api_id=CONFIG["api_id"],
            api_hash=CONFIG["api_hash"]
        )
        client.add_event_handler(
            functools.partial(check_incoming_tg_message, phone_number),
            event=NewMessage()
        )
        auth_codes[phone_number] = None
        # noinspection PyTypeChecker,PyUnresolvedReferences
        await client.start(phone_number)


uvicorn.run(api, log_level="warning")
