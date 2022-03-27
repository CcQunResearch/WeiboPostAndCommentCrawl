# -*- coding: utf-8 -*-
# @Time    : 2022/3/21 16:39
# @Author  : CcQun
# @Email   : 13698603020@163.com
# @File    : utils.py
# @Software: PyCharm
# @Note    :
import json


# 保存网页源码（调试用）
def write_source(driver):
    filename = 'source.html'
    with open(filename, 'w', encoding='utf-8') as file_object:
        html = driver.page_source
        file_object.write(html)


def write_tweet(tweet, filepath):
    with open(filepath, 'w',encoding='utf-8') as file_obj:
        json.dump(tweet, file_obj, indent=4, ensure_ascii=False)
