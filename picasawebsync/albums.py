import os
import re
import urllib


from albumentry import *
from webalbum import *
from fileentry import FileEntry

from consts import Actions

import gdata.media
import gdata.geo

import logging

from progress.bar import Bar


# Class to store details of an album
class Albums:
    def __init__(self, config, replace, namingextract):
        self.config = config
        self.rootDirs = config.rootDirs
        self.albums = self.scanFileSystem(config.albumNaming, config.excludes, replace, namingextract)

    # Method to translate directory name to an album name
    def convertDirToAlbum(self, formElements, root, name, replace, namingextract):
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

    # walk the directory tree populating the list of files we have locally
    # @print_timing
    def scanFileSystem(self, albumNaming, excludes, replace, namingextract):
        fileAlbums = {}
        for rootDir in self.rootDirs:
            for dirName, subdirList, fileList in os.walk(rootDir):
                subdirList[:] = [d for d in subdirList if not re.match(excludes, os.path.join(dirName, d))]
                albumName = self.convertDirToAlbum(albumNaming, rootDir, dirName, replace, namingextract)
                # have we already seen this album? If so append our path to it's list
                if albumName in fileAlbums:
                    album = fileAlbums[albumName]
                    thisRoot = album.suggestNewRoot(dirName)
                else:
                    # create a new album
                    thisRoot = dirName
                    album = AlbumEntry(self.config, dirName, albumName)
                    fileAlbums[albumName] = album
                # now iterate it's files to add them to our list
                for fname in fileList:
                    fullFilename = os.path.join(dirName, fname)
                    if not re.match(excludes, fullFilename):
                        # figure out the filename relative to the root dir of the album (to ensure uniqeness)
                        relFileName = re.sub("^/", "", fullFilename[len(thisRoot):])
                        fileEntry = FileEntry(self.config, relFileName, fullFilename, None, True, album)
                        album.entries[relFileName] = fileEntry
        if self.config.verbose:
            print ("Found " + str(len(fileAlbums)) + " albums on the filesystem")
        if len(fileAlbums) == 0:
            logging.error("No local album")
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
        webAlbums = self.config.getGdClient().GetUserFeed(user=owner)
        for webAlbum in webAlbums.entry:
            webAlbumTitle = Albums.flatten(webAlbum.title.text)
            if re.match(server_excludes, webAlbumTitle):
                if self.config.verbose:
                    print(
                        'Skipping (because matches server exclude) '
                        'web-album %s (containing %s files)' %
                        (
                            webAlbum.title.text,
                            webAlbum.numphotos.text
                        )
                    )
            else:
                if self.config.verbose:
                    print(
                        'Scanning web-album %s (containing %s files)' %
                        (webAlbum.title.text, webAlbum.numphotos.text)
                    )
                if webAlbumTitle in self.albums:
                    foundAlbum = self.albums[webAlbumTitle]
                    self.scanWebPhotos(foundAlbum, webAlbum, deletedups)
                else:
                    album = AlbumEntry(
                        self.config,
                        os.path.join(
                            self.rootDirs[0],
                            webAlbum.title.text
                        ),
                        webAlbum.title.text
                    )
                    self.albums[webAlbum.title.text] = album
                    self.scanWebPhotos(album, webAlbum, deletedups)

    def scanWebPhotos(self, foundAlbum, webAlbum, deletedups):
        photos = self.config.getGdClient().GetFeed(
            webAlbum.GetPhotosUri() + "&imgmax=d"
        )
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
                        print("Deleted dupe of %s on server" % photoTitle)
                        self.config.getGdClient.Delete(photo)
                    else:
                        logging.warning(
                            "More than one copy of %s - ignoring" % photoTitle
                        )
                else:
                    entry.setWebReference(photo)
            else:
                fileEntry = FileEntry(
                    self.config,
                    photoTitle,
                    None,
                    photo,
                    False,
                    foundAlbum
                )
                foundAlbum.entries[photoTitle] = fileEntry

    def uploadMissingAlbumsAndFiles(self, compareattributes, mode, test,
                                    allowDelete):
        size = 0  # total number of items
        count = 0  # number of actions
        for album in self.albums.itervalues():
            size += len(album.entries)
        actionCounts = {}
        for action in Actions:
            actionCounts[action] = 0

        bar = Bar('Uploading', max=size)

        for album in self.albums.itervalues():
            for file in album.entries.itervalues():
                changed = file.changed(compareattributes)
                if self.config.verbose:
                    print(
                        "%s (%s) #%s/%s - %s" %
                        (
                            mode[changed],
                            changed,
                            str(count),
                            str(size),
                            file.getFullName()
                        )
                    )
                if not test:
                    if mode[changed] == Actions.DELETE_LOCAL \
                       and not allowDelete[0]:
                        print(
                            "Not deleting local file %s because permissions "
                            "not granted using allowDelete" %
                            file.getFullName()
                        )
                    else:
                        if mode[changed] == Actions.DELETE_REMOTE \
                           and not allowDelete[1]:
                            print(
                                "Not deleteing remote file %s because "
                                "permissions not granted using allowDelete" %
                                file.getFullName()
                            )
                        else:
                            getattr(file, mode[changed].lower())(changed)

                actionCounts[mode[changed]] += 1
                count += 1
                bar.next()
            album.writeDate()

        bar.finish()

        print(
            "Finished transferring files. Total files found %s, composed of %s"
            % (count, str(actionCounts))
        )

    @staticmethod
    def createAlbumName(name, index):
        if index == 0:
            return name
        else:
            return "%s #%s" % (name, index + 1)

    @staticmethod
    def flatten(name):
        return re.sub("#[0-9]*$", "", name).rstrip()
