import sys
import inspect
from flask.ext.restful import reqparse
from flask.ext import restful
from AuthorityReporter.library import solr, models
import solrcloudpy


def register_resources(api):
    """
    Dynamically registers all restful resources in this module with the API

    :param api: the restful API object paired to the flask app
    :type api: restful.Api
    """
    for name, obj in inspect.getmembers(sys.modules[__name__]):
        if inspect.isclass(obj):
            api.add_resource(obj, *obj.urls)


def get_request_parser():
    """
    Parses the request GET params

    :return: a dict with parser args and vals
    :rtype: dict
    """
    parser = reqparse.RequestParser()
    parser.add_argument(u'limit', type=int, help=u'Limit', default=10)
    parser.add_argument(u'offset', type=int, help=u'Offset', default=0)
    parser.add_argument(u'q', type=str, help=u'The Query', default=None)
    return parser


class WikiTopics(restful.Resource):

    urls = [u"/api/wiki/<int:wiki_id>/topics", u"/api/wiki/<int:wiki_id>/topics/"]

    def get(self, wiki_id):
        """
        Access a JSON response for the top topics for the given wiki

        :param wiki_id: the ID of the wiki
        :type wiki_id: int

        :return: the response dict
        :rtype: dict
        """
        request_args = get_request_parser().parse_args()

        return {
            u'wiki_id': wiki_id,
            u'offset': request_args[u'offset'],
            u'limit': request_args[u'limit'],
            u'topics': models.WikiModel(wiki_id).get_topics(**request_args)
        }


class WikiUsers(restful.Resource):

    urls = [u"/api/wiki/<int:wiki_id>/users", u"/api/wiki/<int:wiki_id>/users/"]

    def get(self, wiki_id):
        """
        Access a JSON response for the top users for the given wiki

        :param wiki_id: the ID of the wiki
        :type wiki_id: int

        :return: the response dict
        :rtype: dict
        """
        request_args = get_request_parser().parse_args()
        return {
            u'wiki_id': wiki_id,
            u'offset': request_args[u'offset'],
            u'limit': request_args[u'limit'],
            u'users': models.WikiModel(wiki_id).get_users(**request_args)
        }


class WikiPages(restful.Resource):

    urls = [u"/api/wiki/<int:wiki_id>/pages", u"/api/wiki/<int:wiki_id>/pages/"]

    def get(self, wiki_id):
        """
        Access a JSON response for the top pages for the given wiki

        :param wiki_id: the ID of the wiki
        :type wiki_id: int

        :return: the response dict
        :rtype: dict
        """
        request_args = get_request_parser().parse_args()
        return {
            u"wiki_id": wiki_id,
            u'offset': request_args[u'offset'],
            u'limit': request_args[u'limit'],
            u'pages': models.WikiModel(wiki_id).get_pages(**request_args)
        }


class Hubs(restful.Resource):

    urls = [u"/api/hubs"]

    def get(self):
        return [dict(hub=hub, count=count) for hub, count
                in solr.iterate_per_facetfield_value(solr.global_collection(),
                                                     solrcloudpy.SearchOptions({'q': '*:*'}), 'hub_s')]


class Wiki(restful.Resource):

    urls = [u"/api/wiki/<int:wiki_id>", u"/api/wiki/<int:wiki_id>/"]

    def get(self, wiki_id):
        """
        Access a JSON response representing data for the wiki, including userity

        :param wiki_id: the ID of the wiki
        :type wiki_id: int

        :return: the response dict
        :rtype: dict
        """
        return models.WikiModel(wiki_id).get_row()


class Wikis(restful.Resource):

    urls = [u"/api/wikis/", u"/api/wikis"]

    def get(self):
        """
        Queries for all wikis given a search query

        :return: the response dict
        :rtype: dict
        """
        return models.WikiModel.search(**get_request_parser().parse_args())


class WikiDetails(restful.Resource):

    urls = [u"/api/wiki/<int:wiki_id>/details"]

    def get(self, wiki_id):
        return models.WikiModel(wiki_id).api_data


class UserDetails(restful.Resource):

    urls = [u"/api/user/<string:user_id>/details"]

    def get(self, user_id):
        return models.UserModel(user_id.split('_').pop()).api_data


class Topics(restful.Resource):

    urls = [u"/api/topics/", u"/api/topics"]

    def get(self):
        """
        Queries for all topics given a search query

        :return: the response dict
        :rtype: dict
        """
        return models.TopicModel.search(**get_request_parser().parse_args())


class TopicPages(restful.Resource):

    urls = [u"/api/topic/<string:topic>/pages/", u"/api/topic/<string:topic>/pages"]

    def get(self, topic):
        """
        Access a JSON response for the top pages for the given topic

        :param topic: the topic in question
        :type topic: str

        :return: the response dict
        :rtype: dict
        """
        request_args = get_request_parser().parse_args()
        return {
            u'topic': topic,
            u'limit': request_args[u'limit'],
            u'offset': request_args[u'offset'],
            u'pages': models.TopicModel(topic).get_pages(**request_args)
        }


class TopicWikis(restful.Resource):

    urls = [u"/api/topic/<string:topic>/wikis/", u"/api/topic/<string:topic>/wikis"]

    def get(self, topic):
        """
        Access a JSON response for the top wikis for the given topic

        :param topic: the topic in question
        :type topic: str

        :return: the response dict
        :rtype: dict
        """
        request_args = get_request_parser().parse_args()
        return {
            u'topic': topic,
            u'limit': request_args[u'limit'],
            u'offset': request_args[u'offset'],
            u'wikis': models.TopicModel(topic).get_wikis(**request_args)
        }


class TopicUsers(restful.Resource):

    urls = [u"/api/topic/<string:topic>/users", u"/api/topic/<string:topic>/users/"]

    def get(self, topic):
        """
        Access a JSON response for the top users for the given topic

        :param topic: the topic in question
        :type topic: str

        :return: the response dict
        :rtype: dict
        """
        request_args = get_request_parser().parse_args()
        return {
            u'topic': topic,
            u'limit': request_args[u'limit'],
            u'offset': request_args[u'offset'],
            u'users': models.TopicModel(topic).get_users(**request_args)
        }


class TopicUsers(restful.Resource):

    urls = [u"/api/topic/<string:topic>/users", u"/api/topic/<string:topic>/users/"]

    def get(self, topic):
        """
        Access a JSON response for the top users for the given topic

        :param topic: the topic in question
        :type topic: str

        :return: the response dict
        :rtype: dict
        """
        request_args = get_request_parser().parse_args()
        return {
            u'topic': topic,
            u'limit': request_args[u'limit'],
            u'offset': request_args[u'offset'],
            u'users': models.TopicModel(topic).get_users(**request_args)
        }


class Topic(restful.Resource):

    urls = [u"/api/topic/<string:topic>", u"/api/topic/<string:topic>/"]

    def get(self, topic):
        """
        Access a JSON response representing data for the topic, including userity

        :param topic: the string value of the topic
        :type topic: str

        :return: the response dict
        :rtype: dict
        """
        return models.TopicModel(topic).get_row()


class UserWikis(restful.Resource):

    urls = [u"/api/user/<int:user_id>/wikis/", u"/api/user/<int:user_id>/wikis"]

    def get(self, user_id):
        """
        Access a JSON response for the top wikis for the given user

        :param user_id: the name of the user in question
        :type user_id: int

        :return: the response dict
        :rtype: dict
        """
        request_args = get_request_parser().parse_args()
        return {
            u'user': user_id,
            u'limit': request_args[u'limit'],
            u'offset': request_args[u'offset'],
            u'wikis': models.UserModel(user_id).get_wikis(**request_args)
        }


class UserTopics(restful.Resource):

    urls = [u"/api/user/<int:user_id>/topics/", u"/api/user/<int:user_id>/topics"]

    def get(self, user_id):
        """
        Access a JSON response for the top topics for the given user

        :param user_id: the name of the user in question
        :type user_id: int

        :return: the response dict
        :rtype: dict
        """
        request_args = get_request_parser().parse_args()
        return {
            u'user': user_id,
            u'limit': request_args[u'limit'],
            u'offset': request_args[u'offset'],
            u'topics': models.UserModel(user_id).get_topics(**request_args).values()
        }


class UserPages(restful.Resource):

    urls = [u"/api/user/<int:user_id>/pages/", u"/api/user/<int:user_id>/pages"]

    def get(self, user_id):
        """
        Access a JSON response for the top pages for the given user

        :param user_id: the name of the user in question
        :type user_id: int

        :return: the response dict
        :rtype: dict
        """
        request_args = get_request_parser().parse_args()
        return {
            u'user': user_id,
            u'limit': request_args[u'limit'],
            u'offset': request_args[u'offset'],
            u'pages': models.UserModel(user_id).get_pages(**request_args)
        }


class UserWikiTopics(restful.Resource):

    urls = [
        u"/api/user/<int:user_id>/topics/wiki/<int:wiki_id>",
        u"/api/user/<int:user_id>/topics/wiki/<int:wiki_id>/",
        u"/api/wiki/<int:wiki_id>/topics/user/<int:user_id>/",
        u"/api/wiki/<int:wiki_id>/topics/user/<int:user_id>",
        ]

    def get(self, user_id, wiki_id):
        """
        Access a JSON response for the top topics for the given user and wiki

        :param user_id: the name of the user in question
        :type user_id: int
        :param wiki_id: the id of the wiki
        :type wiki_id: int

        :return: the response dict
        :rtype: dict
        """
        request_args = get_request_parser().parse_args()
        return {
            u'user': user_id,
            u'limit': request_args[u'limit'],
            u'offset': request_args[u'offset'],
            u'topics': models.UserModel(user_id).get_topics_for_wiki(wiki_id, **request_args)
        }


class User(restful.Resource):

    urls = [u"/api/user/<int:user_id>", u"/api/user/<int:user_id>/"]

    def get(self, user_id):
        """
        Access a JSON response representing data for the user, including authority.
        Scaled authority is for comparing users

        :param user_id: the string value of the user
        :type user_id: int

        :return: the response dict
        :rtype: dict
        """
        return models.UserModel(user_id).get_row()


class Users(restful.Resource):

    urls = [u"/api/users/", u"/api/users"]

    def get(self):
        """
        Queries for all users given a search query

        :return: the response dict
        :rtype: dict
        """
        return models.UserModel.search(**get_request_parser().parse_args())


class PageUsers(restful.Resource):

    urls = [u"/api/page/<string:doc_id>/users",
            u"/api/page/<string:doc_id>/users/"]

    def get(self, doc_id):
        """
        Access a JSON response for the top users for the given wiki

        :param doc_id: the id of the document
        :type doc_id: str

        :return: the response dict
        :rtype: dict
        """
        request_args = get_request_parser().parse_args()
        return {
            u'offset': request_args[u'offset'],
            u'limit': request_args[u'limit'],
            u'users': models.PageModel(doc_id).get_users(**request_args)
        }


class PageTopics(restful.Resource):

    urls = [u"/api/page/<string:doc_id>/topics",
            u"/api//page/<string:doc_id>/topics/"]

    def get(self, doc_id):
        """
        Access a JSON response for the top topics for the given page, sorted by total userity

        :param doc_id: the id of the document
        :type doc_id: str

        :return: the response dict
        :rtype: dict
        """
        request_args = get_request_parser().parse_args()
        return {
            u'offset': request_args[u'offset'],
            u'limit': request_args[u'limit'],
            u'topics': models.PageModel(doc_id).get_topics(**request_args)
        }


class Page(restful.Resource):

    urls = [u"/api/page/<string:doc_id>/details",
            u"/api/page/<string:doc_id>/details/"]

    def get(self, doc_id):
        """
        Access a JSON response representing the page, including userity

        :param doc_id: the id of the document
        :type doc_id: str

        :return: the response dict
        :rtype: dict
        """
        wiki_id, article_id = doc_id.split('_')
        return models.PageModel(doc_id).get_row()