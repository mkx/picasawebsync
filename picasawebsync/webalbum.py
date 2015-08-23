# Class to store web album details

class WebAlbum:
    def __init__(self, config, album, numberFiles):
        self.albumUri = album.GetPhotosUri()
        self.albumTitle = album.title.text
        self.numberFiles = numberFiles
        self.albumid = album.id.text
        self.config = config

    def getEditObject(self):
        return self.config.getGdClient().GetEntry(self.albumid)

