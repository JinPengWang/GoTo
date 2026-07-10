#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GoTo - 鏅鸿兘娴忚鍣ㄥ垎鍙戝櫒
========================
涓€涓交閲忕殑 Windows 鍗忚澶勭悊绋嬪簭锛屾牴鎹煙鍚嶈鍒欒嚜鍔ㄩ€夋嫨 Chrome 鎴?Edge 鎵撳紑閾炬帴銆?瀹夎鍚庝綔涓?http/https 鍗忚澶勭悊鍣紝鐢辩郴缁熷湪鐐瑰嚮閾炬帴鏃惰嚜鍔ㄨ皟鐢紝鎵ц瀹屽嵆閫€鍑恒€?
璁稿彲璇? MIT
"""

import sys
import os
import json
import subprocess
import logging
import winreg
import re
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
from urllib.parse import urlparse

# ============================================================
# 甯搁噺瀹氫箟
# ============================================================

# 绋嬪簭鍚嶇О
APP_NAME: str = "GoTo"

# 鏃ュ織淇濈暀澶╂暟
LOG_RETENTION_DAYS: int = 30

# 榛樿娴忚鍣ㄥ€欓€夎矾寰勶紙鎸変紭鍏堢骇鎺掑垪锛?CHROME_CANDIDATES: List[str] = [
    os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
]

EDGE_CANDIDATES: List[str] = [
    os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
    os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
]

# 娉ㄥ唽琛ㄤ腑 Chrome 鍜?Edge 鐨勮矾寰勯敭
CHROME_REGISTRY_KEYS: List[Tuple[int, str]] = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
]

EDGE_REGISTRY_KEYS: List[Tuple[int, str]] = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"),
]


# ============================================================
# 鏃ュ織绯荤粺
# ============================================================

def get_log_dir() -> Path:
    """鑾峰彇鏃ュ織鐩綍锛屼紭鍏堜娇鐢?%APPDATA%锛屽洖閫€鍒扮▼搴忔墍鍦ㄧ洰褰曘€?""
    candidates: List[Path] = []
    try:
        appdata = os.environ.get("APPDATA")
        if appdata:
            candidates.append(Path(appdata) / APP_NAME / "logs")
    except Exception:
        pass

    candidates.append(get_app_dir() / "logs")
    candidates.append(Path(tempfile.gettempdir()) / APP_NAME / "logs")

    for log_dir in candidates:
        try:
            log_dir.mkdir(parents=True, exist_ok=True)
            return log_dir
        except Exception:
            continue

    return Path(tempfile.gettempdir())


def cleanup_old_logs(log_dir: Path) -> None:
    """鍒犻櫎瓒呰繃 LOG_RETENTION_DAYS 澶╃殑鏃ф棩蹇楁枃浠躲€?""
    cutoff = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    try:
        for log_file in log_dir.glob("*.log"):
            try:
                # 浠庢枃浠跺悕瑙ｆ瀽鏃ユ湡锛歡oto_YYYY-MM-DD.log
                date_str = log_file.stem.split("_")[-1]
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                if file_date < cutoff:
                    log_file.unlink(missing_ok=True)
            except (ValueError, OSError):
                continue
    except Exception:
        pass


def setup_logger() -> logging.Logger:
    """閰嶇疆骞惰繑鍥炴棩蹇楄褰曞櫒銆?""
    log_dir = get_log_dir()
    cleanup_old_logs(log_dir)

    today = datetime.now().strftime("%Y-%m-%d")

    logger = logging.getLogger(APP_NAME)
    logger.setLevel(logging.DEBUG)

    # 閬垮厤閲嶅娣诲姞 handler
    if not logger.handlers:
        handler: logging.Handler
        for candidate_dir in (
            log_dir,
            get_app_dir() / "logs",
            Path(tempfile.gettempdir()) / APP_NAME / "logs",
        ):
            try:
                candidate_dir.mkdir(parents=True, exist_ok=True)
                log_file = candidate_dir / f"goto_{today}.log"
                handler = logging.FileHandler(str(log_file), encoding="utf-8")
                break
            except Exception:
                continue
        else:
            handler = logging.NullHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


# ============================================================
# 璺緞宸ュ叿锛堝吋瀹?PyInstaller 鎵撳寘锛?# ============================================================

def get_app_dir() -> Path:
    """
    鑾峰彇搴旂敤绋嬪簭鎵€鍦ㄧ洰褰曘€?    PyInstaller --onefile 鎵撳寘鍚?__file__ 鎸囧悜涓存椂鐩綍锛?    闇€瑕佺敤 sys.executable 鑾峰彇鐪熸鐨?exe 璺緞銆?    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 鎵撳寘鍚?        return Path(sys.executable).parent
    else:
        # 婧愮爜杩愯
        return Path(__file__).parent


# 鍏ㄥ眬鏃ュ織瀹炰緥
logger = setup_logger()


# ============================================================
# 娴忚鍣ㄨ矾寰勬帰娴?# ============================================================

def read_registry_path(hive: int, sub_key: str) -> Optional[str]:
    """浠?Windows 娉ㄥ唽琛ㄨ鍙栭粯璁ゅ€笺€?""
    try:
        with winreg.OpenKey(hive, sub_key) as key:
            value, _ = winreg.QueryValueEx(key, "")
            if value and os.path.isfile(value):
                return value
    except (OSError, FileNotFoundError, TypeError):
        pass
    return None


def find_browser_by_registry(keys: List[Tuple[int, str]]) -> Optional[str]:
    """閫氳繃娉ㄥ唽琛ㄦ煡鎵炬祻瑙堝櫒璺緞銆?""
    for hive, sub_key in keys:
        path = read_registry_path(hive, sub_key)
        if path:
            return path
    return None


def find_browser_by_candidates(candidates: List[str]) -> Optional[str]:
    """浠庡€欓€夎矾寰勫垪琛ㄤ腑鏌ユ壘绗竴涓瓨鍦ㄧ殑娴忚鍣ㄣ€?""
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def find_chrome(custom_path: str = "") -> Optional[str]:
    """
    鏌ユ壘 Chrome 娴忚鍣ㄨ矾寰勩€?    浼樺厛绾э細鐢ㄦ埛鑷畾涔夎矾寰?> 娉ㄥ唽琛?> 鍊欓€夎矾寰勫垪琛?    """
    if custom_path and os.path.isfile(custom_path):
        return custom_path

    registry_path = find_browser_by_registry(CHROME_REGISTRY_KEYS)
    if registry_path:
        return registry_path

    return find_browser_by_candidates(CHROME_CANDIDATES)


def find_edge(custom_path: str = "") -> Optional[str]:
    """
    鏌ユ壘 Edge 娴忚鍣ㄨ矾寰勩€?    浼樺厛绾э細鐢ㄦ埛鑷畾涔夎矾寰?> 娉ㄥ唽琛?> 鍊欓€夎矾寰勫垪琛?    """
    if custom_path and os.path.isfile(custom_path):
        return custom_path

    registry_path = find_browser_by_registry(EDGE_REGISTRY_KEYS)
    if registry_path:
        return registry_path

    return find_browser_by_candidates(EDGE_CANDIDATES)


def is_goto_executable(path: str) -> bool:
    """Return True when path points to this app's executable."""
    if not path:
        return False

    candidates = [Path(sys.executable)]
    if not getattr(sys, "frozen", False):
        candidates.append(get_app_dir() / "GoTo.exe")

    try:
        target = Path(path).resolve()
        return any(target == candidate.resolve() for candidate in candidates)
    except OSError:
        target = os.path.normcase(os.path.abspath(path))
        return any(
            target == os.path.normcase(os.path.abspath(str(candidate)))
            for candidate in candidates
        )


def get_system_default_browser() -> Optional[str]:
    """鑾峰彇绯荤粺榛樿娴忚鍣ㄨ矾寰勶紙鐢ㄤ簬闄嶇骇锛夈€?""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice"
        ) as key:
            prog_id, _ = winreg.QueryValueEx(key, "ProgId")
        # 灏濊瘯浠?ProgId 瑙ｆ瀽瀹為檯璺緞
        command_key = rf"{prog_id}\shell\open\command"
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, command_key) as key:
            command, _ = winreg.QueryValueEx(key, "")
            # 鎻愬彇寮曞彿鍐呯殑璺緞
            match = re.match(r'"([^"]+)"', command)
            if match and os.path.isfile(match.group(1)) and not is_goto_executable(match.group(1)):
                return match.group(1)
            # 鏃犲紩鍙锋椂鍙栫涓€涓┖鏍煎墠鐨勯儴鍒?            parts = command.split()
            if parts and os.path.isfile(parts[0]) and not is_goto_executable(parts[0]):
                return parts[0]
    except (OSError, FileNotFoundError, TypeError, IndexError):
        pass
    return None


# ============================================================
# 閰嶇疆鏂囦欢鍔犺浇
# ============================================================

def get_config_path() -> Path:
    """
    鑾峰彇閰嶇疆鏂囦欢璺緞銆?    浼樺厛绾э細绋嬪簭鍚岀洰褰?> %APPDATA%
    """
    # 棣栧厛妫€鏌ョ▼搴忓悓鐩綍
    exe_dir = get_app_dir()
    local_config = exe_dir / "rules.json"
    if local_config.is_file():
        return local_config

    # 鐒跺悗妫€鏌?%APPDATA%
    appdata = os.environ.get("APPDATA")
    if appdata:
        appdata_config = Path(appdata) / APP_NAME / "rules.json"
        if appdata_config.is_file():
            return appdata_config

    # 閮戒笉瀛樺湪鏃惰繑鍥炵▼搴忓悓鐩綍璺緞锛堝悗缁細鎶ラ敊锛?    return local_config


def load_rules(config_path: Path) -> Tuple[Dict[str, str], List[Dict[str, Any]]]:
    """
    鍔犺浇閰嶇疆鏂囦欢锛岃繑鍥?(娴忚鍣ㄨ矾寰勯厤缃? 瑙勫垯鍒楄〃)銆?
    Returns:
        (browser_paths, rules): 娴忚鍣ㄨ嚜瀹氫箟璺緞瀛楀吀鍜岃鍒欏垪琛?    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"閰嶇疆鏂囦欢鍔犺浇澶辫触: {e}")
        return {}, []

    browser_paths = data.get("browser_paths", {})
    rules = data.get("rules", [])

    if not rules:
        logger.warning("閰嶇疆鏂囦欢涓病鏈夋壘鍒颁换浣曡鍒?)

    return browser_paths, rules


# ============================================================
# 鍩熷悕鍖归厤
# ============================================================

def extract_domain(url: str) -> str:
    """
    浠?URL 涓彁鍙栧煙鍚嶏紙灏忓啓锛屽幓闄?www. 鍓嶇紑锛夈€?
    Args:
        url: 瀹屾暣鐨?URL 瀛楃涓?
    Returns:
        鎻愬彇鐨勫煙鍚嶅瓧绗︿覆
    """
    try:
        parsed = urlparse(url)
        domain = parsed.hostname or ""
        domain = domain.lower()
        # 鍘婚櫎 www. 鍓嶇紑浠ヤ究缁熶竴鍖归厤
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def match_domain(domain: str, patterns: List[str]) -> bool:
    """
    妫€鏌ュ煙鍚嶆槸鍚﹀尮閰嶄换涓€妯″紡銆?
    鏀寔锛?    - 瀹屾暣鍖归厤: "github.com" 鍖归厤 "github.com"
    - 瀛愬煙鍚嶅尮閰? "gist.github.com" 鍖归厤 "github.com"
    - 閫氶厤绗? "*" 鍖归厤鎵€鏈夊煙鍚?
    Args:
        domain: 寰呭尮閰嶇殑鍩熷悕
        patterns: 鍩熷悕妯″紡鍒楄〃

    Returns:
        鏄惁鍖归厤鎴愬姛
    """
    for pattern in patterns:
        pattern = pattern.lower().strip()
        if pattern == "*":
            return True
        # 瀹屾暣鍖归厤鎴栧瓙鍩熷悕鍖归厤
        if domain == pattern or domain.endswith("." + pattern):
            return True
    return False


def resolve_browser(
    target: str,
    browser_paths: Dict[str, str],
    chrome_path: Optional[str],
    edge_path: Optional[str]
) -> Tuple[Optional[str], str]:
    """
    鏍规嵁鐩爣娴忚鍣ㄥ悕绉拌繑鍥炲疄闄呰矾寰勩€?
    Args:
        target: 鐩爣娴忚鍣ㄥ悕绉?("chrome" 鎴?"edge")
        browser_paths: 鐢ㄦ埛鑷畾涔夎矾寰勯厤缃?        chrome_path: 宸叉帰娴嬪埌鐨?Chrome 璺緞
        edge_path: 宸叉帰娴嬪埌鐨?Edge 璺緞

    Returns:
        (娴忚鍣ㄨ矾寰? 娴忚鍣ㄥ悕绉? 鐨勫厓缁?    """
    if target == "chrome":
        path = chrome_path
        name = "Google Chrome"
    elif target == "edge":
        path = edge_path
        name = "Microsoft Edge"
    else:
        path = None
        name = "鏈煡"

    if path and os.path.isfile(path):
        return path, name

    # 鐩爣娴忚鍣ㄦ湭鎵惧埌锛屽皾璇曢檷绾?    logger.warning(f"{name} 鏈壘鍒帮紝灏濊瘯闄嶇骇鍒扮郴缁熼粯璁ゆ祻瑙堝櫒")
    fallback_candidates: List[Tuple[Optional[str], str]] = []
    if target == "chrome":
        fallback_candidates.append((edge_path, "Microsoft Edge"))
    elif target == "edge":
        fallback_candidates.append((chrome_path, "Google Chrome"))

    fallback_candidates.append((get_system_default_browser(), "system default"))

    for fallback, fallback_name in fallback_candidates:
        if fallback and os.path.isfile(fallback) and not is_goto_executable(fallback):
            return fallback, f"{fallback_name}({Path(fallback).stem})"

    logger.error("娌℃湁鍙敤鐨勬祻瑙堝櫒")
    return None, "鏃?


# ============================================================
# 閾炬帴鎵撳紑
# ============================================================

def open_url(browser_path: str, url: str) -> None:
    """
    浣跨敤鎸囧畾娴忚鍣ㄦ墦寮€ URL銆?
    Args:
        browser_path: 娴忚鍣ㄥ彲鎵ц鏂囦欢璺緞
        url: 瑕佹墦寮€鐨?URL
    """
    try:
        # 浣跨敤 Popen 鍚姩娴忚鍣紝涓嶇瓑寰呭叾鍏抽棴
        subprocess.Popen(
            [browser_path, url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
        )
        logger.info(f"宸插惎鍔ㄦ祻瑙堝櫒: {browser_path}")
    except Exception as e:
        logger.error(f"鍚姩娴忚鍣ㄥけ璐? {e}")
        # 鏈€鍚庡皾璇曚娇鐢?os.startfile锛圵indows 鐗规湁锛?        try:
            os.startfile(url)  # type: ignore[attr-defined]
            logger.info("宸查€氳繃绯荤粺榛樿鏂瑰紡鎵撳紑 URL")
        except Exception as e2:
            logger.error(f"鎵€鏈夋墦寮€鏂瑰紡鍧囧け璐? {e2}")


# ============================================================
# 鍐呴儴 URL 妫€娴?# ============================================================

# 杩欎簺鍗忚/鍓嶇紑搴旂洿鎺ヤ氦缁欏搴旀祻瑙堝櫒锛屼笉鍋氳鍒欏尮閰?EDGE_INTERNAL_PREFIXES: Tuple[str, ...] = (
    "edge://",
    "microsoft-edge://",
    "microsoft-edge:",
)
CHROME_INTERNAL_PREFIXES: Tuple[str, ...] = (
    "chrome://",
    "chrome-extension://",
)
OTHER_INTERNAL_PREFIXES: Tuple[str, ...] = (
    "about:",
    "data:",
    "blob:",
    "javascript:",
)


def handle_internal_url(url: str, edge_path: Optional[str], chrome_path: Optional[str]) -> bool:
    """
    妫€娴嬪苟澶勭悊娴忚鍣ㄥ唴閮?URL锛堝 edge://settings锛夈€?    杩欑被 URL 蹇呴』浜ょ粰瀵瑰簲娴忚鍣ㄧ洿鎺ュ鐞嗭紝涓嶈兘璧拌鍒欏尮閰嶃€?
    Returns:
        True 琛ㄧず宸插鐞嗭紙璋冪敤浜嗘祻瑙堝櫒锛夛紝False 琛ㄧず涓嶆槸鍐呴儴 URL
    """
    url_lower = url.lower()

    # Edge 鍐呴儴 URL 鈫?鐩存帴浜ょ粰 Edge
    if any(url_lower.startswith(p) for p in EDGE_INTERNAL_PREFIXES):
        if edge_path:
            logger.info(f"Edge 鍐呴儴 URL锛岀洿鎺ヤ氦缁?Edge: {url}")
            open_url(edge_path, url)
            return True
        logger.warning("Edge 鍐呴儴 URL 浣?Edge 鏈壘鍒?)

    # Chrome 鍐呴儴 URL 鈫?鐩存帴浜ょ粰 Chrome
    if any(url_lower.startswith(p) for p in CHROME_INTERNAL_PREFIXES):
        if chrome_path:
            logger.info(f"Chrome 鍐呴儴 URL锛岀洿鎺ヤ氦缁?Chrome: {url}")
            open_url(chrome_path, url)
            return True
        logger.warning("Chrome 鍐呴儴 URL 浣?Chrome 鏈壘鍒?)

    # about: 绛夐€氱敤鍐呴儴 URL 鈫?浜ょ粰绯荤粺榛樿娴忚鍣?    if any(url_lower.startswith(p) for p in OTHER_INTERNAL_PREFIXES):
        logger.info(f"鍐呴儴 URL锛屼氦缁欑郴缁熼粯璁ゆ祻瑙堝櫒: {url}")
        fallback = chrome_path or edge_path or get_system_default_browser()
        if fallback:
            open_url(fallback, url)
            return True

    return False


# ============================================================
# 鑷慨澶?# ============================================================

def self_repair() -> None:
    """
    妫€鏌ュ苟淇 GoTo 鐨勬敞鍐岃〃娉ㄥ唽銆?    鐢辫鍒掍换鍔″畾鏈熻皟鐢紝鎴栭€氳繃 --self-repair 鏍囧織鎵嬪姩瑙﹀彂銆?    鍙啓鍏?HKCU锛堟棤闇€绠＄悊鍛樻潈闄愶級銆?    """
    try:
        # 妫€娴嬪綋鍓嶉粯璁ゆ祻瑙堝櫒 ProgId
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice"
        ) as key:
            prog_id, _ = winreg.QueryValueEx(key, "ProgId")
    except (OSError, FileNotFoundError):
        prog_id = "MSEdgeHTM"

    exe_path = str(Path(sys.executable).resolve()) if getattr(sys, 'frozen', False) else str(get_app_dir() / "GoTo.exe")
    new_cmd = f'"{exe_path}" "%1"'

    # 妫€鏌ュ綋鍓?HKCU 澶勭悊鍣ㄦ槸鍚﹀凡鎸囧悜 GoTo
    user_cmd_key = rf"Software\Classes\{prog_id}\shell\open\command"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, user_cmd_key) as key:
            current_cmd, _ = winreg.QueryValueEx(key, "")
            if "GoTo.exe" in current_cmd.lower():
                logger.debug("娉ㄥ唽琛ㄦ甯革紝鏃犻渶淇")
                return
    except (OSError, FileNotFoundError):
        pass

    # 闇€瑕佷慨澶嶏細鍐欏叆 HKCU锛堟棤闇€绠＄悊鍛樻潈闄愶級
    logger.info(f"淇娉ㄥ唽琛? {prog_id} -> GoTo.exe")
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, user_cmd_key, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, new_cmd)
        logger.info("HKCU 淇鎴愬姛")
    except OSError as e:
        logger.error(f"HKCU 淇澶辫触: {e}")



# ============================================================
# 涓绘祦绋?# ============================================================

def clean_url(raw: str) -> str:
    """
    娓呯悊 URL 鍙傛暟锛屽鐞嗗悇绉嶈竟鐣屾儏鍐碉細
    - 鍘婚櫎棣栧熬寮曞彿
    - 鍘婚櫎棣栧熬绌虹櫧
    - 澶勭悊 microsoft-edge: 鍓嶇紑锛圵indows 鏈夋椂浼氭坊鍔狅級
    """
    url = raw.strip().strip('"').strip("'")

    # 澶勭悊 microsoft-edge: 鍗忚鍓嶇紑
    # Windows 閫氱煡涓績銆佸紑濮嬭彍鍗曠瓑浼氱敤 microsoft-edge:https://... 鐨勫舰寮?    prefixes_to_strip = [
        "microsoft-edge://",
        "microsoft-edge:",
    ]
    for prefix in prefixes_to_strip:
        if url.lower().startswith(prefix):
            url = url[len(prefix):]
            # 濡傛灉鍘绘帀鍓嶇紑鍚庝笉鏄?http(s):// 寮€澶达紝琛ヤ笂 https://
            if not url.lower().startswith(("http://", "https://")):
                url = "https://" + url
            break

    return url


def main() -> None:
    """涓诲叆鍙ｅ嚱鏁般€?""
    # 澶勭悊鐗规畩鏍囧織
    if len(sys.argv) >= 2 and sys.argv[1] in ("--self-repair", "--maintain"):
        self_repair()
        return

    # 1. 鑾峰彇 URL 鍙傛暟
    if len(sys.argv) < 2:
        logger.warning("鏈帴鏀跺埌 URL 鍙傛暟锛岄€€鍑?)
        return

    url = clean_url(sys.argv[1])
    if not url:
        logger.warning("URL 鍙傛暟涓虹┖锛岄€€鍑?)
        return

    logger.info(f"鏀跺埌閾炬帴: {url}")

    # 2. 鍔犺浇閰嶇疆
    config_path = get_config_path()
    logger.info(f"閰嶇疆鏂囦欢: {config_path}")

    browser_paths, rules = load_rules(config_path)

    # 3. 鎺㈡祴娴忚鍣ㄨ矾寰勶紙甯﹁嚜瀹氫箟璺緞鏀寔锛?    custom_chrome = browser_paths.get("chrome", "")
    custom_edge = browser_paths.get("edge", "")
    chrome_path = find_chrome(custom_chrome)
    edge_path = find_edge(custom_edge)

    logger.info(f"Chrome 璺緞: {chrome_path or '鏈壘鍒?}")
    logger.info(f"Edge 璺緞: {edge_path or '鏈壘鍒?}")

    # 4. 澶勭悊娴忚鍣ㄥ唴閮?URL锛堢洿鎺ヤ氦缁欏搴旀祻瑙堝櫒锛屼笉璧拌鍒欙級
    if handle_internal_url(url, edge_path, chrome_path):
        return

    # 5. 鍔犺浇瑙勫垯
    if not rules:
        logger.error("鏃犲彲鐢ㄨ鍒欙紝灏濊瘯浣跨敤绯荤粺榛樿娴忚鍣ㄦ墦寮€")
        fallback = chrome_path or edge_path or get_system_default_browser()
        if fallback:
            open_url(fallback, url)
        return

    # 6. 鎻愬彇鍩熷悕骞跺尮閰嶈鍒?    domain = extract_domain(url)
    logger.info(f"鎻愬彇鍩熷悕: {domain}")

    matched_browser = "edge"  # 榛樿鍏滃簳
    matched_rule_name = "鏃犲尮閰嶈鍒欙紙浣跨敤榛樿锛?

    for rule in rules:
        rule_domains = rule.get("domains", [])
        if match_domain(domain, rule_domains):
            matched_browser = rule.get("browser", "edge")
            matched_rule_name = rule.get("name", "鏈懡鍚嶈鍒?)
            logger.info(f"鍛戒腑瑙勫垯: [{matched_rule_name}] -> {matched_browser}")
            break

    # 7. 瑙ｆ瀽娴忚鍣ㄨ矾寰勫苟鎵撳紑
    browser_path, browser_name = resolve_browser(
        matched_browser, browser_paths, chrome_path, edge_path
    )

    if browser_path:
        logger.info(f"浣跨敤娴忚鍣? {browser_name} ({browser_path})")
        open_url(browser_path, url)
    else:
        logger.error("鏃犳硶鎵惧埌浠讳綍鍙敤娴忚鍣紝鏀惧純鎿嶄綔")


if __name__ == "__main__":
    main()

