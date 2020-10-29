'''
Configuration code based on Prof Michal Young's Example: 
https://github.com/MichalYoung/Enroute/blob/master/config.py
'''
import os 
import configparser
import logging


CONFIG_FILE = 'rap_analysis/config.ini'

typedict = {'api': 'APIKEYS', 'uri': 'REDIRECT_URI'}

config_key = ['Spotify','Genius']

config_dict = {}

config = configparser.ConfigParser()
have_file = False 

if os.path.exists(CONFIG_FILE):
    logging.info(f"Found a config file, loading from {CONFIG_FILE}... ")
    have_file = True
    config.read(CONFIG_FILE)


def get(key : str,keytype : str):
    '''
    Gets a value from the config file
    In this case, its only really the Mapbox API key 
    We check OS evironment variables first so that devs can put keys in 
    hosting service's config vars intead of supply an ini file
    '''
    t = typedict[keytype]

    if key in os.environ:
        val = os.environ[key]
    elif have_file:
        val = config[t][key]
    else:
        raise NameError(f"{key} is not a valid config -- not found in file")


    return val