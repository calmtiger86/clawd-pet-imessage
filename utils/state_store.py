# utils/state_store.py
# -----------------------------------------------------------------
# JSON 기반 상태 저장/로드
# -----------------------------------------------------------------

import json
import os
import shutil
from typing import Any, Dict
from utils.logger import logger


def load_state(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.warning(f"상태 파일 로드 실패, 백업 시도: {e}")
        backup = path + '.backup'
        if os.path.exists(backup):
            with open(backup, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}


def save_state(path: str, data: Dict[str, Any]) -> None:
    if os.path.exists(path):
        shutil.copy2(path, path + '.backup')
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
