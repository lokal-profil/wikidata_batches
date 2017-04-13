#!/usr/bin/python
# -*- coding: utf-8  -*-
"""
Bot to import Nationalmuseum (Sweden) illustrations and additional metadata
to Wikidata.

The source data are the LIDO files used for the image import (into Commons).

&params;
"""
import codecs
import os.path as path

import pywikibot

import wikidataStuff.helpers as helpers
from wikidataStuff.WikidataStuff import WikidataStuff as WD
import wikidataStuff.wdqsLookup as wdqsLookup
EDIT_SUMMARY = u'import using #NatMus data'

usage = u"""
Usage:            python NatMus-images/ImageImporter.py [OPTIONS]
                  with options:

-rows:INT         Number of entries to process (default: All)
"""
docuReplacements = {'&params;': usage}


class PaintingsImageBot:
    """Bot to enrich, and create, for items about paintings on Wikidata."""

    def __init__(self, dict_generator, people_items):
        """Initialise the bot."""
        self.people_items = people_items
        self.generator = dict_generator
        self.repo = pywikibot.Site().data_repository()
        self.wd = WD(self.repo, edit_summary=EDIT_SUMMARY)

        # Set log file
        out_dir = path.join(path.split(__file__)[0])
        log_filename = path.join(out_dir, u'PaintingsImageBot.log')
        self.log = codecs.open(log_filename, 'a', 'utf-8')

    def run(self):
        """Start the robot."""
        self.creators = {}

        for painting_data in self.generator:
            # isolate ids
            lido_data, qid, commons_file = painting_data
            painting_item = self.wd.QtoItemPage(qid)
            self.process_painting(painting_item, lido_data, commons_file)

    def process_painting(self, item, lido_data, commons_file):
        """Process a single painting."""
        item.exists()  # load the item
        obj_id_ref = self.make_obj_id_ref(lido_data.get('obj_id'))
        # lido_ref = self.make_lido_ref(lido_data)  # make a reference object

        self.check_and_add_labels(item, lido_data)
        self.add_image_claim(item, commons_file, obj_id_ref)
        self.add_depicted_claim(item, lido_data, obj_id_ref)
        self.add_date_claim(item, lido_data, obj_id_ref)
        self.add_dimension_claims(item, lido_data, obj_id_ref)

    def add_dimension_claims(self, item, lido_data, ref):
        """
        Add height/P2048 and width/P2049 claims.

        Only add non-framed measurements with just height and width.
        """
        height_p = u'P2048'
        width_p = u'P2049'
        # diameter_p = u'P2386'
        # thickness_p = u'P2610'
        dimensions = lido_data.get('measurements').get('_')  # non-framed
        if not dimensions or not dimensions.get('unit'):
            return None
        elif not dimensions.get('width') or not dimensions.get('height') \
                or dimensions.get('depth'):
            # skip complicated cases for now
            return None
        elif not helpers.get_unit_q(dimensions.get('unit')):
            pywikibot.output(
                u'"%s" is an unmapped unit' % dimensions.get('unit'))
            return None

        # prepare all parts before adding claims
        unit = helpers.get_unit_q(dimensions.get('unit'))
        # unit = self.wd.QtoItemPage(unit)
        unit = entity_url_hack(unit)

        height = pywikibot.WbQuantity(
            dimensions.get('height'),
            # unit=unit,
            entity=unit,
            site=self.wd.repo)
        width = pywikibot.WbQuantity(
            dimensions.get('width'),
            # unit=unit,
            entity=unit,
            site=self.wd.repo)

        # make claims
        self.wd.addNewClaim(
            height_p, WD.Statement(height),
            item, ref)
        self.wd.addNewClaim(
            width_p, WD.Statement(width),
            item, ref)

    def add_date_claim(self, item, lido_data, ref):
        """
        Add an inception/P571 claim.

        Only adds the claim if it's an exact year.
        """
        prop = u'P571'
        creation_date = lido_data.get('creation_date')
        wb_date = None
        if not creation_date:
            return None

        # exact date
        if creation_date.get('earliest') and \
                creation_date.get('earliest') == creation_date.get('latest'):
            wb_date = helpers.iso_to_WbTime(creation_date.get('earliest'))

        # make claim
        if wb_date:
            self.wd.addNewClaim(
                prop, WD.Statement(wb_date),
                item, ref)

    def add_depicted_claim(self, item, lido_data, ref):
        """Add a depicted/P180."""
        prop = u'P180'
        if not lido_data.get('subjects'):
            return None

        for subject in lido_data.get('subjects'):
            nsid = subject.get(u'other_id')
            if nsid in self.people_items:
                person_item = self.wd.QtoItemPage(self.people_items[nsid])
                self.wd.addNewClaim(
                    prop, WD.Statement(person_item),
                    item, ref)

    def add_image_claim(self, item, commons_file, ref):
        """
        Add a image/P18 claim.

        Only adds it if there is None already. If one exists output to log.
        """
        prop = u'P18'
        if not commons_file:
            return

        file_page = pywikibot.FilePage(
            pywikibot.Site('commons', 'commons'), commons_file)

        # check if another image is already used
        if prop in item.claims and \
                not self.wd.has_claim(prop, file_page, item):
            self.log.write(
                u"%s already contains image claim: %s -> %s\n" % (
                    item.title(),
                    item.claims.get(prop)[0].getTarget().title(),
                    file_page.title()))
        else:
            self.wd.addNewClaim(
                prop, WD.Statement(file_page),
                item, ref)

    def check_and_add_labels(self, item, lido_data):
        """Process the title field add to the item if needed."""
        if not lido_data.get('title'):
            return

        for lang, value in lido_data.get('title').iteritems():
            if lang == '_':
                continue
            try:
                self.wd.addLabelOrAlias(
                    lang, value, item,
                    caseSensitive=False)
            except pywikibot.data.api.APIError as e:
                self.log.write(u"%s: had an error: %s\n" % (item.title(), e))

    def make_obj_id_ref(self, obj_id):
        """Make a reference object pointing to the objects collection page."""
        uri = u'http://collection.nationalmuseum.se/eMuseumPlus?' \
              u'service=ExternalInterface&module=collection&' \
              u'objectId=%s&viewType=detailView' % obj_id
        return self.make_url_reference(uri)

    def make_url_reference(self, uri):
        """
        Make a Reference object with a retrieval url and today's date.

        @param uri: retrieval uri/url
        @type uri: str
        @rtype: WD.Reference
        """
        date = helpers.today_as_WbTime()
        ref = WD.Reference(
            source_test=self.wd.make_simple_claim(u'P854', uri),
            source_notest=self.wd.make_simple_claim(u'P813', date))
        return ref

    # Not implemented due to uncertainty on referencing individual xml files
    def make_lido_ref(self, lido_data):
        """
        Make a Reference object for the dataset.

        Contains 4 parts:
        * P248: Stated in <the WFD2016 dataset>
        * P577: Publication date <from creation date of the document>
        * P854: Reference url <using the input url>
        * P813: Retrieval date <current date>
        """
        exit()
        #P248: Nationalmuseum dataset
        xml_file = lido_data.get('source_file')
        date = helpers.today_as_WbTime()
        pub_date = helpers.iso_to_WbTime(u'2016-09-30')
        zip_url = u'https://github.com/NationalmuseumSWE/WikidataCollection/' \
                  u'blob/master/valid_items_transform_1677.tgz'
        ref = WD.Reference(
            source_test=[
                self.wd.make_simple_claim(u'P854', zip_url),
                self.wd.make_simple_claim(u'P577', pub_date),
                self.wd.make_simple_claim(u'P?', xml_file),
            ],
            source_notest=self.wd.make_simple_claim(u'P813', date))
        return ref


def entity_url_hack(unit):
    """Temporary hack until WbQuantity fully supports units."""
    return u'http://www.wikidata.org/entity/%s' % unit


def make_labels(lido_data):
    """
    Given a painting object extract all potential labels.

    @param painting: information object for the painting
    @type painting: dict
    @return: language-label pairs
    @rtype: dict
    """
    labels = {}
    if lido_data.get('title'):
        for lang, value in lido_data.get('title').iteritems():
            if lang == '_':
                continue
            labels[lang] = {'language': lang, 'value': value}
    return labels


def load_commons_data(filename):
    """
    Load the local data file on nsid to filenames on Commons.

    The file is a csv of the format:
    <nsid>|<source_file.tif>|https://commons.wikimedia.org/wiki/File:<commons_filename.tif>

    The returned format is a dict with nsid as key and (short) commons
    filename as value.
    """
    commons_data = {}
    commons_string = u'https://commons.wikimedia.org/wiki/File:'
    with codecs.open(filename, 'r', 'utf-8') as f:
        lines = f.read().split('\n')
        lines.pop(0)  # The first row is just explanation
        for line in lines:
            if not line.strip():
                continue
            p = line.split('|')
            commons_name = p[2][len(commons_string):]
            commons_data[p[0]] = commons_name
    return commons_data


def load_offline_data():
    """Load and prepare the local data."""
    # Hard code filenames because I'm lazy
    data_dir = u'NatMus-images/data/'
    commons_names = data_dir + u'obj_id-file-commons.csv'
    nsid = data_dir + u'local_nsid_mapping.json'
    processed_lido = data_dir + u'processed_lido.json'

    local_nsid = helpers.load_json_file(nsid)
    lido = helpers.load_json_file(processed_lido)
    commons_data = load_commons_data(commons_names)

    return local_nsid, lido, commons_data


def load_creator_items():
    """Load existing creator items."""
    item_ids = wdqsLookup.make_claim_wdqs_search(
        'P2538', get_values=True, allow_multiple=True)

    # invert and check existence and uniqueness
    nsid_creators = {}
    for q_id, values in item_ids.iteritems():
        for value in values:
            if value in nsid_creators.keys():
                pywikibot.output(
                    "Multiple Wikidata connected to one creator (%s): %s, %s"
                    % (value, q_id, nsid_creators[value]))
            nsid_creators[value] = q_id

    return nsid_creators


def load_painting_items():
    """Load existing painting items."""
    item_ids = wdqsLookup.make_claim_wdqs_search(
        'P2539', get_values=True, allow_multiple=True)

    # invert and check existence and uniqueness
    nsid_items = {}
    for q_id, values in item_ids.iteritems():
        for value in values:
            if value in nsid_items.keys():
                pywikibot.output(
                    "Multiple Wikidata connected to one painting (%s): %s, %s"
                    % (value, q_id, nsid_items[value]))
            nsid_items[value] = q_id

    return nsid_items


def prepare_data():
    """Load all of the data and package for downstream use."""
    local_nsid, lido, commons_data = load_offline_data()
    creator_items = load_creator_items()
    painting_items = load_painting_items()

    # merge local_nsid and creator_items
    for k, v in local_nsid.iteritems():
        if k in creator_items.keys() and creator_items[k] != v:
            pywikibot.output(
                "Conflict between local and Wikidata mapping (%s): %s, %s"
                % (k, v, creator_items[k]))
        creator_items[k] = v

    return painting_items, lido, commons_data, creator_items


def get_painting_generator(lido_data, painting_items, commons_data, rows=None):
    """Get objects from LIDO data."""
    counter = 0
    for nsid, data in lido_data.iteritems():
        if not rows or counter < rows:
            if nsid in painting_items.keys():
                yield data, painting_items[nsid], commons_data.get(nsid)
        else:
            pywikibot.output(u'You are done!')
            break
        counter += 1

    pywikibot.output(u'No more results! You are done!')


def main(*args):
    """Run the bot from the command line and handle any arguments."""
    # handle arguments
    rows = None

    for arg in pywikibot.handle_args(args):
        option, sep, value = arg.partition(':')
        if option == '-rows':
            if helpers.is_pos_int(value):
                rows = int(value)
            else:
                raise pywikibot.Error(usage)

    painting_items, lido_data, commons_data, people_items = prepare_data()
    painting_gen = get_painting_generator(
        lido_data, painting_items, commons_data, rows=rows)

    paintings_bot = PaintingsImageBot(painting_gen, people_items)
    paintings_bot.run()
    paintings_bot.log.close()

if __name__ == "__main__":
    """Run from the command line."""
    main()
