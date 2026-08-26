package main

import (
	"path/filepath"
	"testing"
)

func TestCleanURL(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"https://github.com/JinPengWang/GoTo", "https://github.com/JinPengWang/GoTo"},
		{"http://example.com/test?a=1&b=2", "http://example.com/test?a=1&b=2"},
		{`  "https://github.com"  `, "https://github.com"},
		{" 'https://github.com' ", "https://github.com"},
		{"github.com", "https://github.com"},
		{"www.google.com/search?q=test", "https://www.google.com/search?q=test"},
		{"microsoft-edge:https://github.com", "https://github.com"},
		{"microsoft-edge:http://example.com", "http://example.com"},
		{"microsoft-edge:github.com", "https://github.com"},
		{"microsoft-edge:?url=https%3A%2F%2Fgithub.com", "https://github.com"},
		{"--renderer-cmd-prefix=calc.exe", ""},
		{"-flag", ""},
		{"   --disable-web-security   ", ""},
		{"javascript:alert(1)", ""},
		{"data:text/html;base64,PHNjcmlwdD4=", ""},
	}

	for _, tt := range tests {
		actual := CleanURL(tt.input)
		if actual != tt.expected {
			t.Errorf("CleanURL(%q) = %q; want %q", tt.input, actual, tt.expected)
		}
	}
}

func TestExtractDomain(t *testing.T) {
	tests := []struct {
		input    string
		expected string
	}{
		{"https://github.com/test", "github.com"},
		{"https://www.google.com/", "google.com"},
		{"http://gist.github.com/123", "gist.github.com"},
		{"github.com/org/repo", "github.com"},
		{"www.bilibili.com", "bilibili.com"},
		{"http://localhost:8080/app", "localhost"},
		{"http://127.0.0.1:3000", "127.0.0.1"},
		{"http://192.168.1.1/admin", "192.168.1.1"},
	}

	for _, tt := range tests {
		actual := ExtractDomain(tt.input)
		if actual != tt.expected {
			t.Errorf("ExtractDomain(%q) = %q; want %q", tt.input, actual, tt.expected)
		}
	}
}

func TestMatchDomain(t *testing.T) {
	patterns := []string{"github.com", "stackoverflow.com"}
	if !MatchDomain("github.com", patterns) {
		t.Errorf("expected github.com to match")
	}
	if !MatchDomain("gist.github.com", patterns) {
		t.Errorf("expected gist.github.com to match")
	}
	if MatchDomain("notgithub.com", patterns) {
		t.Errorf("notgithub.com should not match")
	}

	wildcards := []string{"*.github.com", "google.*"}
	if !MatchDomain("api.github.com", wildcards) {
		t.Errorf("expected api.github.com to match *.github.com")
	}
	if !MatchDomain("github.com", wildcards) {
		t.Errorf("expected github.com to match *.github.com")
	}
	if !MatchDomain("google.com", wildcards) {
		t.Errorf("expected google.com to match google.*")
	}
	if !MatchDomain("google.co.jp", wildcards) {
		t.Errorf("expected google.co.jp to match google.*")
	}
	if MatchDomain("mygoogle.org", wildcards) {
		t.Errorf("mygoogle.org should not match google.*")
	}

	catchAll := []string{"*"}
	if !MatchDomain("anything.com", catchAll) {
		t.Errorf("expected * to match anything")
	}
}

func TestLoadConfig(t *testing.T) {
	configPath := filepath.Join(".", "rules.json")
	cfg, err := LoadConfig(configPath)
	if err != nil {
		t.Fatalf("LoadConfig failed: %v", err)
	}
	if len(cfg.Rules) == 0 {
		t.Fatalf("expected rules in config, got 0")
	}
}
