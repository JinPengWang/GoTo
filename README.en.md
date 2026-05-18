<div align="center">

# GoTo

**Smart Browser Router for Windows**

[中文](README.md) | [English](README.en.md)

![Platform](https://img.shields.io/badge/platform-Windows%2010%20%2F%2011-blue?style=flat-square)
![Python](https://img.shields.io/badge/python-3.8%2B%20build%20only-green?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-yellow?style=flat-square)

Route external links to Chrome or Edge automatically based on domain rules.

No background service | One-click install | Editable rules

</div>

---

## What Is GoTo

GoTo is a Windows link routing tool. After installation, when you click a web link from an external app such as WeChat, QQ, an email client, a PDF reader, or an Office document, Windows calls GoTo first. GoTo then reads `rules.json` and opens the link with Chrome or Edge based on the matched domain rule.

Typical use cases:

- Open GitHub, Google, YouTube, and similar sites with Chrome.
- Open domestic or unmatched sites with Edge by default.
- Pass browser-internal URLs such as `edge://` and `chrome://` directly to the correct browser.

GoTo is not a background service. It starts only when a link is opened, routes the link, and exits immediately.

## Download And Install

Normal users should not download GitHub's source-code zip. Use the release package instead.

1. Open [GitHub Releases](https://github.com/JinPengWang/GoTo/releases).
2. Download **`GoTo-Windows.zip`** from the latest release.
3. Extract it to a folder you will keep, for example `D:\Apps\GoTo`.
4. Double-click **`install.bat`**.
5. Allow the Windows administrator prompt.

The release package already includes `GoTo.exe`. Installation does not require Python, pip, PyInstaller, or network access.

If GoTo stops working later, double-click **`repair.bat`** first. It checks whether the files still exist, validates the rules, and re-registers the URL handler.

## Uninstall

Double-click **`uninstall.bat`** and confirm. The uninstaller will try to restore the backed-up browser handler and remove the QQ/WeChat settings written during installation.

## Features

- Route links to Chrome or Edge by domain rule.
- No background process and no continuous CPU or memory usage.
- 500+ preset common-domain rules.
- `rules.json` changes take effect on the next link open.
- Fallback to another available browser when the target browser is missing.
- Protect internal URLs such as `edge://`, `chrome://`, and `about:`.
- Normalize common `microsoft-edge:` link prefixes.
- Try to configure QQ, QQNT, and WeChat to use the system default browser for external links.

## Rules

The configuration file is `rules.json`.

Basic structure:

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

Rule behavior:

- Rules are matched in order. The first match wins.
- `*` is the fallback rule and should usually be last.
- Subdomains inherit parent-domain rules. For example, `gist.github.com` matches `github.com`.
- `browser` currently supports `chrome` and `edge`.
- Leave `browser_paths` empty for auto-detection. If detection fails, set the browser exe paths manually.

## How It Works

```text
User clicks a link from an external app
        |
        v
Windows resolves the current default browser URL handler
        |
        v
Windows starts GoTo.exe and passes the URL as an argument
        |
        v
GoTo reads rules.json, extracts the domain, and matches rules
        |
        v
GoTo starts Chrome or Edge with the URL
        |
        v
GoTo exits
```

The installer modifies the current default browser ProgId `shell\open\command`. This is how GoTo receives link-open requests from external apps. The installer backs up the original registry values and the uninstaller tries to restore them.

## Security And Antivirus Notes

GoTo is open source, but the current `GoTo.exe` release is not code-signed. Windows SmartScreen or antivirus software may warn because the executable is unsigned and the installer modifies browser-handler registry keys.

Recommendations:

- Download only from this project's GitHub Releases.
- Verify file integrity with `SHA256SUMS.txt` from the release package.
- If `GoTo.exe` disappears after installation, check Windows Security protection history or your antivirus quarantine.
- Do not disable antivirus software by default. If there is a false positive, review the source code and hashes before deciding whether to trust the file.

## FAQ

### Installation fails and says GoTo.exe is missing

You probably downloaded GitHub's source-code zip. Normal users should download `GoTo-Windows.zip` from the Releases page.

### Link routing suddenly stops working

Run `repair.bat` first. If it still fails, check:

- Whether `GoTo.exe` is still in the install folder.
- Whether `rules.json` is valid JSON.
- Whether Windows Security or antivirus software quarantined `GoTo.exe`.
- Whether the source app cached browser settings. Restart that app if needed.

### QQ or WeChat still opens links in the built-in browser

GoTo can only handle links that are passed to the Windows default browser. Some QQ and WeChat links bypass the Windows protocol handler and open directly in the built-in browser. The installer writes `UseDefaultBrowser = 1`, but mini-program, official-account, and payment-related links may still be locked by the app.

### Are links clicked inside Edge routed by GoTo

No. Links opened inside a browser are usually handled by that browser. GoTo mainly handles URL open requests from external apps.

## Build From Source

Normal users do not need this section.

```bat
git clone https://github.com/JinPengWang/GoTo.git
cd GoTo
python -m pip install -r requirements-build.txt
build.bat
install.bat
```

`build.bat` generates `GoTo.exe` and `SHA256SUMS.txt`. The installer does not download build dependencies.

## Project Files

```text
GoTo/
  redirector.py              Core routing logic
  rules.json                 Domain rules
  install.bat                User installer
  repair.bat                 Repair script
  uninstall.bat              Uninstaller
  build.bat                  Developer build script
  requirements-build.txt     Build dependencies
  version_info.txt           Windows exe version metadata
  .github/workflows/         Release automation
```

Local generated files that are not committed:

```text
GoTo.exe
backup/
logs/
build/
dist/
__pycache__/
```

## License

This project is licensed under the [MIT License](LICENSE).

