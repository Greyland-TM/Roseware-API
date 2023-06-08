from apps.package_manager.models import ServicePackage
from apps.integrations.tasks import integrations_run_ads, integrations_post_webpage, integrations_post_blog
from roseware.utils import make_logger

logger = make_logger()

def process_integrations_packages(integrations_packages):
    try:
        # Sort them by type
        integrations_blogs = integrations_packages.filter(type="blog").values_list(flat=True)
        integrations_webpages = integrations_packages.filter(type="webpage").values_list(flat=True)
        integrations_ads = integrations_packages.filter(type="ads").values_list(flat=True)
        logger.info(f'Sorting integrations packages... {integrations_blogs.count()} blogs, {integrations_webpages.count()} webpages, {integrations_ads.count()} ads')

        # TODO - Add more fiters for error handeling

        # Send to the correct tasks
        integrations_post_webpage.delay(list(integrations_webpages))
        integrations_post_blog.delay(list(integrations_blogs))
        integrations_run_ads.delay(list(integrations_ads))
        return True
    except Exception as e:
        logger.info(f'Error: {e}')
    return True

