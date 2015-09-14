from solrcloudpy import SolrConnection, SearchOptions
from copy import deepcopy
import AuthorityReporter


DEFAULT_DOCSIZE = 50


def connection():
    return SolrConnection(AuthorityReporter.app.app.config['SOLR_HOSTS'])


def collection_for_wiki(wiki_id):
    return connection()[str(wiki_id)]


def all_topics_collection():
    return connection()['all_topics']


def all_pages_collection():
    return connection()['all_pages']


def wiki_user_collection():
    return connection()['wiki_users']


def global_collection():
    return connection()['wikis']


def user_collection():
    return connection()['users']


def all_user_pages_collection():
    return connection()['all_user_pages']


def existing_collection(collection):
    """
    Reusable logic for creating a collection if needed

    :param collection: SolrCollection
    :type collection: SolrCollection

    :return: the collection, created for sure
    :rtype: SolrCollection
    """

    exists = False
    try:
        exists = collection.exists()
    except KeyError:
        pass

    if not exists:
        collection.create()

    return collection


def debug_requests():
    import requests
    import logging

    # These two lines enable debugging at httplib level (requests->urllib3->http.client)
    # You will see the REQUEST, including HEADERS and DATA, and RESPONSE with HEADERS but without DATA.
    # The only thing missing will be the response.body which is not logged.
    try:
        import http.client as http_client
    except ImportError:
        # Python 2
        import httplib as http_client
    http_client.HTTPConnection.debuglevel = 1

    # You must initialize logging, otherwise you'll not see debug output.
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


def iterate_results(collection, searchoptions):
    """
    A generator for accessing documents
    :param collection: the collection object from solrpy
    :type collection: solrcloudpy.Collection
    :param searchoptions: the options we are concerned with
    :type searchoptions: solrcloudpy.SearchOptions
    :return: a document
    :rtype: dict
    """
    offset = 0
    searchoptions.commonparams.rows(500)
    while True:
        so = deepcopy(searchoptions)
        so.commonparams.start(offset)
        results = collection.search(so)
        for doc in results.result['response']['docs']:
            yield doc
        offset += 500
        if offset > results.result['response']['numFound']:
            break


def get_docs_by_query(collection, query, page=1, sort="id asc", docsize=DEFAULT_DOCSIZE, fields=None, boost=None):
    """
    Helper function for accessing docs by query

    :param collection: an optional collection to pass
    :type collection: SolrCollection
    :param query: the query string
    :type query: str
    :param page: the page we want
    :type page: int
    :param sort: the sort of the item, default is name asc; pass None to sort by score
    :type sort: str
    :param fields: the fields we want, None if we don't want to specify
    :type fields: list
    :return: list of results
    :rtype: list
    """
    return get_docs_by_query_with_limit(collection,
                                        query,
                                        sort=sort,
                                        limit=docsize,
                                        offset=(page-1) * docsize,
                                        fields=fields,
                                        boost=boost)


def get_docs_by_query_with_limit(collection, query, limit=None, offset=None, sort=None, fields=None, boost=None):
    """
    Helper function for accessing docs by query

    :param collection: an optional collection to pass
    :type collection: SolrCollection
    :param query: the query string
    :type query: str
    :param limit: the number of docs we want
    :type limit: int
    :param offset: starting row of docs
    :type offset: int
    :param sort: the sort of the item, default None to sort by score
    :type sort: str
    :param fields: the fields we want, None if we don't want to specify
    :type fields: list
    :return: the response dict
    :rtype: dict
    """

    return get_result_by_query(collection, query, limit, offset, sort, fields=fields, boost=boost)['docs']


def get_paginated_result_by_query(collection, query, page=1, sort=None, docsize=DEFAULT_DOCSIZE, **kwargs, boost=None):
    """
    Helper function for accessing result by query using approach

    :param collection: an optional collection to pass
    :type collection: SolrCollection
    :param query: the query string
    :type query: str
    :param page: the page we want
    :type page: int
    :param sort: the sort of the item, default None to sort by score
    :type sort: str
    :return: the response dict
    :rtype: dict
    """
    return get_result_by_query(collection, query, limit=docsize, sort=sort, offset=(page-1) * docsize, boost=boost)


def get_result_by_query(collection, query, limit=None, offset=None, sort=None, fields=None, boost=None):
    """
    Helper function for accessing result by query -- lets us access numfound as well

    :param collection: an optional collection to pass
    :type collection: SolrCollection
    :param query: the query string
    :type query: str
    :param limit: the number of docs we want
    :type limit: int
    :param offset: starting row of docs
    :type offset: int
    :param sort: the sort of the item, default is name asc; pass None to sort by score
    :type sort: str
    :param fields: the fields we want, None if we don't want to specify
    :type fields: list
    :return: the response dict
    :rtype: dict
    """
    se = SearchOptions()
    se.commonparams.q(query)
    if sort:
        se.commonparams.sort(sort)
    if fields:
        se.commonparams.fl(fields)
    if boost:
        # i know this is protected, but wtf is wrong with solrcloudpy being so underfeatured
        se.commonparams._q['boost'].add(boost)
        se.commonparams._q['defType'].add('edismax')  # todo: we may want edismax everywhere?
    se.commonparams.rows(limit)
    se.commonparams.start(offset)
    response = collection.search(se)

    return response.result['response']


def get_all_docs_by_query(collection, query, sort=None, fields=None):
    """
    As above, but paginates by itself

    :param collection: the solr collection we're querying
    :type collection: SolrCollection
    :param query: the query string
    :type query: str
    :param sort: the sort of the item, default is name asc; pass None to sort by score
    :type sort: str
    :param fields: the fields we want, None if we don't want to specify
    :type fields: list
    :return: list of all results
    :rtype: list
    """
    page = 1
    results = []
    while True:
        slice = get_docs_by_query(collection, query, page, sort, 1000, fields)
        results += slice
        if not slice:
            return results
        page += 1


def iterate_per_facetfield_value(collection, searchoptions, facetfield_value):
    """
    A generator for accessing facets

    :param collection: the collection object from solrpy
    :type collection: solrcloudpy.Collection
    :param searchoptions: the options we are concerned with
    :type searchoptions: solrcloudpy.SearchOptions
    :param facetfield_value: the field we're faceting over
    :type facetfield_value: str
    :return: a string for each facet field
    :rtype: str
    """

    searchoptions.facetparams.field(facetfield_value)
    searchoptions.facetparams.limit(1000)
    searchoptions.facetparams.mincount(1)
    offset = 0
    while True:
        so = deepcopy(searchoptions)
        so.facetparams.offset(offset)
        results = collection.search(so)
        try:
            result_values = results.result['facet_counts']['facet_fields'][facetfield_value].dict.items()
        except KeyError:
            # will show "error" when we have asked for too many
            return
        for field_value, count in result_values:
            yield field_value, count
        if len(result_values) == 0:
            break
        offset += 1000