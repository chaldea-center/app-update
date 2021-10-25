"""
origin: https://github.com/atlasacademy/fgo-app-update
"""

import json
import os
import re
import time
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

import httpx
import lxml.html

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)" \
             " Chrome/89.0.4389.90 Safari/537.36"
HEADERS = {"user-agent": USER_AGENT}

DEFAULT_VERSION = '1.0.0'


class StoreType(str, Enum):
    PLAY_STORE = "Google Play Store"
    APP_STORE = "iOS App Store"
    MAC_STORE = "Mac App Store"


def is_new_ver(new_ver: str, current_ver: str) -> bool:
    try:
        new_nums = [int(num) for num in new_ver.split(".")]
        current_nums = [int(num) for num in current_ver.split(".")]
        for new_num, current_num in zip(new_nums, current_nums):
            if new_num != current_num:
                return new_num > current_num
    except ValueError:
        return False
    return False


class Store:
    def __init__(self, _type: StoreType, store_url: str, avatar_url: str):
        self.type: StoreType = _type
        self.store_url: str = store_url
        self.avatar_url: str = avatar_url
        self.resolved_version: Optional[str] = None

    def parse_version(self) -> str:
        if self.type == StoreType.PLAY_STORE:
            self.resolved_version = self.get_play_store_version()
        elif self.type == StoreType.APP_STORE:
            self.resolved_version = self.get_ios_version()
        elif self.type == StoreType.MAC_STORE:
            self.resolved_version = self.get_mac_version()
        else:
            raise NotImplementedError(self.type)
        return self.resolved_version

    def get_play_store_version(self) -> str:
        xpath = "/html/body/div[1]/div[4]/c-wiz/div/div[2]/div/div/main/c-wiz[4]/div[1]/div[2]/div/div[4]/span/div/span"
        try:
            response = httpx.get(self.store_url, follow_redirects=True)
            if not response.text:
                print('Empty response')
                return DEFAULT_VERSION
            site_html = lxml.html.fromstring(response.text)
            version_string: str = site_html.xpath(xpath)[0].text
            return re.sub(r'バージョン|Version|版本', '', version_string).strip()
        except Exception as e:  # pylint: disable=broad-except
            print(f'Error: store version not found, error={e}')
            return DEFAULT_VERSION

    def get_ios_version(self) -> str:
        app_store_response = httpx.get(
            self.store_url + f"&time={int(time.time())}", follow_redirects=True
        )
        app_detail = app_store_response.json()["results"][0]
        api_version = str(app_detail["version"])
        return api_version

    def get_mac_version(self) -> str:
        response = httpx.get(self.store_url, follow_redirects=True)
        if not response.text:
            print('Empty response')
            return DEFAULT_VERSION
        matches = re.findall(r'Version (\d+)\.(\d+)\.(\d+)', response.text)
        if matches:
            return '.'.join(matches[0])
        else:
            print('Mac App Store version not found')
            return DEFAULT_VERSION


play_store = Store(
    _type=StoreType.PLAY_STORE,
    store_url="https://play.google.com/store/apps/details?id=cc.narumi.chaldea&hl=en",
    avatar_url="https://i.imgur.com/kN7NO37.png",  # From the PLay Store apk P5w.png,
)
ios_store = Store(
    _type=StoreType.APP_STORE,
    store_url="https://itunes.apple.com/lookup?bundleId=cc.narumi.chaldea&country=us",
    avatar_url="https://i.imgur.com/fTxPeCW.png",  # https://www.apple.com/app-store/
)
mac_store = Store(
    _type=StoreType.MAC_STORE,
    store_url="https://apps.apple.com/us/app/chaldea/id1548713491",
    # https://developer.apple.com/assets/elements/icons/xcode-12/xcode-12-96x96_2x.png
    avatar_url="https://i.imgur.com/XP7rskN.png",
)

ALL_STORES = (play_store, ios_store, mac_store)


def main(webhook: str) -> None:
    commit_file = Path('commit.txt')
    commit_file.write_text('update app version')
    current_ver_path = Path("current_ver.json")
    if current_ver_path.exists():
        old_save_data: Dict[str, str] = json.loads(current_ver_path.read_bytes())
    else:
        old_save_data = {}

    save_data: Dict[StoreType, str] = {}

    for store in ALL_STORES:
        print(f'getting {store.type} version...')
        old_ver = old_save_data.get(store.type) or DEFAULT_VERSION
        new_ver = store.parse_version()
        if is_new_ver(new_ver, old_ver):
            message = f"{store.type} update: v{new_ver}"
            print(f'🎉 {message}')
            commit_file.write_text(message)
            webhook_content = {
                "content": message,
                "username": store.type.value,
                "avatar_url": store.avatar_url,
            }
            httpx.post(webhook, data=webhook_content, follow_redirects=True)
            save_data[store.type] = new_ver
        else:
            print(f'💦 {store.type} stays v{old_ver}')
            save_data[store.type] = old_ver

    Path(current_ver_path).write_text(json.dumps(save_data, indent=2), encoding='utf-8')


if __name__ == "__main__":
    webhook_url = os.environ.get('WEBHOOK_URL')
    if webhook_url:
        main(webhook_url)
    else:
        raise ValueError('WEBHOOK not set')
