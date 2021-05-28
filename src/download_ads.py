import os
import pickle
import sys

from bs4 import BeautifulSoup as BS
from bs4 import NavigableString, Comment
from collections import namedtuple

import \
    urllib.request as urllib2  # using urllib.request bc this script is originally written for python2, and this is the way to run it with python3
from urllib.request import URLError

from time import sleep

from pyparsing import unicode
from tqdm import tqdm

data_folder = """C:/Users/smitric/Desktop/github_projects/nova_kola/"""


class Car:
    def __init__(self, url, brand, model, productionYear=-1, fuel='Unknown', power='Unknown', mileage_in_km=-1):
        self.url = url
        self.brand = brand
        self.model = model
        self.productionYear = productionYear
        self.fuel = fuel
        self.power = power
        self.mileage_in_km = mileage_in_km

    def __str__(self):
        return (self.getBrand() + ' ' + self.getModel() + ', ' + str(self.getProductionYear()) + ' -- ' + str(
            self.getMileage()) + 'km')

    def getUrl(self):
        return self.url

    def setUrl(self, url):
        self.url = url

    def getBrand(self):
        return self.brand

    def setBrand(self, brand):
        self.brand = brand

    def getModel(self):
        return self.model

    def setModel(self, model):
        self.model = model

    def getProductionYear(self):
        return self.productionYear

    def setProductionYear(self, productionYear):
        self.productionYear = productionYear

    def getFuel(self):
        return self.fuel

    def setFuel(self, fuel):
        self.fuel = fuel

    def getPower(self):
        return self.power

    def setPower(self, power):
        self.power = power

    def getMileageInKM(self):
        return self.mileage_in_km

    def setMileageInKM(self, mileage_in_km):
        self.mileage_in_km = mileage_in_km


def save_to_file(data, file_name='cars.pkl'):  # kola.pkl

    import pickle
    f = open(file_name, 'wb')
    pickle.dump(data, f)
    f.close()


def read_cars_array_from_file(file_name='cars_1.pkl'):
    import pickle
    data = {}

    try:
        f = open(file_name, 'rb')
    except Exception as e:
        print('Could not find the ' + file_name + '. Returning empty dict.')
        return {}

    data = pickle.load(f)
    f.close()
    return data


def missing_values_to_None(car_dict):
    params = ['url', 'brand', 'model', 'productionDate', 'fuelType', 'vehicleEngine', 'mileageFromOdometer']

    for p in params:
        if p not in car_dict:
            car_dict[p] = None

    return car_dict


def get_all_urls():
    urls = []
    num_of_pages = 2494  # do ovog broja sam dosao 27/05/2021 jednostavnom pretragom na sajtu
    for page_num in tqdm(range(1, num_of_pages + 1)):
        soup = BS(urllib2.urlopen('https://www.polovniautomobili.com/auto-oglasi/pretraga?page=' + str(
            page_num) + '&sort=basic&city_distance=0&showOldNew=all&without_price=1'), features="html.parser")
        cars = soup.findAll('script', {'type': 'application/ld+json'})

        for car_ in cars:
            car = str(car_)
            if '"@type":"Car",' in car:
                for line in car.split('\n'):
                    if ':' in line:
                        splited = line.split(':')
                        if 'url' in splited[0]:
                            urls.append(line[line.index(':') + 1:].replace('"', '').replace(',', '').strip())

    with open(os.path.join(data_folder, 'urls.pkl'), 'wb') as f:
        pickle.dump(urls, f)

    return urls


def get_characteristics_safety_and_extras_for_soup(soup):
    characteristics_safety_extras = soup.findAll('div', {'class': 'uk-grid js-hidden'})
    if len(characteristics_safety_extras) < 1:
        return None, None
    characteristics_ = characteristics_safety_extras[0]

    characteristics_k = (characteristics_.findAll('div', {'class': 'uk-width-medium-1-4 uk-width-1-2'}))
    characteristics_keys = []
    characteristics_v = (characteristics_.findAll('div', {'class': 'uk-width-medium-1-4 uk-width-1-2 '
                                                                   'uk-text-bold'}))
    characteristics_values = []

    for key in characteristics_k:
        characteristics_keys.append(key.string)
    for value in characteristics_v:
        characteristics_values.append(value.string)

    characteristics_dir = {}
    for pair in list(zip(characteristics_keys, characteristics_values)):
        characteristics_dir[pair[0]] = pair[1]

    if len(characteristics_safety_extras) == 1:
        return characteristics_dir, None

    safety_ = characteristics_safety_extras[1]
    safety_ = safety_.findAll('div', {'class': 'uk-width-medium-1-3 uk-width-1-2'})
    safety = []
    for s in safety_:
        safety.append(s.string)

    if len(characteristics_safety_extras) == 2:
        return characteristics_dir, safety_

    extras_ = characteristics_safety_extras[2]
    extras_ = extras_.findAll('div', {'class': 'uk-width-medium-1-3 uk-width-1-2'})
    extras = []
    for s in extras_:
        extras.append(s.string)

    return characteristics_dir, safety + extras


def basic_car_info(soup):
    scripts = soup.findAll('script', {'type': 'application/ld+json'})

    car_info = [s for s in scripts if '"name": "Polovniautomobili.com",' not in s.string]

    dict_ = {}
    for tag in car_info:
        for line in tag.string.split('\n'):
            if ':' in line:
                if 'logo' not in line and 'url' not in line and 'image' not in line:
                    dict_[line.split(":")[0].replace("\"", "").replace("@", "").strip()] = convert_unicode(
                        line.split(":")[
                            1].replace("\"", "").replace(",", "").strip())
                else:
                    dict_[line.split(":")[0].replace("\"", "").replace("@", "").strip()] = convert_unicode(':'.join(
                        line.split(":")[1:]).replace("\"", "").strip())

    keys = list(dict_.keys())

    for rmv in keys:
        if dict_[rmv] == '{':
            dict_.pop(rmv)
        if 'context' in rmv:
            dict_.pop(rmv)

    return dict_


def convert_unicode(string):
    string = string.replace(r'\u0107', 'c').replace(r'\u0161', 's').replace(r'\u20ac', 'EUR').replace(r'\u010', 'c')

    return string


def save_cars_info(urls, prices):
    print('Getting cars info...')
    sys.setrecursionlimit(500000)
    dict_prices = dict(prices)

    for url in tqdm(urls):
        soup = BS(urllib2.urlopen(url), features="html.parser")
        ch_dir, safety_extras = get_characteristics_safety_and_extras_for_soup(soup)
        car_dict = basic_car_info(soup)

        if url in dict_prices:
            data = (car_dict, ch_dir, safety_extras, dict_prices[url])
        else:
            data = (car_dict, ch_dir, safety_extras, 'price_unknown')

        with open(os.path.join(data_folder, 'car_number_' + str(urls.index(url) + 1)) + '.pkl', 'wb') as f:
            pickle.dump(data, f)


def load_all_setsOf25_and_merge_and_save():
    num_of_pages = 2690
    all_cars = []
    for page_num in range(1, num_of_pages + 1):
        list_ = read_cars_array_from_file('cars/car_' + str(page_num) + '.pkl')
        all_cars = all_cars + list_

    save_to_file(all_cars, 'cars/allCars_Array.pkl')


def loadCars():
    all_cars = read_cars_array_from_file('cars/allCars_Array.pkl')

    all_cars = sorted(all_cars, key=lambda x: x.getMileageInKM(), reverse=True)

    return all_cars


def drawHistogram(all_cars, label='', lower=0, upper=100):
    import matplotlib.pyplot as plt
    kilometraze = list(map(lambda x: x.getMileageInKM(), all_cars))

    plt.hist(kilometraze, bins=(range(10000, 400000, 10000)), rwidth=0.8)
    plt.ylabel('Num of vehicles')
    plt.xlabel('Mileage in kms')
    plt.title(label)
    plt.axis([10000, 400000, lower, upper])
    plt.grid(True)
    plt.show()


def draw_brands(all_cars):
    import matplotlib.pyplot as plt
    brands = list(map(lambda x: x.getBrand(), all_cars))

    frequency = []

    for f in (list(set(frequency))):
        frequency.append((f, brands.count(f)))

    frequencySorted = sorted(frequency, key=lambda u: u[1])

    top5 = (list(map(lambda x: x[0], frequencySorted[-5:])))

    filtered = list(filter(lambda x: False if x not in top5 else True, brands))

    plt.hist(filtered, histtype='bar', rwidth=0.85)
    plt.xticks(range(5))
    plt.show()


def vehiclesByDecades(cars):
    till2000 = list(filter(lambda x: True if x.getProductionYear() <= 2000 else False, cars))
    firstDecade = list(
        filter(lambda x: True if 2000 < x.getProductionYear() <= 2010 else False, cars))
    secondDecade = list(filter(lambda x: True if x.getProductionYear() > 2010 else False, cars))

    drawHistogram(till2000, label='Number of vehicles made before 2000 ordered by Mileage:', lower=0, upper=400)
    drawHistogram(firstDecade, label='Number of vehicles made between 2001 and 2010 ordered by Mileage:', lower=0,
                  upper=5000)
    drawHistogram(secondDecade, label='Number of vehicles made in 2011 or later ordered by Mileage:', lower=0,
                  upper=2000)


def main():
    urls = get_all_urls()
    prices = get_prices(urls)
    save_to_file(prices, os.path.join(data_folder, 'all_url-prices.pkl'))
    save_cars_info(urls, prices)

    for i in range(1, 11):
        print_car_info(i)


def get_prices(urls):
    prices = []
    for url in tqdm(urls):
        soup = BS(urllib2.urlopen(url), features="html.parser")
        price = soup.findAll('div', {'class': 'price-item position-relative'})

        for element in price:
            prices.append((url, element.text.strip()))
    return prices


def get_urls_from_file():
    import pickle
    try:
        f = open('C:\\Users\\smitric\\Desktop\\github_projects\\UsedCarsPricePrediction_Temp\\data\\features\\urls.pkl',
                 'rb')
    except Exception as e:
        print('Could not find the ' + file_name + '. Returning empty dict.')
        return {}
    data = pickle.load(f)
    f.close()

    print(data)

    return data


def print_prices():
    with open('C:\\Users\\smitric\\Desktop\\github_projects\\ML-UsedCarsPricePrediction\\podaci_za_projekat'
              '\\aaab_prices\\aaa_prices.pkl', 'rb') as f:
        data = pickle.load(f)

        print(len(data), data[:15])


def print_car_info(i):
    with open(os.path.join(data_folder, 'car_number_' + str(i) + '.pkl'), 'rb') as car_file:
        unpickled = pickle.load(car_file)
        print(unpickled)


if __name__ == '__main__':
    main()
