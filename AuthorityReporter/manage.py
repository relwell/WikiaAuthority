from flask.ext.script import Manager
from app import app
from AuthorityReporter.commands import analyze_wiki

manager = Manager(app)

scripts = {
    'analyze_wiki': analyze_wiki.AnalyzeWiki()
}


if __name__ == "__main__":
    manager.run(scripts)