import urllib.parse as urlparse
from urllib.parse import parse_qs


def remove_outer_parens(string, strip=True):
    if strip:
        string = string.strip()
    if string.startswith('(') and string.endswith(')'):
        return string[1:-1]
    else:
        return string

# from https://stackoverflow.com/a/5075477
def params_from_url(url):
    parsed = urlparse.urlparse(url)
    return parse_qs(parsed.query)

def id_from_url(url):
    params = params_from_url(url)
    if 'id' in params:
        return int(params['id'][0])
    else:
        return None
