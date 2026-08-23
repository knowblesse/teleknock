import requests
from pathlib import Path

def knock(msg):
    try:
        with open(Path().home() / "teleknock_credentials.txt", "r") as f:
            text = f.read().split('\n')
    except FileNotFoundError:
        raise(FileNotFoundError("Can not find credential file"))
    token = text[0]
    chat_id = text[1]
    response = requests.get(
        "https://api.telegram.org/"
        + token
        + "/sendMessage?chat_id="
        + chat_id
        +"&text="
        + msg
    )
    return response.ok