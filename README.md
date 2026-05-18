<div align="center">

# GoTo

**Windows 智能浏览器路由器**

[中文](README.md) | [English](README.en.md)

![Platform](https://img.shields.io/badge/platform-Windows%2010%20%2F%2011-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.8%2B%20build%20only-green?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-yellow?style=flat-square)

根据域名规则，自动选择用 Chrome 或 Edge 打开外部链接。

无后台常驻进程 | 双击安装 | 规则可自定义

</div>

---

## GoTo 是什么

GoTo 是一个 Windows 链接分流工具。安装后，当你从微信、QQ、邮件客户端、PDF 阅读器、Office 文档等外部应用点击网页链接时，Windows 会先调用 GoTo，GoTo 再根据 `rules.json` 中的域名规则决定使用 Chrome 还是 Edge 打开。

典型场景：

- GitHub、Google、YouTube 等网站用 Chrome 打开。
- 国内网站或未命中规则的网站默认用 Edge 打开。
- `edge://`、`chrome://` 等浏览器内部链接会直接交给对应浏览器处理。

GoTo 不是后台服务。它只在点击链接时启动，完成分流后立即退出。

## 下载与安装

普通用户请不要下载 GitHub 的源码 zip。请使用 Release 包。

1. 打开 [GitHub Releases](https://github.com/JinPengWang/GoTo/releases)。
2. 下载最新版本里的 **`GoTo-Windows.zip`**。
3. 解压到一个长期保留的位置，例如 `D:\Apps\GoTo`。
4. 双击 **`install.bat`**。
5. Windows 弹出管理员授权时，选择允许。

Release 包已经包含 `GoTo.exe`。安装过程不需要 Python、pip、PyInstaller 或网络连接。

如果之后突然失效，先双击 **`repair.bat`**。它会检查文件是否存在、规则是否有效，并重新写入注册表处理器。

## 卸载

双击 **`uninstall.bat`**，按提示确认。卸载脚本会尽量恢复安装前备份的浏览器处理器，并移除安装时写入的 QQ/微信配置。

## 功能

- 按域名规则自动选择 Chrome 或 Edge。
- 不常驻后台，不占用持续内存和 CPU。
- 预置 500+ 常见网站规则。
- 编辑 `rules.json` 后立即生效。
- 目标浏览器找不到时自动降级到可用浏览器。
- 保护 `edge://`、`chrome://`、`about:` 等内部 URL。
- 支持 `microsoft-edge:` 链接前缀的常规化处理。
- 安装时会尝试让 QQ、QQNT、微信使用系统默认浏览器打开外部链接。

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
      "name": "Development",
      "browser": "chrome",
      "domains": ["github.com", "stackoverflow.com"]
    },
    {
      "name": "Fallback",
      "browser": "edge",
      "domains": ["*"]
    }
  ]
}
```

规则说明：

- 规则按顺序匹配，先命中先使用。
- `*` 表示兜底规则，建议放在最后。
- 子域名会继承父域名规则，例如 `gist.github.com` 会匹配 `github.com`。
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
GoTo 读取 rules.json，提取域名并匹配规则
        |
        v
启动 Chrome 或 Edge 打开链接
        |
        v
GoTo 退出
```

安装脚本会修改当前默认浏览器 ProgId 的 `shell\open\command`。这是 GoTo 能拦截外部应用链接的关键。脚本会先备份原始注册表项，卸载时再尝试恢复。

## 安全与杀毒软件

GoTo 是开源项目，但 Release 中的 `GoTo.exe` 目前未做代码签名。Windows SmartScreen 或杀毒软件可能因为“未签名可执行文件”和“修改浏览器处理器注册表”而给出警告。

建议：

- 只从本项目的 GitHub Releases 下载。
- 对照 Release 包里的 `SHA256SUMS.txt` 验证文件完整性。
- 如果 `GoTo.exe` 安装后消失，检查 Windows Security 的保护历史或杀毒软件隔离区。
- 不建议关闭杀毒软件；如果误报，请基于源码和哈希自行判断是否信任。

## 常见问题

### 安装失败，提示找不到 GoTo.exe

你下载的可能是 GitHub 源码 zip。普通用户请下载 Releases 页面中的 `GoTo-Windows.zip`。

### 链接突然不再分流

先运行 `repair.bat`。如果仍然失败，检查：

- `GoTo.exe` 是否还在安装目录。
- `rules.json` 是否是合法 JSON。
- Windows Security 或杀毒软件是否隔离了 `GoTo.exe`。
- 点击链接的应用是否缓存了浏览器设置，必要时重启该应用。

### QQ 或微信仍然用内置浏览器打开

GoTo 只能处理交给 Windows 默认浏览器的链接。QQ、微信的部分链接会绕过 Windows 协议处理器，直接在内置浏览器中打开。安装脚本会写入 `UseDefaultBrowser = 1`，但某些小程序、公众号或支付相关链接仍可能被应用锁定，这是应用自身限制。

### 点击 Edge 内部页面的链接是否会被分流

不会。浏览器内部打开的链接通常由浏览器自己处理，GoTo 主要处理外部应用发起的 URL 打开请求。

## 从源码构建

普通用户不需要执行本节。

```bat
git clone https://github.com/JinPengWang/GoTo.git
cd GoTo
python -m pip install -r requirements-build.txt
build.bat
install.bat
```

`build.bat` 会生成 `GoTo.exe` 和 `SHA256SUMS.txt`。安装脚本本身不会联网安装构建依赖。

## 项目文件

```text
GoTo/
  redirector.py              核心分流逻辑
  rules.json                 域名规则
  install.bat                用户安装脚本
  repair.bat                 修复脚本
  uninstall.bat              卸载脚本
  build.bat                  开发者构建脚本
  requirements-build.txt     构建依赖
  version_info.txt           Windows exe 版本信息
  .github/workflows/         Release 自动打包
```

不会提交到仓库的本机生成物：

```text
GoTo.exe
backup/
logs/
build/
dist/
__pycache__/
```

## 许可证

本项目使用 [MIT License](LICENSE)。
