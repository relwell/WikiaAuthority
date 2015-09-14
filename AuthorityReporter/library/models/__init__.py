from wikia_dstk.authority import get_db_and_cursor
from collections import OrderedDict
import requests
import xlwt
from nlp_services.caching import use_caching
from AuthorityReporter.library import solr
from celery import shared_task


class BaseModel():
    """
    Base class for models
    """

    def __init__(self, args):
        """
        Initializes db and cursor

        :param args: a namespace object with db connection data
        :type args: argparse.Namespace
        """
        self.db, self.cursor = get_db_and_cursor(args)


@shared_task
def get_page_response(tup):
    current_url, ids = tup
    response = requests.get(u'%s/api/v1/Articles/Details' % current_url, params=dict(ids=u','.join(ids)))
    return current_url, dict(response.json().get(u'items', {}))


class TopicModel(BaseModel):

    """
    Provides logic for interacting with a given topic
    """

    def __init__(self, topic, args):
        """
        Init method

        :param topic: the topic
        :type topic: str
        :param args: the argparse namespace w/ db info
        :type args: argparse.Namespace

        """
        self.topic = topic
        BaseModel.__init__(self, args)

    def get_pages(self, limit=10, offset=None, for_api=False):
        """
        Gets most authoritative pages for a topic using Authority DB and Wikia API data

        :param limit: Number of results we want
        :type limit: int
        :param offset: offset
        :type offset: int
        :param for_api: if it's for the api, we add less
        :type for_api: bool

        :return: a list of objects reflecting page results
        :rtype: list
        """

        collection = solr.all_pages_collection()
        return solr.get_docs_by_query_with_limit(collection,
                                                 self.topic,
                                                 limit=limit,
                                                 offset=offset,
                                                 boost='scaled_authority_f')

    def get_wikis(self, limit=10, offset=0, for_api=False):
        """
        Gets wikis for the current topic

        :param limit: the number of wikis we want
        :type limit: int
        :param offset: offset
        :type offset: int
        :param for_api: if it's for the api, we add less
        :type for_api: bool

        :return: a dict with keys for wikis (objects) and wiki ids (ints) for ordering or an ordered list of dicts
        :rtype: dict|list
        """

        collection = solr.global_collection()
        return solr.get_docs_by_query_with_limit(collection,
                                                 self.topic,
                                                 limit=limit,
                                                 offset=offset,
                                                 boost='scaled_authority_f')

    def get_users(self, limit=10, offset=0, for_api=False):
        """
        Gets users for a given topic

        :param limit: the number of users we want
        :type limit: int
        :param offset: offset
        :type offset: int
        :param for_api: if it's for the api, we add less
        :type for_api: bool

        :return: a list of objects related to authors
        :rtype: list
        """

        collection = solr.user_collection()
        return solr.get_docs_by_query_with_limit(collection,
                                                 self.topic,
                                                 limit=limit,
                                                 offset=offset,
                                                 boost='scaled_authority_f')


class WikiModel(BaseModel):
    """
    Logic for a given wiki
    """
    def __init__(self, wiki_id, args):
        """
        Initialized Wiki model

        :param wiki_id: The ID of the wiki
        :type wiki_id: int
        :param args: arguments from command line
        :type args: argparse.Namespace

        """
        self.wiki_id = wiki_id
        self.args = args  # stupid di
        self._api_data = None
        BaseModel.__init__(self, args)

    @property
    def api_data(self):
        """
        Memoized lazy-loaded property access

        :getter: Returns data about this wiki pulled from the Wikia API
        :type: string
        """
        if not self._api_data:
            self._api_data = requests.get(u'http://www.wikia.com/api/v1/Wikis/Details',
                                          params=dict(ids=self.wiki_id)).json()[u'items'][self.wiki_id]
        return self._api_data

    def get_row(self):
        """
        Gets the database for this wiki

        :rtype: dict
        :return: a dict representing the row and its column titles
        """
        collection = solr.global_collection()
        for doc in solr.get_all_docs_by_query(collection, 'id:%s' % str(self.wiki_id)):
            return doc

    def get_topics(self, limit=10, offset=None, for_api=False):
        """
        Get topics for this wiki

        :param limit: number of topics to get
        :type limit: int|None
        :param offset: offset
        :type offset: int
        :param for_api: if it's for the api, we add less
        :type for_api: bool

        :return: a list of dicts
        :rtype: list
        """

        return solr.get_docs_by_query_with_limit(solr.collection_for_wiki(self.wiki_id),
                                                 'type_s:Topic',
                                                 limit=limit,
                                                 ofset=offset,
                                                 sort='total_authority_f desc')

    def get_all_authors(self):
        """
        Optimized to get all authors

        :return: an OrderedDict with author dicts
        :rtype: collections.OrderedDict
        """

        return solr.get_all_docs_by_query(solr.wiki_user_collection(), 'wiki_id_i:%s' % self.wiki_id);

    def get_authors(self, limit=10, offset=None, for_api=False):
        """
        Provides the top authors for a wiki

        :param limit: number of authors you want
        :type limit: int
        :param offset: offset
        :type offset: int
        :param for_api: if it's for the api, we add less
        :type for_api: bool

        :return: list of author dicts
        :rtype: list
        """

        solr.get_docs_by_query_with_limit(solr.wiki_user_collection(),
                                          'wiki_id_i:%s' % self.wiki_id,
                                          limit=limit,
                                          offset=offset,
                                          sort='total_page_authority_f desc')

    def get_pages(self, limit=10, offset=None, for_api=False):
        """
        Gets most authoritative pages for this wiki

        :param limit: the number of pages you want
        :type limit: int
        :param offset: offset
        :type offset: int
        :param for_api: if it's for the api, we add less
        :type for_api: bool

        :return: a list of page objects if not for api, otherwise an ordereddict
        :rtype: list|OrderedDict
        """

        return solr.get_docs_by_query_with_limit(solr.collection_for_wiki(self.wiki_id),
                                                 'type_s:Page',
                                                 limit=limit,
                                                 offset=offset,
                                                 sort='authority_f desc')

    def get_all_titles(self, apfrom=None, aplimit=500):
        """
        Returns all titles for this wiki

        :param apfrom: starting string
        :type apfrom: unicode
        :param aplimit: number of titles
        :type aplimit: int

        :return: list of pages
        :rtype: list
        """
        params = {u'action': u'query', u'list': u'allpages', u'aplimit': aplimit,
                  u'apfilterredir': u'nonredirects', u'format': u'json'}
        if apfrom is not None:
            params[u'apfrom'] = apfrom
        resp = requests.get(u'%s/api.php' % self.api_data[u'url'], params=params)
        response = resp.json()
        resp.close()
        allpages = response.get(u'query', {}).get(u'allpages', [])
        if u'query-continue' in response:
            return allpages + self.get_all_titles(apfrom=response[u'query-continue'][u'allpages'][u'apfrom'],
                                                  aplimit=aplimit)
        return allpages

    def get_all_pages(self):
        """
        Optimized for all pages

        :return: dict of pages
        :rtype: dict
        """
        return solr.get_all_docs_by_query(solr.collection_for_wiki(self.wiki_id), 'type_s:Page', sort='authority_f')

    @staticmethod
    def all_wikis(args):
        """
        Accesses all wikis from database

        :return: dict keying wiki name to ids
        :rtype: dict
        """
        return solr.get_all_docs_by_query(solr.global_collection(), '*:*', sort='scaled_authority_f')

    # this is deprecated for now
    def get_workbook(self, num_processes=8):
        return 'nope'
        use_caching()
        set_global_num_processes(num_processes)

        workbook = xlwt.Workbook()
        pages_sheet = workbook.add_sheet(u"Pages by Authority")
        pages_sheet.write(0, 0, u"Page")
        pages_sheet.write(0, 1, u"Authority")

        page_authority = self.get_all_pages()

        pages, authorities = zip(*page_authority)
        scaler = MinMaxScaler(authorities, enforced_min=0, enforced_max=100)
        for i, page in enumerate(pages):
            if i > 65000:
                break
            pages_sheet.write(i+1, 0, page)
            pages_sheet.write(i+1, 1, scaler.scale(authorities[i]))

        author_authority = self.get_all_authors().values()

        for counter, author in enumerate(author_authority):
            author[u'topics'] = [topic.topic for topic in
                                 UserModel(author, self.args).get_topics_for_wiki(self.wiki_id, limit=5)]
            if counter > 25:
                break

        topic_authority = self.get_topics(limit=None)
        for counter, topic in enumerate(topic_authority):
            topic[u'authors'] = TopicModel(topic[u'topic'], self.args).get_users(5, for_api=True)
            if counter > 25:
                break

        authors_sheet = workbook.add_sheet(u"Authors by Authority")
        authors_sheet.write(0, 0, u"Author")
        authors_sheet.write(0, 1, u"Authority")

        authors_topics_sheet = workbook.add_sheet(u"Topics for Best Authors")
        authors_topics_sheet.write(0, 0, u"Author")
        authors_topics_sheet.write(0, 1, u"Topic")
        authors_topics_sheet.write(0, 2, u"Rank")
        authors_topics_sheet.write(0, 3, u"Score")

        # why is total_authority not there?
        all_total_authorities = [author.get(u'total_authority', 0) for author in author_authority]
        scaler = MinMaxScaler(all_total_authorities, enforced_min=0, enforced_max=100)
        pivot_counter = 1
        for i, author in enumerate(author_authority):
            print author
            authors_sheet.write(i+1, 0, author[u'name'])
            authors_sheet.write(i+1, 1, scaler.scale(author[u'total_authority']))
            for rank, topic in enumerate(author.get(u'topics', [])[:10]):
                if pivot_counter > 65000:
                    break
                authors_topics_sheet.write(pivot_counter, 0, author[u'name'])
                authors_topics_sheet.write(pivot_counter, 1, topic[0])
                authors_topics_sheet.write(pivot_counter, 2, rank+1)
                authors_topics_sheet.write(pivot_counter, 3, topic[1])
                pivot_counter += 1
            if i > 65000:
                break

        topics_sheet = workbook.add_sheet(u"Topics by Authority")
        topics_sheet.write(0, 0, u"Topic")
        topics_sheet.write(0, 1, u"Authority")

        topics_authors_sheet = workbook.add_sheet(u"Authors for Best Topics")
        topics_authors_sheet.write(0, 0, u"Topic")
        topics_authors_sheet.write(0, 1, u"Author")
        topics_authors_sheet.write(0, 2, u"Rank")
        topics_authors_sheet.write(0, 3, u"Authority")

        scaler = MinMaxScaler([x[1].get(u'authority', 0) for x in topic_authority], enforced_min=0, enforced_max=100)
        pivot_counter = 1
        for i, topic in enumerate(topic_authority):
            topics_sheet.write(i+1, 0, topic[0])
            topics_sheet.write(i+1, 1, scaler.scale(topic[1][u'authority']))
            authors = topic[1][u'authors']
            for rank, author in enumerate(authors[:10]):
                if pivot_counter > 65000:
                    break
                topics_authors_sheet.write(pivot_counter, 0, topic[0])
                topics_authors_sheet.write(pivot_counter, 1, author[u'author'])
                topics_authors_sheet.write(pivot_counter, 2, rank+1)
                topics_authors_sheet.write(pivot_counter, 3, author[u'topic_authority'])
                pivot_counter += 1

            if i > 65000:
                break

        return workbook


class PageModel(BaseModel):
    """
    Logic for a given page
    """

    def __init__(self, wiki_id, page_id, args):
        """
        Init method

        :param wiki_id: the wiki id
        :type wiki_id: int
        :param page_id: the id of the page
        :type page_id: int
        :param args: namespace with db info
        :type args: arparse.Namespace

        """
        BaseModel.__init__(self, args)
        self.page_id = page_id
        self.wiki_id = wiki_id
        self.wiki = WikiModel(wiki_id, args)
        self._api_data = None

    @property
    def api_data(self):
        """
        Memoized lazy-loaded property access

        :getter: returns data about article pulled from the Wikia API
        :type: dict
        """
        if not self._api_data:
            self._api_data = requests.get(u'%sapi/v1/Articles/Details' % self.wiki.api_data[u'url'],
                                          params=dict(ids=self.page_id)).json()[u'items'][self.page_id]
        return self._api_data

    def get_users(self, limit=10, offset=0, for_api=False):
        """
        Get the most authoritative users for this page

        :param limit: the number of users you want
        :type limit: int
        :param offset: offset
        :type offset: int
        :param for_api: if it's for the api, we add less
        :type for_api: bool

        :return: a list of of user dicts in order of authority
        :rtype: list
        """

        return solr.get_docs_by_query_with_limit(
            solr.collection_for_wiki(self.wiki_id),
            'type_s:PageUser AND doc_id_s:%s_%s' % (str(self.wiki_id), str(self.page_id)),
            limit=limit,
            offset=offset,
            boost='contribs_f'
        )

    def get_topics(self, limit=10, offset=0, for_api=False):
        """
        Get the topics for the current page

        :param limit: how much you want fool
        :type limit: int
        :param offset: offset
        :type offset: int
        :param for_api: if it's for the api, we add less
        :type for_api: bool

        :return: a list of strings
        :rtype: list
        """
        return self.get_row()['attr_entities'][offset:offset+limit]

    def get_row(self):
        """
        Returns the row from the DB as a dict

        :return: row data
        :rtype: dict
        """
        for row in solr.get_all_docs_by_query(solr.all_pages_collection(),
                                              'id:%s_%s' % (str(self.page_id), str(self.wiki_id))):
            return row


class UserModel(BaseModel):
    """
    Data model for user
    """

    def __init__(self, user_name, args):
        """
        init method

        :param user_name: the username we care about
        :type user_name: str
        :param args: namespace
        :type args: argparse.Namespace

        """
        BaseModel.__init__(self, args)
        self.user_name = user_name

    def get_pages(self, limit=10, offset=0, for_api=False):
        """
        Gets top pages for this author
        calculated by contribs times global authority

        :param limit: how many you want
        :type limit: int
        :param offset: offset
        :type offset: int
        :param for_api: if it's for the api, we add less
        :type for_api: bool

        :return: a list of dicts
        :rtype: list
        """
        return solr.get_docs_by_query_with_limit(solr.all_user_pages_collection(),
                                                 'name_txt_en:%s' % self.user_name,
                                                 limit=limit,
                                                 offset=offset,
                                                 boost='user_page_authority_f')

    def get_wikis(self, limit=10, offset=0, for_api=False):
        """
        Most important wikis for this user
        Calculated by sum of contribs times global authority

        :param limit: the limit
        :type limit: int
        :param offset: offset
        :type offset: int
        :param for_api: if it's for the api, we add less
        :type for_api: bool

        :return: an ordereddict of wiki ids to wiki dicts, or a list, for API
        :rtype: collections.OrderedDict|list
        """
        return solr.get_docs_by_query_with_limit(solr.wiki_user_collection(),
                                                 'name_txt_en:%s' % self.user_name,
                                                 limit=limit,
                                                 offset=offset,
                                                 boost='scaled_contribs_authority_f')

    def get_topics(self, limit=10, offset=0, for_api=False):
        """
        Gets most important topics for this user

        :param limit: limit
        :type limit: int
        :param offset: offset
        :type offset: int
        :param for_api: if it's for the api, we fix the naming
        :type for_api: bool

        :return: ordered dict of topic name to auth or a list of dicts
        :rtype: collections.OrderedDict|list
        """
        self.get_row()['attr_entities']

    def get_topics_for_wiki(self, wiki_id, limit=10, offset=0, for_api=False):
        """
        Gets most important topics for this user on this wiki

        :param limit: the wiki id
        :type limit: str
        :param limit: limit
        :type limit: int
        :param offset: offset
        :type offset: int
        :param for_api: if it's for the api, we fix the naming
        :type for_api: bool

        :return: ordered dict of topic name to auth or a list of dicts for api
        :rtype: collections.OrderedDict|list
        """
        for doc in solr.get_all_docs_by_query(solr.wiki_user_collection(), 'name_txt_en:"%s"' % self.user_name):
            return doc['attr_entities']

    def get_row(self):
        """
        Returns the row from the DB as a dict

        :return: row data
        :rtype: dict
        """
        for doc in solr.get_all_docs_by_query(solr.user_collection(), 'name_txt_en:"%s"' % self.user_name):
            return doc['attr_entities']


class MinMaxScaler:
    """
    Scales values from 0 to 1 by default
    """

    def __init__(self, vals, enforced_min=0, enforced_max=1):
        """
        Init method

        :param vals: an array of integer values
        :type vals: list
        :param enforced_min: the minimum value in the scaling (default 0)
        :type enforced_min: float
        :param enforced_max: the maximum value in the scaling (default 1)
        :type enforced_max: float
        """
        self.min = float(min(vals))
        self.max = float(max(vals))
        self.enforced_min = float(enforced_min)
        self.enforced_max = float(enforced_max)

    def scale(self, val):
        """
        Returns the scaled version of the value

        :param val: the value you want to scale
        :type val: float

        :return: the scaled version of that value
        :rtype: float
        """
        return (((self.enforced_max - self.enforced_min) * (float(val) - self.min))
                / (self.max - self.min)) + self.enforced_min