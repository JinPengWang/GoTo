#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GoTo 单元测试套件
测试 URL 清洗、域名提取、规则匹配、参数安全防护等核心功能。
"""

import os
import sys
import unittest
from pathlib import Path

# 将项目根目录添加到 sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import redirector


class TestURLCleaning(unittest.TestCase):
    """测试 URL 清洗与安全防御"""

    def test_clean_url_standard(self):
        self.assertEqual(
            redirector.clean_url("https://github.com/JinPengWang/GoTo"),
            "https://github.com/JinPengWang/GoTo"
        )
        self.assertEqual(
            redirector.clean_url("http://example.com/test?a=1&b=2"),
            "http://example.com/test?a=1&b=2"
        )

    def test_clean_url_quotes_and_spaces(self):
        self.assertEqual(
            redirector.clean_url('  "https://github.com"  '),
            "https://github.com"
        )
        self.assertEqual(
            redirector.clean_url(" 'https://github.com' "),
            "https://github.com"
        )

    def test_clean_url_without_scheme(self):
        """测试无协议头的 URL 自动补齐"""
        self.assertEqual(
            redirector.clean_url("github.com"),
            "https://github.com"
        )
        self.assertEqual(
            redirector.clean_url("www.google.com/search?q=test"),
            "https://www.google.com/search?q=test"
        )

    def test_clean_url_microsoft_edge_prefix(self):
        """测试 microsoft-edge: 协议前缀的剥离与解码"""
        self.assertEqual(
            redirector.clean_url("microsoft-edge:https://github.com"),
            "https://github.com"
        )
        self.assertEqual(
            redirector.clean_url("microsoft-edge:http://example.com"),
            "http://example.com"
        )
        self.assertEqual(
            redirector.clean_url("microsoft-edge:github.com"),
            "https://github.com"
        )
        # Windows 搜索和小组件常见的编码形式
        self.assertEqual(
            redirector.clean_url("microsoft-edge:?url=https%3A%2F%2Fgithub.com"),
            "https://github.com"
        )

    def test_clean_url_security_rejection(self):
        """测试对恶意参数注入和不安全伪协议的防御"""
        # 拒绝以 - 或 -- 开头的 Chromium 命令行参数注入
        self.assertEqual(redirector.clean_url("--renderer-cmd-prefix=calc.exe"), "")
        self.assertEqual(redirector.clean_url("-flag"), "")
        self.assertEqual(redirector.clean_url("   --disable-web-security   "), "")

        # 拒绝危险的 javascript: 和 data: 伪协议
        self.assertEqual(redirector.clean_url("javascript:alert(1)"), "")
        self.assertEqual(redirector.clean_url("data:text/html;base64,PHNjcmlwdD4="), "")


class TestDomainExtraction(unittest.TestCase):
    """测试域名提取"""

    def test_extract_domain_standard(self):
        self.assertEqual(redirector.extract_domain("https://github.com/test"), "github.com")
        self.assertEqual(redirector.extract_domain("https://www.google.com/"), "google.com")
        self.assertEqual(redirector.extract_domain("http://gist.github.com/123"), "gist.github.com")

    def test_extract_domain_schemeless(self):
        self.assertEqual(redirector.extract_domain("github.com/org/repo"), "github.com")
        self.assertEqual(redirector.extract_domain("www.bilibili.com"), "bilibili.com")

    def test_extract_domain_with_ports(self):
        self.assertEqual(redirector.extract_domain("http://localhost:8080/app"), "localhost")
        self.assertEqual(redirector.extract_domain("http://127.0.0.1:3000"), "127.0.0.1")

    def test_extract_domain_ip(self):
        self.assertEqual(redirector.extract_domain("http://192.168.1.1/admin"), "192.168.1.1")


class TestDomainMatching(unittest.TestCase):
    """测试通配符与域名匹配规则"""

    def test_exact_and_subdomain_matching(self):
        patterns = ["github.com", "stackoverflow.com"]
        self.assertTrue(redirector.match_domain("github.com", patterns))
        self.assertTrue(redirector.match_domain("gist.github.com", patterns))
        self.assertTrue(redirector.match_domain("api.github.com", patterns))
        self.assertFalse(redirector.match_domain("notgithub.com", patterns))
        self.assertFalse(redirector.match_domain("mygithub.com", patterns))
        self.assertFalse(redirector.match_domain("google.com", patterns))

    def test_wildcard_patterns(self):
        # 必须支持 *.github.com 形式
        patterns = ["*.github.com", "google.*"]
        self.assertTrue(redirector.match_domain("api.github.com", patterns))
        self.assertTrue(redirector.match_domain("gist.github.com", patterns))
        self.assertTrue(redirector.match_domain("github.com", patterns))

        # 必须支持 google.*
        self.assertTrue(redirector.match_domain("google.com", patterns))
        self.assertTrue(redirector.match_domain("google.co.jp", patterns))
        self.assertTrue(redirector.match_domain("google.com.hk", patterns))
        self.assertFalse(redirector.match_domain("mygoogle.org", patterns))

    def test_catch_all_wildcard(self):
        patterns = ["*"]
        self.assertTrue(redirector.match_domain("anything.com", patterns))
        self.assertTrue(redirector.match_domain("internal.lan", patterns))
        self.assertTrue(redirector.match_domain("localhost", patterns))


class TestRulesLoading(unittest.TestCase):
    """测试 rules.json 加载"""

    def test_load_default_rules(self):
        config_path = PROJECT_ROOT / "rules.json"
        self.assertTrue(config_path.exists())
        browser_paths, rules = redirector.load_rules(config_path)
        self.assertIsInstance(browser_paths, dict)
        self.assertIsInstance(rules, list)
        self.assertGreater(len(rules), 0)


if __name__ == "__main__":
    unittest.main()
