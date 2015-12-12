# coding=UTF-8

import re
import traceback

import requests
from bs4 import BeautifulSoup


def as_float(text):
    if text:
        return float(re.sub("[^0-9\,\.]", "", text).replace(",", "."))
    return None


class ServerProblem(Exception):
    pass


class NotFound(Exception):
    pass


def to_soup(url):
    page = requests.get(url)
    if page.status_code >= 500:
        raise ServerProblem(page.status_code)
    if page.status_code >= 400:
        raise NotFound()
    return BeautifulSoup(page.content, "html.parser")


def scrap_orsay_url(url):
    def get_price(element):
        if element:
            return as_float(element.find('span', {"class": "price"}).string)

    soup = to_soup(url)
    soup = soup.find('div', {"class": "product-main-info"})
    return {
        "url": url,
        "regular": get_price(soup.find('span', {"class": "regular-price"})) or get_price(
                soup.find('p', {"class": "old-price"})),
        "discount": get_price(soup.find('p', {"class": "special-price"}))
    }


def flatten_list(l):
    return [item for sublist in l for item in sublist]


class SafetyWrapper(object):
    def __init__(self, f):
        self.f = f

    def __call__(self, url):
        try:
            return self.f(url)
        except NotFound:
            print u"Nie mogę znaleźć adresu " + url
        except (requests.exceptions.ConnectionError, ServerProblem):
            return url
        except Exception, e:
            raise Exception("Failed to fetch %s; %s" % (url, traceback.format_exc()), e)


def scrap():
    from multiprocessing import Pool
    pool = Pool(30)

    with open('urls') as f:
        urls = f.readlines()
    urls = [url.strip() for url in urls if url.strip()]

    details = []
    while urls:
        results = pool.map(SafetyWrapper(scrap_orsay_url), urls)
        details += [result for result in results if isinstance(result, dict)]
        urls = [result for result in results if isinstance(result, unicode) or isinstance(result, str)]

    return details


details = scrap()
regular = [detail for detail in details if not detail["discount"]]
discount = [detail for detail in details if detail["discount"]]

print "W promocji:"
for product in sorted(discount, key=lambda x: x['discount']):
    print "Jest {discount}, było {regular}  - {url}".format(**product)
print "\nPozostałe:"
for product in sorted(regular, key=lambda x: x['regular']):
    print "Cena {regular} - {url}".format(**product)
