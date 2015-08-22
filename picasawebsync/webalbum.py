# Class to store web album details

class WebAlbum:
    def __init__(self, album, numberFiles):
        self.albumUri = album.GetPhotosUri()
        self.albumTitle = album.title.text
        self.numberFiles = numberFiles
        self.albumid = album.id.text

    def getEditObject(self):
        # print "Getting id "+self.albumid +" = "+gd_client.GetEntry(self.albumid)
        return gd_client.GetEntry(self.albumid)

