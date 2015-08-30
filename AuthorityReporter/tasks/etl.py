"""
This is all of the tasks related to running an ETL for authority
"""

from boto import connect_s3
from celery import group, shared_task
from AuthorityReporter.app import app
from AuthorityReporter.library import MinMaxScaler
import requests
import traceback
import redis
import time
import json
from lxml import html
from lxml.etree import ParserError
from pygraph.classes.digraph import digraph
from pygraph.algorithms.pagerank import pagerank
from pygraph.classes.exceptions import AdditionError


@shared_task
def links_for_page(title, api_url):
    """
    Retrieves all links for a given page based on its title

    :param title: the title string for a page
    :type title: str
    :param api_url: the URL for the Mediawiki API we're hitting -- wiki specific
    :type api_url: str
    :return: a tuple containing the title and its associated links
    :rtype: tuple
    """
    params = {u'action': u'query', u'titles': title_string.encode(u'utf8'), u'plnamespace': 0,
              u'prop': u'links', u'pllimit': 500, u'format': u'json'}
    links = []
    while True:
        resp = requests.get(api_url, params=params)
        try:
            response = resp.json()
        except ValueError as e:
            print e, traceback.format_exc()
            print resp.content
            return title, links
        resp.close()
        response_links = response.get(u'query', {}).get(u'pages', {0: {}}).values()[0].get(u'links', [])
        links += [link[u'title'] for link in response_links]
        query_continue = response.get(u'query-continue', {}).get(u'links', {}).get(u'plcontinue')
        if query_continue is not None:
            params[u'plcontinue'] = query_continue
        else:
            break
    return title, links


@shared_task
def get_contributing_authors(wiki_id, api_url, title_object, title_revs):
    """
    Retrieves the contributing authors for a wiki and its associated page

    :param wiki_id: the integer ID for the wiki
    :type wiki_id: int
    :param api_url: the api URL for the wiki we're working with
    :type api_url: str
    :param title_object: the object associaited with that title as retrieved from the API
    :type title_object: dict
    :param title_revs: a list of revision dicts
    :type title_revs: list

    :return: a tuple of doc id and author objects
    :type: tuple
    """

    # create an independent session for this request
    requests.Session().mount(u'http://',
                             requests.adapters.HTTPAdapter(pool_connections=1, pool_maxsize=1, pool_block=True))

    doc_id = "%s_%s" % (str(wiki_id), title_object[u'pageid'])
    top_authors = []
    if len(title_revs) == 1 and u'user' in title_revs[0]:
        return doc_id, []

    for i in range(0, len(title_revs)):
        curr_rev = title_revs[i]
        if i == 0:
            edit_dist = 1
        else:
            prev_rev = title_revs[i-1]
            if u'revid' not in curr_rev or u'revid' not in prev_rev:
                continue

            edit_dist = edit_distance(wiki_id, api_url, title_object, prev_rev[u'revid'], curr_rev[u'revid'])

        non_author_revs_comps = [(title_revs[j-1], title_revs[j]) for j in range(i+1, len(title_revs[i+1:i+11]))
                                 if title_revs[j].get(u'user', u'') != curr_rev.get(u'user')]

        avg_edit_qty = (sum(map(lambda x: edit_quality(wiki_id, api_url, title_object, x[0], x[1]), non_author_revs_comps))
                        / max(1, len(set([non_author_rev_cmp[1].get(u'user', u'') for non_author_rev_cmp in
                                          non_author_revs_comps]))))
        avg_edit_qty += app.config['ETL_SMOOTHING']
        curr_rev[u'edit_longevity'] = avg_edit_qty * edit_dist

    authors = filter(lambda x: x[u'userid'] != 0 and x[u'user'] != u'',
                     dict([(title_rev.get(u'userid', 0),
                            {u'userid': title_rev.get(u'userid', 0), u'user': title_rev.get(u'user', u'')}
                            ) for title_rev in title_revs]).values()
                     )

    for author in authors:
        author[u'contribs'] = sum([title_rev[u'edit_longevity'] for title_rev in title_revs
                                  if title_rev.get(u'userid', 0) == author.get(u'userid', 0)
                                  and u'edit_longevity' in title_rev and title_rev[u'edit_longevity'] > 0])

    authors = filter(lambda x: x.get(u'contribs', 0) > 0, authors)

    all_contribs_sum = sum([a[u'contribs'] for a in authors])

    for author in authors:
        author[u'contrib_pct'] = author[u'contribs']/all_contribs_sum

    for author in sorted(authors, key=lambda x: x[u'contrib_pct'], reverse=True):
        if u'user' not in author:
            continue
        if (author[u'contrib_pct'] < app.config['ETL_MIN_CONTRIB_PCT']
                and len(top_authors) >= app.config['ETL_MIN_AUTHORS']):
            break
        top_authors.append(author)
    return doc_id, top_authors


def edit_quality(wiki_id, api_url, title_object, revision_i, revision_j):
    """
    Calculates the edit quality of a title for two revisions

    :param wiki_id: the integer ID for the wiki
    :type wiki_id: int
    :param api_url: the api URL for the wiki we're working with
    :type api_url: str
    :param title_object: the title object from the mw api
    :type title_object: dict
    :param revision_i: a given revision for that title
    :type revision_i: dict
    :param revision_j: another comparable revision for that title
    :type revision_j: dict

    :return: an integer value of -1 or 1
    :rtype: int
    """

    numerator_a = edit_distance(wiki_id, api_url, title_object, revision_i[u'parentid'], revision_j[u'revid'])
    numerator_b = edit_distance(wiki_id, api_url, title_object, revision_i[u'revid'], revision_j[u'revid'])
    denominator = edit_distance(wiki_id, api_url, title_object, revision_i[u'parentid'], revision_i[u'revid'])

    numerator = (numerator_a - numerator_b)

    val = numerator if denominator == 0 or numerator == 0 else numerator / denominator
    return -1 if val < 0 else 1  # must be one of[-1, 1]


@shared_task
def edit_distance(wiki_id, api_url, title_object, earlier_revision, later_revision):
    """
    Returns edit distance for two revisions and a title for a given wiki ID

    :param wiki_id: the integer ID for the wiki
    :type wiki_id: int
    :param api_url: the api URL for the wiki we're working with
    :type api_url: str
    :param title_object: the title object we've already retrieved from the API
    :type title_object: dict
    :param earlier_revision: the first revision we care about, could be str or int, i forget
    :type earlier_revision: str
    :param later_revision: the second revision we care about, could be str or int, i forget
    :type later_revision: int

    :return: the edit distance between the two reivsions expressed as a float
    :rtype: float
    """
    r = redis.StrictRedis(host=app.config['REDIS_HOST'], port=app.config['REDIS_PORT'], db=app.config['REDIS_DB'])
    key = "%s_%s_%s_%s" % (wiki_id, title_object[u'pageid'], str(earlier_revision), str(later_revision))
    print key
    result = r.get(key)
    if result is not None:
        return float(result)

    params = {u'action': u'query',
              u'prop': u'revisions',
              u'rvprop': u'ids|user|userid',
              u'rvlimit': u'1',
              u'format': u'json',
              u'rvstartid': earlier_revision,
              u'rvdiffto': later_revision,
              u'titles': title_object[u'title']}

    resp = requests.get(api_url, params=params)

    try:
        response = resp.json()
    except ValueError as e:
        print e, traceback.format_exc()
        print resp.content
        return 0
    resp.close()
    time.sleep(0.025)  # prophylactic throttling
    revision = (response.get(u'query', {})
                        .get(u'pages', {0: {}})
                        .get(unicode(title_object[u'pageid']), {})
                        .get(u'revisions', [{}])[0])
    revision[u'adds'], revision[u'deletes'], revision[u'moves'] = 0, 0, 0
    distance = 0
    if (u'diff' in revision and u'*' in revision[u'diff']
       and revision[u'diff'][u'*'] != '' and revision[u'diff'][u'*'] is not False
       and revision[u'diff'][u'*'] is not None):
        try:
            diff_dom = html.fromstring(revision[u'diff'][u'*'])
            deleted = [word for span in diff_dom.cssselect(u'td.diff-deletedline span.diffchange-inline')
                       for word in span.text_content().split(' ')]
            added = [word for span in diff_dom.cssselect(u'td.diff-addedline span.diffchange-inline')
                     for word in span.text_content().split(' ')]
            adds = sum([1 for word in added if word not in deleted])
            deletes = sum([1 for word in deleted if word not in added])
            moves = sum([1 for word in added if word in deleted])
            changes = revision[u'adds']+revision[u'deletes']+revision[u'moves']  # bad approx. of % of document
            if changes > 0:
                moves /= changes
            distance = max([adds, deletes]) - 0.5 * min([adds, deletes]) + moves
            r.set(key, distance)

        except (TypeError, ParserError, UnicodeEncodeError):
            pass

    return float(distance)


def author_centrality(titles_to_authors):
    """
    Identifies the centrality of an author

    :param titles_to_authors: a dict keying title strings to the authors associated
    :type titles_to_authors: dict

    :return: a dict matching author to centrality
    :rtype: dict
    """
    author_graph = digraph()
    author_graph.add_nodes(map(lambda x: u"title_%s" % x, titles_to_authors.keys()))
    author_graph.add_nodes(list(set([u'author_%s' % author[u'user']
                                     for authors in titles_to_authors.values()
                                     for author in authors])))

    for title in titles_to_authors:
        for author in titles_to_authors[title]:
            try:
                author_graph.add_edge((u'title_%s' % title, u'author_%s' % author[u'user']))
            except AdditionError:
                pass

    centralities = dict([('_'.join(item[0].split('_')[1:]), item[1])
                         for item in pagerank(author_graph).items() if item[0].startswith(u'author_')])

    centrality_scaler = MinMaxScaler(centralities.values())

    return dict([(cent_author, centrality_scaler.scale(cent_val))
                 for cent_author, cent_val in centralities.items()])


def get_all_titles(api_url, aplimit=500):
    """
    Retrieves all titles from the MediaWiki API for that URL

    :param api_url: the URL of the wiki
    :type api_url: str
    :param aplimit: the limit of titles
    :type aplimit: int

    :return: a list of title objects
    :type: list
    """
    params = {u'action': u'query', u'list': u'allpages', u'aplimit': aplimit,
              u'apfilterredir': u'nonredirects', u'format': u'json'}
    allpages = []
    while True:
        resp = requests.get(api_url, params=params)
        response = resp.json()
        resp.close()
        allpages += response.get(u'query', {}).get(u'allpages', [])
        if u'query-continue' in response:
            params[u'apfrom'] = response[u'query-continue'][u'allpages'][u'apfrom']
        else:
            break
    return allpages


@shared_task
def get_all_revisions(api_url, title_object):
    """
    Retrieves all revisions for a given title object and its API url

    :param api_url: the URL of the wiki
    :type api_url: str
    :param title_object: the title object we're working against
    :type title_object: dict

    :return: a two-element list with the title string and its associated revisions
    :rtype: list
    """
    title_string = title_object[u'title']
    params = {u'action': u'query',
              u'prop': u'revisions',
              u'titles': title_string.encode(u'utf8'),
              u'rvprop': u'ids|user|userid',
              u'rvlimit': u'max',
              u'rvdir': u'newer',
              u'format': u'json'}
    revisions = []
    while True:
        resp = requests.get(api_url, params=params)
        try:
            response = resp.json()
        except ValueError as e:
            print e, traceback.format_exc()
            print response.content
            return revisions
        resp.close()
        revisions += response.get(u'query', {}).get(u'pages', {0: {}}).values()[0].get(u'revisions', [])
        if u'query-continue' in response:
            params[u'rvstartid'] = response[u'query-continue'][u'revisions'][u'rvstartid']
        else:
            break
    return [title_string, revisions]


@shared_task
def prime_edit_distance(wiki_id, api_url, title_obj, title_revs):
    return group(
        edit_distance.s(wiki_id, api_url, title_obj, title_revs[i-1][u'revid'], title_revs[i][u'revid'])
        for j in range(1, len(title_revs))
        for i in range(j, len(title_revs))
    )()


def get_title_top_authors(wiki_id, api_url, all_titles, all_revisions):
    """
    Creates a dictionary of titles and its top authors
    :param wiki_id: the ID of the wiki
    :type wiki_id: int
    :param api_url: the API URL of the wiki
    :type api_url: str
    :param all_titles: a list of all title objects
    :type all_titles: list
    :param all_revisions: a dict keying titles to revisions
    :type all_revisions: dict

    :return: a dict keying title to top authors
    :rtype: dict
    """

    print "Initializing edit distance data"

    all_title_len = len(all_titles)
    for i in range(0, all_title_len, 100):
        print "%d/%d" % (i, all_title_len)
        group(prime_edit_distance.s(wiki_id, api_url, title_obj, all_revisions[title_obj[u'title']])
              for title_obj in all_titles[i:i+100])().get()

    print "Getting contributing authors for titles"
    title_to_authors = group(get_contributing_authors.s(wiki_id, api_url, title_obj, all_revisions[title_obj[u'title']])
                             for title_obj in all_titles)().get()

    contribs_scaler = MinMaxScaler([author[u'contribs']
                                    for title, authors in title_to_authors
                                    for author in authors])

    print "Scaling top authors"
    scaled_title_top_authors = {}
    for title, authors in title_to_authors:
        new_authors = []
        for author in authors:
            author[u'contribs'] = contribs_scaler.scale(author[u'contribs'])
            new_authors.append(author)
        scaled_title_top_authors[title] = new_authors
    return scaled_title_top_authors


@shared_task(ignore_result=True)
def set_page_key(x):
    bucket = connect_s3().get_bucket(u'nlp-data')
    k = bucket.new_key(key_name=u'/service_responses/%s/PageAuthorityService.get' % (x[0].replace(u'_', u'/')))
    k.set_contents_from_string(json.dumps(x[1], ensure_ascii=False))


def etl(wiki_id):
    """
    Runs the "api to database" ETL

    Note that we'll be moving to Solr instead of a database
    And note that we should move all these print statements to a logger

    :param wiki_id:
    :return:
    """
    start = time.time()

    # get wiki info
    resp = requests.get(u'http://www.wikia.com/api/v1/Wikis/Details', params={u'ids': wiki_id})
    items = resp.json()['items']
    if wiki_id not in items:
        print u"Wiki doesn't exist?"
        return

    wiki_data = items[wiki_id]
    resp.close()
    print wiki_data[u'title'].encode(u'utf8')
    api_url = u'%sapi.php' % wiki_data[u'url']

    # can't be parallelized since it's an enum
    all_titles = get_all_titles(api_url)
    print u"Got %d titles" % len(all_titles)

    results = group(get_all_revisions.s(api_url, title) for title in all_titles)()
    all_revisions = results.get()

    print u"%d Revisions" % sum([len(revs) for title, revs in all_revisions])
    all_revisions = dict(all_revisions)

    title_top_authors = get_title_top_authors(wiki_id, api_url, all_titles, all_revisions)

    print time.time() - start

    print "Calculating Centrality"
    centralities = author_centrality(title_top_authors)

    # this com_qscore_pr, the best metric per Qin and Cunningham
    comqscore_authority = dict([(doc_id,
                                 sum([author[u'contribs'] * centralities[author[u'user']]
                                      for author in authors])
                                 ) for doc_id, authors in title_top_authors.items()])

    print u"Got comsqscore, storing data"

    bucket = connect_s3().get_bucket(u'nlp-data')
    key = bucket.new_key(key_name=u'service_responses/%s/WikiAuthorCentralityService.get' % wiki_id)
    key.set_contents_from_string(json.dumps(centralities, ensure_ascii=False))

    key = bucket.new_key(key_name=u'service_responses/%s/WikiAuthorityService.get' % wiki_id)
    key.set_contents_from_string(json.dumps(comqscore_authority, ensure_ascii=False))

    group(set_page_key.s(x) for x in title_top_authors.items())().get()

    print wiki_id, u"finished in", time.time() - start, u"seconds"

