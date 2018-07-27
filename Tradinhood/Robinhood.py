import requests

ENDPOINTS = {
    'tokin': 'https://api.robinhood.com/oauth2/token/'
}

API_HEADERS = {
    'Accept': '*/*',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'en-US,en;q=0.9',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
    'Content-Type': 'application/json',
    'Connection': 'keep-alive',
    'X-Robinhood-API-Version': '1.221.0'
}

OAUTH_CLIENT_ID = 'c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS'

class Robinhood:

    def __init__(self):

        self.session = requests.session()
        self.session.headers = API_HEADERS

    def login(self, username='', password=''):

        if not username or not password:

            import getpass
            username = input('Username > ')
            password = getpass.getpass('Password > ')

        req_json = {
            'client_id': OAUTH_CLIENT_ID,
            'expires_in': 86400,
            'grant_type': 'password',
            'scope': 'internal',
            'username': username,
            'password': password
        }

        try:
            res = self.session.post(ENDPOINTS['tokin'], json=req_json)
            res.raise_for_status()
            res_json = res.json()
        except:
            raise Exception('Login Failed')

        if 'access_token' in res_json:

            self.token = res_json['access_token']
            self.session.headers['Authorization'] = 'Bearer ' + self.token
            return True

        return False
