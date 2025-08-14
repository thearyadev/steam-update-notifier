from steam.client import SteamClient
from steam.enums import EResult
from typing import NoReturn
import logging
import time
import requests
import os
import signal


def signal_handler(signum, frame):
    raise SystemExit(0)


def get_env():
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


def main() -> NoReturn:
    signal.signal(signal.SIGINT, signal_handler)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    APP_ID, SLEEP, WEBHOOK_URL, MENTION_USER_ID = get_env()
    current_timeupdated = None

    client = SteamClient()
    logging.info("Logging in to Steam (anonymous)...")
    if client.anonymous_login() != EResult.OK:
        logging.error("Failed to login anonymously to Steam")
        raise SystemExit(1)

    logging.info(f"Starting update monitor for app {APP_ID}, branch: public")

    while True:
        prod_info = client.get_product_info(apps=[APP_ID])
        if not prod_info or "apps" not in prod_info or APP_ID not in prod_info["apps"]:
            logging.warning("No product info returned for app. Retrying...")
            time.sleep(SLEEP)
            continue

        try:
            release_info = prod_info["apps"][APP_ID]["depots"]["branches"]["public"]
        except KeyError:
            logging.warning("No public branch info for this app. Retrying...")
            time.sleep(SLEEP)
            continue

        time_updated = release_info.get("timeupdated")
        if not time_updated:
            logging.warning("No timeupdated value found in branch data")
            time.sleep(SLEEP)
            continue

        if time_updated != current_timeupdated:
            if current_timeupdated is None:
                logging.info(f"First run. Current timeupdated: {time_updated}")
            else:
                logging.info(f"Update detected! {current_timeupdated} -> {time_updated}")
                payload = {
                    "content": f"<@{MENTION_USER_ID}> Update detected for app {APP_ID}: {current_timeupdated} -> {time_updated}"
                }
                r = requests.post(WEBHOOK_URL, json=payload)
                if r.status_code != 204:
                    logging.error(f"Failed to notify via webhook: {r.status_code} {r.text}")
                else:
                    logging.info("Notification sent successfully.")

            current_timeupdated = time_updated
        else:
            logging.info(f"No update detected. Still at timeupdated: {time_updated}")

        time.sleep(SLEEP)


if __name__ == "__main__":
    main()
