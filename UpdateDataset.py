# -*- coding: utf-8 -*-
# @Time    :
# @Author  :
# @Email   :
# @File    : UpdateDataset.py
# @Software: PyCharm
# @Note    :
import codecs
import csv
import json

from utils import write_source, write_tweet
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver import ChromeOptions
import time
from datetime import datetime
import re
import os

dataset_csv_path = 'train.csv'

username = '13698603020'
password = '5039795891..'

# 截取的一级评论限制数量
tweet_num_limit = 50  # 一次提取的帖子url的数量
comment_num_limit = 600
second_comment_num_limit = 600

driver_path = r'C:\Program Files\Google\Chrome\Application\chromedriver.exe'

wb_login_url = 'https://weibo.com/login.php'

content_xpath = '//div[@class="detail_wbtext_4CRf9"]'  # 帖子正文
tweet_time_xpath = '//a[@class="head-info_time_6sFQg"]'  # 帖子发布时间
comment_num_xpath = '//div[@class="woo-box-item-flex toolbar_item_1ky_D"]/div/span[@class="toolbar_num_JXZul"]'  # 评论数量
comment_list_bottom_xpath = '//div[@class="Bottom_text_1kFLe"]'  # 评论列表页面最底部
popup_comment_list_bottom_xpath = '//div[@class="woo-box-flex woo-box-alignCenter woo-box-justifyCenter woo-modal-wrap ReplyModal_wrap_2j1bg"]//div[@class="Bottom_text_1kFLe"]'  # 弹窗评论列表页面最底部
close_popup_button_xpath = '//div[@class="woo-box-flex woo-box-alignCenter woo-box-justifyCenter woo-modal-wrap ReplyModal_wrap_2j1bg"]//div[@class="wbpro-layer-tit-opt woo-box-flex woo-box-alignCenter woo-box-justifyCenter"]/i'


# tweet_user_xpath = '//a[@class="ALink_default_2ibt1 head_cut_2Zcft head_name_24eEB"]'  # 帖子发布用户id


# 爬取内容之前一定要登录
def login():
    option = ChromeOptions()
    option.add_experimental_option('excludeSwitches', ['enable-automation'])
    driver = webdriver.Chrome(driver_path, options=option)
    driver.maximize_window()

    driver.get(wb_login_url)
    print('正在打开微博登录页面......')

    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, 'loginname')))
    print("成功打开微博登录页面")

    driver.find_element_by_id("loginname").send_keys(username)
    driver.find_element_by_xpath("//div[@class='info_list password']/div/input").send_keys(password)
    print("成功填写账号")

    signal = input("手动点击登录按钮并验证以后输入ok:")
    if signal != 'OK' and signal != 'ok':
        print("输入ok!!!")
    else:
        print("成功登录")

    return driver


# 获取帖子文本和时间，返回dict
def get_tweet_content(driver):
    tweet_text = driver.find_element_by_xpath(content_xpath).get_attribute('innerText')
    tweet_text = tweet_text.replace('<br>', '\n').replace('\u200b', '').replace('\u2006', ' ').replace(
        '\u0026\u0071\u0075\u006f\u0074\u003b', '\"').replace('\u0026\u006e\u0062\u0073\u0070\u003b', ' ').replace(
        '\u0026\u0061\u006d\u0070\u003b', '&')
    tweet_time = driver.find_element_by_xpath(tweet_time_xpath).get_attribute('innerText')

    tweet_dict = {
        'content': tweet_text,
        'time': tweet_time,
        'user id': '',
        'tweet id': ''
    }

    return tweet_dict


# 从帖子url中截取用户和帖子的id，返回两个str
def get_user_tweet_id(tweet_url):
    split_list = tweet_url.split('/')

    user_id = split_list[-2]
    tweet_id = split_list[-1]

    return user_id, tweet_id


def get_tweet_comment(driver):
    comment_num = driver.find_element_by_xpath(comment_num_xpath).get_attribute('innerText').strip()
    tip_xpath = '//span[@class="woo-tip-text"]'
    tip = driver.find_elements_by_xpath(tip_xpath)
    first = find_comment_view(driver, 0)
    if comment_num == '评论' or comment_num == 0 or len(first) == 0:
        return []
    if len(tip) != 0 and tip[-1].get_attribute('innerText').strip() == '暂无评论，发表你的评论或看看推荐吧':
        return []

    WebDriverWait(driver, 5).until(lambda driver: driver.find_elements_by_xpath(
        '//div[@class="RepostCommentList_mar1_3VHkS"]//div[@class="vue-recycle-scroller__item-view"]/div[@data-index="0" and @data-active="true"]'))

    useful_comment_num = scroll_to_show_enough_comment(driver)
    scrolling(driver, 0)

    scrolling_location = 200
    comment_index = 0
    comment_list = []
    for i in range(useful_comment_num):
        comment_view = find_active_comment_view(driver, i)
        if len(comment_view) == 0:
            while 1:
                scrolling(driver, scrolling_location)
                scrolling_location += 200

                find_comment = find_active_comment_view(driver, i)
                if len(find_comment) != 0:
                    break

                time.sleep(0.5)

        root_comment = {'comment id': comment_index, 'parent': -1, 'children': []}
        comment_index += 1

        # if i == 10:
        #     write_source(driver)
        #     time.sleep(100)
        root_view_xpath = f'//div[@class="RepostCommentList_mar1_3VHkS"]//div[@class="vue-recycle-scroller__item-view"]/div[@data-index="{i}" and @data-active="true"]'
        root_view = driver.find_element_by_xpath(root_view_xpath)

        # 爬取评论用户id
        user_id_xpath = './/div[@class="item1"]/div[@class="item1in woo-box-flex"]//div[@class="text"]/a[@class="ALink_default_2ibt1"]'
        user_id = root_view.find_element_by_xpath(user_id_xpath)
        root_comment['user id'] = user_id.get_attribute('to').split('/')[-1]
        root_comment['user name'] = user_id.get_attribute('innerText')

        # 爬取评论内容
        content_xpath = './/div[@class="item1"]/div[@class="item1in woo-box-flex"]//div[@class="text"]/span'
        content = root_view.find_element_by_xpath(content_xpath).get_attribute('innerText')
        root_comment['content'] = content

        # 爬取评论时间
        comment_time_xpath = './/div[@class="item1"]/div[@class="item1in woo-box-flex"]//div[@class="info woo-box-flex woo-box-alignCenter woo-box-justifyBetween"]/div[1]'
        comment_time = root_view.find_element_by_xpath(comment_time_xpath).get_attribute('innerText').strip()
        root_comment['time'] = ' '.join(comment_time.split()[:2])

        comment_list.append(root_comment)

        # 评论存在的所有情况：
        # 1. 单个一级评论
        # 2. 有二级评论不需要展开
        # 3. 有二级评论需要展开-评论数量未超过限制
        # 4. 有二级评论需要展开-评论数量超过限制
        second_comment_xpath = root_view_xpath + '//div[@class="item1"]//div[@class="item2"]'
        second_comment = driver.find_elements_by_xpath(second_comment_xpath)
        if len(second_comment) != 0:  # 有二级评论，对应234

            another_unfold_exist = False  # 应付【xxx等人 共x条回复】的情况
            if len(second_comment) == 1:
                find = second_comment[0].find_elements_by_xpath('./div/div/span')
                if len(find) != 0 and re.match('共.*?条回复', find[0].get_attribute('innerText').strip()) != None:
                    another_unfold_exist = True

            comment_unfold_xpath = root_view_xpath + '//div[@class="item1"]//div[@class="item2"]/div[@class="text"]/a'
            comment_unfold = driver.find_elements_by_xpath(comment_unfold_xpath)  # 搜索看看有没有折叠的评论
            if len(comment_unfold) == 0 and not another_unfold_exist:  # 对应2
                button1 = second_comment[0].find_element_by_xpath('./div/div/a')
                not_delete_only_one = re.match('共.*?条回复', button1.get_attribute(
                    'innerText').strip()) == None  # 这是为了应付用户回复了1条评论又删除掉的情况
                if not_delete_only_one:
                    comment_2_num = len(second_comment)
                    comment_2_list = []

                    for i in range(comment_2_num):
                        comment_2_list.append({'comment id': comment_index, 'parent': -2, 'children': []})
                        comment_index += 1

                    for i, item in enumerate(second_comment):
                        user_id_xpath = './div/div/a[@class="ALink_default_2ibt1"]'
                        user_id = item.find_element_by_xpath(user_id_xpath)
                        comment_2_list[i]['user id'] = user_id.get_attribute('to').split('/')[-1]
                        comment_2_list[i]['user name'] = user_id.get_attribute('innerText')

                        content_xpath = './div/div/span'
                        content = item.find_element_by_xpath(content_xpath)
                        comment_2_list[i]['content'] = content.get_attribute('innerText')

                        comment_time_xpath = './div/div[@class="info woo-box-flex woo-box-alignCenter woo-box-justifyBetween"]/div[1]'
                        comment_time = item.find_element_by_xpath(comment_time_xpath).get_attribute('innerText').strip()
                        comment_2_list[i]['time'] = ' '.join(comment_time.split()[:2])

                        is_reply = content.find_elements_by_xpath('./a')
                        if len(second_comment) == 2 and len(is_reply) != 0:
                            child_index = i
                            parent_index = 1 if child_index == 0 else 0
                            comment_2_list[child_index]['parent'] = comment_2_list[parent_index]['comment id']
                            comment_2_list[parent_index]['children'].append(comment_2_list[child_index]['comment id'])
                        else:
                            comment_2_list[i]['parent'] = root_comment['comment id']
                            root_comment['children'].append(comment_2_list[i]['comment id'])

                    comment_list += comment_2_list
            else:  # 对应34
                unfold_button = second_comment[0].find_element_by_xpath('./div/div/span') if another_unfold_exist else \
                    comment_unfold[0]
                comment_unfold_num = int(unfold_button.get_attribute('innerText').strip()[1:-3])
                if comment_unfold_num <= second_comment_num_limit:  # 对应3
                    driver.execute_script("arguments[0].click();", unfold_button)
                    WebDriverWait(driver, 20).until(lambda driver: driver.find_elements_by_xpath(
                        '//div[@class="list2"]/div[@class="Scroll_container_280Ky"]/div[@class="Scroll_wrap_ObsGW"]//div[@data-index="0"]'))
                    time.sleep(0.3)

                    useful_second_comment_num = scroll_popup_to_show_all_comment(driver)
                    scrolling_popup(driver, 0)

                    second_scrolling_location = 200
                    comment_2_list = []
                    for i in range(useful_second_comment_num):
                        second_comment_view = find_active_second_comment_view(driver, i)
                        if len(second_comment_view) == 0:
                            while 1:
                                scrolling_popup(driver, second_scrolling_location)
                                second_scrolling_location += 200

                                find_comment = find_active_second_comment_view(driver, i)
                                if len(find_comment) != 0:
                                    break

                                time.sleep(0.5)

                        comment = {'comment id': comment_index, 'parent': -1, 'children': []}
                        comment_index += 1

                        comment_view_xpath = f'//div[@class="woo-box-flex woo-box-alignCenter woo-box-justifyCenter woo-modal-wrap ReplyModal_wrap_2j1bg"]//div[@data-index="{i}"]'
                        comment_view = driver.find_element_by_xpath(comment_view_xpath)

                        # 爬取评论用户id
                        user_id_xpath = './div/div/div/a[@class="ALink_default_2ibt1"]'
                        user_id = comment_view.find_element_by_xpath(user_id_xpath)
                        comment['user id'] = user_id.get_attribute('to').split('/')[-1]
                        comment['user name'] = user_id.get_attribute('innerText')

                        # 爬取评论内容
                        content_xpath = './div/div/div/span'
                        content = comment_view.find_elements_by_xpath(
                            content_xpath)  # 这里使用find_elements是因为微博认证图标也是一个span
                        comment['content'] = content[1].get_attribute('innerText') if len(content) != 1 else content[
                            0].get_attribute('innerText')

                        # 爬取评论时间
                        comment_time_xpath = './div/div/div[@class="info woo-box-flex woo-box-alignCenter woo-box-justifyBetween"]/div'
                        comment_time = comment_view.find_element_by_xpath(comment_time_xpath).get_attribute(
                            'innerText').strip()
                        comment['time'] = ' '.join(comment_time.split()[:2])

                        comment_2_list.append(comment)

                    close_popup_button = driver.find_element_by_xpath(close_popup_button_xpath)
                    driver.execute_script("arguments[0].click();", close_popup_button)

                    comment_2_list = sorted(comment_2_list, reverse=True,
                                            key=lambda x: datetime.strptime(x['time'], "%y-%m-%d %H:%M"))

                    for i, item in enumerate(comment_2_list):
                        match_res = re.match('回复@(.*?):', item['content'])
                        if match_res == None:  # 说明是直接回复在一级评论上的
                            item['parent'] = root_comment['comment id']
                            root_comment['children'].append(item['comment id'])
                        else:
                            reply_user_name = match_res.group(1)
                            finded = False
                            for j in range(i + 1, len(comment_2_list)):
                                if comment_2_list[j]['user name'] == reply_user_name:
                                    item['parent'] = comment_2_list[j]['comment id']
                                    comment_2_list[j]['children'].append(item['comment id'])
                                    finded = True
                                    break
                            if not finded:
                                item['parent'] = root_comment['comment id']
                                root_comment['children'].append(item['comment id'])

                    comment_list += comment_2_list
    return comment_list


# 下拉滚动条，加载多条评论
def scroll_to_show_enough_comment(driver):
    useful_comment_num = 0

    check_num = 0
    check_time = 0
    while 1:
        scrolling(driver, 100000)

        bottom_comment = find_comment_view(driver, comment_num_limit - 1)
        comment_list_bottom = driver.find_elements_by_xpath(comment_list_bottom_xpath)

        if len(bottom_comment) != 0:
            useful_comment_num = comment_num_limit
            break

        if len(comment_list_bottom) != 0:
            for i in range(comment_num_limit - 1, -1, -1):
                comment_view = find_comment_view(driver, i)
                if len(comment_view) != 0:
                    useful_comment_num = i + 1
                    break
            break

        check_num += 1
        if check_num == 10:
            check_time += 1
            if check_miss(driver):
                useful_comment_num = comment_num_limit
                break
            check_num = 0

        if check_time > 4:
            useful_comment_num = 0
            break

        # 把滚动条再拉回顶部，否则评论列表到达最底端的提示显示不出来（一直卡在刷新状态）
        scrolling(driver, 0)

        time.sleep(0.5)

    return useful_comment_num


def check_miss(driver):
    comment_view_xpath = f'//div[@class="RepostCommentList_mar1_3VHkS"]//div[@class="vue-recycle-scroller__item-view"]/div[@data-active="true"]'
    print('check num', int(driver.find_elements_by_xpath(comment_view_xpath)[0].get_attribute("data-index")))
    return int(driver.find_elements_by_xpath(comment_view_xpath)[0].get_attribute("data-index")) > comment_num_limit


# 下拉滚动条，加载弹窗内所有评论
def scroll_popup_to_show_all_comment(driver):
    useful_comment_num = 0

    while 1:
        scrolling_popup(driver, 100000)

        popup_comment_list_bottom = driver.find_elements_by_xpath(popup_comment_list_bottom_xpath)

        if len(popup_comment_list_bottom) != 0:
            for i in range(second_comment_num_limit - 1, -1, -1):
                comment_view = find_second_comment_view(driver, i)
                if len(comment_view) != 0:
                    useful_comment_num = i + 1
                    break
            break

        # 把滚动条再拉回顶部，否则评论列表到达最底端的提示显示不出来（一直卡在刷新状态）
        scrolling_popup(driver, 0)

        time.sleep(0.5)

    return useful_comment_num


# 下拉滚动条，加载多个帖子
def scroll_to_show_enough_tweet(driver):
    while 1:
        scrolling(driver, 100000)

        bottom_comment = find_tweet_view(driver, tweet_num_limit - 1)
        if len(bottom_comment) != 0:
            break

        # 把滚动条再拉回顶部，否则评论列表到达最底端的提示显示不出来（一直卡在刷新状态）
        scrolling(driver, 0)

        time.sleep(0.5)


def scrolling(driver, location):
    js = f"var q=document.documentElement.scrollTop={location}"
    driver.execute_script(js)


def scrolling_popup(driver, location):
    scroll = driver.find_element_by_xpath('//div[@class="ReplyModal_scroll3_2kADQ"]')
    driver.execute_script(f'arguments[0].scrollTop={location}', scroll)


def find_comment_view(driver, data_index):
    comment_view_xpath = f'//div[@class="RepostCommentList_mar1_3VHkS"]//div[@class="vue-recycle-scroller__item-view"]/div[@data-index="{data_index}"]'
    return driver.find_elements_by_xpath(comment_view_xpath)


def find_active_comment_view(driver, data_index):
    comment_view_xpath = f'//div[@class="RepostCommentList_mar1_3VHkS"]//div[@class="vue-recycle-scroller__item-view"]/div[@data-active="true" and @data-index="{data_index}"]'
    return driver.find_elements_by_xpath(comment_view_xpath)


def find_second_comment_view(driver, data_index):
    comment_view_xpath = f'//div[@class="woo-box-flex woo-box-alignCenter woo-box-justifyCenter woo-modal-wrap ReplyModal_wrap_2j1bg"]//div[@data-index="{data_index}"]'
    return driver.find_elements_by_xpath(comment_view_xpath)


def find_active_second_comment_view(driver, data_index):
    comment_view_xpath = f'//div[@class="woo-box-flex woo-box-alignCenter woo-box-justifyCenter woo-modal-wrap ReplyModal_wrap_2j1bg"]//div[@data-index="{data_index}" and @data-active="true"]'
    return driver.find_elements_by_xpath(comment_view_xpath)


def find_tweet_view(driver, data_index):
    tweet_view_xpath = f'//div[@class="vue-recycle-scroller__item-view"]/div[@data-index="{data_index}"]'  # 跟评论的xpath一样
    return driver.find_elements_by_xpath(tweet_view_xpath)


def find_active_tweet_view(driver, data_index):
    tweet_view_xpath = f'//div[@class="vue-recycle-scroller__item-view"]/div[@data-index="{data_index}" and @data-active="true"]'  # 跟评论的xpath一样
    return driver.find_elements_by_xpath(tweet_view_xpath)


def check_second_display(comment_view):
    return comment_view.find_element_by_xpath('./..').get_attribute(
        'style') != 'transform: translateY(-9999px); z-index: -1;'


# tweet_url是一个帖子的内容网页，比如https://www.weibo.com/1883881851/LkJwDqkmO
def crawl_tweet(driver, tweet_url):
    driver.get(tweet_url)
    WebDriverWait(driver, 2).until(lambda driver: driver.find_elements_by_xpath(content_xpath))
    time.sleep(0.3)

    tweet_dict = get_tweet_content(driver)
    user_id, tweet_id = get_user_tweet_id(tweet_url)
    tweet_dict['user id'] = user_id
    tweet_dict['tweet id'] = tweet_id

    # print(tweet_dict)

    comment_list = get_tweet_comment(driver)

    if comment_list == []:
        return None

    tweet = {
        'source': tweet_dict,
        'comment': comment_list
    }
    return tweet


if __name__ == '__main__':
    driver = login()

    for filename in os.listdir('Dataset'):
        filepath = os.path.join('Dataset', filename)
        updatefilepath = os.path.join('UpdateDataset', filename)
        if os.path.exists(updatefilepath):
            continue
        post = json.load(open(filepath, 'r', encoding='utf-8'))

        uid = post["source"]["user id"]
        rid = post["source"]["tweet id"]
        label = post["source"]["label"]
        theme = post["source"]["theme"]

        source_url = f'https://weibo.com/{uid}/{rid}'

        try:
            tweet = crawl_tweet(driver, source_url)
            if tweet == None:
                tweet = post
            tweet['source']['label'] = label
            tweet['source']['theme'] = theme
            write_tweet(tweet, updatefilepath)
        except Exception:
            continue
