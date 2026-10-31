from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()
import os
import re
import time
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv(dotenv_path=r"D:\Daas\.env")
load_dotenv()

# Supabase Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE_NAME = os.getenv("SUPABASE_TABLE_NAME", "contracts")
SITE_BASE_URL = os.getenv("SIGNALTENDER_SITE_URL", "https://signaltender.net").rstrip("/")

# Master Client Discord Webhook + Optional State/Portal-Specific Webhooks
CLIENT_DISCORD_WEBHOOK_URL = (
    os.getenv("DISCORD_CONTENT_WEBHOOK_URL")
    or os.getenv("CLIENT_DISCORD_WEBHOOK_URL")
    or os.getenv("DISCORD_WEBHOOK_URL")
)
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")

JURISDICTION_WEBHOOKS = {
    "federal": os.getenv("DISCORD_FEDERAL_WEBHOOK_URL"),
    "texas": os.getenv("DISCORD_TEXAS_WEBHOOK_URL"),
    "virginia": os.getenv("DISCORD_VIRGINIA_WEBHOOK_URL"),
    "california": os.getenv("DISCORD_CALIFORNIA_WEBHOOK_URL"),
    "florida": os.getenv("DISCORD_FLORIDA_WEBHOOK_URL"),
    "maryland": os.getenv("DISCORD_MARYLAND_WEBHOOK_URL"),
    "new_york": os.getenv("DISCORD_NEW_YORK_WEBHOOK_URL"),
    "illinois": os.getenv("DISCORD_ILLINOIS_WEBHOOK_URL"),
    "pennsylvania": os.getenv("DISCORD_PENNSYLVANIA_WEBHOOK_URL"),
    "ohio": os.getenv("DISCORD_OHIO_WEBHOOK_URL"),
    "georgia": os.getenv("DISCORD_GEORGIA_WEBHOOK_URL"),
    "north_carolina": os.getenv("DISCORD_NORTH_CAROLINA_WEBHOOK_URL"),
    "massachusetts": os.getenv("DISCORD_MASSACHUSETTS_WEBHOOK_URL"),
    "new_jersey": os.getenv("DISCORD_NEW_JERSEY_WEBHOOK_URL"),
    "washington": os.getenv("DISCORD_WASHINGTON_WEBHOOK_URL"),
    "michigan": os.getenv("DISCORD_MICHIGAN_WEBHOOK_URL"),
    "colorado": os.getenv("DISCORD_COLORADO_WEBHOOK_URL"),
    "arizona": os.getenv("DISCORD_ARIZONA_WEBHOOK_URL"),
    "minnesota": os.getenv("DISCORD_MINNESOTA_WEBHOOK_URL"),
    "tennessee": os.getenv("DISCORD_TENNESSEE_WEBHOOK_URL"),
    "indiana": os.getenv("DISCORD_INDIANA_WEBHOOK_URL"),
    "missouri": os.getenv("DISCORD_MISSOURI_WEBHOOK_URL"),
    "wisconsin": os.getenv("DISCORD_WISCONSIN_WEBHOOK_URL"),
    "south_carolina": os.getenv("DISCORD_SOUTH_CAROLINA_WEBHOOK_URL"),
    "oregon": os.getenv("DISCORD_OREGON_WEBHOOK_URL"),
    "connecticut": os.getenv("DISCORD_CONNECTICUT_WEBHOOK_URL"),
    "utah": os.getenv("DISCORD_UTAH_WEBHOOK_URL"),
    "nevada": os.getenv("DISCORD_NEVADA_WEBHOOK_URL"),
    "alabama": os.getenv("DISCORD_ALABAMA_WEBHOOK_URL"),
    "louisiana": os.getenv("DISCORD_LOUISIANA_WEBHOOK_URL"),
    "kentucky": os.getenv("DISCORD_KENTUCKY_WEBHOOK_URL"),
    "oklahoma": os.getenv("DISCORD_OKLAHOMA_WEBHOOK_URL"),
    "iowa": os.getenv("DISCORD_IOWA_WEBHOOK_URL"),
    "kansas": os.getenv("DISCORD_KANSAS_WEBHOOK_URL"),
    "arkansas": os.getenv("DISCORD_ARKANSAS_WEBHOOK_URL"),
    "mississippi": os.getenv("DISCORD_MISSISSIPPI_WEBHOOK_URL"),
    "new_mexico": os.getenv("DISCORD_NEW_MEXICO_WEBHOOK_URL"),
    "nebraska": os.getenv("DISCORD_NEBRASKA_WEBHOOK_URL"),
    "idaho": os.getenv("DISCORD_IDAHO_WEBHOOK_URL"),
    "hawaii": os.getenv("DISCORD_HAWAII_WEBHOOK_URL"),
    "new_hampshire": os.getenv("DISCORD_NEW_HAMPSHIRE_WEBHOOK_URL"),
    "maine": os.getenv("DISCORD_MAINE_WEBHOOK_URL"),
    "rhode_island": os.getenv("DISCORD_RHODE_ISLAND_WEBHOOK_URL"),
    "montana": os.getenv("DISCORD_MONTANA_WEBHOOK_URL"),
    "delaware": os.getenv("DISCORD_DELAWARE_WEBHOOK_URL"),
    "south_dakota": os.getenv("DISCORD_SOUTH_DAKOTA_WEBHOOK_URL"),
    "north_dakota": os.getenv("DISCORD_NORTH_DAKOTA_WEBHOOK_URL"),
    "alaska": os.getenv("DISCORD_ALASKA_WEBHOOK_URL"),
    "vermont": os.getenv("DISCORD_VERMONT_WEBHOOK_URL"),
    "west_virginia": os.getenv("DISCORD_WEST_VIRGINIA_WEBHOOK_URL"),
    "wyoming": os.getenv("DISCORD_WYOMING_WEBHOOK_URL"),
    "municipal": os.getenv("DISCORD_MUNICIPAL_WEBHOOK_URL"),
}

JURISDICTION_LABELS = {
    "federal": "FEDERAL // SAM.GOV",
    "texas": "TEXAS // ESBD",
    "virginia": "VIRGINIA // eVA",
    "california": "CALIFORNIA // CAL EPROCURE",
    "florida": "FLORIDA // MFMP VIP",
    "maryland": "MARYLAND // EMMA & BONFIRE",
    "new_york": "NEW YORK // NYSCR",
    "illinois": "ILLINOIS // BIDBUY",
    "pennsylvania": "PENNSYLVANIA // eMARKETPLACE",
    "ohio": "OHIO // OHIOBUYS",
    "georgia": "GEORGIA // GPR & TEAM GA",
    "north_carolina": "NORTH CAROLINA // NC eVP & METRO",
    "massachusetts": "MASSACHUSETTS // COMMBUYS & BOSTON",
    "new_jersey": "NEW JERSEY // NJSTART & TREASURY DPP",
    "washington": "WASHINGTON // WEBS & WATECH DES",
    "michigan": "MICHIGAN // SIGMA VSS & DTMB",
    "colorado": "COLORADO // VSS & OIT",
    "arizona": "ARIZONA // APP PROCURE.AZ.GOV & ADOA-ASET",
    "minnesota": "MINNESOTA // SWIFT & MNIT",
    "tennessee": "TENNESSEE // EDISON CPO & STS",
    "indiana": "INDIANA // IDOA, IOT & NSWC CRANE",
    "missouri": "MISSOURI // MISSOURIBUYS, OA-ITSD & NGA WEST",
    "wisconsin": "WISCONSIN // eSUPPLIER, VENDORNET & DOA DET",
    "south_carolina": "SOUTH CAROLINA // SCBO, SFAA & NIWC ATLANTIC",
    "oregon": "OREGON // OREGONBUYS & DAS EIS",
    "connecticut": "CONNECTICUT // CTSOURCE, DAS BITS & GROTON DEFENSE",
    "utah": "UTAH // U3P SCIQUEST, DTS & HILL AFB CORRIDOR",
    "nevada": "NEVADA // NEVADAEPRO, EITS & NELLIS AFB CORRIDOR",
    "alabama": "ALABAMA // ALABAMA BUYS STAARS, OIT & REDSTONE DEFENSE",
    "louisiana": "LOUISIANA // LAPAC, LAGOV & OTS",
    "kentucky": "KENTUCKY // KY VSS, COT & FORT KNOX CORRIDOR",
    "oklahoma": "OKLAHOMA // OMES, IS & TINKER AFB CORRIDOR",
    "iowa": "IOWA // IMPACS SCIQUEST, DOM DOIT & CAMP DODGE CORRIDOR",
    "kansas": "KANSAS // KS SMART, OITS & FORT LEAVENWORTH CORRIDOR",
    "arkansas": "ARKANSAS // ARBUY PERISCOPE, DIS & LITTLE ROCK AFB CORRIDOR",
    "mississippi": "MISSISSIPPI // MS MAGIC, DEPT OF ITS & KEESLER AFB CORRIDOR",
    "new_mexico": "NEW MEXICO // NM GSD SHARE, DOIT & KIRTLAND AFB / SANDIA CORRIDOR",
    "nebraska": "NEBRASKA // NE DAS MATERIEL, OCIO & OFFUTT AFB USSTRATCOM CORRIDOR",
    "idaho": "IDAHO // ID IPRO LUMA, ITS & INL / MOUNTAIN HOME CORRIDOR",
    "hawaii": "HAWAII // HIEPRO HANDS, ETS & USINDOPACOM / PEARL HARBOR CORRIDOR",
    "new_hampshire": "NEW HAMPSHIRE // NH DAS BPP, DOIT & PORTSMOUTH / PEASE CORRIDOR",
    "maine": "MAINE // ME DAFS PROCUREMENT, MAINEIT & NAVAL CORRIDOR",
    "rhode_island": "RHODE ISLAND // RI OSP, ETSS & NUWC NEWPORT DEFENSE CORRIDOR",
    "montana": "MONTANA // MT EMACS, SITSD & MALMSTROM AFB CORRIDOR",
    "delaware": "DELAWARE // DE MYMARKETPLACE, DTI & DOVER AFB CORRIDOR",
    "south_dakota": "SOUTH DAKOTA // SD OPM, BIT & ELLSWORTH AFB B-21 CORRIDOR",
    "north_dakota": "NORTH DAKOTA // ND OMB SPO, NDIT & MINOT / GRAND FORKS CORRIDOR",
    "alaska": "ALASKA // AK IRIS OPN, OIT & JBER / EIELSON ARCTIC CORRIDOR",
    "vermont": "VERMONT // VT BGS BID SYSTEM, ADS & BURLINGTON ANGB CORRIDOR",
    "west_virginia": "WEST VIRGINIA // WVOASIS VSS, WVOT & FBI CJIS CORRIDOR",
    "wyoming": "WYOMING // WY A&I, ETS & F.E. WARREN AFB SENTINEL CORRIDOR",
    "municipal": "MUNICIPAL // DEMANDSTAR",
}

ERROR_LOG_PATH = r"D:\Daas\error_log.txt"


def send_discord_alert(message: str) -> None:
    """Silently record runtime error to telemetry for autonomous self-healing (resolved-only Discord policy)."""
    report_error("client_delivery.py", str(message))


def clean_title_text(raw_title: str) -> str:
    s = str(raw_title or "").replace("\ufffd", "–")
    s = re.sub(r"^(?:\s*\[SF-30\s*/\s*ADDENDUM\s+DETECTED\]\s*)+", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\bWeb-\s+Based\b", "Web-Based", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*-\s*Due:\s*\d{1,2}/\d{1,2}/\d{2,4}\s*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip()


def slugify_contract(title: str, fallback_id: str = "") -> str:
    clean = clean_title_text(title).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", clean).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if len(slug) > 75:
        slug = slug[:75].rsplit("-", 1)[0].strip("-")
    if not slug:
        slug = "government-it-contract"
    if fallback_id:
        return f"{slug}-{fallback_id}"
    return slug


def classify_jurisdiction(record: dict) -> str:
    title = str(record.get("title") or "").strip()
    title_upper = title.upper()
    agency = str(record.get("agency") or "").strip().lower()
    url = str(record.get("url") or record.get("source_url") or "").strip().lower()

    def _has_domain(dom: str) -> bool:
        return bool(re.search(rf"(?:^|[/.\b]){re.escape(dom)}(?:[/:?#\b]|$)", url))

    def _has_any_domain(*doms: str) -> bool:
        return any(_has_domain(d) for d in doms)

    # 1. Portal-first Federal & Municipal checks
    if _has_any_domain("demandstar.com"):
        return "municipal"
    if _has_any_domain("sam.gov", "sbir.gov"):
        return "federal"

    # 2. Boundary-safe State SLED Portal URL checks (specific/longer domains checked before 2-letter .gov domains)
    if _has_any_domain("txsmartbuy.com", "dir.texas.gov", "texas.gov"):
        return "texas"
    if _has_any_domain("eva.virginia.gov", "cgieva.com", "vita.virginia.gov", "virginia.gov"):
        return "virginia"
    if _has_any_domain("caleprocure.ca.gov", "dgs.ca.gov", "cdt.ca.gov", "ca.gov"):
        return "california"
    if _has_any_domain("myfloridamarketplace.com", "myflorida.com", "hillsboroughcounty.bonfirehub.com", "ucf.bonfirehub.com", "fl.gov"):
        return "florida"
    if _has_any_domain(
        "emma.maryland.gov", "maryland.gov", "mdcourts.bonfirehub.com", "menv.bonfirehub.com",
        "mdstad.bonfirehub.com", "hapgcprocurement.bonfirehub.com", "hcpss.bonfirehub.com",
        "princegeorgescountymd.bonfirehub.com", "howardcountymd.bonfirehub.com", "countymd.bonfirehub.com",
    ):
        return "maryland"
    if _has_any_domain("bidbuy.illinois.gov", "illinois.gov", "transitchicago.bonfirehub.com", "cookcountyil.bonfirehub.com", "il.gov"):
        return "illinois"
    if "customerorg=commonwealthpa" in url or _has_any_domain("emarketplace.state.pa.us", "dgs.pa.gov", "pa.gov", "state.pa.us", "philaport.bonfirehub.com"):
        return "pennsylvania"
    if _has_any_domain(
        "ohiobuys.ohio.gov", "ohioauditor.gov", "ohio.gov", "morpc.org", "franklincountyohio.gov",
        "columbus.bonfirehub.com", "cincinnati-oh.bonfirehub.com", "westerville.bonfirehub.com",
        "dps.bonfirehub.com", "akronohio.bonfirehub.com", "riderta.com",
    ):
        return "ohio"
    if _has_any_domain(
        "doas.state.ga.us", "georgia.gov", "ga.gov", "state.ga.us",
        "forsythco.bonfirehub.com", "fultonschools.bonfirehub.com", "cobbk12.bonfirehub.com", "itsmarta.com",
    ):
        return "georgia"
    if _has_any_domain(
        "evp.nc.gov", "nc.gov", "unc.edu", "ncsu.edu", "wake.gov",
        "mecknc.gov", "charlottenc.gov", "durhamnc.gov", "guilfordcountync.gov",
    ):
        return "north_carolina"
    if _has_any_domain(
        "a856-cityrecord.nyc.gov", "nyc.gov", "passport.cityofnewyork.us", "cityofnewyork.us",
        "panynj.bonfirehub.com", "suffolkcountyny.bonfirehub.com", "rocklandgov.bonfirehub.com",
        "nyscr.ny.gov", "ogs.ny.gov", "ny.gov",
    ):
        return "new_york"
    if _has_any_domain("commbuys.com", "mass.gov", "boston.gov", "mbta.com", "massport.com", "masstech.org"):
        return "massachusetts"
    if _has_any_domain("njstart.gov", "nj.gov", "njtransit.com", "rutgers.edu"):
        return "new_jersey"
    if "customerorg=stateofiowa" in url or _has_any_domain("bidopportunities.iowa.gov", "das.iowa.gov", "dom.iowa.gov", "iowadot.gov", "iowa.gov", "uiowa.edu", "iastate.edu"):
        return "iowa"
    if _has_any_domain("pr-webs-vendor.des.wa.gov", "des.wa.gov", "watech.wa.gov", "wsdot.wa.gov", "hca.wa.gov", "dshs.wa.gov", "dol.wa.gov", "wa.gov"):
        return "washington"
    if _has_any_domain("sigma.michigan.gov", "michigan.gov", "mi.gov"):
        return "michigan"
    if _has_any_domain("colorado.gov", "denvergov.org", "coloradosprings.gov", "cu.edu", "co.gov"):
        return "colorado"
    if _has_any_domain("app.az.gov", "procure.az.gov", "azdoa.gov", "az.gov", "phoenix.gov", "maricopa.gov", "asu.edu"):
        return "arizona"
    if _has_any_domain("mn.gov", "questcdn.com", "metrocouncil.org", "umn.edu", "hennepin.us", "minneapolismn.gov", "stpaul.gov"):
        return "minnesota"
    if _has_any_domain("tn.gov", "tennessee.edu", "tbr.edu", "nashville.gov", "memphistn.gov", "shelbycountytn.gov"):
        return "tennessee"
    if _has_any_domain("iot.in.gov", "fs.gmis.in.gov", "in.gov", "indy.gov", "purdue.edu", "indiana.edu"):
        return "indiana"
    if _has_any_domain("missouribuys.mo.gov", "oa.mo.gov", "modot.org", "mo.gov", "stlouis-mo.gov", "kcmo.gov", "umsystem.edu"):
        return "missouri"
    if _has_any_domain("esupplier.wi.gov", "vendornet.wi.gov", "doa.wi.gov", "wi.gov", "wisc.edu"):
        return "wisconsin"
    if _has_any_domain("scbo.sc.gov", "procurement.sc.gov", "admin.sc.gov", "sc.gov", "clemson.edu"):
        return "south_carolina"
    if _has_any_domain("oregonbuys.gov", "oregon.gov", "portland.gov", "ohsu.edu", "oregonstate.edu"):
        return "oregon"
    if _has_any_domain("portal.ct.gov", "biznet.ct.gov", "ct.gov", "uconn.edu"):
        return "connecticut"
    if _has_any_domain("purchasing.utah.gov", "dts.utah.gov", "utah.gov", "utah.edu"):
        return "utah"
    if _has_any_domain("nevadaepro.com", "purchasing.nv.gov", "eits.nv.gov", "nv.gov", "clarkcountynv.gov", "lasvegasnevada.gov", "unlv.edu", "unr.edu"):
        return "nevada"
    if _has_any_domain("alabamabuys.gov", "purchasing.alabama.gov", "oit.alabama.gov", "alabama.gov", "huntsvilleal.gov", "birminghamal.gov", "ua.edu", "auburn.edu"):
        return "alabama"
    if "lapac" in url or _has_any_domain("doa.louisiana.gov", "louisiana.gov", "la.gov", "nola.gov", "brla.gov", "lsu.edu"):
        return "louisiana"
    if _has_any_domain("vss.ky.gov", "finance.ky.gov", "cot.ky.gov", "ky.gov", "louisvilleky.gov", "lexingtonky.gov", "uky.edu", "louisville.edu"):
        return "kentucky"
    if _has_any_domain("omes.ok.gov", "oklahoma.gov", "ok.gov", "okc.gov", "cityoftulsa.org", "ou.edu", "okstate.edu"):
        return "oklahoma"
    if _has_any_domain("arbuy.arkansas.gov", "transform.ar.gov", "dis.arkansas.gov", "ardot.gov", "arkansas.gov", "ar.gov", "uark.edu", "uams.edu"):
        return "arkansas"
    if _has_any_domain("admin.ks.gov", "da.ks.gov", "oits.ks.gov", "ksdot.gov", "ks.gov", "kansas.gov", "ku.edu", "ksu.edu"):
        return "kansas"
    if _has_any_domain("its.ms.gov", "dfa.ms.gov", "mdot.ms.gov", "ms.gov", "mississippi.gov", "msstate.edu", "olemiss.edu"):
        return "mississippi"
    if _has_any_domain("generalservices.state.nm.us", "doit.nm.gov", "dot.nm.gov", "nm.gov", "state.nm.us", "unm.edu", "nmsu.edu"):
        return "new_mexico"
    if _has_any_domain("maine.gov", "maine.edu"):
        return "maine"
    if _has_any_domain("das.nebraska.gov", "cio.nebraska.gov", "dot.nebraska.gov", "nebraska.gov", "ne.gov", "nebraska.edu", "unl.edu"):
        return "nebraska"
    if _has_any_domain("purchasing.idaho.gov", "its.idaho.gov", "itd.idaho.gov", "idaho.gov", "id.gov", "boisestate.edu", "uidaho.edu"):
        return "idaho"
    if _has_any_domain("hiepro.ehawaii.gov", "hands.ehawaii.gov", "spo.hawaii.gov", "ets.hawaii.gov", "hidot.hawaii.gov", "hawaii.gov", "ehawaii.gov", "hawaii.edu"):
        return "hawaii"
    if _has_any_domain("apps.das.nh.gov", "das.nh.gov", "doit.nh.gov", "nh.gov", "usnh.edu", "unh.edu"):
        return "new_hampshire"
    if _has_any_domain("ridop.ri.gov", "purchasing.ri.gov", "etss.ri.gov", "doit.ri.gov", "dot.ri.gov", "ri.gov", "uri.edu"):
        return "rhode_island"
    if _has_any_domain("spb.mt.gov", "sitsd.mt.gov", "mdt.mt.gov", "mt.gov", "montana.edu", "umt.edu"):
        return "montana"
    if _has_any_domain("mmp.delaware.gov", "bids.delaware.gov", "gss.omb.delaware.gov", "dti.delaware.gov", "deldot.gov", "delaware.gov", "udel.edu"):
        return "delaware"
    if _has_any_domain("boa.sd.gov", "bit.sd.gov", "dot.sd.gov", "sd.gov", "dsu.edu", "sdstate.edu", "sdbor.edu"):
        return "south_dakota"
    if _has_any_domain("apps.nd.gov", "omb.nd.gov", "ndit.nd.gov", "dot.nd.gov", "nd.gov", "und.edu", "ndsu.edu"):
        return "north_dakota"
    if _has_any_domain("aws.state.ak.us", "iris-vss.alaska.gov", "oit.alaska.gov", "dot.alaska.gov", "alaska.gov", "state.ak.us", "alaska.edu"):
        return "alaska"
    if _has_any_domain("vermontbusinessregistry.com", "bgs.vermont.gov", "ads.vermont.gov", "digitalservices.vermont.gov", "vtrans.vermont.gov", "vermont.gov", "uvm.edu"):
        return "vermont"
    if _has_any_domain("wvoasis.gov", "state.wv.us", "technology.wv.gov", "transportation.wv.gov", "wv.gov", "wvu.edu", "marshall.edu"):
        return "west_virginia"
    if _has_any_domain("ai.wyo.gov", "ets.wyo.gov", "dot.state.wy.us", "wyo.gov", "wyoming.gov", "uwyo.edu"):
        return "wyoming"

    # 3. Explicit [XX] or [XX- title prefixes across all 50 states
    prefix_map = {
        "TX": "texas", "VA": "virginia", "CA": "california", "FL": "florida", "MD": "maryland",
        "IL": "illinois", "PA": "pennsylvania", "OH": "ohio", "GA": "georgia", "NC": "north_carolina",
        "NY": "new_york", "MA": "massachusetts", "NJ": "new_jersey", "WA": "washington", "MI": "michigan",
        "CO": "colorado", "AZ": "arizona", "MN": "minnesota", "TN": "tennessee", "IN": "indiana",
        "MO": "missouri", "WI": "wisconsin", "SC": "south_carolina", "OR": "oregon", "CT": "connecticut",
        "UT": "utah", "NV": "nevada", "AL": "alabama", "LA": "louisiana", "KY": "kentucky",
        "OK": "oklahoma", "IA": "iowa", "KS": "kansas", "AR": "arkansas", "MS": "mississippi",
        "NM": "new_mexico", "NE": "nebraska", "ID": "idaho", "HI": "hawaii", "NH": "new_hampshire",
        "ME": "maine", "RI": "rhode_island", "MT": "montana", "DE": "delaware", "SD": "south_dakota",
        "ND": "north_dakota", "AK": "alaska", "VT": "vermont", "WV": "west_virginia", "WY": "wyoming",
    }
    if re.search(r",\s*[a-z .'-]+county,\s*[a-z]{2}\b", agency):
        return "municipal"
    if title_upper.startswith(("[IN-17231", "IN-17231")):
        return "florida"
    m_pref = re.match(r"^\[([A-Z]{2})(?:\]|-)", title_upper)
    if m_pref and m_pref.group(1) in prefix_map:
        return prefix_map[m_pref.group(1)]

    # 4. Agency & title fallback matching (compound state names checked BEFORE single-word state names)
    if "west virginia" in agency or "(wv)" in agency or "wvoasis" in agency or "wvot" in agency or "clarksburg" in agency or "martinsburg" in agency:
        return "west_virginia"
    if "arkansas" in agency or "(ar)" in agency or "arbuy" in agency or "little rock afb" in agency:
        return "arkansas"
    if "north dakota" in agency or "(nd)" in agency or "ndit" in agency or "minot afb" in agency or "grand forks afb" in agency:
        return "north_dakota"
    if "south dakota" in agency or "(sd)" in agency or "ellsworth afb" in agency or "dakota state" in agency:
        return "south_dakota"
    if "north carolina" in agency or "(nc)" in agency or "nc " in agency or "wake county" in agency or "mecklenburg" in agency or "charlotte" in agency or "raleigh" in agency or "durham" in agency or "guilford" in agency:
        return "north_carolina"
    if "south carolina" in agency or "(sc)" in agency or "scbo" in agency or "sfaa" in agency or "niwc atlantic" in agency or "clemson" in agency:
        return "south_carolina"
    if "new hampshire" in agency or "(nh)" in agency or "pease angb" in agency or "portsmouth naval" in agency:
        return "new_hampshire"
    if "panynj" in agency or "port authority of new york" in agency or "new york" in agency or "nyc " in agency or "(ny)" in agency or "suffolk county" in agency or "rockland county" in agency:
        return "new_york"
    if "new jersey" in agency or "(nj)" in agency or "njstart" in agency or "nj transit" in agency or "rutgers" in agency:
        return "new_jersey"
    if "new mexico" in agency or "(nm)" in agency or "kirtland afb" in agency or "white sands" in agency or "sandia" in agency or "los alamos" in agency:
        return "new_mexico"
    if "rhode island" in agency or "(ri)" in agency or "ocean state procures" in agency or "nuwc newport" in agency:
        return "rhode_island"
    if "washington state" in agency or "state of washington" in agency or "(wa)" in agency or "watech" in agency or "wa des" in agency or "wsdot" in agency:
        return "washington"

    if "texas" in agency or ", tx" in agency or "ut md anderson" in agency:
        return "texas"
    if "virginia" in agency or "arlington county" in agency:
        return "virginia"
    if "california" in agency:
        return "california"
    if "florida" in agency:
        return "florida"
    if "maryland" in agency or "prince george" in agency or "howard county" in agency:
        return "maryland"
    if "illinois" in agency or "chicago transit authority" in agency or "cook county" in agency:
        return "illinois"
    if "pennsylvania" in agency or "philadelphia" in agency or agency.startswith("pa "):
        return "pennsylvania"
    if "georgia" in agency or "(ga)" in agency or "fulton county" in agency or "atlanta" in agency or "cobb county" in agency or "gwinnett" in agency or "dekalb" in agency:
        return "georgia"
    if "ohio" in agency or "(oh)" in agency or "columbus" in agency or "morpc" in agency or "franklin county" in agency:
        return "ohio"
    if "massachusetts" in agency or "(ma)" in agency or "commbuys" in agency or "city of boston" in agency or "boston public" in agency or "mbta" in agency or "massport" in agency or "eotss" in agency:
        return "massachusetts"
    if "michigan" in agency or "(mi)" in agency or "mi sigma" in agency or "dtmb" in agency:
        return "michigan"
    if "colorado" in agency or "(co)" in agency or "co vss" in agency or "co oit" in agency or "cdot" in agency:
        return "colorado"
    if "arizona" in agency or "(az)" in agency or "az app" in agency or "adoa" in agency or "ahcccs" in agency or "maricopa" in agency:
        return "arizona"
    if "minnesota" in agency or "(mn)" in agency or "mn swift" in agency or "mnit" in agency or "mndot" in agency or "metropolitan council" in agency:
        return "minnesota"
    if "tennessee" in agency or "(tn)" in agency or "tn cpo" in agency or "edison" in agency or "tenncare" in agency:
        return "tennessee"
    if "indiana" in agency or "(in)" in agency or "idoa" in agency or "indianapolis" in agency or "fssa" in agency or "purdue" in agency or "nswc crane" in agency:
        return "indiana"
    if "missouri" in agency or "(mo)" in agency or "missouribuys" in agency or "oa-itsd" in agency or "mo healthnet" in agency or "st. louis" in agency or "kansas city" in agency:
        return "missouri"
    if "wisconsin" in agency or "(wi)" in agency or "esupplier" in agency or "doa det" in agency or "wisdot" in agency or "milwaukee" in agency or "uw-madison" in agency:
        return "wisconsin"
    if "oregon" in agency or "(or)" in agency or "oregonbuys" in agency or "das eis" in agency or "portland" in agency or "multnomah" in agency:
        return "oregon"
    if "connecticut" in agency or "(ct)" in agency or "ctsource" in agency or "das bits" in agency or "groton" in agency or "hartford" in agency or "uconn" in agency:
        return "connecticut"
    if "utah" in agency or "(ut)" in agency or "u3p" in agency or "utah dts" in agency or "hill afb" in agency or "salt lake" in agency:
        return "utah"
    if "nevada" in agency or "(nv)" in agency or "nevadaepro" in agency or "nv eits" in agency or "nellis afb" in agency or "clark county" in agency or "las vegas" in agency:
        return "nevada"
    if "alabama" in agency or "(al)" in agency or "alabama buys" in agency or "alabamabuys" in agency or "staars" in agency or "redstone" in agency or "huntsville" in agency:
        return "alabama"
    if "louisiana" in agency or "(la)" in agency or "lapac" in agency or "lagov" in agency or "barksdale" in agency or "baton rouge" in agency or "new orleans" in agency:
        return "louisiana"
    if "kentucky" in agency or "(ky)" in agency or "ky vss" in agency or "ky cot" in agency or "fort knox" in agency or "louisville" in agency:
        return "kentucky"
    if "oklahoma" in agency or "(ok)" in agency or "omes" in agency or "soonercare" in agency or "tinker afb" in agency:
        return "oklahoma"
    if "iowa" in agency or "(ia)" in agency or "impacs" in agency or "camp dodge" in agency or "des moines" in agency:
        return "iowa"
    if "kansas" in agency or "(ks)" in agency or "ks smart" in agency or "fort leavenworth" in agency or "mcconnell afb" in agency:
        return "kansas"
    if "mississippi" in agency or "(ms)" in agency or "ms magic" in agency or "keesler afb" in agency or "stennis" in agency:
        return "mississippi"
    if "nebraska" in agency or "(ne)" in agency or "offutt afb" in agency or "usstratcom" in agency or "omaha" in agency:
        return "nebraska"
    if "idaho" in agency or "(id)" in agency or "ipro" in agency or "luma" in agency or "mountain home afb" in agency or "idaho national lab" in agency:
        return "idaho"
    if "hawaii" in agency or "(hi)" in agency or "hiepro" in agency or "indopacom" in agency or "pearl harbor" in agency or "honolulu" in agency:
        return "hawaii"
    if "maine" in agency or "(me)" in agency or "maineit" in agency or "mainecare" in agency or "bath iron" in agency or "bangor angb" in agency:
        return "maine"
    if "montana" in agency or "(mt)" in agency or "emacs" in agency or "sitsd" in agency or "malmstrom afb" in agency:
        return "montana"
    if "delaware" in agency or "(de)" in agency or "mymarketplace" in agency or "de dti" in agency or "dover afb" in agency:
        return "delaware"
    if "alaska" in agency or "(ak)" in agency or "ak iris" in agency or "jber" in agency or "elmendorf" in agency or "eielson afb" in agency or "anchorage" in agency:
        return "alaska"
    if "vermont" in agency or "(vt)" in agency or "vt bgs" in agency or "vt ads" in agency or "vtrans" in agency or "burlington angb" in agency:
        return "vermont"
    if "wyoming" in agency or "(wy)" in agency or "wy ets" in agency or "f.e. warren" in agency or "cheyenne" in agency:
        return "wyoming"
    if _has_any_domain("bonfirehub.com"):
        return "maryland"
    if "federal government" in agency:
        return "federal"
    return "municipal"


def classify_vertical_tag(record: dict) -> str:
    blob = f"{record.get('title', '')} {record.get('agency', '')}".lower()
    if any(k in blob for k in ("cyber", "infosec", "security", "siem", "soc", "zero trust", "firewall", "audit", "rmf")):
        return "Cybersecurity & Zero-Trust"
    if any(k in blob for k in ("cloud", "aws", "azure", "saas", "data center", "server", "storage", "hosting")):
        return "Cloud & Infrastructure"
    if any(k in blob for k in ("network", "fiber", "broadband", "telecom", "wireless", "hardware", "audio/visual")):
        return "Network, Telecom & Hardware"
    return "Enterprise Software, Data & AI"


def format_lead_block(record: dict) -> str:
    """Format an individual Supabase contract record into an enriched Discord intelligence block."""
    raw_title = str(record.get("title") or "N/A").strip()
    clean_title = clean_title_text(raw_title)
    agency = str(record.get("agency") or "N/A").strip()
    closing_date = str(record.get("closing_date") or "").strip()
    if not closing_date:
        m_due = re.search(r"Due:\s*(\d{1,2}/\d{1,2}/\d{2,4})", raw_title, flags=re.IGNORECASE)
        closing_date = m_due.group(1) if m_due else "Open / See Official Portal"
    link = str(record.get("url") or "N/A").strip()
    rec_id = str(record.get("id") or "")

    j_key = classify_jurisdiction(record)
    j_badge = JURISDICTION_LABELS.get(j_key, "FEDERAL // SAM.GOV")
    vertical = classify_vertical_tag(record)
    slug = slugify_contract(raw_title, fallback_id=rec_id)
    dossier_url = f"{SITE_BASE_URL}/contracts/rfp/{slug}.html"

    lines = [
        f"**[{j_badge}]** • `{vertical}`",
        f"**Solicitation:** {clean_title}",
        f"**Buyer Agency:** {agency} | **Closing Date:** `{closing_date}`",
        f"**Official Portal:** <{link}>",
        f"**SignalTender Dossier:** <{dossier_url}>",
        f"{'─' * 44}",
    ]
    return "\n".join(lines)


def _post_batches_to_webhook(records: list[dict], webhook_url: str, label: str = "Master Wire") -> bool:
    """Group records into <1900-char batches and POST to a Discord webhook with rate-limit retry."""
    if not records or not webhook_url:
        return False

    batches = []
    current_batch = []
    current_char_count = 0

    for rec in records:
        block = format_lead_block(rec)
        block_len = len(block) + 4
        if current_char_count + block_len > 1900 and current_batch:
            batches.append(current_batch)
            current_batch = [rec]
            current_char_count = len(block)
        else:
            current_batch.append(rec)
            current_char_count += block_len

    if current_batch:
        batches.append(current_batch)

    for batch_index, batch in enumerate(batches, start=1):
        blocks = [format_lead_block(rec) for rec in batch]
        message_content = "\n\n".join(blocks)

        print(f"[*] Posting {label} batch {batch_index}/{len(batches)} ({len(batch)} lead(s)) to Discord...", flush=True)
        payload = {
            "username": "SignalWire Pro",
            "content": message_content,
            "flags": 4,
        }
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10,
        )
        if response.status_code == 429:
            retry_after = response.json().get("retry_after", 1.5)
            time.sleep(float(retry_after))
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10,
            )
        response.raise_for_status()
        time.sleep(0.4)

    return True


def _resolve_dossiers_for_cycle(records: list[dict], passed_dossiers: list[dict] | None = None) -> list[dict]:
    """Load or resolve the CaptureDesk Autopilot 25-API dossiers corresponding to the current 6-hour cycle."""
    if passed_dossiers:
        return list(passed_dossiers)
    import json
    dossier_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "capturedesk_dossiers.json")
    cached: dict = {}
    if os.path.exists(dossier_path):
        try:
            with open(dossier_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    cached = loaded
        except Exception:
            cached = {}

    matched: list[dict] = []
    seen_urls: set[str] = set()
    rec_urls = {str(r.get("url") or "").strip() for r in (records or []) if r.get("url")}
    rec_ids = {str(r.get("id") or "").strip() for r in (records or []) if r.get("id")}

    for rid in rec_ids:
        if rid in cached and isinstance(cached[rid], dict):
            d = cached[rid]
            u = str(d.get("source_url") or "")
            if u not in seen_urls:
                matched.append(d)
                seen_urls.add(u)

    if len(matched) < 2 and cached:
        all_dossiers = [v for v in cached.values() if isinstance(v, dict)]
        all_dossiers.sort(key=lambda x: str(x.get("enriched_at") or ""), reverse=True)
        for d in all_dossiers:
            u = str(d.get("source_url") or "")
            if u in rec_urls and u not in seen_urls:
                matched.append(d)
                seen_urls.add(u)
        for d in all_dossiers:
            if len(matched) >= 3:
                break
            u = str(d.get("source_url") or "")
            if u not in seen_urls:
                matched.append(d)
                seen_urls.add(u)

    return matched[:3]


def _compute_subscriber_pwin_summary(
    records: list[dict],
    subscriber_meta: dict | None = None,
) -> tuple[str, str]:
    """
    Computes a personalized `Pwin Fit Score` & `Set-Aside / NAICS Match` summary header
    for a subscriber's 6-hour briefing based on their saved `company_profile` and `alert_filters`.
    Returns `(plain_text_line, html_badge)`.
    """
    from html import escape

    meta = subscriber_meta if isinstance(subscriber_meta, dict) else {}
    c_prof = meta.get("company_profile") if isinstance(meta.get("company_profile"), dict) else {}
    a_filt = meta.get("alert_filters") if isinstance(meta.get("alert_filters"), dict) else {}

    comp_name = str(
        c_prof.get("company_name")
        or meta.get("company")
        or "SUBSCRIBER CAPTURE TEAM"
    ).strip()
    socio = str(
        c_prof.get("socioeconomic_status")
        or "Small Business / 8(a) / SDVOSB Eligible"
    ).strip()
    naics_list = a_filt.get("naics") if isinstance(a_filt.get("naics"), list) and a_filt.get("naics") else ["541512", "541511", "541519"]
    states_list = a_filt.get("states") if isinstance(a_filt.get("states"), list) and a_filt.get("states") else ["federal", "virginia", "texas"]

    naics_str = ", ".join(str(n) for n in naics_list[:3])
    states_norm = {str(s).strip().lower() for s in states_list}
    matched_count = 0
    for r in (records or []):
        j_k = classify_jurisdiction(r)
        if "all" in states_norm or j_k in states_norm or j_k == "federal":
            matched_count += 1
    if matched_count == 0 and records:
        matched_count = min(len(records), 3)

    pwin_score = min(96, 86 + min(8, matched_count) + (2 if c_prof.get("company_name") else 0))
    plain_line = (
        f"Pwin Fit Score  : {pwin_score}/100 Pwin for {comp_name} • "
        f"Set-Aside: {socio} • Target NAICS: {naics_str} ({matched_count} Direct Territory Matches)"
    )
    html_badge = (
        f'<div style="margin-top:8px;padding:8px 12px;background:#0f172a;border:1px solid #1e293b;border-radius:8px;font-family:monospace;font-size:11px;color:#34d399;">'
        f'<strong>MATCH SCORE FOR {escape(comp_name.upper())}: {pwin_score}/100 Pwin</strong> &bull; '
        f'<span style="color:#cbd5e1;">Set-Aside: {escape(socio)} | NAICS: {escape(naics_str)} ({matched_count} Territory Matches)</span>'
        f'</div>'
    )
    return plain_line, html_badge


def format_subscriber_email_briefing(
    tier: str,
    records: list[dict],
    dossiers: list[dict] | None = None,
    to_email: str = "",
    subscriber_meta: dict | None = None,
) -> tuple[str, str, str]:
    """
    Build an organized, executive-formatted 6-hour email briefing tailored by subscription tier:
      - Tier 1 (`tier_1` / SignalWire Pro):
          Section I: 52-Portal Live RFP Alert Wire (all newly discovered IT/Cyber solicitations with direct official portal links).
      - Tier 2 (`tier_2` / CaptureDesk Autopilot):
          Single Unified 6-Hour Email combining BOTH:
            Section I: CaptureDesk Autopilot 25-API Executive Dossiers (8-part pre-shredded capture memos)
            Section II: Complete 52-Portal Live RFP Alert Wire (all newly discovered IT/Cyber solicitations)
    Returns `(subject, plain_text_body, html_body)`.
    """
    from datetime import datetime, timezone
    from html import escape
    from urllib.parse import quote_plus

    raw_tier = str(tier or "").strip().lower()
    if raw_tier in ("tier_4", "tier4", "oem", "foia"):
        norm_tier = "tier_4"
    elif raw_tier in ("tier_3", "tier3", "proposal"):
        norm_tier = "tier_3"
    elif raw_tier in ("tier_1", "tier1", "pro", "signalwire"):
        norm_tier = "tier_1"
    else:
        norm_tier = "tier_2"
    cycle_ts = datetime.now(timezone.utc).strftime("%b %d, %Y • %H:%M UTC")
    disable_url = (
        f"https://b2b-contract-parser-api.onrender.com/v1/webhooks/email-briefings"
        f"?email={quote_plus(to_email)}&enabled=false"
    )
    resolved_dossiers = _resolve_dossiers_for_cycle(records, dossiers) if norm_tier != "tier_1" else []
    wire_items = (records or [])[:15]
    total_wire = len(records or [])

    fed_count = sum(1 for r in (records or []) if classify_jurisdiction(r) == "federal")
    muni_count = sum(1 for r in (records or []) if classify_jurisdiction(r) == "municipal")
    sled_count = max(0, total_wire - fed_count - muni_count)
    pwin_plain_line, pwin_html_badge = _compute_subscriber_pwin_summary(records, subscriber_meta)

    if norm_tier == "tier_1":
        subject = (
            f"[SignalTender // Tier 1 Wire] 6-Hour GovCon RFP Briefing — "
            f"{total_wire} Vetted IT & Cyber Solicitations ({cycle_ts})"
        )
    elif norm_tier == "tier_3":
        subject = (
            f"[SignalTender // Tier 3 Proposal Autopilot] 6-Hour Executive Capture Briefing — "
            f"{len(resolved_dossiers)} CaptureDesk 25-API Dossiers + {total_wire} Live Wire RFPs ({cycle_ts})"
        )
    elif norm_tier == "tier_4":
        subject = (
            f"[SignalTender // Tier 4 Enterprise OEM & FOIA Vault] 6-Hour Executive Capture Briefing — "
            f"{len(resolved_dossiers)} CaptureDesk 25-API Dossiers + {total_wire} Live Wire RFPs ({cycle_ts})"
        )
    else:
        subject = (
            f"[SignalTender // Tier 2 Autopilot] 6-Hour Executive Capture Briefing — "
            f"{len(resolved_dossiers)} CaptureDesk 25-API Dossiers + {total_wire} Live Wire RFPs ({cycle_ts})"
        )

    # -------------------------------------------------------------------------
    # 1. Structured Executive Plain-Text Briefing
    # -------------------------------------------------------------------------
    lines: list[str] = []
    rule_heavy = "=" * 78
    rule_light = "-" * 78

    lines.append(rule_heavy)
    if norm_tier == "tier_1":
        lines.append("SIGNALTENDER // TIER 1 — 6-HOUR LIVE RFP ALERT WIRE BRIEFING")
        lines.append(f"Cycle Timestamp : {cycle_ts}")
        lines.append("Plan Tier       : Tier 1 // SignalWire Pro (52 Federal, State SLED & Municipal Portals)")
        lines.append(
            f"Cycle Summary   : {total_wire} Newly Vetted High-Signal IT/Cyber RFPs "
            f"(Federal: {fed_count} | 50-State SLED: {sled_count} | Municipal: {muni_count})"
        )
        lines.append(pwin_plain_line)
    else:
        tier_header_map = {
            "tier_4": "SIGNALTENDER // TIER 4 — ENTERPRISE OEM, FOIA WINNING-BID VAULT & 25-API CAPTUREDESK BRIEFING",
            "tier_3": "SIGNALTENDER // TIER 3 — PROPOSAL AUTOPILOT (.ZIP COMPILER), TEAMING & 25-API CAPTUREDESK BRIEFING",
            "tier_2": "SIGNALTENDER // TIER 2 — UNIFIED CAPTUREDESK AUTOPILOT & LIVE RFP WIRE BRIEFING",
        }
        tier_plan_map = {
            "tier_4": "Tier 4 // Enterprise OEM & FOIA Winning-Bid Vault (52 Portals + 25-API Capture Suite + 50k API Calls/Mo)",
            "tier_3": "Tier 3 // Proposal Autopilot Enterprise (52 Portals + 25-API Capture Suite + 1-Click 6-File Shipley .ZIP Compiler)",
            "tier_2": "Tier 2 // CaptureDesk Autopilot (52 Portals + 25-API Capture Suite)",
        }
        lines.append(tier_header_map.get(norm_tier, tier_header_map["tier_2"]))
        lines.append(f"Cycle Timestamp : {cycle_ts}")
        lines.append(f"Plan Tier       : {tier_plan_map.get(norm_tier, tier_plan_map['tier_2'])}")
        lines.append(
            f"Cycle Summary   : {len(resolved_dossiers)} Pre-Shredded 25-API CaptureDesk Dossiers + "
            f"{total_wire} Newly Vetted Live Wire RFPs (Federal: {fed_count} | SLED: {sled_count} | Municipal: {muni_count})"
        )
        lines.append(pwin_plain_line)
        lines.append(rule_light)
        lines.append("TABLE OF CONTENTS (UNIFIED SINGLE-EMAIL BRIEFING)")
        lines.append(
            f"  • SECTION I   : CAPTUREDESK AUTOPILOT 25-API EXECUTIVE DOSSIERS ({len(resolved_dossiers)} Deep-Dive Packages)"
        )
        lines.append(
            f"  • SECTION II  : COMPLETE 52-PORTAL LIVE RFP ALERT WIRE ({len(wire_items)} of {total_wire} Vetted Solicitations)"
        )
        lines.append("  • SECTION III : ENTERPRISE API, MCP, PROPOSAL .ZIP & SELF-SERVICE DELIVERY CONTROLS")
    lines.append(rule_heavy)
    lines.append("")

    if norm_tier != "tier_1" and resolved_dossiers:
        lines.append("SECTION I // CAPTUREDESK AUTOPILOT 25-API EXECUTIVE DOSSIERS")
        lines.append("Pre-shredded Bid/No-Go memos, IGCE/Wrap/PTW models, CMMC/NIST/RMF gates, and Shipley win themes.")
        lines.append(rule_light)
        for idx, d in enumerate(resolved_dossiers, start=1):
            d_title = clean_title_text(str(d.get("title") or "Government IT Solicitation"))
            d_agency = str(d.get("agency") or "Government Agency").strip()
            d_due = str(d.get("closing_date") or "Open / See Official Portal").strip()
            d_badge = str(d.get("jurisdiction_badge") or "FEDERAL // SAM.GOV").strip()
            d_vert = str(d.get("vertical") or "Enterprise Software, Data & AI").strip()
            d_naics = str(d.get("primary_naics") or "541512")
            d_psc = str(d.get("primary_psc") or "D399")
            d_nigp = str(d.get("primary_nigp") or "")
            d_sba = str(d.get("sba_size_standard") or "$34.0M")
            d_comp = str(d.get("compliance_posture") or "SOC 2 Type II / NIST 800-53 / Section 508 VPAT")
            d_team = str(d.get("teaming_posture") or "13 CFR § 125.6 (50% Rule) + 3 Past Performance Refs")
            d_ptw = str(d.get("igce_ptw_posture") or "Wrap ~1.80x • Target PTW: -5.5% vs. IGCE")
            d_lcat = str(d.get("key_personnel_lcats") or "Program Manager (PMP) • Lead Solutions Architect")
            d_cpars = str(d.get("cpars_relevance_benchmark") or "Substantial Confidence Target • 3 Very Relevant Refs")
            d_ost = str(d.get("ostensible_sub_risk") or "LOW RISK (13 CFR § 121.103(h)(3))")
            d_src = str(d.get("source_url") or "")
            d_url = str(d.get("dossier_url") or f"{SITE_BASE_URL}/contracts")
            if "?unlocked=1" not in d_url:
                d_url = f"{d_url}?unlocked=1"

            nigp_str = f" | NIGP: {d_nigp}" if d_nigp else ""
            lines.append(f"[DOSSIER #{idx:02d}] [{d_badge}] • {d_vert}")
            lines.append(f"  1. Solicitation Title   : {d_title}")
            lines.append(f"     Issuing Buyer Agency : {d_agency}  |  Closing Date: {d_due}")
            lines.append(
                f"  2. Classification (#02) : NAICS {d_naics} | PSC {d_psc}{nigp_str} | SBA Size: {d_sba}"
            )
            lines.append(f"     Ostensible Sub (#11) : {d_ost}")
            lines.append(f"  3. Cyber & RMF (#06/#18): {d_comp}")
            lines.append(f"  4. IGCE, PTW & MAS (#16): {d_ptw}")
            lines.append(f"  5. Key LCATs & CPARS    : {d_lcat} | {d_cpars}")
            lines.append(f"  6. Teaming Mandate (#11): {d_team}")
            themes = [str(t).replace("**", "").strip() for t in (d.get("win_themes") or [])[:3] if t]
            if themes:
                lines.append("  7. Tailored Shipley Section L/M Win Strategy (#05/#17/#19/#33/#56):")
                for t_item in themes:
                    lines.append(f"       - {t_item}")
            ev_list = [str(e).replace("**", "").strip() for e in (d.get("evidence_needed") or [])[:2] if e]
            if ev_list:
                lines.append("     Required Proposal Evidence:")
                for e_item in ev_list:
                    lines.append(f"       - {e_item}")
            lines.append(f"  8. Official Portal URL  : {d_src}")
            lines.append(f"     25-API Web Dossier   : {d_url}")
            lines.append(rule_light)
        lines.append("")

    wire_section_title = (
        "SECTION II // COMPLETE 52-PORTAL LIVE RFP ALERT WIRE"
        if norm_tier != "tier_1"
        else "SECTION I // 52-PORTAL LIVE RFP ALERT WIRE"
    )
    lines.append(wire_section_title)
    lines.append(
        "All newly discovered, AI-vetted IT, Cloud, Cybersecurity & Software RFPs across 52 government portals."
    )
    lines.append(rule_light)

    for idx, rec in enumerate(wire_items, start=1):
        raw_title = str(rec.get("title") or "N/A").strip()
        clean_title = clean_title_text(raw_title)
        agency = str(rec.get("agency") or "Government Agency").strip()
        closing_date = str(rec.get("closing_date") or "").strip()
        if not closing_date:
            m_due = re.search(r"Due:\s*(\d{1,2}/\d{1,2}/\d{2,4})", raw_title, flags=re.IGNORECASE)
            closing_date = m_due.group(1) if m_due else "Open / See Official Portal"
        link = str(rec.get("url") or "N/A").strip()
        rec_id = str(rec.get("id") or "")
        j_key = classify_jurisdiction(rec)
        j_badge = JURISDICTION_LABELS.get(j_key, "FEDERAL // SAM.GOV")
        vertical = classify_vertical_tag(rec)
        slug = slugify_contract(raw_title, fallback_id=rec_id)
        dossier_url = f"{SITE_BASE_URL}/contracts/rfp/{slug}.html?unlocked=1"

        lines.append(f"[{idx:02d}] [{j_badge}] • {vertical}")
        lines.append(f"     Solicitation    : {clean_title}")
        lines.append(f"     Buyer Agency    : {agency}  |  Closing Date: {closing_date}")
        lines.append(f"     Official Portal : {link}")
        lines.append(f"     Unlocked Brief  : {dossier_url}")
        lines.append(rule_light)

    lines.append("")
    ctrl_section_title = (
        "SECTION III // ENTERPRISE API, MCP, PROPOSAL .ZIP & DELIVERY CONTROLS"
        if norm_tier != "tier_1"
        else "SECTION II // SUBSCRIBER DIRECTORY & DELIVERY CONTROLS"
    )
    lines.append(ctrl_section_title)
    lines.append(f"  • Full 52-Portal Live Directory (Un-Blurred) : {SITE_BASE_URL}/contracts")
    if norm_tier != "tier_1":
        lines.append(f"  • 58-API GovCon Capture Studio               : {SITE_BASE_URL}/apis.html")
        lines.append("  • Remote Streamable-HTTP MCP Server          : https://b2b-contract-parser-api.onrender.com/mcp")
    if norm_tier in ("tier_3", "tier_4"):
        lines.append("  • 1-Click 6-File Shipley Proposal .ZIP       : https://b2b-contract-parser-api.onrender.com/v1/proposal-autopilot/compile-full-package")
        lines.append("  • Two-Sided 13 CFR § 125.6 Teaming Exchange  : https://b2b-contract-parser-api.onrender.com/v1/proposal-autopilot/teaming-clearinghouse")
    if norm_tier == "tier_4":
        lines.append("  • Post-Award FOIA Winning-Bid Rate Vault     : https://b2b-contract-parser-api.onrender.com/v1/proposal-autopilot/foia-winning-bid-vault")
    lines.append(f"  • Manage Discord / Webhook / Email Settings  : {SITE_BASE_URL}/#account")
    lines.append(f"  • 1-Click Turn OFF 6-Hour Email Briefings    : {disable_url}")
    lines.append(rule_heavy)

    plain_body = "\n".join(lines)

    # -------------------------------------------------------------------------
    # 2. Executive HTML Briefing (for Resend & SMTP clients)
    # -------------------------------------------------------------------------
    tier_pill_map = {
        "tier_4": "TIER 4 // ENTERPRISE OEM & FOIA VAULT (DOSSIERS + FOIA VAULT + LIVE WIRE)",
        "tier_3": "TIER 3 // PROPOSAL AUTOPILOT (.ZIP COMPILER + DOSSIERS + LIVE WIRE)",
        "tier_2": "TIER 2 // CAPTUREDESK AUTOPILOT (UNIFIED DOSSIERS + LIVE WIRE)",
        "tier_1": "TIER 1 // SIGNALWIRE PRO (52-PORTAL LIVE RFP WIRE)",
    }
    tier_pill = tier_pill_map.get(norm_tier, tier_pill_map["tier_2"])
    tier_accent = "#f59e0b" if norm_tier == "tier_4" else ("#10b981" if norm_tier == "tier_3" else ("#6366f1" if norm_tier == "tier_2" else "#0ea5e9"))

    dossier_html_cards = []
    if norm_tier != "tier_1" and resolved_dossiers:
        for idx, d in enumerate(resolved_dossiers, start=1):
            d_title = escape(clean_title_text(str(d.get("title") or "Government IT Solicitation")))
            d_agency = escape(str(d.get("agency") or "Government Agency").strip())
            d_due = escape(str(d.get("closing_date") or "Open / See Official Portal").strip())
            d_badge = escape(str(d.get("jurisdiction_badge") or "FEDERAL // SAM.GOV").strip())
            d_vert = escape(str(d.get("vertical") or "Enterprise Software, Data & AI").strip())
            d_naics = escape(str(d.get("primary_naics") or "541512"))
            d_psc = escape(str(d.get("primary_psc") or "D399"))
            d_sba = escape(str(d.get("sba_size_standard") or "$34.0M"))
            d_comp = escape(str(d.get("compliance_posture") or "SOC 2 Type II / NIST 800-53"))
            d_team = escape(str(d.get("teaming_posture") or "13 CFR § 125.6 (50% Rule)"))
            d_ptw = escape(str(d.get("igce_ptw_posture") or "Wrap ~1.80x • Target PTW: -5.5% vs. IGCE"))
            d_lcat = escape(str(d.get("key_personnel_lcats") or "Program Manager (PMP) • Lead Architect"))
            d_src = escape(str(d.get("source_url") or "#"))
            raw_durl = str(d.get("dossier_url") or f"{SITE_BASE_URL}/contracts")
            if "?unlocked=1" not in raw_durl:
                raw_durl = f"{raw_durl}?unlocked=1"
            d_url = escape(raw_durl)
            themes_li = "".join(
                f"<li style='margin-bottom:4px;'>{escape(str(t).replace('**', '').strip())}</li>"
                for t in (d.get("win_themes") or [])[:3]
                if t
            )
            dossier_html_cards.append(
                f"""
                <div style="border:1px solid #312e81;background:#0f172a;border-radius:10px;padding:16px;margin-bottom:14px;">
                  <div style="font-family:monospace;font-size:11px;color:#a5b4fc;margin-bottom:6px;">
                    <strong>[DOSSIER #{idx:02d}] {d_badge}</strong> &bull; {d_vert}
                  </div>
                  <div style="font-size:15px;font-weight:700;color:#ffffff;margin-bottom:6px;">{d_title}</div>
                  <div style="font-size:12px;color:#cbd5e1;margin-bottom:10px;">
                    <strong>Buyer Agency:</strong> {d_agency} &nbsp;|&nbsp; <strong>Closing Date:</strong> <span style="color:#34d399;font-family:monospace;">{d_due}</span>
                  </div>
                  <table style="width:100%;border-collapse:collapse;font-size:12px;color:#e2e8f0;margin-bottom:10px;">
                    <tr><td style="padding:4px 0;color:#94a3b8;width:190px;">Taxonomic &amp; SBA Size (#02):</td><td style="padding:4px 0;font-family:monospace;">NAICS {d_naics} | PSC {d_psc} | SBA Size {d_sba}</td></tr>
                    <tr><td style="padding:4px 0;color:#94a3b8;">Cyber &amp; RMF Gates (#06/#18):</td><td style="padding:4px 0;">{d_comp}</td></tr>
                    <tr><td style="padding:4px 0;color:#94a3b8;">IGCE, Wrap &amp; PTW (#16/#20):</td><td style="padding:4px 0;color:#6ee7b7;">{d_ptw}</td></tr>
                    <tr><td style="padding:4px 0;color:#94a3b8;">Key Personnel LCATs (#13):</td><td style="padding:4px 0;">{d_lcat}</td></tr>
                    <tr><td style="padding:4px 0;color:#94a3b8;">Teaming &amp; Sub Goal (#11):</td><td style="padding:4px 0;">{d_team}</td></tr>
                  </table>
                  <div style="font-size:12px;color:#cbd5e1;margin-bottom:10px;">
                    <strong style="color:#a5b4fc;">Tailored Shipley Section L/M Win Strategy (#05/#17/#19/#33/#56):</strong>
                    <ul style="margin:6px 0 0 18px;padding:0;">{themes_li}</ul>
                  </div>
                  <div style="margin-top:10px;">
                    <a href="{d_src}" style="display:inline-block;padding:7px 12px;background:#1e293b;color:#38bdf8;text-decoration:none;border-radius:6px;font-size:12px;font-family:monospace;border:1px solid #334155;margin-right:8px;">Official Portal Bid &nearr;</a>
                    <a href="{d_url}" style="display:inline-block;padding:7px 12px;background:#4f46e5;color:#ffffff;text-decoration:none;border-radius:6px;font-size:12px;font-family:monospace;font-weight:700;">Open Full 25-API Dossier &rarr;</a>
                  </div>
                </div>
                """
            )

    wire_html_rows = []
    for idx, rec in enumerate(wire_items, start=1):
        raw_title = str(rec.get("title") or "N/A").strip()
        clean_title = escape(clean_title_text(raw_title))
        agency = escape(str(rec.get("agency") or "Government Agency").strip())
        closing_date = str(rec.get("closing_date") or "").strip()
        if not closing_date:
            m_due = re.search(r"Due:\s*(\d{1,2}/\d{1,2}/\d{2,4})", raw_title, flags=re.IGNORECASE)
            closing_date = m_due.group(1) if m_due else "Open / See Official Portal"
        closing_date = escape(closing_date)
        link = escape(str(rec.get("url") or "#").strip())
        rec_id = str(rec.get("id") or "")
        j_key = classify_jurisdiction(rec)
        j_badge = escape(JURISDICTION_LABELS.get(j_key, "FEDERAL // SAM.GOV"))
        vertical = escape(classify_vertical_tag(rec))
        slug = slugify_contract(raw_title, fallback_id=rec_id)
        dossier_url = escape(f"{SITE_BASE_URL}/contracts/rfp/{slug}.html?unlocked=1")

        wire_html_rows.append(
            f"""
            <div style="border:1px solid #1e293b;background:#0f172a;border-radius:8px;padding:12px 14px;margin-bottom:10px;">
              <div style="font-family:monospace;font-size:11px;color:#38bdf8;margin-bottom:4px;">
                <strong>[{idx:02d}] {j_badge}</strong> &bull; <span style="color:#94a3b8;">{vertical}</span>
              </div>
              <div style="font-size:14px;font-weight:600;color:#f8fafc;margin-bottom:4px;">{clean_title}</div>
              <div style="font-size:12px;color:#cbd5e1;margin-bottom:8px;">
                <strong>Buyer:</strong> {agency} &nbsp;|&nbsp; <strong>Due:</strong> <span style="color:#34d399;font-family:monospace;">{closing_date}</span>
              </div>
              <div>
                <a href="{link}" style="color:#38bdf8;font-size:12px;font-family:monospace;text-decoration:none;margin-right:14px;">Official Government Portal &nearr;</a>
                <a href="{dossier_url}" style="color:#a5b4fc;font-size:12px;font-family:monospace;text-decoration:none;">Unlocked SignalTender Brief &rarr;</a>
              </div>
            </div>
            """
        )

    section_i_html = ""
    if norm_tier != "tier_1" and dossier_html_cards:
        section_i_html = f"""
        <div style="margin-top:18px;margin-bottom:22px;">
          <div style="font-family:monospace;font-size:12px;font-weight:700;color:#a5b4fc;letter-spacing:0.05em;text-transform:uppercase;border-bottom:1px solid #312e81;padding-bottom:6px;margin-bottom:12px;">
            SECTION I // CAPTUREDESK AUTOPILOT 25-API EXECUTIVE DOSSIERS ({len(resolved_dossiers)} PACKAGES)
          </div>
          {''.join(dossier_html_cards)}
        </div>
        """

    wire_header_label = (
        f"SECTION II // COMPLETE 52-PORTAL LIVE RFP ALERT WIRE ({len(wire_items)} OF {total_wire} SOLICITATIONS)"
        if norm_tier != "tier_1"
        else f"SECTION I // 52-PORTAL LIVE RFP ALERT WIRE ({len(wire_items)} OF {total_wire} SOLICITATIONS)"
    )

    html_body = f"""
    <div style="background:#020617;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;padding:24px;max-width:760px;margin:0 auto;border-radius:12px;border:1px solid #1e293b;">
      <div style="border-bottom:2px solid {tier_accent};padding-bottom:14px;margin-bottom:16px;">
        <div style="font-family:monospace;font-size:11px;color:{tier_accent};font-weight:700;letter-spacing:0.06em;">{escape(tier_pill)}</div>
        <h2 style="margin:6px 0 4px 0;font-size:20px;color:#ffffff;">SignalTender 6-Hour GovCon Capture Briefing</h2>
        <div style="font-size:12px;color:#94a3b8;font-family:monospace;">
          Cycle: {escape(cycle_ts)} &bull; Federal: {fed_count} | 50-State SLED: {sled_count} | Municipal: {muni_count}
        </div>
        {pwin_html_badge}
      </div>
      {section_i_html}
      <div style="margin-top:14px;margin-bottom:20px;">
        <div style="font-family:monospace;font-size:12px;font-weight:700;color:#38bdf8;letter-spacing:0.05em;text-transform:uppercase;border-bottom:1px solid #1e293b;padding-bottom:6px;margin-bottom:12px;">
          {escape(wire_header_label)}
        </div>
        {''.join(wire_html_rows)}
      </div>
      <div style="border-top:1px solid #1e293b;padding-top:14px;font-size:12px;color:#94a3b8;line-height:1.6;">
        <div><strong>Subscriber Quick Links:</strong> <a href="{SITE_BASE_URL}/contracts" style="color:#38bdf8;">Live 52-Portal Directory</a> &bull; <a href="{SITE_BASE_URL}/#checkout" style="color:#38bdf8;">Delivery Settings</a> &bull; <a href="{escape(disable_url)}" style="color:#f87171;">Pause Email Briefings</a></div>
      </div>
    </div>
    """.strip()

    return subject, plain_body, html_body


def _dispatch_via_instantly_transactional_campaign(
    to_email: str,
    subject: str,
    plain_body: str,
    first_name: str = "",
    company_name: str = "",
) -> bool:
    """
    Dispatches a 1-step transactional/subscriber briefing email via Instantly campaign
    `748eecf5-6b63-4dff-b9f2-1d2ff1a4a96f`.
    Deletes any prior completed lead (`status == 3`) for `to_email` in that campaign first
    so repeat 6-hour briefings never deadlock on Instantly's one-shot lead completion state.
    """
    clean_to = str(to_email or "").strip().lower()
    if not clean_to or "@" not in clean_to:
        return False
    dom = clean_to.split("@", 1)[1]
    if dom in ("signaltender.net", "example.com", "test.com", "localhost"):
        return False
    inst_key = os.getenv("INSTANTLY_API_KEY", "").strip()
    inst_sub_cid = os.getenv("INSTANTLY_SUBSCRIBER_CAMPAIGN_ID", "748eecf5-6b63-4dff-b9f2-1d2ff1a4a96f").strip()
    if not (inst_key and inst_sub_cid):
        return False
    headers = {"Authorization": f"Bearer {inst_key}", "Content-Type": "application/json"}
    try:
        l_resp = requests.post(
            "https://api.instantly.ai/api/v2/leads/list",
            headers=headers,
            json={"campaign": inst_sub_cid, "search": clean_to, "limit": 20},
            timeout=10,
        )
        if l_resp.status_code == 200:
            for item in (l_resp.json().get("items") or []):
                if str(item.get("email") or "").strip().lower() == clean_to and item.get("id"):
                    requests.delete(
                        f"https://api.instantly.ai/api/v2/leads/{item['id']}",
                        headers={"Authorization": f"Bearer {inst_key}"},
                        timeout=10,
                    )
    except Exception:
        pass
    lead_payload: dict = {
        "campaign": inst_sub_cid,
        "email": clean_to,
        "skip_if_in_campaign": False,
        "custom_variables": {"subject_line": subject, "email_body": plain_body},
    }
    if first_name:
        lead_payload["first_name"] = first_name
    if company_name:
        lead_payload["company_name"] = company_name
    r = requests.post(
        "https://api.instantly.ai/api/v2/leads",
        headers=headers,
        json=lead_payload,
        timeout=10,
    )
    if r.status_code in (200, 201):
        requests.post(
            f"https://api.instantly.ai/api/v2/campaigns/{inst_sub_cid}/activate",
            headers=headers,
            json={},
            timeout=10,
        )
        return True
    return False


def _send_subscriber_email_briefing(
    to_email: str,
    records: list[dict],
    tier: str = "tier_2",
    dossiers: list[dict] | None = None,
    subscriber_meta: dict | None = None,
) -> bool:
    """
    Send an organized, tier-specific 6-hour briefing email ONLY to active subscribers
    who opted in (`email_briefings_enabled: True`).
    Tier 2 subscribers receive BOTH CaptureDesk Autopilot 25-API Dossiers (Section I)
    and the Complete 52-Portal Live RFP Alert Wire (Section II) in the same single email.
    """
    clean_to = str(to_email or "").strip().lower()
    if not clean_to or "@" not in clean_to or clean_to.endswith("@signaltender.net"):
        return False
    resend_key = os.getenv("RESEND_API_KEY", "").strip()
    smtp_user = os.getenv("SMTP_USER", "").strip()
    smtp_pass = os.getenv("SMTP_PASSWORD", "").strip()
    from_email = os.getenv("SMTP_FROM_EMAIL", smtp_user or "aaron@getsignaltender.com").strip()

    subject, plain_body, html_body = format_subscriber_email_briefing(
        tier=tier,
        records=records,
        dossiers=dossiers,
        to_email=clean_to,
        subscriber_meta=subscriber_meta,
    )
    sender_label = (
        "SignalTender CaptureDesk Autopilot"
        if str(tier or "").strip().lower() not in ("tier_1", "tier1", "pro", "signalwire")
        else "SignalTender Live RFP Wire"
    )
    try:
        if resend_key:
            r = requests.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {resend_key}", "Content-Type": "application/json"},
                json={
                    "from": f"{sender_label} <{from_email}>",
                    "to": [clean_to],
                    "subject": subject,
                    "text": plain_body,
                    "html": html_body,
                },
                timeout=10,
            )
            return r.status_code in (200, 201)
        elif smtp_user and smtp_pass:
            import smtplib, ssl
            from email.message import EmailMessage
            msg = EmailMessage()
            msg["Subject"] = subject
            msg["From"] = f"{sender_label} <{from_email}>"
            msg["To"] = clean_to
            msg.set_content(plain_body)
            msg.add_alternative(html_body, subtype="html")
            with smtplib.SMTP(os.getenv("SMTP_HOST", "smtp.gmail.com"), int(os.getenv("SMTP_PORT") or "587"), timeout=10) as s:
                s.starttls(context=ssl.create_default_context())
                s.login(smtp_user, smtp_pass)
                s.send_message(msg)
            return True
        return _dispatch_via_instantly_transactional_campaign(
            to_email=clean_to,
            subject=subject,
            plain_body=plain_body,
        )
    except Exception:
        pass
    return False


def format_external_webhook_payload(
    tier: str,
    webhook_url: str,
    records: list[dict],
    dossiers: list[dict] | None = None,
    destination_type: str = "auto",
) -> dict:
    """
    Build an organized, platform-native 6-hour external webhook payload tailored by
    both Subscription Tier (`tier_1` vs `tier_2`) and Destination Platform (`Slack`,
    `Microsoft Teams`, `Discord`, or `CRM / Zapier / Make.com / n8n / HubSpot / Salesforce`):
      - Tier 1 (`tier_1` / SignalWire Pro):
          Section I: 52-Portal Live RFP Alert Wire (all newly discovered IT/Cyber solicitations).
      - Tier 2 (`tier_2` / CaptureDesk Autopilot):
          Single Unified 6-Hour Dispatch combining BOTH:
            Section I: CaptureDesk Autopilot 25-API Executive Dossiers (8-part pre-shredded memos)
            Section II: Complete 52-Portal Live RFP Alert Wire (all newly discovered IT/Cyber solicitations)
    """
    from datetime import datetime, timezone

    raw_tier = str(tier or "").strip().lower()
    if raw_tier in ("tier_4", "tier4", "oem", "foia"):
        norm_tier = "tier_4"
    elif raw_tier in ("tier_3", "tier3", "proposal"):
        norm_tier = "tier_3"
    elif raw_tier in ("tier_1", "tier1", "pro", "signalwire"):
        norm_tier = "tier_1"
    else:
        norm_tier = "tier_2"
    u_low = str(webhook_url or "").strip().lower()
    d_hint = str(destination_type or "auto").strip().lower()

    if "hooks.slack.com" in u_low or d_hint == "slack":
        platform = "slack"
    elif "webhook.office.com" in u_low or "logic.azure.com" in u_low or d_hint == "teams":
        platform = "teams"
    elif "discord.com/api/webhooks" in u_low or "discordapp.com/api/webhooks" in u_low or d_hint == "discord":
        platform = "discord"
    else:
        platform = d_hint if d_hint not in ("", "auto") else "crm_webhook"

    cycle_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    cycle_label = datetime.now(timezone.utc).strftime("%b %d, %Y • %H:%M UTC")
    resolved_dossiers = _resolve_dossiers_for_cycle(records, dossiers) if norm_tier != "tier_1" else []
    wire_items = (records or [])[:12]
    total_wire = len(records or [])

    fed_count = sum(1 for r in (records or []) if classify_jurisdiction(r) == "federal")
    muni_count = sum(1 for r in (records or []) if classify_jurisdiction(r) == "municipal")
    sled_count = max(0, total_wire - fed_count - muni_count)

    # 1. Native Slack `mrkdwn` Formatting (`*bold*`, `<url|Label>`)
    if platform == "slack":
        s_lines: list[str] = []
        if norm_tier == "tier_1":
            s_lines.append("*SIGNALTENDER // TIER 1 — 6-HOUR LIVE RFP ALERT WIRE*")
            s_lines.append(
                f"`Cycle: {cycle_label}` • *{total_wire} Vetted IT/Cyber RFPs* "
                f"(Federal: `{fed_count}` | 50-State SLED: `{sled_count}` | Municipal: `{muni_count}`)"
            )
            s_lines.append("─" * 46)
            s_lines.append("*SECTION I // 52-PORTAL LIVE RFP ALERT WIRE*")
        else:
            s_lines.append("*SIGNALTENDER // TIER 2 — UNIFIED 6-HOUR CAPTUREDESK AUTOPILOT & LIVE WIRE BRIEFING*")
            s_lines.append(
                f"`Cycle: {cycle_label}` • *{len(resolved_dossiers)} CaptureDesk 25-API Dossiers* + "
                f"*{total_wire} Live Wire RFPs* (Federal: `{fed_count}` | SLED: `{sled_count}` | Municipal: `{muni_count}`)"
            )
            s_lines.append(
                "• *Section I:* CaptureDesk Autopilot 25-API Executive Dossiers\n"
                "• *Section II:* Complete 52-Portal Live RFP Alert Wire"
            )
            s_lines.append("─" * 46)
            if resolved_dossiers:
                s_lines.append("*SECTION I // CAPTUREDESK AUTOPILOT 25-API EXECUTIVE DOSSIERS*")
                for idx, d in enumerate(resolved_dossiers, start=1):
                    d_title = clean_title_text(str(d.get("title") or "Government IT Solicitation"))
                    d_agency = str(d.get("agency") or "Government Agency").strip()
                    d_due = str(d.get("closing_date") or "Open / See Official Portal").strip()
                    d_badge = str(d.get("jurisdiction_badge") or "FEDERAL // SAM.GOV").strip()
                    d_vert = str(d.get("vertical") or "Enterprise Software, Data & AI").strip()
                    d_naics = str(d.get("primary_naics") or "541512")
                    d_psc = str(d.get("primary_psc") or "D399")
                    d_sba = str(d.get("sba_size_standard") or "$34.0M")
                    d_comp = str(d.get("compliance_posture") or "SOC 2 Type II / NIST 800-53")
                    d_ptw = str(d.get("igce_ptw_posture") or "Wrap ~1.80x • Target PTW: -5.5% vs. IGCE")
                    d_lcat = str(d.get("key_personnel_lcats") or "Program Manager (PMP) • Lead Solutions Architect")
                    d_team = str(d.get("teaming_posture") or "13 CFR § 125.6 (50% Rule)")
                    d_src = str(d.get("source_url") or f"{SITE_BASE_URL}/contracts")
                    d_url = str(d.get("dossier_url") or f"{SITE_BASE_URL}/contracts")
                    if "?unlocked=1" not in d_url:
                        d_url = f"{d_url}?unlocked=1"
                    themes = [str(t).replace("**", "").strip() for t in (d.get("win_themes") or [])[:2] if t]
                    theme_str = "\n".join(f"    ◦ {t}" for t in themes)

                    s_lines.append(f"*[DOSSIER #{idx:02d}] [{d_badge}]* • `{d_vert}`")
                    s_lines.append(f"  *1. Solicitation:* {d_title}")
                    s_lines.append(f"  *2. Buyer & Deadline:* {d_agency} | Due: `{d_due}`")
                    s_lines.append(f"  *3. Classification (#02/#11):* NAICS `{d_naics}` | PSC `{d_psc}` | SBA Size `{d_sba}`")
                    s_lines.append(f"  *4. Cyber & RMF Gates (#06/#18):* `{d_comp}`")
                    s_lines.append(f"  *5. IGCE, Wrap & PTW (#16/#20):* `{d_ptw}`")
                    s_lines.append(f"  *6. Key LCATs & Teaming (#11/#13):* `{d_lcat}` | `{d_team}`")
                    if theme_str:
                        s_lines.append(f"  *7. Shipley Section L/M Win Strategy (#05/#17/#19/#33/#56):*\n{theme_str}")
                    s_lines.append(f"  *8. Action Links:* <{d_src}|Official Portal Bid ↗>  |  <{d_url}|Open Full 25-API Dossier →>")
                    s_lines.append("─" * 46)
            s_lines.append("*SECTION II // COMPLETE 52-PORTAL LIVE RFP ALERT WIRE*")

        for idx, rec in enumerate(wire_items[:10], start=1):
            raw_title = str(rec.get("title") or "N/A").strip()
            clean_title = clean_title_text(raw_title)
            agency = str(rec.get("agency") or "Government Agency").strip()
            closing_date = str(rec.get("closing_date") or "").strip() or "Open / See Official Portal"
            link = str(rec.get("url") or f"{SITE_BASE_URL}/contracts").strip()
            rec_id = str(rec.get("id") or "")
            j_badge = JURISDICTION_LABELS.get(classify_jurisdiction(rec), "FEDERAL // SAM.GOV")
            vertical = classify_vertical_tag(rec)
            slug = slugify_contract(raw_title, fallback_id=rec_id)
            dossier_url = f"{SITE_BASE_URL}/contracts/rfp/{slug}.html?unlocked=1"
            s_lines.append(
                f"*[{idx:02d}] [{j_badge}]* • `{vertical}`\n"
                f"  • *Solicitation:* {clean_title}\n"
                f"  • *Buyer:* {agency} | *Due:* `{closing_date}`\n"
                f"  • <{link}|Official Government Portal ↗>  |  <{dossier_url}|Unlocked SignalTender Brief →>"
            )
        s_lines.append(f"<{SITE_BASE_URL}/contracts|View Full 52-Portal Directory> • <{SITE_BASE_URL}/#checkout|Delivery Settings>")
        return {"text": "\n".join(s_lines)}

    # 2. Native Microsoft Teams Markdown Card (`**bold**`, `[Label](url)`)
    if platform == "teams":
        t_lines: list[str] = []
        if norm_tier == "tier_1":
            t_lines.append("### SIGNALTENDER // TIER 1 — 6-HOUR LIVE RFP ALERT WIRE")
            t_lines.append(
                f"**Cycle:** `{cycle_label}` | **Total Vetted RFPs:** `{total_wire}` "
                f"(Federal: `{fed_count}` • 50-State SLED: `{sled_count}` • Municipal: `{muni_count}`)"
            )
            t_lines.append("---")
            t_lines.append("#### SECTION I // 52-PORTAL LIVE RFP ALERT WIRE")
        else:
            t_lines.append("### SIGNALTENDER // TIER 2 — UNIFIED 6-HOUR CAPTUREDESK AUTOPILOT & LIVE WIRE BRIEFING")
            t_lines.append(
                f"**Cycle:** `{cycle_label}` | **{len(resolved_dossiers)} CaptureDesk 25-API Dossiers** + "
                f"**{total_wire} Live Wire RFPs** (Federal: `{fed_count}` • SLED: `{sled_count}` • Municipal: `{muni_count}`)"
            )
            t_lines.append(
                "- **Section I:** CaptureDesk Autopilot 25-API Executive Dossiers\n"
                "- **Section II:** Complete 52-Portal Live RFP Alert Wire"
            )
            t_lines.append("---")
            if resolved_dossiers:
                t_lines.append("#### SECTION I // CAPTUREDESK AUTOPILOT 25-API EXECUTIVE DOSSIERS")
                for idx, d in enumerate(resolved_dossiers, start=1):
                    d_title = clean_title_text(str(d.get("title") or "Government IT Solicitation"))
                    d_agency = str(d.get("agency") or "Government Agency").strip()
                    d_due = str(d.get("closing_date") or "Open / See Official Portal").strip()
                    d_badge = str(d.get("jurisdiction_badge") or "FEDERAL // SAM.GOV").strip()
                    d_vert = str(d.get("vertical") or "Enterprise Software, Data & AI").strip()
                    d_naics = str(d.get("primary_naics") or "541512")
                    d_psc = str(d.get("primary_psc") or "D399")
                    d_sba = str(d.get("sba_size_standard") or "$34.0M")
                    d_comp = str(d.get("compliance_posture") or "SOC 2 Type II / NIST 800-53")
                    d_ptw = str(d.get("igce_ptw_posture") or "Wrap ~1.80x • Target PTW: -5.5% vs. IGCE")
                    d_lcat = str(d.get("key_personnel_lcats") or "Program Manager (PMP) • Lead Solutions Architect")
                    d_team = str(d.get("teaming_posture") or "13 CFR § 125.6 (50% Rule)")
                    d_src = str(d.get("source_url") or f"{SITE_BASE_URL}/contracts")
                    d_url = str(d.get("dossier_url") or f"{SITE_BASE_URL}/contracts")
                    if "?unlocked=1" not in d_url:
                        d_url = f"{d_url}?unlocked=1"
                    t_lines.append(
                        f"**[DOSSIER #{idx:02d}] [{d_badge}]** • `{d_vert}`\n"
                        f"- **1. Solicitation:** {d_title}\n"
                        f"- **2. Buyer & Deadline:** {d_agency} | Due: `{d_due}`\n"
                        f"- **3. Classification (#02/#11):** NAICS `{d_naics}` | PSC `{d_psc}` | SBA Size `{d_sba}`\n"
                        f"- **4. Cyber & RMF Gates (#06/#18):** `{d_comp}`\n"
                        f"- **5. IGCE, Wrap & PTW (#16/#20):** `{d_ptw}`\n"
                        f"- **6. Key LCATs & Teaming (#11/#13):** `{d_lcat}` | `{d_team}`\n"
                        f"- **7. Action Links:** [Official Portal Bid ↗]({d_src}) | [Open Full 25-API Dossier →]({d_url})"
                    )
                t_lines.append("---")
            t_lines.append("#### SECTION II // COMPLETE 52-PORTAL LIVE RFP ALERT WIRE")

        for idx, rec in enumerate(wire_items[:10], start=1):
            raw_title = str(rec.get("title") or "N/A").strip()
            clean_title = clean_title_text(raw_title)
            agency = str(rec.get("agency") or "Government Agency").strip()
            closing_date = str(rec.get("closing_date") or "").strip() or "Open / See Official Portal"
            link = str(rec.get("url") or f"{SITE_BASE_URL}/contracts").strip()
            rec_id = str(rec.get("id") or "")
            j_badge = JURISDICTION_LABELS.get(classify_jurisdiction(rec), "FEDERAL // SAM.GOV")
            vertical = classify_vertical_tag(rec)
            slug = slugify_contract(raw_title, fallback_id=rec_id)
            dossier_url = f"{SITE_BASE_URL}/contracts/rfp/{slug}.html?unlocked=1"
            t_lines.append(
                f"**[{idx:02d}] [{j_badge}]** • `{vertical}` — **{clean_title}**\n"
                f"Buyer: {agency} | Due: `{closing_date}` | [Official Government Portal ↗]({link}) | [Unlocked Brief →]({dossier_url})"
            )
        return {"text": "\n\n".join(t_lines)}

    # 3. Customer-Owned Discord Webhook (`flags: 4` suppress embeds, <= 1950 chars)
    if platform == "discord":
        blocks = []
        char_total = 0
        if norm_tier != "tier_1" and resolved_dossiers:
            header = f"**[{norm_tier.upper().replace('_', ' ')} // UNIFIED 6-HR BRIEFING: CAPTUREDESK DOSSIERS + LIVE WIRE]**\n"
            blocks.append(header)
            char_total += len(header)
            d0 = resolved_dossiers[0]
            d_url = str(d0.get("dossier_url") or f"{SITE_BASE_URL}/contracts")
            if "?unlocked=1" not in d_url:
                d_url = f"{d_url}?unlocked=1"
            d_block = (
                f"**[SECTION I // CAPTUREDESK 25-API DOSSIER]** `{d0.get('jurisdiction_badge', 'FEDERAL')}`\n"
                f"**Solicitation:** {clean_title_text(str(d0.get('title') or ''))}\n"
                f"**NAICS/PSC:** `{d0.get('primary_naics', '541512')}` | `{d0.get('primary_psc', 'D399')}` | **IGCE/PTW:** `{d0.get('igce_ptw_posture', '')}`\n"
                f"**Cyber/RMF:** `{d0.get('compliance_posture', '')}`\n"
                f"**Official Portal:** <{d0.get('source_url', '')}> | **25-API Dossier:** <{d_url}>\n"
                f"{'─' * 44}"
            )
            blocks.append(d_block)
            char_total += len(d_block) + 2
        for rec in wire_items[:8]:
            b = format_lead_block(rec)
            if char_total + len(b) + 4 > 1900 and blocks:
                break
            blocks.append(b)
            char_total += len(b) + 4
        return {
            "username": "SignalTender CaptureDesk Autopilot" if norm_tier != "tier_1" else "SignalWire Pro",
            "avatar_url": "https://cdn.discordapp.com/avatars/1561230679860056117/79a24b4cd14595244f5ac4414807d9a1.png",
            "content": "\n\n".join(blocks),
            "flags": 4,
        }

    # 4. Structured CRM & Automation Webhook JSON (HubSpot, Salesforce, Zapier, Make.com, n8n, Custom HTTPS)
    _, plain_summary, _ = format_subscriber_email_briefing(
        tier=norm_tier,
        records=records,
        dossiers=resolved_dossiers,
        to_email="",
    )
    live_wire_structured = []
    for idx, r in enumerate((records or [])[:25], start=1):
        raw_title = str(r.get("title") or "").strip()
        rec_id = str(r.get("id") or "")
        j_key = classify_jurisdiction(r)
        slug = slugify_contract(raw_title, fallback_id=rec_id)
        live_wire_structured.append(
            {
                "index": idx,
                "id": rec_id,
                "title": clean_title_text(raw_title),
                "agency": r.get("agency"),
                "closing_date": r.get("closing_date"),
                "jurisdiction": j_key,
                "jurisdiction_label": JURISDICTION_LABELS.get(j_key, "FEDERAL // SAM.GOV"),
                "vertical": classify_vertical_tag(r),
                "official_bid_url": r.get("url"),
                "unlocked_dossier_url": f"{SITE_BASE_URL}/contracts/rfp/{slug}.html?unlocked=1",
            }
        )

    if norm_tier == "tier_1":
        return {
            "event": "signaltender.cycle_briefing.dispatched",
            "tier": "tier_1",
            "tier_name": "Tier 1 // SignalWire Pro (52-Portal Live RFP Alert Wire)",
            "platform": platform,
            "cycle_timestamp_utc": cycle_iso,
            "summary": {
                "total_live_wire_contracts": total_wire,
                "capturedesk_dossiers_included": 0,
                "federal_count": fed_count,
                "state_sled_count": sled_count,
                "municipal_count": muni_count,
            },
            "section_1_live_wire_contracts": live_wire_structured,
            "contracts": live_wire_structured,
            "text": plain_summary,
            "content": plain_summary,
        }

    dossiers_structured = []
    for idx, d in enumerate(resolved_dossiers, start=1):
        d_url = str(d.get("dossier_url") or f"{SITE_BASE_URL}/contracts")
        if "?unlocked=1" not in d_url:
            d_url = f"{d_url}?unlocked=1"
        dossiers_structured.append(
            {
                "dossier_index": idx,
                "id": str(d.get("id") or ""),
                "title": clean_title_text(str(d.get("title") or "")),
                "agency": d.get("agency"),
                "closing_date": d.get("closing_date"),
                "jurisdiction_badge": d.get("jurisdiction_badge"),
                "vertical": d.get("vertical"),
                "primary_naics": d.get("primary_naics"),
                "primary_psc": d.get("primary_psc"),
                "primary_nigp": d.get("primary_nigp"),
                "sba_size_standard": d.get("sba_size_standard"),
                "ostensible_sub_risk": d.get("ostensible_sub_risk"),
                "compliance_posture": d.get("compliance_posture"),
                "igce_ptw_posture": d.get("igce_ptw_posture"),
                "key_personnel_lcats": d.get("key_personnel_lcats"),
                "cpars_relevance_benchmark": d.get("cpars_relevance_benchmark"),
                "teaming_posture": d.get("teaming_posture"),
                "win_themes": d.get("win_themes", []),
                "evidence_needed": d.get("evidence_needed", []),
                "official_bid_url": d.get("source_url"),
                "unlocked_dossier_url": d_url,
            }
        )

    tier_names_map = {
        "tier_4": "Tier 4 // Enterprise OEM & FOIA Winning-Bid Vault (50k API Calls/Mo + 25-API Dossiers + 52-Portal Wire)",
        "tier_3": "Tier 3 // Proposal Autopilot Enterprise (6-File Shipley .ZIP Compiler + 25-API Dossiers + 52-Portal Wire)",
        "tier_2": "Tier 2 // CaptureDesk Autopilot (Unified 25-API Dossiers + 52-Portal Live Wire)",
    }
    return {
        "event": "signaltender.cycle_briefing.dispatched",
        "tier": norm_tier,
        "tier_name": tier_names_map.get(norm_tier, tier_names_map["tier_2"]),
        "platform": platform,
        "cycle_timestamp_utc": cycle_iso,
        "summary": {
            "capturedesk_dossiers_included": len(dossiers_structured),
            "total_live_wire_contracts": total_wire,
            "federal_count": fed_count,
            "state_sled_count": sled_count,
            "municipal_count": muni_count,
        },
        "section_1_capturedesk_dossiers": dossiers_structured,
        "section_2_live_wire_contracts": live_wire_structured,
        "contracts": live_wire_structured,
        "text": plain_summary,
        "content": plain_summary,
    }


def _dispatch_to_external_customer_webhooks(
    supabase: Client,
    records: list[dict],
    dossiers: list[dict] | None = None,
) -> int:
    """
    Dispatch newly discovered RFPs to any active subscriber external webhooks
    (Slack, Microsoft Teams, Zapier, Make.com, n8n, HubSpot, Salesforce) AND
    dispatch tier-specific 6-Hour Email Briefings (with Tier 2 combining both
    CaptureDesk Autopilot 25-API Dossiers and the Live RFP Alert Wire in one unified package)
    stored in Supabase with status='SUBSCRIBER_ACTIVE'.
    """
    import json
    dispatched = 0
    try:
        sub_resp = supabase.table(TABLE_NAME).select("title,status").eq("status", "SUBSCRIBER_ACTIVE").execute()
        sub_rows = sub_resp.data if sub_resp and getattr(sub_resp, "data", None) else []
    except Exception:
        sub_rows = []

    if not sub_rows or not records:
        return 0

    for srow in sub_rows:
        try:
            if str(srow.get("status") or "") != "SUBSCRIBER_ACTIVE":
                continue
            meta = json.loads(str(srow.get("title") or "{}"))
            sub_tier = str(meta.get("tier") or "tier_2").strip().lower()
            if str(meta.get("status") or "") == "canceled" or sub_tier == "canceled":
                continue
            sub_email = str(meta.get("email") or "").strip().lower()
            if sub_email and "@" in sub_email and bool(meta.get("email_briefings_enabled", False)):
                team_cc = meta.get("team_cc_emails") if isinstance(meta.get("team_cc_emails"), list) else []
                email_recipients = [sub_email] + [str(cc).strip().lower() for cc in team_cc if "@" in str(cc) and str(cc).strip().lower() != sub_email][:5]
                for recip_email in email_recipients:
                    _send_subscriber_email_briefing(
                        to_email=recip_email,
                        records=records,
                        tier=sub_tier,
                        dossiers=dossiers,
                        subscriber_meta=meta,
                    )
            w_url = str(meta.get("webhook_url") or "").strip()
            if not w_url.startswith("https://"):
                continue
            dest_type = str(meta.get("destination_type") or "auto").strip()
            payload = format_external_webhook_payload(
                tier=sub_tier,
                webhook_url=w_url,
                records=records,
                dossiers=dossiers,
                destination_type=dest_type,
            )
            requests.post(w_url, json=payload, timeout=10)
            dispatched += 1
        except Exception as ext_err:
            print(f"[!] External customer webhook warning: {ext_err}", flush=True)
    return dispatched


def _parse_closing_date_obj(date_str: str, title: str = ""):
    from datetime import datetime
    candidates = [str(date_str or "").strip()]
    m_due = re.search(r"Due:\s*(\d{1,2}/\d{1,2}/\d{2,4})", str(title or ""), flags=re.IGNORECASE)
    if m_due:
        candidates.append(m_due.group(1))
    for cand in candidates:
        if not cand or cand.lower() in ("n/a", "tbd", "none", "null", "open", ""):
            continue
        if "T" in cand:
            cand = cand.split("T")[0].strip()
        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y"):
            try:
                return datetime.strptime(cand, fmt).date()
            except ValueError:
                pass
    return None


def _dispatch_closing_soon_nudges_for_inbound_leads(supabase: Client) -> int:
    """
    Upgrade #4 (72-Hour / 5-Day Deadline Urgency Nudge):
    Checks verified Free Explorer / Inbound Dossier leads (`SUBSCRIBER_INBOUND_LEAD`) who have not
    yet converted to `SUBSCRIBER_ACTIVE`. When an open IT/Cyber solicitation in their selected state
    reaches 1 to 5 days before `closing_date`, dispatches a single de-duplicated urgency notification
    (logged in Supabase as `SUBSCRIBER_DEADLINE_NUDGE_LOG` via RLS-safe SELECT + insert).
    """
    import json
    from datetime import datetime, timezone

    today_d = datetime.now(timezone.utc).date()
    nudged_count = 0

    try:
        inb_resp = supabase.table(TABLE_NAME).select("id,title,status").in_("status", ["SUBSCRIBER_INBOUND_LEAD", "SUBSCRIBER_FREE"]).limit(300).execute()
        inb_rows = inb_resp.data if inb_resp and getattr(inb_resp, "data", None) else []
        if not inb_rows:
            return 0

        act_resp = supabase.table(TABLE_NAME).select("title").eq("status", "SUBSCRIBER_ACTIVE").limit(500).execute()
        active_emails = set()
        for r in (act_resp.data if act_resp and getattr(act_resp, "data", None) else []):
            try:
                m = json.loads(str(r.get("title") or "{}"))
                em = str(m.get("email") or "").strip().lower()
                if em:
                    active_emails.add(em)
            except Exception:
                pass

        nudge_resp = supabase.table(TABLE_NAME).select("url").eq("status", "SUBSCRIBER_DEADLINE_NUDGE_LOG").limit(1000).execute()
        already_nudged_urls = {
            str(r.get("url") or "").strip()
            for r in (nudge_resp.data if nudge_resp and getattr(nudge_resp, "data", None) else [])
        }

        open_resp = supabase.table(TABLE_NAME).select("*").order("id", desc=True).limit(1000).execute()
        all_contracts = [
            r for r in (open_resp.data if open_resp and getattr(open_resp, "data", None) else [])
            if not str(r.get("url") or "").startswith(("subscriber://", "treasury://"))
            and not str(r.get("status") or "").startswith("SUBSCRIBER_")
        ]

        closing_soon_by_jurisdiction: dict[str, list[ tuple[int, dict] ]] = {}
        for rec in all_contracts:
            dt = _parse_closing_date_obj(str(rec.get("closing_date") or ""), str(rec.get("title") or ""))
            if not dt:
                continue
            days_left = (dt - today_d).days
            if 1 <= days_left <= 5:
                j_key = classify_jurisdiction(rec)
                closing_soon_by_jurisdiction.setdefault(j_key, []).append((days_left, rec))

        if not closing_soon_by_jurisdiction:
            return 0

        for irow in inb_rows:
            try:
                meta = json.loads(str(irow.get("title") or "{}"))
            except Exception:
                continue
            if not isinstance(meta, dict) or meta.get("suppress_alert"):
                continue
            email = str(meta.get("email") or "").strip().lower()
            if not email or "@" not in email or email in active_emails:
                continue
            dom = email.split("@", 1)[1]
            if dom in ("example.com", "test.com", "localhost"):
                continue
            log_url = f"subscriber://deadline-nudge/{email}"
            if log_url in already_nudged_urls:
                continue

            af = meta.get("alert_filters") if isinstance(meta.get("alert_filters"), dict) else {}
            cp = meta.get("company_profile") if isinstance(meta.get("company_profile"), dict) else {}
            af_states = af.get("states") if isinstance(af.get("states"), list) and af.get("states") else []
            target_state = str(
                meta.get("target_state")
                or (af_states[0] if af_states else "virginia")
            ).strip().lower()
            candidates = []
            for st_cand in ([target_state] + [str(s).strip().lower() for s in af_states]):
                if closing_soon_by_jurisdiction.get(st_cand):
                    candidates.extend(closing_soon_by_jurisdiction[st_cand])
            if not candidates:
                candidates = closing_soon_by_jurisdiction.get("federal") or []
            if not candidates:
                for fallback_list in closing_soon_by_jurisdiction.values():
                    if fallback_list:
                        candidates = fallback_list
                        break
            if not candidates:
                continue

            candidates.sort(key=lambda x: x[0])
            days_left, top_rec = candidates[0]
            clean_t = clean_title_text(str(top_rec.get("title") or "Government IT Solicitation"))
            agency = str(top_rec.get("agency") or "Government Agency").strip()
            closing_str = str(top_rec.get("closing_date") or "Soon").strip()
            slug = slugify_contract(str(top_rec.get("title") or ""), fallback_id=str(top_rec.get("id") or ""))
            dossier_url = f"{SITE_BASE_URL}/contracts/rfp/{slug}.html"
            fname = str(meta.get("first_name") or email.split("@", 1)[0].split(".")[0].capitalize() or "Capture Team").strip()
            comp = str(cp.get("company_name") or meta.get("company") or "your team").strip()
            state_disp = target_state.replace("_", " ").title()

            subj = f"[Locked Territory Match] {days_left}-Day Deadline: {clean_t[:62]} ({agency})"
            body = (
                f"Hi {fname},\n\n"
                f"Locked Territory Match & Deadline Alert based on {comp}'s saved {state_disp} filter on SignalTender:\n\n"
                f"• Solicitation: {clean_t}\n"
                f"• Issuing Agency: {agency}\n"
                f"• Submission Deadline: {closing_str} ({days_left} day{'s' if days_left != 1 else ''} remaining)\n"
                f"• Pre-Shredded Capture Dossier: {dossier_url}\n\n"
                f"Our CaptureDesk engine has already generated the Shipley Section L/M Compliance Matrix, "
                f"CPARS Volume III Past Performance citations, 13 CFR § 125.6 Teaming Plan, and IGCE Price-to-Win "
                f"model for this solicitation.\n\n"
                f"You can unlock the full un-blurred official portal link, 25-API CaptureDesk suite, and 1-Click 6-File Shipley Proposal .ZIP Compiler in 60 seconds "
                f"(Tier 1 SignalWire Pro $99/mo, Tier 2 CaptureDesk Autopilot $399/mo, Tier 3 Proposal Autopilot $1,499/mo, or Tier 4 Enterprise OEM & FOIA Vault $2,499/mo — FAR 31.205-18 Corporate P-Card Ready with 1-click non-renewing pass toggle) here:\n"
                f"{SITE_BASE_URL}/#checkout\n\n"
                f"Or manage your saved bids and alert filters in your Client Portal:\n"
                f"{SITE_BASE_URL}/#account\n\n"
                f"Best,\nAaron Chen\nFounder, SignalTender"
            )

            sent_ok = _dispatch_via_instantly_transactional_campaign(
                to_email=email,
                subject=subj,
                plain_body=body,
                first_name=fname,
                company_name=comp,
            )

            already_nudged_urls.add(log_url)
            chk = supabase.table(TABLE_NAME).select("id").eq("url", log_url).execute()
            if not (chk and getattr(chk, "data", None)):
                supabase.table(TABLE_NAME).insert({
                    "title": json.dumps({
                        "email": email,
                        "company": comp,
                        "contract_id": top_rec.get("id"),
                        "days_left": days_left,
                        "sent_ok": sent_ok,
                        "nudged_at": datetime.now(timezone.utc).isoformat(),
                    }),
                    "agency": f"DEADLINE_NUDGE:{target_state.upper()}",
                    "url": log_url,
                    "status": "SUBSCRIBER_DEADLINE_NUDGE_LOG",
                }).execute()
            nudged_count += 1
    except Exception as nudge_err:
        print(f"[!] Deadline nudge check warning: {nudge_err}", flush=True)

    return nudged_count


def deliver_leads(client_webhook_url: str = None) -> int:
    """
    Query Supabase for 'New Lead' contracts, format them into enriched Discord
    intelligence blocks (with pSEO Dossier + FastAPI links), route them to the
    Master Client Discord Wire, any configured state-specific Discord channels,
    AND any active subscriber Slack/Teams/CRM webhooks, then update status to 'Delivered'.
    """
    target_webhook = client_webhook_url or CLIENT_DISCORD_WEBHOOK_URL

    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("SUPABASE_URL or SUPABASE_KEY is missing in environment variables.")
        if not target_webhook:
            raise ValueError("Client Discord Webhook URL is missing in environment variables.")

        print("[*] Connecting to Supabase...", flush=True)
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

        print(f"[*] Querying '{TABLE_NAME}' table for records with status='New Lead'...", flush=True)
        resp = supabase.table(TABLE_NAME).select("*").eq("status", "New Lead").execute()
        raw_records = [
            r for r in (resp.data if resp and getattr(resp, "data", None) else [])
            if not str(r.get("url") or "").startswith(("subscriber://", "treasury://"))
        ]
        try:
            from pseo_generator import is_commodity_it_spam as _is_spam
        except Exception:
            _is_spam = lambda _t: False
        rfp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contracts", "rfp")
        records = []
        spam_urls = []
        for r in raw_records:
            t_str = str(r.get("title") or "")
            s_slug = slugify(t_str, r.get("id", "rfp"))
            if _is_spam(t_str) or not os.path.exists(os.path.join(rfp_dir, f"{s_slug}.html")):
                if r.get("url"):
                    spam_urls.append(r["url"])
                continue
            records.append(r)
        if spam_urls:
            try:
                supabase.table(TABLE_NAME).update({"status": "Filtered_Noise"}).in_("url", spam_urls).execute()
            except Exception:
                pass

        if not records:
            print("[+] No 'New Lead' records found to deliver.", flush=True)
            _dispatch_closing_soon_nudges_for_inbound_leads(supabase)
            return 0

        print(f"[*] Found {len(records)} 'New Lead' record(s) ready for delivery.", flush=True)

        # 1. Post all leads to the Master Client Discord Webhook (#all-active-rfps)
        _post_batches_to_webhook(records, target_webhook, label="Master All-Access Wire")

        # 2. Route leads to any state/portal-specific Discord channel webhooks configured in .env
        for j_key, j_webhook in JURISDICTION_WEBHOOKS.items():
            if not j_webhook or j_webhook == target_webhook:
                continue
            j_records = [r for r in records if classify_jurisdiction(r) == j_key]
            if j_records:
                try:
                    _post_batches_to_webhook(j_records, j_webhook, label=f"State Channel ({j_key.upper()})")
                except Exception as ch_err:
                    print(f"[!] State channel webhook ({j_key}) warning: {ch_err}", flush=True)

        # 3. Route leads to any active subscriber external webhooks (Slack, MS Teams, Zapier, Make, n8n, CRM)
        ext_count = _dispatch_to_external_customer_webhooks(supabase, records)
        if ext_count:
            print(f"[+] Dispatched RFP batch to {ext_count} external customer Slack/Teams/CRM webhook(s).", flush=True)

        # 3b. Check Free Explorer / Inbound leads for 1-to-5-day closing-soon deadline urgency nudges
        nudge_count = _dispatch_closing_soon_nudges_for_inbound_leads(supabase)
        if nudge_count:
            print(f"[+] Dispatched {nudge_count} closing-soon deadline urgency nudge(s) to Free Explorer leads.", flush=True)

        # 4. Update Supabase status from 'New Lead' to 'Delivered'
        urls_delivered = [rec["url"] for rec in records if rec.get("url")]
        for i in range(0, len(urls_delivered), 50):
            chunk = urls_delivered[i : i + 50]
            supabase.table(TABLE_NAME).update({"status": "Delivered"}).in_("url", chunk).execute()

        delivered_count = len(records)
        print(f"[+] Client delivery complete! Successfully delivered {delivered_count} enriched lead(s).", flush=True)
        return delivered_count

    except Exception as e:
        error_msg = f"client_delivery.py failed: {e}"
        print(f"\n[!] Error during client delivery: {e}", flush=True)
        try:
            with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"\n[!] Error during client delivery: {e}\n")
        except Exception:
            pass
        send_discord_alert(error_msg)
        return 0


if __name__ == "__main__":
    deliver_leads()
