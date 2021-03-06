# coding: utf-8
"""
A pythonic library to discover and control Teufel Raumfeld speakers
"""
import socket
try:
    from urllib.parse import urlparse  # python3
except ImportError:
    from urlparse import urlparse      # python2
from pysimplesoap.client import SoapClient
from pysimplesoap.simplexml import SimpleXMLElement
from pysimplesoap.helpers import fetch
from pysimplesoap.transport import get_Http
import xml.etree.ElementTree as ET


__version__ = '0.2'
__all__ = ['discover', 'RaumfeldDevice']


def discover(timeout=1, retries=1):
    """Discover Raumfeld devices in the network

    :param timeout: The timeout in seconds
    :param retries: How often the search should be retried
    :returns: A list of raumfeld devices
    """
    locations = []

    group = ('239.255.255.250', 1900)
    service = 'ssdp:urn:schemas-upnp-org:device:MediaRenderer:1'  # 'ssdp:all'
    message = '\r\n'.join(['M-SEARCH * HTTP/1.1',
                           'HOST: {group[0]}:{group[1]}',
                           'MAN: "ssdp:discover"',
                           'ST: {st}',
                           'MX: 1', '', '']).format(group=group, st=service)

    socket.setdefaulttimeout(timeout)
    for _ in range(retries):
        sock = socket.socket(socket.AF_INET,
                             socket.SOCK_DGRAM,
                             socket.IPPROTO_UDP)
        # socket options
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

        # send group multicast
        sock.sendto(message.encode('utf-8'), group)

        while True:
            try:
                response = sock.recv(2048).decode('utf-8')
                for line in response.split('\r\n'):
                    if line.startswith('Location: '):
                        location = line.split(' ')[1].strip()
                        if not location in locations:
                            locations.append(location)
            except socket.timeout:
                break
    devices = sorted([RaumfeldDevice(location) for location in locations], key = lambda device: device.friendly_name)
    zones = [device for device in devices if device.model_description == 'Virtual Media Player']
    if(len(zones)>0):
        # only return 'Virtual Media Player'
        return zones
    else:
        # return all Renderers, useful to extract host IP, when all rooms are unassigned (after reboot or something)
        return devices


class RaumfeldDevice(object):

    def __init__(self, location):
        self.location = location

        # parse location url
        scheme, netloc, path, _, _, _ = urlparse(location)
        self.address = '%s://%s' % (scheme, netloc)

        # parse device description
        Http = get_Http()
        self.http = Http(timeout=1)
        xml = fetch(self.location, self.http)
        d = SimpleXMLElement(xml)
        self.friendly_name = unicode(next(d.device.friendlyName()))
        self.model_description = str(next(d.device.modelDescription()))
        self.model_name = str(next(d.modelName()))

        # set up soap clients
        self.rendering_control = SoapClient(
            location='%s/RenderingService/Control' % self.address,
            action='urn:upnp-org:serviceId:RenderingControl#',
            namespace='http://schemas.xmlsoap.org/soap/envelope/',
            soap_ns='soap', ns='s', exceptions=True)
        self.av_transport = SoapClient(
            location='%s/TransportService/Control' % self.address,
            action='urn:schemas-upnp-org:service:AVTransport:1#',
            namespace='http://schemas.xmlsoap.org/soap/envelope/',
            soap_ns='soap', ns='s', exceptions=True)

    def play(self):
        """Start playing"""
        self.av_transport.Play(InstanceID=1, Speed=2)

    def playURI(self, value, meta = ''):
        self.av_transport.SetAVTransportURI(InstanceID=1, CurrentURI=value, CurrentURIMetaData=meta)

    def next(self):
        """Next"""
        self.av_transport.Next(InstanceID=1)

    def previous(self):
        """Previous"""
        self.av_transport.Previous(InstanceID=1)

    def pause(self):
        """Pause"""
        self.av_transport.Pause(InstanceID=1)

    def seek(self, target, unit = 'ABS_TIME'):
        """Seek; unit = _ABS_TIME_/REL_TIME/TRACK_NR"""
        return self.av_transport.Seek(InstanceID=1, Unit = unit, Target = target)

    @property
    def volume(self):
        """get/set the current volume"""
        return self.rendering_control.GetVolume(InstanceID=1).CurrentVolume

    @volume.setter
    def volume(self, value):
        self.rendering_control.SetVolume(InstanceID=1, DesiredVolume=value)

    @property
    def mute(self):
        """get/set the current mute state"""
        response = self.rendering_control.GetMute(InstanceID=1, Channel=1)
        return response.CurrentMute == 1

    @mute.setter
    def mute(self, value):
        self.rendering_control.SetMute(InstanceID=1,
                                       DesiredMute=1 if value else 0)

    @property
    def curTransState(self):
        """Get Current Transport State"""
        return self.av_transport.GetTransportInfo(InstanceID=1).CurrentTransportState

    @property
    def currentURI(self):
        """Get CurrentURI"""
        return self.av_transport.GetMediaInfo(InstanceID=1).CurrentURI

    @property
    def currentURIMetaData(self):
        """Get CurrentURIMetaData"""
        tree = ET.fromstring(self.av_transport.GetMediaInfo(InstanceID=1).CurrentURIMetaData.as_xml())
        meta_data = tree[0][0][3].text
        return meta_data

    @property
    def trackURI(self):
        """Get TrackURI"""
        return self.av_transport.GetPositionInfo(InstanceID=1).TrackURI

    @property
    def trackMetaData(self):
        """Get TrackURIMetaData"""
        return self.av_transport.GetPositionInfo(InstanceID=1).TrackMetaData

    @property
    def trackDuration(self):
        """Get TrackDuration"""
        return self.av_transport.GetPositionInfo(InstanceID=1).TrackDuration

    @property
    def trackRelTime(self):
        """Get RelTime"""
        return self.av_transport.GetPositionInfo(InstanceID=1).RelTime

    @property
    def trackAbsTime(self):
        """Get AbsTime"""
        return self.av_transport.GetPositionInfo(InstanceID=1).AbsTime

    @property
    def track_pos_info(self):
        """Get PositionInfo"""
        pos_info = self.av_transport.GetPositionInfo(InstanceID=1)
        track = str(pos_info.Track)
        track_duration = str(pos_info.TrackDuration)
        tree = ET.fromstring(pos_info.TrackMetaData.as_xml())
        tree[0][0][2].text
        meta_data = tree[0][0][2].text
        track_uri = str(pos_info.TrackURI)
        rel_time = str(pos_info.RelTime)
        abs_time = str(pos_info.AbsTime)
        return track, track_duration, meta_data, track_uri, rel_time, abs_time

    def __repr__(self):
        return ('<RaumfeldDevice(location="{0}", name="{1}")>'
                .format(self.location, self.friendly_name))

    def __str__(self):
        return self.friendly_name


if __name__ == '__main__':
    print('Library version %s' % __version__)
    devices = discover()
    print('Devices: %s' % devices)
    if len(devices) > 0:
        device = devices.pop()
        print('Volume: %s' % device.volume)
        print('Muted: %s' % device.mute)
    else:
        print('No Raumfeld devices found!')
