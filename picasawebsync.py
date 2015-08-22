#!/usr/bin/python

import re
import argparse
import mimetypes
import hashlib
import time
import urllib
import fnmatch
import tempfile
import calendar
import httplib2

# from apiclient import discovery
from oauth2client import client
from subprocess import call

from gdata.photos.service import *
import gdata.media
import gdata.geo
import Image

from picasawebsync.albums import *


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





# Method to translate directory name to an album name
def convertDirToAlbum(formElements, root, name, replace, namingextract):
    if root == name:
        return "Home"
    nameElements = re.split("/", re.sub("^/", "", name[len(root):]))
    which = min(len(formElements), len(nameElements))
    work = formElements[which - 1].format(*nameElements)
    # apply naming extraction if provided
    if namingextract:
        nePattern = namingextract.split('|')
        work = re.sub(nePattern[0], nePattern[1], work)

    # apply replacement pattern if provided
    if replace:
        rePattern = replace.split('|')
        work = re.sub(rePattern[0], rePattern[1], work)

    return work


supportedImageFormats = frozenset(
    [
        "image/bmp",
        "image/gif",
        "image/jpeg",
        "image/png"
    ]
)

supportedVideoFormats = frozenset(
    [
        "video/3gpp",
        "video/avi",
        "video/quicktime",
        "video/mp4",
        "video/mpeg",
        "video/mpeg4",
        "video/msvideo",
        "video/x-ms-asf",
        "video/x-ms-wmv",
        "video/x-msvideo"
    ]
)


class Enum(set):
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError


Comparisons = Enum(
    [
        'REMOTE_OLDER',
        'DIFFERENT',
        'SAME',
        'UNKNOWN',
        'LOCAL_ONLY',
        'REMOTE_ONLY'
    ]
)

Actions = Enum(
    [
        'UPLOAD_LOCAL',
        'DELETE_LOCAL',
        'SILENT',
        'REPORT',
        'DOWNLOAD_REMOTE',
        'DELETE_REMOTE',
        'TAG_REMOTE',
        'REPLACE_REMOTE_WITH_LOCAL',
        'UPDATE_REMOTE_METADATA'
    ]
)

UploadOnlyActions = {
    Comparisons.REMOTE_OLDER: Actions.REPLACE_REMOTE_WITH_LOCAL,
    Comparisons.DIFFERENT: Actions.REPORT,
    Comparisons.SAME: Actions.SILENT,
    Comparisons.UNKNOWN: Actions.REPORT,
    Comparisons.LOCAL_ONLY: Actions.UPLOAD_LOCAL,
    Comparisons.REMOTE_ONLY: Actions.REPORT}
DownloadOnlyActions = {
    Comparisons.REMOTE_OLDER: Actions.REPORT,
    Comparisons.DIFFERENT: Actions.DOWNLOAD_REMOTE,
    Comparisons.SAME: Actions.SILENT,
    Comparisons.UNKNOWN: Actions.REPORT,
    Comparisons.LOCAL_ONLY: Actions.REPORT,
    Comparisons.REMOTE_ONLY: Actions.DOWNLOAD_REMOTE}
PassiveActions = {
    Comparisons.REMOTE_OLDER: Actions.REPORT,
    Comparisons.DIFFERENT: Actions.REPORT,
    Comparisons.SAME: Actions.SILENT,
    Comparisons.UNKNOWN: Actions.REPORT,
    Comparisons.LOCAL_ONLY: Actions.REPORT,
    Comparisons.REMOTE_ONLY: Actions.REPORT}
RepairActions = {
    Comparisons.REMOTE_OLDER: Actions.REPLACE_REMOTE_WITH_LOCAL,
    Comparisons.DIFFERENT: Actions.REPLACE_REMOTE_WITH_LOCAL,
    Comparisons.SAME: Actions.SILENT,
    Comparisons.UNKNOWN: Actions.UPDATE_REMOTE_METADATA,
    Comparisons.LOCAL_ONLY: Actions.UPLOAD_LOCAL,
    Comparisons.REMOTE_ONLY: Actions.DELETE_REMOTE}
SyncActions = {
    Comparisons.REMOTE_OLDER: Actions.REPLACE_REMOTE_WITH_LOCAL,
    Comparisons.DIFFERENT: Actions.REPORT,
    Comparisons.SAME: Actions.SILENT,
    Comparisons.UNKNOWN: Actions.REPORT,
    Comparisons.LOCAL_ONLY: Actions.UPLOAD_LOCAL,
    Comparisons.REMOTE_ONLY: Actions.DOWNLOAD_REMOTE}
SyncUploadActions = {
    Comparisons.REMOTE_OLDER: Actions.REPLACE_REMOTE_WITH_LOCAL,
    Comparisons.DIFFERENT: Actions.REPLACE_REMOTE_WITH_LOCAL,
    Comparisons.SAME: Actions.SILENT,
    Comparisons.UNKNOWN: Actions.REPLACE_REMOTE_WITH_LOCAL,
    Comparisons.LOCAL_ONLY: Actions.UPLOAD_LOCAL,
    Comparisons.REMOTE_ONLY: Actions.DELETE_REMOTE}

modes={
    'upload': UploadOnlyActions,
    'download': DownloadOnlyActions,
    'report': PassiveActions,
    'repairUpload': RepairActions,
    'sync': SyncActions,
    'syncUpload': SyncUploadActions
}

formats={
    'photo': supportedImageFormats,
    'video': supportedVideoFormats,
    'both': supportedImageFormats.union(supportedVideoFormats)
}

allowDeleteOptions={
    'neither': (False, False),
    'both': (True, True),
    'local': (True, False),
    'remote': (False, True)
}


def convertAllowDelete(string):
    return allowDeleteOptions[string]


def convertMode(string):
    return modes[string]


def convertFormat(string):
    return formats[string]


def convertDate(string):
    return time.strptime(string, '%Y-%m-%d')


def repeat(function,  description, onFailRethrow):
    exc_info = None
    for attempt in range(3):
        try:
            if verbose and (attempt > 0):
                print ("Trying %s attempt %s" % (description, attempt))
            return function()
        except Exception,  e:
            if exc_info is None:
                exc_info = e
                # FIXME - to try and stop 403 token expired
                time.sleep(6)
                continue
            else:
                break
        else:
            print
            (
                "WARNING: Failed to %s. This was due to %s" %
                (description, exc_info)
            )
            if onFailRethrow:
                raise exc_info


def oauthLogin():
    # using http://stackoverflow.com/questions/20248555/
    # list-of-spreadsheets-gdata-oauth2/29157967#29157967 (thanks)
    from oauth2client.file import Storage

    filename = os.path.join(os.path.expanduser('~'), ".picasawebsync")
    storage = Storage(filename)
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        flow = client.flow_from_clientsecrets(
            'client_secrets.json',
            scope='https://picasaweb.google.com/data/',
            redirect_uri='urn:ietf:wg:oauth:2.0:oob'
        )
        auth_uri = flow.step1_get_authorize_url()
        print 'Authorization URL: %s' % auth_uri
        auth_code = raw_input('Enter the auth code: ')
        credentials = flow.step2_exchange(auth_code)
        storage.put(credentials)
    if credentials.access_token_expired:
        credentials.refresh(httplib2.Http())

    gd_client = gdata.photos.service.PhotosService(
        email='default',
        additional_headers={
            'Authorization': 'Bearer %s' % credentials.access_token
        }
    )

    return gd_client

# start of the program

defaultNamingFormat = ["{0}", "{1} ({0})"]

parser = argparse.ArgumentParser()

parser.add_argument(
    "-d",
    "--directory",
    nargs='+',
    help="The local directories. The first of these will be used for any "
    "downloaded items"
)

parser.add_argument(
    "-n",
    "--naming",
    default=defaultNamingFormat, nargs='+',
    help="Expression to convert directory names to web album names. Formed as "
    "a ~ seperated list of substitution strings, "
    "so if a sub directory is in the root scanning directory then the first "
    "element will be used, if there is a directory between them the second, "
    "etc. If the directory path is longer than the "
    "list then the last element is used (and thus the path is flattened). "
    "Default is \"%s\"" % defaultNamingFormat
)

parser.add_argument(
    "--namingextract",
    default=False,
    help="Naming extraction rules. It applies to the name computed according "
    "to naming options."
    "Search capturing pattern is seperated by a | from formatting expression "
    "(ex: '([0-9]{4})[0-9]*-(.*)|\2 (\2)'"
)

parser.add_argument(
    "-c",
    "--compareattributes",
    type=int,
    help="set of flags to indicate whether to use date (1), filesize (2), "
    "hash (4) in addition to filename. "
    "These are applied in order from left to right with a difference "
    "returning immediately and a similarity passing on to the next check."
    "They work like chmod values, so add the values in brackets to switch on "
    "a check. Date uses a 60 second margin (to allow for different time stamp"
    "between google and your local machine, and can only identify a locally "
    "modified file not a remotely modified one. Filesize and hash are used by "
    "default",
    default=3
)

parser.add_argument(
    "-v",
    "--verbose",
    default=False,
    action='store_true',
    help="Increase verbosity"
)

parser.add_argument(
    "-t",
    "--test",
    default=False,
    action='store_true',
    help="Don't actually run activities, but report what you would have done "
    "(you may want to enable verbose)"
)

parser.add_argument(
    "-m",
    "--mode",
    type=convertMode,
    help="The mode is a preset set of actions to execute in different "
    "circumstances, e.g. upload, download, sync, etc. The full set of "
    "options is %s. "
    "The default is upload. Look at the github page for full details of what "
    "each action does" % list(modes),
    default="upload"
)

parser.add_argument(
    "-dd",
    "--deletedups",
    default=False,
    action='store_true',
    help="Delete any remote side duplicates"
)

parser.add_argument(
    "-f",
    "--format",
    type=convertFormat,
    default="photo",
    help="Upload photos, videos or both"
)

parser.add_argument(
    "-s",
    "--skip",
    nargs='*',
    default=[],
    help="Skip (local) files or folders using a list of glob expressions."
)

parser.add_argument(
    "--skipserver",
    nargs='*',
    default=[],
    help="Skip (remote) files or folders using a list of glob expressions."
)

parser.add_argument(
    "--purge",
    default=False,
    action='store_true',
    help="Purge empty web filders"
)

parser.add_argument(
    "--noupdatealbummetadata",
    default=False,
    action='store_true',
    help="Disable the updating of album metadata"
)

parser.add_argument(
    "--allowDelete",
    type=convertAllowDelete,
    default="neither",
    help="Are we allowed to do delete operations: %s" %
    list(allowDeleteOptions)
)

parser.add_argument(
    "-r",
    "--replace",
    default=False,
    help="Replacement pattern. Search string is seperated by a pipe from "
    "replace string (ex: '-| '"
)

parser.add_argument(
    "-o",
    "--owner",
    default="default",
    help="The username of the user whos albums to sync (leave blank for your "
    "own)"
)

parser.add_argument(
    "--dateLimit",
    type=convertDate,
    help="A date limit, before which albums are ignored."
)

for comparison in Comparisons:
    parser.add_argument(
        "--override:%s" % comparison,
        default=None,
        help="Override the action for %s from the list of %s" %
        (comparison, ",".join(list(Actions)))
    )

args = parser.parse_args()

chosenFormats = args.format
dateLimit = args.dateLimit

gd_client = oauthLogin()
verbose = args.verbose
rootDirs = args.directory  # set the directory you want to start from

albumNaming = args.naming
mode = args.mode
noupdatealbummetadata = args.noupdatealbummetadata
for comparison in Comparisons:
    r = getattr(args, "override:%s" % comparison, None)
    if r:
        mode[comparison] = r

excludes = r'|'.join([fnmatch.translate(x) for x in args.skip]) or r'$.'
server_excludes = \
r'|'.join([fnmatch.translate(x) for x in args.skipserver]) or r'$.'

print
(
    "Excluding %s on client and %s on server" %
    (excludes, server_excludes)
)

albums = Albums(
    rootDirs,
    albumNaming,
    excludes,
    args.replace,
    args.namingextract
)

albums.scanWebAlbums(
    args.owner,
    args.deletedups,
    server_excludes
)

albums.uploadMissingAlbumsAndFiles(
    args.compareattributes,
    mode,
    args.test,
    args.allowDelete
)

if args.purge:
    albums.deleteEmptyWebAlbums(args.owner)
