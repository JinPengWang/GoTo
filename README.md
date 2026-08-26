<div align="center">

# GoTo

**Windows 智能浏览器路由器**

[中文](README.md) | [English](README.en.md)

![Platform](https://img.shields.io/badge/platform-Windows%2010%20%2F%2011-blue?style=flat-square)
![Go](https://img.shields.io/badge/go-1.21%2B-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.8%2B-green?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-yellow?style=flat-square)

根据域名规则，自动选择用 Chrome 或 Edge 打开外部链接。

无后台常驻进程 | 瞬间唤起秒开 | 规则可自定义 | 双击一键安装

</div>

---

## GoTo 是什么

GoTo 是一个 Windows 链接分流工具。安装后，当你从微信、QQ、邮件客户端、PDF 阅读器、Office 文档等外部应用点击网页链接时，Windows 会先调用 GoTo，GoTo 再根据 `rules.json` 中的域名规则决定使用 Chrome 还是 Edge 打开。

典型场景：

- GitHub、Google、YouTube、StackOverflow 等网站用 Chrome 打开。
- 国内网站或未命中规则的网站默认用 Edge 打开。
- `edge://`、`chrome://` 等浏览器内部链接会直接交给对应浏览器处理。
- 支持无协议链接（如 `github.com`）自动补齐并分流。

GoTo 不是后台常驻服务。它只在点击链接时启动，完成分流后立即退出。

## 下载与安装

普通用户请不要下载 GitHub 的源码 zip。请使用 Release 包。

1. 打开 [GitHub Releases](https://github.com/JinPengWang/GoTo/releases)。
2. 下载最新版本里的 **`GoTo-Windows.zip`**。
3. 解压到一个长期保留的位置，例如 `D:\Apps\GoTo`。
4. 双击 **`install.bat`**。
5. Windows 弹出管理员授权时，选择允许。

Release 包已经包含预编译好的 `GoTo.exe`。安装过程不需要 Python、Go、pip 或网络连接。

如果之后突然失效，先双击 **`repair.bat`**。它会检查文件是否存在、规则是否有效，并重新写入注册表处理器。

## 卸载

双击 **`uninstall.bat`**，按提示确认。卸载脚本会恢复安装前备份的浏览器处理器，并移除安装时写入的 QQ/微信配置，**不会误删您的程序与规则文件**。

## 功能特性

- **超快响应**：不常驻后台，零内存与 CPU 持续占用。
- **直觉通配符**：支持 `*.github.com`、`google.*` 等通用通配规则。
- **参数注入防御**：严格过滤恶意命令行参数与 `javascript:` 等不安全伪协议。
- **预置规则丰富**：内置 500+ 常见网站规则。
- **即时生效**：编辑 `rules.json` 后立即生效，无需重启。
- **安全降级**：目标浏览器找不到时自动安全降级到系统可用浏览器，杜绝循环死锁。
- **内部协议保护**：保护 `edge://`、`chrome://`、`about:` 等内部 URL。
- **Windows 深度适配**：支持 `microsoft-edge:` 链接前缀与查询参数解码。
- **应用外链优化**：安装时会自动配置 QQ、QQNT、微信优先使用系统默认浏览器。

## 调试与自检指令

在命令提示符或 PowerShell 中进入 GoTo 所在目录：

- **测试某条链接命中哪个浏览器**：
  ```bat
  GoTo.exe --test "https://github.com"
  GoTo.exe --test "bilibili.com"
  ```
- **一键校验规则与浏览器环境**：
  ```bat
  GoTo.exe --validate
  ```

## 配置规则

配置文件是 `rules.json`。

基本结构：

```json
{
  "browser_paths": {
    "chrome": "",
    "edge": ""
  },
  "rules": [
    {
      "name": "开发与外网",
      "browser": "chrome",
      "domains": [
        "github.com",
        "*.github.com",
        "google.*",
        "stackoverflow.com"
      ]
    },
    {
      "name": "兜底规则",
      "browser": "edge",
      "domains": ["*"]
    }
  ]
}
```

规则说明：

- 规则按顺序匹配，先命中先使用。
- `*` 表示兜底规则，建议放在最后。
- 支持子域名继承匹配（如 `github.com` 会自动匹配 `gist.github.com`）。
- 支持通配符匹配（如 `*.domain.com`、`domain.*`）。
- `browser` 目前支持 `chrome` 和 `edge`。
- `browser_paths` 留空时自动探测浏览器路径；探测失败时可以手动填写 exe 路径。

## 工作原理

```text
用户在外部应用中点击链接
        |
        v
Windows 查询当前默认浏览器的 URL 处理器
        |
        v
调用 GoTo.exe，并把 URL 作为参数传入
        |
        v
GoTo 清洗 URL 并比对 rules.json 规则
        |
        v
启动 Chrome 或 Edge 打开链接
        |
        v
GoTo 退出
```

## 从源码构建

普通用户不需要执行本节。

本项目支持 **Go 原生构建（推荐，极速秒开）** 与 **Python / PyInstaller 构建**：

```bat
git clone https://github.com/JinPengWang/GoTo.git
cd GoTo
build.bat
install.bat
```

`build.bat` 具备智能双引擎检测：检测到 Go 时自动构建原生极速版；未检测到 Go 时自动调用 Python 构建。

## 项目文件

```text
GoTo/
  ├── main.go                # Go 原生主程序入口
  ├── router.go              # Go 核心路由与通配符规则引擎
  ├── browser_windows.go     # Go Windows 注册表与浏览器唤起
  ├── router_test.go         # Go 单元测试套件
  ├── redirector.py          # Python 核心分流逻辑
  ├── tests/                 # Python 自动化测试套件
  ├── rules.json             # 域名分流规则文件
  ├── install.bat            # 一键安装脚本
  ├── repair.bat             # 一键修复脚本
  ├── uninstall.bat          # 安全卸载脚本
  ├── build.bat              # 智能双引擎构建脚本
  ├── build-go.bat           # Go 极速版构建脚本
  ├── requirements-build.txt # Python 构建依赖
  ├── version_info.txt       # Windows exe 版本信息
  └── .github/workflows/     # GitHub Actions 自动化 CI/CD
```

## 许可证

本项目使用 [MIT License](LICENSE)。
