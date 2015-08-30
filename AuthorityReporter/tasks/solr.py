from celery import group, shared_task
from nlp_services.caching import use_caching
from nlp_services.authority import WikiAuthorityService, PageAuthorityService
from nlp_services.discourse.entities import WikiPageToEntitiesService, WikiEntitiesService, CombinedWikiEntitiesService
from itertools import izip_longest
from AuthorityReporter.library.solr import collection_for_wiki, global_collection, get_all_docs_by_query
from time import sleep
import requests


def iter_grouper(n, iterable, fillvalue=None):
    args = [iter(iterable)] * n
    return izip_longest(fillvalue=fillvalue, *args)


@shared_task
def add_with_metadata(wiki_data, docs):
    params = {
        u'controller': u'WikiaSearchIndexerController',
        u'method': u'get',
        u'service': u'Metadata',
        u'ids': u'|'.join([doc['id'] for doc in docs])
    }
    response = requests.get(u"%swikia.php" % wiki_data['url'], params=params).json()
    author_pages = []

    pa = PageAuthorityService()

    for doc in docs:
        for resp in response.get('contents', []):
            if doc['id'] == resp['id']:
                doc.update(resp)

        users_txt = []
        user_ids_is = []
        total_contribs_f = 0.0
        contribs = pa.get(doc['id'])
        for contrib in contribs:
            users_txt.append(contrib['user'])
            user_ids_is.append(contrib['userid'])
            total_contribs_f += contrib['contribs']

            author_pages.append({
                'id': '%s_%s' % (doc['id'], contrib['userid']),
                'type_s': {'set': 'PageUser'},
                'name_txt_en': {'set': contrib['user']},
                'name_s': {'set': contrib['user']},
                'contribs_f': {'set': contrib['contribs']},
                'entities_txt': {'set': doc['entities_txt']},
                'authority_f': {'set': doc['authority_f']}
            })

            doc['users_txt'] = {'set': users_txt}
            doc['user_ids_is'] = {'set': user_ids_is}
            doc['total_contribs_f'] = {'set': total_contribs_f}

    update_docs = docs + author_pages
    collection_for_wiki(wiki_data['id']).add(update_docs)


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

    wiki_data = items[wiki_id]

    collection = collection_for_wiki(wiki_id)
    exists = False
    try:
        exists = collection.exists()
    except KeyError:
        pass

    if not exists:
        collection.create()

    use_caching(is_read_only=True, shouldnt_compute=True)

    wpe = WikiPageToEntitiesService().get_value(wiki_id)
    if not wpe:
        print u"NO WIKI PAGE TO ENTITIES SERVICE FOR", wiki_id
        return False

    documents = []

    grouped_futures = []

    for counter, (doc_id, entity_data) in enumerate(wpe.items()):
        documents.append({
            'id': doc_id,
            'entities_txt': {'set': list(set(entity_data.get(u'redirects', {}).values() + entity_data.get(u'titles')))},
            'type_s': {'set': 'Page'}
        })

        if counter % 1500 == 0:
            print counter
            grouped_futures.append(
                group(add_with_metadata.s(wiki_data, grouping) for grouping in iter_grouper(15, documents))()
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

    collection.commit()

    wiki_data['entities_txt'] = []
    for count, entities in CombinedWikiEntitiesService().get(wiki_id):
        for entity in entities:
            map(wiki_data['entities_txt'].append, [entity] * count)


    all_user_ids = []
    all_users = []
    for page_doc in get_all_docs_by_query(collection, 'type_s:Page', fields=['users_txt', 'user_ids_s']):
        map(all_user_ids.append, page_doc['user_ids_is'])
        map(all_users.append, page_doc['users_txt'])

    wiki_data['user_ids_is'] = {'set': list(set(all_user_ids))}
    wiki_data['users_txt'] = {'set': list(set(all_users))}

    # next steps:
    # * Need to create User document for Wiki core by aggregating PageUsers
    # * Will need to create a separate task for creating global user documents I think
    #


    wiki_collection = global_collection()

    WikiEntitiesService.get()

    wiki_collection.add(wiki_data)
    wiki_collection.commit()