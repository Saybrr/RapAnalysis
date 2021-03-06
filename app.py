'''
Juno Mayer, Alex Marozick and Abduarraheem Elfandi
'''

from flask import Flask, render_template, url_for, request, redirect, abort, flash, jsonify, session, make_response
from flask_session import Session
from pprint import pprint as pp
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException, default_exceptions, Aborter
from spotipy.oauth2 import SpotifyOAuth
import os
import pprint
import requests
import json
import config
import spotipy
import time
import uuid
import logging
import pymongo
import analyzeSong
import datetime
import spotifyData

# logging.basicConfig(level=app.logger.debug)
class FileTypeException(HTTPException):   # this error is thrown when the file type is incorrect
    code = 400
    description = 'Error: File Type Incorrect!'

default_exceptions[400] = FileTypeException
abort = Aborter()



session_counter = 0 # for debugging
app = Flask(__name__)
secret_key = os.urandom(64)
app.secret_key = secret_key
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_FILE_DIR'] = './.flask_session/'
Session(app)
scope = "playlist-modify-public playlist-read-private user-follow-read user-read-recently-played"
client_id = config.get('SPOTIPY_CLIENT_ID','api') # NOTE hey do this
client_secret = config.get('SPOTIPY_CLIENT_SECRET','api') # NOTE hey do this
token_url = 'https://accounts.spotify.com/api/token'


mongo_clusters = config.get("CLIENT",'MONGODB')
db_name = config.get("DB_NAME",'MONGODB')

cluster = pymongo.MongoClient(mongo_clusters)
db = cluster[db_name]


possible_hues = [i for i in range(0,370) if i % 10 == 0]

# NOTE Make sure this is also the same in your Spotify app.
REDIRECT_URI = config.get('SPOTIPY_REDIRECT_URI','uri')
GENIUS_ACCESS_TOKEN = config.get('GENIUS_CLIENT_ACCESS_TOKEN','api')
# All the cached spotify data will be in this folder
# but will be deleted as soon as the user signsout/session ends.
caches_folder = '.spotify_caches/'
if not os.path.exists(caches_folder):
    os.makedirs(caches_folder)
    

def session_cache_path():

    '''
    Function that returns the session cached path (basically the cache folder).
    '''
    app.logger.debug("Starting session_cache_path")        # for debugging
    app.logger.debug(caches_folder)                        # for debugging
    app.logger.debug(session.get('uuid'))                  # for debugging
    app.logger.debug("Finished session_cache_path")        # for debugging
    return caches_folder + session.get('uuid')

def getsongdata(songdict :list) -> list:
    '''
    Gets the lyrics of a dict of artists and their songs  
    songdict : {"song" : SONGNAME, "artist"}
    returns [{object_id: ObjectID, "album": ALBUM, "colors" : COLORS, 'lyrics' : LYRICS}]
    COLORS is a list of lists. Each sublist corresponds to a section of the song (deliminated by something like [Intro] or [Chorus])
    '''

    dbArtists = db.list_collection_names()
    res = []
    query_result = []
    #for each song
    for item in songdict:
        #case of multiple artists per song 
        if type(item['artist']) == list: # NOTE the way I am doing these checks could probably be done better also something else to consider is what if no artist is given - Abduarraheem
            for a in item['artist']:
                artist = a.lower().replace("$","s").replace(".", "")
                # query_result = db[artist].find({ "song": item['song']  })
                if artist in dbArtists:
                    query_result = db[artist].find({"$text" :{"$search" : item['song'], "$caseSensitive" : False}})
                   
                    # print(item['song'])
                    # break because one of the artists was in the data base, 
                    # NOTE then since we can't be 100% sure that this artist 
                    # has the song we are looking for we would need to go 
                    # to the next artist in the list to check if the artist has the song given.
                    break  
        #case of one artist per song 
        else:
            artist = item['artist'].lower().replace("$","s").replace(".", "")
            if artist in dbArtists:
                query_result = db[artist].find({"$text" :{"$search" : item['song'], "$caseSensitive" : False}}) 

        if query_result == []:
            print(f"Error Artist {artist} not in the Data Base")
            continue
            # res.append("NoArtist")


        try:
            docs = [doc for doc in query_result]
            res.append(docs)
        except (UnboundLocalError, TypeError): # if the artist wasn't in the db, go the next song.
            continue
    # pp(res)
    logging.debug(f"RETURNING {res} from getsongdata")
    return res

@app.route('/')
def index():
    return render_template("index.html")


@app.route('/about')
def about():
    return render_template("about.html")

@app.route('/_analyzeSpotify')
def analyzeSpotify():
    print(request.args)
    analyzeType = request.args.get('type')
    # print(playlist)
    sp_oauth = SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=REDIRECT_URI, 
                            scope=scope, cache_path=session_cache_path(), show_dialog=True)
    spotify = spotipy.Spotify(auth_manager=sp_oauth)

    if analyzeType == 'playlist':
        playlistID = request.args.get('playlistID')
        songs_artists = spotifyData.get_songs_from_playlist(spotify, playlistID)
        songdata = getsongdata(songs_artists)
    elif analyzeType == 'recent':
        recent_num = request.args.get('recent_num', 10, int)
        songs_artists = spotifyData.get_recent_plays(spotify, recent_num)
        songdata = getsongdata(songs_artists)
    songs = []
    

    # get all song names from the playlist
    songnames = [songname['song'] for songname in songs_artists]
    # loop through all the queries returned from getsongdata
    for i, query in enumerate(songdata): 
        # Set skip to be true for init
        if query is not []:
            skip = True 
            # strip some characters from the song name that was gotten from the playlist
            songnameP = ((songnames[i].lower()).strip(" ")).replace(".",'') 
            # loop through the results of one query
            for songDict in query:
                # strip some characters from the song name that was gotten from the query
                #print(f'Song name from playlist{songnameP}') # for debugging 
                songnameDB = ((songDict['song'].lower()).strip(" ")).replace(".",'') 
                #print(f'Song name from Data Base{songnameDB}') # for debugging
                # check if the song name from the play list is a sub string of the one gotten from the database, 
                # NOTE this check might need to be modified.
                if songnameP in songnameDB: 
                    skip = False            # if so then do not skip 
                if not skip:
                    # call functions
                    lyrics, colors = parse_songdata2(songDict)
                    highlighted = highlight_words(lyrics,colors)
                    songs.append({'song' : songnames[i], 'index' : i, 'highlight' : highlighted})
                    break
        else: 
            print(f"Missing Artist {songnames[i]}")

    return jsonify(result=songs)

def parse_songdata2(songdata : dict) -> (list, list):
    '''
    Pareses a songdata query from the DB and returns a list of lyrics and colors to be 
    applied 
    '''
    skip_header = False
    proc_lyrics = []
    proc_colors = []
    # add a check to see if songdata is none.
    proc_lyrics = songdata['lyrics']  # string
    if 'colors' in songdata:
         proc_colors = songdata['colors']
    else:
        proc_colors = songdata['rhyme']
      # list of lists

    app.logger.debug(proc_lyrics)
    app.logger.debug(proc_colors)

    # split the lyrics into a list of lists
    split_newl = proc_lyrics.replace('\n', '\n ').split(' ')
    #take section headers out of lyrics
    lyrics_nosection = []
    for word in split_newl: 
        if '[' in word: 
            skip_header = True
        if ']' in word: 
            skip_header = False
            continue

        if not skip_header:
            lyrics_nosection.append(word)

    colorlist = []
    for l in proc_colors:
        for color in l: 
            colorlist.append(color)
    # these should be roughly the same
    #print(len(lyrics_nosection))
    #print(len(colorlist))

    return lyrics_nosection, colorlist



@app.route('/spotify_login')
def spotify_login():
    # global session_counter # used for debugging
    # If a new user joins give random id to the user.
    if not session.get('uuid'):
        session['uuid'] = str(uuid.uuid4())
        # session_counter +=1 # for debugging
        # print(f"Session counter: {session_counter}\n Session id: {session['uuid']}") # for debugging


    sp_oauth = SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=REDIRECT_URI, 
                            scope=scope, cache_path=session_cache_path(), show_dialog=True)
    
    # Authorization Code Flow Step 2
    if request.args.get('code'):
        auth_code = request.args.get('code')                        # get the code from the url.
        sp_token = sp_oauth.get_access_token(auth_code)             # use that code to get a token
        return redirect("/spotify_login")


    display = "Login to Spotify"
    if sp_oauth.get_cached_token():
        # Authorization Code Flow Step 3 
        # NOTE here we can get data from the Spotify API.
        spotify = spotipy.Spotify(auth_manager=sp_oauth)
        display = "User: " + spotify.me()["display_name"] + " (Sign Out)"
        spotify_data = spotifyData.spotify_data(spotify)
        # pp(spotify_data)
        return render_template("spotify.html", display=display, playlists=spotify_data["playlists"])
    return render_template("spotify_login.html", display=display)


@app.route('/login-btn', methods=['GET', 'POST'])    
def login():
    if request.method == 'POST':
        try:
            sp_oauth = SpotifyOAuth(client_id=client_id, client_secret=client_secret, redirect_uri=REDIRECT_URI, 
                                    scope=scope, cache_path=session_cache_path(), show_dialog=True)
            
            # So if we have a token(which means we are logged in) 
            # and the login button is clicked then we need to sign out

            if not sp_oauth.get_cached_token():
                # Authorization Code Flow Step 1
                auth_url = sp_oauth.get_authorize_url()
                return redirect(auth_url)
            return redirect("/sign_out")
        except TypeError:
            pass
    return redirect("spotify_login")


@app.route('/sign_out')
def sign_out():
    try:
        os.remove(session_cache_path())
        session.clear()
    except OSError as e:
        print ("Error: %s - %s." % (e.filename, e.strerror))
    return redirect('/')

# @app.route('/user-lyrics')
# def analyze_user_lyrics():
#     print("GOT INTO USER LYRICS")
#     lyrics = request.args.get('textboxid')
#     if lyrics is None:
#         print('lyrics is none')
#     print(lyrics)
#     return jsonify(result=lyrics)


@app.route('/get-lyrics')
def get_input():
    
    song_name = request.args.get('songid')
    artist_name = request.args.get('artistid')

    error = ''
    if (song_name == '' or artist_name == ''):
        print("User submitted an empty string: returning to throw error message")
        return jsonify(result = error)
    
    # print(song_name)
    # print(artist_name)

    song_name = song_name.strip()
    artist_name = artist_name.strip()

    app.logger.debug(song_name)                                       
    app.logger.debug(artist_name)                                            

    # pass in a dictionary to display and highlight in form {"song": song_name, "artist" : artist_name}

    songdata = getsongdata([{'song': song_name, 'artist': artist_name}])
    if songdata == []:
        return jsonify(result=f"Could not find artist {artist_name} in Database")
    elif songdata == [[]]:
        return jsonify(result="Found the Artist, but not the song! Check your spelling")
    
    # app.logger.debug(f"Result from query: \n {songdata}")
    songnames = [song[0]['song'] for song in songdata]
    print(songnames)
    lyrics = []
    colors = []
    for query in songdata:
        for song in query:
            print(song)
            if song_name.lower().replace("'","") in song['song'].lower().replace('’', ""):
                lyrics, colors = parse_songdata2(song)
                break

    if len(lyrics) + len(colors) == 0: 
        return jsonify(result="Found the Artist, but not the song! Sorry! PARSE ")

    highlighted = highlight_words(lyrics,colors)
    return jsonify(result = highlighted)


def highlight_words(lyrics : str, colorlist : list):
    """
    Applies a list of colors to a list of lyrics 
    """
    possible_hues = [i for i in range(0,370) if i % 10 == 0]
    #print(lyrics)
    highlighted = ""
    coloritr = 0
    skip = False
    for idx, word in enumerate(lyrics):
        first_pass = True
        try:
            if word != '\n':
                if colorlist[coloritr] != -1:
            
                    num = colorlist[coloritr]
                    modded_num = (num *2) % len(possible_hues)
                    if  modded_num == 0 and first_pass == False:
                        num += 1

                    if possible_hues[modded_num] in [350,360]:
                        first_pass = False
                    hue = possible_hues[modded_num]
                    lum = 80 if (modded_num) % 2 == 0 else 50
                    highlightword = f'<mark style=\"background: hsl({hue}, 100% ,{lum}% );\">{word}</mark> '
                
                    if '\n' in word:
                        highlightword += '<br>'

                    highlighted += highlightword
                
                else: 
                    highlighted += word.replace('\n','<br>') if '\n' in word else f"{word} "
                    
                coloritr +=1 

            else: 
                highlighted += '<br>'  
                app.logger.debug(f'FOUND NEWLINE at {idx}')        

        except IndexError:
            app.logger.debug(f"OVERFLOW at word {idx} out of {len(lyrics)}-- here's whats left") 
            app.logger.debug(lyrics[idx:])
            return highlighted
    
# if not skip
    return highlighted




@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(403)
def page_forbidden(e):
    return render_template("403.html"), 403


if __name__ == "__main__":
    app.run(debug=False)


# def parse_songdata(artist_name : str,song_name : str, songdata : list) -> (list, list):
#     '''
#     Pareses a songdata query from the DB and returns a list of lyrics and colors to be 
#     applied 
#     '''
#     skip_header = False

#     proc_lyrics = songdata['lyrics']  # string
#     proc_colors = songdata['colors']  # list of lists


#     # app.logger.debug(proc_lyrics)
#     # app.logger.debug(proc_colors)
#     if proc_lyrics == []: 
#         return [],[]

#     # split the lyrics into a list of lists
#     split_newl = proc_lyrics.replace('\n', '\n ').split(' ')
#     #take section headers out of lyrics
#     lyrics_nosection = []
#     for word in split_newl: 
#         if '[' in word: 
#             skip_header = True
#         if ']' in word: 
#             skip_header = False
#             continue

#         if not skip_header:
#             lyrics_nosection.append(word)

#     # app.logger.debug(lyrics_nosection)

#     #flatten colorlist from [list[lyrics]] to [lyrics]
#     colorlist = []
#     for l in proc_colors:
#         for color in l: 
#             colorlist.append(color)
#     # these should be roughly the same
#     print(len(lyrics_nosection))
#     print(len(colorlist))

#     return lyrics_nosection, colorlist
