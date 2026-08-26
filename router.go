package main

import (
	"encoding/json"
	"net/url"
	"os"
	"path/filepath"
	"strings"
)

// Config 表示 rules.json 的配置结构
type Config struct {
	BrowserPaths map[string]string `json:"browser_paths"`
	Rules        []Rule            `json:"rules"`
}

// Rule 表示单组分流规则
type Rule struct {
	Name    string   `json:"name"`
	Browser string   `json:"browser"`
	Domains []string `json:"domains"`
}

// 危险脚本伪协议列表
var dangerousPrefixes = []string{
	"javascript:",
	"data:",
	"vbscript:",
	"blob:",
}

// 内部协议前缀
var internalPrefixes = []string{
	"edge://",
	"microsoft-edge://",
	"microsoft-edge:",
	"chrome://",
	"chrome-extension://",
	"about:",
}

// CleanURL 清洗与标准化 URL 参数
func CleanURL(raw string) string {
	if raw == "" {
		return ""
	}

	u := strings.TrimSpace(raw)
	u = strings.Trim(u, `"'`)
	u = strings.TrimSpace(u)

	// 安全防御：拦截以 - 或 -- 开头的命令行参数注入攻击
	if strings.HasPrefix(u, "-") {
		return ""
	}

	lowerU := strings.ToLower(u)

	// 安全防御：拦截危险伪协议
	for _, prefix := range dangerousPrefixes {
		if strings.HasPrefix(lowerU, prefix) {
			return ""
		}
	}

	// 处理 microsoft-edge: 前缀
	if strings.HasPrefix(lowerU, "microsoft-edge:") {
		rest := strings.TrimLeft(u[len("microsoft-edge:"):], "/")
		// 检查是否为 ?url=https%3A%2F%2F... 或 url=... 形式
		if strings.HasPrefix(rest, "?") || strings.HasPrefix(rest, "url=") {
			queryStr := strings.TrimPrefix(rest, "?")
			values, err := url.ParseQuery(queryStr)
			if err == nil && len(values["url"]) > 0 && values["url"][0] != "" {
				u = values["url"][0]
			} else {
				decoded, err := url.QueryUnescape(rest)
				if err == nil {
					u = decoded
				} else {
					u = rest
				}
			}
		} else {
			decoded, err := url.QueryUnescape(rest)
			if err == nil {
				u = decoded
			} else {
				u = rest
			}
		}
		u = strings.TrimSpace(u)
	}

	// 检查是否已有合法协议
	lowerU = strings.ToLower(u)
	if strings.HasPrefix(lowerU, "http://") ||
		strings.HasPrefix(lowerU, "https://") ||
		strings.HasPrefix(lowerU, "edge://") ||
		strings.HasPrefix(lowerU, "chrome://") ||
		strings.HasPrefix(lowerU, "chrome-extension://") ||
		strings.HasPrefix(lowerU, "about:") {
		return u
	}

	// 缺少协议头且不以 / 开头时，默认补齐 https://
	if u != "" && !strings.Contains(u, "://") && !strings.HasPrefix(u, "/") {
		u = "https://" + u
	}

	return u
}

// ExtractDomain 从 URL 中提取小写域名（剥离 www. 前缀）
func ExtractDomain(rawURL string) string {
	if rawURL == "" {
		return ""
	}

	target := rawURL
	if !strings.Contains(target, "://") && !strings.HasPrefix(target, "/") && !strings.HasPrefix(target, "\\") {
		target = "https://" + target
	}

	parsed, err := url.Parse(target)
	if err != nil {
		return ""
	}

	host := parsed.Hostname()
	host = strings.ToLower(strings.TrimSpace(host))

	// 剥离 www. 前缀
	if strings.HasPrefix(host, "www.") {
		host = host[4:]
	}

	return host
}

// MatchDomain 检查域名是否匹配任一模式
func MatchDomain(domain string, patterns []string) bool {
	if domain == "" {
		return false
	}
	domain = strings.ToLower(strings.TrimSpace(domain))

	for _, pattern := range patterns {
		if MatchSinglePattern(domain, pattern) {
			return true
		}
	}
	return false
}

// MatchSinglePattern 匹配单个模式
func MatchSinglePattern(domain, pattern string) bool {
	p := strings.ToLower(strings.TrimSpace(pattern))
	if p == "*" {
		return true
	}

	// 支持 *.domain.com
	if strings.HasPrefix(p, "*.") {
		root := p[2:]
		if domain == root || strings.HasSuffix(domain, "."+root) {
			return true
		}
		// 通配符匹配
		matched, _ := filepath.Match(p, domain)
		return matched
	}

	// 包含其它位置的通配符（如 google.*）
	if strings.Contains(p, "*") {
		matched, _ := filepath.Match(p, domain)
		return matched
	}

	// 完整匹配或子域名自动继承
	if domain == p || strings.HasSuffix(domain, "."+p) {
		return true
	}

	return false
}

// LoadConfig 从指定路径加载 rules.json
func LoadConfig(configPath string) (*Config, error) {
	data, err := os.ReadFile(configPath)
	if err != nil {
		return nil, err
	}

	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}

	if cfg.BrowserPaths == nil {
		cfg.BrowserPaths = make(map[string]string)
	}

	return &cfg, nil
}
