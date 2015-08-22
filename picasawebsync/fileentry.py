# Class to store details of an individual file


import os.path
import calendar
import time
import re
import urllib
import mimetypes
import hashlib


from consts import Comparisons, supportedImageFormats, supportedVideoFormats


class FileEntry:
    def __init__(self, config, name, path, webReference, isLocal, album):
        self.config = config
        self.name = name
        if path:
            self.path = path
            self.type = mimetypes.guess_type(path)[0]
        else:
            self.path = os.path.join(album.rootPath, name)
            self.type = None
        self.isLocal = isLocal
        self.localHash = None
        self.remoteHash = None
        self.remoteDate = None
        self.remoteTimestamp = None
        self.remoteSize = None
        self.album = album
        self.setWebReference(webReference)

    def setWebReference(self, webReference):
        if webReference:
            for content in webReference.media.content:
                # If we haven't found a type yet, or prioritise video type
                if not self.type or (content.medium == 'video'):
                    self.type = content.type

            self.gphoto_id = webReference.gphoto_id.text
            self.albumid = webReference.albumid.text
            self.webUrl = webReference.content.src
            self.remoteHash = webReference.checksum.text
            self.remoteDate = calendar.timegm(
                time.strptime(re.sub("\.[0-9]{3}Z$", ".000 UTC", webReference.updated.text),
                              '%Y-%m-%dT%H:%M:%S.000 %Z'))
            self.remoteTimestamp = time.mktime(webReference.timestamp.datetime().timetuple())
            self.remoteSize = int(webReference.size.text)
        else:
            self.webUrl = None

    def getEditObject(self):
        if self.gphoto_id:
            photo = self.config.getGdClient().GetFeed(
                '/data/feed/api/user/%s/albumid/%s/photoid/%s' % ("default", self.albumid, self.gphoto_id))
            return photo
        return None

    def getFullName(self):
        return self.album.getAlbumName() + " " + self.name

    def getLocalHash(self):
        if not (self.localHash):
            md5 = hashlib.md5()
            with open(self.path, 'rb') as f:
                for chunk in iter(lambda: f.read(128 * md5.block_size), b''):
                    md5.update(chunk)
            self.localHash = md5.hexdigest()
        return self.localHash

    def getLocalDate(self):
        return os.path.getmtime(self.path)

    def getLocalSize(self):
        return os.path.getsize(self.path)

    def changed(self, compareattributes):
        if self.isLocal:
            if self.isWeb():
                # filesize (2), date (1),  hash (4)
                if compareattributes & 1:
                    # print "%s: remote=%s and local=%s" % (self.getFullName(), time.gmtime(self.remoteDate), time.gmtime(self.getLocalDate()))
                    if self.remoteDate < self.getLocalDate() + 60:
                        return Comparisons.REMOTE_OLDER
                if compareattributes & 2:
                    if self.config.verbose:
                        print "%s: remote size=%s and local=%s" % (
                            self.getFullName(), self.remoteSize, self.getLocalSize())
                    if self.remoteSize != self.getLocalSize():
                        return Comparisons.DIFFERENT
                if compareattributes & 4:
                    if self.remoteHash:
                        if self.remoteHash != self.getLocalHash():
                            return Comparisons.DIFFERENT
                    else:
                        return Comparisons.UNKNOWN
                return Comparisons.SAME
            else:
                return Comparisons.LOCAL_ONLY
        else:
            return Comparisons.REMOTE_ONLY

    def isWeb(self):
        return self.webUrl is not None

    # UPLOAD_LOCAL', 'DELETE_LOCAL', 'SILENT', 'REPORT', 'DOWNLOAD_REMOTE', 'DELETE_REMOTE', 'TAG_REMOTE', 'REPLACE_REMOTE_WITH_LOCAL', 'UPDATE_REMOTE_METADATA'
    def delete_local(self, event):
        os.remove(self.path)

    def silent(self, event):
        None

    def report(self, event):
        print ("Identified %s as %s - taking no action" % (self.name, event))

    def tag_remote(self, event):
        print ("Not implemented tag")

    def replace_remote_with_local(self, event):
        self.delete_remote(event)
        self.upload_local(event)

    def update_remote_metadata(self, event):
        entry = self.config.getGdClient().GetEntry(self.getEditObject().GetEditLink().href)
        self.album.considerEarliestDate(entry.exif)
        self.addMetadata(entry)
        self.setWebReference(self.config.getGdClient().UpdatePhotoMetadata(entry))

    def download_remote(self, event):
        if self.type not in self.config.chosenFormats:
            print ("Skipped %s (because can't download file of type %s)." % (self.path, self.type))
        elif dateLimit is not None and self.remoteTimestamp < dateLimit:
            print ("Skipped %s (because remote album pre %s)." % (self.path, time.asctime(dateLimit)))
        else:
            url = self.webUrl
            path = os.path.split(self.path)[0]
            if not os.path.exists(path):
                os.makedirs(path)
            urllib.urlretrieve(url, self.path)
            os.utime(path, (int(self.remoteDate), int(self.remoteDate)))

    def delete_remote(self, event):
        self.config.getGdClient().Delete(self.getEditObject())
        print ("Deleted %s" % self.getFullName())

    def upload_local(self, event):
        if self.type in self.config.chosenFormats:
            while self.album.webAlbumIndex < len(self.album.webAlbum) and \
                  self.album.webAlbum[self.album.webAlbumIndex].numberFiles >= 999:
                self.album.webAlbumIndex = self.album.webAlbumIndex + 1
            if self.album.webAlbumIndex >= len(self.album.webAlbum):
                googleWebAlbum = self.config.getGdClient().InsertAlbum(
                    title=Albums.createAlbumName(
                        self.album.getAlbumName(),
                        self.album.webAlbumIndex
                    ),
                    access='private',
                    summary='synced from ' + self.album.rootPath +
                    ' using picasawebsync'
                )
                subAlbum = WebAlbum(googleWebAlbum, 0)
                self.album.webAlbum.append(subAlbum)
                if self.config.verbose:
                    print ('Created album %s to sync %s' %
                    (
                        subAlbum.albumTitle,
                        self.album.rootPath
                    ))
            else:
                subAlbum = self.album.webAlbum[self.album.webAlbumIndex]
            if self.type in supportedImageFormats:
                photo = self.upload_local_img(subAlbum)
            if self.type in supportedVideoFormats:
                if self.getLocalSize() > 1073741824:
                    print
                    (
                        "Not uploading %s because it exceeds maximum file "
                        "size" % self.path
                    )
                else:
                    photo = self.upload_local_video(subAlbum)
        else:
            print
            (
                "Skipped %s (because can't upload file of type %s)."
                % (self.path, self.type)
            )

    def upload_local_img(self, subAlbum):
        name = urllib.quote(self.name, '')
        metadata = gdata.photos.PhotoEntry()
        # have to quote as certain charecters, e.g. / seem to break it
        metadata.title = atom.Title(text=name)
        self.addMetadata(metadata)
        currentFile = self.path
        photo = self.config.getGdClient().InsertPhoto
        (
            subAlbum.albumUri,
            metadata,
            currentFile,
            self.type
        )
        self.album.considerEarliestDate(photo.exif)
        subAlbum.numberFiles = subAlbum.numberFiles + 1
        return photo

    def upload_local_video(self, subAlbum):
        name = urllib.quote(self.name, '')
        metadata = gdata.photos.VideoEntry()
        # have to quote as certain charecters, e.g. / seem to break it
        metadata.title = atom.Title(text=name)
        self.addMetadata(metadata)
        photo = self.config.getGdClient().InsertVideo
        (
            subAlbum.albumUri,
            metadata,
            self.path,
            self.type
        )
        subAlbum.numberFiles = subAlbum.numberFiles + 1
        return photo

    def addMetadata(self, metadata):
        metadata.summary = atom.Summary(text=os.path.relpath
            (
                self.path, self.album.rootPath
            ),
            summary_type='text'
        )
        metadata.checksum = gdata.photos.Checksum(text=self.getLocalHash())
        if self.config.verbose and (metadata is None):
            print "Warning: " + self.name + " does not have a date set"
