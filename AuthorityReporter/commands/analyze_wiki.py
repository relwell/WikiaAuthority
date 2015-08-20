from flask.ext.script import Command, Option
from wikia_authority import tasks


class AnalyzeWiki(Command):
    """
    Responsible for analyzing a wiki using the Flask app's Celery config
    """

    option_list = (
        Option('--wiki-id', '-w', dest='wiki_id'),
    )

    def run(self, wiki_id):
        """
        Performs analysis of a wiki using Celery to handle the hard stuff.

        :param wiki_id: the ID of the wiki
        :type wiki_id: str
        :return:
        """
        print tasks.test.s(wiki_id).apply_async().get()
