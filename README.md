## About this repo
This repo is a collection of various individual batch uploads based on
[lokal-profil/wikidata-stuff](https://github.com/lokal-profil/wikidata-stuff)
(they were split out from that repo).

To run it you will have to install `wikidata-stuff` using:
`pip install git+https://github.com/lokal-profil/wikidata-stuff.git`

*Note*: You might have to add the `--process-dependency-links` flag to the above
command if you are running a different version of pywikibot from the required one.


These projects are mainly here for my own use and to illustrate how wikidataStuff
can be used. There is no guarantee that any of them will work at any given time
since I'm not guaranteeing that I keep them in sync with any later changes to
wikidataStuff.

As such they may also include implicit assumptions about the in-data, hard-coded
mappings or insufficient documentation. There may also be nonsensical comments
and todo's left in the code and the commit messages probably won't make much
sense either. And don't expect any tests or similar sensible and useful
precautions.

## Projects
* **`NatMus-image`**: A batch import of additional data for paintings from
  Nationalmuseum (Stockholm). The in-data was acquired a part of the processing
  done in [lokal-profil/upload_batches/Nationalmuseum/](https://github.com/lokal-profil/upload_batches/tree/master/Nationalmuseum).
* **`NatMus`**: A [sum of all paintings](http://www.wikidata.org/wiki/Wikidata:WikiProject_sum_of_all_paintings)
  bot for importing paintings from Nationalmuseum Sweden to Wikidata (via
  Europeana).
* **`WFD`**: A batch import of European water data based on the Water Framework
  Directive reporting.
* **`Riksdagsdata`**: An unfinished bot for importing data on members of Sweden's
  Riksdag from the [Riksdag data hub](http://data.riksdagen.se/).
* **`KulturNav`**
  * kulturnavBot.py: A framework for building bots to adding and/or
    sourcing statements made available through [KulturNav](http://kulturnav.org/).
    Also includes some more general pywikibot methods for Wikidata.
    * kulturnavBotArkDes: A bot for adding and/or sourcing statements about
      architects based on data curated by Swedish Centre for Architecture and
      Design ([ArkDes](http://www.arkdes.se/)) made available through KulturNav.
    * kulturnavBotSMM: A bot for adding and/or sourcing statements about
      maritime objects based on data curated by the National Maritime Museums
      ([SMM](http://www.maritima.se/)) made available through KulturNav.
    * kulturnavBotNatMus: A bot for adding and/or sourcing statements about
      artists based on data curated by the Nationalmuseum Sweden
      ([NatMus](http://www.nationalmuseum.se/)) made available through KulturNav.
  * synkedKulturnav.py: A small script for generating statistics on
    KulturNav-Wikidata connections.
