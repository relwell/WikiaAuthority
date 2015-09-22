from flask.ext.script import Command, Option
from AuthorityReporter.tasks.solr import global_ingestion


class AnalyzeGlobal(Command):
    """
    Responsible for analyzing all wikis globall using the Flask app's Celery config
    """

    def run(self):
        """
        Performs analysis of a wiki using Celery to handle the hard stuff.
        """
        global_ingestion()
