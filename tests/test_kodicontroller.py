#!/usr/bin/env python3

'''

Testbench for kodicontroller

This uses an actual Kodi instance to test the client functionality.

Either edit the server info below or add a seperate
server_info.py with the required details.

'''

import os
import shutil
import random
import string

import kodicontroller

import unittest

try:
  from server_info import *
except ImportError:
  # EDIT SERVER INFO #

  TEST_SERVER   = '192.168.0.1'
  TEST_PORT     = '8080'
  TEST_USERNAME = 'kodiuser'
  TEST_PASSWORD = 'kodipwd'

  # --------------- #

ENABLE_PRINT_DEBUG = False
ENABLE_JSON_LOGGING = False

class TestKodiController(unittest.TestCase):
  # Set up test infrastructure
  @classmethod
  def setUpClass(cls):
    cls.controller = kodicontroller.KodiController()
    cls.controller.SetServer(TEST_SERVER, TEST_PORT, TEST_USERNAME, TEST_PASSWORD)

    if ENABLE_JSON_LOGGING:
      cls.controller.EnableLogging()

    randomString = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(10))
    cls.cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache_{}'.format(randomString))

  # Tear down test infrastructure
  @classmethod
  def tearDownClass(cls):
    if os.path.isdir(cls.cache_dir):
      shutil.rmtree(cls.cache_dir)

  def do_print(self, message):
    if ENABLE_PRINT_DEBUG:
      print(message)

  # Check server is online
  def test_ping_server(self):
    response = self.controller.Status()
    self.assertEqual(response, 'Online')

  # Check with and without cache dir set
  def test_cache_dir(self):
    self.controller.VideoLibrary_GetMovies()
    self.controller.SetThumbnailCache(self.cache_dir)
    self.controller.VideoLibrary_GetMovies()

  # Check resume percentage function (using GetTVShows)
  def test_resume_percentage(self):
    self.controller.VideoLibrary_GetTVShows()

  # Check Player.GetItem method
  def test_get_playing(self):
    self.controller.Player_GetItem()

  # Check File info
  def test_files(self):
    media_list = ['video', 'music', 'pictures', 'files', 'programs']
    for media in media_list:
      self.do_print("\nFile sources for media {} are:\n".format(media))
      sources = self.controller.Files_GetSources(media)
      for source in sources:
        self.do_print("{} : {}".format(source['label'], source['file']))
        files = self.controller.Files_GetDirectory(source['file'])
        for file in files:
          self.do_print("File Info: {}".format(file))
          if file['filetype'] == 'file':
            details = self.controller.Files_GetFileDetails(file['file'])
            self.do_print("File Details: {}".format(details))

  # Check Addon info
  def test_addons(self):
    self.controller.SetThumbnailCache(self.cache_dir)
    addons = self.controller.Addons_GetAddons(addoncontent='video')
    for addon in addons:
      self.do_print("\nAddon: {}".format(addon))
      details = self.controller.Addons_GetAddonDetails(addon['addonid'])
      self.do_print("\nAddon Details: {}".format(details))
      self.controller.EnableLogging()
      addon_dir = "plugin://{}".format(details['addonid'])
      self.controller.Files_GetDirectory(addon_dir)

if __name__ == '__main__':
  unittest.main()
