from . import etl
from . import solr


def get_with_backoff(future, backoff=None, retries=5):
    try:
        return future.get()
    except:  # todo: be more specific here
        if retries == 0:
            return backoff
        else:
            return get_with_backoff(future, backoff, retries-1)