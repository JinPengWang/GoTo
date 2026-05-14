<div align="center">

# GoTo

**Smart Browser Router for Windows**

![Platform](https://img.shields.io/badge/platform-Windows%2010%20%2F%2011-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.8%2B-green?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-yellow?style=flat-square)
![Size](https://img.shields.io/badge/exe_size-~6MB-orange?style=flat-square)

根据域名规则，自动将链接分发给 Chrome 或 Edge 打开。

零后台进程 · 零资源占用 · 安装即忘

</div>

---

## Why GoTo?

在国内使用 Windows，系统默认浏览器是 Edge。但 GitHub、Google、YouTube 等网站需要 Chrome 才能正常访问（通常搭配代理）。每次都要手动复制链接到 Chrome？太低效了。

GoTo 将自己注册为系统的链接处理器。点击任何链接时，Windows 自动调用 GoTo，GoTo 根据域名规则瞬间决定用 Chrome 还是 Edge 打开，然后立即退出。整个过程 < 0.5 秒，无窗口、无弹框、无感知。

---

## Features

- **Not a background process** — 由系统按需调用，执行完即退出，不常驻内存
- **Lightweight** — exe 约 6MB，启动到退出 < 0.5s
- **Invisible** — 无窗口、无托盘图标、无通知
- **500+ preset rules** — 覆盖搜索、社交、开发、学术、云服务、AI 等 18 个类别
- **Academic-friendly** — IEEE, ACM, Springer, Nature, Science, arXiv, OpenReview 等学术网站全覆盖
- **Real-time customization** — 编辑 `rules.json` 即可增删规则，无需重启
- **Smart fallback** — 目标浏览器未找到时自动降级到系统默认浏览器
- **Internal URL protection** — `edge://`、`chrome://` 等浏览器内部 URL 不受影响
- **microsoft-edge: protocol** — 自动处理 Windows 通知中心/开始菜单的强制 Edge 链接

---

## Quick Start

### Prerequisites

| Requirement | Notes |
|-------------|-------|
| Windows 10/11 | Required |
| Python 3.8+ | [Download](https://www.python.org/downloads/), check "Add Python to PATH" |
| Chrome and/or Edge | At least one installed |

### Install

```bash
git clone https://github.com/your-username/GoTo.git
cd GoTo
```

Double-click **`install.bat`** — done.

The script will: find Python → install PyInstaller → build exe → backup registry → register as link handler.

### Uninstall

Double-click **`uninstall.bat`** — everything restored to original state.

---

## How It Works

```
User clicks a link (from any app: WeChat, email, PDF reader, etc.)
    │
    ▼
Windows looks up UserChoice → finds MSEdgeHTM ProgId
    │
    ▼
MSEdgeHTM\shell\open\command → points to GoTo.exe
    │
    ▼
GoTo.exe receives URL as argument
    │
    ├─ Is it edge://, chrome://, about:?  →  Pass to corresponding browser directly
    ├─ Is it microsoft-edge:https://...?  →  Strip prefix, apply normal rules
    │
    ▼
Extract domain from URL, match against rules.json (first match wins)
    │
    ├─ Matched "chrome" rule  →  Open in Chrome
    ├─ Matched "edge" rule    →  Open in Edge
    └─ No match              →  Use fallback rule (default: Edge)
    │
    ▼
GoTo.exe exits immediately (< 0.5s)
```

---

## Configuration

The configuration file is `rules.json`. Edit it — changes take effect immediately, no restart needed.

### Structure

```json
{
    "browser_paths": {
        "chrome": "",
        "edge": ""
    },
    "rules": [
        {
            "name": "Development & Tech",
            "browser": "chrome",
            "domains": ["github.com", "stackoverflow.com"]
        },
        {
            "name": "Fallback - everything else uses Edge",
            "browser": "edge",
            "domains": ["*"]
        }
    ]
}
```

### Adding a website

Find the relevant rule group, add the domain to the `domains` array:

```json
{
    "name": "Development & Tech",
    "browser": "chrome",
    "domains": [
        "github.com",
        "stackoverflow.com",
        "mysite.com"
    ]
}
```

### Creating a new rule group

```json
{
    "name": "My Custom Sites",
    "browser": "chrome",
    "domains": [
        "notion.so",
        "figma.com",
        "linear.app"
    ]
}
```

### Forcing a site to use Edge

```json
{
    "name": "Force Edge",
    "browser": "edge",
    "domains": ["example.com"]
}
```

### Specifying browser paths manually

If auto-detection fails, set the path in `browser_paths`:

```json
{
    "browser_paths": {
        "chrome": "D:\\Apps\\Chrome\\chrome.exe",
        "edge": ""
    }
}
```

Leave empty `""` for auto-detection. Auto-detection checks: registry → `%ProgramFiles%` → `%LocalAppData%`.

### Matching rules

- Rules are matched **in order**, first match wins
- `*` matches all domains (use as fallback, always put last)
- Subdomains inherit parent rules: `gist.github.com` matches `github.com`

---

## Preset Rules (500+ domains)

| Category | Examples |
|----------|----------|
| Search & Email | google.com, gmail.com, outlook.live.com, yahoo.com |
| Video | youtube.com, vimeo.com, twitch.tv, tiktok.com |
| Social Media | twitter.com, facebook.com, instagram.com, reddit.com, linkedin.com |
| Dev & Tech | github.com, gitlab.com, stackoverflow.com, docker.com, vercel.com |
| Cloud Services | AWS, Azure, Google Cloud, Cloudflare, Fastly, Akamai |
| Academic Publishers | IEEE, ACM, Springer, Nature, Science, Elsevier, Wiley, JSTOR, arXiv, bioRxiv |
| Academic Tools | Semantic Scholar, OpenReview, Papers with Code, Overleaf, Zotero |
| AI & ML | openai.com, claude.ai, huggingface.co, pytorch.org, kaggle.com |
| Online Learning | coursera.org, edx.org, udemy.com, leetcode.com |
| Cloud & Office | notion.so, dropbox.com, slack.com, zoom.us, figma.com |
| E-Commerce | amazon.com, ebay.com, etsy.com, aliexpress.com |
| News | cnn.com, bbc.com, nytimes.com, reuters.com, bloomberg.com |
| Design | dribbble.com, behance.net, adobe.com, unsplash.com |
| VPN & Privacy | expressvpn.com, protonvpn.com, torproject.org, eff.org |

All unmatched domains default to Edge.

---

## Logging

Every invocation is logged with: timestamp, original URL, matched rule, browser used.

**Log location:** `%APPDATA%\GoTo\logs\`

Logs auto-rotate: files older than 30 days are deleted automatically.

---

## FAQ

### Links not routing after install?

1. Confirm `install.bat` ran as admin and showed "INSTALLATION COMPLETE"
2. Confirm `GoTo.exe` exists in the project directory
3. Some apps cache browser settings — restart the app
4. Check logs at `%APPDATA%\GoTo\logs\`

### Does it consume system resources?

No. GoTo is not a background process. It runs only when you click a link, exits immediately after opening the browser. No memory, no CPU, no startup entry.

### How to temporarily disable?

Run `uninstall.bat`. Re-run `install.bat` when needed. Takes seconds.

### Will it break my default browser setting?

No. GoTo only modifies the browser's command handler, not the system default browser setting. Uninstall restores everything.

### Does it work for links clicked inside Edge?

No. Links clicked inside Edge are handled by Edge internally — GoTo never sees them. This applies to Edge's built-in PDF viewer, Edge's address bar, etc. For links from **external apps** (Word, Adobe Reader, WeChat, email clients, etc.), GoTo works perfectly.

> **Tip:** For PDF files, use an external reader like Adobe Acrobat or SumatraPDF instead of opening them in Edge. Links in those PDFs will be routed by GoTo.

### Support other browsers?

Currently Chrome and Edge only. To add Firefox/Brave, modify `redirector.py`. PRs welcome.

---

## Project Structure

```
GoTo/
├── redirector.py       # Core logic
├── rules.json          # Domain rules (500+ domains)
├── install.bat         # One-click install (asks for admin)
├── uninstall.bat       # One-click uninstall
├── README.md           # This file
├── .gitignore          # Git ignore rules
└── LICENSE             # MIT License
```

After install, additional files are generated:

```
GoTo/
├── GoTo.exe            # Built executable (~6MB)
└── backup/             # Registry backups (for uninstall)
```

---

## Technical Details

### Protocol hijacking

Windows 10/11 uses `UserChoice` (with anti-tampering Hash) to determine which browser handles URLs. This cannot be directly modified. GoTo works around this by modifying the **command handler** of the current default browser's ProgId (e.g., `MSEdgeHTM`). All "open in Edge" requests go through GoTo first.

### microsoft-edge: protocol

Windows Start Menu, Notification Center, and Cortana use `microsoft-edge:` prefix to force-open links in Edge. GoTo automatically strips this prefix and applies normal routing rules.

### Internal URL protection

`edge://`, `chrome://`, `about:`, `data:`, `blob:` URLs are detected and passed directly to the corresponding browser. GoTo never interferes with browser internals.

### Graceful degradation

If the target browser is not found, GoTo falls back to the system default browser. If even that fails, the URL is passed to `os.startfile()` (Windows native). No link is ever lost.

---

## Contributing

Contributions welcome!

1. Fork this repo
2. Create a branch: `git checkout -b feature/my-feature`
3. Commit: `git commit -m 'Add my feature'`
4. Push: `git push origin feature/my-feature`
5. Open a Pull Request

---

## License

[MIT](LICENSE)

---

<div align="center">

**If this project helps you, give it a star!**

</div>
