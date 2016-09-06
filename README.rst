kodicontroller
==================

This package provides an array of functions which can be used to
control a Kodi instance.

For full details of exactly what functions are available, the necessary parameters
which must be provided to those functions and exactly what the subsequent processing
of the response is please refer to the source code directly.

*Note: This is a work in progress and not all Kodi JSON methods are implemented.*

Example
-------
This is an example of the GetMovies method given a kodi server at 192.168.0.1,
using port 8000 (username='user1', password='pwd'):

.. code:: python

    controller = kodicontroller.KodiController()
    controller.SetServer('192.168.0.1', '8000', 'user1', 'pwd')
    controller.VideoLibrary_GetMovies()

This will setup the Kodi JSON client given the provided server details and call
the VideoLibrary.GetMovies JSON method with the following parameters:

.. code:: python

  params = {'properties':['title',
                          'lastplayed',
                          'thumbnail',
                          'plot',
                          'playcount',
                          'resume',
                          'file']}
  movies = server.VideoLibrary.GetMovies(params)

The response will then be parsed to extract an appropriate resume percentage and
it will also download and (optionally) locally cache any thumbnails.

Requirements
---------------
This is a python package and requires the following:

- Python 3.4+
- Python kodijsonrpc package

And of course to have a purpose a Kodi instance is required:

- Kodi v13 or later

Installation
---------------
Install using pip:

.. code-block:: bash

    $ pip install kodicontroller

Requests, Issues, Bugs or Suggestions
---------------------------------------------
Add any feature requests, issues, bugs or suggestions here: https://github.com/davgeo/kodicontroller/issues

Please give as much detail as possible.
