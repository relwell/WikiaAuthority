from celery import shared_task
import requests
import traceback
import redis


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
def get_contributing_authors(wiki_id, title_object, title_revs,
                             minimum_authors=5,
                             minimum_contribution_pct=0.05,
                             smoothing=0.05):
    """
    Retrieves the contributing authors for a wiki and its associated page

    :param wiki_id: the integer ID for the wiki
    :type wiki_id: int
    :param title_object: the object associaited with that title as retrieved from the API
    :type title_object: dict
    :param title_revs: a list of revision dicts
    :type title_revs: list
    :param minimum_authors: the minimum number of authors we should retrieve
    :type minimum_authors: int
    :param minimum_contribution_pct: authors with a contribution percentage less than this will be ignored
    :type minimum_contribution_pct: float
    :param smoothing: a smoothing param for handling zeros in the calculation
    :type smoothing: float
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

    """
    I should break this into a celery task so we can
    paralellize requests to the mediawiki API.
    It should return the edit longevity for each revision.
    Then we should add that value to each revision.
    """
    for i in range(0, len(title_revs)):
        curr_rev = title_revs[i]
        if i == 0:
            edit_dist = 1
        else:
            prev_rev = title_revs[i-1]
            if u'revid' not in curr_rev or u'revid' not in prev_rev:
                continue

            edit_dist = edit_distance(title_object, prev_rev[u'revid'], curr_rev[u'revid'])

        non_author_revs_comps = [(title_revs[j-1], title_revs[j]) for j in range(i+1, len(title_revs[i+1:i+11]))
                                 if title_revs[j].get(u'user', u'') != curr_rev.get(u'user')]

        avg_edit_qty = (sum(map(lambda x: edit_quality(title_object, x[0], x[1]), non_author_revs_comps))
                        / max(1, len(set([non_author_rev_cmp[1].get(u'user', u'') for non_author_rev_cmp in
                                          non_author_revs_comps]))))
        if avg_edit_qty == 0:
            avg_edit_qty = smoothing
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
        if author[u'contrib_pct'] < minimum_contribution_pct and len(top_authors) >= minimum_authors:
            break
        top_authors += [author]
    return doc_id, top_authors


@shared_task
def edit_distance(title_object, earlier_revision, later_revision, already_retried=False):

    # replace edit distance memoization cache with redis since we're gonna use redis
    global api_url, edit_distance_memoization_cache

    r = redis.StrictRedis(host='localhost', port=6379, db=0)

    if (earlier_revision, later_revision) in edit_distance_memoization_cache:
        return edit_distance_memoization_cache[(earlier_revision, later_revision)]
    params = {u'action': u'query',
              u'prop': u'revisions',
              u'rvprop': u'ids|user|userid',
              u'rvlimit': u'1',
              u'format': u'json',
              u'rvstartid': earlier_revision,
              u'rvdiffto': later_revision,
              u'titles': title_object[u'title']}

    try:
        resp = requests.get(api_url, params=params)
    except requests.exceptions.ConnectionError as e:
        if already_retried:
            print u"Gave up on some socket shit", e
            return 0
        print u"Fucking sockets"
        time.sleep(240)  # wait four minutes for your wimpy ass sockets to get their shit together
        return edit_distance(title_object, earlier_revision, later_revision, already_retried=True)

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
            edit_distance_memoization_cache[(earlier_revision, later_revision)] = distance
            return distance
        except (TypeError, ParserError, UnicodeEncodeError):
            return 0
    return 0