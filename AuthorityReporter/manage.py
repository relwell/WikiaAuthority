from flask.ext.script import Manager
from app import app
from AuthorityReporter.commands import analyze_wiki, ingest_data

manager = Manager(app)

scripts = {
    'analyze_wiki': analyze_wiki.AnalyzeWiki(),
    'ingest_data': ingest_data.IngestData()
}


if __name__ == "__main__":
    manager.run(scripts)