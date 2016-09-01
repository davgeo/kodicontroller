
'''
kodicontroller.py

Contains functions which set up the correct parameters
for the corresponding Kodi JSON methods, calls the JSON method
via the instantiated KodiJSONClient and processes the responses.

'''
import urllib
import re
import requests
import os
import shutil
import hashlib
import logging

from kodijsonrpc import KodiJSONClient, EnableJSONLogging

EnableJSONLogging()

#################################################
# GetServer
#################################################
def GetServer(func):
  def wrapper(host, port, user, pwd, *args, **kwargs):
    server = KodiJSONClient(host, port, user, pwd)
    return func(server, *args, **kwargs)
  return wrapper

#################################################
# GetActivePlayer
#################################################
def GetActivePlayer(func):
  def wrapper(server, *args, **kwargs):
    try:
      player_id = server.Player.GetActivePlayers()[0]['playerid']
    except Exception as e:
      logging.info(e)
      return {}
    else:
      return func(server, player_id, *args, **kwargs)
  return wrapper

#################################################
# GetPlaylists
#################################################
def GetPlaylists(func):
  def wrapper(server, playlistType, *args, **kwargs):
    response = server.Playlist.GetPlaylists()
    for playlist in response:
      if playlist['type'] == playlistType:
        playlist_id = playlist['playlistid']
    return func(server, playlist_id, *args, **kwargs)
  return wrapper

#################################################
# GetThumbnail
# TODO: Fix hardcoded request auth
#################################################
def GetThumbnail(server, thumbnail, cacheDir):
  try:
    re.findall(r'.jpg', thumbnail)[0]
  except IndexError:
    return ''
  else:
    # Generate hash to avoid illegal characters in filepath (and give unique reference)
    fileHash = hashlib.md5(thumbnail.encode())
    imgPath = os.path.join(cacheDir, fileHash.hexdigest())

    if not os.path.exists(imgPath):
      logging.info("Downloading thumbnail from kodi server: {0}".format(thumbnail))

      if not os.path.exists(cacheDir):
        os.mkdir(cacheDir)

      if not os.path.isdir(cacheDir):
        raise Exception("Image cache directory path exists but is not a directory")

      url = server.url + 'image/' + urllib.parse.quote_plus(thumbnail)
      response = requests.get(url, auth=('xbmc', 'xbmc'), stream=True)

      with open(imgPath, 'wb') as f:
        response.raw.decode_content = True
        shutil.copyfileobj(response.raw, f)

    return fileHash.hexdigest()

#################################################
# ProcessThumbnails
# TODO: Revisit hardcoded static paths
#################################################
def ProcessThumbnails(server, thumbnailList):
  cacheDir = os.path.join('static', 'cache')

  for item in thumbnailList:
    item['thumbnail'] = GetThumbnail(server, item['thumbnail'], cacheDir)

#################################################
# GetResumePercent
#################################################
def GetResumePercent(resumeList):
  for item in resumeList:
    try:
      resume = item['resume']
    except KeyError:
      try:
        currentValue = item['watchedepisodes']
        maxValue = item['episode']
      except KeyError:
        logging.info("Unable to get values to calulate resume percentage")
        maxValue = 0
      finally:
        item['resume'] = {}
    else:
      maxValue = float(resume['total'])
      currentValue = float(resume['position'])
    finally:
      if maxValue == 0:
        resumePercent = 0
      else:
        resumePercent = 100.0 * currentValue/maxValue

      item['resume']['percentage'] = resumePercent

#################################################
# Status
#################################################
@GetServer
def Status(server):
  try:
    server.JSONRPC.Ping()
  except Exception as e:
    logging.info(e)
    return 'Offline'
  else:
    return 'Online'

#################################################
# VideoLibrary
#################################################
@GetServer
def VideoLibrary_Clean(server):
  raise NotImplementedError

@GetServer
def VideoLibrary_Export(server):
  raise NotImplementedError

@GetServer
def VideoLibrary_GetEpisodeDetails(server, episode_id):
  params = {'episodeid':int(episode_id),
            'properties':['title',
                          'plot',
                          'showtitle',
                          'thumbnail',
                          'tvshowid',
                          'episode',
                          'season',
                          'playcount',
                          'lastplayed',
                          'resume',
                          'file']}

  response = server.VideoLibrary.GetEpisodeDetails(params)
  episode = response['episodedetails']
  ProcessThumbnails(server, (episode, ))
  GetResumePercent((episode, ))
  return episode

@GetServer
def VideoLibrary_GetEpisodes(server, show_id, season_id):
  params = {'tvshowid':int(show_id),
            'season':int(season_id),
            'properties':['title',
                          'plot',
                          'showtitle',
                          'thumbnail',
                          'tvshowid',
                          'episode',
                          'season',
                          'playcount',
                          'lastplayed',
                          'resume',
                          'file']}

  response = server.VideoLibrary.GetEpisodes(params)
  episodes = response['episodes']

  for item in episodes:
    item['episode'] = int(item['episode'])

  ProcessThumbnails(server, episodes)
  GetResumePercent(episodes)
  return episodes

@GetServer
def VideoLibrary_GetGenres(server):
  raise NotImplementedError

@GetServer
def VideoLibrary_GetMovieDetails(server, movie_id):
  params = {'movieid':int(movie_id),
            'properties':['title',
                          'lastplayed',
                          'thumbnail',
                          'plot',
                          'playcount',
                          'resume',
                          'file']}
  response = server.VideoLibrary.GetMovieDetails(params)
  movie = response['moviedetails']
  ProcessThumbnails(server, (movie, ))
  GetResumePercent((movie, ))
  return movie

@GetServer
def VideoLibrary_GetMovieSetDetails(server):
  raise NotImplementedError

@GetServer
def VideoLibrary_GetMovieSets(server):
  raise NotImplementedError

@GetServer
def VideoLibrary_GetMovies(server):
  params = {'properties':['title',
                          'lastplayed',
                          'thumbnail',
                          'plot',
                          'playcount',
                          'resume',
                          'file']}
  recentMovies = server.VideoLibrary.GetMovies(params)

  try:
    movies = recentMovies['movies']
  except KeyError:
    movies = []
  else:
    ProcessThumbnails(server, movies)
    GetResumePercent(movies)

  return movies

@GetServer
def VideoLibrary_GetMusicVideoDetails(server):
  raise NotImplementedError

@GetServer
def VideoLibrary_GetMusicVideos(server):
  raise NotImplementedError

@GetServer
def VideoLibrary_GetRecentlyAddedEpisodes(server):
  params = {'properties':['title',
                          'showtitle',
                          'thumbnail',
                          'tvshowid',
                          'episode',
                          'season']}

  recentEpisodes = server.VideoLibrary.GetRecentlyAddedEpisodes(params)
  episodes = recentEpisodes['episodes']
  ProcessThumbnails(server, episodes)
  return episodes

@GetServer
def VideoLibrary_GetRecentlyAddedMovies(server):
  params = {'properties':['title',
                          'thumbnail']}
  recentMovies = server.VideoLibrary.GetRecentlyAddedMovies(params)

  try:
    movies = recentMovies['movies']
  except KeyError:
    movies = []
  else:
    ProcessThumbnails(server, movies)

  return movies

@GetServer
def VideoLibrary_GetRecentlyAddedMusicVideos(server):
  raise NotImplementedError

@GetServer
def VideoLibrary_GetSeasonDetails(server, season_id):
  raise NotImplementedError

@GetServer
def VideoLibrary_GetSeasons(server, show_id):
  params = {'tvshowid':int(show_id),
            'properties':['season',
                          'showtitle',
                          'playcount',
                          'episode',
                          'fanart',
                          'thumbnail',
                          'tvshowid',
                          'watchedepisodes',
                          'art']}

  response = server.VideoLibrary.GetSeasons(params)
  seasons = response['seasons']
  ProcessThumbnails(server, seasons)
  GetResumePercent(seasons)
  return seasons

@GetServer
def VideoLibrary_GetTVShowDetails(server, show_id):
  params = {'tvshowid':int(show_id),
            'properties':['title',
                          'thumbnail',
                          'plot']}
  response = server.VideoLibrary.GetTVShowDetails(params)
  tvshowdetails = response['tvshowdetails']
  ProcessThumbnails(server, (tvshowdetails, ))
  return tvshowdetails

@GetServer
def VideoLibrary_GetTVShows(server):
  params = {'properties':['title',
                          'thumbnail',
                          'episode',
                          'watchedepisodes']}
  response = server.VideoLibrary.GetTVShows(params)
  tvshows = response['tvshows']
  ProcessThumbnails(server, tvshows)
  GetResumePercent(tvshows)
  return tvshows

@GetServer
def VideoLibrary_RemoveEpisode(server, episode_id):
  params = {'episodeid':int(episode_id)}
  response = server.VideoLibrary.RemoveEpisode(params)

@GetServer
def VideoLibrary_RemoveMovie(server, movie_id):
  params = {'movieid':int(movie_id)}
  response = server.VideoLibrary.RemoveMovie(params)

@GetServer
def VideoLibrary_RemoveMusicVideo(server):
  raise NotImplementedError

@GetServer
def VideoLibrary_RemoveTVShow(server, show_id):
  params = {'tvshowid':int(show_id)}
  response = server.VideoLibrary.RemoveTVShow(params)

@GetServer
def VideoLibrary_Scan(server, show_dialog=False):
  params = {'showdialogs':show_dialog}
  response = server.VideoLibrary.Scan(params)

@GetServer
def VideoLibrary_SetEpisodeDetails(server, episode_id, playcount=None):
  params = {'episodeid':int(episode_id)}

  if playcount is not None:
    params.update({'playcount' : playcount})

  response = server.VideoLibrary.SetEpisodeDetails(params)

@GetServer
def VideoLibrary_SetMovieDetails(server, movie_id, playcount=None):
  params = {'movieid':int(movie_id)}

  if playcount is not None:
    params.update({'playcount' : playcount})

  response = server.VideoLibrary.SetMovieDetails(params)

@GetServer
def VideoLibrary_SetMovieSetDetails(server):
  raise NotImplementedError

@GetServer
def VideoLibrary_SetMusicVideoDetails(server):
  raise NotImplementedError

@GetServer
def VideoLibrary_SetSeasonDetails(server):
  raise NotImplementedError

@GetServer
def VideoLibrary_SetTVShowDetails(server):
  raise NotImplementedError

#################################################
# Player
#################################################
@GetServer
@GetActivePlayer
def Player_GetItem(server, player_id):
  params = {"playerid": player_id,
            'properties':['title',
                          'showtitle',
                          'thumbnail',
                          'tvshowid',
                          'episode',
                          'season',
                          'uniqueid']}
  response = server.Player.GetItem(params)

  item = response['item']
  ProcessThumbnails(server, (item, ))
  return item

@GetServer
def Player_GetPlayers(server):
  params = {"media": "video"}
  response = server.Player.GetPlayers(params)
  return response[0]['playercoreid']

@GetServer
@GetActivePlayer
def Player_GetProperties(server, player_id):
  params = {"playerid": player_id,
            "properties": ["type",
                           "partymode",
                           "speed",
                           "time",
                           "percentage",
                           "totaltime",
                           "playlistid",
                           "position",
                           "repeat",
                           "shuffled",
                           "canseek",
                           "canchangespeed",
                           "canmove",
                           "canzoom",
                           "canrotate",
                           "canshuffle",
                           "canrepeat",
                           "currentaudiostream",
                           "audiostreams",
                           "subtitleenabled",
                           "currentsubtitle",
                           "subtitles",
                           "live"]}
  return server.Player.GetProperties(params)

@GetServer
@GetActivePlayer
def Player_GoTo(server, player_id, index):
  params = {'playerid':int(player_id),
            'to':int(index)}
  response = server.Player.GoTo(params)

@GetServer
@GetActivePlayer
def Player_Move(server, player_id):
  raise NotImplementedError

@GetServer
@GetPlaylists
def Player_Open(server, playlist_id):
  params = {"item" : {"playlistid" : int(playlist_id)}}
  return server.Player.Open(params)

@GetServer
@GetActivePlayer
def Player_PlayPause(server, player_id):
  response = server.Player.PlayPause({"playerid":player_id})
  return response['speed']

@GetServer
@GetActivePlayer
def Player_Rotate(server, player_id):
  raise NotImplementedError

@GetServer
@GetActivePlayer
def Player_Seek(server, player_id, position):
  params = {"playerid": player_id}
  params['value'] = {'percentage': float(position)}
  response = server.Player.Seek(params)

@GetServer
@GetActivePlayer
def Player_SetAudioStream(server, player_id):
  raise NotImplementedError

@GetServer
@GetActivePlayer
def Player_SetPartymode(server, player_id):
  raise NotImplementedError

@GetServer
@GetActivePlayer
def Player_SetRepeat(server, player_id):
  raise NotImplementedError

@GetServer
@GetActivePlayer
def Player_SetShuffle(server, player_id):
  raise NotImplementedError

@GetServer
@GetActivePlayer
def Player_SetSpeed(server, player_id, speed):
  params = {"playerid": player_id,
            "speed": speed}
  response = server.Player.SetSpeed(params)

@GetServer
@GetActivePlayer
def Player_SetSubtitle(server, player_id, mode):
  # mode can be: on, off, next, previous
  params = {"playerid": player_id,
            "subtitle": mode}
  response = server.Player.SetSubtitle(params)

@GetServer
@GetActivePlayer
def Player_Stop(server, player_id):
  response = server.Player.Stop({"playerid":player_id})

@GetServer
@GetActivePlayer
def Player_Zoom(server, player_id):
  raise NotImplementedError

#################################################
# Playerlist
#################################################
@GetServer
@GetPlaylists
def Playlist_Add(server, playlist_id, params):
  params.update({'playlistid':int(playlist_id)})
  response = server.Playlist.Add(params)

@GetServer
@GetPlaylists
def Playlist_Clear(server, playlist_id):
  params = {'playlistid':int(playlist_id)}
  response = server.Playlist.Clear(params)

@GetServer
@GetPlaylists
def Playlist_GetItems(server, playlist_id):
  params = {'playlistid':int(playlist_id),
            'properties':['title',
                          'showtitle',
                          'thumbnail',
                          'tvshowid',
                          'episode',
                          'season',
                          'uniqueid']}

  response = server.Playlist.GetItems(params)

  try:
    episodes = response['items']
  except KeyError:
    episodes = []
  else:
    ProcessThumbnails(server, episodes)

  return episodes

@GetServer
def Playlist_GetProperties(server):
  raise NotImplementedError

@GetServer
def Playlist_Insert(server):
  raise NotImplementedError

@GetServer
@GetPlaylists
def Playlist_Remove(server, playlist_id, index):
  params = {'playlistid':int(playlist_id),
            'position':int(index)}
  response = server.Playlist.Remove(params)

@GetServer
def Playlist_Swap(server):
  raise NotImplementedError

#################################################
# Application
#################################################
@GetServer
def Favourites_AddFavourite(server):
  raise NotImplementedError

@GetServer
def Favourites_GetFavourites(server):
  params = {'properties': ["path",
                           "thumbnail",
                           "window",
                           "windowparameter"]}
  response = server.Favourites.GetFavourites(params)

  try:
    favourites = response['favourites']
  except KeyError:
    favourites = []
  else:
    ProcessThumbnails(server, favourites)

  return favourites


#################################################
# Application
#################################################
@GetServer
def Application_GetProperties(server):
  params = {"properties": ["volume", "muted"]}
  response = server.Application.GetProperties(params)
  return response

@GetServer
def Application_Quit(server):
  response = server.Application.Quit()

@GetServer
def Application_SetMute(server):
  params = {"mute": "toggle"}
  response = server.Application.SetMute(params)

@GetServer
def Application_SetVolume(server, volume):
  params = {"volume": int(volume)}
  response = server.Application.SetVolume(params)

#################################################
# System
#################################################
@GetServer
def System_EjectOpticalDrive(server):
  raise NotImplementedError

@GetServer
def System_GetProperties(server):
  raise NotImplementedError

@GetServer
def System_Hibernate(server):
  response = server.System.Hibernate()

@GetServer
def System_Reboot(server):
  response = server.System.Reboot()

@GetServer
def System_Shutdown(server):
  response = server.System.Shutdown()

@GetServer
def System_Suspend(server):
  response = server.System.Suspend()
