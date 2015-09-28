CELERY_BROKER_URL = "amqp://guest:guest@127.0.0.1"
REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6379
REDIS_DB = 0
CELERY_RESULT_BACKEND = 'redis://%s:%d/%d' % (REDIS_HOST, REDIS_PORT, REDIS_DB)

# ETL params
ETL_MIN_AUTHORS = 5  # minimum number of authors to care about
ETL_MIN_CONTRIB_PCT = 0.01  # the bottom threshold for contributions
ETL_SMOOTHING = 0.001  # smoothing for zero values

# Solr Params
SOLR_HOSTS = ['localhost:8983', 'localhost:7574']