import argparse
import requests
import xlwt
from datetime import datetime
from boto import connect_s3
from collections import defaultdict
from wikia_authority import MinMaxScaler
from nlp_services.caching import use_caching
from nlp_services.pooling import set_global_num_processes
from nlp_services.authority import WikiAuthorityService, WikiTopicsToAuthorityService, WikiAuthorTopicAuthorityService
from nlp_services.authority import WikiAuthorsToIdsService


def get_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--wiki-id', dest="wiki_id", required=True,
                    help="The ID of the wiki ")
    ap.add_argument('--num-processes', dest="num_processes", default=96,
                    help="Number of processes to run to compute this shiz")
    ap.add_argument('--send-to-s3', dest="send_to_s3", action="store_true", default=False,
                    help="Whether to upload the spreadsheet to S3")
    return ap.parse_args()


def get_all_titles(api_url, apfrom=None, aplimit=500):
    params = {'action': 'query', 'list': 'allpages', 'aplimit': aplimit,
              'apfilterredir': 'nonredirects', 'format': 'json'}
    if apfrom is not None:
        params['apfrom'] = apfrom
    resp = requests.get(api_url, params=params)
    response = resp.json()
    resp.close()
    allpages = response.get('query', {}).get('allpages', [])
    if 'query-continue' in response:
        return allpages + get_all_titles(api_url,
                                         apfrom=response['query-continue']['allpages']['apfrom'], aplimit=aplimit)
    return allpages


def get_api_data(wiki_id):
    return requests.get('http://www.wikia.com/api/v1/Wikis/Details',
                        params=dict(ids=wiki_id)).json()['items'][wiki_id]


def get_page_authority(api_data):
    num_pages = api_data['stats']['articles']
    print "Getting Title Data for %d Pages" % num_pages
    page_ids_to_title = {}
    for obj in get_all_titles(api_data['url']+"api.php"):
        page_ids_to_title[obj['pageid']] = obj['title']

    print "Getting Authority Data"
    authority_data = WikiAuthorityService().get_value(str(api_data['id']))

    print "Cross-Referencing Authority Data"
    return sorted([(page_ids_to_title[int(z[0].split('_')[-1])], z[1])
                   for z in authority_data.items() if int(z[0].split('_')[-1]) in page_ids_to_title],
                  key=lambda y: y[1], reverse=True)


def get_author_authority(api_data):
    print "Getting Topic Authority"
    topic_authority_data = WikiAuthorTopicAuthorityService().get_value(str(api_data['id']))

    print "Correlating Authors to Topics"
    authors_to_topics = sorted(topic_authority_data['weighted'].items(),
                               key=lambda y: sum(y[1].values()),
                               reverse=True)

    print "Correlating Authors to IDs"
    a2ids = WikiAuthorsToIdsService().get_value(str(api_data['id']))

    print "Authors to Topics to ID"
    authors_dict = defaultdict(dict)
    authors_dict.update(dict([(x[0], dict(name=x[0],
                                          total_authority=sum(x[1].values()),
                                          topics=sorted(x[1].items(), key=lambda z: z[1], reverse=True)))
                              for x in authors_to_topics]))

    print "Getting Author Data from API"
    user_strs = [str(a2ids[user]) for user, contribs in authors_to_topics]
    user_api_data = []
    for i in range(0, len(user_strs), 100):
        user_api_data += requests.get(api_data['url']+'/api/v1/User/Details',
                                      params={'ids': ','.join(user_strs[i:i+100]),
                                      'format': 'json'}).json()['items']

    print "Adding that Data"
    for user_data in user_api_data:
        if user_data['name'] in authors_dict:
            authors_dict[user_data['name']].update(user_data)
            authors_dict[user_data['name']]['url'] = authors_dict[user_data['name']]['url'][1:]

    print "Sorting Author Objects"
    author_objects = sorted(authors_dict.values(), key=lambda z: z.get('total_authority', 0), reverse=True)
    return author_objects


def main():
    use_caching()
    args = get_args()
    set_global_num_processes(args.num_processes)
    api_data = get_api_data(args.wiki_id)

    workbook = xlwt.Workbook()
    pages_sheet = workbook.add_sheet("Pages by Authority")
    pages_sheet.write(0, 0, "Page")
    pages_sheet.write(0, 1, "Authority")

    print "Getting Page Data..."
    page_authority = get_page_authority(api_data)

    print "Writing Page Data..."
    pages, authorities = zip(*page_authority)
    scaler = MinMaxScaler(authorities, enforced_min=0, enforced_max=100)
    for i, page in enumerate(pages):
        if i > 65000:
            break
        pages_sheet.write(i+1, 0, page)
        pages_sheet.write(i+1, 1, scaler.scale(authorities[i]))

    print "Getting Author and Topic Data..."
    author_authority = get_author_authority(api_data)
    topic_authority = sorted(WikiTopicsToAuthorityService().get_value(args.wiki_id),
                             key=lambda y: y[1]['authority'], reverse=True)

    print "Writing Author Data..."
    authors_sheet = workbook.add_sheet("Authors by Authority")
    authors_sheet.write(0, 0, "Author")
    authors_sheet.write(0, 1, "Authority")

    authors_topics_sheet = workbook.add_sheet("Topics for Best Authors")
    authors_topics_sheet.write(0, 0, "Author")
    authors_topics_sheet.write(0, 1, "Topic")
    authors_topics_sheet.write(0, 2, "Rank")
    authors_topics_sheet.write(0, 3, "Score")

    # why is total_authority not there?
    all_total_authorities = [author.get('total_authority', 0) for author in author_authority]
    scaler = MinMaxScaler(all_total_authorities, enforced_min=0, enforced_max=100)
    pivot_counter = 1
    for i, author in enumerate(author_authority):
        authors_sheet.write(i+1, 0, author['name'])
        authors_sheet.write(i+1, 1, scaler.scale(author['total_authority']))
        for rank, topic in enumerate(author['topics'][:10]):
            if pivot_counter > 65000:
                break
            authors_topics_sheet.write(pivot_counter, 0, author['name'])
            authors_topics_sheet.write(pivot_counter, 1, topic[0])
            authors_topics_sheet.write(pivot_counter, 2, rank+1)
            authors_topics_sheet.write(pivot_counter, 3, topic[1])
            pivot_counter += 1
        if i > 65000:
            break

    print "Writing Topic Data"
    topics_sheet = workbook.add_sheet("Topics by Authority")
    topics_sheet.write(0, 0, "Topic")
    topics_sheet.write(0, 1, "Authority")

    topics_authors_sheet = workbook.add_sheet("Authors for Best Topics")
    topics_authors_sheet.write(0, 0, "Topic")
    topics_authors_sheet.write(0, 1, "Author")
    topics_authors_sheet.write(0, 2, "Rank")
    topics_authors_sheet.write(0, 3, "Authority")

    scaler = MinMaxScaler([x[1].get('authority', 0) for x in topic_authority], enforced_min=0, enforced_max=100)
    pivot_counter = 1
    for i, topic in enumerate(topic_authority):
        topics_sheet.write(i+1, 0, topic[0])
        topics_sheet.write(i+1, 1, scaler.scale(topic[1]['authority']))
        authors = topic[1]['authors']
        for rank, author in enumerate(authors[:10]):
            if pivot_counter > 65000:
                break
            topics_authors_sheet.write(pivot_counter, 0, topic[0])
            topics_authors_sheet.write(pivot_counter, 1, author['author'])
            topics_authors_sheet.write(pivot_counter, 2, rank+1)
            topics_authors_sheet.write(pivot_counter, 3, author['topic_authority'])
            pivot_counter += 1

        if i > 65000:
            break

    print "Saving to Excel"
    wiki_name = api_data['url'].replace('http://', '').replace('.wikia', '').replace('.com/', '')
    fname = "%s-%s-authority-data-%s.xls" % (args.wiki_id, wiki_name,
                                             datetime.strftime(datetime.now(), '%Y-%m-%d-%H-%M'))
    workbook.save(fname)

    if args.send_to_s3:
        bucket = connect_s3().get_bucket('nlp-data')
        k = bucket.new_key('authority/%s/%s' % (args.wiki_id, fname))
        k.set_contents_from_fiename(fname)

    print fname


if __name__ == '__main__':
    main()