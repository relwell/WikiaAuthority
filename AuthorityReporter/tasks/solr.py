from celery import group, shared_task
from nlp_services.caching import use_caching
from nlp_services.authority import WikiAuthorityService, PageAuthorityService
from nlp_services.discourse.entities import WikiPageToEntitiesService, WikiEntitiesService
from itertools import izip_longest
from AuthorityReporter.library import solr, MinMaxScaler
from time import sleep
import requests


def iter_grouper(n, iterable, fillvalue=None):
    args = [iter(iterable)] * n
    return izip_longest(fillvalue=fillvalue, *args)


@shared_task
def add_with_metadata(wiki_data, docs):
    """
    For a grouping of docs, gets metadata from SearchController, and generates user documents.
    Then commits. Let's hear it for asynchronous request handling.

    :param wiki_data: a dict representing the data we've retrieved from the Wikia API
    :type wiki_data: dict
    :param docs: a list of docs ready to be uploaded to solr
    :type docs: list

    :return: a list of tuples including user ids and accompanying user name
    :rtype: list
    """
    docs = filter(lambda x: x, docs)
    params = {
        u'controller': u'WikiaSearchIndexerController',
        u'method': u'get',
        u'service': u'Metadata',
        u'ids': u'|'.join([doc['id'] for doc in docs if doc])  # doc can be none here LOL
    }
    response = requests.get(u"%swikia.php" % wiki_data['url'], params=params).json()
    author_pages = []

    pa = PageAuthorityService()

    user_dict = {}

    for doc in docs:
        for resp in response.get('contents', []):
            if doc['id'] == resp['id']:
                doc.update(resp)

        users_txt = []
        user_ids_is = []
        total_contribs_f = 0.0
        pa_response = pa.get(doc['id'])
        if pa_response['status'] != 200:
            continue

        for contrib in pa_response[doc['id']]:
            user_dict[(contrib['userid'], contrib['user'])] = 1
            users_txt.append(contrib['user'])
            user_ids_is.append(contrib['userid'])
            total_contribs_f += contrib['contribs']

            author_pages.append({
                'id': '%s_%s' % (doc['id'], contrib['userid']),
                'doc_id_s': doc['id'],
                'user_id_i': '%s' % contrib['userid'],
                'type_s': {'set': 'PageUser'},
                'name_txt_en': {'set': contrib['user']},
                'name_s': {'set': contrib['user']},
                'contribs_f': {'set': contrib['contribs']},
                'attr_entities': {'set': doc['attr_entities']['set']},
                'doc_authority_f': {'set': doc['authority_f']['set']},
                'user_page_authority_f': {'set': contrib['contribs'] * doc['authority_f']['set']}
            })

            doc['attr_users'] = {'set': users_txt}
            doc['user_ids_is'] = {'set': user_ids_is}
            doc['total_contribs_f'] = {'set': total_contribs_f}

    update_docs = list(docs) + list(author_pages)
    solr.collection_for_wiki(wiki_data['id']).add(update_docs)
    return user_dict.keys()


def build_wiki_user_doc(wiki_data, user_tuple):
    """
    Retrieves data from wiki collection to generate a user document at the wiki level

    :param wiki_data: a dict representing the data we've retrieved from the Wikia API
    :type wiki_data: dict
    :param user_tuple: a tuple containing user id and user name
    :type user_tuple: tuple

    :return: the document we want to add to solr; we will commit in bulk instead of blasting the network
    :rtype: dict
    """

    user_id, user_name = user_tuple
    collection = solr.collection_for_wiki(str(wiki_data['id']))
    user_doc = {
        'id': '%d_%d' % (wiki_data['id'], user_id),
        'user_id_i': user_id,
        'wiki_id_i': wiki_data['id'],
        'wiki_name_txt': wiki_data['title'],
        'name_s': {'set': user_name},
        'type_s': {'set': 'WikiUser'},
        'name_txt_en': {'set': user_name},
    }
    doc_ids = []
    entities = []
    authorities = []
    for doc in solr.get_all_docs_by_query(collection, 'type_s:PageUser AND user_id_i:%d' % user_id):
        doc_ids.append(doc['doc_id_s'])
        map(entities.append, doc['attr_entities'])
        authorities.append(doc['user_page_authority_f'])

    user_doc['doc_ids_ss'] = {'set': doc_ids}
    user_doc['attr_entities'] = {'set': entities}
    user_doc['total_page_authority_f'] = {'set': sum(authorities)}
    user_doc['page_authority_fs'] = {'set': authorities}

    return user_doc


def ingest_data(wiki_id):
    """
    Create Solr documents for a given wiki ID

    :param wiki_id: the ID of the wiki (int or str)
    :type wiki_id: int
    :return:
    """

    resp = requests.get(u'http://www.wikia.com/api/v1/Wikis/Details', params={u'ids': wiki_id})
    items = resp.json()['items']
    if wiki_id not in items:
        print u"Wiki doesn't exist?"
        return

    api_data = items[wiki_id]
    wiki_data = {
        'id': api_data['id'],
        'wam_f': {'set': api_data['wam_score']},
        'desc_txt': {'set': api_data['desc']}
    }
    for key in api_data['stats'].keys():
        wiki_data['%s_i' % key] = {'set': api_data['stats'][key]}

    collection = solr.existing_collection(solr.collection_for_wiki(wiki_id))

    use_caching(is_read_only=True, shouldnt_compute=True)

    wpe = WikiPageToEntitiesService().get_value(wiki_id)
    if not wpe:
        print u"NO WIKI PAGE TO ENTITIES SERVICE FOR", wiki_id
        return False

    documents = []

    grouped_futures = []

    pages_to_authority = WikiAuthorityService().get_value(str(wiki_data['id']))
    for counter, (doc_id, entity_data) in enumerate(wpe.items()):
        documents.append({
            'id': doc_id,
            'attr_entities': {'set': list(set(entity_data.get(u'redirects', {}).values()
                                              + entity_data.get(u'titles')))},
            'type_s': {'set': 'Page'},
            'authority_f': {'set': pages_to_authority.get(doc_id, 0)}
        })

        if counter % 1500 == 0:
            print counter
            grouped_futures.append(
                group(add_with_metadata.s(api_data, grouping) for grouping in iter_grouper(15, documents))()
            )

            documents = []

    # block on completion of all grouped futures
    while True:
        completed = 0
        total = 0
        for future in grouped_futures:
            completed += future.completed_count()
            total += len(future.results)
        print "Grouped Tasks: (%d/%d)" % (completed, total)
        sleep(30)

    # Get ready to behold the power of fp and async:
    # unpack all the return values into list, flatten the list via list comprehension
    all_user_tuples = list(set([user_tuple for future in grouped_futures for user_tuple in future.get()]))

    # assign the unique user ids to the first variable, and the unique usernames to the second
    all_user_ids, all_users = zip(*all_user_tuples)

    collection.commit()

    wiki_data['attr_entities'] = {'set': []}
    for count, entities in WikiEntitiesService().get_value(str(wiki_id)):
        for entity in entities:
            map(wiki_data['attr_entities']['set'].append, [entity] * count)

    wiki_data['user_ids_is'] = {'set': all_user_ids}
    wiki_data['attr_users'] = {'set': all_users}
    wiki_data['total_authority_f'] = {'set': sum(pages_to_authority.values())}
    wiki_data['authorities_fs'] = {'set': pages_to_authority.values()}

    wiki_collection = solr.existing_collection(solr.global_collection())
    wiki_collection.add(wiki_data)
    wiki_collection.commit()

    print "Retrieving user docs..."
    futures = group(build_wiki_user_doc.s(api_data, user_tuple) for user_tuple in all_user_tuples)()

    while not futures.ready():
        print "Progress: (%d/%d)" % (futures.completed_count(), len(futures.results))
        sleep(30)

    user_docs = futures.get()

    scaler = MinMaxScaler([doc['total_page_authority_f'] for doc in user_docs])
    for doc in user_docs:
        doc['scaled_authority_f'] = scaler.scale(doc['total_page_authority_f'])

    wiki_user_collection = solr.existing_collection(solr.wiki_user_collection())
    wiki_user_collection.add(user_docs)
    wiki_user_collection.commit()


    # next steps:
    # * Need to create User document for Wiki core by aggregating PageUsers
    # * Will need to create a separate task for creating global user documents I think


def global_ingestion():
    print "Analyzing Wikis..."
    wiki_collection = solr.existing_collection(solr.global_collection())

    wiki_docs = [doc for doc in solr.get_all_docs_by_query(wiki_collection, '*:*')]
    scaler = MinMaxScaler([doc['total_authority_f'] for doc in wiki_docs])
    for doc in wiki_docs:
        doc['scaled_authority_f'] = scaler.scale(doc['total_authority_f'])

    print "Analyzing Users..."
    user_collection = solr.existing_collection(solr.user_collection())
    wiki_user_collection = solr.wiki_user_collection()

    id_to_docs = dict()
    for user_doc in solr.get_all_docs_by_query(wiki_user_collection, '*:*'):
        doc_id = user_doc['id']
        if doc_id not in id_to_docs:
            id_to_docs[doc_id] = dict(id=doc_id,
                                      attr_entities={'set': []},
                                      name_s={'set': user_doc['name_s']},
                                      wikis_is={'set': []},
                                      attr_wikis={'set': []},
                                      authorities_fs={'set': []},
                                      total_authority_f={'set': 0},
                                      scaled_authority_f={'set': 0})
        map(id_to_docs[doc_id]['attr_entities']['set'].append, user_doc['attr_entities'])
        id_to_docs[doc_id]['wikis_is']['set'].append(user_doc['wiki_id_i'])
        id_to_docs[doc_id]['attr_wikis']['set'].append(user_doc['wiki_name_txt'])
        id_to_docs[doc_id]['authorities_fs']['set'].append(user_doc['total_page_authority_f'])

    id_to_total_authorities = dict([(uid, sum(doc['total_page_authorities_fs'])) for uid, doc in id_to_docs.items()])
    user_scaler = MinMaxScaler(id_to_total_authorities.values())
    for uid, total_authority in id_to_total_authorities:
        id_to_docs[uid]['total_authority_f']['set'] = total_authority
        id_to_docs[uid]['scaled_authority_f']['set'] = user_scaler.scale(total_authority)

    user_collection.add(id_to_docs.values())
    user_collection.commit()


    # we also need to start thinking about how we're going to represent topics and what their authority is per wiki,
    # and per page.