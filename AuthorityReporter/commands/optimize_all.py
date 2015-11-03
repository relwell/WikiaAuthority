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
        print 'global'
        global_coll.optimize()
        for doc in solr.get_all_docs_by_query(global_coll, '*:*', fields='id'):
            print doc['id']
            solr.collection_for_wiki(doc['id']).optimize()
        print 'all pages'
        solr.all_pages_collection().optimize()
        print 'all topics'
        solr.all_topics_collection().optimize()
        print 'all user pages'
        solr.all_user_pages_collection().optimize()
        print 'wiki user'
        solr.wiki_user_collection().optimize()
        print 'user'
        solr.user_collection().optimize()
