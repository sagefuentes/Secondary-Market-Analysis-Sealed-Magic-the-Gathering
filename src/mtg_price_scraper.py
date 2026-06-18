"""
MTG Booster Box Price Scraper
Source: PriceCharting.com (secondary market / completed sales)

Extracts monthly price history from VGPC.chart_data["used"] embedded in
each product page. Outputs a single long-format CSV ready for Power BI / Tableau.

Columns:
    set_name            Display name of the set
    set_type            Core / Standard / Masters / Commander / Special /
                        Un-Set / Beta
    is_universes_beyond 1 if the set is a Universes Beyond product, else 0
    release_year        Year the set was released
    date                First day of the month the price was recorded (YYYY-MM-DD)
    price_usd           Secondary market price in USD
    source_url          PriceCharting URL the data was scraped from

Usage:
    uv add requests beautifulsoup4 pandas
    python mtg_price_scraper.py
"""

import re
import json
import time
import logging
import requests
import pandas as pd
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

SETS = [
    # -- Beta --
    {"set_name": "Beta",                                    "url": "https://www.pricecharting.com/game/magic-beta/booster-box",                                                "release_year": 1993, "set_type": "Core",          "is_universes_beyond": 0},
    # -- Vintage / Old Border --
    {"set_name": "Unlimited",                               "url": "https://www.pricecharting.com/game/magic-unlimited/booster-box",                                           "release_year": 1993, "set_type": "Core",           "is_universes_beyond": 0},
    {"set_name": "Arabian Nights",                          "url": "https://www.pricecharting.com/game/magic-arabian-nights/booster-box",                                      "release_year": 1993, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Antiquities",                             "url": "https://www.pricecharting.com/game/magic-antiquities/booster-box",                                         "release_year": 1994, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Legends",                                 "url": "https://www.pricecharting.com/game/magic-legends/booster-box",                                             "release_year": 1994, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "The Dark",                                "url": "https://www.pricecharting.com/game/magic-the-dark/booster-box",                                            "release_year": 1994, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Fallen Empires",                          "url": "https://www.pricecharting.com/game/magic-fallen-empires/booster-box",                                      "release_year": 1994, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Revised Edition",                         "url": "https://www.pricecharting.com/game/magic-revised/booster-box",                                             "release_year": 1994, "set_type": "Core",           "is_universes_beyond": 0},
    {"set_name": "Ice Age",                                 "url": "https://www.pricecharting.com/game/magic-ice-age/booster-box",                                             "release_year": 1995, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "4th Edition",                             "url": "https://www.pricecharting.com/game/magic-4th-edition/booster-box",                                         "release_year": 1995, "set_type": "Core",           "is_universes_beyond": 0},
    {"set_name": "Homelands",                               "url": "https://www.pricecharting.com/game/magic-homelands/booster-box",                                           "release_year": 1995, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Alliances",                               "url": "https://www.pricecharting.com/game/magic-alliances/booster-box",                                           "release_year": 1996, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Mirage",                                  "url": "https://www.pricecharting.com/game/magic-mirage/booster-box",                                              "release_year": 1996, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Visions",                                 "url": "https://www.pricecharting.com/game/magic-visions/booster-box",                                             "release_year": 1997, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Weatherlight",                            "url": "https://www.pricecharting.com/game/magic-weatherlight/booster-box",                                        "release_year": 1997, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Tempest",                                 "url": "https://www.pricecharting.com/game/magic-tempest/booster-box",                                             "release_year": 1997, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Portal",                                  "url": "https://www.pricecharting.com/game/magic-portal/booster-box",                                              "release_year": 1997, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "5th Edition",                             "url": "https://www.pricecharting.com/game/magic-5th-edition/booster-box",                                         "release_year": 1997, "set_type": "Core",           "is_universes_beyond": 0},
    {"set_name": "Stronghold",                              "url": "https://www.pricecharting.com/game/magic-stronghold/booster-box",                                          "release_year": 1998, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Exodus",                                  "url": "https://www.pricecharting.com/game/magic-exodus/booster-box",                                              "release_year": 1998, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Portal Second Age",                       "url": "https://www.pricecharting.com/game/magic-portal-second-age/booster-box",                                   "release_year": 1998, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Unglued",                                 "url": "https://www.pricecharting.com/game/magic-unglued/booster-box",                                             "release_year": 1998, "set_type": "Un-Set",         "is_universes_beyond": 0},
    {"set_name": "Urza's Saga",                             "url": "https://www.pricecharting.com/game/magic-urzas-saga/booster-box",                                          "release_year": 1998, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Urza's Legacy",                           "url": "https://www.pricecharting.com/game/magic-urzas-legacy/booster-box",                                        "release_year": 1999, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Urza's Destiny",                          "url": "https://www.pricecharting.com/game/magic-urzas-destiny/booster-box",                                       "release_year": 1999, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "6th Edition",                             "url": "https://www.pricecharting.com/game/magic-6th-edition/booster-box",                                         "release_year": 1999, "set_type": "Core",           "is_universes_beyond": 0},
    {"set_name": "Mercadian Masques",                       "url": "https://www.pricecharting.com/game/magic-mercadian-masques/booster-box",                                   "release_year": 1999, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Nemesis",                                 "url": "https://www.pricecharting.com/game/magic-nemesis/booster-box",                                             "release_year": 2000, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Prophecy",                                "url": "https://www.pricecharting.com/game/magic-prophecy/booster-box",                                            "release_year": 2000, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Invasion",                                "url": "https://www.pricecharting.com/game/magic-invasion/booster-box",                                            "release_year": 2000, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Portal Three Kingdoms",                   "url": "https://www.pricecharting.com/game/magic-portal-three-kingdoms/booster-box",                               "release_year": 2000, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Planeshift",                              "url": "https://www.pricecharting.com/game/magic-planeshift/booster-box",                                          "release_year": 2001, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Apocalypse",                              "url": "https://www.pricecharting.com/game/magic-apocalypse/booster-box",                                          "release_year": 2001, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "7th Edition",                             "url": "https://www.pricecharting.com/game/magic-7th-edition/booster-box",                                         "release_year": 2001, "set_type": "Core",           "is_universes_beyond": 0},
    {"set_name": "Odyssey",                                 "url": "https://www.pricecharting.com/game/magic-odyssey/booster-box",                                             "release_year": 2001, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Torment",                                 "url": "https://www.pricecharting.com/game/magic-torment/booster-box",                                             "release_year": 2002, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Judgment",                                "url": "https://www.pricecharting.com/game/magic-judgment/booster-box",                                            "release_year": 2002, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Onslaught",                               "url": "https://www.pricecharting.com/game/magic-onslaught/booster-box",                                           "release_year": 2002, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Legions",                                 "url": "https://www.pricecharting.com/game/magic-legions/booster-box",                                             "release_year": 2003, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Scourge",                                 "url": "https://www.pricecharting.com/game/magic-scourge/booster-box",                                             "release_year": 2003, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "8th Edition",                             "url": "https://www.pricecharting.com/game/magic-8th-edition/booster-box",                                         "release_year": 2003, "set_type": "Core",           "is_universes_beyond": 0},
    {"set_name": "Mirrodin",                                "url": "https://www.pricecharting.com/game/magic-mirrodin/booster-box",                                            "release_year": 2003, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Darksteel",                               "url": "https://www.pricecharting.com/game/magic-darksteel/booster-box",                                           "release_year": 2004, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Fifth Dawn",                              "url": "https://www.pricecharting.com/game/magic-fifth-dawn/booster-box",                                          "release_year": 2004, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Unhinged",                                "url": "https://www.pricecharting.com/game/magic-unhinged/booster-box",                                            "release_year": 2004, "set_type": "Un-Set",         "is_universes_beyond": 0},
    {"set_name": "Champions of Kamigawa",                   "url": "https://www.pricecharting.com/game/magic-champions-of-kamigawa/booster-box",                               "release_year": 2004, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Betrayers of Kamigawa",                   "url": "https://www.pricecharting.com/game/magic-betrayers-of-kamigawa/booster-box",                               "release_year": 2005, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Ravnica City of Guilds",                  "url": "https://www.pricecharting.com/game/magic-ravnica/booster-box",                                             "release_year": 2005, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Time Spiral",                             "url": "https://www.pricecharting.com/game/magic-time-spiral/booster-box",                                         "release_year": 2006, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Planar Chaos",                            "url": "https://www.pricecharting.com/game/magic-planar-chaos/booster-box",                                        "release_year": 2007, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Conflux",                                 "url": "https://www.pricecharting.com/game/magic-conflux/booster-box",                                             "release_year": 2009, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "M10",                                     "url": "https://www.pricecharting.com/game/magic-m10/booster-box",                                                 "release_year": 2009, "set_type": "Core",           "is_universes_beyond": 0},
    {"set_name": "Rise of the Eldrazi",                     "url": "https://www.pricecharting.com/game/magic-rise-of-the-eldrazi/booster-box",                                 "release_year": 2010, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Scars of Mirrodin",                       "url": "https://www.pricecharting.com/game/magic-scars-of-mirrodin/booster-box",                                   "release_year": 2010, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "New Phyrexia",                            "url": "https://www.pricecharting.com/game/magic-new-phyrexia/booster-box",                                        "release_year": 2011, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Core Set 2012",                           "url": "https://www.pricecharting.com/game/magic-core-set-2012/booster-box",                                       "release_year": 2011, "set_type": "Core",           "is_universes_beyond": 0},
    {"set_name": "Innistrad",                               "url": "https://www.pricecharting.com/game/magic-innistrad/booster-box",                                           "release_year": 2011, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Dark Ascension",                          "url": "https://www.pricecharting.com/game/magic-dark-ascension/booster-box",                                      "release_year": 2012, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Core Set 2013",                           "url": "https://www.pricecharting.com/game/magic-core-set-2013/booster-box",                                       "release_year": 2012, "set_type": "Core",           "is_universes_beyond": 0},
    {"set_name": "Return to Ravnica",                       "url": "https://www.pricecharting.com/game/magic-return-to-ravnica/booster-box",                                   "release_year": 2012, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Modern Masters",                          "url": "https://www.pricecharting.com/game/magic-modern-masters/booster-box",                                      "release_year": 2013, "set_type": "Masters",        "is_universes_beyond": 0},
    {"set_name": "M14",                                     "url": "https://www.pricecharting.com/game/magic-m14/booster-box",                                                 "release_year": 2013, "set_type": "Core",           "is_universes_beyond": 0},
    {"set_name": "Theros",                                  "url": "https://www.pricecharting.com/game/magic-theros/booster-box",                                              "release_year": 2013, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Born of the Gods",                        "url": "https://www.pricecharting.com/game/magic-born-of-the-gods/booster-box",                                    "release_year": 2014, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Conspiracy",                              "url": "https://www.pricecharting.com/game/magic-conspiracy/booster-box",                                          "release_year": 2014, "set_type": "Special",        "is_universes_beyond": 0},
    {"set_name": "Khans of Tarkir",                         "url": "https://www.pricecharting.com/game/magic-khans-of-tarkir/booster-box",                                     "release_year": 2014, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Fate Reforged",                           "url": "https://www.pricecharting.com/game/magic-fate-reforged/booster-box",                                       "release_year": 2015, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Magic Origins",                           "url": "https://www.pricecharting.com/game/magic-magic-origins/booster-box",                                       "release_year": 2015, "set_type": "Core",           "is_universes_beyond": 0},
    {"set_name": "Modern Masters 2015",                     "url": "https://www.pricecharting.com/game/magic-modern-masters-2015/booster-box",                                 "release_year": 2015, "set_type": "Masters",        "is_universes_beyond": 0},
    {"set_name": "Battle for Zendikar",                     "url": "https://www.pricecharting.com/game/magic-battle-for-zendikar/booster-box",                                 "release_year": 2015, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Conspiracy Take the Crown",               "url": "https://www.pricecharting.com/game/magic-conspiracy-take-the-crown/booster-box",                           "release_year": 2016, "set_type": "Special",        "is_universes_beyond": 0},
    {"set_name": "Eternal Masters",                         "url": "https://www.pricecharting.com/game/magic-eternal-masters/booster-box",                                     "release_year": 2016, "set_type": "Masters",        "is_universes_beyond": 0},
    {"set_name": "Shadows over Innistrad",                  "url": "https://www.pricecharting.com/game/magic-shadows-over-innistrad/booster-box",                              "release_year": 2016, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Eldritch Moon",                           "url": "https://www.pricecharting.com/game/magic-eldritch-moon/booster-box",                                       "release_year": 2016, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Kaladesh",                                "url": "https://www.pricecharting.com/game/magic-kaladesh/booster-box",                                            "release_year": 2016, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Aether Revolt",                           "url": "https://www.pricecharting.com/game/magic-aether-revolt/booster-box",                                       "release_year": 2017, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Amonkhet",                                "url": "https://www.pricecharting.com/game/magic-amonkhet/booster-box",                                            "release_year": 2017, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Hour of Devastation",                     "url": "https://www.pricecharting.com/game/magic-hour-of-devastation/booster-box",                                 "release_year": 2017, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Ixalan",                                  "url": "https://www.pricecharting.com/game/magic-ixalan/booster-box",                                              "release_year": 2017, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Rivals of Ixalan",                        "url": "https://www.pricecharting.com/game/magic-rivals-of-ixalan/booster-box",                                    "release_year": 2018, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Dominaria",                               "url": "https://www.pricecharting.com/game/magic-dominaria/booster-box",                                           "release_year": 2018, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Masters 25",                              "url": "https://www.pricecharting.com/game/magic-masters-25/booster-box",                                          "release_year": 2018, "set_type": "Masters",        "is_universes_beyond": 0},
    {"set_name": "Core Set 2019",                           "url": "https://www.pricecharting.com/game/magic-core-set-2019/booster-box",                                       "release_year": 2018, "set_type": "Core",           "is_universes_beyond": 0},
    {"set_name": "Guilds of Ravnica",                       "url": "https://www.pricecharting.com/game/magic-guilds-of-ravnica/booster-box",                                   "release_year": 2018, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Ultimate Masters",                        "url": "https://www.pricecharting.com/game/magic-ultimate-masters/booster-box",                                    "release_year": 2018, "set_type": "Masters",        "is_universes_beyond": 0},
    {"set_name": "Ravnica Allegiance",                      "url": "https://www.pricecharting.com/game/magic-ravnica-allegiance/booster-box",                                  "release_year": 2019, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "War of the Spark",                        "url": "https://www.pricecharting.com/game/magic-war-of-the-spark/booster-box",                                    "release_year": 2019, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Modern Horizons",                         "url": "https://www.pricecharting.com/game/magic-modern-horizons/booster-box",                                     "release_year": 2019, "set_type": "Masters",        "is_universes_beyond": 0},
    {"set_name": "Core Set 2020",                           "url": "https://www.pricecharting.com/game/magic-core-set-2020/booster-box",                                       "release_year": 2019, "set_type": "Core",           "is_universes_beyond": 0},
    {"set_name": "Throne of Eldraine",                      "url": "https://www.pricecharting.com/game/magic-throne-of-eldraine/booster-box",                                  "release_year": 2019, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Theros Beyond Death",                     "url": "https://www.pricecharting.com/game/magic-theros-beyond-death/booster-box",                                 "release_year": 2020, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Ikoria Lair of Behemoths",                "url": "https://www.pricecharting.com/game/magic-ikoria-lair-of-behemoths/booster-box",                            "release_year": 2020, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Commander Legends",                       "url": "https://www.pricecharting.com/game/magic-commander-legends/booster-box",                                   "release_year": 2020, "set_type": "Commander",      "is_universes_beyond": 0},
    {"set_name": "Jumpstart",                               "url": "https://www.pricecharting.com/game/magic-jumpstart/booster-box",                                           "release_year": 2020, "set_type": "Special",        "is_universes_beyond": 0},
    {"set_name": "Mystery Booster",                         "url": "https://www.pricecharting.com/game/magic-mystery-booster/booster-box",                                     "release_year": 2020, "set_type": "Special",        "is_universes_beyond": 0},
    {"set_name": "Zendikar Rising",                         "url": "https://www.pricecharting.com/game/magic-zendikar-rising/booster-box",                                     "release_year": 2020, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Time Spiral Remastered",                  "url": "https://www.pricecharting.com/game/magic-time-spiral-remastered/booster-box",                              "release_year": 2021, "set_type": "Masters",        "is_universes_beyond": 0},
    {"set_name": "Strixhaven",                              "url": "https://www.pricecharting.com/game/magic-strixhaven-school-of-mages/booster-box",                          "release_year": 2021, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Modern Horizons 2",                       "url": "https://www.pricecharting.com/game/magic-modern-horizons-2/booster-box",                                   "release_year": 2021, "set_type": "Masters",        "is_universes_beyond": 0},
    {"set_name": "Adventures in the Forgotten Realms",      "url": "https://www.pricecharting.com/game/magic-adventures-in-the-forgotten-realms/booster-box",                  "release_year": 2021, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Innistrad Midnight Hunt",                 "url": "https://www.pricecharting.com/game/magic-innistrad-midnight-hunt/booster-box",                             "release_year": 2021, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Innistrad Crimson Vow",                   "url": "https://www.pricecharting.com/game/magic-innistrad-crimson-vow/booster-box",                               "release_year": 2021, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "The Brothers War",                        "url": "https://www.pricecharting.com/game/magic-brother%27s-war/draft-booster-box",                               "release_year": 2022, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Commander Legends Battle for Baldurs Gate","url": "https://www.pricecharting.com/game/magic-commander-legends-battle-for-baldur%27s-gate/booster-box",       "release_year": 2022, "set_type": "Commander",      "is_universes_beyond": 0},
    {"set_name": "Unfinity",                                "url": "https://www.pricecharting.com/game/magic-unfinity/booster-box-draft",                                      "release_year": 2022, "set_type": "Un-Set",         "is_universes_beyond": 0},
    {"set_name": "March of the Machine",                    "url": "https://www.pricecharting.com/game/magic-march-of-the-machine/booster-box",                                "release_year": 2023, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Commander Masters",                       "url": "https://www.pricecharting.com/game/magic-commander-masters/booster-box",                                   "release_year": 2023, "set_type": "Masters",      "is_universes_beyond": 0},
    {"set_name": "Wilds of Eldraine",                       "url": "https://www.pricecharting.com/game/magic-wilds-of-eldraine/booster-box",                                   "release_year": 2023, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Lost Caverns of Ixalan",                  "url": "https://www.pricecharting.com/game/magic-lost-caverns-of-ixalan/booster-box-draft",                        "release_year": 2023, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Modern Horizons 3",                       "url": "https://www.pricecharting.com/game/magic-modern-horizons-3/booster-box-play",                              "release_year": 2024, "set_type": "Masters",        "is_universes_beyond": 0},
    {"set_name": "Foundations",                             "url": "https://www.pricecharting.com/game/magic-foundations/booster-box-play",                                    "release_year": 2024, "set_type": "Core",           "is_universes_beyond": 0},
    {"set_name": "Aetherdrift",                             "url": "https://www.pricecharting.com/game/magic-aetherdrift/booster-box-play",                                    "release_year": 2025, "set_type": "Standard",       "is_universes_beyond": 0},
    {"set_name": "Innistrad Remastered",                    "url": "https://www.pricecharting.com/game/magic-innistrad-remastered/booster-box",                                "release_year": 2025, "set_type": "Masters",        "is_universes_beyond": 0},
    {"set_name": "Tarkir Dragonstorm",                      "url": "https://www.pricecharting.com/game/magic-tarkir-dragonstorm/booster-box-play",                             "release_year": 2025, "set_type": "Standard",       "is_universes_beyond": 0},
    # -- Universes Beyond (also Standard) --
    {"set_name": "Final Fantasy",                           "url": "https://www.pricecharting.com/game/magic-final-fantasy/booster-box-play",                                  "release_year": 2025, "set_type": "Standard",       "is_universes_beyond": 1},
    {"set_name": "Marvel Spider-Man",                       "url": "https://www.pricecharting.com/game/magic-marvel-spider-man/play-booster-box",                              "release_year": 2025, "set_type": "Standard",       "is_universes_beyond": 1},
    {"set_name": "Teenage Mutant Ninja Turtles",            "url": "https://www.pricecharting.com/game/magic-teenage-mutant-ninja-turtles/play-booster-display",               "release_year": 2025, "set_type": "Standard",       "is_universes_beyond": 1},
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

REQUEST_DELAY_SECONDS = 2.0


def extract_price_history(html: str) -> list[dict]:
    """
    Parse VGPC.chart_data from the page and return monthly records from
    the 'used' key (completed eBay/marketplace sales).
    Falls back to 'new' if 'used' has no data.
    Timestamps are Unix milliseconds; prices are integer cents.
    """
    match = re.search(r'VGPC\.chart_data\s*=\s*(\{.*?\})\s*;', html, re.DOTALL)
    if not match:
        return []

    try:
        chart_data = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []

    series = chart_data.get("used") or chart_data.get("new") or []

    records = []
    for ts_ms, price_cents in series:
        if price_cents == 0:
            continue
        date = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
        records.append({"date": date, "price_usd": round(price_cents / 100, 2)})

    return records


def scrape_set(set_info: dict, session: requests.Session) -> list[dict]:
    url = set_info["url"]
    try:
        resp = session.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        log.warning("  Request failed for %s: %s", set_info["set_name"], e)
        return []

    records = extract_price_history(resp.text)

    if not records:
        log.warning("  No price data found for %s — skipping", set_info["set_name"])
        return []

    log.info(
        "  %-45s  %d records  (latest: $%.2f on %s)",
        set_info["set_name"],
        len(records),
        records[-1]["price_usd"],
        records[-1]["date"],
    )

    for r in records:
        r.update({
            "set_name":           set_info["set_name"],
            "set_type":           set_info["set_type"],
            "is_universes_beyond": set_info["is_universes_beyond"],
            "release_year":       set_info["release_year"],
            "source_url":         url,
        })

    return records


def main():
    all_records: list[dict] = []
    session = requests.Session()
    session.get("https://www.pricecharting.com/", headers=HEADERS, timeout=15)

    log.info("Starting scrape for %d sets...", len(SETS))
    for i, set_info in enumerate(SETS, 1):
        log.info("[%d/%d] %s", i, len(SETS), set_info["set_name"])
        records = scrape_set(set_info, session)
        all_records.extend(records)
        time.sleep(REQUEST_DELAY_SECONDS)

    if not all_records:
        log.error("No data collected — check connection or page structure.")
        return

    df = pd.DataFrame(all_records)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["set_name", "date"]).reset_index(drop=True)
    df = df[[
        "set_name", "set_type", "is_universes_beyond",
        "release_year", "date", "price_usd", "source_url"
    ]]

    out_path = "../data/mtg_booster_box_prices.csv"
    df.to_csv(out_path, index=False)
    log.info(
        "Done. %d total records across %d sets → %s",
        len(df),
        df["set_name"].nunique(),
        out_path,
    )

    summary = (
        df.groupby(["set_name", "set_type", "is_universes_beyond", "release_year"])["price_usd"]
        .agg(months="count", min_price="min", max_price="max", latest_price="last")
        .reset_index()
        .sort_values("release_year")
    )
    print("\n" + summary.to_string(index=False))


if __name__ == "__main__":
    main()
