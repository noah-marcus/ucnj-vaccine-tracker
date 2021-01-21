import os
import time
import datetime

from requests_html import HTMLSession
from bs4 import BeautifulSoup
import tweepy
import yaml


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
        session = HTMLSession()

        url = 'https://ucnjvaccine.org/index.php/vaccine/vaccine_availability'
        r = session.get(url)
        r.html.render()

        database_grouping = r.html.find('#datatable-grouping', first=True)
        no_covid_vaccine_search = database_grouping.search('There are no appointments at this time')

        # the search could not find this expression, which means the table has some data in it
        if not no_covid_vaccine_search:


            table_body = database_grouping.find('tbody')
            if table_body and len(table_body) > 0:
                table_html = table_body[0].html
                soup = BeautifulSoup(table_html, 'html.parser')

                table_rows = soup.find_all('tr')

                if len(table_rows) > 0:
                    # first row of table will always be the date, remove it
                    vaccine_rows = table_rows[1:]

                    # if there are still rows, then the table has some vaccine information up
                    if vaccine_rows:

                        # walk through each individual row
                        for row in vaccine_rows:

                            index = 0
                            location = ""
                            availability = ""

                            # walk through each column in the row, collect data on location and availability
                            # first col = location, second col = availability
                            for column in row:

                                # remove all new lines
                                if not column == "\n":
                                    # print("index: {}, text: {}".format(index, column.text))

                                    if index == 0:
                                        location = column.text
                                        index += 1
                                    elif index == 1:
                                        availability = column.text
                                        index += 1

                            # print("found - location: {}, availability: {}".format(location, availability))
                            # now we have location and availability
                            # availability format: "XXX / XXX", split and get fist number
                            if int(availability.split()[0]) > 0:
                                print("{} - TWEETING: I've detected an update!! Appointments may be available.\n\n There are currently {} spots available at {}. \n\n https://ucnjvaccine.org/index.php/vaccine/vaccine_availability".format(datetime.datetime.now(), availability, location))
                                api.update_status("I've detected an update!! Appointments may be available.\n\n There are currently {} spots available at {}. \n\n https://ucnjvaccine.org/index.php/vaccine/vaccine_availability".format(availability, location))
                            else:
                                print("{} - 0 vaccines available at {}".format(datetime.datetime.now(), location))
        else:
            print('{} - no vaccine'.format(datetime.datetime.now()))

    except Exception as e:
        print(e)

    finally:
        time.sleep(600)
