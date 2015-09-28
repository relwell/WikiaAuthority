import argparse
import json
import mimetypes
import StringIO

import xlwt
from flask import Flask, render_template, Response, jsonify
from flask.ext import restful
from werkzeug.datastructures import Headers
from nlp_services.caching import use_caching

from library import api
from AuthorityReporter.library.models import TopicModel, WikiModel, UserModel
from celery import Celery


def bootstrap_celery(app):
    """
    Registers celery with the app

    :param app: the flask app

    :return: the Celery context
    """

    # importing here because some tasks refer to app, lol
    from AuthorityReporter.tasks.etl import links_for_page, get_contributing_authors, edit_distance, get_all_revisions
    from AuthorityReporter.tasks.etl import get_title_top_authors, set_page_key
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task
    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)
    celery.Task = ContextTask
    return celery


use_caching()

app = Flask(__name__)
app.config.from_object('AuthorityReporter.default_settings')
try:
    app.config.from_pyfile('/etc/authority/settings.py')
except (IOError, RuntimeError):  # file doesn't exist
    pass

celery = bootstrap_celery(app)

args = None


def excel_response(spreadsheet, filename=u'export.xls'):
    """
    Prepares an excel spreadsheet for response in Flask
    :param spreadsheet: the spreadsheet
    :type spreadsheet:class:`xlwt.Workbook`
    :param filename: the name of the file when downloaded
    :type filename: unicode
    :return: the flask response
    :rtype:class:`flask.Response`
    """
    response = Response()
    response.status_code = 200
    output = StringIO.StringIO()
    spreadsheet.save(output)
    response.data = output.getvalue()
    mimetype_tuple = mimetypes.guess_type(filename)

    #HTTP headers for forcing file download
    response_headers = Headers({
        u'Pragma': u"public",  # required,
        u'Expires': u'0',
        u'Cache-Control': [u'must-revalidate, post-check=0, pre-check=0', u'private'],
        u'Content-Type': mimetype_tuple[0],
        u'Content-Disposition': u'attachment; filename=\"%s\";' % filename,
        u'Content-Transfer-Encoding': u'binary',
        u'Content-Length': len(response.data)
    })

    if not mimetype_tuple[1] is None:
        response_headers.update({u'Content-Encoding': mimetype_tuple[1]})

    response.headers = response_headers
    response.set_cookie(u'fileDownload', u'true', path=u'/')
    return response


@app.route(u'/wiki/<wiki_id>/xls/')
def spreadsheet_for_wiki(wiki_id):
    """
    Generates a spreadsheet with topics, authors, and pages
    """
    global args
    return excel_response(WikiModel(wiki_id).get_workbook(), filename=u'wiki-%s-report.xls' % wiki_id)


@app.route(u'/wiki_autocomplete.js')
def wiki_autocomplete():
    """
    This allows JS typeahead for wikis on the homepage
    """
    global args
    wikis = WikiModel.all_wikis()
    return Response(u"var wikis = %s;" % json.dumps(wikis),
                    mimetype=u"application/javascript",
                    content_type=u"application/javascript")


@app.route(u'/topic/<topic>/wikis/xls/')
def wikis_for_topic_xls(topic):
    global args
    wkbk = xlwt.Workbook()
    wksht = wkbk.add_sheet(topic)
    titles = [u"Wiki ID", u"Wiki Name", u"Wiki URL", u"Authority"]
    response = TopicModel(topic).get_wikis(limit=200)
    keys = [u'id', u'title', u'url', u'authority']
    map(lambda (cell, title): wksht.write(0, cell, title), enumerate(titles))
    map(lambda (row, wiki_id): map(lambda (cell, key): wksht.write(row+1, cell, response[u'wikis'][wiki_id][key]),
                                   enumerate(keys)),
        enumerate(response[u'wiki_ids']))

    return excel_response(wkbk, filename=u"%s-wikis.xls" % topic)

@app.route(u'/topic/<topic>/pages/xls/')
def pages_for_topic_xls(topic):
    """
    Gets the excel download of the best pages for a topic
    """
    global args
    workbook = xlwt.Workbook()
    worksheet = workbook.add_sheet(topic)
    titles = [u"Wiki ID", u"Page ID", u"Wiki Name", u"Page URL", u"Page Title", u"Authority"]
    keys = [u'wiki_id', u'page_id', u'wiki', u'full_url', u'title', u'authority']
    pages = TopicModel(topic).get_pages(1000)
    map(lambda (cell, title): worksheet.write(0, cell, title), enumerate(titles))
    map(lambda (row, page): map(lambda (cell, key): worksheet.write(row+1, cell, page.get(key, u'?')),
                                enumerate(keys)),
        enumerate(pages))
    return excel_response(workbook, filename=u'%s-pages.xls' % topic)


@app.route(u'/topic/<topic>/users/xls/')
def users_for_topic_xls(topic):
    """
    Spreadsheet of users for a topic
    """
    global args
    workbook = xlwt.Workbook()
    worksheet = workbook.add_sheet(topic)
    titles = [u"Name", u"Authority"]
    keys = [u"user_name", u"total_authority"]
    map(lambda (cell, title): worksheet.write(0, cell, title), enumerate(titles))
    users = TopicModel(topic).get_users(limit=1000, for_api=True)
    map(lambda (row, user): map(lambda (cell, key): worksheet.write(row+1, cell, user[key]),
                                enumerate(keys)),
        enumerate(users))
    return excel_response(workbook, filename=u'%s-users.xls' % topic)


@app.route(u'/api/user/<user_name>/wikis/')
def wikis_for_user(user_name):
    """
    Shows the top 10 wikis for a user
    """
    global args
    data = UserModel(user_name).get_wikis(limit=12)
    return render_template(u'wikis_for_user.html', wikis=data, wiki_ids=data.keys(),
                           user_name=user_name)


@app.route('/')
def root():
    return app.send_static_file('index.html')


@app.route('/<path:path>')
def static_proxy(path):
    # send_static_file will guess the correct MIME type
    return app.send_static_file(path)


def main():
    global app, args
    parser = argparse.ArgumentParser(description=u'Authority Flask App')
    parser.add_argument(u'--app-host', dest=u'app_host', action=u'store', default=u'0.0.0.0',
                        help=u"App host")
    parser.add_argument(u'--app-port', dest=u'app_port', action=u'store', default=5000, type=int,
                        help=u"App port")
    args = parser.parse_args()
    app.debug = True
    app_api = restful.Api(app)
    api.register_resources(app_api)
    app.run(host=args.app_host, port=args.app_port)


if __name__ == u'__main__':
    main()
