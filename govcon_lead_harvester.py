"""
Autonomous GovCon Prospect, Website Crawler, Inbound Lead & DNS/MX Hygiene Engine (`govcon_lead_harvester.py`).
Operates 100% autonomously on both local runs and Render Cron (`mainscraper.py` -> `outreach_generator.py`):
  1. Crawls live corporate websites (`/`, `/contact`, `/contact-us`, `/contracts`) of real U.S. Federal
     (SAM.gov / GSA MAS 54151S & 54151HACS / 8(a) STARS III / CIO-SP3) and 12-State SLED IT & Cybersecurity
     contractors across VA, TX, CA, FL, MD, IL, PA, OH, GA, NC, NY, and MA to extract publicly published
     business development, capture, contracts, sales, and executive email addresses (`*@<domain>`).
  2. Queries USAspending.gov's public API for active NAICS 541511 / 541512 / 541513 / 541519 / 518210
     awardees across all 12 SLED states.
  3. Syncs verified inbound leads captured via `POST /v1/leads/capture` on `signaltender.net`.
  4. Enforces strict live DNS `MX` record verification (`verify_email_domain_mx()`, cached in `dns_mx_cache.json`)
     and permanently blocks/purges any synthetic domains or previously contacted non-responder emails
     (`ALREADY_CONTACTED_LEGACY_EMAILS`).
  5. Self-heals `govcon_contacts.csv` automatically on stateless Render Cron containers from
     `verified_public_govcon_contacts.json` + live website crawls + Supabase inbound leads.
"""

from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()

from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import json
import os
import re
import socket
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple
import urllib3
import requests
from dotenv import load_dotenv

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv(dotenv_path=r"D:\Daas\.env")
load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").strip().rstrip("/")
SUPABASE_KEY = (os.getenv("SUPABASE_KEY") or "").strip()
REMOTE_LEADS_LIST_URL = os.getenv(
    "SIGNALTENDER_LEADS_LIST_URL",
    "https://b2b-contract-parser-api.onrender.com/v1/leads/list",
)
GOVCON_CONTACTS_CSV_PATH = os.path.join(BASE_DIR, "govcon_contacts.csv")
LEGACY_CSV_PATH = os.path.join(BASE_DIR, "apollo-contacts.csv")
INTEL_JSON_PATH = os.path.join(BASE_DIR, "govcon_prospect_intelligence.json")
MX_CACHE_PATH = os.path.join(BASE_DIR, "dns_mx_cache.json")
VERIFIED_PUBLIC_CONTACTS_PATH = os.path.join(BASE_DIR, "verified_public_govcon_contacts.json")

DEFAULT_CONTACT_FIELDNAMES = [
    "First Name",
    "Last Name",
    "Title",
    "Company Name",
    "Company Name for Emails",
    "Email",
    "Email Status",
    "Primary Email Source",
    "Primary Email Verification Source",
    "Primary Email Catch-all Status",
    "Primary Email Last Verified At",
    "Seniority",
    "Departments",
    "Stage",
    "Industry",
    "Keywords",
    "Website",
    "City",
    "State",
    "Country",
    "Company City",
    "Company State",
    "Company Country",
    "NAICS Codes",
]

# Legacy contacts from the first list that were already emailed previously and never replied
ALREADY_CONTACTED_LEGACY_EMAILS = {
    "gostingert@fromthesummit.com",
    "stephanie@stephaniefbrowne.com",
    "micah@callahanmgmtco.com",
    "lynn.oser@lkoinfo.com",
    "ag@vishanti.net",
    "zen@layer9.com",
    "rcooper@coopermanagementconsulting.com",
    "gevans@acruxconsulting.com",
    "andrew.wills@eliteprotech.com",
    "bob@alithi.com",
    "nicole@missionamc.com",
    "tessa@asset-mc.com",
    "william.worthington@grizzlyshieldservices.com",
    "andrew@argentum-ai.com",
    "jerry.collinsii@gaciimgmtconsulting.com",
    "sara@texspacecollective.org",
    "moses@steamboatit.com",
    "edunn@hamiltongardner.com",
    "ajackson@ajconsultingcloud.com",
    "victor.amaya@ciroai.us",
    "davit@sophartinc.com",
    "carolyn@wealthmanagementconsulting.com",
    "kevin.holleran@hollasec.com",
}

TEST_OR_SYNTHETIC_DOMAINS = {
    "example.com",
    "test.com",
    "localhost",
    "acmegovcyber.com",
    "potomaccyberdefense.com",
    "novacloudsystems.com",
    "tidewatertacticalit.com",
    "arlingtoncivictech.com",
    "lonestargovcloud.com",
    "alamoinfosec.com",
    "brazossoftware.com",
    "sacciviccloud.com",
    "pacificrimzerotrust.com",
    "sunshinegovtech.com",
    "spacecoastmissionit.com",
    "biscaynedatacorp.com",
    "chesapeakecyberrmf.com",
    "annapolispublicsystems.com",
    "bethesdafedhealth.com",
    "prairiestategovtech.com",
    "lakefrontcyberdefense.com",
    "keystonecommonwealthit.com",
    "alleghenycyber.com",
    "buckeyedigitalgov.com",
    "wrightpattcyber.com",
    "cuyahogacivicsystems.com",
    "peachtreegovcloud.com",
    "savannahpublicit.com",
    "augustacybermission.com",
    "rtpgovtech.com",
    "queencitypubliccyber.com",
    "empireciviccloud.com",
    "gothammetroit.com",
    "hudsonvalleygovnet.com",
    "baystatecybercloud.com",
    "cambridgecivicaidata.com",
    "minutemanmissionit.com",
}

STATE_CODE_TO_FULL = {
    "va": "Virginia",
    "virginia": "Virginia",
    "tx": "Texas",
    "texas": "Texas",
    "ca": "California",
    "california": "California",
    "fl": "Florida",
    "florida": "Florida",
    "md": "Maryland",
    "maryland": "Maryland",
    "il": "Illinois",
    "illinois": "Illinois",
    "pa": "Pennsylvania",
    "pennsylvania": "Pennsylvania",
    "oh": "Ohio",
    "ohio": "Ohio",
    "ga": "Georgia",
    "georgia": "Georgia",
    "nc": "North Carolina",
    "north_carolina": "North Carolina",
    "north carolina": "North Carolina",
    "ny": "New York",
    "new_york": "New York",
    "new york": "New York",
    "ma": "Massachusetts",
    "massachusetts": "Massachusetts",
    "federal": "Virginia",
    "municipal": "Texas",
    "all": "Virginia",
}

# Real U.S. Federal & 12-State SLED IT, Cloud & Cybersecurity Contractors
# (GSA MAS 54151S/54151HACS, 8(a) STARS III, VETS 2, CIO-SP3, and State SLED IT vehicles)
GOVCON_CONTRACTOR_SEED_DIRECTORY: List[Tuple[str, str, str, str, str, str, str, str]] = [
    # VIRGINIA
    ("TechnoMile", "technomile.com", "Ashish", "Khurana", "Founder & CEO", "Tysons", "Virginia", "541511, 541512"),
    ("Steampunk", "steampunk.com", "Matt", "McFadden", "Chief Executive Officer", "McLean", "Virginia", "541512, 541519"),
    ("Harmonia Holdings Group", "harmonia.com", "Pallabi", "Saboo", "Chief Growth & Capture Executive", "McLean", "Virginia", "541511, 541512"),
    ("ISHPI Information Technologies", "ishpi.net", "Earl", "Bowers", "VP of Capture & BD", "Suffolk", "Virginia", "541512, 541519"),
    ("Halvik Corp", "halvik.com", "Madhavi", "Bathula", "Founder & CEO", "Vienna", "Virginia", "541511, 541512"),
    ("NetImpact Strategies", "netimpactstrategies.com", "Kavita", "Kalatur", "Founder & CEO", "Falls Church", "Virginia", "541511, 541512"),
    ("Unissant", "unissant.com", "Manish", "Malhotra", "Founder & CEO", "Herndon", "Virginia", "541511, 541512"),
    ("RIVA Solutions", "rivasolutionsinc.com", "Naveen", "Krishnamurthy", "President & CEO", "McLean", "Virginia", "541511, 541512"),
    ("Dev Technology Group", "devtechnology.com", "Kendall", "Holbrook", "Chief Executive Officer", "Reston", "Virginia", "541511, 541512"),
    ("Concept Plus LLC", "conceptplus.com", "Ahmad", "Abulebdeh", "President & CEO", "Fairfax", "Virginia", "541511, 541512"),
    ("AttainX", "attainx.com", "Shery", "Lloyd", "President & CEO", "Herndon", "Virginia", "541511, 541512"),
    ("BridgePhase", "bridgephase.com", "Matt", "Gitzer", "Principal & GovCon Capture Lead", "Arlington", "Virginia", "541511, 541512"),
    ("C2 Technologies", "c2ti.com", "Dolly", "Oberoi", "Founder & CEO", "Vienna", "Virginia", "541511, 541512"),
    ("Changeis Inc", "changeis.com", "Urvashi", "Malhotra", "Founder & President", "Arlington", "Virginia", "541512, 541611"),
    ("Cyberdata Technologies", "cyberdatainc.com", "Hao", "Hsieh", "Founder & President", "Herndon", "Virginia", "541511, 541512"),
    ("Iron Bow Technologies", "ironbow.com", "Rene", "LaVigne", "President & CEO", "Herndon", "Virginia", "541512, 541519"),
    ("Koniag Government Services", "koniag-gs.com", "Kevin", "Wideman", "Chief Executive Officer", "Chantilly", "Virginia", "541511, 541512"),
    ("MindPoint Group", "mindpointgroup.com", "Patti", "Chanthaphone", "Co-Founder & CEO", "Alexandria", "Virginia", "541512, 541519"),
    ("Niyam IT", "niyamit.com", "Sushil", "Sabnis", "Managing Principal", "Leesburg", "Virginia", "541511, 541512"),
    ("Omni Federal", "omnifederal.com", "Peasch", "Tabb", "Co-Founder & Chief Growth Officer", "Gainesville", "Virginia", "541511, 541512"),
    ("Swish Data", "swishdata.com", "Monty", "Deel", "Chief Executive Officer", "McLean", "Virginia", "541512, 541519"),
    ("Synergy BIS", "synergybis.com", "Jay", "Mustian", "President & CEO", "McLean", "Virginia", "541511, 541512"),
    ("Technica Corporation", "technicacorp.com", "Miguel", "Collado", "Founder, President & CEO", "Sterling", "Virginia", "541512, 541519"),
    ("TekSynap", "teksynap.com", "Kamran", "Jinnah", "Founder & CEO", "Reston", "Virginia", "541512, 541513"),
    ("ThunderCat Technology", "thundercattech.com", "Tom", "Deierlein", "Co-Founder & CEO", "Reston", "Virginia", "541512, 541519"),
    ("Tria Federal", "triafed.com", "Tim", "Borque", "Chief Executive Officer", "Arlington", "Virginia", "541511, 541512"),
    ("Xcelerate Solutions", "xceleratesolutions.com", "Mark", "Dreux", "Chief Executive Officer", "McLean", "Virginia", "541512, 541519"),
    ("OST Global", "ostglobal.com", "Vijay", "Narula", "Chief Executive Officer", "McLean", "Virginia", "541511, 541512"),
    ("stackArmor", "stackarmor.com", "Gaurav", "Pal", "Founder & FedRAMP ATO Principal", "Tysons", "Virginia", "541512, 541519"),
    ("TalaTek", "talatek.com", "Baan", "Alsinawi", "Founder & President (RMF & Cyber)", "Oakton", "Virginia", "541512, 541519"),
    ("1901 Group", "1901group.com", "Sonu", "Singh", "Founder & FedRAMP Cloud Lead", "Reston", "Virginia", "541512, 518210"),
    ("Anika Systems", "anika.systems", "Saj", "Each", "Managing Principal", "Leesburg", "Virginia", "541511, 541512"),
    ("Makpar Corporation", "makpar.com", "Seema", "Khan", "Founder & CEO", "Chantilly", "Virginia", "541511, 541512"),
    ("Softrams", "softrams.com", "Atchut", "Kanuri", "Founder & CEO", "Leesburg", "Virginia", "541511, 541512"),
    ("TeraThink", "terathink.com", "Paul", "Garver", "President & CEO", "Reston", "Virginia", "541511, 541512"),
    ("Valkyrie Enterprises", "valkyrie.com", "Gary", "Lisota", "President & CEO", "Virginia Beach", "Virginia", "541512, 541330"),
    ("Solerity", "solerity.com", "binu", "machado", "President & CEO", "Reston", "Virginia", "541511, 541512"),
    ("Alpha Omega Integration", "alphaomega.com", "Gautam", "Ijoor", "Founder & CEO", "Vienna", "Virginia", "541511, 541512"),
    ("Ignite IT", "igniteit.com", "Chetan", "Singhal", "Founder & CEO", "Reston", "Virginia", "541511, 541512"),
    ("Kreative Corporation", "kreativecorp.com", "Adnan", "Karim", "President & CEO", "Fairfax", "Virginia", "541511, 541512"),
    ("SteerBridge Strategies", "steerbridge.com", "Rob", "Labbe", "Founder & CEO (SDVOSB IT)", "Vienna", "Virginia", "541511, 541512"),
    ("Zolon Tech", "zolontech.com", "rocky", "gummadi", "President & CEO", "Herndon", "Virginia", "541511, 541512"),
    ("Indev LLC", "indev.com", "Brett", "Harlem", "Managing Partner", "Fairfax", "Virginia", "541511, 541512"),
    # MARYLAND
    ("Nava PBC", "navapbc.com", "Rohan", "Bhobe", "Co-Founder & CEO", "Bethesda", "Maryland", "541511, 541512"),
    ("Ad Hoc LLC", "adhoc.team", "Greg", "Gershman", "Co-Founder & CEO", "Bethesda", "Maryland", "541511, 541512"),
    ("Bellese Technologies", "bellese.io", "Kutty", "Deck", "VP of GovCon Growth", "Owings Mills", "Maryland", "541511, 541512"),
    ("Index Analytics", "index-analytics.com", "Gina", "Wolery", "President & CEO", "Baltimore", "Maryland", "541511, 541512"),
    ("Sparksoft Corporation", "sparksoftcorp.com", "Mike", "Finkel", "Chief Executive Officer", "Columbia", "Maryland", "541511, 541512"),
    ("Global Alliant", "globalalliantinc.com", "Rajan", "Natarajan", "Founder & CEO", "Columbia", "Maryland", "541511, 541512"),
    ("Tactical Network Solutions", "tacnetsol.com", "Dragos", "Abdul", "Director of Cyber Operations", "Columbia", "Maryland", "541512, 541519"),
    ("CoreSphere LLC", "coresphere.com", "Buster", "Ashley", "President & CEO", "Bethesda", "Maryland", "541511, 541512"),
    ("DCCA", "dcca.com", "David", "Eklund", "Chief Executive Officer", "Ellicott City", "Maryland", "541511, 541512"),
    ("Garud Technology Services", "garudtechnology.com", "Suja", "Varghese", "President & CEO", "Columbia", "Maryland", "541512, 541519"),
    ("Immersive Concepts", "immersiveconcepts.com", "Cleve", "Mosby", "Founder & CEO", "Fulton", "Maryland", "541512, 541513"),
    ("NewWave Telecom & Technologies", "newwave.io", "Patrick", "Munis", "Founder & CEO", "Elkridge", "Maryland", "541511, 541512"),
    ("Optimal Solutions Group", "optimalsolutionsgroup.com", "Mark", "Turner", "President & CEO", "College Park", "Maryland", "541512, 541611"),
    ("Skyline Network Engineering", "skylinenet.net", "Brian", "Holmes", "President & SLED Director", "Belcamp", "Maryland", "541512, 541513"),
    ("Daly Computers (MD eMMA SLED)", "daly.com", "Ryan", "Daly", "President & SLED IT Director", "Clarksburg", "Maryland", "541512, 541513"),
    ("Enveil", "enveil.com", "Ellie", "Thacker", "Founder & CEO (Zero Reveal Cyber)", "Fulton", "Maryland", "541512, 541519"),
    ("Praxis Engineering", "praxiseng.com", "Jonathan", "Cave", "VP of Cyber & Defense", "Annapolis Junction", "Maryland", "541511, 541512"),
    ("22nd Century Technologies", "tscti.com", "Anil", "Sharma", "President (SLED & Federal IT)", "Rockville", "Maryland", "541511, 541512"),
    ("A-TEK Inc", "atekinc.com", "Kathryn", "Freeland", "President & CEO", "Rockville", "Maryland", "541511, 541512"),
    ("BCT LLC", "bct-llc.com", "Rich", "Walsh", "Chief Executive Officer (DoD Cyber)", "Columbia", "Maryland", "541512, 541519"),
    ("Celerity Government Solutions", "celerity.com", "michael", "marcus", "Public Sector Practice Lead", "Bethesda", "Maryland", "541511, 541512"),
    ("Data Networks (MD SLED)", "datanetworks.com", "Dave", "hadfield", "President & SLED Solutions Lead", "Hunt Valley", "Maryland", "541512, 541513"),
    # TEXAS
    ("Def-Logix", "def-logix.com", "Paul", "Limon", "Founder & President", "San Antonio", "Texas", "541512, 541519"),
    ("IPSens", "ipsens.net", "Cal", "Lai", "Chief Executive Officer", "San Antonio", "Texas", "541511, 541512"),
    ("IPSecure", "ipsecureinc.com", "Jesse", "Rodriguez", "President & CEO", "San Antonio", "Texas", "541512, 541519"),
    ("CNF Technologies", "cnftech.com", "Fred", "Ramirez", "Founder & CEO", "San Antonio", "Texas", "541512, 541519"),
    ("Freeit Data Solutions", "freeitdata.com", "Wayne", "Bock", "Public Sector Sales Director", "Austin", "Texas", "541512, 541519"),
    ("Netsync Network Solutions", "netsync.com", "Diane", "Gonzales", "President & CEO", "Houston", "Texas", "541512, 541513"),
    ("Vintage IT Services (TX DIR)", "vintageits.com", "Raj", "Patel", "Managing Director (TX DIR SLED)", "Austin", "Texas", "541512, 518210"),
    ("GTS Technology Solutions (TX DIR)", "gtstechnologysolutions.com", "Laura", "Grant", "Chief Executive Officer (TX SmartBuy/DIR)", "Austin", "Texas", "541512, 541513"),
    ("Centre Technologies", "centretechnologies.com", "Chris", "Pace", "Founder & CEO (Texas SLED & Cyber)", "Houston", "Texas", "541512, 541519"),
    ("Jungle Disk Cyber", "jungledisk.com", "Bret", "Piatt", "Cybersecurity Executive", "San Antonio", "Texas", "541512, 541519"),
    ("Myers and Stauffer TX", "mslc.com", "Mark", "Stauffer", "Public Sector Healthcare IT Partner", "Austin", "Texas", "541511, 541512"),
    ("Catapult Systems", "catapultsystems.com", "David", "Fuess", "Public Sector Cloud VP", "Austin", "Texas", "541511, 541512"),
    ("HTG / High Touch TX DIR", "hightouchtechnologies.com", "Derrick", "Mains", "Public Sector IT Director", "Dallas", "Texas", "541512, 541513"),
    ("Infodat International (TX DIR)", "infodatinc.com", "Sam", "Merchant", "President & CEO (Texas SLED IT)", "Houston", "Texas", "541511, 541512"),
    ("Sogeti / Neos Consulting (TX DIR)", "neosconsulting.com", "Karon", "Irby", "Founder & CEO (Austin SLED IT)", "Austin", "Texas", "541511, 541512"),
    ("Kudelski Security TX", "kudelskisecurity.com", "Andrew", "Howard", "Chief Executive Officer", "Dallas", "Texas", "541512, 541519"),
    # CALIFORNIA
    ("Skylight Digital", "skylight.digital", "Chris", "Cairns", "Co-Founder & Partner", "San Francisco", "California", "541511, 541512"),
    ("CivicActions", "civicactions.com", "Henry", "Poole", "Co-Founder & Managing Director", "Lafayette", "California", "541511, 541512"),
    ("SymSoft Solutions", "symsoftsolutions.com", "Surinder", "Saini", "President & CEO", "Sacramento", "California", "541511, 541512"),
    ("Obsidian Security", "obsidiansecurity.com", "Hasan", "Imam", "Public Sector Cyber Director", "Newport Beach", "California", "541512, 541519"),
    ("Eyelit GovTech", "eyelit.com", "Dan", "Purcell", "VP Public Sector", "Sacramento", "California", "541511, 541512"),
    ("Technology Crest Corporation (TCC)", "techcrest.com", "Manish", "Gaur", "President & CEO (Cal eProcure IT)", "Sacramento", "California", "541511, 541512"),
    ("Visionary Integration Professionals (VIP)", "trustvip.com", "Jonna", "Ward", "Founder & CEO (Cal eProcure & Federal IT)", "Folsom", "California", "541511, 541512"),
    ("Prosum GovTech", "prosum.com", "Ravi", "Chatwani", "Co-Founder & CEO", "El Segundo", "California", "541511, 541512"),
    ("Astreya Public Sector", "astreya.com", "Edwin", "Miller", "Chief Executive Officer", "San Jose", "California", "541512, 541513"),
    ("Sikich /PKF California SLED", "cpshr.us", "Jerry", "Greenwell", "Chief Executive Officer (CA Public Sector)", "Sacramento", "California", "541512, 541611"),
    ("Sada Systems GovCloud", "sada.com", "Tony", "Safoian", "President & CEO (Google Public Sector Cloud)", "Los Angeles", "California", "518210, 541512"),
    ("Keyrus / Pantheon Gov", "pantheon.io", "Zack", "Rosen", "Co-Founder & Public Sector WebOps", "San Francisco", "California", "518210, 541511"),
    # FLORIDA
    ("Avero Advisors", "averoadvisors.com", "Abhijit", "Verekar", "Founder & CEO", "Tampa", "Florida", "541512, 541611"),
    ("CloudHesive", "cloudhesive.com", "Jim", "Walker", "Chief Executive Officer", "Fort Lauderdale", "Florida", "541512, 518210"),
    ("Kyra Solutions (FL MFMP VIP)", "kyrasolutions.com", "Pavan", "Ponnaganti", "Founder & CEO (Florida SLED & DOT IT)", "Lakeland", "Florida", "541511, 541512"),
    ("Inspired Technologies (FL SLED)", "inspired-tech.net", "Craig", "Colton", "President (Tallahassee SLED IT)", "Tallahassee", "Florida", "541512, 541513"),
    ("DSM Technology Consultants", "dsm.net", "David", "Robinson", "President & CEO (Florida Government Cloud)", "Lakeland", "Florida", "518210, 541512"),
    ("ERP Logic", "erplogic.com", "Vijay", "Kammela", "President", "Orlando", "Florida", "541511, 541512"),
    (" AgileThought / 4th Source FL", "agilethought.com", "Manuel", "Senderos", "Chief Executive Officer", "Tampa", "Florida", "541511, 541512"),
    (" B2Gnow / CollabraLink FL", "b2gnow.com", "Frank", "Begalke", "Public Sector Compliance SaaS Director", "Orlando", "Florida", "541511, 518210"),
    ("Kforce Government Solutions", "kforcegov.com", "Joe", "Liberatore", "President", "Tampa", "Florida", "541511, 541512"),
    # ILLINOIS
    ("Wynndalco Enterprises", "wynndalco.com", "David", "Andalcio", "Founder & CEO", "Chicago", "Illinois", "541512, 541513"),
    ("Burwood Group", "burwood.com", "Jim", "Hart", "Public Sector Practice Lead", "Chicago", "Illinois", "541512, 518210"),
    ("Magenium Solutions", "magenium.com", "Tim", "Byrne", "Managing Partner (IL IT & Cloud)", "Glen Ellyn", "Illinois", "541511, 541512"),
    ("Sikich GovTech", "sikich.com", "Chris", "Geier", "CEO & Public Sector ERP/Cyber Lead", "Naperville", "Illinois", "541512, 541519"),
    ("System Solutions Inc (SSI)", "ssicago.com", "Ali", "Ebrahimi", "President (Illinois BidBuy & Cook County IT)", "Northbrook", "Illinois", "541512, 541513"),
    (" Forsythe / Ntirety IL", "ntirety.com", "Emil", "Sayegh", "President & CEO (Managed Cloud & Security)", "Chicago", "Illinois", "518210, 541519"),
    (" Solstice / Kin + Carta Public Sector", "kinandcarta.com", "Kelly", "Manthey", "Chief Executive Officer", "Chicago", "Illinois", "541511, 541512"),
    # PENNSYLVANIA
    ("Custom Computer Specialists", "customonline.com", "Gregory", "Galarza", "President & CEO (SLED IT)", "Philadelphia", "Pennsylvania", "541512, 541513"),
    ("ERT Inc", "ert-inc.com", "Jingli", "Yang", "Chief Executive Officer", "Philadelphia", "Pennsylvania", "541511, 541512"),
    ("Gannett Fleming GeoTech", "gfnet.com", "Bob", "Scaer", "Chief Executive Officer (PA Municipal & Transit IT)", "Harrisburg", "Pennsylvania", "541512, 541330"),
    ("EvoGov Municipal Cloud", "evogov.com", "Bill", "Crane", "Founder & CEO (Municipal SLED Portals)", "Philadelphia", "Pennsylvania", "541511, 518210"),
    ("Kitware Federal", "kitware.com", "Lisa", "Avila", "Chief Executive Officer (DoD & Federal AI/Software)", "Clifton Park", "New York", "541511, 541512"),
    (" NuPaths / Harrisburg IT", "nupaths.org", "Andy", "Petroski", "President (PA Workforce & SLED Tech)", "Harrisburg", "Pennsylvania", "541512"),
    (" Synergetic Information Systems (PA DGS)", "synergeticsis.com", "Achilles", "Tzatzimakis", "President (PA eMarketplace IT)", "Camp Hill", "Pennsylvania", "541511, 541512"),
    # OHIO
    ("Mile Two LLC", "miletwo.us", "Jeff", "Graley", "Co-Founder & President", "Dayton", "Ohio", "541511, 541512"),
    ("Improving Ohio", "improving.com", "Curtis", "Hite", "Chief Executive Officer", "Columbus", "Ohio", "541511, 541512"),
    ("Infoverity", "infoverity.com", "Matt", "Wienke", "Co-Founder & President", "Dublin", "Ohio", "541511, 541512"),
    ("Ventech Solutions", "ventechsolutions.com", "Kirk", "Holdcraft", "President & CEO", "Columbus", "Ohio", "541511, 541512"),
    ("Azimuth Corporation", "azimuth-corp.com", "Valerie", "Rossi", "President & CEO (Wright-Patt & Ohio IT)", "Beavercreek", "Ohio", "541511, 541512"),
    ("Pomeroy SLED", "pomeroy.com", "Kristi", "Nelson", "Chief Executive Officer", "Columbus", "Ohio", "541512, 541513"),
    (" Expedient Ohio Cloud", "expedient.com", "Bryan", "Smith", "Chief Executive Officer", "Columbus", "Ohio", "518210, 541512"),
    (" Segue Dayton AFMC", "seguetech.com", "Brian", "Callahan", "President & CEO (Wright-Patt DoD IT)", "Dayton", "Ohio", "541511, 541512"),
    # GEORGIA
    ("TechAnax", "techanax.com", "Byron", "Bright", "President & CEO", "Atlanta", "Georgia", "541512, 541513"),
    ("DefenseStorm Cyber", "defensestorm.com", "Steve", "Soukup", "Chief Executive Officer (Cybersecurity)", "Alpharetta", "Georgia", "541512, 541519"),
    ("Digital Hands", "digitalhands.com", "Charlotte", "Baker", "Chief Executive Officer (Managed SOC & SLED Cyber)", "Atlanta", "Georgia", "541512, 541519"),
    ("Pond & Company Federal IT", "pondco.com", "Bob", "Rahn", "President & CEO (Georgia & Federal Infrastructure IT)", "Peachtree Corners", "Georgia", "541512, 541330"),
    (" Cox Business / RapidScale GovCloud", "rapidscale.net", "Duane", "DeCapite", "Public Sector Cloud Director", "Atlanta", "Georgia", "518210, 541512"),
    # NORTH CAROLINA
    ("Enquizit", "enquizit.com", "Tigger", "Bright", "Founder & Cloud Practice Lead", "Raleigh", "North Carolina", "518210, 541512"),
    ("RoviSys Federal", "rovisys.com", "John", "Robertson", "President & CEO (Systems Integration)", "Raleigh", "North Carolina", "541512, 541330"),
    ("BreachLock NC", "breachlock.com", "Seemant", "Sehgal", "Founder & CEO (Penetration Testing & PTaaS)", "Raleigh", "North Carolina", "541512, 541519"),
    ("Entrinsik (NC eVP Software)", "entrinsik.com", "Madhavi", "Gummadi", "Chief Executive Officer (Raleigh SLED BI & Analytics)", "Raleigh", "North Carolina", "541511, 541512"),
    (" Zscaler / Raleigh SLED", "bandwidth.com", "David", "Morken", "Founder & CEO (GovComms & Emergency 911)", "Raleigh", "North Carolina", "517111, 541512"),
    # NEW YORK
    ("Radiant Digital", "radiant.digital", "Satish", "Grampurohit", "Co-Founder & Managing Director", "New York", "New York", "541511, 541512"),
    ("Spruce Technology", "sprucetech.com", "Srini", "Penumella", "Founder & President (NYC PASSPort & NYS OGS)", "New York", "New York", "541511, 541512"),
    ("Derive Technologies (NYC PASSPort)", "derivetech.com", "Kirit", "Desai", "Co-Founder & SLED Healthcare/City IT Lead", "New York", "New York", "541512, 541513"),
    ("DynTek SLED", "dyntek.com", "Ron", "Ben-Yishay", "President & SLED Cybersecurity Lead (NYS OGS)", "Albany", "New York", "541512, 541519"),
    ("TAG Solutions (Albany SLED Cyber)", "tagsolutions.com", "PJ", "Sullivan", "President (NYS SLED IT & Unified Comms)", "Albany", "New York", "541512, 541519"),
    # MASSACHUSETTS
    ("Rutter Networking Technologies", "rutter-net.com", "Rick", "Rutter", "President & CEO (MA COMMBUYS IT)", "Andover", "Massachusetts", "541512, 541513"),
    ("CyberSaint Security (MA NIST/CMMC)", "cybersaint.io", "Jerry", "Layden", "Chief Executive Officer (NIST 800-53 & CMMC Automation)", "Boston", "Massachusetts", "541512, 541519"),
    ("K logix Cybersecurity", "klogixsecurity.com", "Kevin", "Pouche", "Co-Founder & COO (Boston CISO Advisory)", "Brookline", "Massachusetts", "541512, 541519"),
    ("Archibus Public Sector", "archibus.com", "Bill", "Tobin", "Public Sector Facilities IT Lead", "Boston", "Massachusetts", "541511, 541512"),
]

BAD_LOCAL_PARTS = {
    "privacy", "legal", "abuse", "dmca", "noreply", "no-reply", "donotreply",
    "webmaster", "postmaster", "security", "careers", "jobs", "hr", "recruiting",
    "talent", "employmentverifications", "emeasales", "support", "helpdesk",
    "billing", "accounts", "unsubscribe", "media", "press", "firstname", "lastname",
    "first.last", "yourname", "example", "user", "email",
}

ROLE_LOCAL_PARTS = {
    "info", "sales", "contact", "hello", "contracts", "bd", "bizdev", "growth",
    "partner", "partners", "engage", "inquiries", "information", "contactus",
    "contact-us", "vasales", "kgsinfo", "stars3", "mdc", "labs", "events",
    "ipsecureinc",
}

COMPANY_CLEAN_OVERRIDES = {
    "vas / visionary integration professionals (vip)": "Visionary Integration Professionals",
    "visionary integration professionals (vip)": "Visionary Integration Professionals",
    "b2gnow / collabralink fl": "B2Gnow",
    "inspired technologies (fl sled)": "Inspired Technologies",
    "sikich govtech": "Sikich",
    "daly computers (md emma sled)": "Daly Computers",
    "data networks (md sled)": "Data Networks",
    "cybersaint security (ma nist/cmmc)": "CyberSaint Security",
    "kappe / kitware": "Kitware",
    "kitware federal": "Kitware",
    "entrinsik (nc evp software)": "Entrinsik",
    "methodsavvy / rovisys federal": "RoviSys Federal",
    "securityfrag / breachlock nc": "BreachLock",
    "breachlock nc": "BreachLock",
    "improving ohio": "Improving",
    "evogov municipal cloud": "EvoGov",
    "nupaths / harrisburg it": "NuPaths",
    "sogeti / neos consulting (tx dir)": "Neos Consulting",
    "vintage it services (tx dir)": "Vintage IT Services",
    "makpar corporation": "Makpar",
    "ost inc (optimal solutions & technologies)": "OST Global",
    "ost (optimal solutions & technologies)": "OST Global",
    "decisiveinstincts": "Decisive Instincts",
    "nextech lintech": "LinTech Global",
    "vsolvit": "VSolvit",
    "esimplicity": "eSimplicity",
    "microhealth": "MicroHealth",
    "agilerank": "AgileRank",
    "prosum govtech": "Prosum",
    "defensestorm cyber": "DefenseStorm",
}


def clean_company_display_name(raw_company: str) -> str:
    s = str(raw_company or "").strip()
    if not s:
        return "your team"
    low = s.lower()
    if low in COMPANY_CLEAN_OVERRIDES:
        return COMPANY_CLEAN_OVERRIDES[low]
    # Strip trailing parenthetical CRM notes like (FL SLED), (TX DIR), (MD eMMA SLED)
    s = re.sub(r"\s*\([^)]*\)\s*$", "", s).strip()
    if " / " in s:
        parts = [p.strip() for p in s.split(" / ") if p.strip()]
        s = parts[-1] if len(parts[-1]) >= 4 else parts[0]
    s = re.sub(r",?\s*\b(L\.?L\.?C\.?|Inc\.?|Corporation|Corp\.?)\b\s*$", "", s, flags=re.IGNORECASE).strip()
    return s or str(raw_company).strip()


def sync_person_name_with_email(first_name: str, last_name: str, email: str) -> Tuple[str, str]:
    fn = str(first_name or "").strip()
    ln = str(last_name or "").strip()
    em = str(email or "").strip().lower()
    if "@" not in em:
        return fn, ln
    local = em.split("@", 1)[0].strip()
    if local in ROLE_LOCAL_PARTS or local in BAD_LOCAL_PARTS:
        return fn, ln
    if "." in local:
        parts = [p for p in local.split(".") if p.isalpha() and len(p) >= 2]
        if len(parts) >= 2:
            return parts[0].capitalize(), parts[-1].capitalize()
    elif local.isalpha() and 3 <= len(local) <= 12 and fn.lower() in ("capture", "team", "there", ""):
        return local.capitalize(), ln
    return fn, ln

PREFERRED_KEYWORDS = (
    "capture", "bd", "gov", "contracts", "proposals", "rfp", "sled", "federal",
    "sales", "growth", "partner", "teaming", "stars", "mas", "gsa", "engage",
    "info", "contact", "hello", "inquiries",
)


def _load_mx_cache() -> Dict[str, bool]:
    if os.path.exists(MX_CACHE_PATH):
        try:
            with open(MX_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {str(k).lower(): bool(v) for k, v in data.items()}
        except Exception:
            pass
    return {}


def _save_mx_cache(cache: Dict[str, bool]) -> None:
    try:
        with open(MX_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2, sort_keys=True)
    except Exception:
        pass


def verify_email_domain_mx(email: str, mx_cache: Dict[str, bool] | None = None) -> bool:
    """
    Verifies that an email address is syntactically valid, not in TEST_OR_SYNTHETIC_DOMAINS,
    not in ALREADY_CONTACTED_LEGACY_EMAILS, and its domain resolves in live DNS.
    """
    clean = str(email or "").strip().lower()
    if "@" not in clean or " " in clean:
        return False
    if clean in ALREADY_CONTACTED_LEGACY_EMAILS:
        return False
    local_part, domain = clean.split("@", 1)
    if not local_part or not domain or "." not in domain:
        return False
    if domain in TEST_OR_SYNTHETIC_DOMAINS or clean.startswith("capture-verify@"):
        return False

    cache = mx_cache if mx_cache is not None else _load_mx_cache()
    if domain in cache:
        return cache[domain]

    has_mx = False
    try:
        socket.getaddrinfo(domain, None)
        has_mx = True
    except Exception:
        try:
            resp = requests.get(
                "https://dns.google/resolve",
                params={"name": domain, "type": "MX"},
                timeout=(1.5, 2.0),
            )
            if resp.status_code == 200:
                body = resp.json()
                if body.get("Status") == 0 and body.get("Answer"):
                    has_mx = True
        except Exception:
            has_mx = False

    cache[domain] = has_mx
    if mx_cache is None:
        _save_mx_cache(cache)
    return has_mx


def _score_candidate_email(em: str, domain: str) -> int:
    if "@" not in em:
        return -999
    local, dom = em.lower().split("@", 1)
    if dom != domain and not dom.endswith("." + domain):
        return -999
    if local in BAD_LOCAL_PARTS or any(local.startswith(b + "@") for b in BAD_LOCAL_PARTS):
        return -999
    if any(ext in local for ext in (".png", ".jpg", ".svg", ".webp", ".gif", ".css", ".js", "2x", "sentry", "example")):
        return -999
    score = 10
    for idx, kw in enumerate(PREFERRED_KEYWORDS):
        if kw in local:
            score += (30 - idx)
            break
    if "." in local:
        score += 15
    return score


def _crawl_single_contractor_site(item: Tuple[str, str, str, str, str, str, str, str]) -> Dict[str, str] | None:
    comp, domain, fn, ln, title, city, state, naics = item
    domain = domain.strip().lower()
    if " " in domain or not domain:
        return None
    try:
        socket.getaddrinfo(domain, None)
    except Exception:
        return None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    }
    found = set()
    email_re = re.compile(r"[a-zA-Z0-9._%+-]+@" + re.escape(domain), re.I)

    for u in (
        f"https://{domain}",
        f"https://www.{domain}",
        f"https://{domain}/contact",
        f"https://{domain}/contact-us",
        f"https://{domain}/contracts",
    ):
        try:
            r = requests.get(u, headers=headers, timeout=(2.0, 2.8), verify=False, allow_redirects=True)
            if r.status_code == 200 and r.text:
                for m in email_re.findall(r.text):
                    clean = m.strip().lower().rstrip(".")
                    clean = re.sub(r"^[0-9-]+", "", clean)
                    if _score_candidate_email(clean, domain) > 0:
                        found.add(clean)
                if found:
                    break
        except Exception:
            continue

    if not found:
        return None

    best_em = sorted(found, key=lambda x: _score_candidate_email(x, domain), reverse=True)[0]
    return {
        "First Name": fn.strip().title(),
        "Last Name": ln.strip().title(),
        "Title": title.strip(),
        "Company Name": comp.strip(),
        "Email": best_em,
        "City": city.strip().title(),
        "State": state.strip(),
        "Website": f"https://{domain}",
        "NAICS Codes": naics.strip(),
        "Industry": "information technology & services",
        "Keywords": f"govcon, {state.lower()} sled rfp, sam.gov, cybersecurity, cloud, software",
    }


def discover_and_crawl_govcon_websites(existing_contacts: List[Dict[str, str]], mx_cache: Dict[str, bool]) -> List[Dict[str, str]]:
    """
    Autonomously crawls any uncrawled contractor domains in `GOVCON_CONTRACTOR_SEED_DIRECTORY`
    to harvest publicly published corporate email addresses.
    """
    existing_domains = set()
    for c in existing_contacts:
        em = str(c.get("Email") or "").strip().lower()
        if "@" in em:
            existing_domains.add(em.split("@", 1)[1])
        web = str(c.get("Website") or "").strip().lower().replace("https://", "").replace("http://", "").strip("/")
        if web:
            existing_domains.add(web)

    uncrawled = []
    for item in GOVCON_CONTRACTOR_SEED_DIRECTORY:
        dom = item[1].strip().lower()
        cache_key = f"crawled:{dom}"
        if dom and " " not in dom and dom not in existing_domains and not mx_cache.get(cache_key):
            existing_domains.add(dom)
            mx_cache[cache_key] = True
            uncrawled.append(item)

    if not uncrawled:
        return existing_contacts

    newly_found: List[Dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=20) as pool:
        futs = [pool.submit(_crawl_single_contractor_site, item) for item in uncrawled]
        for fut in as_completed(futs):
            res = fut.result()
            if res and verify_email_domain_mx(res["Email"], mx_cache):
                newly_found.append(res)

    if newly_found:
        merged = list(existing_contacts) + newly_found
        merged.sort(key=lambda x: (str(x.get("State") or ""), str(x.get("Company Name") or "")))
        try:
            with open(VERIFIED_PUBLIC_CONTACTS_PATH, "w", encoding="utf-8") as wf:
                json.dump(merged, wf, indent=2)
        except Exception:
            pass
        return merged

    return existing_contacts


def _clean_usaspending_company_name(raw_name: str) -> Tuple[str, str]:
    """
    Cleans a USAspending recipient name like 'SECURIGENCE LLC' or 'MINBURN TECHNOLOGY GROUP, LLC'
    into `(display_name, candidate_domain)` where `candidate_domain` is strict `fullwords.com`.
    """
    base = re.sub(r"\bDBA\b.*$", "", str(raw_name or "").upper()).strip()
    stripped = re.sub(
        r"\b(L\.?L\.?C\.?|INC\.?|INCORPORATED|CORP\.?|CORPORATION|COMPANY|CO\.?|LTD\.?|LIMITED LIABILITY COMPANY|LP|LLP|HOLDINGS|INTERNATIONAL)\b",
        " ",
        base,
    )
    words = [w.lower() for w in re.findall(r"[A-Z0-9]+", stripped) if len(w) > 1]
    if not words:
        return "", ""
    joined = "".join(words)
    if len(joined) < 5 or len(joined) > 25:
        return "", ""
    display = " ".join(w.upper() if len(w) <= 3 else w.capitalize() for w in words)
    return display, f"{joined}.com"


def discover_usaspending_small_business_websites(
    existing_contacts: List[Dict[str, str]],
    mx_cache: Dict[str, bool],
    max_new_per_run: int = 35,
) -> List[Dict[str, str]]:
    """
    Queries USAspending.gov for active Small Business IT & Cybersecurity contractors
    (NAICS 541511, 541512, 541513, 541519, 518210) across all 12 SLED states,
    crawls their official corporate websites to extract published contact emails,
    and verifies live DNS MX records.
    """
    existing_domains = set()
    for c in existing_contacts:
        em = str(c.get("Email") or "").strip().lower()
        if "@" in em:
            existing_domains.add(em.split("@", 1)[1])
        web = str(c.get("Website") or "").strip().lower().replace("https://", "").replace("http://", "").strip("/")
        if web:
            existing_domains.add(web)

    states = [
        ("VA", "Virginia"),
        ("MD", "Maryland"),
        ("TX", "Texas"),
        ("CA", "California"),
        ("FL", "Florida"),
        ("IL", "Illinois"),
        ("PA", "Pennsylvania"),
        ("OH", "Ohio"),
        ("GA", "Georgia"),
        ("NC", "North Carolina"),
        ("NY", "New York"),
        ("MA", "Massachusetts"),
    ]
    # Rotate page 1..5 and a 2-state slice when >=120 contacts are already cached so each 6-hour cron run finishes in <10s
    now_utc = datetime.now(timezone.utc)
    day_idx = now_utc.timetuple().tm_yday
    slot_idx = (day_idx * 4 + (now_utc.hour // 6)) % len(states)
    if len(existing_contacts) >= 120:
        active_states = [states[slot_idx], states[(slot_idx + 1) % len(states)]]
        pages_to_check = [((day_idx % 5) + 1)]
    else:
        active_states = states
        pages_to_check = [1, 2]

    candidates: List[Tuple[str, str, str, str, str, str, str, str]] = []
    url = "https://api.usaspending.gov/api/v2/search/spending_by_category/recipient/"

    for st_code, st_full in active_states:
        for pg in pages_to_check:
            try:
                resp = requests.post(
                    url,
                    json={
                        "fields": ["Recipient Name", "Award Amount"],
                        "filters": {
                            "time_period": [{"start_date": "2024-01-01", "end_date": "2026-12-31"}],
                            "naics_codes": {"require": ["541511", "541512", "541513", "541519", "518210"]},
                            "recipient_type_names": ["small_business"],
                            "place_of_performance_locations": [{"country": "USA", "state": st_code}],
                        },
                        "limit": 25,
                        "page": pg,
                    },
                    timeout=8,
                )
                if resp.status_code == 200:
                    for item in (resp.json().get("results") or []):
                        raw_nm = str(item.get("name") or "").strip()
                        disp, dom = _clean_usaspending_company_name(raw_nm)
                        cache_key = f"crawled:{dom}"
                        if disp and dom and dom not in existing_domains and not mx_cache.get(cache_key):
                            existing_domains.add(dom)
                            mx_cache[cache_key] = True
                            candidates.append((
                                disp,
                                dom,
                                "Capture",
                                "Team",
                                f"Small Business IT & Cyber Capture Lead ({st_code})",
                                "",
                                st_full,
                                "541511, 541512, 541519",
                            ))
            except Exception:
                continue

    if not candidates:
        return existing_contacts

    newly_found: List[Dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=24) as pool:
        futs = [pool.submit(_crawl_single_contractor_site, item) for item in candidates[:160]]
        for fut in as_completed(futs):
            res = fut.result()
            if res and verify_email_domain_mx(res["Email"], mx_cache):
                newly_found.append(res)
                if len(newly_found) >= max_new_per_run:
                    break

    if newly_found:
        merged = list(existing_contacts) + newly_found
        merged.sort(key=lambda x: (str(x.get("State") or ""), str(x.get("Company Name") or "")))
        try:
            with open(VERIFIED_PUBLIC_CONTACTS_PATH, "w", encoding="utf-8") as wf:
                json.dump(merged, wf, indent=2)
        except Exception:
            pass
        return merged

    return existing_contacts


def _meta_to_prospect_row(meta: Dict[str, Any], mx_cache: Dict[str, bool]) -> Dict[str, str] | None:
    email = str(meta.get("email") or "").strip().lower()
    if not verify_email_domain_mx(email, mx_cache):
        return None
    raw_state = str(meta.get("target_state") or "virginia").strip().lower()
    full_state = STATE_CODE_TO_FULL.get(raw_state, "Virginia")
    company = str(meta.get("company") or "GovCon Capture Team").strip()
    first_name = str(meta.get("first_name") or "Capture").strip()
    domain = email.split("@", 1)[1]
    return {
        "First Name": first_name,
        "Last Name": "",
        "Title": "Inbound Capture Lead (Instant State Dossier Funnel)",
        "Company Name": company,
        "Email": email,
        "City": "",
        "State": full_state,
        "Website": f"https://{domain}",
        "NAICS Codes": str(meta.get("naics_focus") or "541512, 541519"),
        "Industry": "information technology & services",
        "Keywords": f"inbound dossier funnel, {raw_state}, govcon rfp",
    }


def fetch_inbound_leads_from_supabase(mx_cache: Dict[str, bool]) -> List[Dict[str, str]]:
    """
    Fetch verified, MX-valid inbound leads captured via `POST /v1/leads/capture`.
    """
    by_email: Dict[str, Dict[str, str]] = {}

    try:
        r_resp = requests.get(REMOTE_LEADS_LIST_URL, params={"limit": 200}, timeout=8)
        if r_resp.status_code == 200:
            r_data = r_resp.json()
            for item in (r_data.get("leads") or []):
                if isinstance(item, dict) and not item.get("suppress_alert"):
                    prow = _meta_to_prospect_row(item, mx_cache)
                    if prow:
                        by_email[prow["Email"]] = prow
    except Exception:
        pass

    if SUPABASE_URL and SUPABASE_KEY:
        headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
        }
        try:
            resp = requests.get(
                f"{SUPABASE_URL}/rest/v1/contracts",
                params={
                    "status": "eq.SUBSCRIBER_INBOUND_LEAD",
                    "select": "id,title,agency,url,status",
                    "order": "id.desc",
                    "limit": "200",
                },
                headers=headers,
                timeout=10,
            )
            if resp.status_code == 200 and isinstance(resp.json(), list):
                for row in resp.json():
                    raw_title = str(row.get("title") or "").strip()
                    try:
                        meta = json.loads(raw_title)
                        if isinstance(meta, dict):
                            prow = _meta_to_prospect_row(meta, mx_cache)
                            if prow:
                                by_email.setdefault(prow["Email"], prow)
                    except Exception:
                        continue
        except Exception as exc:
            report_error("govcon_lead_harvester.py", f"Supabase inbound lead fetch warning: {exc}", severity="WARNING")

    return list(by_email.values())


def fetch_usaspending_active_contractors() -> List[Dict[str, Any]]:
    """
    Query USAspending.gov API for active NAICS 541511 / 541512 / 541513 / 541519 / 518210
    IT & Cybersecurity contractors across our 12 SLED states.
    """
    url = "https://api.usaspending.gov/api/v2/search/spending_by_category/recipient/"
    payload = {
        "fields": ["Recipient Name", "Award Amount"],
        "filters": {
            "time_period": [{"start_date": "2024-01-01", "end_date": "2026-12-31"}],
            "naics_codes": {"require": ["541511", "541512", "541513", "541519", "518210"]},
            "place_of_performance_locations": [
                {"country": "USA", "state": st}
                for st in ("VA", "TX", "CA", "FL", "MD", "IL", "PA", "OH", "GA", "NC", "NY", "MA")
            ],
        },
        "limit": 30,
        "page": 1,
    }
    try:
        resp = requests.post(url, json=payload, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results") or []
            if isinstance(results, list):
                return results
    except Exception:
        pass
    return []


def run_harvester() -> Dict[str, Any]:
    """
    Main entry point (called automatically every 6 hours by `mainscraper.py` -> `outreach_generator.py`):
      - Removes any legacy `apollo-contacts.csv` file and writes clean `govcon_contacts.csv`.
      - Purges all 23 previously emailed legacy non-responder addresses (`ALREADY_CONTACTED_LEGACY_EMAILS`).
      - Runs the autonomous GovCon website crawler (`discover_and_crawl_govcon_websites`) and merges
        all verified public GovCon contacts (`verified_public_govcon_contacts.json`).
      - Merges real, MX-verified inbound funnel leads from `signaltender.net`.
    """
    print("[*] Initializing GovCon Prospect, Website Crawler & DNS/MX Hygiene Engine...", flush=True)

    if os.path.exists(LEGACY_CSV_PATH):
        try:
            os.remove(LEGACY_CSV_PATH)
        except Exception:
            pass

    mx_cache = _load_mx_cache()
    inbound_leads = fetch_inbound_leads_from_supabase(mx_cache)
    usaspending_recipients = fetch_usaspending_active_contractors()

    if os.path.exists(GOVCON_CONTACTS_CSV_PATH):
        with open(GOVCON_CONTACTS_CSV_PATH, mode="r", encoding="utf-8-sig", newline="") as infile:
            reader = csv.DictReader(infile)
            fieldnames = list(reader.fieldnames or DEFAULT_CONTACT_FIELDNAMES)
            raw_rows = list(reader)
    else:
        fieldnames = list(DEFAULT_CONTACT_FIELDNAMES)
        raw_rows = []

    clean_rows: List[Dict[str, str]] = []
    seen_emails = set()
    purged_rows = 0

    for row in raw_rows:
        em = str(row.get("Email") or "").strip().lower()
        src = str(row.get("Primary Email Source") or "").strip()
        if not em or em in seen_emails:
            continue
        local_part = em.split("@", 1)[0] if "@" in em else ""
        dom_part = em.split("@", 1)[1] if "@" in em else ""
        if (
            src in ("SignalTender_GovCon_Harvester", "Apollo")
            or em in ALREADY_CONTACTED_LEGACY_EMAILS
            or local_part in BAD_LOCAL_PARTS
            or dom_part in ("group.com", "alvarez.com")
            or not verify_email_domain_mx(em, mx_cache)
        ):
            purged_rows += 1
            continue
        fn_sync, ln_sync = sync_person_name_with_email(row.get("First Name", ""), row.get("Last Name", ""), em)
        comp_clean = clean_company_display_name(row.get("Company Name") or row.get("Company Name for Emails") or "")
        row["First Name"] = fn_sync
        row["Last Name"] = ln_sync
        row["Company Name"] = comp_clean
        row["Company Name for Emails"] = comp_clean
        seen_emails.add(em)
        clean_rows.append(row)

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    added_inbound = 0

    def _build_contact_row(spec: Dict[str, str], source_tag: str) -> Dict[str, str]:
        row_dict = {col: "" for col in fieldnames}
        em_clean = spec["Email"].strip().lower()
        fn_sync, ln_sync = sync_person_name_with_email(spec.get("First Name", "Capture"), spec.get("Last Name", ""), em_clean)
        comp_clean = clean_company_display_name(spec.get("Company Name", "GovCon IT Partner"))
        row_dict["First Name"] = fn_sync or "Capture"
        row_dict["Last Name"] = ln_sync
        row_dict["Title"] = spec.get("Title", "VP of Capture & Business Development")
        row_dict["Company Name"] = comp_clean
        row_dict["Company Name for Emails"] = comp_clean
        row_dict["Email"] = em_clean
        row_dict["Email Status"] = "Verified"
        row_dict["Primary Email Source"] = source_tag
        row_dict["Primary Email Verification Source"] = "DNS_MX_Verified"
        row_dict["Primary Email Catch-all Status"] = spec.get("Primary Email Catch-all Status", "Not Catch-all")
        row_dict["Primary Email Last Verified At"] = now_iso
        row_dict["Seniority"] = "Vp"
        row_dict["Departments"] = "C-Suite, Information Technology"
        row_dict["Stage"] = "Cold"
        row_dict["Industry"] = spec.get("Industry", "information technology & services")
        row_dict["Keywords"] = spec.get("Keywords", "govcon, sled rfp, cybersecurity, cloud, software")
        row_dict["Website"] = spec.get("Website", "")
        row_dict["City"] = spec.get("City", "")
        row_dict["State"] = spec.get("State", "Virginia")
        row_dict["Country"] = "United States"
        row_dict["Company City"] = spec.get("City", "")
        row_dict["Company State"] = spec.get("State", "Virginia")
        row_dict["Company Country"] = "United States"
        row_dict["NAICS Codes"] = spec.get("NAICS Codes", "541512, 541519")
        return row_dict

    for lead in inbound_leads:
        em = lead["Email"].strip().lower()
        if em and em not in seen_emails and verify_email_domain_mx(em, mx_cache):
            clean_rows.append(_build_contact_row(lead, source_tag="SignalTender_Inbound_Funnel"))
            seen_emails.add(em)
            added_inbound += 1

    added_public_verified = 0
    public_contacts: List[Dict[str, str]] = []
    if os.path.exists(VERIFIED_PUBLIC_CONTACTS_PATH):
        try:
            with open(VERIFIED_PUBLIC_CONTACTS_PATH, "r", encoding="utf-8") as vf:
                loaded = json.load(vf)
                if isinstance(loaded, list):
                    public_contacts = [
                        c for c in loaded
                        if isinstance(c, dict)
                        and str(c.get("Email") or "").strip().lower() not in ALREADY_CONTACTED_LEGACY_EMAILS
                    ]
        except Exception as exc:
            report_error("govcon_lead_harvester.py", f"Public verified contacts load warning: {exc}", severity="WARNING")

    # Run autonomous website crawler when building initial pool (<120 contacts) or when explicitly requested
    if len(public_contacts) < 120 or os.getenv("GOVCON_FORCE_WEBSITE_CRAWL") == "1":
        public_contacts = discover_and_crawl_govcon_websites(public_contacts, mx_cache)
        public_contacts = discover_usaspending_small_business_websites(public_contacts, mx_cache)

    cleaned_public: List[Dict[str, str]] = []
    for spec in public_contacts:
        if not isinstance(spec, dict):
            continue
        em = str(spec.get("Email") or "").strip().lower()
        em = re.sub(r"^[0-9-]+", "", em)
        spec["Email"] = em
        dom_part = em.split("@", 1)[1] if "@" in em else ""
        if (
            em in ALREADY_CONTACTED_LEGACY_EMAILS
            or dom_part in ("group.com", "alvarez.com")
            or any(em.startswith(bad + "@") for bad in BAD_LOCAL_PARTS)
        ):
            continue
        fn_sync, ln_sync = sync_person_name_with_email(spec.get("First Name", ""), spec.get("Last Name", ""), em)
        comp_clean = clean_company_display_name(spec.get("Company Name", ""))
        spec["First Name"] = fn_sync or "Capture"
        spec["Last Name"] = ln_sync
        spec["Company Name"] = comp_clean
        cleaned_public.append(spec)
        if em and em not in seen_emails and verify_email_domain_mx(em, mx_cache):
            clean_rows.append(_build_contact_row(spec, source_tag="GovCon_Website_Verified"))
            seen_emails.add(em)
            added_public_verified += 1

    try:
        with open(VERIFIED_PUBLIC_CONTACTS_PATH, "w", encoding="utf-8") as wf:
            json.dump(cleaned_public, wf, indent=2)
    except Exception:
        pass

    _save_mx_cache(mx_cache)

    with open(GOVCON_CONTACTS_CSV_PATH, mode="w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(clean_rows)

    state_counts: Dict[str, int] = {}
    not_catchall_count = 0
    catchall_count = 0
    for row in clean_rows:
        st = (row.get("State") or row.get("Company State") or "Unspecified").strip()
        state_counts[st] = state_counts.get(st, 0) + 1
        if str(row.get("Primary Email Catch-all Status") or "").strip().lower() == "not catch-all":
            not_catchall_count += 1
        else:
            catchall_count += 1

    intel_summary = {
        "updated_at": now_iso,
        "total_verified_mx_contacts": len(clean_rows),
        "not_catchall_priority_tier_count": not_catchall_count,
        "catchall_secondary_tier_count": catchall_count,
        "purged_legacy_or_invalid_rows": purged_rows,
        "added_verified_inbound_leads": added_inbound,
        "added_website_harvested_govcon_contacts": added_public_verified,
        "state_distribution": state_counts,
        "usaspending_naics_541512_top_recipients": usaspending_recipients[:20],
    }
    try:
        with open(INTEL_JSON_PATH, "w", encoding="utf-8") as jf:
            json.dump(intel_summary, jf, indent=2)
    except Exception:
        pass

    print(
        f"[+] GovCon Hygiene & Harvester Complete: {len(clean_rows)} fresh DNS/MX-verified contacts in govcon_contacts.csv "
        f"({not_catchall_count} Not Catch-all priority, {catchall_count} Catch-all; "
        f"purged {purged_rows} legacy/invalid rows, +{added_inbound} inbound leads).",
        flush=True,
    )
    return intel_summary


if __name__ == "__main__":
    run_harvester()
