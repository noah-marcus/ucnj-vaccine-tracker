import os
import time
import datetime

import tweepy
import yaml
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from bs4 import NavigableString

# load in twitter api config
with open('config.yaml', 'r') as config_yaml:
    try:
        twitter_api_keys = yaml.safe_load(config_yaml)["twitter_api_keys"]
        if twitter_api_keys:
            consumer_key = twitter_api_keys['consumer_key']
            consumer_secret = twitter_api_keys['consumer_secret']
            access_token = twitter_api_keys['access_token']
            secret_access_token = twitter_api_keys['secret_access_token']
    except yaml.YAMLError as e:
        print(e)
        exit(0)
    except KeyError as e:
        print("No Twitter API Keys in Config File.")
        exit(0)

# set up tweepy credentials
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, secret_access_token)

# Create API object
api = tweepy.API(auth)

while(True):

    try:
        options = Options()
        options.headless = True

        driver = webdriver.Chrome(options=options)
        driver.get("https://ucnjvaccine.org/index.php/vaccine/vaccine_availability")

        table_element = driver.find_element_by_id('datatable-grouping')
        table_element = table_element.find_element_by_tag_name('tbody')
        table_html = table_element.get_attribute('innerHTML')

        if 'There are no appointments at this time' not in table_html:
            soup = BeautifulSoup(table_html, 'html.parser')
            table_rows = soup.find_all('tr')

            # capture date a little globally
            date = "(No Date Found)"

            # walk through each individual row
            for row in table_rows:

                # if row only has one column, it is the date
                if (len(row) == 1):
                    date = row.text
                else:
                    index = 0
                    location = ""
                    availability = ""

                    # walk through each column in the row, collect data on location and availability
                    # first col = location, second col = availability
                    for column in row:

                        if isinstance(column, NavigableString) or column == "\n":
                            continue

                        # print("index: {}, text: {}".format(index, column.text))

                        if index == 0:
                            location = column.text
                            index += 1
                        elif index == 1:
                            availability = column.text
                            index += 1

                    # print("found - date: {}, location: {}, availability: {}".format(date, location, availability))
                    # now we have location and availability
                    # availability format: "XXX / XXX", split and get fist number
                    if int(availability.split()[0]) > 0:
                        print("{} - TWEETING: I've detected an update!! Appointments may be available.\n\n There are currently {} spots available at {} on {}. \n\n https://ucnjvaccine.org/index.php/vaccine/vaccine_availability".format(datetime.datetime.now(), availability, location, date))
                        api.update_status("I've detected an update!! Appointments may be available.\n\n There are currently {} spots available at {} on {}. \n\n https://ucnjvaccine.org/index.php/vaccine/vaccine_availability".format(availability, location, date))

                    else:
                        print("{} - 0 vaccines available at {} on {}".format(datetime.datetime.now(), location, date))

        else:
            print('{} - no vaccine'.format(datetime.datetime.now()))

    except Exception as e:
        print("{} - Exception!!".format(datetime.datetime.now()))
        print(str(e))

    finally:
        driver.quit()
        time.sleep(300)
