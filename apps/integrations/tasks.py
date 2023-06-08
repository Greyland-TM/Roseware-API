from roseware.celery import app
from apps.package_manager.models import ServicePackage
from roseware.utils import make_logger

# set up the logger
logger = make_logger()


# TODO - These task will be called from the package manager after the celery beat task has determined that a package is due
@app.task
def integrations_run_ads(integrations_ads_package_pks):
    logger.info(f'Running integrations ads package for {len(integrations_ads_package_pks)} customers... (Needs to be implemented)')
    return True

@app.task
def integrations_post_webpage(integrations_webpage_package_pks):
    logger.info(f'Running integrations webpage packages for {len(integrations_webpage_package_pks)} customers... (Needs to be implemented)')
    return True

@app.task
def integrations_post_blog(integrations_blog_package_pks): 
    logger.info(f'Running integrations blog packages for {len(integrations_blog_package_pks)} customers... (Needs to be implemented)')
    return True