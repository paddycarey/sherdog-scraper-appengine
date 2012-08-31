import webapp2
import handlers

ROUTES = [
    (r'/(\w+)/(\d+)', handlers.ScraperHandler),
    ]
app = webapp2.WSGIApplication(ROUTES, debug=True)
