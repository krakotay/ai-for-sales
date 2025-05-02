import tomllib      # для Python ≥3.11
import toml         # pip install toml
import jwt
import requests
from datetime import datetime
from json import JSONDecodeError
import logging

CONFIG_PATH = "amo/config.toml"

def load_full_config() -> dict:
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)

def save_full_config(full_cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        toml.dump(full_cfg, f)


def is_token_expired(token: str) -> bool:
    payload = jwt.decode(token, options={"verify_signature": False})
    exp_time = datetime.utcfromtimestamp(payload["exp"])
    return datetime.utcnow() >= exp_time


class AmoCRMWrapper:
    def __init__(self):
        self._full_cfg = load_full_config()
        self._cfg = self._full_cfg.setdefault("amocrm", {})

    def _save_tokens(self, access_token: str, refresh_token: str):
        self._cfg["access_token"] = access_token
        self._cfg["refresh_token"] = refresh_token
        save_full_config(self._full_cfg)

    def init_oauth2(self):
        data = {
            "client_id": self._cfg["client_id"],
            "client_secret": self._cfg["client_secret"],
            "grant_type": "authorization_code",
            "code": self._cfg["secret_code"],
            "redirect_uri": self._cfg["redirect_uri"],
        }
        url = f"https://{self._cfg['subdomain']}.amocrm.ru/oauth2/access_token"
        resp = requests.post(url, json=data)
        resp.raise_for_status()
        response = resp.json()
        self._save_tokens(response["access_token"], response["refresh_token"])
        print("Tokens saved to config.toml")

    def _get_new_tokens(self):
        data = {
            "client_id": self._cfg["client_id"],
            "client_secret": self._cfg["client_secret"],
            "grant_type": "refresh_token",
            "refresh_token": self._cfg["refresh_token"],
            "redirect_uri": self._cfg["redirect_uri"],
        }
        url = f"https://{self._cfg['subdomain']}.amocrm.ru/oauth2/access_token"
        resp = requests.post(url, json=data)
        resp.raise_for_status()
        response = resp.json()
        self._save_tokens(response["access_token"], response["refresh_token"])

    def get_access_token(self) -> str:
        token = self._cfg.get("access_token", "")
        if not token or is_token_expired(token):
            raise RuntimeError("Access token missing or expired; call init_oauth2() first")
        return token

    def _base_request(self, *, endpoint: str, type: str, data: dict | None = None) -> dict:
        if is_token_expired(self.get_access_token()):
            self._get_new_tokens()

        headers = {
            "Authorization": f"Bearer {self.get_access_token()}",
            "Content-Type": "application/json"
        }
        url = f"https://{self._cfg['subdomain']}.amocrm.ru{endpoint}"

        resp = None
        if type == "get":
            resp = requests.get(url, headers=headers)
        elif type == "post":
            resp = requests.post(url, headers=headers, json=data)
        else:
            raise ValueError(f"Unsupported request type: {type}")

        # для отладки можно раскомментировать:
        print("REQUEST URL:", url)
        print("STATUS:", resp.status_code)
        # print("RESPONSE:", resp.text)

        try:
            return resp.json()
        except JSONDecodeError:
            logging.warning(f"Non-JSON response {resp.status_code}")
            return {}

    def connect_account(self):
        """
        Теперь используем реально полученный account_id из конфига.
        """
        account_id = self._cfg.get("channel").get('account_id')
        title = self._cfg.get("channel").get('name')
        endpoint = f"/v2/origin/custom/{account_id}/connect"
        body = {
            "account_id": account_id,
            "title": title,
            "hook_api_version": "v2",
        }
        # print('body = ', body)
        return self._base_request(endpoint=endpoint, type="post", data=body)


if __name__ == "__main__":
    wrapper = AmoCRMWrapper()
    # Если ещё нет токенов:
    # wrapper.init_oauth2()
    # Вы можете получить и сохранить account_id:
    # wrapper.fetch_account_id()

    # print("Current access token:", wrapper.get_access_token())
    print("Connect response:", wrapper.connect_account())


    print()

