python-raumfeld
===============

A pythonic library for discovering and controlling Teufel Raumfeld
devices.

Tested with a Raumfeld One. Hardware donations to improve the library
are welcome :smile:

Supports Python >2.7, 3.x

Installation
------------

::

    pip install raumfeld

Quickstart
----------

.. code:: python

    import raumfeld

    # discovery returns a list of RaumfeldDevices
    devices = raumfeld.discover()
    if len(devices) > 0:
        speaker = devices[0]

        # now you can control your raumfeld speaker
        speaker.mute = True     # mute
        print(speaker.volume)   # print current volume
        speaker.volume = 50     # set volume

        speaker.pause()
        speaker.play()
    else:
        print('No devices found.')

