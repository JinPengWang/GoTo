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
import fnmatch
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Tuple, List, Dict, Any
from urllib.parse import urlparse, parse_qs, unquote

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

# 内部/专用协议前缀
EDGE_INTERNAL_PREFIXES: Tuple[str, ...] = (
    "edge://",
    "microsoft-edge://",
    "microsoft-edge:",
)

CHROME_INTERNAL_PREFIXES: Tuple[str, ...] = (
    "chrome://",
    "chrome-extension://",
)

SAFE_INTERNAL_PREFIXES: Tuple[str, ...] = (
    "about:",
)

# 危险伪协议（直接拒绝处理，防止脚本执行攻击）
DANGEROUS_PREFIXES: Tuple[str, ...] = (
    "javascript:",
    "data:",
    "vbscript:",
    "blob:",
)


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
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent


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
    """删除超过 LOG_RETENTION_DAYS 天的旧日志文件（在维护任务中调用）。"""
    cutoff = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    try:
        for log_file in log_dir.glob("*.log"):
            try:
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
    today = datetime.now().strftime("%Y-%m-%d")

    logger = logging.getLogger(APP_NAME)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        handler: logging.Handler = logging.NullHandler()
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

        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


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
        if path and os.path.isfile(path):
            return path
    return None


def find_chrome(custom_path: str = "") -> Optional[str]:
    """查找 Chrome 浏览器路径。"""
    if custom_path and os.path.isfile(custom_path):
        return custom_path

    registry_path = find_browser_by_registry(CHROME_REGISTRY_KEYS)
    if registry_path:
        return registry_path

    return find_browser_by_candidates(CHROME_CANDIDATES)


def find_edge(custom_path: str = "") -> Optional[str]:
    """查找 Edge 浏览器路径。"""
    if custom_path and os.path.isfile(custom_path):
        return custom_path

    registry_path = find_browser_by_registry(EDGE_REGISTRY_KEYS)
    if registry_path:
        return registry_path

    return find_browser_by_candidates(EDGE_CANDIDATES)


def is_goto_executable(path: str) -> bool:
    """判断路径是否指向当前 GoTo 可执行文件，防止循环调用。"""
    if not path:
        return False

    candidates = [Path(sys.executable)]
    if not getattr(sys, "frozen", False):
        candidates.append(get_app_dir() / "GoTo.exe")

    try:
        target = Path(path).resolve()
        return any(target == candidate.resolve() for candidate in candidates)
    except OSError:
        target_str = os.path.normcase(os.path.abspath(path))
        return any(
            target_str == os.path.normcase(os.path.abspath(str(c)))
            for c in candidates
        )


def get_system_default_browser() -> Optional[str]:
    """获取系统默认浏览器路径（用于安全降级）。"""
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice"
        ) as key:
            prog_id, _ = winreg.QueryValueEx(key, "ProgId")

        command_key = rf"{prog_id}\shell\open\command"
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, command_key) as key:
            command, _ = winreg.QueryValueEx(key, "")
            match = re.match(r'"([^"]+)"', command)
            if match and os.path.isfile(match.group(1)) and not is_goto_executable(match.group(1)):
                return match.group(1)
            parts = command.split()
            if parts and os.path.isfile(parts[0]) and not is_goto_executable(parts[0]):
                return parts[0]
    except (OSError, FileNotFoundError, TypeError, IndexError):
        pass
    return None


# ============================================================
# 配置文件加载与校验
# ============================================================

def get_config_path() -> Path:
    """获取配置文件路径，优先程序同目录，其次 %APPDATA%。"""
    exe_dir = get_app_dir()
    local_config = exe_dir / "rules.json"
    if local_config.is_file():
        return local_config

    appdata = os.environ.get("APPDATA")
    if appdata:
        appdata_config = Path(appdata) / APP_NAME / "rules.json"
        if appdata_config.is_file():
            return appdata_config

    return local_config


def load_rules(config_path: Path) -> Tuple[Dict[str, str], List[Dict[str, Any]]]:
    """加载配置文件，返回 (浏览器路径配置, 规则列表)。"""
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
# URL 清洗与域名匹配
# ============================================================

def clean_url(raw: str) -> str:
    """
    清洗与标准化 URL 参数，处理各种边界情况：
    - 去除首尾空白与引号
    - 拦截以 - 或 -- 开头的 Chromium 命令行参数注入攻击
    - 拦截危险伪协议（javascript:, data:, vbscript:）
    - 剥离并解码 microsoft-edge: 前缀（含 ?url= 参数）
    - 自动为缺少协议头的链接补充 https://
    """
    if not raw:
        return ""

    url = raw.strip().strip('"').strip("'").strip()

    # 安全检查：拦截参数注入攻击（不能以 - 或 -- 开头）
    if url.startswith("-"):
        logger.warning(f"安全拦截：检测到可能的命令行参数注入: {url}")
        return ""

    url_lower = url.lower()

    # 安全检查：拦截危险脚本伪协议
    if any(url_lower.startswith(prefix) for prefix in DANGEROUS_PREFIXES):
        logger.warning(f"安全拦截：检测到不安全的伪协议: {url}")
        return ""

    # 处理 microsoft-edge: 协议前缀
    if url_lower.startswith("microsoft-edge:"):
        rest = url[len("microsoft-edge:"):].lstrip("/")
        # 处理 ?url=https%3A%2F%2F... 或 url=... 形式
        if rest.startswith("?") or rest.startswith("url="):
            query_str = rest.lstrip("?")
            params = parse_qs(query_str)
            if "url" in params and params["url"]:
                url = unquote(params["url"][0])
            else:
                url = unquote(rest)
        else:
            url = unquote(rest)
        url = url.strip()

    # 如果是浏览器内部协议或合法协议，保持原样
    if url.lower().startswith(("http://", "https://", "edge://", "chrome://", "chrome-extension://", "about:")):
        return url

    # 缺乏协议头且不是内部协议时，默认为 https://
    if url and "://" not in url and not url.startswith("/"):
        url = "https://" + url

    return url


def extract_domain(url: str) -> str:
    """从 URL 中提取域名（小写，去除 www. 前缀，兼容无协议头 URL）。"""
    if not url:
        return ""

    target_url = url
    if "://" not in target_url and not target_url.startswith(("/", "\\")):
        target_url = "https://" + target_url

    try:
        parsed = urlparse(target_url)
        domain = parsed.hostname or ""
        domain = domain.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def match_domain(domain: str, patterns: List[str]) -> bool:
    """
    检查域名是否匹配任一模式。

    支持：
    - 通配符全匹配: "*" 匹配所有
    - 直觉通配符模式: "*.github.com", "google.*"
    - 完整域名匹配: "github.com" 匹配 "github.com"
    - 子域名自动继承: "gist.github.com" 匹配 "github.com"
    """
    if not domain:
        return False

    domain = domain.lower().strip()

    for pattern in patterns:
        p = pattern.lower().strip()
        if p == "*":
            return True

        # 支持 *.domain.com 形式
        if p.startswith("*."):
            root = p[2:]
            if domain == root or domain.endswith("." + root) or fnmatch.fnmatch(domain, p):
                return True
        elif "*" in p:
            if fnmatch.fnmatch(domain, p):
                return True
        else:
            # 完整匹配或子域名继承匹配
            if domain == p or domain.endswith("." + p):
                return True

    return False


def resolve_browser(
    target: str,
    browser_paths: Dict[str, str],
    chrome_path: Optional[str],
    edge_path: Optional[str]
) -> Tuple[Optional[str], str]:
    """根据目标浏览器名称解析实际可用路径与名称。"""
    target_clean = (target or "").lower().strip()

    if target_clean == "chrome":
        path = chrome_path
        name = "Google Chrome"
    elif target_clean == "edge":
        path = edge_path
        name = "Microsoft Edge"
    else:
        # 支持 rules.json 中自定义的其他浏览器名称（如 "firefox", "brave"）
        custom = browser_paths.get(target_clean, "")
        if custom and os.path.isfile(custom):
            return custom, target_clean
        path = None
        name = target_clean or "未知"

    if path and os.path.isfile(path):
        return path, name

    # 目标浏览器未找到，尝试降级
    logger.warning(f"{name} 未找到，尝试降级到可用浏览器")
    fallback_candidates: List[Tuple[Optional[str], str]] = []
    if target_clean == "chrome":
        fallback_candidates.append((edge_path, "Microsoft Edge"))
    elif target_clean == "edge":
        fallback_candidates.append((chrome_path, "Google Chrome"))

    fallback_candidates.append((get_system_default_browser(), "系统默认浏览器"))

    for fallback, fallback_name in fallback_candidates:
        if fallback and os.path.isfile(fallback) and not is_goto_executable(fallback):
            return fallback, f"{fallback_name}({Path(fallback).stem})"

    logger.error("没有可用的浏览器")
    return None, "无"


# ============================================================
# 链接打开
# ============================================================

def open_url(browser_path: str, url: str) -> bool:
    """使用指定浏览器打开 URL（防止参数注入与 Fork 炸弹递归）。"""
    if not browser_path or not os.path.isfile(browser_path):
        logger.error(f"浏览器路径无效: {browser_path}")
        return False

    if is_goto_executable(browser_path):
        logger.error("拒绝将请求重新分发给 GoTo 本身（防止循环调用）")
        return False

    try:
        # 启动浏览器进程
        subprocess.Popen(
            [browser_path, url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
        )
        logger.info(f"已启动浏览器: {browser_path}")
        return True
    except Exception as e:
        logger.error(f"启动浏览器失败: {e}")
        # 注意：此处坚决不能调用 os.startfile(url)，否则会触发 Fork 炸弹无限递归
        return False


def handle_internal_url(url: str, edge_path: Optional[str], chrome_path: Optional[str]) -> bool:
    """检测并直接处理内部 URL（如 edge://settings）。"""
    url_lower = url.lower()

    if any(url_lower.startswith(p) for p in EDGE_INTERNAL_PREFIXES):
        if edge_path:
            logger.info(f"Edge 内部 URL，直接交给 Edge: {url}")
            return open_url(edge_path, url)
        logger.warning("Edge 内部 URL 但 Edge 未找到")

    if any(url_lower.startswith(p) for p in CHROME_INTERNAL_PREFIXES):
        if chrome_path:
            logger.info(f"Chrome 内部 URL，直接交给 Chrome: {url}")
            return open_url(chrome_path, url)
        logger.warning("Chrome 内部 URL 但 Chrome 未找到")

    if any(url_lower.startswith(p) for p in SAFE_INTERNAL_PREFIXES):
        logger.info(f"内部 URL，交给系统默认浏览器: {url}")
        fallback = chrome_path or edge_path or get_system_default_browser()
        if fallback:
            return open_url(fallback, url)

    return False


# ============================================================
# 自修复与维护
# ============================================================

def self_repair() -> None:
    """检查并修复 GoTo 的注册表注册与日志清理（只写入 HKCU，无需管理员权限）。"""
    # 顺便清理旧日志
    cleanup_old_logs(get_log_dir())

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice"
        ) as key:
            prog_id, _ = winreg.QueryValueEx(key, "ProgId")
    except (OSError, FileNotFoundError):
        prog_id = "MSEdgeHTM"

    exe_path = str(Path(sys.executable).resolve()) if getattr(sys, 'frozen', False) else str(get_app_dir() / "GoTo.exe")
    new_cmd = f'"{exe_path}" "%1"'

    user_cmd_key = rf"Software\Classes\{prog_id}\shell\open\command"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, user_cmd_key) as key:
            current_cmd, _ = winreg.QueryValueEx(key, "")
            if "GoTo.exe" in current_cmd:
                logger.debug("注册表正常，无需修复")
                return
    except (OSError, FileNotFoundError):
        pass

    logger.info(f"修复注册表: {prog_id} -> GoTo.exe")
    try:
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, user_cmd_key, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, new_cmd)
        logger.info("HKCU 修复成功")
    except OSError as e:
        logger.error(f"HKCU 修复失败: {e}")


# ============================================================
# 调试与校验命令
# ============================================================

def run_test_mode(target_url: str) -> None:
    """命令行测试模式：打印 URL 解析与规则命中详情，不实际启动浏览器。"""
    print("\n============================================================")
    print("  GoTo - 规则匹配测试 (Test Mode)")
    print("============================================================\n")

    cleaned = clean_url(target_url)
    print(f"原始 URL:    {target_url}")
    print(f"清洗后 URL:  {cleaned or '[被安全拦截/无效]'}")

    if not cleaned:
        print("\n[结果] URL 无效或被安全机制拦截。")
        return

    domain = extract_domain(cleaned)
    print(f"提取域名:    {domain or '[无域名]'}")

    config_path = get_config_path()
    print(f"配置文件:    {config_path}")

    browser_paths, rules = load_rules(config_path)
    chrome_path = find_chrome(browser_paths.get("chrome", ""))
    edge_path = find_edge(browser_paths.get("edge", ""))

    print(f"Chrome 路径: {chrome_path or '未检测到'}")
    print(f"Edge 路径:   {edge_path or '未检测到'}")
    print("------------------------------------------------------------")

    # 检查是否为内部 URL
    url_lower = cleaned.lower()
    if any(url_lower.startswith(p) for p in EDGE_INTERNAL_PREFIXES):
        print("命中类型:    Edge 内部链接 -> Microsoft Edge")
        print(f"预计使用:    {edge_path or '无可用路径'}")
        return

    if any(url_lower.startswith(p) for p in CHROME_INTERNAL_PREFIXES):
        print("命中类型:    Chrome 内部链接 -> Google Chrome")
        print(f"预计使用:    {chrome_path or '无可用路径'}")
        return

    matched_browser = "edge"
    matched_rule_name = "兜底（无匹配规则）"

    for rule in rules:
        rule_domains = rule.get("domains", [])
        if match_domain(domain, rule_domains):
            matched_browser = rule.get("browser", "edge")
            matched_rule_name = rule.get("name", "未命名规则")
            break

    browser_path, browser_name = resolve_browser(
        matched_browser, browser_paths, chrome_path, edge_path
    )

    print(f"命中规则:    [{matched_rule_name}]")
    print(f"目标浏览器:  {matched_browser}")
    print(f"实际分发给:  {browser_name}")
    print(f"执行文件:    {browser_path or '未找到可用浏览器'}")
    print("\n============================================================\n")


def run_validate_mode() -> None:
    """校验 rules.json 语法及浏览器可用性。"""
    print("\n============================================================")
    print("  GoTo - 配置文件校验 (Validate Mode)")
    print("============================================================\n")

    config_path = get_config_path()
    print(f"检查文件: {config_path}")

    if not config_path.exists():
        print("[错误] rules.json 文件不存在！\n")
        return

    browser_paths, rules = load_rules(config_path)
    print(f"规则总数: {len(rules)} 组")

    total_domains = sum(len(r.get("domains", [])) for r in rules)
    print(f"域名总数: {total_domains} 个")

    chrome_path = find_chrome(browser_paths.get("chrome", ""))
    edge_path = find_edge(browser_paths.get("edge", ""))

    print(f"Chrome 状态: {'[OK] ' + chrome_path if chrome_path else '[未检测到]'}")
    print(f"Edge 状态:   {'[OK] ' + edge_path if edge_path else '[未检测到]'}")
    print("\n[OK] 配置文件格式正确。\n")


# ============================================================
# 主流程
# ============================================================

def main() -> None:
    """主入口函数。"""
    # 1. 命令行参数处理
    if len(sys.argv) >= 2:
        arg1 = sys.argv[1].strip()
        if arg1 in ("--self-repair", "--maintain"):
            self_repair()
            return
        elif arg1 == "--validate":
            run_validate_mode()
            return
        elif arg1 == "--test" and len(sys.argv) >= 3:
            run_test_mode(sys.argv[2])
            return

    # 2. 获取 URL 参数
    if len(sys.argv) < 2:
        logger.warning("未接收到 URL 参数，退出")
        return

    raw_url = " ".join(sys.argv[1:]) if len(sys.argv) > 2 else sys.argv[1]
    url = clean_url(raw_url)
    if not url:
        logger.warning("URL 参数无效或被拦截，退出")
        return

    logger.info(f"收到链接: {url}")

    # 3. 加载配置
    config_path = get_config_path()
    browser_paths, rules = load_rules(config_path)

    # 4. 探测浏览器路径
    custom_chrome = browser_paths.get("chrome", "")
    custom_edge = browser_paths.get("edge", "")
    chrome_path = find_chrome(custom_chrome)
    edge_path = find_edge(custom_edge)

    # 5. 处理浏览器内部 URL
    if handle_internal_url(url, edge_path, chrome_path):
        return

    # 6. 无规则时降级
    if not rules:
        logger.error("无可用规则，尝试使用系统默认浏览器打开")
        fallback = chrome_path or edge_path or get_system_default_browser()
        if fallback:
            open_url(fallback, url)
        return

    # 7. 提取域名并匹配规则
    domain = extract_domain(url)
    logger.info(f"提取域名: {domain}")

    matched_browser = "edge"
    matched_rule_name = "无匹配规则（使用默认）"

    for rule in rules:
        rule_domains = rule.get("domains", [])
        if match_domain(domain, rule_domains):
            matched_browser = rule.get("browser", "edge")
            matched_rule_name = rule.get("name", "未命名规则")
            logger.info(f"命中规则: [{matched_rule_name}] -> {matched_browser}")
            break

    # 8. 解析浏览器路径并打开
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
