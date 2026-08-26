package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
)

func getAppDir() string {
	exe, err := os.Executable()
	if err != nil {
		return "."
	}
	return filepath.Dir(exe)
}

func getConfigPath() string {
	appDir := getAppDir()
	localConfig := filepath.Join(appDir, "rules.json")
	if fileExists(localConfig) {
		return localConfig
	}

	appData := os.Getenv("APPDATA")
	if appData != "" {
		appDataConfig := filepath.Join(appData, appName, "rules.json")
		if fileExists(appDataConfig) {
			return appDataConfig
		}
	}

	return localConfig
}

func handleInternalURL(targetURL, chromePath, edgePath string) bool {
	lower := strings.ToLower(targetURL)
	if strings.HasPrefix(lower, "edge://") ||
		strings.HasPrefix(lower, "microsoft-edge://") ||
		strings.HasPrefix(lower, "microsoft-edge:") {
		if edgePath != "" {
			return OpenURL(edgePath, targetURL)
		}
	}

	if strings.HasPrefix(lower, "chrome://") ||
		strings.HasPrefix(lower, "chrome-extension://") {
		if chromePath != "" {
			return OpenURL(chromePath, targetURL)
		}
	}

	if strings.HasPrefix(lower, "about:") {
		fallback := chromePath
		if fallback == "" {
			fallback = edgePath
		}
		if fallback == "" {
			fallback = GetSystemDefaultBrowser()
		}
		if fallback != "" {
			return OpenURL(fallback, targetURL)
		}
	}

	return false
}

func runTestMode(targetURL string) {
	fmt.Println("\n============================================================")
	fmt.Println("  GoTo (Native Go) - 规则匹配测试 (Test Mode)")
	fmt.Println("============================================================\n")

	cleaned := CleanURL(targetURL)
	fmt.Printf("原始 URL:    %s\n", targetURL)
	if cleaned == "" {
		fmt.Println("清洗后 URL:  [被安全机制拦截或为空]")
		fmt.Println("\n[结果] URL 无效或被拦截。")
		return
	}
	fmt.Printf("清洗后 URL:  %s\n", cleaned)

	domain := ExtractDomain(cleaned)
	fmt.Printf("提取域名:    %s\n", domain)

	configPath := getConfigPath()
	fmt.Printf("配置文件:    %s\n", configPath)

	cfg, err := LoadConfig(configPath)
	if err != nil {
		fmt.Printf("[错误] 配置文件读取失败: %v\n", err)
		return
	}

	chromePath := FindChrome(cfg.BrowserPaths["chrome"])
	edgePath := FindEdge(cfg.BrowserPaths["edge"])

	fmt.Printf("Chrome 路径: %s\n", chromePath)
	fmt.Printf("Edge 路径:   %s\n", edgePath)
	fmt.Println("------------------------------------------------------------")

	lower := strings.ToLower(cleaned)
	if strings.HasPrefix(lower, "edge://") || strings.HasPrefix(lower, "microsoft-edge:") {
		fmt.Println("命中类型:    Edge 内部链接 -> Microsoft Edge")
		fmt.Printf("预计使用:    %s\n", edgePath)
		return
	}
	if strings.HasPrefix(lower, "chrome://") || strings.HasPrefix(lower, "chrome-extension://") {
		fmt.Println("命中类型:    Chrome 内部链接 -> Google Chrome")
		fmt.Printf("预计使用:    %s\n", chromePath)
		return
	}

	matchedBrowser := "edge"
	matchedRuleName := "兜底（无匹配规则）"

	for _, rule := range cfg.Rules {
		if MatchDomain(domain, rule.Domains) {
			matchedBrowser = rule.Browser
			matchedRuleName = rule.Name
			break
		}
	}

	browserPath, browserName := ResolveBrowser(matchedBrowser, cfg.BrowserPaths, chromePath, edgePath)
	fmt.Printf("命中规则:    [%s]\n", matchedRuleName)
	fmt.Printf("目标浏览器:  %s\n", matchedBrowser)
	fmt.Printf("实际分发给:  %s\n", browserName)
	fmt.Printf("执行文件:    %s\n", browserPath)
	fmt.Println("\n============================================================\n")
}

func runValidateMode() {
	fmt.Println("\n============================================================")
	fmt.Println("  GoTo (Native Go) - 配置文件校验 (Validate Mode)")
	fmt.Println("============================================================\n")

	configPath := getConfigPath()
	fmt.Printf("检查文件: %s\n", configPath)

	cfg, err := LoadConfig(configPath)
	if err != nil {
		fmt.Printf("[错误] 无法解析 rules.json: %v\n\n", err)
		return
	}

	fmt.Printf("规则总数: %d 组\n", len(cfg.Rules))
	totalDomains := 0
	for _, r := range cfg.Rules {
		totalDomains += len(r.Domains)
	}
	fmt.Printf("域名总数: %d 个\n", totalDomains)

	chromePath := FindChrome(cfg.BrowserPaths["chrome"])
	edgePath := FindEdge(cfg.BrowserPaths["edge"])

	if chromePath != "" {
		fmt.Printf("Chrome 状态: [OK] %s\n", chromePath)
	} else {
		fmt.Println("Chrome 状态: [未检测到]")
	}

	if edgePath != "" {
		fmt.Printf("Edge 状态:   [OK] %s\n", edgePath)
	} else {
		fmt.Println("Edge 状态:   [未检测到]")
	}

	fmt.Println("\n[OK] 配置文件解析成功，格式有效。\n")
}

func main() {
	args := os.Args[1:]
	if len(args) == 0 {
		return
	}

	// 1. 处理特殊标志
	switch args[0] {
	case "--maintain", "--self-repair":
		_ = SelfRepair()
		return
	case "--validate":
		runValidateMode()
		return
	case "--test":
		if len(args) >= 2 {
			runTestMode(args[1])
		}
		return
	}

	// 2. 获取并清洗 URL
	rawURL := strings.Join(args, " ")
	targetURL := CleanURL(rawURL)
	if targetURL == "" {
		return
	}

	// 3. 加载配置与探测浏览器
	configPath := getConfigPath()
	cfg, err := LoadConfig(configPath)
	if err != nil {
		// 配置文件损坏时，降级使用默认浏览器
		defaultBrowser := GetSystemDefaultBrowser()
		if defaultBrowser != "" {
			OpenURL(defaultBrowser, targetURL)
		}
		return
	}

	chromePath := FindChrome(cfg.BrowserPaths["chrome"])
	edgePath := FindEdge(cfg.BrowserPaths["edge"])

	// 4. 处理内部协议
	if handleInternalURL(targetURL, chromePath, edgePath) {
		return
	}

	// 5. 提取域名与规则匹配
	domain := ExtractDomain(targetURL)
	matchedBrowser := "edge"

	for _, rule := range cfg.Rules {
		if MatchDomain(domain, rule.Domains) {
			matchedBrowser = rule.Browser
			break
		}
	}

	// 6. 分发并打开
	browserPath, _ := ResolveBrowser(matchedBrowser, cfg.BrowserPaths, chromePath, edgePath)
	if browserPath != "" {
		OpenURL(browserPath, targetURL)
	}
}
