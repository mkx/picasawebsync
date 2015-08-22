class AlbumEntry:
    def __init__(self, fileName, albumName):
        self.paths = [fileName]
        self.rootPath = fileName
        self.albumName = albumName
        self.entries = {}
        self.webAlbum = []
        self.webAlbumIndex = 0
        self.earliestDate = None

    def considerEarliestDate(self, exif):
        if exif is not None and exif.time is not None \
           and noupdatealbummetadata is False:
            date = exif.time.text
            if self.earliestDate is None or date < self.earliestDate:
                self.earliestDate = date

    def writeDate(self):
        if self.earliestDate is not None and \
           noupdatealbummetadata is False:
            if verbose:
                print "Attempting to write date (" + self.earliestDate + ") to album " + self.albumName
            for a in self.webAlbum:
                album = a.getEditObject()
                album.timestamp = gdata.photos.Timestamp(text=self.earliestDate)
                edit_link = album.GetEditLink()
                if edit_link is None:
                    print "Warning: Null edit link from " + a.albumTitle + " so skipping metadata update"
                else:
                    repeat
                    (
                        lambda:
                        gd_client.Put
                        (
                            album,
                            edit_link.href,
                            converter=gdata.photos.AlbumEntryFromString
                        ),
                        "Update album metadata for " + a.albumTitle,
                        False
                    )
        else:
            print "Not Attempting to write date to album " + self.albumName

    def __str__(self):
        return (
            self.getAlbumName() + " under " + self.rootPath + " " +
            str(len(self.entries)) + " entries " +
            ["exists", "doesn't exist"][not self.webAlbum] +
            " online")

    def getAlbumName(self):
        return self.albumName

    def getPathsAsString(self):
        return ",".join(self.paths)

    def suggestNewRoot(self, name):
        for path in self.paths:
            if name.startswith(path):
                return path
        self.paths.append(name)
        return name


