from celery import group, shared_task
from nlp_services.caching import use_caching
from nlp_services.authority import WikiAuthorityService, PageAuthorityService
from nlp_services.discourse.entities import WikiPageToEntitiesService, WikiEntitiesService
from itertools import izip_longest
from AuthorityReporter.library import solr, MinMaxScaler
from time import sleep
from solrcloudpy import SearchOptions
from AuthorityReporter.tasks import get_with_backoff
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
        u'service': u'All',
        u'ids': u'|'.join([doc['id'] for doc in docs if doc])  # doc can be none here LOL
    }

    r = requests.get(u"%swikia.php" % wiki_data['url'], params=params)
    response = r.json()
    contents = response.get('contents', [])
    
    author_pages = []

    pa = PageAuthorityService()

    user_dict = {}

    for doc in docs:
        for search_doc in contents:
            if 'id' not in search_doc:
                continue

            if doc['id'] == search_doc['pageid']['set']:
                doc.update(dict(
                    attr_title=search_doc['title_en'],
                    title_s=search_doc['title_en'],
                    url_s=search_doc['url'],
                    hub_s=search_doc['hub']
                ))

        users_txt = []
        user_ids_is = []
        total_contribs_f = 0.0
        pa_response = pa.get(doc['id'])
        if pa_response['status'] != 200:
            continue

        wiki_id, page_id = doc['id'].split('_')

        for contrib in pa_response[doc['id']]:
            user_dict[(contrib['userid'], contrib['user'])] = 1
            users_txt.append(contrib['user'])
            user_ids_is.append(contrib['userid'])
            total_contribs_f += contrib['contribs']

            author_pages.append({
                'id': '%s_%s' % (doc['id'], contrib['userid']),
                'doc_id_s': {'set': doc['id']},
                'wiki_id_i': wiki_id,
                'page_id_i': page_id,
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
    solr.all_pages_collection().add(docs)
    solr.all_user_pages_collection().add(author_pages)
    return user_dict.keys()


@shared_task
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
    contribs = []
    for doc in solr.get_all_docs_by_query(collection, 'type_s:PageUser AND user_id_i:%d' % user_id):
        doc_ids.append(doc['doc_id_s'])
        if 'attr_entities' in doc:
            map(entities.append, doc['attr_entities'])
        if 'user_page_authority_f' in doc:
            authorities.append(doc['user_page_authority_f'])
        if 'contribs_f' in doc:
            contribs.append(doc['contribs_f'])

    total_authorities = sum(authorities)
    total_contribs = sum(contribs)

    user_doc['doc_ids_ss'] = {'set': doc_ids}
    user_doc['attr_entities'] = {'set': entities}
    user_doc['total_page_authority_f'] = {'set': total_authorities}
    user_doc['total_contribs_f'] = {'set': total_contribs}
    user_doc['page_authority_fs'] = {'set': authorities}
    user_doc['contribs_fs'] = {'set': contribs}
    user_doc['total_contribs_authority_f'] = {'set': total_authorities * total_contribs}

    return user_doc


@shared_task
def get_wiki_topic_doc(wiki_id, topic):
    """
    Create a solr doc for a given topic based on all matching pages for a wiki

    :param wiki_id: the ID of the wiki
    :type wiki_id: str
    :param topic: the topic we're creating a document for
    :type topic: str

    :return: the solr document we want to add
    :rtype: dict
    """
    collection = solr.collection_for_wiki(wiki_id)
    authorities = []
    all_user_id_dict = {}
    all_user_name_dict = {}

    for doc in solr.get_all_docs_by_query(collection, 'type_s:Page AND attr_entities:"%s"' % topic):
        if 'user_id_is' in doc:
            for user_id in doc['user_ids_is']:
                all_user_id_dict[user_id] = True
        if 'attr_users' in doc:
            for user_name in doc['attr_users']:
                all_user_name_dict[user_name] = True
        if 'authority_f' in doc:
            authorities.append(doc['authority_f'])

    total_authority = sum(authorities)
    return {
        'id': '%s_%s' % (wiki_id, topic),
        'wiki_id_i': wiki_id,
        'topic_s': topic,
        'topic_txt_en': topic,
        'type_s': {'set': 'Topic'},
        'user_ids_is': {'set': all_user_id_dict.keys()},
        'user_names_ss': {'set': all_user_name_dict.keys()},
        'total_authority_f': {'set': total_authority},
        'avg_authority_f': {'set': total_authority / float(len(authorities))}
    }


def ingest_data(wiki_id):
    """
    Create Solr documents for a given wiki ID

    :param wiki_id: the ID of the wiki (int or str)
    :type wiki_id: int
    :return:
    """

    # make sure all pages and all user pages exists
    solr.existing_collection(solr.all_pages_collection())
    solr.existing_collection(solr.all_user_pages_collection())

    resp = requests.get(u'http://www.wikia.com/api/v1/Wikis/Details', params={u'ids': wiki_id})
    items = resp.json()['items']
    if wiki_id not in items:
        print u"Wiki doesn't exist?"
        return

    api_data = items[wiki_id]
    wiki_data = {
        'id': api_data['id'],
        'wam_f': {'set': api_data['wam_score']},
        'title_s': {'set': api_data['title']},
        'attr_title': {'set': api_data['title']},
        'attr_desc': {'set': api_data['desc']}
    }
    for key in api_data['stats'].keys():
        wiki_data['%s_i' % key] = {'set': api_data['stats'][key]}

    wiki_api_data = requests.get(u'%swikia.php' % (api_data[u'url']),
                                 params={u'method': u'getForWiki',
                                         u'service': u'CrossWikiCore',
                                         u'controller': u'WikiaSearchIndexerController'}).json()[u'contents']

    wiki_data[u'hub_s'] = wiki_api_data[u'hub_s']

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

        if counter != 0 and counter % 1500 == 0:
            grouped_futures.append(
                group(add_with_metadata.s(api_data, grouping) for grouping in iter_grouper(15, documents))()
            )

            documents = []

    grouped_futures.append(
        group(add_with_metadata.s(api_data, grouping) for grouping in iter_grouper(15, documents))()
    )

    # block on completion of all grouped futures
    completed = 0
    total = 0
    while len(filter(lambda x: not x.ready(), grouped_futures)) > 1:
        new_completed = 0
        new_total = 0
        for future in grouped_futures:
            new_completed += future.completed_count()
            new_total += len(future.results)
        if completed != new_completed or total != new_total:
            completed = new_completed
            total = new_total
            print "Grouped Tasks: (%d/%d)" % (completed, total)
        sleep(2)

    all_user_tuples = []
    for future in grouped_futures:
        result = get_with_backoff(future, [])
        map(all_user_tuples.extend, result)

    all_user_tuples = list(set(all_user_tuples))
    if not all_user_tuples:
        print "Empty user tuples, bailing"
        return

    # assign the unique user ids to the first variable, and the unique usernames to the second
    all_user_ids, all_users = zip(*all_user_tuples)

    collection.commit()
    solr.all_pages_collection().commit()
    solr.all_user_pages_collection().commit()

    wiki_data['attr_entities'] = {'set': []}

    for count, entities in WikiEntitiesService().get_value(str(wiki_id)).items():
        for entity in entities:
            map(wiki_data['attr_entities']['set'].append, [entity] * int(count))  # goddamnit count isn't int

    wiki_data['user_ids_is'] = {'set': all_user_ids}
    wiki_data['attr_users'] = {'set': all_users}
    wiki_data['total_authority_f'] = {'set': sum(pages_to_authority.values())}
    wiki_data['authorities_fs'] = {'set': pages_to_authority.values()}

    wiki_collection = solr.existing_collection(solr.global_collection())
    wiki_collection.add([wiki_data])
    wiki_collection.commit()
    print "Committed wiki data"

    print "Retrieving user docs..."
    futures = group(build_wiki_user_doc.s(api_data, user_tuple) for user_tuple in all_user_tuples)()
    future_result_len = len(futures.results)
    while not futures.ready():
        print "Progress: (%d/%d)" % (futures.completed_count(), future_result_len)
        sleep(2)

    user_docs = get_with_backoff(futures, [])
    if not user_docs:
        print "User docs was empty. Possibly connection problems."
        return

    authority_scaler = MinMaxScaler([doc['total_page_authority_f']['set'] for doc in user_docs])
    contribs_scaler = MinMaxScaler([doc['total_contribs_f']['set'] for doc in user_docs])
    for doc in user_docs:
        scaled_authority = authority_scaler.scale(doc['total_page_authority_f']['set'])
        scaled_contribs = contribs_scaler.scale(doc['total_contribs_f']['set'])
        doc['scaled_authority_f'] = {'set': scaled_authority}
        doc['scaled_contribs_f'] = {'set': scaled_contribs}
        doc['scaled_contribs_authority_f'] = {'set': scaled_authority * scaled_contribs}

    wiki_user_collection = solr.existing_collection(solr.wiki_user_collection())
    wiki_user_collection.add(user_docs)
    wiki_user_collection.commit()

    print "Analyzing topics"
    futures = group(get_wiki_topic_doc.s(wiki_data['id'], topic)
                    for topic in list(set(wiki_data['attr_entities']['set'])))()
    future_result_len = len(futures.results)
    counter = 0
    while not futures.ready():
        if counter % 5 == 0:
            print "Progress: (%d/%d)" % (futures.completed_count(), future_result_len)
        sleep(2)
        counter += 1
    topic_docs = get_with_backoff(futures, [])
    if not topic_docs:
        print "No topics, probably a connection error"
        return

    collection.add(topic_docs)
    collection.commit()

    topic_collection = solr.existing_collection(solr.all_topics_collection())
    topic_collection.add(topic_docs)
    topic_collection.commit()


@shared_task
def analyze_pages_globally():
    print "Analyzing All Pages..."
    page_collection = solr.all_pages_collection()

    authorities = []
    for page_doc in solr.get_all_docs_by_query(page_collection, '*:*'):
        authorities.append(page_doc['authority_f'])

    page_scaler = MinMaxScaler(authorities)
    docs = []
    counter = 0
    for page_doc in solr.get_all_docs_by_query(page_collection, '*:*'):
        docs.append({'id': page_doc['id'], 'scaled_authority_f': {'set': page_scaler.scale(page_doc['authority_f'])}})
        counter += 1
        if counter % 500:
            page_collection.add(docs)
            docs = []
    page_collection.commit()


@shared_task
def analyze_users_globally():
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
                                      name_txt_en={'set': user_doc['name_txt_en']},
                                      wikis_is={'set': []},
                                      attr_wikis={'set': []},
                                      authorities_fs={'set': []},
                                      total_authority_f={'set': 0},
                                      scaled_authority_f={'set': 0})
        map(id_to_docs[doc_id]['attr_entities']['set'].append, user_doc['attr_entities'])
        id_to_docs[doc_id]['wikis_is']['set'].append(user_doc['wiki_id_i'])
        id_to_docs[doc_id]['attr_wikis']['set'].append(user_doc['wiki_name_txt'])
        id_to_docs[doc_id]['authorities_fs']['set'].append(user_doc['total_page_authority_f'])

    id_to_total_authorities = dict([(uid, sum(doc['authorities_fs']['set'])) for uid, doc in id_to_docs.items()])
    user_scaler = MinMaxScaler(id_to_total_authorities.values())
    for uid, total_authority in id_to_total_authorities.items():
        id_to_docs[uid]['total_authority_f']['set'] = total_authority
        id_to_docs[uid]['scaled_authority_f']['set'] = user_scaler.scale(total_authority)

    user_collection.add(id_to_docs.values())
    user_collection.commit()


@shared_task
def analyze_wikis_globally():
    print "Analyzing Wikis..."
    wiki_collection = solr.existing_collection(solr.global_collection())

    wiki_docs = [doc for doc in solr.get_all_docs_by_query(wiki_collection, '*:*')]
    scaler = MinMaxScaler([doc['total_authority_f'] for doc in wiki_docs])
    new_docs = []
    for doc in wiki_docs:
        new_docs.append({'id': doc['id'], 'scaled_authority_f': {'set': scaler.scale(doc['total_authority_f'])}})
    wiki_collection.add(new_docs)
    wiki_collection.commit()


@shared_task
def aggregate_global_topic(topic):
    collection = solr.all_topics_collection()

    total_authorities = []
    all_user_id_dict = {}
    all_user_name_dict = {}
    all_wikis = []

    for doc in solr.get_all_docs_by_query(collection, topic):
        total_authorities.append(doc['total_authority_f'])
        if 'user_id_is' in doc:
            for user_id in doc['user_id_is']:
                all_user_id_dict[user_id] = True
        if 'user_names_ss' in doc:
            for user_name in doc['user_names_ss']:
                all_user_name_dict[user_name] = True
        if 'wiki_id_i' in doc:
            all_wikis.append(doc['wiki_id_i'])

    total_authority = sum(total_authorities)

    avg_authority = 0
    if total_authority > 0:
        avg_authority = total_authority / float(total_authority)

    return {
        'id': topic,
        'topic_s': {'set': topic},
        'wikis_is': {'set': all_wikis},
        'user_ids_is': {'set': all_user_id_dict.keys()},
        'user_names_ss': {'set': all_user_name_dict.keys()},
        'total_authority_f': {'set': total_authority},
        'avg_authority_f': {'set': avg_authority},
    }


@shared_task
def analyze_topics_globally():
    print "Analyzing Topics..."
    collection = solr.all_topics_collection()

    se = SearchOptions()
    se.commonparams.q('*:*')

    futures = group(aggregate_global_topic.s(topic)
                    for topic, _ in solr.iterate_per_facetfield_value(collection, se, 'topic_s'))()

    while not futures.ready():
        print "Progress: (%d/%d)" % (futures.completed_count(), len(futures.results))
        sleep(2)

    collection.add(get_with_backoff(futures, []))
    collection.commit()


@shared_task()
def analyze_all_user_pages_globally():
    collection = solr.all_user_pages_collection()
    authorities = []
    contribs = []
    for doc in solr.get_all_docs_by_query(collection, '*:*', fields="id,doc_authority_f"):
        authorities.append(doc['doc_authority_f'])
        contribs.append(doc['contribs_f'])

    authority_scaler = MinMaxScaler(authorities)
    contribs_scaler = MinMaxScaler(contribs)
    new_docs = []
    for doc in solr.get_all_docs_by_query(collection, '*:*', fields="id,doc_authority_f"):
        scaled_authority = authority_scaler.scale(doc['doc_authority_f'])
        scaled_contribs = contribs_scaler.scale(doc['contribs_f'])
        new_docs.append({
            'id': doc['id'],
            'scaled_authority_f': {'set': scaled_authority},
            'scaled_contribs_f': {'set': scaled_contribs},
            'scaled_contrib_authority_f': {'set': scaled_authority * scaled_contribs}
        })

    collection.add(new_docs)
    collection.commit()


def global_ingestion():

    # todo: async
    analyze_wikis_globally()
    analyze_users_globally()
    analyze_pages_globally()
    analyze_topics_globally()
    analyze_users_globally()