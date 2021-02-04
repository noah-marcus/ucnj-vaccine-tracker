import os
import time
import datetime

import tweepy
import facebook
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

# load in facebook api config
with open('config.yaml', 'r') as config_yaml:
    try:
        facebook_api_keys = yaml.safe_load(config_yaml)["facebook_api_keys"]
        if facebook_api_keys:
            page_access_token = facebook_api_keys['page_access_token']
    except yaml.YAMLError as e:
        print(e)
        exit(0)
    except KeyError as e:
        print("No Facebook API Keys in Config File.")
        exit(0)

# set up tweepy credentials
auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
auth.set_access_token(access_token, secret_access_token)

# Create Twitter API object
twitter_api = tweepy.API(auth)

# Create Facebook API object
facebook_api = facebook.GraphAPI(access_token=page_access_token, version="3.0")

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

                    # now we have location and availability
                    # availability format: "XXX / XXX", split and get fist number
                    if int(availability.split()[0]) > 0:
                        print("found - date: {}, location: {}, availability: {}".format(date, location, availability))
                        print("Tweeting")
                        try:
                            twitter_api.update_status("I've detected an update!! Appointments may be available.\n\nThere are currently {} spots available at {} on {}. \n\nhttps://ucnjvaccine.org/index.php/vaccine/vaccine_availability".format(availability, location, date))
                        except Exception as e:
                            print('error tweeting!!')
                            print('error - {}'.format(str(e)))

                        print("Posting to Facebook")
                        try:
                            facebook_api.put_object(
                              parent_object="100491275407459",
                              connection_name="feed",
                              message="I've detected an update!! Appointments may be available.\n\nThere are currently {} spots available at {} on {}. \n\nhttps://ucnjvaccine.org/index.php/vaccine/vaccine_availability".format(availability, location, date),
                            )
                        except Exception as e:
                            print('error posting to facebook!!')
                            print('error - {}'.format(str(e)))

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
