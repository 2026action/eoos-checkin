#!/usr/bin/env python3
"""
EOOS.TOP 自动签到脚本 - Playwright无头浏览器版 (带Cookie持久化)
流程:
  1. 尝试从环境变量EOOS_COOKIE恢复浏览器cookie
  2. 如果cookie有效 → 直接签到
  3. 如果cookie失效 → 登录 → 签到 → 提取新cookie → 输出到stdout
用于GitHub Actions, 输出格式: {"cookie": "...", "reward": "0.72", "status": "success"}
"""

import sys
import re
import json
import os
from playwright.sync_api import sync_playwright

USERNAME = os.environ.get("EOOS_USERNAME", "niubi1705")
PASSWORD = os.environ.get("EOOS_PASSWORD", "zxc9696")
BASE_URL = "https://eoos.top"
TIMEOUT = 90_000

def find_chromium():
    import glob
    pw_paths = [
        os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome"),
        os.path.expanduser("~/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell"),
    ]
    for pattern in pw_paths:
        matches = glob.glob(pattern)
        if matches:
            return matches[-1]
    sys_paths = ["/usr/bin/chromium", "/usr/bin/chromium-browser", "/snap/bin/chromium"]
    for p in sys_paths:
        if os.path.exists(p):
            return p
    return None

def log(msg):
    print(f"[{__import__('datetime').datetime.now().strftime('%H:%M:%S')}] {msg}")

def main():
    log("🚀 启动Playwright无头浏览器")

    chrome_path = find_chromium()
    launch_kwargs = {
        "headless": True,
        "args": [
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
        ]
    }
    if chrome_path:
        launch_kwargs["executable_path"] = chrome_path
        log(f"   📍 使用Chromium: {chrome_path}")
    else:
        log("   ⚠️ 未找到Chromium, 尝试Playwright默认")

    with sync_playwright() as p:
        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        # ===== 尝试恢复sessionStorage =====
        saved_token = os.environ.get("EOOS_COOKIE", "")
        cookie_valid = False

        if saved_token:
            log("🔑 尝试恢复登录token...")
            try:
                # 先访问站点建立sessionStorage
                page.goto(BASE_URL, wait_until="domcontentloaded", timeout=15000)
                # 注入token到sessionStorage
                page.evaluate(f"""() => {{
                    sessionStorage.setItem('auth_token', '{saved_token}');
                }}""")
                page.wait_for_timeout(1000)
                # 访问仪表盘测试token是否有效
                page.goto(f"{BASE_URL}/dashboard", wait_until="networkidle", timeout=15000)
                page.wait_for_timeout(2000)
                page_text = page.inner_text("body")
                if "niubi1705" in page_text and ("仪表盘" in page_text or "dashboard" in page_text.lower()):
                    log("   ✅ Token有效, 已登录!")
                    cookie_valid = True
                else:
                    log("   ⚠️ Token已失效, 需要重新登录")
                    page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded", timeout=15000)
            except Exception as e:
                log(f"   ⚠️ Token恢复失败: {e}, 需要重新登录")
                page.goto(f"{BASE_URL}/login", wait_until="domcontentloaded", timeout=15000)
        else:
            log("   ℹ️ 无已保存的token")

        # ===== 登录（如需） =====
        if not cookie_valid:
            log("🔑 登录...")
            page.goto(f"{BASE_URL}/login", wait_until="networkidle", timeout=30000)

            page.wait_for_selector("input[type='text'], input[placeholder*='账号'], input[placeholder*='用户'], input[name='userName']", timeout=15000)

            username_input = page.locator("input[placeholder*='账号'], input[placeholder*='用户'], input[name='userName'], input[type='text']").first
            username_input.fill(USERNAME)

            password_input = page.locator("input[type='password'], input[placeholder*='密码'], input[name='password']").first
            password_input.fill(PASSWORD)

            login_btn = page.locator("button:has-text('登录'), button:has-text('登 录'), button[type='submit']").first
            login_btn.click()

            log("   ⏳ 等待登录完成...")
            # 等待导航离开登录页或直接访问dashboard验证
            try:
                page.wait_for_url("**/dashboard**", timeout=10000)
            except:
                # 如果没自动跳转，手动导航
                pass
            # 访问dashboard验证登录
            page.goto(f"{BASE_URL}/dashboard", wait_until="networkidle", timeout=15000)
            log("   ✅ 登录成功!")

        # ===== 检查签到状态 =====
        log("📊 检查签到状态...")
        page.goto(f"{BASE_URL}/dashboard", wait_until="networkidle", timeout=15000)
        page.wait_for_timeout(2000)
        page_text = page.inner_text("body")

        if "今日已签到" in page_text:
            amounts = re.findall(r'[+-]?\d+\.\d+', page_text)
            reward = amounts[0] if amounts else "?"
            log(f"   ✅ 今日已签到! 奖励: {reward} RCoin")

            # 提取token供下次使用
            new_token = None
            if not cookie_valid:
                try:
                    new_token = page.evaluate("() => sessionStorage.getItem('auth_token') || ''")
                    if new_token:
                        log(f"   💾 已保存token, 下次免登录")
                except Exception as e:
                    log(f"   ⚠️ 提取token失败: {e}")

            browser.close()
            return {"status": "already_checked_in", "reward": reward, "token": new_token}

        # ===== 点击签到 =====
        log("🎯 点击签到按钮...")
        checkin_clicked = False
        selectors = [
            "button:has-text('立即签到')",
            "button:has-text('签到')",
            "text=立即签到",
            "text=今日签到",
            "[class*='checkin']",
            "[class*='sign']",
        ]

        for selector in selectors:
            try:
                btn = page.locator(selector).first
                if btn.is_visible(timeout=2000):
                    log(f"   🔍 找到按钮: {selector}")
                    btn.click()
                    checkin_clicked = True
                    log("   ✅ 已点击签到按钮")
                    break
            except:
                continue

        if not checkin_clicked:
            try:
                btn = page.get_by_text("立即签到", exact=True).first
                if btn.is_visible():
                    btn.click()
                    checkin_clicked = True
                    log("   ✅ 已点击签到按钮(get_by_text)")
            except:
                pass

        if not checkin_clicked:
            log("   ❌ 未找到签到按钮")
            browser.close()
            return {"status": "error", "message": "no checkin button found"}

        # ===== 等待cap.js验证 =====
        log("🧩 等待人机验证完成...")
        log("   (cap.js会自动解决PoW挑战, 等待中)")

        checked_in = False
        reward = "?"
        for i in range(120):
            page.wait_for_timeout(1000)
            try:
                page_text = page.inner_text("body")
            except:
                page_text = ""

            if not page_text:
                continue

            if "今日已签到" in page_text or "签到完成" in page_text or "签到成功" in page_text:
                checked_in = True
                amounts = re.findall(r'[+-]?\d+\.\d+', page_text)
                reward = amounts[0] if amounts else "?"
                log(f"   ✅ 签到完成! ({i+1}s) 奖励: {reward} RCoin")
                break

            if "验证失败" in page_text or "失败" in page_text:
                log(f"   ❌ 验证失败 (第{i+1}s)")
                break

            if i % 10 == 0 and i > 0:
                log(f"   ⏳ 等待中... ({i+1}s)")

        # ===== 提取token供下次使用 =====
        new_token = None
        if checked_in and not cookie_valid:
            try:
                new_token = page.evaluate("() => sessionStorage.getItem('auth_token') || ''")
                if new_token:
                    log(f"   💾 已保存token, 下次免登录")
                else:
                    log("   ⚠️ sessionStorage中未找到auth_token")
            except Exception as e:
                log(f"   ⚠️ 提取token失败: {e}")

        browser.close()

        if checked_in:
            log(f"🎉 签到成功! 获得 {reward} RCoin")
            return {"status": "success", "reward": reward, "token": new_token}
        else:
            log("❌ 签到失败或超时")
            return {"status": "timeout", "message": "check-in not confirmed within timeout"}

if __name__ == "__main__":
    result = main()
    print(f"\n{'='*50}")
    print(f"状态: {result.get('status')}")
    if 'reward' in result and result['reward']:
        print(f"奖励: {result['reward']} RCoin")
    # 输出token供GitHub Action捕获
    if result.get('token'):
        print(f"__NEW_TOKEN__={result['token']}")
    print(f"{'='*50}")