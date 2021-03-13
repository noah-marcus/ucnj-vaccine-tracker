import os
import time
import yaml
import tweepy
import random
import requests
import datetime
import facebook

from bs4 import BeautifulSoup
from bs4 import NavigableString
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def pass_captcha(url, captcha_site_key, _2captcha_api_key):
    start = datetime.datetime.now()
    print('{} - Sending 2captcha request'.format(start))

    # set up 2captcha form
    _2capthca_form = {
        "method": "userrecaptcha",
        "googlekey": captcha_site_key,
        "key": _2captcha_api_key,
        "pageurl": url,
        "json": True
    }

    # send 2captcha request
    try:
        response = requests.post('http://2captcha.com/in.php', data=_2capthca_form)
        request_id = response.json()['request']
    except Exception as e:
        print(e.__class__.__name__)
        print("Error sending 2captcha request form")
        print(str(e))
        print(response.json())
        return None

    # wait to start request
    time.sleep(15)

    # wait for 2captcha to solve the recaptcha
    _2captcha_url = f"http://2captcha.com/res.php?key={_2captcha_api_key}&action=get&id={request_id}&json=1"
    ready = False
    while (not ready):
        # get 2captcha response
        try:
            res = requests.get(_2captcha_url)
        except Exception as e:
            print(e.__class__.__name__)
            print("Error getting 2captcha response")
            print(str(e))
            return None

        # if response is 0, wait 3 seconds
        if res.json()['status']==0:
            if res.json()['request'] == 'ERROR_CAPTCHA_UNSOLVABLE':
                # record how long it took
                end = datetime.datetime.now()
                time_elapsed = (end-start).total_seconds()
                print("{} - Got 'ERROR_CAPTCHA_UNSOLVABLE' from 2captcha in {} seconds. Resubmitting...".format(end, time_elapsed))

                return "resubmit"

            time.sleep(10)
        else:
            requ = res.json()['request']
            # record how long it took
            end = datetime.datetime.now()
            time_elapsed = (end-start).total_seconds()
            print("{} - Got response from 2captcha in {} seconds".format(end, time_elapsed))

            # return token
            return requ

def get_table_html(url, _2captcha_requ):
    try:
        print("{} - Getting table html from url: {}".format(datetime.datetime.now(), url))
        options = Options()
        options.headless = True

        driver = webdriver.Chrome(options=options)
        driver.get(url)

        # submit 2captcha response to solve recaptcha
        try:
            js = f'document.getElementById("g-recaptcha-response").innerHTML="{_2captcha_requ}";'
            driver.execute_script(js)
            submit_button_xpath = '//input[@type="submit" and @value="Continue"]'
            driver.find_element_by_xpath(submit_button_xpath).submit()
        except Exception as e:
            print(e.__class__.__name__)
            print("Error submitting 2captcha response to solve recaptcha")
            print(str(e))
            driver.quit()
            return None

        # wait 3 seconds for page to load
        time.sleep(3)
        driver.save_screenshot('ucnj.png')
        table_element = driver.find_element_by_id('datatable-grouping')
        table_element = table_element.find_element_by_tag_name('tbody')
        table_html = table_element.get_attribute('innerHTML')

        driver.quit()
        return table_html

    except Exception as e:
        print("Error getting table html")
        print("{} - {}".format(e.__class__.__name__, str(e)))
        driver.quit()
        return None

def find_appointments(table_html):
    print("{} - Looking for appointments in table_html".format(datetime.datetime.now()))

    soup = BeautifulSoup(table_html, 'html.parser')
    table_rows = soup.find_all('tr')

    # capture date a little globally
    date = "(No Date Found)"
    appts = []

    # walk through each individual row
    for row in table_rows:

        # if row only has one column, it is the date
        if (len(row) == 1):
            date = row.text
        else:
            index = 0
            location = ""
            available = False

            # walk through each column in the row, collect data on location and status
            # first col = location, second col = status
            for column in row:

                if isinstance(column, NavigableString) or column == "\n":
                    continue

                if index == 0:
                    location = column.text
                    index += 1
                elif index == 1:
                    status = column.find_all('i')
                    if len(status) > 0 and status[0].has_attr('class'):
                        # nothing is available if there is 'fa-times-circle' (image used to signal nothing is available)
                        if 'fa-times-circle' not in status[0]['class']:
                            available = True

            # now we have location and status
            if (available):
                appt = {"location": location, "date": date}
                appts.append(appt)

    return appts

def check_page(url, _2captcha_api_key, captcha_site_key):
    try:
        print("{} - Checking page: {}".format(datetime.datetime.now(), url))

        # get recaptcha request token
        requ = None
        send_2captcha = True
        _2captcha_request_limit = 3
        reqs = 0
        while (send_2captcha and reqs < _2captcha_request_limit):
            requ = pass_captcha(url, captcha_site_key, _2captcha_api_key)
            if requ == "resubmit":
                time.sleep(5)
                reqs += 1
            else:
                send_2captcha = False

        # got request, captcha was passed
        if requ != None:
            table_html = get_table_html(url, requ)
            if table_html != None:
                # check to make sure there are some rows in the table
                if 'There are no appointments at this time' not in table_html:
                    try:
                        appts = find_appointments(table_html)

                        if appts == []:
                            return None

                        return appts
                    except Exception as e:
                        print("Error parsing table_html for available appointments")
                        print("{} - {}".format(e.__class__.__name__, str(e)))
                        return None
                else:
                    print("{} - No appointments in table".format(datetime.datetime.now()))
                    return None

            else:
                print("{} - Could not get table html.".format(datetime.datetime.now()))
                return None

        else:
            print("{} - Could not solve captcha.".format(datetime.datetime.now()))
            return None

    except Exception as e:
        print("Error Checking Page")
        print("{} - {}".format(e.__class__.__name__, str(e)))
        return None
