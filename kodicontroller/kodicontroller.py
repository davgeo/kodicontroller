
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
import kodijsonrpc

''' Decorators '''
#################################################
# CheckServerValid
#################################################
def CheckServerValid(func):
  def wrapper(self, *args, **kwargs):
    if self.server is None:
      return None
    else:
      return func(self, *args, **kwargs)
  return wrapper

#################################################
# GetActivePlayer
#################################################
def GetActivePlayer(func):
  @CheckServerValid
  def wrapper(self, *args, **kwargs):
    try:
      player_id = self.server.Player.GetActivePlayers()[0]['playerid']
    except Exception as e:
      logging.info(e)
      return {}
    else:
      return func(self, player_id, *args, **kwargs)
  return wrapper

#################################################
# GetPlaylists
#################################################
def GetPlaylists(func):
  @CheckServerValid
  def wrapper(self, playlistType, *args, **kwargs):
    response = self.server.Playlist.GetPlaylists()
    for playlist in response:
      if playlist['type'] == playlistType:
        playlist_id = playlist['playlistid']
    return func(self, playlist_id, *args, **kwargs)
  return wrapper

''' Controller class '''
#################################################
#
# KodiController
#
# Controller class for Kodi. This contains functions
# which set up the correct parameters for the
# corresponding Kodi JSON methods, calls the JSON
# method via the instantiated KodiJSONClient and
# processes the responses.
#
#################################################
class KodiController(object):
  #################################################
  # __init__
  #################################################
  def __init__(self, cache_thumbnail_dir=None, host=None, port=None, user=None, pwd=None):
    self.cache_thumbnail_dir = cache_thumbnail_dir

    if host is None or port is None or user is None or pwd is None:
      self.server=None
    else:
      set_server(host, port, user, pwd)

  #################################################
  # EnableLogging
  #################################################
  def EnableLogging(self):
    kodijsonrpc.EnableJSONLogging()

  #################################################
  # SetServer
  #################################################
  def SetServer(self, host, port, user, pwd):
    self.auth = (user, pwd)
    self.server = kodijsonrpc.KodiJSONClient(host, port, user, pwd)

  #################################################
  # SetThumbnailCache
  #################################################
  def SetThumbnailCache(self, path):
    self.cache_thumbnail_dir = path

  #################################################
  # GetThumbnail
  #################################################
  def GetThumbnail(self, thumbnail):
    if self.cache_thumbnail_dir is None or self.auth is None:
      return ''
    else:
      thumbnail = thumbnail.strip('/')
      ext = os.path.splitext(thumbnail)[1]

      if ext not in ('.jpg', '.png'):
        return ''
      else:
        # Generate hash to avoid illegal characters in filepath (and give unique reference)
        fileHash = hashlib.md5(thumbnail.encode())
        imgPath = os.path.join(self.cache_thumbnail_dir, fileHash.hexdigest())

        if not os.path.exists(imgPath):
          logging.info("Downloading thumbnail from kodi server: {0}".format(thumbnail))

          if not os.path.exists(self.cache_thumbnail_dir):
            os.mkdir(self.cache_thumbnail_dir)

          if not os.path.isdir(self.cache_thumbnail_dir):
            raise Exception("Image cache directory path exists but is not a directory")

          url = self.server.url + 'image/' + urllib.parse.quote_plus(thumbnail)
          response = requests.get(url, auth=self.auth, stream=True)

          with open(imgPath, 'wb') as f:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, f)

        return fileHash.hexdigest()

  #################################################
  # ProcessThumbnails
  #################################################
  def ProcessThumbnails(self, thumbnailList):
    if self.cache_thumbnail_dir is not None:
      for item in thumbnailList:
        item['thumbnail'] = self.GetThumbnail(item['thumbnail'])

  #################################################
  # GetResumePercent
  #################################################
  def GetResumePercent(self, resumeList):
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
  @CheckServerValid
  def Status(self):
    try:
      self.server.JSONRPC.Ping()
    except Exception as e:
      logging.info(e)
      return 'Offline'
    else:
      return 'Online'

  #################################################
  # VideoLibrary
  #################################################
  @CheckServerValid
  def VideoLibrary_Clean(self):
    raise NotImplementedError

  @CheckServerValid
  def VideoLibrary_Export(self):
    raise NotImplementedError

  @CheckServerValid
  def VideoLibrary_GetEpisodeDetails(self, episode_id):
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

    response = self.server.VideoLibrary.GetEpisodeDetails(params)
    episode = response['episodedetails']
    self.ProcessThumbnails((episode, ))
    self.GetResumePercent((episode, ))
    return episode

  @CheckServerValid
  def VideoLibrary_GetEpisodes(self, show_id, season_id):
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
                            'file',
                            'firstaired',
                            'specialsortseason',
                            'specialsortepisode']}

    response = self.server.VideoLibrary.GetEpisodes(params)
    episodes = response['episodes']

    for item in episodes:
      item['episode'] = int(item['episode'])
      item['season'] = int(item['season'])
      item['specialsortseason'] = int(item['specialsortseason'])
      item['specialsortepisode'] = int(item['specialsortepisode'])

    self.ProcessThumbnails(episodes)
    self.GetResumePercent(episodes)
    return episodes

  @CheckServerValid
  def VideoLibrary_GetGenres(self):
    raise NotImplementedError

  @CheckServerValid
  def VideoLibrary_GetMovieDetails(self, movie_id):
    params = {'movieid':int(movie_id),
              'properties':['title',
                            'lastplayed',
                            'thumbnail',
                            'plot',
                            'playcount',
                            'resume',
                            'file']}
    response = self.server.VideoLibrary.GetMovieDetails(params)
    movie = response['moviedetails']
    self.ProcessThumbnails((movie, ))
    self.GetResumePercent((movie, ))
    return movie

  @CheckServerValid
  def VideoLibrary_GetMovieSetDetails(self):
    raise NotImplementedError

  @CheckServerValid
  def VideoLibrary_GetMovieSets(self):
    raise NotImplementedError

  @CheckServerValid
  def VideoLibrary_GetMovies(self):
    params = {'properties':['title',
                            'lastplayed',
                            'thumbnail',
                            'plot',
                            'playcount',
                            'resume',
                            'file']}
    recentMovies = self.server.VideoLibrary.GetMovies(params)

    try:
      movies = recentMovies['movies']
    except KeyError:
      movies = []
    else:
      self.ProcessThumbnails(movies)
      self.GetResumePercent(movies)

    return movies

  @CheckServerValid
  def VideoLibrary_GetMusicVideoDetails(self):
    raise NotImplementedError

  @CheckServerValid
  def VideoLibrary_GetMusicVideos(self):
    raise NotImplementedError

  @CheckServerValid
  def VideoLibrary_GetRecentlyAddedEpisodes(self):
    params = {'properties':['title',
                            'showtitle',
                            'thumbnail',
                            'tvshowid',
                            'episode',
                            'season']}

    recentEpisodes = self.server.VideoLibrary.GetRecentlyAddedEpisodes(params)
    episodes = recentEpisodes['episodes']
    self.ProcessThumbnails(episodes)
    return episodes

  @CheckServerValid
  def VideoLibrary_GetRecentlyAddedMovies(self):
    params = {'properties':['title',
                            'thumbnail']}
    recentMovies = self.server.VideoLibrary.GetRecentlyAddedMovies(params)

    try:
      movies = recentMovies['movies']
    except KeyError:
      movies = []
    else:
      self.ProcessThumbnails(movies)

    return movies

  @CheckServerValid
  def VideoLibrary_GetRecentlyAddedMusicVideos(self):
    raise NotImplementedError

  @CheckServerValid
  def VideoLibrary_GetSeasonDetails(self, season_id):
    raise NotImplementedError

  @CheckServerValid
  def VideoLibrary_GetSeasons(self, show_id):
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

    response = self.server.VideoLibrary.GetSeasons(params)
    seasons = response['seasons']
    self.ProcessThumbnails(seasons)
    self.GetResumePercent(seasons)
    return seasons

  @CheckServerValid
  def VideoLibrary_GetTVShowDetails(self, show_id):
    params = {'tvshowid':int(show_id),
              'properties':['title',
                            'thumbnail',
                            'plot']}
    response = self.server.VideoLibrary.GetTVShowDetails(params)
    tvshowdetails = response['tvshowdetails']
    self.ProcessThumbnails((tvshowdetails, ))
    return tvshowdetails

  @CheckServerValid
  def VideoLibrary_GetTVShows(self):
    params = {'properties':['title',
                            'thumbnail',
                            'episode',
                            'watchedepisodes']}
    response = self.server.VideoLibrary.GetTVShows(params)
    tvshows = response['tvshows']
    self.ProcessThumbnails(tvshows)
    self.GetResumePercent(tvshows)
    return tvshows

  @CheckServerValid
  def VideoLibrary_RemoveEpisode(self, episode_id):
    params = {'episodeid':int(episode_id)}
    response = self.server.VideoLibrary.RemoveEpisode(params)

  @CheckServerValid
  def VideoLibrary_RemoveMovie(self, movie_id):
    params = {'movieid':int(movie_id)}
    response = self.server.VideoLibrary.RemoveMovie(params)

  @CheckServerValid
  def VideoLibrary_RemoveMusicVideo(self):
    raise NotImplementedError

  @CheckServerValid
  def VideoLibrary_RemoveTVShow(self, show_id):
    params = {'tvshowid':int(show_id)}
    response = self.server.VideoLibrary.RemoveTVShow(params)

  @CheckServerValid
  def VideoLibrary_Scan(self, show_dialog=False):
    params = {'showdialogs':show_dialog}
    response = self.server.VideoLibrary.Scan(params)

  @CheckServerValid
  def VideoLibrary_SetEpisodeDetails(self, episode_id, playcount=None):
    params = {'episodeid':int(episode_id)}

    if playcount is not None:
      params.update({'playcount' : playcount})

    response = self.server.VideoLibrary.SetEpisodeDetails(params)

  @CheckServerValid
  def VideoLibrary_SetMovieDetails(self, movie_id, playcount=None):
    params = {'movieid':int(movie_id)}

    if playcount is not None:
      params.update({'playcount' : playcount})

    response = self.server.VideoLibrary.SetMovieDetails(params)

  @CheckServerValid
  def VideoLibrary_SetMovieSetDetails(self):
    raise NotImplementedError

  @CheckServerValid
  def VideoLibrary_SetMusicVideoDetails(self):
    raise NotImplementedError

  @CheckServerValid
  def VideoLibrary_SetSeasonDetails(self):
    raise NotImplementedError

  @CheckServerValid
  def VideoLibrary_SetTVShowDetails(self):
    raise NotImplementedError

  #################################################
  # Player
  #################################################
  @GetActivePlayer
  def Player_GetItem(self, player_id):
    params = {"playerid": player_id,
              'properties':['title',
                            'showtitle',
                            'thumbnail',
                            'tvshowid',
                            'episode',
                            'season',
                            'uniqueid',
                            'file']}
    response = self.server.Player.GetItem(params)

    item = response['item']
    self.ProcessThumbnails((item, ))
    return item

  @CheckServerValid
  def Player_GetPlayers(self):
    params = {"media": "video"}
    response = self.server.Player.GetPlayers(params)
    return response[0]['playercoreid']

  @GetActivePlayer
  def Player_GetProperties(self, player_id):
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
    return self.server.Player.GetProperties(params)

  @GetActivePlayer
  def Player_GoTo(self, player_id, index):
    params = {'playerid':int(player_id),
              'to':int(index)}
    response = self.server.Player.GoTo(params)

  @GetActivePlayer
  def Player_Move(self, player_id):
    raise NotImplementedError

  @GetPlaylists
  def Player_Open(self, playlist_id):
    params = {"item" : {"playlistid" : int(playlist_id)}}
    return self.server.Player.Open(params)

  @GetActivePlayer
  def Player_PlayPause(self, player_id):
    response = self.server.Player.PlayPause({"playerid":player_id})
    return response['speed']

  @GetActivePlayer
  def Player_Rotate(self, player_id):
    raise NotImplementedError

  @GetActivePlayer
  def Player_Seek(self, player_id, position):
    params = {"playerid": player_id}
    params['value'] = {'percentage': float(position)}
    response = self.server.Player.Seek(params)

  @GetActivePlayer
  def Player_SetAudioStream(self, player_id):
    raise NotImplementedError

  @GetActivePlayer
  def Player_SetPartymode(self, player_id):
    raise NotImplementedError

  @GetActivePlayer
  def Player_SetRepeat(self, player_id):
    raise NotImplementedError

  @GetActivePlayer
  def Player_SetShuffle(self, player_id):
    raise NotImplementedError

  @GetActivePlayer
  def Player_SetSpeed(self, player_id, speed):
    params = {"playerid": player_id,
              "speed": speed}
    response = self.server.Player.SetSpeed(params)

  @GetActivePlayer
  def Player_SetSubtitle(self, player_id, mode):
    # mode can be: on, off, next, previous
    params = {"playerid": player_id,
              "subtitle": mode}
    response = self.server.Player.SetSubtitle(params)

  @GetActivePlayer
  def Player_Stop(self, player_id):
    response = self.server.Player.Stop({"playerid":player_id})

  @GetActivePlayer
  def Player_Zoom(self, player_id):
    raise NotImplementedError

  #################################################
  # Playerlist
  #################################################
  @GetPlaylists
  def Playlist_Add(self, playlist_id, params):
    params.update({'playlistid':int(playlist_id)})
    response = self.server.Playlist.Add(params)

  @GetPlaylists
  def Playlist_Clear(self, playlist_id):
    params = {'playlistid':int(playlist_id)}
    response = self.server.Playlist.Clear(params)

  @GetPlaylists
  def Playlist_GetItems(self, playlist_id):
    params = {'playlistid':int(playlist_id),
              'properties':['title',
                            'showtitle',
                            'thumbnail',
                            'tvshowid',
                            'episode',
                            'season',
                            'uniqueid',
                            'file']}

    response = self.server.Playlist.GetItems(params)

    try:
      episodes = response['items']
    except KeyError:
      episodes = []
    else:
      self.ProcessThumbnails(episodes)

    return episodes

  @CheckServerValid
  def Playlist_GetProperties(self):
    raise NotImplementedError

  @CheckServerValid
  def Playlist_Insert(self):
    raise NotImplementedError

  @GetPlaylists
  def Playlist_Remove(self, playlist_id, index):
    params = {'playlistid':int(playlist_id),
              'position':int(index)}
    response = self.server.Playlist.Remove(params)

  @CheckServerValid
  def Playlist_Swap(self):
    raise NotImplementedError

  #################################################
  # Files
  #################################################
  def Files_GetDirectory(self, directory):
    params = {'directory': directory}
    response = self.server.Files.GetDirectory(params)
    try:
      files = response['files']
    except KeyError:
      files = []
    return files

  def Files_GetFileDetails(self, file, media='video'):
    params = {'file': file,
              'media': media,
              'properties': ["title",
                             "artist",
                             "albumartist",
                             "genre",
                             "year",
                             "rating",
                             "album",
                             "track",
                             "duration",
                             "comment",
                             "lyrics",
                             "musicbrainztrackid",
                             "musicbrainzartistid",
                             "musicbrainzalbumid",
                             "musicbrainzalbumartistid",
                             "playcount",
                             "fanart",
                             "director",
                             "trailer",
                             "tagline",
                             "plot",
                             "plotoutline",
                             "originaltitle",
                             "lastplayed",
                             "writer",
                             "studio",
                             "mpaa",
                             "cast",
                             "country",
                             "imdbnumber",
                             "premiered",
                             "productioncode",
                             "runtime",
                             "set",
                             "showlink",
                             "streamdetails",
                             "top250",
                             "votes",
                             "firstaired",
                             "season",
                             "episode",
                             "showtitle",
                             "thumbnail",
                             "file",
                             "resume",
                             "artistid",
                             "albumid",
                             "tvshowid",
                             "setid",
                             "watchedepisodes",
                             "disc",
                             "tag",
                             "art",
                             "genreid",
                             "displayartist",
                             "albumartistid",
                             "description",
                             "theme",
                             "mood",
                             "style",
                             "albumlabel",
                             "sorttitle",
                             "episodeguide",
                             "uniqueid",
                             "dateadded",
                             "size",
                             "lastmodified",
                             "mimetype",
                             "specialsortseason",
                             "specialsortepisode"]}
    response = self.server.Files.GetFileDetails(params)
    try:
      file_details = response['filedetails']
    except KeyError:
      file_details = []
    return file_details

  def Files_GetSources(self, media):
    params = {'media': media}
    response = self.server.Files.GetSources(params)
    try:
      sources = response['sources']
    except KeyError:
      sources = []
    return sources

  def Files_PrepareDownload(self):
    raise NotImplementedError

  #################################################
  # Addons
  #################################################
  # Executes the given addon with the given parameters (if possible)
  def Addons_ExecuteAddon(self, addonid):
    params = {'addonid': addonid}
    response = self.server.Addons.ExecuteAddon(params)
    return response

  # Gets the details of a specific addon
  def Addons_GetAddonDetails(self, addonid):
    params = {'addonid': addonid,
              'properties': ["name",
                             "version",
                             "summary",
                             "description",
                             "path",
                             "author",
                             "thumbnail",
                             "disclaimer",
                             "fanart",
                             "dependencies",
                             "broken",
                             "extrainfo",
                             "rating",
                             "enabled"]}
    response = self.server.Addons.GetAddonDetails(params)
    try:
      addon = response['addon']
    except KeyError:
      addon = []
    else:
      self.ProcessThumbnails((addon, ))
    return addon

  # Gets all available addons
  def Addons_GetAddons(self, addontype='unknown', addoncontent='unknown'):
    params = {'type': addontype,
              'content': addoncontent}
    response = self.server.Addons.GetAddons(params)
    try:
      addons = response['addons']
    except KeyError:
      addons = []
    return addons

  # Enables/Disables a specific addon
  def Addons_SetAddonEnabled(self):
    raise NotImplementedError

  #################################################
  # Favourites
  #################################################
  @CheckServerValid
  def Favourites_AddFavourite(self):
    raise NotImplementedError

  @CheckServerValid
  def Favourites_GetFavourites(self):
    params = {'properties': ["path",
                             "thumbnail",
                             "window",
                             "windowparameter"]}
    response = self.server.Favourites.GetFavourites(params)

    try:
      favourites = response['favourites']
    except KeyError:
      favourites = []
    else:
      self.ProcessThumbnails(favourites)

    return favourites


  #################################################
  # Application
  #################################################
  @CheckServerValid
  def Application_GetProperties(self):
    params = {"properties": ["volume", "muted"]}
    response = self.server.Application.GetProperties(params)
    return response

  @CheckServerValid
  def Application_Quit(self):
    response = self.server.Application.Quit()

  @CheckServerValid
  def Application_SetMute(self):
    params = {"mute": "toggle"}
    response = self.server.Application.SetMute(params)

  @CheckServerValid
  def Application_SetVolume(self, volume):
    params = {"volume": int(volume)}
    response = self.server.Application.SetVolume(params)

  #################################################
  # System
  #################################################
  @CheckServerValid
  def System_EjectOpticalDrive(self):
    raise NotImplementedError

  @CheckServerValid
  def System_GetProperties(self):
    raise NotImplementedError

  @CheckServerValid
  def System_Hibernate(self):
    response = self.server.System.Hibernate()

  @CheckServerValid
  def System_Reboot(self):
    response = self.server.System.Reboot()

  @CheckServerValid
  def System_Shutdown(self):
    response = self.server.System.Shutdown()

  @CheckServerValid
  def System_Suspend(self):
    response = self.server.System.Suspend()
