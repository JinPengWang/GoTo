//go:build windows
// +build windows

package main

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"syscall"

	"golang.org/x/sys/windows/registry"
)

// 常量定义
const appName = "GoTo"

// 候选路径定义
func getChromeCandidates() []string {
	return []string{
		os.ExpandEnv(`%ProgramFiles%\Google\Chrome\Application\chrome.exe`),
		os.ExpandEnv(`%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe`),
		os.ExpandEnv(`%LocalAppData%\Google\Chrome\Application\chrome.exe`),
		os.ExpandEnv(`%ProgramW6432%\Google\Chrome\Application\chrome.exe`),
	}
}

func getEdgeCandidates() []string {
	return []string{
		os.ExpandEnv(`%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe`),
		os.ExpandEnv(`%ProgramFiles%\Microsoft\Edge\Application\msedge.exe`),
		os.ExpandEnv(`%ProgramW6432%\Microsoft\Edge\Application\msedge.exe`),
	}
}

func fileExists(path string) bool {
	if path == "" {
		return false
	}
	info, err := os.Stat(path)
	if err != nil {
		return false
	}
	return !info.IsDir()
}

func readRegistryString(root registry.Key, path, valueName string) (string, error) {
	k, err := registry.OpenKey(root, path, registry.QUERY_VALUE)
	if err != nil {
		return "", err
	}
	defer k.Close()

	val, _, err := k.GetStringValue(valueName)
	return val, err
}

func findBrowserFromRegistry(keys []struct {
	root registry.Key
	path string
}) string {
	for _, item := range keys {
		val, err := readRegistryString(item.root, item.path, "")
		if err == nil && fileExists(val) {
			return val
		}
	}
	return ""
}

// FindChrome 查找 Chrome 浏览器路径
func FindChrome(customPath string) string {
	if fileExists(customPath) {
		return customPath
	}

	keys := []struct {
		root registry.Key
		path string
	}{
		{registry.LOCAL_MACHINE, `SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe`},
		{registry.CURRENT_USER, `SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe`},
	}
	if p := findBrowserFromRegistry(keys); p != "" {
		return p
	}

	for _, cand := range getChromeCandidates() {
		if fileExists(cand) {
			return cand
		}
	}
	return ""
}

// FindEdge 查找 Edge 浏览器路径
func FindEdge(customPath string) string {
	if fileExists(customPath) {
		return customPath
	}

	keys := []struct {
		root registry.Key
		path string
	}{
		{registry.LOCAL_MACHINE, `SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe`},
		{registry.CURRENT_USER, `SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\msedge.exe`},
	}
	if p := findBrowserFromRegistry(keys); p != "" {
		return p
	}

	for _, cand := range getEdgeCandidates() {
		if fileExists(cand) {
			return cand
		}
	}
	return ""
}

// IsGoToExecutable 判断指定路径是否为 GoTo 自身
func IsGoToExecutable(targetPath string) bool {
	if targetPath == "" {
		return false
	}
	exe, err := os.Executable()
	if err != nil {
		return false
	}

	cleanTarget := strings.ToLower(filepath.Clean(targetPath))
	cleanExe := strings.ToLower(filepath.Clean(exe))
	if cleanTarget == cleanExe {
		return true
	}

	appDir := filepath.Dir(exe)
	if cleanTarget == strings.ToLower(filepath.Join(appDir, "goto.exe")) {
		return true
	}

	return false
}

// GetSystemDefaultBrowser 获取系统默认浏览器路径（用于安全降级）
func GetSystemDefaultBrowser() string {
	progID, err := readRegistryString(
		registry.CURRENT_USER,
		`SOFTWARE\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice`,
		"ProgId",
	)
	if err != nil || progID == "" {
		return ""
	}

	cmdStr, err := readRegistryString(
		registry.CLASSES_ROOT,
		fmt.Sprintf(`%s\shell\open\command`, progID),
		"",
	)
	if err != nil || cmdStr == "" {
		return ""
	}

	re := regexp.MustCompile(`"([^"]+)"`)
	match := re.FindStringSubmatch(cmdStr)
	if len(match) > 1 && fileExists(match[1]) && !IsGoToExecutable(match[1]) {
		return match[1]
	}

	parts := strings.Fields(cmdStr)
	if len(parts) > 0 && fileExists(parts[0]) && !IsGoToExecutable(parts[0]) {
		return parts[0]
	}

	return ""
}

// ResolveBrowser 解析目标浏览器路径与名称
func ResolveBrowser(target string, customPaths map[string]string, chromePath, edgePath string) (string, string) {
	targetLower := strings.ToLower(strings.TrimSpace(target))

	var path, name string
	switch targetLower {
	case "chrome":
		path = chromePath
		name = "Google Chrome"
	case "edge":
		path = edgePath
		name = "Microsoft Edge"
	default:
		if custom, ok := customPaths[targetLower]; ok && fileExists(custom) {
			return custom, targetLower
		}
		path = ""
		name = target
	}

	if fileExists(path) {
		return path, name
	}

	// 降级选择
	fallbacks := []struct {
		p    string
		name string
	}{
		{edgePath, "Microsoft Edge"},
		{chromePath, "Google Chrome"},
		{GetSystemDefaultBrowser(), "系统默认浏览器"},
	}

	if targetLower == "edge" {
		fallbacks[0], fallbacks[1] = fallbacks[1], fallbacks[0]
	}

	for _, fb := range fallbacks {
		if fileExists(fb.p) && !IsGoToExecutable(fb.p) {
			return fb.p, fmt.Sprintf("%s (%s)", fb.name, filepath.Base(fb.p))
		}
	}

	return "", "无可用浏览器"
}

// OpenURL 启动指定浏览器打开 URL
func OpenURL(browserPath, targetURL string) bool {
	if !fileExists(browserPath) || IsGoToExecutable(browserPath) {
		return false
	}

	cmd := exec.Command(browserPath, targetURL)
	cmd.SysProcAttr = &syscall.SysProcAttr{
		HideWindow:    true,
		CreationFlags: 0x08000000 | 0x00000200, // CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
	}

	if err := cmd.Start(); err != nil {
		return false
	}

	return true
}

// SelfRepair 修复 HKCU 注册表关联
func SelfRepair() error {
	exePath, err := os.Executable()
	if err != nil {
		return err
	}

	progID, err := readRegistryString(
		registry.CURRENT_USER,
		`SOFTWARE\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice`,
		"ProgId",
	)
	if err != nil || progID == "" {
		progID = "MSEdgeHTM"
	}

	userCmdKey := fmt.Sprintf(`Software\Classes\%s\shell\open\command`, progID)
	currentCmd, err := readRegistryString(registry.CURRENT_USER, userCmdKey, "")
	if err == nil && strings.Contains(strings.ToLower(currentCmd), "goto.exe") {
		return nil // 正常，无需写入
	}

	k, _, err := registry.CreateKey(registry.CURRENT_USER, userCmdKey, registry.SET_VALUE)
	if err != nil {
		return err
	}
	defer k.Close()

	newCmd := fmt.Sprintf(`"%s" "%%1"`, exePath)
	return k.SetStringValue("", newCmd)
}
