from flask.ext.script import Manager
from app import app
from AuthorityReporter.commands import analyze_wiki, ingest_data, analyze_global, delete_all, optimize_all

manager = Manager(app)

scripts = {
    'analyze_wiki': analyze_wiki.AnalyzeWiki(),
    'ingest_data': ingest_data.IngestData(),
    'analyze_global': analyze_global.AnalyzeGlobal(),
    'delete_all': delete_all.DeleteAll(),
    'optimize_all': optimize_all.OptimizeAll(),
}


if __name__ == "__main__":
    manager.run(scripts)