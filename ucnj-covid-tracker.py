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

# initialize posting variables
first_post = True
recently_posted = False
wait_post_count = 0
follow_up_threshold = 5

def configure_twitter():
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

    # Create Twitter API object
    twitter_api = tweepy.API(auth)

    return twitter_api

def configure_facebook():
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

    # Create Facebook API object
    facebook_api = facebook.GraphAPI(access_token=page_access_token, version="3.0")

    return facebook_api

# function for posting to facebook and twitter
def post(appts, post_msg_start):
    # set up fb post
    fb_msg = post_msg_start

    # set up tweet
    twitter_msg = post_msg_start
    twitter_msg_length = len(post_msg_start)
    tweet_id = None
    sent_last_tweet = False

    # look through appointments and build message
    for appt in appts:

        # if adding the appointment and two new lines fits, add it
        if (twitter_msg_length+len(appt)+1) < 280:
            sent_last_tweet = False
            twitter_msg = twitter_msg + appt + "\n"
            twitter_msg_length = len(twitter_msg)

            fb_msg = fb_msg + appt + "\n"
        else:
            print('tweeting msg')
            try:
                if tweet_id:
                    tweet = twitter_api.update_status(twitter_msg, tweet_id)
                    tweet_id = tweet.id_str

                else:
                    tweet = twitter_api.update_status(twitter_msg)
                    tweet_id = tweet.id_str

                sent_last_tweet = True
            except Exception as e:
                print('error tweeting!!')
                print('error - {}'.format(str(e)))

            twitter_msg = "[Continued]\n\nWebsite: ucnjvaccine.org/index.php/vaccine/vaccine_availability\n\nAlso:\n"
            twitter_msg_length = len(twitter_msg)

    # post remaining tweet if not tweeted
    if not sent_last_tweet:
        print('tweeting msg')
        try:
            twitter_api.update_status(twitter_msg, tweet_id)
        except Exception as e:
            print('error tweeting!!')
            print('error - {}'.format(str(e)))

    print("Posting to Facebook")
    try:
        facebook_api.put_object(
          parent_object="100491275407459",
          connection_name="feed",
          message=fb_msg,
        )
    except Exception as e:
        print('error posting to facebook!!')
        print('error - {}'.format(str(e)))

def get_table_html():
    table_html = ""
    try:
        options = Options()
        options.headless = True

        driver = webdriver.Chrome(options=options)
        driver.get("https://www.ucnjvaccine.org/index.php/vaccine/vaccine_availability")

        table_element = driver.find_element_by_id('datatable-grouping')
        table_element = table_element.find_element_by_tag_name('tbody')
        table_html = table_element.get_attribute('innerHTML')
    except Exception as e:
        print('{} - Could not get URL'.format(datetime.datetime.now()))
        print('Exception - {}'.format(str(e)))
    finally:
        driver.quit()
        return table_html

def find_appointments(table_html):
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
            availability = ""

            # walk through each column in the row, collect data on location and availability
            # first col = location, second col = availability
            for column in row:

                if isinstance(column, NavigableString) or column == "\n":
                    continue

                if index == 0:
                    location = column.text
                    index += 1
                elif index == 1:
                    availability = column.text
                    index += 1

            # now we have location and availability
            # availability format: "XXX / XXX", split and get first number
            if int(availability.split()[0]) > 0:
                print("{} - FOUND: date: {}, location: {}, availability: {}".format(datetime.datetime.now(), date, location, availability))

                appt = " - {} appointments available at {} on {}".format(availability, location, date)
                appts.append(appt)
            else:
                print("{} - 0 vaccines available at {} on {}".format(datetime.datetime.now(), location, date))

    return appts

if __name__ == "__main__":

    # configure APIs
    twitter_api = configure_twitter()
    facebook_api = configure_facebook()

    while (True):
        print('first_post: {}, recently_posted: {}, wait_post_count: {}'.format(first_post, recently_posted, wait_post_count))
        try:
            table_html = get_table_html()

            if 'There are no appointments at this time' not in table_html:
                appts = find_appointments(table_html)

                # post if we found some appointments
                if (len(appts) > 0):
                    # always send first post in batch
                    if first_post:
                        start_msg = "I\'ve detected some appointments!\n\nCheck the website: ucnjvaccine.org/index.php/vaccine/vaccine_availability\n\nAt this time, there are:\n"
                        post(appts, start_msg)
                        first_post = False
                        recently_posted = True

                    # check how long since last post
                    if wait_post_count >= follow_up_threshold:
                        recently_posted = False

                    # if we have recently posted, increase counter
                    if recently_posted:
                        wait_post_count += 1
                        print('waiting to post')
                    else:
                        start_msg = "There are still appointments available!\n\nCheck the website: ucnjvaccine.org/index.php/vaccine/vaccine_availability\n\nAt this time, there are:\n"
                        post(appts, start_msg)
                        recently_posted = True
                        wait_post_count = 1

                # if there is nothing to tweet, reset booleans and counts
                else:
                    first_post = True
                    recently_posted = False
                    wait_post_count = 0

            else:
                # no vaccines available, reset counters
                first_post = True
                recently_posted = False
                wait_post_count = 0
                print('{} - no vaccine'.format(datetime.datetime.now()))

        except Exception as e:
            print("{} - Exception!!".format(datetime.datetime.now()))
            print('Exception: {}'.format(str(e)))
        finally:
            time.sleep(60)
