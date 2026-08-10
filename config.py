import json
import os
from typing import Any, Dict, List, Tuple

CONFIG_FILE = 'config.json'

LEGACY_KEY_MAP = {
    'channel_type': 'channels.enabled',
    'webhook_url': 'channels.dingding.webhook_url',
    'hour': 'execution.schedule.hour',
    'minute': 'execution.schedule.minute',
    'telegram_config': 'channels.telegram'
}

DEFAULT_CONFIG = {
    'users': [],
    'completion_threshold': 1,
    'execution': {
        'mode': 'both',
        'run_on_startup': False,
        'schedule': {
            'hour': 9,
            'minute': 0,
            'timezone': 'Asia/Shanghai',
            'interval_seconds': None,
            'max_runs': None
        }
    },
    'channels': {
        'enabled': ['dingding'],
        'feishu': {
            'webhook_url': '',
            'secret': '',
            'msg_type': 'text'
        },
        'dingding': {
            'webhook_url': '',
            'secret': '',
            'msg_type': 'text'
        },
        'telegram': {
            'bot_token': '',
            'chat_id': ''
        },
        'wechat': {
            'webhook_url': '',
            'enabled': False
        },
        'facebook': {
            'page_access_token': '',
            'recipient_id': '',
            'enabled': False
        }
    }
}


def _set_nested(data: Dict[str, Any], path: str, value: Any) -> None:
    keys = path.split('.')
    current = data
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value


def _migrate_legacy(config: Dict[str, Any]) -> Dict[str, Any]:
    is_legacy = any(k in config for k in LEGACY_KEY_MAP.keys())
    if not is_legacy:
        return config

    migrated = json.loads(json.dumps(DEFAULT_CONFIG))

    if 'users' in config:
        migrated['users'] = config['users']

    for legacy_key, new_path in LEGACY_KEY_MAP.items():
        if legacy_key in config:
            value = config[legacy_key]
            if legacy_key == 'channel_type':
                if isinstance(value, str):
                    migrated['channels']['enabled'] = [value]
                elif isinstance(value, list):
                    migrated['channels']['enabled'] = value
            elif legacy_key == 'telegram_config' and isinstance(value, dict):
                migrated['channels']['telegram'].update(value)
            else:
                _set_nested(migrated, new_path, value)

    return migrated


def _apply_defaults(config: Dict[str, Any]) -> Dict[str, Any]:
    result = json.loads(json.dumps(DEFAULT_CONFIG))

    def deep_merge(target: Dict[str, Any], source: Dict[str, Any]) -> None:
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                deep_merge(target[key], value)
            else:
                target[key] = value

    deep_merge(result, config)
    return result


def load_config() -> Dict[str, Any]:
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(f"配置文件不存在: {CONFIG_FILE}")

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        raw_config = json.load(f)

    migrated = _migrate_legacy(raw_config)
    final_config = _apply_defaults(migrated)

    mode = final_config.get('execution', {}).get('mode', 'both')
    if mode not in ('manual', 'schedule', 'both'):
        raise ValueError(f"无效的执行模式: {mode}，可选值: manual, schedule, both")

    enabled_channels = final_config.get('channels', {}).get('enabled', [])
    if not isinstance(enabled_channels, list):
        raise ValueError("channels.enabled 必须是列表类型")

    return final_config


def save_config(config: Dict[str, Any]) -> None:
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def _normalize_user_entry(entry: Any) -> Tuple[str, str]:
    if isinstance(entry, str):
        return entry, entry
    if isinstance(entry, dict):
        slug = str(entry.get("slug", "") or entry.get("user", "") or "").strip()
        real_name = str(entry.get("real_name", "") or entry.get("name", "") or "").strip()
        if not slug:
            return "", ""
        if not real_name:
            real_name = slug
        return slug, real_name
    return "", ""


def parse_users(raw_users: List[Any]) -> List[Dict[str, str]]:
    result: List[Dict[str, str]] = []
    for entry in (raw_users or []):
        slug, real_name = _normalize_user_entry(entry)
        if slug:
            result.append({"slug": slug, "real_name": real_name})
    return result


def get_user_slugs(raw_users: List[Any]) -> List[str]:
    return [u["slug"] for u in parse_users(raw_users)]


def build_name_map(raw_users: List[Any]) -> Dict[str, str]:
    return {u["slug"]: u["real_name"] for u in parse_users(raw_users)}


def format_display_name(slug: str, name_map: Dict[str, str]) -> str:
    real_name = name_map.get(slug)
    if not real_name or real_name == slug:
        return slug
    return f"{slug}（{real_name}）"
