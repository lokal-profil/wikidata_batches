#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import and source statements about Maritime objects in KulturNav.

usage:
    python KulturNav/kulturnavBotSMM.py [OPTIONS]

Author: Lokal_Profil
License: MIT

Options (required):
-dataset:STR       the dataset to work on

&params;
"""
import pywikibot
import wikidataStuff.helpers as helpers
from wikidataStuff.WikidataStuff import WikidataStuff as WD
from kulturnavBot import parameter_help
from kulturnavBot import KulturnavBot
from kulturnavBot import Rule
from kulturnavBotTemplates import Person
docuReplacements = {
    '&params;': parameter_help
}


class KulturnavBotSMM(KulturnavBot):
    """Bot to enrich/create info on Wikidata for SMM naval objects."""

    # KulturNav based
    EDIT_SUMMARY = 'import using #Kulturnav #SMM data'
    DATASETS = {
        u'Fartyg': {
            'id': 0,
            'fullName': u'Fartyg',
            'DATASET_ID': '9a816089-2156-42ce-a63a-e2c835b20688',
            'ENTITY_TYPE': 'NavalVessel',
            'DATASET_Q': '20734454'},
        u'Fartygstyper': {
            'id': 1,
            'fullName': u'Fartygstyper',
            'DATASET_ID': 'c43d8eba-030b-4542-b1ac-6a31a0ba6d00',
            'ENTITY_TYPE': 'Concept',
            'MAP_TAG': 'concept.exactMatch_s',
            'DATASET_Q': '20103697'},
        u'Namngivna': {
            'id': 2,
            'fullName': u'Namngivna fartygstyper',
            'DATASET_ID': '51f2bd1f-7720-4f03-8d95-c22a85d26bbb',
            'ENTITY_TYPE': 'Concept',
            'MAP_TAG': 'concept.exactMatch_s',
            'DATASET_Q': '20742915'},
        u'Personer': {
            'id': 3,
            'fullName': u'Personer verksamma inom fartygs- och båtbyggeri',
            'DATASET_ID': 'c6a7e732-650f-4fdb-a34c-366088f1ff0e',
            'ENTITY_TYPE': 'Person',
            'DATASET_Q': '20669482'},
        u'Serietillverkade': {
            'id': 4,
            'fullName': u'Serietillverkade fartyg',
            'DATASET_ID': '6a98b348-8c90-4ccc-9da7-42351bd4feb7',
            'ENTITY_TYPE': 'NavalVesselDesign',
            'DATASET_Q': '20742975'},
        u'Klasser': {
            'id': 5,
            'fullName': u'Svenska marinens klasser för örlogsfartyg',
            'DATASET_ID': 'fb4faa4b-984a-404b-bdf7-9c24a298591e',
            'ENTITY_TYPE': 'NavalVesselDesign',
            'DATASET_Q': '20742782'},
        u'Varv': {
            'id': 6,
            'fullName': u'Varv',
            'DATASET_ID': 'b0fc1427-a9ab-4239-910a-cd02c02c4a76',
            'ENTITY_TYPE': 'Organization',
            'DATASET_Q': '20669386'}
    }
    MAP_TAG = 'entity.sameAs_s'

    DATASET = None  # set by setDataset()
    SHIPYARD_Q = '190928'
    SHIPCLASS_Q = '559026'
    SUBMARINECLASS_Q = '1428357'
    BOATTYPE_Q = '16103215'
    SUBMARINETYPE_K = 'd7286bae-9e1f-4048-94b5-f70017d139f8'
    SHIPTYPE_Q = '2235308'
    SWENAVY_Q = '1141396'
    COMPANY_Q = '783794'
    ORGANISATION_Q = '43229'
    IKNO_K = u'http://kulturnav.org/2c8a7e85-5b0c-4ceb-b56f-a229b6a71d2a'
    class_list = None
    type_list = None
    all_ship_types = None  # any item in the ship type tree

    def run(self):
        """Start the bot."""
        # switch run method based on DATASET
        if self.DATASET == 'Personer':
            self.runPerson()
        elif self.DATASET == 'Varv':
            self.runVarv()
        elif self.DATASET == 'Fartyg':
            self.class_list = self.wd.wdqLookup(
                u'CLAIM[1248]{CLAIM[972:%s]}' %
                self.DATASETS[u'Klasser']['DATASET_Q'])
            self.type_list = self.wd.wdqLookup(
                u'CLAIM[1248]{'
                u'CLAIM[972:%s] OR CLAIM[972:%s] OR CLAIM[972:%s]}' % (
                    self.DATASETS[u'Fartygstyper']['DATASET_Q'],
                    self.DATASETS[u'Namngivna']['DATASET_Q'],
                    self.DATASETS[u'Serietillverkade']['DATASET_Q']))
            self.all_ship_types = self.wd.wdqLookup(
                u'CLAIM[31:%s]' % self.SHIPTYPE_Q)
            self.all_ship_types += self.wd.wdqLookup(
                u'CLAIM[31:%s]' % self.BOATTYPE_Q)
            self.runFartyg()
        elif self.DATASET == 'Klasser':
            self.runKlasser()
        elif self.DATASET == 'Fartygstyper':
            self.runFartygstyper()
        elif self.DATASET == 'Namngivna':
            self.runNamngivna()
        elif self.DATASET == 'Serietillverkade':
            self.runSerietillverkade()
        else:
            raise NotImplementedError("Please implement this dataset: %s"
                                      % self.DATASET)

    def runPerson(self):
        """Start a bot for adding info on people."""
        rules = Person.get_rules()

        def claims(self, values):
            """Add protoclaims.

            @param values: the values extracted using the rules
            @type values: dict
            @return: the protoclaims
            @rtype: dict PID-WD.Statement pairs
            """
            # get basic person claims
            protoclaims = Person.get_claims(self, values)

            # P106 occupation - fieldOfActivityOfThePerson
            return protoclaims

        # pass settings on to runLayout()
        self.runLayout(datasetRules=rules,
                       datasetProtoclaims=claims,
                       datasetSanityTest=Person.person_test,
                       label=u'name',
                       shuffle=True)

    def runVarv(self):
        """Start a bot for adding info on shipyards."""
        rules = {
            u'name': None,
            u'agent.ownership': Rule(
                target='agent.ownedBy',
                viaId={
                    'owner': 'agent.ownership.owner',
                    'start': ('event.timespan', 'startDate'),
                    'end': ('event.timespan', 'endDate')
                }),
            u'establishment.date': Rule(
                target='association.establishment',
                viaId='event.time'),
            u'termination.date': Rule(
                target='association.termination',
                viaId='event.time'),
            u'location': Rule(
                target='E7_Activity',
                viaId=('P7_took_place_at', 'location'))
        }

        def claims(self, values):
            """Add protoclaims.

            @param values: the values extracted using the rules
            @type values: dict
            @return: the protoclaims
            @rtype: dict PID-WD.Statement pairs
            """
            protoclaims = {}
            self.set_is_instance(self.SHIPYARD_Q, protoclaims)
            self.set_location(values, protoclaims)
            self.set_owner(values, protoclaims)

            # handle values
            if values.get(u'establishment.date'):
                protoclaims[u'P571'] = WD.Statement(
                    helpers.iso_to_WbTime(values[u'establishment.date']))
            if values.get(u'termination.date'):
                protoclaims[u'P576'] = WD.Statement(
                    helpers.iso_to_WbTime(values[u'termination.date']))

            return protoclaims

        def test(self, hit_item):
            """Test that this isn't something other than a shipyard.

            Fail if has instance claims and none of them are
            shipyard/company/organisation

            @parm hit_item: item to check
            @type hit_item: pywikibot.ItemPage
            @return: if test passed
            @rtype: bool
            """
            return self.withClaimTest(hit_item,
                                      self.IS_A_P,
                                      [self.SHIPYARD_Q,
                                       self.COMPANY_Q,
                                       self.ORGANISATION_Q],
                                      u'shipyard')

        # pass settings on to runLayout()
        self.runLayout(datasetRules=rules,
                       datasetProtoclaims=claims,
                       datasetSanityTest=test,
                       label=u'name',
                       shuffle=False)

    def runFartyg(self):
        """Start a bot for adding info on ships."""
        # @todo: add navalVessel.wrecked
        #        (see 42329089-247c-4045-aa22-967d3fb06dfe)
        rules = KulturnavBotSMM.get_base_ship_rules()
        rules.update({
            u'navalVessel.signalLetters': None,
            u'entity.code': None,
            u'built.date': Rule(
                target='navalVessel.built',
                viaId=('event.timespan', 'startDate')),
            u'built.location': Rule(
                target='navalVessel.built',
                viaId=('P7_took_place_at', 'location')),
            u'built.shipyard': Rule(
                target='navalVessel.built',
                viaId='navalVessel.built.shipyard'),
            u'launched.date': Rule(
                target='navalVessel.launched',
                viaId='event.time'),
            u'launched.location': Rule(
                target='navalVessel.launched',
                viaId=('P7_took_place_at', 'location')),
            u'launched.shipyard': Rule(
                target='navalVessel.launched',
                viaId='navalVessel.launched.shipyard'),
            u'delivered.date': Rule(
                target='navalVessel.delivered',
                viaId='event.time'),
            u'decommissioned.date': Rule(
                target='navalVessel.decommissioned',
                viaId='event.time'),
            u'homePort': Rule(
                target='navalVessel.homePort',
                viaId={
                    'location': ('P7_took_place_at', 'location'),
                    'start': ('event.timespan', 'startDate'),
                    'end': ('event.timespan', 'endDate')
                }),
            u'navalVessel.isSubRecord': None,
            u'navalVessel.hasSubRecord': None,
            u'navalVessel.registration': Rule(
                target='navalVessel.registration',
                viaId={
                    'number': 'registration.number',
                    'type': 'registration.register'
                })
        })

        def claims(self, values):
            """Add protoclaims.

            @todo: implement:
                u'delivered.date'
                u'navalVessel.isSubRecord'
                u'navalVessel.hasSubRecord'

            @param values: the values extracted using the rules
            @type values: dict
            @return: the protoclaims
            @rtype: dict PID-WD.Statement pairs
            """
            # handle altNames together with names
            values[u'entity.name'] = KulturnavBotSMM.prep_names(values)
            # convert from ALL-CAPS
            for i, v in enumerate(values[u'entity.name']):
                values[u'entity.name'][i][u'@value'] = \
                    v[u'@value'].capitalize()

            # bundle type and otherType
            values[u'navalVessel.type'] = KulturnavBotSMM.prep_types(values)

            # check that we can always safely ignore entity.code
            KulturnavBotSMM.verify_entity_code_assumption(values)

            protoclaims = {}
            self.set_type_and_class(values, protoclaims)
            self.set_registration_no(values, protoclaims)
            self.set_homeport(values, protoclaims)
            self.set_shipyard(values, protoclaims)  # Manufacturer (Shipyard)
            self.set_constructor(values, protoclaims)  # Designer (Constructor)
            self.set_ship_events(values, protoclaims)

            # P2317 - call sign
            if values.get(u'navalVessel.signalLetters'):
                protoclaims[u'P2317'] = WD.Statement(
                    values[u'navalVessel.signalLetters'])

            return protoclaims

        def test(self, hit_item):
            """Test if the item is a type of ship/boat.

            Is there any way of testing that it is a ship... of some type?
            Possibly if any of P31 is in wdqList for claim[31:2235308].

            @parm hit_item: item to check
            @type hit_item: pywikibot.ItemPage
            @return: if test passed
            @rtype: bool
            """
            P = u'P31'
            if P not in hit_item.claims.keys():
                return True
            claims = []
            for claim in hit_item.claims[P]:
                # add resolved Qno of each claim
                target = self.wd.bypassRedirect(claim.getTarget())
                claims.append(int(target.title()[1:]))
            # check if any of the claims are recognised shipTypes
            if any(x in claims for x in self.all_ship_types):
                return True
            pywikibot.output(u'%s is identified as something other than '
                             u'a ship/boat type. Check!' % hit_item.title())
            return False

        # pass settings on to runLayout()
        self.runLayout(datasetRules=rules,
                       datasetProtoclaims=claims,
                       datasetSanityTest=test,
                       label=u'entity.name',
                       shuffle=False)

    def runKlasser(self):
        """Start a bot for adding info on ship classes."""
        rules = KulturnavBotSMM.get_base_ship_rules()

        def claims(self, values):
            """Add protoclaims.

            @param values: the values extracted using the rules
            @type values: dict
            @return: the protoclaims
            @rtype: dict PID-WD.Statement pairs
            """
            # handle altNames together with names
            values[u'entity.name'] = KulturnavBotSMM.prep_names(values)

            # bundle type and otherType
            values[u'navalVessel.type'] = KulturnavBotSMM.prep_types(values)

            protoclaims = {
                # operator = Swedish Navy
                u'P137': WD.Statement(
                    self.wd.QtoItemPage(self.SWENAVY_Q))
            }

            # P31 - instance of
            # ship class unless a submarine
            class_Q = self.SHIPCLASS_Q
            if values[u'navalVessel.type'] and \
                    any(x.endswith(self.SUBMARINETYPE_K)
                        for x in values[u'navalVessel.type']):
                class_Q = self.SUBMARINECLASS_Q
            protoclaims[u'P31'] = WD.Statement(
                self.wd.QtoItemPage(class_Q))

            # P279 - subgroup
            self.set_subgroup(values, protoclaims)

            # P287 - Designer (Constructor)
            self.set_constructor(values, protoclaims)

            return protoclaims

        def test(self, hit_item):
            """Fail if instance claims and none of them are ship class.

            @parm hit_item: item to check
            @type hit_item: pywikibot.ItemPage
            @return: if test passed
            @rtype: bool
            """
            return self.withClaimTest(hit_item,
                                      self.IS_A_P,
                                      [self.SHIPCLASS_Q,
                                       self.SHIPTYPE_Q,
                                       self.SUBMARINECLASS_Q],
                                      u'ship class or type')

        # pass settings on to runLayout()
        self.runLayout(datasetRules=rules,
                       datasetProtoclaims=claims,
                       datasetSanityTest=test,
                       label=u'entity.name',
                       shuffle=False)

    def runFartygstyper(self):
        """Start a bot for adding info on ship types.

        @todo: if a boat_type then it should be possible to
               add everything except P31
        """
        rules = {
            u'prefLabel': None,
            u'altLabel': None,
            u'broader': None
        }

        def claims(self, values):
            """Add protoclaims.

            @param values: the values extracted using the rules
            @type values: dict
            @return: the protoclaims
            @rtype: dict PID-WD.Statement pairs
            """
            # handle prefLabel together with altLabel
            values[u'prefLabel'] = KulturnavBotSMM.prep_labels(values)

            protoclaims = {}
            self.set_is_instance(self.SHIPTYPE_Q, protoclaims)

            # P279 - subgroup self.kulturnav2Wikidata(broader)
            if values.get(u'broader'):
                protoclaims[u'P279'] = WD.Statement(
                    self.kulturnav2Wikidata(
                        values[u'broader']))
            return protoclaims

        # pass settings on to runLayout()
        self.runLayout(datasetRules=rules,
                       datasetProtoclaims=claims,
                       datasetSanityTest=KulturnavBotSMM.test_shiptype,
                       label=u'prefLabel',
                       shuffle=False)

    def runNamngivna(self):
        """Start a bot for adding info on named ship models."""
        rules = {
            u'prefLabel': None,
            u'altLabel': None,
            u'navalVessel.type': None,
            u'navalVessel.otherType': None
        }

        def claims(self, values):
            """Add protoclaims.

            @param values: the values extracted using the rules
            @type values: dict
            @return: the protoclaims
            @rtype: dict PID-WD.Statement pairs
            """
            # handle prefLabel together with altLabel
            values[u'prefLabel'] = KulturnavBotSMM.prep_labels(values)

            # bundle type and otherType
            values[u'navalVessel.type'] = KulturnavBotSMM.prep_types(values)

            protoclaims = {}
            self.set_is_instance(self.SHIPTYPE_Q, protoclaims)
            self.set_subgroup(values, protoclaims)

            return protoclaims

        # pass settings on to runLayout()
        self.runLayout(datasetRules=rules,
                       datasetProtoclaims=claims,
                       datasetSanityTest=KulturnavBotSMM.test_shiptype,
                       label=u'prefLabel',
                       shuffle=False)

    def runSerietillverkade(self):
        """Start a bot for adding info on serially produced ships."""
        rules = KulturnavBotSMM.get_base_ship_rules()

        def claims(self, values):
            """Add protoclaims.

            @param values: the values extracted using the rules
            @type values: dict
            @return: the protoclaims
            @rtype: dict PID-WD.Statement pairs
            """
            # handle altNames together with names
            values[u'entity.name'] = KulturnavBotSMM.prep_names(values)

            # bundle type and otherType
            values[u'navalVessel.type'] = KulturnavBotSMM.prep_types(values)

            protoclaims = {}
            self.set_is_instance(self.SHIPTYPE_Q, protoclaims)
            self.set_subgroup(values, protoclaims)
            self.set_constructor(values, protoclaims)  # Designer (Constructor)

            return protoclaims

        # pass settings on to runLayout()
        self.runLayout(datasetRules=rules,
                       datasetProtoclaims=claims,
                       datasetSanityTest=KulturnavBotSMM.test_shiptype,
                       label=u'entity.name',
                       shuffle=False)

    @staticmethod
    def get_base_ship_rules():
        """Construct the basic rules for shiplike objects.

        @return: The rules
        @rtype: dict
        """
        return {
            u'entity.name': Rule(
                target='entity.name'),
            u'altLabel': None,
            u'navalVessel.type': None,  # a type or another class
            u'navalVessel.otherType': None,
            u'constructor': Rule(
                target='navalVessel.constructed',
                viaId={
                    'constructedBy': 'navalVessel.constructed.constructedBy',
                    'start': ('event.timespan', 'startDate'),
                    'end': ('event.timespan', 'endDate')
                })
            # navalVessel.measurement
        }

    @staticmethod
    def test_shiptype(bot, hit_item):
        """Fail if there are instance claims and none of them are ship type.

        @param bot: the instance of the bot calling upon the test
        @param bot: KulturnavBotSMM
        @parm hit_item: item to check
        @type hit_item: pywikibot.ItemPage
        @return: if test passed
        @rtype: bool
        """
        return bot.withClaimTest(hit_item,
                                 bot.IS_A_P,
                                 bot.SHIPTYPE_Q,
                                 u'ship type')

    def set_shipyard(self, values, protoclaims):
        """Identify Manufacturer/Shipyard (P176) and add to claims.

        Adds the claim to the protoclaims dict.

        @param values: the values extracted using the rules
        @type values: dict
        @param protoclaims: the dict of claims to add
        @type protoclaims: dict
        """
        if values[u'built.shipyard'] or values[u'launched.shipyard']:
            shipyard = helpers.bundle_values(
                [values[u'built.shipyard'],
                 values[u'launched.shipyard']])
            shipyard = list(set(shipyard))
            if len(shipyard) > 1:
                pywikibot.output(u'Found multiple shipyards, not sure how '
                                 u'to proceed: %s' % values[u'identifier'])
            else:
                protoclaims[u'P176'] = WD.Statement(
                    self.kulturnav2Wikidata(
                        shipyard[0]))

    def set_registration_no(self, values, protoclaims):
        """Identify registration number (P879) and add to claims.

        Adds the claim to the protoclaims dict.

        @param values: the values extracted using the rules
        @type values: dict
        @param protoclaims: the dict of claims to add
        @type protoclaims: dict
        """
        values_target = values['navalVessel.registration']

        if values_target:
            values_target = helpers.listify(values_target)
            claims = []
            for val in values_target:
                if val['type'] == self.IKNO_K:
                    # only one type is currently mapped
                    claims.append(WD.Statement(val['number']))
            if claims:
                protoclaims[u'P879'] = claims

    def set_subgroup(self, values, protoclaims):
        """Identify subgroup (P279) and add to claims.

        Adds the claim to the protoclaims dict.

        @param values: the values extracted using the rules
        @type values: dict
        @param protoclaims: the dict of claims to add
        @type protoclaims: dict
        """
        if values.get(u'navalVessel.type'):
            claims = []
            for t in values[u'navalVessel.type']:
                item = self.kulturnav2Wikidata(t)
                if item:
                    claims.append(WD.Statement(item))
            if claims:
                protoclaims[u'P279'] = claims

    def set_homeport(self, values, protoclaims):
        """Identify homePort (P504) and add, with start/end dates, to claims.

        Adds the claim to the protoclaims dict.

        @param values: the values extracted using the rules
        @type values: dict
        @param protoclaims: the dict of claims to add
        @type protoclaims: dict
        """
        prop = u'P504'
        target_values = values[u'homePort']
        main_key = 'location'

        if target_values:
            target_values = helpers.listify(target_values)
            claims = []
            for val in target_values:
                claim = WD.Statement(
                    self.location2Wikidata(val[main_key]))
                claims.append(
                    helpers.add_start_end_qualifiers(
                        claim,
                        val[u'start'],
                        val[u'end']))
            if claims:
                protoclaims[prop] = claims

    def set_type_and_class(self, values, protoclaims):
        """Identify type (P31) and class (P289) and add to claims.

        Adds the claim to the protoclaims dict.

        @param values: the values extracted using the rules
        @type values: dict
        @param protoclaims: the dict of claims to add
        @type protoclaims: dict
        """
        if values.get(u'navalVessel.type'):
            ship_class = []
            ship_type = []
            for val in values[u'navalVessel.type']:
                item = self.kulturnav2Wikidata(val)
                if item:
                    q = int(item.title()[1:])
                    if q in self.class_list:
                        ship_class.append(WD.Statement(item))
                    elif q in self.type_list:
                        ship_type.append(WD.Statement(item))
                    else:
                        pywikibot.output(u'Q%d not matched as either ship'
                                         u'type or ship class' % q)
            if ship_class:
                protoclaims[u'P289'] = ship_class
            if ship_type:
                protoclaims[u'P31'] = ship_type

    def set_owner(self, values, protoclaims):
        """Identify owner (P127) and add, with start/end dates, to claims.

        Adds the claim to the protoclaims dict.

        @param values: the values extracted using the rules
        @type values: dict
        @param protoclaims: the dict of claims to add
        @type protoclaims: dict
        """
        prop = u'P127'
        target_values = values[u'agent.ownership']
        main_key = 'owner'
        self.set_claim_with_start_and_end(
            prop, target_values, main_key, protoclaims)

    def set_constructor(self, values, protoclaims):
        """Identify constructor(s)/designers (P287) and add to claims.

        Adds the claim to the protoclaims dict.

        @param values: the values extracted using the rules
        @type values: dict
        @param protoclaims: the dict of claims to add
        @type protoclaims: dict
        """
        prop = u'P287'
        target_values = values[u'constructor']
        main_key = 'constructedBy'
        self.set_claim_with_start_and_end(
            prop, target_values, main_key, protoclaims)

    def set_is_instance(self, qid, protoclaims):
        """Set instance_of (P31) to the given Q no.

        Adds the claim, with the suitable property, to the protoclaims dict.

        @param qid: the Q-no for the claim (with or without "Q")
        @type qid: str
        @param protoclaims: the dict of claims to add
        @type protoclaims: dict
        """
        protoclaims[u'P31'] = WD.Statement(
            self.wd.QtoItemPage(qid))

    def set_location(self, values, protoclaims):
        """Identify a location and its type then add to claims.

        Adds the claim, with the suitable property, to the protoclaims dict.

        @param values: the values extracted using the rules
        @type values: dict
        @param protoclaims: the dict of claims to add
        @type protoclaims: dict
        """
        if values.get(u'location'):
            if isinstance(values[u'location'], list):
                pywikibot.output('No support for multiple locations yet')
                return

            location_q = self.location2Wikidata(values[u'location'])
            prop = self.getLocationProperty(location_q)
            if prop:
                protoclaims[prop] = WD.Statement(
                    self.location2Wikidata(values[u'location']))

    def set_location_qualifier(self, values, key, statement):
        """Add a location (P279) qualifier to a statement.

        @param values: the values extracted using the rules
        @type values: dict
        @param key: the key to which the location is associated
            e.g. built for built.location
        @type key: str
        @param statement: statment to add qualifier to
        @type statement: WD.Statement
        @return: if qualifier was found
        @rtype: bool
        """
        location_key = u'%s.location' % key
        if not values[location_key]:
            return False
        statement.addQualifier(
            WD.Qualifier(
                P=self.PLACE_P,
                itis=self.location2Wikidata(values[location_key])))
        return True

    def set_ship_events(self, values, protoclaims):
        """Identify any events (P793) for a ship then add to claims.

        Adds the claim(s) to the protoclaims dict.
        Events are only added IFF they have an associated date.
        @todo: commissioned: Q14475832

        @param values: the values extracted using the rules
        @type values: dict
        @param protoclaims: the dict of claims to add
        @type protoclaims: dict
        """
        events = []

        # built: Q474200
        event = WD.Statement(self.wd.QtoItemPage('Q474200'))
        if self.set_date_qualifier(values, 'built', event,
                                   prop=helpers.END_P):
            self.set_location_qualifier(values, 'built', event)
            # u'built.shipyard'
            events.append(event)

        # launched: Q596643
        event = WD.Statement(self.wd.QtoItemPage('Q596643'))
        if self.set_date_qualifier(values, 'launched', event):
            # u'launched.shipyard'
            events.append(event)

        # decommissioned: Q7497952
        event = WD.Statement(self.wd.QtoItemPage('Q7497952'))
        if self.set_date_qualifier(values, 'decommissioned', event):
            events.append(event)

        # set all events
        if events:
            protoclaims[u'P793'] = events

    def set_date_qualifier(self, values, key, statement, prop=None):
        """Add a date qualifier to a statement.

        @param values: the values extracted using the rules
        @type values: dict
        @param key: the key to which the location is associated
            e.g. built for built.location
        @type key: str
        @param statement: statment to add qualifier to
        @type statement: WD.Statement
        @param prop: the property to use, defaults to self.TIME_P/P585
        @type prop: str
        @return: if qualifier was found
        @rtype: bool
        """
        prop = prop or self.TIME_P
        date_key = u'%s.date' % key
        if not values[date_key]:
            return False
        statement.addQualifier(
            WD.Qualifier(
                P=prop,
                itis=helpers.iso_to_WbTime(values[date_key])))
        return True

    def set_claim_with_start_and_end(self, prop, target_values, main_key,
                                     protoclaims):
        """
        Add a claim with start and end date qualifiers to protoclaims.

        Requires the value to be resolvable using kulturnav2Wikidata.

        @param prop: the property of the claim
        @type prop: str
        @param target_values: the values for the claim
        @type target_values: dict|list (of dict)|None
        @param main_key: the key for the main entry of the target_values dict
        @type main_key: str
        @param protoclaims: the dict of claims to add
        @type protoclaims: dict
        """
        if target_values:
            target_values = helpers.listify(target_values)
            claims = []
            for val in target_values:
                claim = WD.Statement(
                    self.kulturnav2Wikidata(val[main_key]))
                claims.append(
                    helpers.add_start_end_qualifiers(
                        claim,
                        val[u'start'],
                        val[u'end']))
            if claims:
                protoclaims[prop] = claims

    @staticmethod
    def prep_labels(values):
        """Combine prefLabel with altLabel and trim any comments.

        @param values: the values extracted using the rules
        @type values: dict
        @return: the combined list of scrubbed labels
        @rtype: list
        """
        # handle prefLabel together with altLabel
        pref_label = helpers.bundle_values(
            [values[u'prefLabel'],
             values[u'altLabel']])

        # remove comments from lables
        for i, v in enumerate(pref_label):
            if '(' in v['@value']:
                val = v['@value'].split('(')[0].strip()
                pref_label[i]['@value'] = val

        return pref_label

    @staticmethod
    def prep_names(values):
        """Handle altLabel together with entity.name.

        @param values: the values extracted using the rules
        @type values: dict
        @return: the combined list of names
        @rtype: list
        """
        # handle altNames together with names
        return helpers.bundle_values(
            [values[u'entity.name'],
             values[u'altLabel']])

    @staticmethod
    def prep_types(values):
        """Handle otherType together with type.

        @param values: the values extracted using the rules
        @type values: dict
        @return: the combined list of types
        @rtype: list
        """
        return helpers.bundle_values(
            [values[u'navalVessel.type'],
             values[u'navalVessel.otherType']])

    @staticmethod
    def verify_entity_code_assumption(values):
        """Verify assumption made about entity code.

        The assumption is that the entity code and signalLetters always
        coincide.

        @param values: the values extracted using the rules
        @type values: dict
        @raise pywikibot.Error
        """
        if values[u'entity.code'] and \
                values[u'navalVessel.signalLetters'] != values[u'entity.code']:
            raise pywikibot.Error(
                u'signalLetters!=code for %s: %s <> %s' %
                (values[u'identifier'],
                 values[u'navalVessel.signalLetters'],
                 values[u'entity.code']))

    @classmethod
    def get_dataset_variables(cls, *args):
        """Extract the matching dataset from the -dataset arg.

        Ideally this would be called after pywikibot variables have been
        dealt with.

        TODO: Ideally this would be handled differently e.g. by unhandled
        args in kulturnavBot.main being sent to an overloaded method. This
        would however require set_variables to be handled differently as well.

        @return: The key for the matching entry in DATASETS
        @rtype: str
        """
        if not args:
            args = pywikibot.argvu[1:]

        # allow dataset to be specified through id
        num_pairs = {}
        for k, v in cls.DATASETS.iteritems():
            num_pairs[str(v['id'])] = k

        for arg in args:
            option, sep, value = arg.partition(':')
            if option == '-dataset':
                if value in cls.DATASETS.keys():
                    return value
                elif value in num_pairs.keys():
                    return num_pairs[value]

        # if nothing found
        txt = u''
        for k, v in num_pairs.iteritems():
            txt += u'\n%s %s' % (k, v)
        pywikibot.output(u'No valid -dataset argument was found. This '
                         u'must be given by either number or name.\n'
                         'Available datasets are: %s' % txt)
        exit(1)

    @classmethod
    def main(cls, *args):
        """Start the bot from the command line."""
        # pick one dataset from DATASETS
        cls.DATASET = cls.get_dataset_variables(*args)
        variables = cls.DATASETS[cls.DATASET]

        # override variables and start bot
        cls.set_variables(
            dataset_q=variables.get('DATASET_Q'),
            dataset_id=variables.get('DATASET_ID'),
            entity_type=variables.get('ENTITY_TYPE'),
            map_tag=variables.get('MAP_TAG')
        )
        super(KulturnavBotSMM, cls).main(*args)

    @classmethod
    def run_from_list(cls, uuids, *args):
        """Start the bot with a list of uuids."""
        # pick one dataset from DATASETS
        cls.DATASET = cls.get_dataset_variables(*args)
        variables = cls.DATASETS[cls.DATASET]

        # override variables and start bot
        cls.set_variables(
            dataset_q=variables.get('DATASET_Q'),
            dataset_id=variables.get('DATASET_ID'),
            entity_type=variables.get('ENTITY_TYPE'),
            map_tag=variables.get('MAP_TAG')
        )
        super(KulturnavBotSMM, cls).run_from_list(uuids, *args)


if __name__ == "__main__":
    KulturnavBotSMM.main()
