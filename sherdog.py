"""
    A simple scraper to retrieve data from sherdog.py
    in a predictable/easily machine readable format

    Copyright (c) 2012, Patrick Carey

    Permission to use, copy, modify, and/or distribute this software for any
    purpose with or without fee is hereby granted, provided that the above
    copyright notice and this permission notice appear in all copies.

    THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
    WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
    MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
    ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
    WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
    ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF OR
    IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
"""

import datetime
import re
from BeautifulSoup import BeautifulSoup
from google.appengine.api import urlfetch


class Scraper(object):

    """A collection of functions which can be used to retrieve and parse fight related data from sherdog.com"""

    # Base URL for all requests
    base_url = 'http://www.sherdog.com'

    @classmethod
    def fetch_url(self, url):

        """Fetch a url and return it's contents as a string"""

        uf = urlfetch.fetch(url)
        return uf.content

    @classmethod
    def isNone(self, x):

        """Simple check if an object is None for use in building list comprehensions"""

        if x is not None:
            return False
        else:
            return True

    @classmethod
    def scrape_promotion(self, promotion_id):

        """Retrieve and parse a promotion's details from sherdog.com"""

        # make sure the promotion id is an integer
        promotion_id = int(promotion_id)

        def build_event(ev):

            """Build and return a dictionary containing event information scraped from the promotion page"""

            # get the event's date as a string
            date = ev.find('meta', {'itemprop': 'startDate'})['content'].split('T')[0]

            # if the event is in the future stop parsing and return None
            if datetime.datetime.strptime(date, "%Y-%m-%d") > datetime.datetime.now():
                return None

            # get the event's url
            url = self.base_url + ev['onclick'].replace("document.location='", '').replace("';", '')

            # get the event's id
            event_id = url.rsplit('-', 1)[1]

            # get the event's location
            location = ev.find('td', {'itemprop': 'location'}).contents[-1].lstrip()

            # get the event's name
            name = ''.join(ev.find('span', {'itemprop': 'name'}).contents)

            # build a result dict and return it
            result = {
                'date': date,
                'url': url,
                'id': event_id,
                'location': location,
                'name': name,
            }
            return result

        # fetch the required url and parse it
        url_content = self.fetch_url('%s/organizations/x-%d' % (self.base_url, promotion_id))
        soup = BeautifulSoup(url_content)

        # get the promotion's full name
        try:
            name = soup.find('section', {'itemtype': "http://schema.org/Organization"})
            name = name.find('h2', {'itemprop': 'name'}).contents[0]
        except AttributeError:
            return None

        # get a list of event's held by the promotion
        events = soup.findAll('tr', {'itemtype': "http://schema.org/Event"})
        events = [x for x in (build_event(event) for event in events) if not self.isNone(x)]

        # build a result dict and return it
        result = {
            'name': name,
            'events': events,
        }
        return result

    @classmethod
    def scrape_event(self, event_id):

        """Retrieve and parse an event's details from sherdog.com"""

        # ensure the event_id is an int
        event_id = int(event_id)

        def build_fighter(fghtr):

            """Build and return a dictionary containing fighter information scraped from the event page"""

            # fighter's name
            name = fghtr.find('span', {'itemprop': 'name'}).contents[0]

            # fighter's sherdog url
            url = self.base_url + fghtr.find('a', {'itemprop': 'url'})['href']

            # fighter's sherdog id
            fighter_id = int(url.rsplit('-', 1)[1])

            # fight result
            win = fghtr.find('span', {'class': re.compile("final_result.*")}).contents[0] == 'win'

            # Build result dict and return it
            result = {
                'name': name,
                'url': url,
                'id': fighter_id,
                'win': win,
            }
            return result

        def build_fight(fght):

            """Build and return a dictionary containing fight information scraped from the event page"""

            # fighter details
            fighters_soup = fght.findAll('td', {'itemprop': 'performer'})
            fighters = [build_fighter(fighter) for fighter in fighters_soup]

            # needed to parse further results
            results = fght.findAll('td')

            # method of victory/finish (official decision)
            method = results[-3].contents[0]

            # round in which the fight ended
            end_round = results[-2].contents[0]

            # time in the final round in which the fight ended
            end_time = results[-1].contents[0]

            # build a result dict and return it
            result = {
                'fighters': fighters,
                'method': method,
                'round': end_round,
                'end_time': end_time,
            }
            return result

        # fetch the required url and parse it
        url_content = self.fetch_url('%s/events/x-%d' % (self.base_url, event_id))
        soup = BeautifulSoup(url_content)

        # get the event's details
        event = soup.find('div', {'itemtype': "http://schema.org/Event"})

        # get the event's name
        name = event.find('span', {'itemprop': 'name'}).contents[0]

        # get the event's date
        date = event.find('meta', {'itemprop': 'startDate'})['content'].split('T')[0]

        # get the event's location
        location = event.find('span', {'itemprop': 'location'}).contents[0]

        # get a list of fights from the event and parse it
        fight_soup = soup.findAll('tr', {'itemprop': "subEvent"})
        fights = [build_fight(fight) for fight in fight_soup]

        # build a dict with the scraped data and return it
        result = {
            'name': name,
            'date': date,
            'location': location,
            'fights': fights
        }
        return result

    @classmethod
    def scrape_fighter(self, fighter_id):

        """Retrieve and parse a fighter's details from sherdog.com"""

        # make sure fighter_id is an int
        fighter_id = int(fighter_id)

        # fetch the required url and parse it
        url_content = self.fetch_url('%s/fighter/x-%d' % (self.base_url, fighter_id))
        soup = BeautifulSoup(url_content)

        # get the fighter's name
        name = soup.find('h1', {'itemprop': 'name'}).span.contents[0]

        # get the fighter's birth date
        try:
            birth_date = soup.find('span', {'itemprop': 'birthDate'}).contents[0]
        except AttributeError:
            birth_date = None

        # get the fighter's locality
        try:
            locality = soup.find('span', {'itemprop': 'addressLocality'}).contents[0]
        except AttributeError:
            locality = None

        # get the fighter's height in CM
        try:
            height_cm = soup.find('span', {'class': 'item height'}).contents[-1].lstrip().rstrip().replace(' cm', '')
        except AttributeError:
            height_cm = None

        # get the fighter's weight in KG
        try:
            weight_kg = soup.find('span', {'class': 'item weight'}).contents[-1].lstrip().rstrip().replace(' kg', '')
        except AttributeError:
            weight_kg = None

        # get the fighter's camp/team
        try:
            camp_team = soup.find('h5', {'class': 'item association'}).strong.span.a.span.contents[0]
        except AttributeError:
            camp_team = None

        # build a dict with the scraped data and return it
        result = {
            'name': name,
            'birth_date': birth_date,
            'locality': locality,
            'height_cm': height_cm,
            'weight_kg': weight_kg,
            'camp_team': camp_team,
            'id': fighter_id
        }
        return result
