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
