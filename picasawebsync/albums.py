import os


# Class to store details of an album
class Albums:
    def __init__(self, rootDirs, albumNaming, excludes, replace, namingextract):
        self.rootDirs = rootDirs
        self.albums = self.scanFileSystem(albumNaming, excludes, replace, namingextract)

    # walk the directory tree populating the list of files we have locally
    # @print_timing
    def scanFileSystem(self, albumNaming, excludes, replace, namingextract):
        fileAlbums = {}
        for rootDir in self.rootDirs:
            for dirName, subdirList, fileList in os.walk(rootDir):
                subdirList[:] = [d for d in subdirList if not re.match(excludes, os.path.join(dirName, d))]
                albumName = convertDirToAlbum(albumNaming, rootDir, dirName, replace, namingextract)
                # have we already seen this album? If so append our path to it's list
                if albumName in fileAlbums:
                    album = fileAlbums[albumName]
                    thisRoot = album.suggestNewRoot(dirName)
                else:
                    # create a new album
                    thisRoot = dirName
                    album = AlbumEntry(dirName, albumName)
                    fileAlbums[albumName] = album
                # now iterate it's files to add them to our list
                for fname in fileList:
                    fullFilename = os.path.join(dirName, fname)
                    if not re.match(excludes, fullFilename):
                        # figure out the filename relative to the root dir of the album (to ensure uniqeness)
                        relFileName = re.sub("^/", "", fullFilename[len(thisRoot):])
                        fileEntry = FileEntry(relFileName, fullFilename, None, True, album)
                        album.entries[relFileName] = fileEntry
        #if verbose:
        #    print ("Found " + str(len(fileAlbums)) + " albums on the filesystem")
        return fileAlbums

    def deleteEmptyWebAlbums(self, owner):
        webAlbums = gd_client.GetUserFeed(user=owner)
        for webAlbum in webAlbums.entry:
            if int(webAlbum.numphotos.text) == 0:
                print "Deleting empty album %s" % webAlbum.title.text
                gd_client.Delete(webAlbum)
                # @print_timing

    def scanWebAlbums(self, owner, deletedups, server_excludes):
        # walk the web album finding albums there
        webAlbums = gd_client.GetUserFeed(user=owner)
        for webAlbum in webAlbums.entry:
            webAlbumTitle = Albums.flatten(webAlbum.title.text)
            if re.match(server_excludes, webAlbumTitle):
                if verbose:
                    print ('Skipping (because matches server exclude) web-album %s (containing %s files)' % (
                        webAlbum.title.text, webAlbum.numphotos.text))
            else:
                if verbose:
                    print (
                        'Scanning web-album %s (containing %s files)' % (webAlbum.title.text, webAlbum.numphotos.text))
                # print "Album %s is %s in %s" % (webAlbumTitle, webAlbumTitle in self.albums,	",".join(self.albums))
                if webAlbumTitle in self.albums:
                    foundAlbum = self.albums[webAlbumTitle]
                    self.scanWebPhotos(foundAlbum, webAlbum, deletedups)
                else:
                    album = AlbumEntry(os.path.join(self.rootDirs[0], webAlbum.title.text), webAlbum.title.text)
                    self.albums[webAlbum.title.text] = album
                    self.scanWebPhotos(album, webAlbum, deletedups)

    def scanWebPhotos(self, foundAlbum, webAlbum, deletedups):
        # bit of a hack, but can't see anything in api to do it.
        photos = repeat(lambda: gd_client.GetFeed(webAlbum.GetPhotosUri() + "&imgmax=d"),
                        "list photos in album %s" % foundAlbum.albumName, True)
        webAlbum = WebAlbum(webAlbum, int(photos.total_results.text))
        foundAlbum.webAlbum.append(webAlbum)
        for photo in photos.entry:
            if photo.title.text is None:
                photoTitle = ""
            else:
                photoTitle = urllib.unquote(photo.title.text)

            if photoTitle in foundAlbum.entries:
                entry = foundAlbum.entries[photoTitle]
                if entry.isWeb():
                    if (deletedups):
                        print "Deleted dupe of %s on server" % photoTitle
                        repeat(lambda: gd_client.Delete(photo), "deleting dupe %s" % photoTitle, False)
                    else:
                        print "WARNING: More than one copy of %s - ignoring" % photoTitle
                else:
                    entry.setWebReference(photo)
                    # print photo.exif.time
            else:
                fileEntry = FileEntry(photoTitle, None, photo, False, foundAlbum)
                foundAlbum.entries[photoTitle] = fileEntry

    def uploadMissingAlbumsAndFiles(self, compareattributes, mode, test, allowDelete):
        size = 0
        for album in self.albums.itervalues():
            size += len(album.entries)
        count = 0
        actionCounts = {}
        for action in Actions:
            actionCounts[action] = 0
        for album in self.albums.itervalues():
            for file in album.entries.itervalues():
                changed = file.changed(compareattributes)
                if verbose:
                    print ("%s (%s) #%s/%s - %s" % (mode[changed], changed, str(count), str(size), file.getFullName()))
                if not test:
                    if mode[changed] == Actions.DELETE_LOCAL and not allowDelete[0]:
                        print (
                            "Not deleteing local file %s because permissions not granted using allowDelete" % file.getFullName())
                    else:
                        if mode[changed] == Actions.DELETE_REMOTE and not allowDelete[1]:
                            print (
                                "Not deleteing remote file %s because permissions not granted using allowDelete" % file.getFullName())
                        else:
                            repeat(lambda: getattr(file, mode[changed].lower())(changed),
                                   "%s on %s identified as %s" % (mode[changed], file.getFullName(), changed), False)
                actionCounts[mode[changed]] += 1
                count += 1
            album.writeDate()
        print("Finished transferring files. Total files found %s, composed of %s" % (count, str(actionCounts)))

    @staticmethod
    def createAlbumName(name, index):
        if index == 0:
            return name
        else:
            return "%s #%s" % (name, index + 1)

    @staticmethod
    def flatten(name):
        return re.sub("#[0-9]*$", "", name).rstrip()


