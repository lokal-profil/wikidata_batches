#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Importer for Australia national and commonwealth heritage lists.

The indata files are all expected to be pipe separated csv files
(without quoted strings).

Based on WFD importer.
"""
from __future__ import unicode_literals
from builtins import dict, open
import csv
import os.path as path

import pywikibot

import wikidataStuff.helpers as helpers
import wikidataStuff.wdqsLookup as wdqs
from wikidataStuff.WikidataStuff import WikidataStuff as WdS
from wikidataStuff.PreviewItem import PreviewItem

parameter_help = """\
ImporterBot options (may be omitted unless otherwise mentioned):
-in_file           path to the main data file (if not data.csv)
-new               if present new items are created on Wikidata, otherwise
                   only updates are processed.
-cutoff            number items to process before stopping (if not then all)
-preview_file      path to a file where previews should be outputted, sets the
                   run to demo mode

Can also handle any pywikibot options. Most importantly:
-simulate          don't write to database
-dir               directory in which user_config is located
-help              output all available options
"""
docuReplacements = {'&params;': parameter_help}
DATA_INPUT_FILE = 'data.csv'
NATIONAL_COORD_FILE = 'national_coords.csv'
COMMONWEALTH_COORD_FILE = 'commonwealth_coords.csv'
LOGFILE = 'importer.log'
EDIT_SUMMARY = 'importing Australia #COH #WLM #au'
DEFAULT_PREC = 0.0001  # default precision for coordinates


class ImporterBot(object):
    """Bot to enrich/create info on Wikidata for Australian heritage items."""

    def __init__(self, base_path, new=False, cutoff=None, preview_file=None):
        """
        Initialise the ImporterBot.

        :param base_path: path to the output directory
        :param new: whether to also create new items
        :param cutoff: the number of items to process before stopping. None
            being interpreted as all.
        :param preview_file: run in demo mode (create previews rather than
            live edits) and output the result to this file.
        """
        self.repo = pywikibot.Site().data_repository()
        self.wd = WdS(self.repo, EDIT_SUMMARY)
        self.new = new
        self.cutoff = cutoff
        if preview_file:
            self.demo = True
            self.preview_file = path.join(base_path, preview_file)
        else:
            self.demo = False
        self.preview_data = []

        self.set_references()
        self.place_id_p = 'P3008'  # unique identifier property
        self.country = self.wd.QtoItemPage('Q408')
        self.states = self.make_states_map()
        self.settlements = self.make_settlements_map()
        self.hectares = self.wd.QtoItemPage(helpers.get_unit_q('ha'))
        self.make_status_and_instance_map()

        self.place_id_items = helpers.fill_cache_wdqs(
            self.place_id_p, no_strip=True)

    def set_references(self):
        """Set the three types of references needed."""
        self.ref = {
            'national': self.make_url_ref(
                'http://data.gov.au/dataset/2016-soe-her-aus-national-heritage',  # noqa
                '2017-07-21',
                '2017-06-07'),
            'commonwealth': self.make_url_ref(
                'http://data.gov.au/dataset/commonwealth-heritage-list',
                '2017-07-21',
                '2017-05-31')
        }
        self.coord_ref = {
            'national': self.make_url_ref(
                'http://www.environment.gov.au/heritage/places/national-heritage-list',  # noqa
                '2017-08-13'),
            'commonwealth': self.make_url_ref(
                'https://data.gov.au/dataset/57720684-4948-45db-a2c8-37259d531d87',  # noqa
                '2017-08-13',
                '2017-07-10')
        }

    def make_status_and_instance_map(self):
        """Construct mapping for cultural heritage status and instance type."""
        self.status = {
            'national': self.wd.QtoItemPage('Q20747146'),
            'commonwealth': self.wd.QtoItemPage('Q30108476')
        }
        self.instance_type = {
            'indigenous': self.wd.QtoItemPage('Q38048771'),
            'historic': self.wd.QtoItemPage('Q38048707'),
            'natural': self.wd.QtoItemPage('Q38048753')
        }

    def make_settlements_map(self):
        """Retrieve Australian settlements with state/territory connection."""
        sparql = (
            "SELECT DISTINCT ?city ?cityLabel ?admin ?adminLabel "
            "WHERE "
            "{ "
            "?city wdt:P31/wdt:P279* wd:Q486972 . "
            "?city wdt:P17 wd:Q408 . "
            "?city wdt:P131* ?admin . "
            "{ ?admin wdt:P31 wd:Q5852411 . }"
            "UNION"
            "{ ?admin wdt:P31 wd:Q14192252 . }"
            "UNION"
            "{ ?admin wdt:P31 wd:Q14192199 . }"
            'SERVICE wikibase:label { bd:serviceParam wikibase:language "en" . }'  # noqa
            "}"
        )
        data = wdqs.make_simple_wdqs_query(sparql)
        settlements = dict()
        for d in data:
            state_qid = d['admin'].split('/')[-1]
            city_qid = d['city'].split('/')[-1]
            city_name = d['cityLabel']
            if city_name not in settlements:
                settlements[city_name] = []
            settlements[city_name].append({
                'state': state_qid,
                'qid': city_qid
            })
        return settlements

    def make_states_map(self):
        """
        Retrieve the state/territory mappings from Wikidata.

        Also tries to match items for the EXT and OS codes.
        """
        sparql = (
            "SELECT ?item ?iso "
            "WHERE "
            "{ "
            "?item wdt:P300 ?value . "
            "?item wdt:P17 wd:Q408 . "
            "BIND(REPLACE(?value, 'AU-', '', 'i') AS ?iso) "
            "}"
        )
        data = wdqs.make_select_wdqs_query(sparql, 'item', 'iso')
        states = dict()
        for k, v in data.items():
            states[v] = self.wd.QtoItemPage(k)

        # external territories (random hits mapped)
        states['EXT'] = {
            'Ashmore and Cartier Islands': self.wd.QtoItemPage('Q133888'),
            "Australian Antarctic Territory|Dumont D'Urville Station|Mawson Station": self.wd.QtoItemPage('Q178994'),  # noqa
            'Christmas Island|Settlement|Drumsite|Poon Saan': self.wd.QtoItemPage('Q31063'),  # noqa
            'Cocos (Keeling) Islands': self.wd.QtoItemPage('Q36004'),
            'Coral Sea Islands': self.wd.QtoItemPage('Q172216'),
            'Heard and McDonald Islands': self.wd.QtoItemPage('Q131198'),
            'Jervis Bay Territory': self.wd.QtoItemPage('Q15577'),
            'Norfolk Island|Kingston|Longridge|Burnt Pine|Middlegate': self.wd.QtoItemPage('Q31057')  # noqa
        }

        # OS other state?
        states['OS'] = {
            'United Kingdom': self.wd.QtoItemPage('Q145'),
            'USA': self.wd.QtoItemPage('Q30')
        }

        return states

    def make_url_ref(self, url, fetch_date, publish_date=None):
        """Make a Reference object for a url.

        Contains 3 parts:
        * P813: Retrieval date
        * P577: Publication date <from creation date of the document>
        * P854: Reference url <using the input url>

        :param url: the source url
        :param fetch_date: the retrieval date url (iso)
        :param publish_date: the retrieval date url (iso)
        :return: WdS.Reference
        """
        date_claims = []
        if publish_date:
            date_claims.append(
                self.wd.make_simple_claim(
                    'P577',
                    helpers.iso_to_WbTime(publish_date)))
        date_claims.append(
            self.wd.make_simple_claim(
                'P813',
                helpers.iso_to_WbTime(fetch_date)))

        ref = WdS.Reference(
            source_test=[
                self.wd.make_simple_claim('P854', url)
            ],
            source_notest=date_claims
        )
        return ref

    def output_previews(self):
        """Output any PreviewItems to the preview_file."""
        with open(self.preview_file, 'w', encoding='utf-8') as f:
            for preview in self.preview_data:
                f.write(preview.make_preview_page())
                f.write('--------------\n\n')
        pywikibot.output('Created "{}" for previews'.format(self.preview_file))

    def process_all_objects(self, data):
        """
        Handle all the Australian heritage objects.

        Only increments counter when an object is updated.

        :param data: dict of all the heritage objects.
        """
        count = 0
        for place_id, entry_data in data.items():
            if self.cutoff and count >= self.cutoff:
                break
            item = None
            if place_id in self.place_id_items:
                item = self.wd.QtoItemPage(self.place_id_items[place_id])

            if item or self.new:
                self.process_single_object(entry_data, item)
                count += 1

    def process_single_object(self, data, item):
        """
        Process a single Australian heritage object.

        :param data: dict of data for a single object
        :param item: Wikidata item associated with an object, or None if one
            should be created.
        """
        if not self.demo:
            item = item or self.create_new_place_id_item(data)
            item.exists()  # load the item contents

        # Determine claims
        labels = self.make_labels(data)
        descriptions = self.make_descriptions(data)
        protoclaims = self.make_protoclaims(data)
        ref = self.ref[self.get_heritage_type(data['type'])]

        # Upload claims
        if self.demo:
            self.preview_data.append(
                PreviewItem(labels, descriptions, protoclaims,
                            item, ref))
        else:
            self.commit_labels(labels, item)
            self.commit_descriptions(descriptions, item)
            self.commit_claims(protoclaims, item, ref)

    def create_new_place_id_item(self, data):
        """
        Create a new place_id item with some basic info and return it.

        :param data: dict of data for a single object
        :return: pywikibot.ItemPage
        """
        labels = helpers.convert_language_dict_to_json(
            self.make_labels(data),
            typ='labels')
        desc = helpers.convert_language_dict_to_json(
            self.make_descriptions(data),
            typ='descriptions')
        id_claim = self.wd.make_simple_claim(
            self.place_id_p, data.get('place_id'))

        item_data = {
            "labels": labels,
            "descriptions": desc,
            "claims": [id_claim.toJSON(), ]
        }

        try:
            return self.wd.make_new_item(item_data, EDIT_SUMMARY)
        except pywikibot.data.api.APIError as e:
            raise pywikibot.Error('Error during item creation: {:s}'.format(e))

    def make_labels(self, data):
        """
        Make a label object from the available info.

        :param data: dict of data for a single object
        :return: label dict
        """
        labels = {}
        name = data.get('name')
        if name:
            labels['en'] = [name.replace('  ', ' ').strip(), ]
        return labels

    def make_descriptions(self, data):
        """
        Make a description object in English.

        Address is partitioned so as to include the place name and
        territory/state in case these are not included anywhere later.

        :param data: dict of data for a single object
        :return: description object
        """
        text = '{heritage_type} {list_type} heritage site in {address}'
        descriptions = {
            'en': text.format(
                heritage_type=data['class'].lower(),
                list_type=self.get_heritage_type(data['type']),
                address=data['address'].rpartition(',')[2].strip()
            )
        }
        return descriptions

    def commit_labels(self, labels, item):
        """
        Add labels and aliases to item.

        :param labels: label object
        :param item: item to add labels to
        """
        if labels:
            self.wd.add_multiple_label_or_alias(
                labels, item, case_sensitive=False)

    def commit_descriptions(self, descriptions, item):
        """
        Add descriptions to item.

        :param descriptions: description object
        :param item: item to add descriptions to
        """
        if descriptions:
            self.wd.add_multiple_descriptions(descriptions, item)

    def commit_claims(self, protoclaims, item, default_ref):
        """
        Add each claim (if new) and source it.

        :param protoclaims: a dict of claims with
            key: Prop number
            val: Statement|list of Statements
        :param item: the target entity
        :param default_ref: main/default reference to use
        """
        for prop, statements in protoclaims.items():
            if statements:
                statements = helpers.listify(statements)
                statements = set(statements)  # eliminate potential duplicates
                for statement in statements:
                    # check if None or a Statement(None)
                    if (statement is not None) and (not statement.isNone()):
                        # use internal reference if present, else the general
                        ref = statement.ref or default_ref
                        self.wd.addNewClaim(
                            prop, statement, item, ref)

                        # reload item so that next call is aware of changes
                        item = self.wd.QtoItemPage(item.title())
                        item.exists()

    def make_protoclaims(self, data):
        """
        Construct potential claims for an entry.

        :param data: dict of data for a single heritage object
        """
        protoclaims = dict()

        # P17: country
        protoclaims['P17'] = WdS.Statement(self.country)

        # P1435: heritage status
        heritage_type = self.get_heritage_type(data.get('type'))
        statement = WdS.Statement(self.status[heritage_type])
        if data.get('register_date'):
            statement.addQualifier(
                WdS.Qualifier('P580', self.parse_date(
                    data.get('register_date'))))
        protoclaims['P1435'] = statement

        # P31: class
        protoclaims['P31'] = WdS.Statement(
            self.instance_type[data.get('class').lower()])

        # P3008: place_id
        protoclaims[self.place_id_p] = WdS.Statement(data['place_id'])

        # P131: state
        protoclaims['P131'] = WdS.Statement(
            self.get_state(data['state'], data['address']))

        # P2046: area
        if data.get('hectares'):
            protoclaims['P2046'] = WdS.Statement(
                pywikibot.WbQuantity(
                    data['hectares'], unit=self.hectares, site=self.wd.repo))

        # P969: address
        if ',' in data['address']:
            protoclaims['P969'] = WdS.Statement(data['address'])

        # P276: place
        protoclaims['P276'] = WdS.Statement(
            self.get_place(data['state'], data['address']))

        # P625: coordinate
        if data.get('lat') and data.get('lon'):
            protoclaims['P625'] = self.get_coordinate_statement(
                data.get('lat'), data.get('lon'), heritage_type)

        return protoclaims

    def get_coordinate_statement(self, lat, lon, heritage_type):
        """Construct a Statement for the provided coordinates."""
        statement = WdS.Statement(
            pywikibot.Coordinate(
                float(lat), float(lon), globe='earth', precision=DEFAULT_PREC))
        statement.add_reference(self.coord_ref[heritage_type])
        return statement

    def get_heritage_type(self, typ):
        """Determine which heritage type the object is."""
        heritage_type = None
        if typ.startswith('Q1116950'):
            heritage_type = 'commonwealth'
        elif typ.startswith('Q781601'):
            heritage_type = 'national'
        else:
            pywikibot.error('Unrecognized status: {0}'.format(typ))
        return heritage_type

    def parse_date(self, date):
        """Convert date in DD-MMM-YYYY format to WbTime."""
        months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG',
                  'SEP', 'OCT', 'NOV', 'DEC']
        dd, mmm, yyyy = date.split('-')
        iso = '{year}-{month:02d}-{day:02d}'.format(
            year=yyyy, day=int(dd), month=months.index(mmm) + 1)
        return helpers.iso_to_WbTime(iso)

    def get_place(self, state, address):
        """
        Determine which settlement the object is in.

        The format of address is "street, place STATE_ISO"
        """
        place = address.rpartition(',')[2][:-len(state)].strip()
        state_item = self.get_state(state, address)
        if place in self.settlements and state_item:
            hits = []
            for candidate in self.settlements[place]:
                if candidate['state'] == state_item.id:
                    hits.append(candidate['qid'])
            if len(set(hits)) == 1:
                return self.wd.QtoItemPage(hits[0])

    def get_state(self, state, address):
        """Determine which state/territory the object is in."""
        state_item = None
        if state not in self.states:
            pywikibot.error('Unrecognized state: {0}'.format(state))
        elif state == 'EXT':
            address = address[:-len('EXT')].strip()
            for key, v in self.states['EXT'].items():
                if any(address.endswith(k) for k in key.split('|')):
                    state_item = v
                    break
        elif state == 'OS':
            for k, v in self.states['OS'].items():
                if address.endswith(k):
                    state_item = v
                    break
        else:
            state_item = self.states[state]
        return state_item


def load_csv_data(filename, log):
    """Load the csv files and handle any duplicate entries."""
    with open(filename, encoding='utf-8') as csv_file:
        reader = csv.DictReader(
            csv_file, delimiter='|', quoting=csv.QUOTE_NONE)
        local_log = []

        result = {}
        for row in reader:
            key = row.get('place_id')
            if key in result:
                result[key] = handle_dupe(row, result[key], local_log, key)
            else:
                result[key] = row

        if local_log:
            log[filename] = local_log
        return result


def handle_dupe(new_entry, old_entry, log, place_id):
    """Handle duplicate entries in csv by removing conflicting fields."""
    dropped = []
    for k, v in old_entry.items():
        if v != new_entry[k]:
            old_entry[k] = None
            dropped.append(k)

    log.append('Found dupe in {0}, dropped: {1}'.format(
        place_id, ', '.join(dropped)))
    return old_entry


def combine_data(main_data, nat_coords_data, com_coords_data, log):
    """Add the coordinates to the main data store."""
    local_log = []
    for k, v in main_data.items():
        found_coord = None
        coords = {'lat': None, 'lon': None}

        if k in nat_coords_data:
            found_coord = nat_coords_data[k]
        if k in com_coords_data:
            if found_coord:
                local_log.append(
                    'Found coordinates in both files for {0}. Skip'.format(k))
                found_coord = None
            else:
                found_coord = com_coords_data[k]

        if found_coord and found_coord['lat'] and found_coord['lon']:
            coords['lat'] = found_coord['lat']
            coords['lon'] = found_coord['lon']

        main_data[k].update(coords)

    if local_log:
        log['combining'] = local_log
    return main_data


def main(*args):
    """Command line entry point."""
    base_path = path.dirname(path.abspath(__file__))
    options = handle_args(args)
    log = {}

    # load 3 indata files and combine
    data_file = options.pop('in_file') or path.join(base_path, DATA_INPUT_FILE)
    main_data = load_csv_data(data_file, log)
    nat_coords_data = load_csv_data(
        path.join(base_path, NATIONAL_COORD_FILE), log)
    com_coords_data = load_csv_data(
        path.join(base_path, COMMONWEALTH_COORD_FILE), log)
    data = combine_data(main_data, nat_coords_data, com_coords_data, log)

    if log:
        output_log(path.join(base_path, LOGFILE), log)

    # initialise ImporterBot
    bot = ImporterBot(base_path, **options)
    bot.process_all_objects(data)

    if bot.demo:
        bot.output_previews()


def output_log(logfile, log):
    """
    Output the logfile.

    The log should be a dictionary with the import step as key and a list of
    log messages as value.
    """
    with open(logfile, 'w', encoding='utf-8') as f:
        for k, v in log.items():
            f.write('-------{label}-------\n{lines}\n\n'.format(
                label=k, lines='\n'.join(v)))
        pywikibot.output('Created "{0}"'.format(LOGFILE))


def handle_args(args):
    """
    Parse and load all of the basic arguments.

    Also passes any needed arguments on to pywikibot and sets any defaults.

    :param args: list of arguments to be handled
    :return: dict of options
    """
    options = {
        'new': False,
        'cutoff': None,
        'preview_file': None,
        'in_file': None,
    }

    for arg in pywikibot.handle_args(args):
        option, sep, value = arg.partition(':')
        if option == '-in_file':
            options['in_file'] = value
        if option == '-new':
            options['new'] = True
        elif option == '-cutoff':
            options['cutoff'] = int(value)
        elif option == '-preview_file':
            options['preview_file'] = value

    return options


if __name__ == "__main__":
    main()
