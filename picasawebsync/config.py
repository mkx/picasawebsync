import os.path
from gdata.photos.service import *
import httplib2


class Config:

    def __init__(self):
        from oauth2client.file import Storage

        filename = os.path.join(os.path.expanduser('~'), ".picasawebsync")
        storage = Storage(filename)
        self.credentials = storage.get()
    
    def refreshLogin(self):
        # using http://stackoverflow.com/questions/20248555/
        # list-of-spreadsheets-gdata-oauth2/29157967#29157967 (thanks)

        if self.credentials is None or self.credentials.invalid:
            flow = client.flow_from_clientsecrets(
                'client_secrets.json',
                scope='https://picasaweb.google.com/data/',
                redirect_uri='urn:ietf:wg:oauth:2.0:oob'
            )
            auth_uri = flow.step1_get_authorize_url()
            print 'Authorization URL: %s' % auth_uri
            auth_code = raw_input('Enter the auth code: ')
            self.credentials = flow.step2_exchange(auth_code)
            storage.put(self.credentials)

        if self.credentials.access_token_expired:
            self.credentials.refresh(httplib2.Http())

        self.gd_client = gdata.photos.service.PhotosService(
            email='default',
            additional_headers={
                'Authorization': 'Bearer %s' % self.credentials.access_token
            }
        )

    def getGdClient(self):
        if self.gd_client is None or \
           self.credentials is None or self.credentials.invalid or \
           self.credentials.access_token_expired:
            self.refreshLogin()

        return self.gd_client


# Upload video code came form http://nathanvangheem.com/news/moving-to-picasa-update
class VideoEntry(gdata.photos.PhotoEntry):
    pass

gdata.photos.VideoEntry = VideoEntry


def InsertVideo(self, album_or_uri, video, filename_or_handle, content_type='image/jpeg'):
    """Copy of InsertPhoto which removes protections since it *should* work"""
    try:
        assert (isinstance(video, VideoEntry))
    except AssertionError:
        raise GooglePhotosException({'status': GPHOTOS_INVALID_ARGUMENT,
                                     'body': '`video` must be a gdata.photos.VideoEntry instance',
                                     'reason': 'Found %s, not PhotoEntry' % type(video)
                                     })
    try:
        majtype, mintype = content_type.split('/')
    # assert(mintype in SUPPORTED_UPLOAD_TYPES)
    except (ValueError, AssertionError):
        raise GooglePhotosException({'status': GPHOTOS_INVALID_CONTENT_TYPE,
                                     'body': 'This is not a valid content type: %s' % content_type,
                                     'reason': 'Accepted content types:'
                                     })
    if isinstance(filename_or_handle, (str, unicode)) and \
            os.path.exists(filename_or_handle):  # it's a file name
        mediasource = gdata.MediaSource()
        mediasource.setFile(filename_or_handle, content_type)
    elif hasattr(filename_or_handle, 'read'):  # it's a file-like resource
        if hasattr(filename_or_handle, 'seek'):
            filename_or_handle.seek(0)  # rewind pointer to the start of the file
        # gdata.MediaSource needs the content length, so read the whole image
        file_handle = StringIO.StringIO(filename_or_handle.read())
        name = 'image'
        if hasattr(filename_or_handle, 'name'):
            name = filename_or_handle.name
        mediasource = gdata.MediaSource(file_handle, content_type,
                                        content_length=file_handle.len, file_name=name)
    else:  # filename_or_handle is not valid
        raise GooglePhotosException
        (
            {
                'status': GPHOTOS_INVALID_ARGUMENT,
                'body': '`filename_or_handle` must be a path name or a file-like object',
                'reason': 'Found %s, not path name or object with a .read() method' %
                type(filename_or_handle)
            }
        )

    if isinstance(album_or_uri, (str, unicode)):  # it's a uri
        feed_uri = album_or_uri
    elif hasattr(album_or_uri, 'GetFeedLink'):  # it's a AlbumFeed object
        feed_uri = album_or_uri.GetFeedLink().href

    try:
        return self.Post(video, uri=feed_uri, media_source=mediasource,
                         converter=None)
    except gdata.service.RequestError, e:
        raise GooglePhotosException(e.args[0])


gdata.photos.service.PhotosService.InsertVideo = InsertVideo
