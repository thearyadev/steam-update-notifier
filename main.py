from steam.client import SteamClient
from typing import Never 
from steam.enums import EResult
import logging
import time
import requests
import os
import signal

def signal_handler(signum, frame):
    raise SystemExit(0)

def get_authed_client() -> tuple[SteamClient, EResult]:
    client = SteamClient()
    if not client.logged_on:
        return client, client.anonymous_login()
    return client, EResult.OK

def get_env() -> tuple[int, int, str, str]:
    try:
        return (
            int(os.environ["APP_ID"]),
            int(os.environ["SLEEP"]),
            os.environ["WEBHOOK_URL"],
            os.environ["MENTION_USER_ID"],
        )
    except KeyError as e:
        logging.error(f"Missing environment variable: {e}")
        raise SystemExit(1)
    except ValueError as e:
        logging.error(f"Invalid environment variable (failed during int cast): {e}")
        raise SystemExit(1)


def main() -> Never:
    signal.signal(signal.SIGINT, signal_handler)
    logging.basicConfig(level=logging.INFO)
    current_build_id = None
    APP_ID, SLEEP, WEBHOOK_URL, MENTION_USER_ID = get_env()
    
    while True:
        client, login_result = get_authed_client()
        if login_result != EResult.OK:
            logging.error(f"Failed to login: {login_result}")
            raise SystemExit(1)

        prod_info = client.get_product_info(apps=[APP_ID])
        if not prod_info:
            logging.error("Failed to get product info")
            raise SystemExit(1)
        
        try:
            release_info = prod_info["apps"][APP_ID]["depots"]["branches"]["public"]
        except KeyError:
            logging.error("Failed to get release info. Data may not be in the expected shape.")
            raise SystemExit(1)
        
        build_id = release_info.get("buildid")
        if not build_id:
            logging.error("Failed to get build id. Data may not be in the expected shape.")
            raise SystemExit(1)
        # notify
        if build_id != current_build_id:
            r = requests.post(WEBHOOK_URL, json={"content": f"<@{MENTION_USER_ID}> New build detected: {current_build_id if current_build_id is not None else 'first run'} -> {build_id}"})
            if r.status_code != 204:
                logging.error(f"Failed to notify: {r.status_code}")
                raise SystemExit(1)
            logging.info(f"New build detected: {build_id}")
            current_build_id = build_id
        time.sleep(SLEEP)


if __name__ == "__main__":
    main()
