from flask.ext.script import Command, Option
from AuthorityReporter.library import solr


class DeleteAll(Command):
    """
    Drops all indices to start fresh
    """

    def run(self):
        """
        Drops all indices
        """
        global_coll = solr.global_collection()
        for doc in solr.get_all_docs_by_query(global_coll, '*:*', fields='id'):
            solr.collection_for_wiki(doc['id']).drop()
        global_coll.drop()
        solr.all_pages_collection().drop()
        solr.all_topics_collection().drop()
        solr.all_user_pages_collection().drop()
        solr.wiki_user_collection().drop()
        solr.user_collection().drop()
