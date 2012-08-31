import json
import logging
import sherdog
import sys
import webapp2
from google.appengine.api import memcache
from raven import Client

# Init Sentry client for error reporting
client = Client('')


class ScraperHandler(webapp2.RequestHandler):

    """Default handler for all requests to the scraper with memcache and sentry logging support"""

    # Cache all items for one week
    cache_time = 3600 * 24 * 7

    def get_scraped_data(self, scraper, object_type, object_id):

        """Retrieve scraped data, either from memcache or sherdog"""

        # Build a cache key from the object type and id
        cache_key = '%s_%s' % (object_type, object_id)

        # attempt to retrieve object from cache
        cached_object = memcache.get(cache_key)

        # Perform scrape if object not in cache
        if cached_object is None:
            # Scrape sherdog
            scraped_object = scraper(int(object_id))
            # Throw 404 if not found
            if scraped_object is None:
                self.abort(404)
            # Convert scraped object to JSON encoded string
            scraped_object = json.dumps(scraped_object)
            # Store scraped JSON object in cache
            memcache.set(cache_key, scraped_object, self.cache_time)
            # Return the scraped object
            return scraped_object
        else:
            # Return the cached object
            return cached_object

    def get(self, object_type, object_id):

        """Default handler for all get requests"""

        # Set the response headers
        self.response.headers['Content-Type'] = 'application/json'

        # Dict containing all possible scraper combinations
        scrapers = {
            'promotion': {
                'scraper': sherdog.Scraper.scrape_promotion,
                'object_type': 'promotion',
                'object_id': object_id,
            },
            'event': {
                'scraper': sherdog.Scraper.scrape_event,
                'object_type': 'event',
                'object_id': object_id,
            },
            'fighter': {
                'scraper': sherdog.Scraper.scrape_fighter,
                'object_type': 'fighter',
                'object_id': object_id,
            },
        }

        try:
            scraper = scrapers[object_type]
        except KeyError:
            self.abort(404)

        # Scrape the requested object and write it to the response
        scraped_object = self.get_scraped_data(**scraper)
        self.response.write(scraped_object)

    def handle_exception(self, exception, debug):

        """Override the default exception handler to log exceptions to sentry aswell as the appengine log"""

        # Log the exception
        logging.exception(exception)

        # Log the error to sentry
        client.capture('Exception',
            exc_info=sys.exc_info(),
            data={
                'sentry.interfaces.Http': {
                    'method': self.request.method,
                    'url': self.request.path_url,
                    'query_string': self.request.query_string,
                    'headers': dict(self.request.headers),
                    'env': dict((
                        ('REMOTE_ADDR', self.request.environ['REMOTE_ADDR']),
                        ('SERVER_NAME', self.request.environ['SERVER_NAME']),
                        ('SERVER_PORT', self.request.environ['SERVER_PORT']),
                    )),
                }
            },
        )

        # Set the response headers
        self.response.headers['Content-Type'] = 'application/json'

        # If the exception is a HTTPException, use its error code.
        # Otherwise use a generic 500 error code.
        if isinstance(exception, webapp2.HTTPException):
            self.response.set_status(exception.code)
        else:
            self.response.set_status(500)

        # Write a simple JSON error msg in the response
        self.response.write(json.dumps({'status': self.response.status, 'error': unicode(exception)}))
