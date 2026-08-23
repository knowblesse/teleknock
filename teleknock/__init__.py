import json
from pathlib import Path

import requests

CREDENTIALS_PATH = Path.home() / "teleknock_credentials.json"


def _slugify(title):
    return title.lower().replace(" ", "")


def _load_credentials():
    with open(CREDENTIALS_PATH, "r") as f:
        return json.load(f)


def _save_credentials(creds):
    tmp = CREDENTIALS_PATH.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(creds, f, indent=2)
    tmp.replace(CREDENTIALS_PATH)


def knock(msg, chat=None):
    creds = _load_credentials()
    token = creds["token"]
    chat_key = chat or creds.get("default_chat")
    if chat_key is None:
        raise ValueError(
            "no chat given and no default_chat set in teleknock_credentials.json"
        )
    try:
        chat_id = creds["chats"][chat_key]
    except KeyError:
        raise KeyError(
            f"unknown chat '{chat_key}', known chats: {sorted(creds.get('chats', {}))}"
        )
    response = requests.get(
        f"https://api.telegram.org/{token}/sendMessage",
        params={"chat_id": chat_id, "text": msg},
    )
    return response.ok


def index_chats():
    """Discover chats from recent bot activity and merge them into
    teleknock_credentials.json, keyed by lowercase title with spaces
    removed.

    A chat only shows up here after the bot has seen at least one event in
    it since the last indexed update — send it a message, or just add the
    bot to the chat/group/channel (that alone generates an event).
    """
    creds = _load_credentials()
    token = creds["token"]
    resp = requests.get(f"https://api.telegram.org/{token}/getUpdates")
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"getUpdates failed: {data}")

    chats = creds.setdefault("chats", {})
    for update in data.get("result", []):
        chat = None
        for field in ("message", "edited_message", "channel_post", "my_chat_member"):
            if field in update:
                chat = update[field].get("chat")
                if chat:
                    break
        if chat is None:
            continue
        title = (
            chat.get("title")
            or chat.get("username")
            or chat.get("first_name")
            or str(chat["id"])
        )
        key = _slugify(title)
        chat_id = str(chat["id"])
        if key not in chats:
            chats[key] = chat_id
            print(f"added: {key} -> {chat_id}")
        elif chats[key] != chat_id:
            print(f"warning: '{key}' id changed {chats[key]} -> {chat_id}, overwriting")
            chats[key] = chat_id

    _save_credentials(creds)
    print_chats(creds)
    return creds


def print_chats(creds=None):
    creds = creds or _load_credentials()
    default = creds.get("default_chat")
    if not creds.get("chats"):
        print("no chats indexed yet")
        return
    for name, chat_id in creds["chats"].items():
        marker = "  (default)" if name == default else ""
        print(f"{name}: {chat_id}{marker}")


def migrate_from_txt(txt_path=None):
    """One-time conversion of the old two-line teleknock_credentials.txt
    (token, chat_id) into teleknock_credentials.json. Looks up the existing
    chat's title via getChat so it lands under a real name instead of a
    placeholder, and sets it as default_chat.
    """
    txt_path = Path(txt_path) if txt_path else Path.home() / "teleknock_credentials.txt"
    token, chat_id = txt_path.read_text().split("\n")[:2]

    resp = requests.get(
        f"https://api.telegram.org/{token}/getChat", params={"chat_id": chat_id}
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"getChat failed: {data}")

    chat = data["result"]
    title = (
        chat.get("title")
        or chat.get("username")
        or chat.get("first_name")
        or str(chat["id"])
    )
    key = _slugify(title)

    creds = {"token": token, "default_chat": key, "chats": {key: str(chat_id)}}
    _save_credentials(creds)
    print(f"migrated: {key} -> {chat_id} (default)")
    return creds
