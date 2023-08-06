from utils import write_source, write_tweet
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import ChromeOptions
import time
from datetime import datetime
import re
import os

driver_path = r'C:\Program Files\Google\Chrome\Application\chromedriver.exe'


# 爬取内容之前一定要登录
def login():
    # option = ChromeOptions()
    # option.add_experimental_option('excludeSwitches', ['enable-automation'])
    # driver = webdriver.Chrome(driver_path, options=option)
    # driver.maximize_window()
    #
    # driver.get(wb_login_url)
    # print('正在打开微博登录页面......')
    #
    # WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, 'loginname')))
    # print("成功打开微博登录页面")
    #
    # driver.find_element_by_id("loginname").send_keys(username)
    # driver.find_element_by_xpath("//div[@class='info_list password']/div/input").send_keys(password)
    # print("成功填写账号")
    #
    # signal = input("手动点击登录按钮并验证以后输入ok:")
    # if signal != 'OK' and signal != 'ok':
    #     print("输入ok!!!")
    # else:
    #     print("成功登录")

    options = ChromeOptions()
    chrome_options = Options()
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    chrome_options.add_experimental_option("debuggerAddress", "127.0.0.1:9225")
    driver = webdriver.Chrome(driver_path, options=options, chrome_options=chrome_options)

    return driver


if __name__ == '__main__':
    driver = login()

    emoji_dict = {}

    driver.get('https://www.emojiall.com/en/platform-weibo')
    time.sleep(2)
    trs = driver.find_elements_by_xpath('//table/tbody/tr')

    for tr in trs:
        tds = tr.find_elements_by_xpath('./td')
        if len(tds) == 3:
            span = tds[2].find_elements_by_xpath('./a/span')
            if len(span) == 1:
                if tds[1].get_attribute('innerText') != "":
                    emoji_dict[tds[1].get_attribute('innerText')] = span[0].get_attribute('innerText')
    print(emoji_dict)
    import json

    with open('emoji.json', 'w', encoding='utf-8') as file_obj:
        json.dump(emoji_dict, file_obj, indent=4, ensure_ascii=False)
