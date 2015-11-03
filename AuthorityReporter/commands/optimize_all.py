from flask.ext.script import Command, Option
from AuthorityReporter.library import solr


class OptimizeAll(Command):
    """
    Optimize all indices to fix file descriptor BS
    """

    def run(self):
        """
        Drops all indices
        """
        global_coll = solr.global_collection()
        for doc in solr.get_all_docs_by_query(global_coll, '*:*', fields='id'):
            solr.collection_for_wiki(doc['id']).optimize()
        global_coll.optimize()
        solr.all_pages_collection().optimize()
        solr.all_topics_collection().optimize()
        solr.all_user_pages_collection().optimize()
        solr.wiki_user_collection().optimize()
        solr.user_collection().optimize()
