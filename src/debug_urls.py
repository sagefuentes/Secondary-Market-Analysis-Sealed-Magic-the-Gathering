"""
PriceCharting URL Debugger
Checks each URL in the set list and reports:
  - HTTP status
  - Whether VGPC.chart_data was found
  - Which keys have non-zero data and how many points
  - Whether multiple sales exist per month (raw data density)

Run this before the main scraper to validate all URLs and pick the best key per set.

Usage:
    uv run python debug_urls.py
    or: python debug_urls.py > debug_report.txt
"""

import re
import json
import time
import logging
import requests
from datetime import datetime, timezone
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Full URL list — each entry is the complete PriceCharting product URL
# ---------------------------------------------------------------------------
SETS = [
    # -- Old border / vintage --
    {"set_name": "Alpha",                               "url": "https://www.pricecharting.com/game/magic-beta/booster-box",                                           "release_year": 1993, "set_type": "Core"},
    {"set_name": "Unlimited",                           "url": "https://www.pricecharting.com/game/magic-unlimited/booster-box",                                      "release_year": 1993, "set_type": "Core"},
    {"set_name": "Arabian Nights",                      "url": "https://www.pricecharting.com/game/magic-arabian-nights/booster-box",                                 "release_year": 1993, "set_type": "Standard"},
    {"set_name": "Antiquities",                         "url": "https://www.pricecharting.com/game/magic-antiquities/booster-box",                                    "release_year": 1994, "set_type": "Standard"},
    {"set_name": "Legends",                             "url": "https://www.pricecharting.com/game/magic-legends/booster-box",                                        "release_year": 1994, "set_type": "Standard"},
    {"set_name": "The Dark",                            "url": "https://www.pricecharting.com/game/magic-the-dark/booster-box",                                       "release_year": 1994, "set_type": "Standard"},
    {"set_name": "Fallen Empires",                      "url": "https://www.pricecharting.com/game/magic-fallen-empires/booster-box",                                 "release_year": 1994, "set_type": "Standard"},
    {"set_name": "Revised Edition",                     "url": "https://www.pricecharting.com/game/magic-revised/booster-box",                                        "release_year": 1994, "set_type": "Core"},
    {"set_name": "Ice Age",                             "url": "https://www.pricecharting.com/game/magic-ice-age/booster-box",                                        "release_year": 1995, "set_type": "Standard"},
    {"set_name": "4th Edition",                         "url": "https://www.pricecharting.com/game/magic-4th-edition/booster-box",                                    "release_year": 1995, "set_type": "Core"},
    {"set_name": "Homelands",                           "url": "https://www.pricecharting.com/game/magic-homelands/booster-box",                                      "release_year": 1995, "set_type": "Standard"},
    {"set_name": "Alliances",                           "url": "https://www.pricecharting.com/game/magic-alliances/booster-box",                                      "release_year": 1996, "set_type": "Standard"},
    {"set_name": "Mirage",                              "url": "https://www.pricecharting.com/game/magic-mirage/booster-box",                                         "release_year": 1996, "set_type": "Standard"},
    {"set_name": "Visions",                             "url": "https://www.pricecharting.com/game/magic-visions/booster-box",                                        "release_year": 1997, "set_type": "Standard"},
    {"set_name": "Weatherlight",                        "url": "https://www.pricecharting.com/game/magic-weatherlight/booster-box",                                   "release_year": 1997, "set_type": "Standard"},
    {"set_name": "Tempest",                             "url": "https://www.pricecharting.com/game/magic-tempest/booster-box",                                        "release_year": 1997, "set_type": "Standard"},
    {"set_name": "Portal",                              "url": "https://www.pricecharting.com/game/magic-portal/booster-box",                                         "release_year": 1997, "set_type": "Standard"},
    {"set_name": "5th Edition",                         "url": "https://www.pricecharting.com/game/magic-5th-edition/booster-box",                                    "release_year": 1997, "set_type": "Core"},
    {"set_name": "Stronghold",                          "url": "https://www.pricecharting.com/game/magic-stronghold/booster-box",                                     "release_year": 1998, "set_type": "Standard"},
    {"set_name": "Exodus",                              "url": "https://www.pricecharting.com/game/magic-exodus/booster-box",                                         "release_year": 1998, "set_type": "Standard"},
    {"set_name": "Portal Second Age",                   "url": "https://www.pricecharting.com/game/magic-portal-second-age/booster-box",                              "release_year": 1998, "set_type": "Standard"},
    {"set_name": "Urza's Saga",                         "url": "https://www.pricecharting.com/game/magic-urzas-saga/booster-box",                                     "release_year": 1998, "set_type": "Standard"},
    {"set_name": "Urza's Legacy",                       "url": "https://www.pricecharting.com/game/magic-urzas-legacy/booster-box",                                   "release_year": 1999, "set_type": "Standard"},
    {"set_name": "Urza's Destiny",                      "url": "https://www.pricecharting.com/game/magic-urzas-destiny/booster-box",                                  "release_year": 1999, "set_type": "Standard"},
    {"set_name": "6th Edition",                         "url": "https://www.pricecharting.com/game/magic-6th-edition/booster-box",                                    "release_year": 1999, "set_type": "Core"},
    {"set_name": "Mercadian Masques",                   "url": "https://www.pricecharting.com/game/magic-mercadian-masques/booster-box",                              "release_year": 1999, "set_type": "Standard"},
    {"set_name": "Nemesis",                             "url": "https://www.pricecharting.com/game/magic-nemesis/booster-box",                                        "release_year": 2000, "set_type": "Standard"},
    {"set_name": "Prophecy",                            "url": "https://www.pricecharting.com/game/magic-prophecy/booster-box",                                       "release_year": 2000, "set_type": "Standard"},
    {"set_name": "Invasion",                            "url": "https://www.pricecharting.com/game/magic-invasion/booster-box",                                       "release_year": 2000, "set_type": "Standard"},
    {"set_name": "Portal Three Kingdoms",               "url": "https://www.pricecharting.com/game/magic-portal-three-kingdoms/booster-box",                          "release_year": 2000, "set_type": "Standard"},
    {"set_name": "Planeshift",                          "url": "https://www.pricecharting.com/game/magic-planeshift/booster-box",                                     "release_year": 2001, "set_type": "Standard"},
    {"set_name": "Apocalypse",                          "url": "https://www.pricecharting.com/game/magic-apocalypse/booster-box",                                     "release_year": 2001, "set_type": "Standard"},
    {"set_name": "7th Edition",                         "url": "https://www.pricecharting.com/game/magic-7th-edition/booster-box",                                    "release_year": 2001, "set_type": "Core"},
    {"set_name": "Odyssey",                             "url": "https://www.pricecharting.com/game/magic-odyssey/booster-box",                                        "release_year": 2001, "set_type": "Standard"},
    {"set_name": "Torment",                             "url": "https://www.pricecharting.com/game/magic-torment/booster-box",                                        "release_year": 2002, "set_type": "Standard"},
    {"set_name": "Judgment",                            "url": "https://www.pricecharting.com/game/magic-judgment/booster-box",                                       "release_year": 2002, "set_type": "Standard"},
    {"set_name": "Onslaught",                           "url": "https://www.pricecharting.com/game/magic-onslaught/booster-box",                                      "release_year": 2002, "set_type": "Standard"},
    {"set_name": "Legions",                             "url": "https://www.pricecharting.com/game/magic-legions/booster-box",                                        "release_year": 2003, "set_type": "Standard"},
    {"set_name": "Scourge",                             "url": "https://www.pricecharting.com/game/magic-scourge/booster-box",                                        "release_year": 2003, "set_type": "Standard"},
    {"set_name": "8th Edition",                         "url": "https://www.pricecharting.com/game/magic-8th-edition/booster-box",                                    "release_year": 2003, "set_type": "Core"},
    {"set_name": "Mirrodin",                            "url": "https://www.pricecharting.com/game/magic-mirrodin/booster-box",                                       "release_year": 2003, "set_type": "Standard"},
    {"set_name": "Darksteel",                           "url": "https://www.pricecharting.com/game/magic-darksteel/booster-box",                                      "release_year": 2004, "set_type": "Standard"},
    {"set_name": "Fifth Dawn",                          "url": "https://www.pricecharting.com/game/magic-fifth-dawn/booster-box",                                     "release_year": 2004, "set_type": "Standard"},
    {"set_name": "Champions of Kamigawa",               "url": "https://www.pricecharting.com/game/magic-champions-of-kamigawa/booster-box",                          "release_year": 2004, "set_type": "Standard"},
    {"set_name": "Betrayers of Kamigawa",               "url": "https://www.pricecharting.com/game/magic-betrayers-of-kamigawa/booster-box",                          "release_year": 2005, "set_type": "Standard"},
    {"set_name": "Ravnica City of Guilds",              "url": "https://www.pricecharting.com/game/magic-ravnica/booster-box",                                        "release_year": 2005, "set_type": "Standard"},
    {"set_name": "Time Spiral",                         "url": "https://www.pricecharting.com/game/magic-time-spiral/booster-box",                                    "release_year": 2006, "set_type": "Standard"},
    {"set_name": "Planar Chaos",                        "url": "https://www.pricecharting.com/game/magic-planar-chaos/booster-box",                                   "release_year": 2007, "set_type": "Standard"},
    {"set_name": "Conflux",                             "url": "https://www.pricecharting.com/game/magic-conflux/booster-box",                                        "release_year": 2009, "set_type": "Standard"},
    {"set_name": "Rise of the Eldrazi",                 "url": "https://www.pricecharting.com/game/magic-rise-of-the-eldrazi/booster-box",                            "release_year": 2010, "set_type": "Standard"},
    {"set_name": "M10",                                 "url": "https://www.pricecharting.com/game/magic-m10/booster-box",                                            "release_year": 2009, "set_type": "Core"},
    {"set_name": "Scars of Mirrodin",                   "url": "https://www.pricecharting.com/game/magic-scars-of-mirrodin/booster-box",                              "release_year": 2010, "set_type": "Standard"},
    {"set_name": "New Phyrexia",                        "url": "https://www.pricecharting.com/game/magic-new-phyrexia/booster-box",                                   "release_year": 2011, "set_type": "Standard"},
    {"set_name": "Core Set 2012",                       "url": "https://www.pricecharting.com/game/magic-core-set-2012/booster-box",                                  "release_year": 2011, "set_type": "Core"},
    {"set_name": "Innistrad",                           "url": "https://www.pricecharting.com/game/magic-innistrad/booster-box",                                      "release_year": 2011, "set_type": "Standard"},
    {"set_name": "Dark Ascension",                      "url": "https://www.pricecharting.com/game/magic-dark-ascension/booster-box",                                 "release_year": 2012, "set_type": "Standard"},
    {"set_name": "Core Set 2013",                       "url": "https://www.pricecharting.com/game/magic-core-set-2013/booster-box",                                  "release_year": 2012, "set_type": "Core"},
    {"set_name": "Return to Ravnica",                   "url": "https://www.pricecharting.com/game/magic-return-to-ravnica/booster-box",                              "release_year": 2012, "set_type": "Standard"},
    {"set_name": "Modern Masters",                      "url": "https://www.pricecharting.com/game/magic-modern-masters/booster-box",                                 "release_year": 2013, "set_type": "Masters"},
    {"set_name": "Born of the Gods",                    "url": "https://www.pricecharting.com/game/magic-born-of-the-gods/booster-box",                               "release_year": 2014, "set_type": "Standard"},
    {"set_name": "M14",                                 "url": "https://www.pricecharting.com/game/magic-m14/booster-box",                                            "release_year": 2013, "set_type": "Core"},
    {"set_name": "Theros",                              "url": "https://www.pricecharting.com/game/magic-theros/booster-box",                                         "release_year": 2013, "set_type": "Standard"},
    {"set_name": "Conspiracy",                          "url": "https://www.pricecharting.com/game/magic-conspiracy/booster-box",                                     "release_year": 2014, "set_type": "Special"},
    {"set_name": "Khans of Tarkir",                     "url": "https://www.pricecharting.com/game/magic-khans-of-tarkir/booster-box",                                "release_year": 2014, "set_type": "Standard"},
    {"set_name": "Fate Reforged",                       "url": "https://www.pricecharting.com/game/magic-fate-reforged/booster-box",                                  "release_year": 2015, "set_type": "Standard"},
    {"set_name": "Modern Masters 2015",                 "url": "https://www.pricecharting.com/game/magic-modern-masters-2015/booster-box",                            "release_year": 2015, "set_type": "Masters"},
    {"set_name": "Battle for Zendikar",                 "url": "https://www.pricecharting.com/game/magic-battle-for-zendikar/booster-box",                            "release_year": 2015, "set_type": "Standard"},
    {"set_name": "Conspiracy Take the Crown",           "url": "https://www.pricecharting.com/game/magic-conspiracy-take-the-crown/booster-box",                      "release_year": 2016, "set_type": "Special"},
    {"set_name": "Eternal Masters",                     "url": "https://www.pricecharting.com/game/magic-eternal-masters/booster-box",                                "release_year": 2016, "set_type": "Masters"},
    {"set_name": "Eldritch Moon",                       "url": "https://www.pricecharting.com/game/magic-eldritch-moon/booster-box",                                  "release_year": 2016, "set_type": "Standard"},
    {"set_name": "Shadows over Innistrad",              "url": "https://www.pricecharting.com/game/magic-shadows-over-innistrad/booster-box",                         "release_year": 2016, "set_type": "Standard"},
    {"set_name": "Kaladesh",                            "url": "https://www.pricecharting.com/game/magic-kaladesh/booster-box",                                       "release_year": 2016, "set_type": "Standard"},
    {"set_name": "Aether Revolt",                       "url": "https://www.pricecharting.com/game/magic-aether-revolt/booster-box",                                  "release_year": 2017, "set_type": "Standard"},
    {"set_name": "Amonkhet",                            "url": "https://www.pricecharting.com/game/magic-amonkhet/booster-box",                                       "release_year": 2017, "set_type": "Standard"},
    {"set_name": "Hour of Devastation",                 "url": "https://www.pricecharting.com/game/magic-hour-of-devastation/booster-box",                            "release_year": 2017, "set_type": "Standard"},
    {"set_name": "Ixalan",                              "url": "https://www.pricecharting.com/game/magic-ixalan/booster-box",                                         "release_year": 2017, "set_type": "Standard"},
    {"set_name": "Rivals of Ixalan",                    "url": "https://www.pricecharting.com/game/magic-rivals-of-ixalan/booster-box",                               "release_year": 2018, "set_type": "Standard"},
    {"set_name": "Dominaria",                           "url": "https://www.pricecharting.com/game/magic-dominaria/booster-box",                                      "release_year": 2018, "set_type": "Standard"},
    {"set_name": "Masters 25",                          "url": "https://www.pricecharting.com/game/magic-masters-25/booster-box",                                     "release_year": 2018, "set_type": "Masters"},
    {"set_name": "Core Set 2019",                       "url": "https://www.pricecharting.com/game/magic-core-set-2019/booster-box",                                  "release_year": 2018, "set_type": "Core"},
    {"set_name": "Guilds of Ravnica",                   "url": "https://www.pricecharting.com/game/magic-guilds-of-ravnica/booster-box",                              "release_year": 2018, "set_type": "Standard"},
    {"set_name": "Ultimate Masters",                    "url": "https://www.pricecharting.com/game/magic-ultimate-masters/booster-box",                               "release_year": 2018, "set_type": "Masters"},
    {"set_name": "Ravnica Allegiance",                  "url": "https://www.pricecharting.com/game/magic-ravnica-allegiance/booster-box",                             "release_year": 2019, "set_type": "Standard"},
    {"set_name": "War of the Spark",                    "url": "https://www.pricecharting.com/game/magic-war-of-the-spark/booster-box",                               "release_year": 2019, "set_type": "Standard"},
    {"set_name": "Modern Horizons",                     "url": "https://www.pricecharting.com/game/magic-modern-horizons/booster-box",                                "release_year": 2019, "set_type": "Masters"},
    {"set_name": "Core Set 2020",                       "url": "https://www.pricecharting.com/game/magic-core-set-2020/booster-box",                                  "release_year": 2019, "set_type": "Core"},
    {"set_name": "Throne of Eldraine",                  "url": "https://www.pricecharting.com/game/magic-throne-of-eldraine/booster-box",                             "release_year": 2019, "set_type": "Standard"},
    {"set_name": "Theros Beyond Death",                 "url": "https://www.pricecharting.com/game/magic-theros-beyond-death/booster-box",                            "release_year": 2020, "set_type": "Standard"},
    {"set_name": "Ikoria Lair of Behemoths",            "url": "https://www.pricecharting.com/game/magic-ikoria-lair-of-behemoths/booster-box",                       "release_year": 2020, "set_type": "Standard"},
    {"set_name": "Jumpstart",                           "url": "https://www.pricecharting.com/game/magic-jumpstart/booster-box",                                      "release_year": 2020, "set_type": "Special"},
    {"set_name": "Mystery Booster",                     "url": "https://www.pricecharting.com/game/magic-mystery-booster/booster-box",                                "release_year": 2020, "set_type": "Special"},
    {"set_name": "Zendikar Rising",                     "url": "https://www.pricecharting.com/game/magic-zendikar-rising/booster-box",                                "release_year": 2020, "set_type": "Standard"},
    {"set_name": "Kaldheim",                            "url": "https://www.pricecharting.com/game/magic-kaldheim/booster-box-set",                                   "release_year": 2021, "set_type": "Standard"},
    {"set_name": "Strixhaven",                          "url": "https://www.pricecharting.com/game/magic-strixhaven-school-of-mages/booster-box",                     "release_year": 2021, "set_type": "Standard"},
    {"set_name": "Modern Horizons 2",                   "url": "https://www.pricecharting.com/game/magic-modern-horizons-2/booster-box",                              "release_year": 2021, "set_type": "Masters"},
    {"set_name": "Adventures in the Forgotten Realms",  "url": "https://www.pricecharting.com/game/magic-adventures-in-the-forgotten-realms/booster-box",             "release_year": 2021, "set_type": "Universes Beyond"},
    {"set_name": "Innistrad Midnight Hunt",             "url": "https://www.pricecharting.com/game/magic-innistrad-midnight-hunt/booster-box",                        "release_year": 2021, "set_type": "Standard"},
    {"set_name": "Innistrad Crimson Vow",               "url": "https://www.pricecharting.com/game/magic-innistrad-crimson-vow/booster-box",                          "release_year": 2021, "set_type": "Standard"},
    {"set_name": "Commander Legends",                   "url": "https://www.pricecharting.com/game/magic-commander-legends/booster-box",                              "release_year": 2020, "set_type": "Commander"},
    {"set_name": "The Brothers War",                    "url": "https://www.pricecharting.com/game/magic-brother%27s-war/draft-booster-box",                          "release_year": 2022, "set_type": "Standard"},
    {"set_name": "Double Masters 2022",                 "url": "https://www.pricecharting.com/game/magic-double-masters-2022/booster-box",                            "release_year": 2022, "set_type": "Masters"},
    {"set_name": "Commander Legends Battle for Baldurs Gate", "url": "https://www.pricecharting.com/game/magic-commander-legends-battle-for-baldur%27s-gate/booster-box", "release_year": 2022, "set_type": "Commander"},
    {"set_name": "March of the Machine",                "url": "https://www.pricecharting.com/game/magic-march-of-the-machine/booster-box",                           "release_year": 2023, "set_type": "Standard"},
    {"set_name": "Wilds of Eldraine",                   "url": "https://www.pricecharting.com/game/magic-wilds-of-eldraine/booster-box",                              "release_year": 2023, "set_type": "Standard"},
    {"set_name": "Lost Caverns of Ixalan (Draft)",      "url": "https://www.pricecharting.com/game/magic-lost-caverns-of-ixalan/booster-box-draft",                   "release_year": 2023, "set_type": "Standard"},
    {"set_name": "Lost Caverns of Ixalan",              "url": "https://www.pricecharting.com/game/magic-lost-caverns-of-ixalan/booster-box",                         "release_year": 2023, "set_type": "Standard"},
    {"set_name": "Commander Masters",                   "url": "https://www.pricecharting.com/game/magic-commander-masters/booster-box",                              "release_year": 2023, "set_type": "Commander"},
    {"set_name": "Time Spiral Remastered",              "url": "https://www.pricecharting.com/game/magic-time-spiral-remastered/booster-box",                         "release_year": 2021, "set_type": "Masters"},
    {"set_name": "Innistrad Remastered",                "url": "https://www.pricecharting.com/game/magic-innistrad-remastered/booster-box",                           "release_year": 2025, "set_type": "Masters"},
    {"set_name": "Modern Horizons 3 (Play)",            "url": "https://www.pricecharting.com/game/magic-modern-horizons-3/booster-box-play",                         "release_year": 2024, "set_type": "Masters"},
    {"set_name": "Foundations (Play)",                  "url": "https://www.pricecharting.com/game/magic-foundations/booster-box-play",                               "release_year": 2024, "set_type": "Core"},
    {"set_name": "Aetherdrift (Play)",                  "url": "https://www.pricecharting.com/game/magic-aetherdrift/booster-box-play",                               "release_year": 2025, "set_type": "Standard"},
    {"set_name": "Tarkir Dragonstorm (Play)",           "url": "https://www.pricecharting.com/game/magic-tarkir-dragonstorm/booster-box-play",                        "release_year": 2025, "set_type": "Standard"},
    # -- Un-Sets --
    {"set_name": "Unglued",                             "url": "https://www.pricecharting.com/game/magic-unglued/booster-box",                                        "release_year": 1998, "set_type": "Un-Set"},
    {"set_name": "Unhinged",                            "url": "https://www.pricecharting.com/game/magic-unhinged/booster-box",                                       "release_year": 2004, "set_type": "Un-Set"},
    {"set_name": "Unfinity (Draft)",                    "url": "https://www.pricecharting.com/game/magic-unfinity/booster-box-draft",                                 "release_year": 2022, "set_type": "Un-Set"},
    # -- Universes Beyond --
    {"set_name": "Marvel Spider-Man (Play)",            "url": "https://www.pricecharting.com/game/magic-marvel-spider-man/play-booster-box",                         "release_year": 2025, "set_type": "Universes Beyond"},
    {"set_name": "Teenage Mutant Ninja Turtles",        "url": "https://www.pricecharting.com/game/magic-teenage-mutant-ninja-turtles/play-booster-display",          "release_year": 2025, "set_type": "Universes Beyond"},
    {"set_name": "Final Fantasy (Play)",                "url": "https://www.pricecharting.com/game/magic-final-fantasy/booster-box-play",                             "release_year": 2025, "set_type": "Universes Beyond"},
    {"set_name": "Magic Origins",                       "url": "https://www.pricecharting.com/game/magic-magic-origins/booster-box",                                  "release_year": 2015, "set_type": "Core"},
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_DELAY_SECONDS = 1.5


def check_url(set_info: dict, session: requests.Session) -> dict:
    result = {
        "set_name": set_info["set_name"],
        "url": set_info["url"],
        "status": None,
        "chart_data_found": False,
        "keys_with_data": [],
        "best_key": None,
        "total_points": 0,
        "date_range": None,
        "notes": "",
    }

    try:
        resp = session.get(set_info["url"], headers=HEADERS, timeout=15)
        result["status"] = resp.status_code
        if resp.status_code != 200:
            result["notes"] = f"HTTP {resp.status_code}"
            return result
    except requests.RequestException as e:
        result["status"] = "ERROR"
        result["notes"] = str(e)
        return result

    match = re.search(r'VGPC\.chart_data\s*=\s*(\{.*?\})\s*;', resp.text, re.DOTALL)
    if not match:
        result["notes"] = "VGPC.chart_data not found in page"
        return result

    result["chart_data_found"] = True

    try:
        chart_data = json.loads(match.group(1))
    except json.JSONDecodeError:
        result["notes"] = "JSON parse error"
        return result

    # Check each key for non-zero data
    key_summary = {}
    for key, values in chart_data.items():
        non_zero = [(ts, v) for ts, v in values if v != 0]
        if non_zero:
            dates = [datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m") for ts, _ in non_zero]
            key_summary[key] = {
                "count": len(non_zero),
                "date_range": f"{dates[0]} → {dates[-1]}",
                "latest_price": round(non_zero[-1][1] / 100, 2),
            }

    result["keys_with_data"] = list(key_summary.keys())

    # Check for multiple data points per month (sub-monthly granularity)
    for key in ["used", "new", "cib"]:
        if key in chart_data:
            non_zero = [(ts, v) for ts, v in chart_data[key] if v != 0]
            if len(non_zero) > 1:
                # Check if any two consecutive timestamps are less than 20 days apart
                timestamps = [ts for ts, _ in non_zero]
                gaps = [(timestamps[i+1] - timestamps[i]) / (1000 * 60 * 60 * 24)
                        for i in range(len(timestamps) - 1)]
                min_gap = min(gaps) if gaps else 999
                if min_gap < 20:
                    result["notes"] += f" [{key}: sub-monthly data, min gap {min_gap:.0f}d]"

    # Pick best key: prefer 'used', then 'new', then whatever has most points
    best_key = None
    if "used" in key_summary:
        best_key = "used"
    elif "new" in key_summary:
        best_key = "new"
    elif key_summary:
        best_key = max(key_summary, key=lambda k: key_summary[k]["count"])

    if best_key:
        result["best_key"] = best_key
        result["total_points"] = key_summary[best_key]["count"]
        result["date_range"] = key_summary[best_key]["date_range"]

    return result


def main():
    session = requests.Session()
    session.get("https://www.pricecharting.com/", headers=HEADERS, timeout=15)

    results = []
    ok, skipped = 0, 0

    log.info("Checking %d URLs...\n", len(SETS))
    for i, set_info in enumerate(SETS, 1):
        log.info("[%d/%d] %s", i, len(SETS), set_info["set_name"])
        r = check_url(set_info, session)
        results.append(r)

        status_str = (
            f"  ✓ {r['best_key']:8s} {r['total_points']:3d} pts  {r['date_range']}"
            if r["best_key"]
            else f"  ✗ {r['notes']}"
        )
        log.info(status_str)
        if r["best_key"]:
            ok += 1
        else:
            skipped += 1
        time.sleep(REQUEST_DELAY_SECONDS)

    print(f"\n{'='*70}")
    print(f"SUMMARY: {ok} sets with data, {skipped} failed/missing")
    print(f"{'='*70}")

    print("\n--- FAILED / MISSING DATA ---")
    for r in results:
        if not r["best_key"]:
            print(f"  {r['set_name']:<45} {r['status']}  {r['notes']}")

    print("\n--- SETS WITH DATA (key, points, date range) ---")
    for r in results:
        if r["best_key"]:
            print(f"  {r['set_name']:<45} {r['best_key']:8s}  {r['total_points']:3d} pts  {r['date_range']}")

    print("\n--- KEYS AVAILABLE PER SET ---")
    for r in results:
        if r["keys_with_data"]:
            print(f"  {r['set_name']:<45} {r['keys_with_data']}")


if __name__ == "__main__":
    main()
