"""抖音发布工具 - Playwright 操作实现"""

import json
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser

# Cookie 存储路径
COOKIE_DIR = Path(__file__).parent.parent.parent / "cookies"
COOKIE_FILE = COOKIE_DIR / "douyin.json"
CREATOR_URL = "https://creator.douyin.com"


async def _save_cookies(cookies: list):
    """保存 Cookie 到文件"""
    COOKIE_DIR.mkdir(exist_ok=True)
    COOKIE_FILE.write_text(json.dumps(cookies, ensure_ascii=False, indent=2))


async def _load_cookies() -> list | None:
    """从文件加载 Cookie"""
    if not COOKIE_FILE.exists():
        return None
    try:
        return json.loads(COOKIE_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        return None


async def _create_browser(headless: bool = True) -> tuple[Browser, Page]:
    """创建浏览器和页面"""
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=headless)
    page = await browser.new_page()
    return browser, page


async def _check_logged_in(page: Page) -> bool:
    """检查当前页面是否已登录"""
    await page.goto(CREATOR_URL, wait_until="domcontentloaded", timeout=30000)
    await page.wait_for_timeout(2000)
    url = page.url
    return "login" not in url


async def login(headless: bool = False) -> dict:
    """
    扫码登录抖音创作者中心。
    headless=False 打开浏览器，等待用户用抖音APP扫码登录。
    """
    browser, page = await _create_browser(headless=headless)
    try:
        await page.goto(CREATOR_URL, wait_until="domcontentloaded")
        print("请用抖音APP扫码登录...")
        # 等待登录成功（URL 变化，最长等 120 秒）
        await page.wait_for_function(
            "() => !window.location.href.includes('login')",
            timeout=120000,
        )
        await page.wait_for_timeout(2000)
        cookies = await page.context.cookies()
        await _save_cookies(cookies)
        return {"status": "success", "message": "登录成功，Cookie 已保存"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        await browser.close()


async def check_login() -> dict:
    """检查登录状态"""
    browser, page = await _create_browser(headless=True)
    try:
        cookies = await _load_cookies()
        if not cookies:
            return {"logged_in": False, "message": "无 Cookie 文件"}

        await page.context.add_cookies(cookies)
        logged_in = await _check_logged_in(page)
        return {"logged_in": logged_in, "message": "已登录" if logged_in else "Cookie 已过期"}
    finally:
        await browser.close()


async def publish_video(
    video_path: str,
    title: str,
    tags: list[str] = [],
    headless: bool = True,
) -> dict:
    """
    发布视频到抖音。
    参数：
        video_path: 视频文件绝对路径
        title: 视频标题（最多30字）
        tags: 话题标签列表，如 ["干货", "教程"]
        headless: 是否无头模式
    返回：
        {status: "success"/"error", url/message: ...}
    """
    video_file = Path(video_path)
    if not video_file.exists():
        return {"status": "error", "message": f"视频文件不存在: {video_path}"}

    cookies = await _load_cookies()
    if not cookies:
        return {"status": "error", "message": "未登录，请先调用 login 工具扫码登录"}

    browser, page = await _create_browser(headless=headless)
    try:
        # 加载 Cookie 并登录
        await page.context.add_cookies(cookies)
        await page.goto(CREATOR_URL, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2000)

        if "login" in page.url:
            return {"status": "error", "message": "Cookie 已过期，请重新扫码登录"}

        # 点击「上传视频」
        upload_btn = page.locator('text=上传视频').first
        await upload_btn.click()
        await page.wait_for_timeout(1000)

        # 上传视频文件
        file_input = page.locator('input[type="file"]').first
        await file_input.set_input_files(str(video_file.absolute()))

        # 等待上传完成（轮询进度条消失）
        await _wait_for_upload(page)

        # 填写标题
        title_input = page.locator('textarea[placeholder*="标题"], input[placeholder*="标题"]').first
        await title_input.click()
        await title_input.fill(title[:30])

        # 填写话题标签
        if tags:
            tag_text = " ".join([f"#{tag}" for tag in tags])
            desc_input = page.locator('textarea[placeholder*="描述"], div[contenteditable="true"]').first
            await desc_input.click()
            await desc_input.fill(tag_text)

        await page.wait_for_timeout(1000)

        # 点击发布
        publish_btn = page.locator('button:has-text("发布")').first
        await publish_btn.click()
        await page.wait_for_timeout(3000)

        # 检查是否发布成功
        success = await _check_publish_success(page)
        if success:
            return {"status": "success", "message": "视频发布成功", "url": page.url}
        else:
            return {"status": "error", "message": "发布可能失败，请检查页面状态"}

    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        await browser.close()


async def _wait_for_upload(page: Page, timeout: int = 300):
    """等待视频上传完成"""
    import time
    start = time.time()
    while time.time() - start < timeout:
        # 检查是否有上传进度提示
        progress = await page.locator('text=/\\d+%|上传中|处理中/').count()
        if progress == 0:
            # 没有进度提示，可能已完成
            await page.wait_for_timeout(2000)
            return
        await page.wait_for_timeout(3000)
    # 超时但不报错，继续流程


async def _check_publish_success(page: Page) -> bool:
    """检查发布是否成功"""
    await page.wait_for_timeout(3000)
    # 检查是否有成功提示或跳转到作品页
    success_indicators = [
        page.locator('text=/发布成功|作品已发布/'),
        page.locator('text=作品管理'),
    ]
    for indicator in success_indicators:
        if await indicator.count() > 0:
            return True
    return False
