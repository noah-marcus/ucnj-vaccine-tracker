import os
import time
import yaml
import tweepy
import datetime
import facebook

from scripts.check_page import check_page

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

def configure_2captcha():
    with open('config.yaml', 'r') as config:
        try:
            cfg = yaml.safe_load(config)
            _2captcha_api_key = cfg.get('_2captcha_api_key', None)

            if _2captcha_api_key == None:
                print('captcha keys not specified')
                exit(0)

            return _2captcha_api_key
        except:
            print('configure_2captcha: Could not open config')
            exit(0)

def build_msg(results):
    msg = "Appointments live!\n\nMust be a resident or work in Union County. \n\nCheck the website: ucnjvaccine.org/index.php/vaccine/vaccine_availability\n\n"
    return msg

# function for posting to twitter
def post(msg, tweet_id=None):

    print('{} - Tweeting msg:'.format(datetime.datetime.now()))
    print(msg)

    try:
        if tweet_id:
            tweet = twitter_api.update_status(msg, tweet_id)
            tweet_id = tweet.id_str
        else:
            tweet = twitter_api.update_status(msg)
            tweet_id = tweet.id_str

        return tweet_id
    except Exception as e:
        print('error tweeting!!')
        print('error - {}'.format(str(e)))
        return None

    print("Posting to Facebook")
    try:
        facebook_api.put_object(
          parent_object="100491275407459",
          connection_name="feed",
          message=msg,
        )
    except Exception as e:
        print('error posting to facebook!!')
        print('error - {}'.format(str(e)))

    return tweet_id

if __name__ == "__main__":

    # configure APIs
    twitter_api = configure_twitter()
    # facebook_api = configure_facebook()
    _2captcha_api_key = configure_2captcha()

    # union county captcha site key
    captcha_site_key = "6LdYK1MaAAAAAPjTovMhKTgBChwIs5FEnpgRI06B"

    # configure page parameters
    url = "https://ucnjvaccine.org/index.php/vaccine/vaccine_availability"

    while(True):
        print("\n******************************************")
        appts = check_page(url, _2captcha_api_key, captcha_site_key)
        if appts == None or appts == []:
            print("{} - No appointments found".format(datetime.datetime.now()))
        else:
            # appointments available! send out alerts
            print("{} - Appointments found!".format(datetime.datetime.now()))
            msg = build_msg(appts)
            tweet_id = post(msg)

            # wait until they are not available again
            while(appts != None):
                print("{} - Appointments still available, sleeping for 180 seconds.".format(datetime.datetime.now()))
                time.sleep(180)
                print("{} - Checking status.".format(datetime.datetime.now()))
                appts = check_page(url, _2captcha_api_key, captcha_site_key)

            # there are no more appointments
            print('{} - There are no more appointments available'.format(datetime.datetime.now()))
            done_msg = "All available apointments are now gone."
            post(done_msg, tweet_id)

        print("{} - Done. Sleeping for 300 seconds.".format(datetime.datetime.now()))
        print("******************************************\n")
        time.sleep(300)
