from celery import shared_task


@shared_task
def test(strang):
    print strang