<div align="center">

# GoTo

**Smart Windows Browser Router**

[中文](README.md) | [English](README.en.md)

![Platform](https://img.shields.io/badge/platform-Windows%2010%20%2F%2011-blue?style=flat-square)
![Go](https://img.shields.io/badge/go-1.21%2B-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.8%2B-green?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-yellow?style=flat-square)

Automatically routes external web links to Chrome or Edge based on customizable domain rules.

No background daemon | Instant launch | Customizable rules | One-click install

</div>

---

## What is GoTo

GoTo is a lightweight Windows URL dispatching tool. After installation, whenever you click a link from external applications (WeChat, QQ, email clients, PDF readers, Office documents), Windows invokes GoTo, which parses the target URL according to `rules.json` and opens it in Chrome or Edge instantly.

Typical scenarios:

- Development websites (GitHub, Google, StackOverflow, etc.) open in Chrome.
- Domestic or unmatched websites default to Edge.
- Browser internal protocols (`edge://`, `chrome://`, `about:`) route directly to the respective browser.
- Schemeless links (e.g. `github.com`) are automatically normalized and routed.

GoTo is not a resident background service. It executes only when a link is clicked and exits immediately.

## Download & Installation

For general users, please do not download the GitHub source zip. Use the prebuilt Release package.

1. Open [GitHub Releases](https://github.com/JinPengWang/GoTo/releases).
2. Download **`GoTo-Windows.zip`** from the latest release.
3. Extract to a permanent folder (e.g. `D:\Apps\GoTo`).
4. Double-click **`install.bat`** and grant administrator access when prompted.

The Release package includes the prebuilt `GoTo.exe`. No Python, Go, or internet connection is required during installation.

If routing stops working after system/browser updates, double-click **`repair.bat`** to re-register the protocol handler.

## Uninstallation

Double-click **`uninstall.bat`**. The script will restore original browser handlers and clean up scheduled tasks without deleting your program or configuration files.

## Features

- **Ultra-fast response**: No resident background daemon, zero ongoing memory or CPU footprint.
- **Intuitive wildcards**: Supports `*.github.com`, `google.*`, and catch-all `*`.
- **Security protections**: Rejects CLI flag injection and unsafe pseudo-protocols (`javascript:`, `data:`).
- **500+ preloaded rules**: Out-of-the-box rules for common developer and everyday sites.
- **Hot reload**: Changes to `rules.json` take effect immediately.
- **Safe fallback**: Automatically falls back to available browsers without recursion deadlocks.
- **Windows integration**: Decodes `microsoft-edge:` query strings and parameters cleanly.

## Debug Commands

Run in PowerShell or Command Prompt within the GoTo directory:

- **Test routing for a URL**:
  ```bat
  GoTo.exe --test "https://github.com"
  GoTo.exe --test "bilibili.com"
  ```
- **Validate rules and browser detection**:
  ```bat
  GoTo.exe --validate
  ```

## Building from Source

GoTo supports both **Go Native (Recommended, < 5ms startup)** and **Python / PyInstaller**:

```bat
git clone https://github.com/JinPengWang/GoTo.git
cd GoTo
build.bat
install.bat
```

`build.bat` automatically detects the Go compiler first and falls back to Python if Go is not installed.

## License

This project is licensed under the [MIT License](LICENSE).
