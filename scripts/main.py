import logging
import pyautogui
import pygetwindow as gw
import random
import time
from datetime import datetime

import scraper.slider_image_process as sip

from playwright.sync_api import sync_playwright


class ElectricityScraper:
    def __init__(self, config):
        logging.info("初始化 ElectricityScraper")
        logging.info("初始化 self.config")
        self.config = config
        logging.info("self.config 初始化完成")
        logging.info("ElectricityScraper 初始化完成")

    def fetch_data(self):
        with sync_playwright() as pw:
            logging.info("尝试启动浏览器")
            self.browser = pw.chromium.launch(headless=True)
            logging.info("浏览器启动完成")
            self.context = self.browser.new_context(viewport={'width': 1920, 'height': 1080})
            self.page = self.context.new_page()

            self.page.goto("https://www.95598.cn/osgweb/login")
            self.page.locator(".user").click()
            self.page.get_by_placeholder("请输入用户名/手机号/邮箱").fill(self.config.get('Credentials', 'username'))
            self.page.get_by_placeholder("请输入密码").fill(self.config.get('Credentials', 'password'))

            self.page.get_by_role("button", name="登录").click()

            # 抓取验证码数据
            self.loading_slide()
            self.page.wait_for_selector('canvas')
            slide_bg_img = self.page.evaluate("() => document.querySelector('canvas').toDataURL('image/png')")
            slide_block_img = self.page.evaluate(
                "() => document.querySelector('.slide-verify-block').toDataURL('image/png')")

            slide_bg_img = sip.base64_to_img(slide_bg_img)
            slide_block_img = sip.cutting_transparent_block(sip.base64_to_img(slide_block_img), offset=65)
            Loc = sip.identify_gap(slide_bg_img, slide_block_img)

            distance = 0.0
            special_block = sip.check_special_block(slide_block_img)
            if special_block:
                distance = Loc[0] - 4
            else:
                distance = Loc[0] - 13
            distance = distance / 350.946 * 371

            self.move_slide(distance)

            try:
                while self.page.locator(".cff8").nth(0).get_by_text('元').inner_text(timeout=5000)[:-1] == "--":
                    time.sleep(0.5)
                amount = float(self.page.locator(".cff8").nth(0).get_by_text('元').inner_text()[:-1])
                logging.info(f"今日电费：{amount}")
            except:
                self.page.screenshot(path='debug.png', full_page=True)

                self.page.close()
                self.context.close()
                self.browser.close()
                raise TimeoutError("验证或网络错误")

            self.page.close()
            self.context.close()
            self.browser.close()

            return amount

    def loading_slide(self, timeout=10):
        while True:
            self.page.locator("canvas").nth(0).screenshot(path='slide.png')
            if not sip.is_monochrome('slide.png'):
                break
            time.sleep(0.5)
            logging.info("等待验证码图片加载...")

            timeout -= 1
            if timeout <= 0:
                self.page.close()
                self.context.close()
                self.browser.close()
                raise TimeoutError("加载验证码图片失败")

    def move_slide(self, distance):
        slider_btn_rect = self.page.locator('#slideVerify div').nth(3).bounding_box()
        self.page.mouse.move(slider_btn_rect['x'] + 20, slider_btn_rect['y'] + 20)
        time.sleep(0.5)
        self.page.mouse.down()

        tracks = sip.get_tracks(distance)

        for x in tracks:
            self.page.mouse.move(slider_btn_rect['x'] + 20 + x, random.randint(-5, 5) + slider_btn_rect['y'] + 20)
        self.page.mouse.move(slider_btn_rect['x'] - 5 + tracks[-1] + 20,
                             random.randint(-5, 5) + slider_btn_rect['y'] + 20)
        self.page.mouse.move(slider_btn_rect['x'] + 5 + tracks[-1] + 20,
                             random.randint(-5, 5) + slider_btn_rect['y'] + 20)
        time.sleep(0.5)
        self.page.mouse.up()


# 在 run_task 函数中创建 ElectricityScraper 实例并调用 fetch_data 方法
def run_task(data_fetcher: DataFetcher, sensor_updator: SensorUpdator):
    try:
        # 其他代码...
        electricity_scraper = ElectricityScraper(config)  # 创建 ElectricityScraper 实例
        electricity_scraper.fetch_data()  # 调用 fetch_data 方法
        # 其他代码...
    except Exception as e:
        logging.error(f"state-refresh task failed, reason is {e}")
        traceback.print_exc()

