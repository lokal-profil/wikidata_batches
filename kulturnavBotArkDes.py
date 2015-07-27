#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Bot to import and source statements about Architects in KulturNav.

usage:
    python kulturnavBotArkDes.py [OPTIONS]

Author: Lokal_Profil
License: MIT

Options (may be omitted):
  -cutoff:INT       number of entries to process before terminating
  -maxHits:INT      number of items to request at a time from Kulturnav
                    (default 250)
"""
import pywikibot
from kulturnavBot import KulturnavBot

# KulturNav based
EDIT_SUMMARY = 'KulturnavBot(ArkDes)'
DATASET_ID = '2b7670e1-b44e-4064-817d-27834b03067c'
ENTITY_TYPE = 'Person'
MAP_TAG = 'entity.sameAs_s'
DATASET_Q = '17373699'


class KulturnavBotArkDes(KulturnavBot):
    """
    A bot to enrich and create information on Wikidata based on KulturNav info
    """
    ARCHITECT_Q = '42973'
    GROUP_OF_PEOPLE_Q = '16334295'
    HUMAN_Q = '5'

    def run(self, cutoff=None):
        """
        Starts the robot
        """
        rules = {
            # u'deathPlace': None,
            u'deathDate': None,
            # u'birthPlace': None,
            u'birthDate': None,
            u'firstName': None,
            u'gender': None,
            u'lastName': None,
            u'name': None,
            u'person.nationality': None
        }

        def claims(self, values):
            protoclaims = {
                u'P31': pywikibot.ItemPage(  # instance of
                    self.repo,
                    u'Q%s' % self.HUMAN_Q),
                u'P106': pywikibot.ItemPage(
                    self.repo,
                    u'Q%s' % self.ARCHITECT_Q)
                }
            # P106 occupation - fieldOfActivityOfThePerson

            #    protoclaims[u'P20'] = self.dbpedia2Wikidata(values[u'deathPlace'])
            if values[u'deathDate']:
                protoclaims[u'P570'] = self.dbDate(values[u'deathDate'])
            # if values[u'birthPlace']:
            #    protoclaims[u'P19'] = self.dbpedia2Wikidata(values[u'birthPlace'])
            if values[u'birthDate']:
                protoclaims[u'P569'] = self.dbDate(values[u'birthDate'])
            if values[u'gender']:
                protoclaims[u'P21'] = self.dbGender(values[u'gender'])
            if values[u'firstName']:
                protoclaims[u'P735'] = self.dbName(values[u'firstName'],
                                                   u'firstName')
            if values[u'lastName']:
                protoclaims[u'P734'] = self.dbName(values[u'lastName'],
                                                   u'lastName')
            if values[u'person.nationality']:
                protoclaims[u'P27'] = self.location2Wikidata(
                    values[u'person.nationality'])

            return protoclaims

        def personTest(self, hitItem):
            group_item = pywikibot.ItemPage(
                self.repo,
                u'Q%s' % self.GROUP_OF_PEOPLE_Q)
            if self.wd.hasClaim('P%s' % self.IS_A_P, group_item, hitItem):
                    pywikibot.output(u'%s is matched to a group of people, '
                                     u'FIXIT' % hitItem.title())
                    return False
            else:
                    return True

        # pass settingson to runLayout()
        self.runLayout(datasetRules=rules,
                       datasetProtoclaims=claims,
                       datasetSanityTest=personTest,
                       label=u'name',
                       shuffle=True)

    @classmethod
    def main(cls, *args):
        cls.setVariables(
            dataset_q=DATASET_Q,
            dataset_id=DATASET_ID,
            entity_type=ENTITY_TYPE,
            map_tag=MAP_TAG,
            edit_summary=EDIT_SUMMARY
        )
        super(KulturnavBotArkDes, cls).main(*args)


if __name__ == "__main__":
    KulturnavBotArkDes.main()
