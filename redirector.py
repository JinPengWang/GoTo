#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GoTo - 智能浏览器分发器
========================
一个轻量的 Windows 协议处理程序，根据域名规则自动选择 Chrome 或 Edge 打开链接。
安装后作为 http/https 协议处理器，由系统在点击链接时自动调用，执行完即退出。

许可证: MIT
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
# 常量定义
# ============================================================

# 程序名称
APP_NAME: str = "GoTo"

# 日志保留天数
LOG_RETENTION_DAYS: int = 30

# 默认浏览器候选路径（按优先级排列）
CHROME_CANDIDATES: List[str] = [
    os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
]

EDGE_CANDIDATES: List[str] = [
    os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
    os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
]

# 注册表中 Chrome 和 Edge 的路径键
CHROME_REGISTRY_KEYS: List[Tuple[int, str]] = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe"),
]

EDGE_REGISTRY_KEYS: List[Tuple[int, str]] = [
    (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"),
    (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe"),
]


# ============================================================
# 日志系统
# ============================================================

def get_log_dir() -> Path:
    """获取日志目录，优先使用 %APPDATA%，回退到程序所在目录。"""
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
    """删除超过 LOG_RETENTION_DAYS 天的旧日志文件。"""
    cutoff = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    try:
        for log_file in log_dir.glob("*.log"):
            try:
                # 从文件名解析日期：goto_YYYY-MM-DD.log
                date_str = log_file.stem.split("_")[-1]
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                if file_date < cutoff:
                    log_file.unlink(missing_ok=True)
            except (ValueError, OSError):
                continue
    except Exception:
        pass


def setup_logger() -> logging.Logger:
    """配置并返回日志记录器。"""
    log_dir = get_log_dir()
    cleanup_old_logs(log_dir)

    today = datetime.now().strftime("%Y-%m-%d")

    logger = logging.getLogger(APP_NAME)
    logger.setLevel(logging.DEBUG)

    # 避免重复添加 handler
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
# 路径工具（兼容 PyInstaller 打包）
# ============================================================

def get_app_dir() -> Path:
    """
    获取应用程序所在目录。
    PyInstaller --onefile 打包后 __file__ 指向临时目录，
    需要用 sys.executable 获取真正的 exe 路径。
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后
        return Path(sys.executable).parent
    else:
        # 源码运行
        return Path(__file__).parent


# 全局日志实例
logger = setup_logger()


# ============================================================
# 浏览器路径探测
# ============================================================

def read_registry_path(hive: int, sub_key: str) -> Optional[str]:
    """从 Windows 注册表读取默认值。"""
    try:
        with winreg.OpenKey(hive, sub_key) as key:
            value, _ = winreg.QueryValueEx(key, "")
            if value and os.path.isfile(value):
                return value
    except (OSError, FileNotFoundError, TypeError):
        pass
    return None


def find_browser_by_registry(keys: List[Tuple[int, str]]) -> Optional[str]:
    """通过注册表查找浏览器路径。"""
    for hive, sub_key in keys:
        path = read_registry_path(hive, sub_key)
        if path:
            return path
    return None


def find_browser_by_candidates(candidates: List[str]) -> Optional[str]:
    """从候选路径列表中查找第一个存在的浏览器。"""
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def find_chrome(custom_path: str = "") -> Optional[str]:
    """
    查找 Chrome 浏览器路径。
    优先级：用户自定义路径 > 注册表 > 候选路径列表
    """
    if custom_path and os.path.isfile(custom_path):
        return custom_path

    registry_path = find_browser_by_registry(CHROME_REGISTRY_KEYS)
    if registry_path:
        return registry_path

    return find_browser_by_candidates(CHROME_CANDIDATES)


def find_edge(custom_path: str = "") -> Optional[str]:
    """
    查找 Edge 浏览器路径。
    优先级：用户自定义路径 > 注册表 > 候选路径列表
    """
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
    """获取系统默认浏览器路径（用于降级）。"""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice"
        ) as key:
            prog_id, _ = winreg.QueryValueEx(key, "ProgId")
        # 尝试从 ProgId 解析实际路径
        command_key = rf"{prog_id}\shell\open\command"
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, command_key) as key:
            command, _ = winreg.QueryValueEx(key, "")
            # 提取引号内的路径
            match = re.match(r'"([^"]+)"', command)
            if match and os.path.isfile(match.group(1)) and not is_goto_executable(match.group(1)):
                return match.group(1)
            # 无引号时取第一个空格前的部分
            parts = command.split()
            if parts and os.path.isfile(parts[0]) and not is_goto_executable(parts[0]):
                return parts[0]
    except (OSError, FileNotFoundError, TypeError, IndexError):
        pass
    return None


# ============================================================
# 配置文件加载
# ============================================================

def get_config_path() -> Path:
    """
    获取配置文件路径。
    优先级：程序同目录 > %APPDATA%
    """
    # 首先检查程序同目录
    exe_dir = get_app_dir()
    local_config = exe_dir / "rules.json"
    if local_config.is_file():
        return local_config

    # 然后检查 %APPDATA%
    appdata = os.environ.get("APPDATA")
    if appdata:
        appdata_config = Path(appdata) / APP_NAME / "rules.json"
        if appdata_config.is_file():
            return appdata_config

    # 都不存在时返回程序同目录路径（后续会报错）
    return local_config


def load_rules(config_path: Path) -> Tuple[Dict[str, str], List[Dict[str, Any]]]:
    """
    加载配置文件，返回 (浏览器路径配置, 规则列表)。

    Returns:
        (browser_paths, rules): 浏览器自定义路径字典和规则列表
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"配置文件加载失败: {e}")
        return {}, []

    browser_paths = data.get("browser_paths", {})
    rules = data.get("rules", [])

    if not rules:
        logger.warning("配置文件中没有找到任何规则")

    return browser_paths, rules


# ============================================================
# 域名匹配
# ============================================================

def extract_domain(url: str) -> str:
    """
    从 URL 中提取域名（小写，去除 www. 前缀）。

    Args:
        url: 完整的 URL 字符串

    Returns:
        提取的域名字符串
    """
    try:
        parsed = urlparse(url)
        domain = parsed.hostname or ""
        domain = domain.lower()
        # 去除 www. 前缀以便统一匹配
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def match_domain(domain: str, patterns: List[str]) -> bool:
    """
    检查域名是否匹配任一模式。

    支持：
    - 完整匹配: "github.com" 匹配 "github.com"
    - 子域名匹配: "gist.github.com" 匹配 "github.com"
    - 通配符: "*" 匹配所有域名

    Args:
        domain: 待匹配的域名
        patterns: 域名模式列表

    Returns:
        是否匹配成功
    """
    for pattern in patterns:
        pattern = pattern.lower().strip()
        if pattern == "*":
            return True
        # 完整匹配或子域名匹配
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
    根据目标浏览器名称返回实际路径。

    Args:
        target: 目标浏览器名称 ("chrome" 或 "edge")
        browser_paths: 用户自定义路径配置
        chrome_path: 已探测到的 Chrome 路径
        edge_path: 已探测到的 Edge 路径

    Returns:
        (浏览器路径, 浏览器名称) 的元组
    """
    if target == "chrome":
        path = chrome_path
        name = "Google Chrome"
    elif target == "edge":
        path = edge_path
        name = "Microsoft Edge"
    else:
        path = None
        name = "未知"

    if path and os.path.isfile(path):
        return path, name

    # 目标浏览器未找到，尝试降级
    logger.warning(f"{name} 未找到，尝试降级到系统默认浏览器")
    fallback_candidates: List[Tuple[Optional[str], str]] = []
    if target == "chrome":
        fallback_candidates.append((edge_path, "Microsoft Edge"))
    elif target == "edge":
        fallback_candidates.append((chrome_path, "Google Chrome"))

    fallback_candidates.append((get_system_default_browser(), "system default"))

    for fallback, fallback_name in fallback_candidates:
        if fallback and os.path.isfile(fallback) and not is_goto_executable(fallback):
            return fallback, f"{fallback_name}({Path(fallback).stem})"

    logger.error("没有可用的浏览器")
    return None, "无"


# ============================================================
# 链接打开
# ============================================================

def open_url(browser_path: str, url: str) -> None:
    """
    使用指定浏览器打开 URL。

    Args:
        browser_path: 浏览器可执行文件路径
        url: 要打开的 URL
    """
    try:
        # 使用 Popen 启动浏览器，不等待其关闭
        subprocess.Popen(
            [browser_path, url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
        )
        logger.info(f"已启动浏览器: {browser_path}")
    except Exception as e:
        logger.error(f"启动浏览器失败: {e}")
        # 最后尝试使用 os.startfile（Windows 特有）
        try:
            os.startfile(url)  # type: ignore[attr-defined]
            logger.info("已通过系统默认方式打开 URL")
        except Exception as e2:
            logger.error(f"所有打开方式均失败: {e2}")


# ============================================================
# 内部 URL 检测
# ============================================================

# 这些协议/前缀应直接交给对应浏览器，不做规则匹配
EDGE_INTERNAL_PREFIXES: Tuple[str, ...] = (
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
    检测并处理浏览器内部 URL（如 edge://settings）。
    这类 URL 必须交给对应浏览器直接处理，不能走规则匹配。

    Returns:
        True 表示已处理（调用了浏览器），False 表示不是内部 URL
    """
    url_lower = url.lower()

    # Edge 内部 URL → 直接交给 Edge
    if any(url_lower.startswith(p) for p in EDGE_INTERNAL_PREFIXES):
        if edge_path:
            logger.info(f"Edge 内部 URL，直接交给 Edge: {url}")
            open_url(edge_path, url)
            return True
        logger.warning("Edge 内部 URL 但 Edge 未找到")

    # Chrome 内部 URL → 直接交给 Chrome
    if any(url_lower.startswith(p) for p in CHROME_INTERNAL_PREFIXES):
        if chrome_path:
            logger.info(f"Chrome 内部 URL，直接交给 Chrome: {url}")
            open_url(chrome_path, url)
            return True
        logger.warning("Chrome 内部 URL 但 Chrome 未找到")

    # about: 等通用内部 URL → 交给系统默认浏览器
    if any(url_lower.startswith(p) for p in OTHER_INTERNAL_PREFIXES):
        logger.info(f"内部 URL，交给系统默认浏览器: {url}")
        fallback = chrome_path or edge_path or get_system_default_browser()
        if fallback:
            open_url(fallback, url)
            return True

    return False


# ============================================================
# 自修复
# ============================================================

def self_repair() -> None:
    """
    检查并修复 GoTo 的注册表注册。
    由计划任务定期调用，或通过 --self-repair 标志手动触发。
    只写入 HKCU（无需管理员权限）。
    """
    try:
        # 检测当前默认浏览器 ProgId
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice"
        ) as key:
            prog_id, _ = winreg.QueryValueEx(key, "ProgId")
    except (OSError, FileNotFoundError):
        prog_id = "MSEdgeHTM"

    exe_path = str(Path(sys.executable).resolve()) if getattr(sys, 'frozen', False) else str(get_app_dir() / "GoTo.exe")
    new_cmd = f'"{exe_path}" "%1"'

    # 检查当前 HKCU 处理器是否已指向 GoTo
    user_cmd_key = rf"Software\Classes\{prog_id}\shell\open\command"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, user_cmd_key) as key:
            current_cmd, _ = winreg.QueryValueEx(key, "")
            if "GoTo.exe" in current_cmd.lower():
                logger.debug("注册表正常，无需修复")
                return
    except (OSError, FileNotFoundError):
        pass

    # 需要修复：写入 HKCU（无需管理员权限）
    logger.info(f"修复注册表: {prog_id} -> GoTo.exe")
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, user_cmd_key, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, new_cmd)
        logger.info("HKCU 修复成功")
    except OSError as e:
        logger.error(f"HKCU 修复失败: {e}")

    # 尝试写入 HKCR（可能需要管理员权限，失败不报错）
    for key_path in [
        rf"{prog_id}\shell\open\command",
        r"http\shell\open\command",
        r"https\shell\open\command",
    ]:
        try:
            with winreg.CreateKeyEx(winreg.HKEY_CLASSES_ROOT, key_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, new_cmd)
        except OSError:
            pass


# ============================================================
# 主流程
# ============================================================

def clean_url(raw: str) -> str:
    """
    清理 URL 参数，处理各种边界情况：
    - 去除首尾引号
    - 去除首尾空白
    - 处理 microsoft-edge: 前缀（Windows 有时会添加）
    """
    url = raw.strip().strip('"').strip("'")

    # 处理 microsoft-edge: 协议前缀
    # Windows 通知中心、开始菜单等会用 microsoft-edge:https://... 的形式
    prefixes_to_strip = [
        "microsoft-edge://",
        "microsoft-edge:",
    ]
    for prefix in prefixes_to_strip:
        if url.lower().startswith(prefix):
            url = url[len(prefix):]
            # 如果去掉前缀后不是 http(s):// 开头，补上 https://
            if not url.lower().startswith(("http://", "https://")):
                url = "https://" + url
            break

    return url


def main() -> None:
    """主入口函数。"""
    # 处理特殊标志
    if len(sys.argv) >= 2 and sys.argv[1] in ("--self-repair", "--maintain"):
        self_repair()
        return

    # 1. 获取 URL 参数
    if len(sys.argv) < 2:
        logger.warning("未接收到 URL 参数，退出")
        return

    url = clean_url(sys.argv[1])
    if not url:
        logger.warning("URL 参数为空，退出")
        return

    logger.info(f"收到链接: {url}")

    # 2. 加载配置
    config_path = get_config_path()
    logger.info(f"配置文件: {config_path}")

    browser_paths, rules = load_rules(config_path)

    # 3. 探测浏览器路径（带自定义路径支持）
    custom_chrome = browser_paths.get("chrome", "")
    custom_edge = browser_paths.get("edge", "")
    chrome_path = find_chrome(custom_chrome)
    edge_path = find_edge(custom_edge)

    logger.info(f"Chrome 路径: {chrome_path or '未找到'}")
    logger.info(f"Edge 路径: {edge_path or '未找到'}")

    # 4. 处理浏览器内部 URL（直接交给对应浏览器，不走规则）
    if handle_internal_url(url, edge_path, chrome_path):
        return

    # 5. 加载规则
    if not rules:
        logger.error("无可用规则，尝试使用系统默认浏览器打开")
        fallback = chrome_path or edge_path or get_system_default_browser()
        if fallback:
            open_url(fallback, url)
        return

    # 6. 提取域名并匹配规则
    domain = extract_domain(url)
    logger.info(f"提取域名: {domain}")

    matched_browser = "edge"  # 默认兜底
    matched_rule_name = "无匹配规则（使用默认）"

    for rule in rules:
        rule_domains = rule.get("domains", [])
        if match_domain(domain, rule_domains):
            matched_browser = rule.get("browser", "edge")
            matched_rule_name = rule.get("name", "未命名规则")
            logger.info(f"命中规则: [{matched_rule_name}] -> {matched_browser}")
            break

    # 7. 解析浏览器路径并打开
    browser_path, browser_name = resolve_browser(
        matched_browser, browser_paths, chrome_path, edge_path
    )

    if browser_path:
        logger.info(f"使用浏览器: {browser_name} ({browser_path})")
        open_url(browser_path, url)
    else:
        logger.error("无法找到任何可用浏览器，放弃操作")


if __name__ == "__main__":
    main()
