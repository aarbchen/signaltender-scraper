from error_telemetry import configure_utf8_stdio, report_error
configure_utf8_stdio()
"""
SignalTender — CaptureDesk Autopilot Dossier Engine
Automatically chains SignalTender's live FastAPI microservices (NAICS/PSC/SIC/NIGP Classifier
and Shipley Compliance Matrix & Outline) against newly scraped Federal & State SLED RFPs in Supabase,
persists enriched JSON dossiers, and dispatches executive CaptureDesk briefs to Discord.
"""

import json
import os
import re
from datetime import datetime, timezone
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables without hardcoding secrets
load_dotenv(dotenv_path=r"D:\Daas\.env")
load_dotenv(dotenv_path=r"D:\Data API Ecosystem\.env")
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TABLE_NAME = os.getenv("SUPABASE_TABLE_NAME", "contracts")

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
DISCORD_CAPTUREDESK_WEBHOOK_URL = os.getenv("DISCORD_CAPTUREDESK_WEBHOOK_URL")

API_BASE_URL = os.getenv(
    "SIGNALTENDER_API_BASE_URL",
    "https://b2b-contract-parser-api.onrender.com",
).rstrip("/")
RAPIDAPI_PROXY_SECRET = os.getenv("RAPIDAPI_PROXY_SECRET")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

SITE_BASE_URL = os.getenv("SIGNALTENDER_SITE_URL", "https://signaltender.net").rstrip("/")
STRIPE_TIER2_URL = os.getenv(
    "STRIPE_TIER2_CHECKOUT_URL",
    f"{SITE_BASE_URL}/index.html#checkout-tier2",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ERROR_LOG_PATH = os.path.join(BASE_DIR, "error_log.txt")
DOSSIER_CACHE_PATH = os.path.join(BASE_DIR, "capturedesk_dossiers.json")
BATCH_LIMIT = int(os.getenv("CAPTUREDESK_BATCH_LIMIT", "2"))

RAPIDAPI_ENDPOINT_HOSTS = {
    "/v1/classify/naics-psc-nigp": "naics-sic-psc-unspsc-industry-classifier-api.p.rapidapi.com",
    "/v1/generate/compliance-matrix": "rfp-compliance-matrix-proposal-outline-api.p.rapidapi.com",
    "/v1/generate/price-to-win": "govcon-igce-wrap-rate-price-to-win-modeler-api.p.rapidapi.com",
    "/v1/audit/far-dfars-clauses": "far-dfars-cmmc-clause-flow-down-auditor-api.p.rapidapi.com",
    "/v1/generate/teaming-strategy": "small-business-set-aside-subcontracting-calculator-api.p.rapidapi.com",
    "/v1/generate/past-performance": "cpars-past-performance-volume-generator-api.p.rapidapi.com",
    "/v1/generate/oral-presentation-prep": "govcon-oral-presentation-tech-demo-murder-board-prep-api.p.rapidapi.com",
    "/v1/generate/ato-rmf-package": "govcon-rmf-continuous-ato-cato-ssp-poa-m-generator-api.p.rapidapi.com",
    "/v1/generate/debriefing-bid-protest": "govcon-debriefing-far-15-506-gao-bid-protest-analyzer-api.p.rapidapi.com",
    "/v1/generate/gsa-mas-offer": "govcon-gsa-mas-schedule-sin-mapper-prc-compliance-api.p.rapidapi.com",
    "/v1/generate/sources-sought-response": "govcon-sources-sought-rfi-set-aside-shaping-responder-api.p.rapidapi.com",
    "/v1/generate/quality-assurance-qasp": "govcon-qasp-prs-sla-kpi-surveillance-matrix-api.p.rapidapi.com",
    "/v1/generate/phase-in-transition-plan": "govcon-30-60-90-day-phase-in-transition-plan-api.p.rapidapi.com",
    "/v1/generate/capture-black-hat-review": "govcon-shipley-black-hat-incumbent-ghosting-api.p.rapidapi.com",
}

JURISDICTION_LABELS = {
    "federal": "FEDERAL // SAM.GOV",
    "texas": "TEXAS // ESBD",
    "virginia": "VIRGINIA // eVA",
    "california": "CALIFORNIA // CAL EPROCURE",
    "florida": "FLORIDA // MFMP VIP",
    "maryland": "MARYLAND // EMMA & BONFIRE",
    "new_york": "NEW YORK // NYC CROL, PASSPORT & PANYNJ",
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


def log_error(msg: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{timestamp}] [CaptureDesk Autopilot] {msg}\n"
    try:
        with open(ERROR_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception:
        pass


def send_discord_alert(message: str) -> None:
    """Silently record runtime error to telemetry for autonomous self-healing (resolved-only Discord policy)."""
    report_error("capturedesk_autopilot.py", str(message))
    log_error(str(message))


def classify_jurisdiction(record: dict) -> str:
    title = str(record.get("title") or "").strip()
    agency = str(record.get("agency") or "").strip().lower()
    url = str(record.get("url") or record.get("source_url") or "").strip().lower()

    if "demandstar.com" in url:
        return "municipal"
    if "sam.gov" in url or "sbir.gov" in url:
        return "federal"
    if "txsmartbuy.com" in url:
        return "texas"
    if "eva.virginia.gov" in url or "cgieva.com" in url:
        return "virginia"
    if "caleprocure.ca.gov" in url:
        return "california"
    if "myfloridamarketplace.com" in url:
        return "florida"
    if "bidbuy.illinois.gov" in url or "transitchicago.bonfirehub.com" in url or "cookcountyil.bonfirehub.com" in url:
        return "illinois"
    if "emarketplace.state.pa.us" in url or "dgs.pa.gov" in url or "philaport.bonfirehub.com" in url:
        return "pennsylvania"
    if (
        "ohiobuys.ohio.gov" in url
        or "ohioauditor.gov" in url
        or "morpc.org" in url
        or "franklincountyohio.gov" in url
        or "columbus.bonfirehub.com" in url
        or "cincinnati-oh.bonfirehub.com" in url
        or "westerville.bonfirehub.com" in url
        or "dps.bonfirehub.com" in url
        or "akronohio.bonfirehub.com" in url
    ):
        return "ohio"
    if (
        "doas.state.ga.us" in url
        or "georgia.gov" in url
        or "ga.gov" in url
        or "forsythco.bonfirehub.com" in url
        or "fultonschools.bonfirehub.com" in url
        or "cobbk12.bonfirehub.com" in url
        or "itsmarta.com" in url
    ):
        return "georgia"
    if (
        "evp.nc.gov" in url
        or "nc.gov" in url
        or "unc.edu" in url
        or "ncsu.edu" in url
        or "wake.gov" in url
        or "mecknc.gov" in url
        or "charlottenc.gov" in url
        or "durhamnc.gov" in url
        or "guilfordcountync.gov" in url
    ):
        return "north_carolina"
    if (
        "a856-cityrecord.nyc.gov" in url
        or "passport.cityofnewyork.us" in url
        or "cityofnewyork.us" in url
        or "panynj.bonfirehub.com" in url
        or "suffolkcountyny.bonfirehub.com" in url
        or "rocklandgov.bonfirehub.com" in url
        or "nyscr.ny.gov" in url
        or "ogs.ny.gov" in url
    ):
        return "new_york"
    if (
        "commbuys.com" in url
        or "mass.gov" in url
        or "boston.gov" in url
        or "mbta.com" in url
        or "massport.com" in url
        or "masstech.org" in url
    ):
        return "massachusetts"
    if (
        "njstart.gov" in url
        or "nj.gov" in url
        or "njtransit.com" in url
        or "rutgers.edu" in url
    ):
        return "new_jersey"
    if (
        "pr-webs-vendor.des.wa.gov" in url
        or "des.wa.gov" in url
        or "watech.wa.gov" in url
        or "wsdot.wa.gov" in url
        or "hca.wa.gov" in url
        or "dshs.wa.gov" in url
        or "dol.wa.gov" in url
        or "wa.gov" in url
    ):
        return "washington"
    if (
        "sigma.michigan.gov" in url
        or "michigan.gov" in url
    ):
        return "michigan"
    if (
        "colorado.gov" in url
        or "denvergov.org" in url
        or "coloradosprings.gov" in url
        or "cu.edu" in url
    ):
        return "colorado"
    if (
        "app.az.gov" in url
        or "procure.az.gov" in url
        or "azdoa.gov" in url
        or "az.gov" in url
        or "phoenix.gov" in url
        or "maricopa.gov" in url
        or "asu.edu" in url
    ):
        return "arizona"
    if (
        "mn.gov" in url
        or "questcdn.com" in url
        or "metrocouncil.org" in url
        or "umn.edu" in url
        or "hennepin.us" in url
        or "minneapolismn.gov" in url
        or "stpaul.gov" in url
    ):
        return "minnesota"
    if (
        "tn.gov" in url
        or "tennessee.edu" in url
        or "tbr.edu" in url
        or "nashville.gov" in url
        or "memphistn.gov" in url
        or "shelbycountytn.gov" in url
    ):
        return "tennessee"
    if (
        "in.gov/idoa" in url
        or "iot.in.gov" in url
        or "fs.gmis.in.gov" in url
        or "in.gov" in url
        or "indy.gov" in url
        or "purdue.edu" in url
        or "indiana.edu" in url
    ):
        return "indiana"
    if (
        "missouribuys.mo.gov" in url
        or "oa.mo.gov" in url
        or "modot.org" in url
        or "mo.gov" in url
        or "stlouis-mo.gov" in url
        or "kcmo.gov" in url
        or "umsystem.edu" in url
    ):
        return "missouri"
    if (
        "esupplier.wi.gov" in url
        or "vendornet.wi.gov" in url
        or "doa.wi.gov" in url
        or "wi.gov" in url
        or "wisc.edu" in url
    ):
        return "wisconsin"
    if (
        "scbo.sc.gov" in url
        or "procurement.sc.gov" in url
        or "admin.sc.gov" in url
        or "sc.gov" in url
        or "clemson.edu" in url
    ):
        return "south_carolina"
    if (
        "oregonbuys.gov" in url
        or "oregon.gov" in url
        or "portland.gov" in url
        or "ohsu.edu" in url
        or "oregonstate.edu" in url
    ):
        return "oregon"
    if (
        "portal.ct.gov" in url
        or "biznet.ct.gov" in url
        or "ct.gov" in url
        or "uconn.edu" in url
    ):
        return "connecticut"
    if (
        "purchasing.utah.gov" in url
        or "dts.utah.gov" in url
        or "utah.gov" in url
        or "utah.edu" in url
    ):
        return "utah"
    if (
        "nevadaepro.com" in url
        or "purchasing.nv.gov" in url
        or "eits.nv.gov" in url
        or "nv.gov" in url
        or "clarkcountynv.gov" in url
        or "lasvegasnevada.gov" in url
        or "unlv.edu" in url
        or "unr.edu" in url
    ):
        return "nevada"
    if (
        "alabamabuys.gov" in url
        or "purchasing.alabama.gov" in url
        or "oit.alabama.gov" in url
        or "alabama.gov" in url
        or "huntsvilleal.gov" in url
        or "birminghamal.gov" in url
        or "ua.edu" in url
        or "auburn.edu" in url
    ):
        return "alabama"
    if (
        "doa.louisiana.gov" in url
        or "lapac" in url
        or "louisiana.gov" in url
        or "la.gov" in url
        or "nola.gov" in url
        or "brla.gov" in url
        or "lsu.edu" in url
    ):
        return "louisiana"
    if (
        "vss.ky.gov" in url
        or "finance.ky.gov" in url
        or "cot.ky.gov" in url
        or "ky.gov" in url
        or "louisvilleky.gov" in url
        or "lexingtonky.gov" in url
        or "uky.edu" in url
        or "louisville.edu" in url
    ):
        return "kentucky"
    if (
        "oklahoma.gov/omes" in url
        or "omes.ok.gov" in url
        or "oklahoma.gov" in url
        or "ok.gov" in url
        or "okc.gov" in url
        or "cityoftulsa.org" in url
        or "ou.edu" in url
        or "okstate.edu" in url
    ):
        return "oklahoma"
    if (
        "customerorg=stateofiowa" in url
        or "das.iowa.gov" in url
        or "dom.iowa.gov" in url
        or "iowa.gov" in url
        or "uiowa.edu" in url
        or "iastate.edu" in url
    ):
        return "iowa"
    if (
        "admin.ks.gov" in url
        or "oits.ks.gov" in url
        or "ks.gov" in url
        or "kansas.gov" in url
        or "ku.edu" in url
        or "ksu.edu" in url
    ):
        return "kansas"
    if (
        "arbuy.arkansas.gov" in url
        or "transform.ar.gov" in url
        or "arkansas.gov" in url
        or "ar.gov" in url
        or "uark.edu" in url
        or "uams.edu" in url
    ):
        return "arkansas"
    if (
        "its.ms.gov" in url
        or "dfa.ms.gov" in url
        or "ms.gov" in url
        or "mississippi.gov" in url
        or "msstate.edu" in url
        or "olemiss.edu" in url
    ):
        return "mississippi"
    if (
        "generalservices.state.nm.us" in url
        or "doit.nm.gov" in url
        or "nm.gov" in url
        or "state.nm.us" in url
        or "unm.edu" in url
        or "nmsu.edu" in url
    ):
        return "new_mexico"
    if (
        "das.nebraska.gov" in url
        or "cio.nebraska.gov" in url
        or "nebraska.gov" in url
        or "ne.gov" in url
        or "nebraska.edu" in url
        or "unl.edu" in url
    ):
        return "nebraska"
    if (
        "purchasing.idaho.gov" in url
        or "its.idaho.gov" in url
        or "idaho.gov" in url
        or "id.gov" in url
        or "boisestate.edu" in url
        or "uidaho.edu" in url
    ):
        return "idaho"
    if (
        "hiepro.ehawaii.gov" in url
        or "hands.ehawaii.gov" in url
        or "ets.hawaii.gov" in url
        or "hawaii.gov" in url
        or "ehawaii.gov" in url
        or "hawaii.edu" in url
    ):
        return "hawaii"
    if (
        "das.nh.gov" in url
        or "doit.nh.gov" in url
        or "nh.gov" in url
        or "usnh.edu" in url
        or "unh.edu" in url
    ):
        return "new_hampshire"
    if (
        "maine.gov/dafs" in url
        or "maine.gov/oit" in url
        or "maine.gov" in url
        or "maine.edu" in url
    ):
        return "maine"
    if (
        "ridop.ri.gov" in url
        or "etss.ri.gov" in url
        or "ri.gov" in url
        or "uri.edu" in url
    ):
        return "rhode_island"
    if (
        "spb.mt.gov" in url
        or "sitsd.mt.gov" in url
        or "mt.gov" in url
        or "montana.edu" in url
        or "umt.edu" in url
    ):
        return "montana"
    if (
        "mmp.delaware.gov" in url
        or "bids.delaware.gov" in url
        or "dti.delaware.gov" in url
        or "delaware.gov" in url
        or "udel.edu" in url
    ):
        return "delaware"
    if (
        "boa.sd.gov" in url
        or "bit.sd.gov" in url
        or "sd.gov" in url
        or "dsu.edu" in url
        or "sdstate.edu" in url
    ):
        return "south_dakota"
    if (
        "apps.nd.gov/csd/spo" in url
        or "omb.nd.gov" in url
        or "ndit.nd.gov" in url
        or "nd.gov" in url
        or "und.edu" in url
        or "ndsu.edu" in url
    ):
        return "north_dakota"
    if (
        "aws.state.ak.us" in url
        or "iris-vss.alaska.gov" in url
        or "oit.alaska.gov" in url
        or "alaska.gov" in url
        or "state.ak.us" in url
        or "alaska.edu" in url
    ):
        return "alaska"
    if (
        "vermontbusinessregistry.com" in url
        or "bgs.vermont.gov" in url
        or "ads.vermont.gov" in url
        or "vermont.gov" in url
        or "uvm.edu" in url
    ):
        return "vermont"
    if (
        "wvoasis.gov" in url
        or "state.wv.us/admin/purchase" in url
        or "technology.wv.gov" in url
        or "wv.gov" in url
        or "wvu.edu" in url
        or "marshall.edu" in url
    ):
        return "west_virginia"
    if (
        "ai.wyo.gov" in url
        or "ets.wyo.gov" in url
        or "wyo.gov" in url
        or "wyoming.gov" in url
        or "uwyo.edu" in url
    ):
        return "wyoming"
    if (
        "customerorg=stateofiowa" in url
        or "das.iowa.gov" in url
        or "dom.iowa.gov" in url
        or "iowa.gov" in url
        or "uiowa.edu" in url
        or "iastate.edu" in url
    ):
        return "iowa"
    if (
        "admin.ks.gov" in url
        or "oits.ks.gov" in url
        or "ks.gov" in url
        or "kansas.gov" in url
        or "ku.edu" in url
        or "ksu.edu" in url
    ):
        return "kansas"
    if (
        "arbuy.arkansas.gov" in url
        or "transform.ar.gov" in url
        or "arkansas.gov" in url
        or "ar.gov" in url
        or "uark.edu" in url
        or "uams.edu" in url
    ):
        return "arkansas"
    if (
        "its.ms.gov" in url
        or "dfa.ms.gov" in url
        or "ms.gov" in url
        or "mississippi.gov" in url
        or "msstate.edu" in url
        or "olemiss.edu" in url
    ):
        return "mississippi"
    if (
        "generalservices.state.nm.us" in url
        or "doit.nm.gov" in url
        or "nm.gov" in url
        or "state.nm.us" in url
        or "unm.edu" in url
        or "nmsu.edu" in url
    ):
        return "new_mexico"
    if (
        "das.nebraska.gov" in url
        or "cio.nebraska.gov" in url
        or "nebraska.gov" in url
        or "ne.gov" in url
        or "nebraska.edu" in url
        or "unl.edu" in url
    ):
        return "nebraska"
    if (
        "purchasing.idaho.gov" in url
        or "its.idaho.gov" in url
        or "idaho.gov" in url
        or "id.gov" in url
        or "boisestate.edu" in url
        or "uidaho.edu" in url
    ):
        return "idaho"
    if (
        "hiepro.ehawaii.gov" in url
        or "hands.ehawaii.gov" in url
        or "ets.hawaii.gov" in url
        or "hawaii.gov" in url
        or "ehawaii.gov" in url
        or "hawaii.edu" in url
    ):
        return "hawaii"
    if (
        "das.nh.gov" in url
        or "doit.nh.gov" in url
        or "nh.gov" in url
        or "usnh.edu" in url
        or "unh.edu" in url
    ):
        return "new_hampshire"
    if (
        "maine.gov/dafs" in url
        or "maine.gov/oit" in url
        or "maine.gov" in url
        or "maine.edu" in url
    ):
        return "maine"
    if (
        "ridop.ri.gov" in url
        or "etss.ri.gov" in url
        or "ri.gov" in url
        or "uri.edu" in url
    ):
        return "rhode_island"
    if (
        "spb.mt.gov" in url
        or "sitsd.mt.gov" in url
        or "mt.gov" in url
        or "montana.edu" in url
        or "umt.edu" in url
    ):
        return "montana"
    if (
        "mmp.delaware.gov" in url
        or "bids.delaware.gov" in url
        or "dti.delaware.gov" in url
        or "delaware.gov" in url
        or "udel.edu" in url
    ):
        return "delaware"
    if (
        "boa.sd.gov" in url
        or "bit.sd.gov" in url
        or "sd.gov" in url
        or "dsu.edu" in url
        or "sdstate.edu" in url
    ):
        return "south_dakota"
    if (
        "apps.nd.gov/csd/spo" in url
        or "omb.nd.gov" in url
        or "ndit.nd.gov" in url
        or "nd.gov" in url
        or "und.edu" in url
        or "ndsu.edu" in url
    ):
        return "north_dakota"
    if (
        "aws.state.ak.us" in url
        or "iris-vss.alaska.gov" in url
        or "oit.alaska.gov" in url
        or "alaska.gov" in url
        or "state.ak.us" in url
        or "alaska.edu" in url
    ):
        return "alaska"
    if (
        "vermontbusinessregistry.com" in url
        or "bgs.vermont.gov" in url
        or "ads.vermont.gov" in url
        or "vermont.gov" in url
        or "uvm.edu" in url
    ):
        return "vermont"
    if (
        "wvoasis.gov" in url
        or "state.wv.us/admin/purchase" in url
        or "technology.wv.gov" in url
        or "wv.gov" in url
        or "wvu.edu" in url
        or "marshall.edu" in url
    ):
        return "west_virginia"
    if (
        "ai.wyo.gov" in url
        or "ets.wyo.gov" in url
        or "wyo.gov" in url
        or "wyoming.gov" in url
        or "uwyo.edu" in url
    ):
        return "wyoming"
    if "emma.maryland.gov" in url or "maryland.gov" in url or "countymd.bonfirehub.com" in url:
        return "maryland"

    if title.startswith("[TX]") or "texas" in agency or ", tx" in agency or "ut md anderson" in agency:
        return "texas"
    if title.startswith("[VA]") or "virginia" in agency or "arlington county" in agency:
        return "virginia"
    if title.startswith("[CA]") or "california" in agency:
        return "california"
    if title.startswith("[FL]") or "florida" in agency:
        return "florida"
    if title.startswith("[IL]") or "state of illinois" in agency or "chicago transit authority" in agency or "cook county" in agency:
        return "illinois"
    if title.startswith("[PA]") or "pennsylvania" in agency or "philadelphia" in agency or agency.startswith("pa "):
        return "pennsylvania"
    if title.startswith("[GA]") or "georgia" in agency or "(ga)" in agency or "fulton county" in agency or "atlanta" in agency or "cobb county" in agency or "gwinnett" in agency or "dekalb" in agency:
        return "georgia"
    if title.startswith("[NC]") or "north carolina" in agency or "(nc)" in agency or "nc " in agency or "wake county" in agency or "mecklenburg" in agency or "charlotte" in agency or "raleigh" in agency or "durham" in agency or "guilford" in agency:
        return "north_carolina"
    if (
        title.startswith("[NY]")
        or "new york" in agency
        or "nyc " in agency
        or "(ny)" in agency
        or "panynj" in agency
        or "port authority of new york" in agency
        or "suffolk county" in agency
        or "rockland county" in agency
    ):
        return "new_york"
    if (
        title.startswith("[MA]")
        or "massachusetts" in agency
        or "(ma)" in agency
        or "commbuys" in agency
        or "city of boston" in agency
        or "boston public" in agency
        or "mbta" in agency
        or "massport" in agency
        or "eotss" in agency
    ):
        return "massachusetts"
    if (
        title.startswith("[NJ]")
        or "new jersey" in agency
        or "(nj)" in agency
        or "njstart" in agency
        or "nj transit" in agency
        or "rutgers" in agency
    ):
        return "new_jersey"
    if (
        title.startswith("[WA]")
        or "washington state" in agency
        or "state of washington" in agency
        or "(wa)" in agency
        or "watech" in agency
        or "wa des" in agency
        or "wsdot" in agency
    ):
        return "washington"
    if (
        title.startswith("[MI]")
        or title.lower().startswith("[mi-")
        or "michigan" in agency
        or "(mi)" in agency
        or "mi sigma" in agency
        or "dtmb" in agency
        or "mdhhs" in agency
        or "mdot" in agency
        or "msp" in agency
    ):
        return "michigan"
    if (
        title.startswith("[CO]")
        or title.lower().startswith("[co-")
        or "colorado" in agency
        or "(co)" in agency
        or "co vss" in agency
        or "co oit" in agency
        or "cdot" in agency
        or "cdphe" in agency
        or "cdhs" in agency
    ):
        return "colorado"
    if (
        title.startswith("[AZ]")
        or title.lower().startswith("[az-")
        or "arizona" in agency
        or "(az)" in agency
        or "az app" in agency
        or "adoa" in agency
        or "ahcccs" in agency
        or "adot" in agency
        or "maricopa" in agency
    ):
        return "arizona"
    if (
        title.startswith("[MN]")
        or title.lower().startswith("[mn-")
        or "minnesota" in agency
        or "(mn)" in agency
        or "mn swift" in agency
        or "mnit" in agency
        or "mndot" in agency
        or "metropolitan council" in agency
    ):
        return "minnesota"
    if (
        title.startswith("[TN]")
        or title.lower().startswith("[tn-")
        or "tennessee" in agency
        or "(tn)" in agency
        or "tn cpo" in agency
        or "edison" in agency
        or "tenncare" in agency
        or "tdot" in agency
        or "tdec" in agency
    ):
        return "tennessee"
    if (
        title.startswith("[IN]")
        or title.lower().startswith("[in-")
        or "indiana" in agency
        or "(in)" in agency
        or "idoa" in agency
        or "indianapolis" in agency
        or "fssa" in agency
        or "indot" in agency
        or "purdue" in agency
        or "nswc crane" in agency
    ):
        return "indiana"
    if (
        title.startswith("[MO]")
        or title.lower().startswith("[mo-")
        or "missouri" in agency
        or "(mo)" in agency
        or "missouribuys" in agency
        or "oa-itsd" in agency
        or "modot" in agency
        or "mo healthnet" in agency
        or "st. louis" in agency
        or "kansas city" in agency
    ):
        return "missouri"
    if (
        title.startswith("[WI]")
        or title.lower().startswith("[wi-")
        or "wisconsin" in agency
        or "(wi)" in agency
        or "esupplier" in agency
        or "doa det" in agency
        or "wisdot" in agency
        or "milwaukee" in agency
        or "uw-madison" in agency
    ):
        return "wisconsin"
    if (
        title.startswith("[SC]")
        or title.lower().startswith("[sc-")
        or "south carolina" in agency
        or "(sc)" in agency
        or "scbo" in agency
        or "sfaa" in agency
        or "scdhhs" in agency
        or "scdot" in agency
        or "niwc atlantic" in agency
        or "clemson" in agency
    ):
        return "south_carolina"
    if (
        title.startswith("[OR]")
        or title.lower().startswith("[or-")
        or "oregon" in agency
        or "(or)" in agency
        or "oregonbuys" in agency
        or "das eis" in agency
        or "odot" in agency
        or "portland" in agency
        or "multnomah" in agency
    ):
        return "oregon"
    if (
        title.startswith("[CT]")
        or title.lower().startswith("[ct-")
        or "connecticut" in agency
        or "(ct)" in agency
        or "ctsource" in agency
        or "das bits" in agency
        or "ctdot" in agency
        or "groton" in agency
        or "hartford" in agency
        or "uconn" in agency
    ):
        return "connecticut"
    if (
        title.startswith("[UT]")
        or title.lower().startswith("[ut-")
        or "utah" in agency
        or "(ut)" in agency
        or "u3p" in agency
        or "utah dts" in agency
        or "udot" in agency
        or "hill afb" in agency
        or "salt lake" in agency
    ):
        return "utah"
    if (
        title.startswith("[NV]")
        or title.lower().startswith("[nv-")
        or "nevada" in agency
        or "(nv)" in agency
        or "nevadaepro" in agency
        or "nv eits" in agency
        or "ndot" in agency
        or "nellis afb" in agency
        or "clark county" in agency
        or "las vegas" in agency
    ):
        return "nevada"
    if (
        title.startswith("[AL]")
        or title.lower().startswith("[al-")
        or "alabama" in agency
        or "(al)" in agency
        or "alabama buys" in agency
        or "staars" in agency
        or "aldot" in agency
        or "redstone" in agency
        or "huntsville" in agency
    ):
        return "alabama"
    if (
        title.startswith("[LA]")
        or title.lower().startswith("[la-")
        or "louisiana" in agency
        or "(la)" in agency
        or "lapac" in agency
        or "la ots" in agency
        or "ldh" in agency
        or "dotd" in agency
        or "barksdale" in agency
        or "baton rouge" in agency
    ):
        return "louisiana"
    if (
        title.startswith("[KY]")
        or title.lower().startswith("[ky-")
        or "kentucky" in agency
        or "(ky)" in agency
        or "ky vss" in agency
        or "ky cot" in agency
        or "chfs" in agency
        or "kytc" in agency
        or "fort knox" in agency
        or "louisville" in agency
    ):
        return "kentucky"
    if (
        title.startswith("[OK]")
        or title.lower().startswith("[ok-")
        or "oklahoma" in agency
        or "(ok)" in agency
        or "omes" in agency
        or "ohca" in agency
        or "soonercare" in agency
        or "tinker afb" in agency
        or "76th sweg" in agency
    ):
        return "oklahoma"
    if (
        title.startswith("[IA]")
        or title.lower().startswith("[ia-")
        or "iowa" in agency
        or "(ia)" in agency
        or "impacs" in agency
        or "dom doit" in agency
        or "iowa dot" in agency
        or "camp dodge" in agency
        or "des moines" in agency
    ):
        return "iowa"
    if (
        title.startswith("[KS]")
        or title.lower().startswith("[ks-")
        or "kansas" in agency
        or "(ks)" in agency
        or "ks smart" in agency
        or "oits" in agency
        or "kiso" in agency
        or "kdot" in agency
        or "fort leavenworth" in agency
        or "mcconnell afb" in agency
    ):
        return "kansas"
    if (
        title.startswith("[AR]")
        or title.lower().startswith("[ar-")
        or "arkansas" in agency
        or "(ar)" in agency
        or "arbuy" in agency
        or "ar dis" in agency
        or "ardot" in agency
        or "little rock afb" in agency
        or "ebbing" in agency
    ):
        return "arkansas"
    if (
        title.startswith("[MS]")
        or title.lower().startswith("[ms-")
        or "mississippi" in agency
        or "(ms)" in agency
        or "ms magic" in agency
        or "ms its" in agency
        or "mdot" in agency
        or "keesler afb" in agency
        or "stennis" in agency
    ):
        return "mississippi"
    if (
        title.startswith("[NM]")
        or title.lower().startswith("[nm-")
        or "new mexico" in agency
        or "(nm)" in agency
        or "nm gsd" in agency
        or "nm doit" in agency
        or "nmdot" in agency
        or "kirtland afb" in agency
        or "white sands" in agency
        or "sandia" in agency
        or "los alamos" in agency
    ):
        return "new_mexico"
    if (
        title.startswith("[NE]")
        or title.lower().startswith("[ne-")
        or "nebraska" in agency
        or "(ne)" in agency
        or "ne das" in agency
        or "ne ocio" in agency
        or "offutt afb" in agency
        or "usstratcom" in agency
        or "55th wing" in agency
        or "omaha" in agency
    ):
        return "nebraska"
    if (
        title.startswith("[ID]")
        or title.lower().startswith("[id-")
        or "idaho" in agency
        or "(id)" in agency
        or "ipro" in agency
        or "luma" in agency
        or "id its" in agency
        or "idhw" in agency
        or "mountain home afb" in agency
        or "idaho national lab" in agency
    ):
        return "idaho"
    if (
        title.startswith("[HI]")
        or title.lower().startswith("[hi-")
        or "hawaii" in agency
        or "(hi)" in agency
        or "hiepro" in agency
        or "hi ets" in agency
        or "med-quest" in agency
        or "hdot" in agency
        or "indopacom" in agency
        or "pearl harbor" in agency
        or "hickam" in agency
        or "honolulu" in agency
    ):
        return "hawaii"
    if (
        title.startswith("[NH]")
        or title.lower().startswith("[nh-")
        or "new hampshire" in agency
        or "(nh)" in agency
        or "nh das" in agency
        or "nh doit" in agency
        or "nhdot" in agency
        or "pease angb" in agency
        or "portsmouth naval" in agency
        or "new boston sfs" in agency
    ):
        return "new_hampshire"
    if (
        title.startswith("[ME]")
        or title.lower().startswith("[me-")
        or "maine" in agency
        or "(me)" in agency
        or "maineit" in agency
        or "mainecare" in agency
        or "mainedot" in agency
        or "bath iron" in agency
        or "bangor angb" in agency
    ):
        return "maine"
    if (
        title.startswith("[RI]")
        or title.lower().startswith("[ri-")
        or "rhode island" in agency
        or "(ri)" in agency
        or "ocean state procures" in agency
        or "ri etss" in agency
        or "ridot" in agency
        or "nuwc newport" in agency
        or "naval station newport" in agency
    ):
        return "rhode_island"
    if (
        title.startswith("[MT]")
        or title.lower().startswith("[mt-")
        or "montana" in agency
        or "(mt)" in agency
        or "emacs" in agency
        or "sitsd" in agency
        or "malmstrom afb" in agency
        or "341st mw" in agency
    ):
        return "montana"
    if (
        title.startswith("[DE]")
        or title.lower().startswith("[de-")
        or "delaware" in agency
        or "(de)" in agency
        or "mymarketplace" in agency
        or "de dti" in agency
        or "deldot" in agency
        or "dover afb" in agency
        or "436th aw" in agency
    ):
        return "delaware"
    if (
        title.startswith("[SD]")
        or title.lower().startswith("[sd-")
        or "south dakota" in agency
        or "(sd)" in agency
        or "sd opm" in agency
        or "sd bit" in agency
        or "sddot" in agency
        or "ellsworth afb" in agency
        or "28th bw" in agency
        or "dakota state" in agency
    ):
        return "south_dakota"
    if (
        title.startswith("[ND]")
        or title.lower().startswith("[nd-")
        or "north dakota" in agency
        or "(nd)" in agency
        or "nd spo" in agency
        or "ndit" in agency
        or "nddot" in agency
        or "minot afb" in agency
        or "grand forks afb" in agency
    ):
        return "north_dakota"
    if (
        title.startswith("[AK]")
        or title.lower().startswith("[ak-")
        or "alaska" in agency
        or "(ak)" in agency
        or "ak iris" in agency
        or "ak oit" in agency
        or "jber" in agency
        or "elmendorf" in agency
        or "eielson afb" in agency
        or "clear sfs" in agency
        or "anchorage" in agency
    ):
        return "alaska"
    if (
        title.startswith("[VT]")
        or title.lower().startswith("[vt-")
        or "vermont" in agency
        or "(vt)" in agency
        or "vt bgs" in agency
        or "vt ads" in agency
        or "vtrans" in agency
        or "dvha" in agency
        or "158th fw" in agency
        or "burlington angb" in agency
    ):
        return "vermont"
    if (
        title.startswith("[WV]")
        or title.lower().startswith("[wv-")
        or "west virginia" in agency
        or "(wv)" in agency
        or "wvoasis" in agency
        or "wvot" in agency
        or "wvdot" in agency
        or "clarksburg" in agency
        or "martinsburg" in agency
    ):
        return "west_virginia"
    if (
        title.startswith("[WY]")
        or title.lower().startswith("[wy-")
        or "wyoming" in agency
        or "(wy)" in agency
        or "wy ets" in agency
        or "wydot" in agency
        or "f.e. warren" in agency
        or "90th mw" in agency
        or "cheyenne" in agency
    ):
        return "wyoming"
    if (
        title.startswith("[IA]")
        or title.lower().startswith("[ia-")
        or "iowa" in agency
        or "(ia)" in agency
        or "impacs" in agency
        or "dom doit" in agency
        or "iowa dot" in agency
        or "camp dodge" in agency
        or "des moines" in agency
    ):
        return "iowa"
    if (
        title.startswith("[KS]")
        or title.lower().startswith("[ks-")
        or "kansas" in agency
        or "(ks)" in agency
        or "ks smart" in agency
        or "oits" in agency
        or "kiso" in agency
        or "kdot" in agency
        or "fort leavenworth" in agency
        or "mcconnell afb" in agency
    ):
        return "kansas"
    if (
        title.startswith("[AR]")
        or title.lower().startswith("[ar-")
        or "arkansas" in agency
        or "(ar)" in agency
        or "arbuy" in agency
        or "ar dis" in agency
        or "ardot" in agency
        or "little rock afb" in agency
        or "ebbing" in agency
    ):
        return "arkansas"
    if (
        title.startswith("[MS]")
        or title.lower().startswith("[ms-")
        or "mississippi" in agency
        or "(ms)" in agency
        or "ms magic" in agency
        or "ms its" in agency
        or "mdot" in agency
        or "keesler afb" in agency
        or "stennis" in agency
    ):
        return "mississippi"
    if (
        title.startswith("[NM]")
        or title.lower().startswith("[nm-")
        or "new mexico" in agency
        or "(nm)" in agency
        or "nm gsd" in agency
        or "nm doit" in agency
        or "nmdot" in agency
        or "kirtland afb" in agency
        or "white sands" in agency
        or "sandia" in agency
        or "los alamos" in agency
    ):
        return "new_mexico"
    if (
        title.startswith("[NE]")
        or title.lower().startswith("[ne-")
        or "nebraska" in agency
        or "(ne)" in agency
        or "ne das" in agency
        or "ne ocio" in agency
        or "offutt afb" in agency
        or "usstratcom" in agency
        or "55th wing" in agency
        or "omaha" in agency
    ):
        return "nebraska"
    if (
        title.startswith("[ID]")
        or title.lower().startswith("[id-")
        or "idaho" in agency
        or "(id)" in agency
        or "ipro" in agency
        or "luma" in agency
        or "id its" in agency
        or "idhw" in agency
        or "mountain home afb" in agency
        or "idaho national lab" in agency
    ):
        return "idaho"
    if (
        title.startswith("[HI]")
        or title.lower().startswith("[hi-")
        or "hawaii" in agency
        or "(hi)" in agency
        or "hiepro" in agency
        or "hi ets" in agency
        or "med-quest" in agency
        or "hdot" in agency
        or "indopacom" in agency
        or "pearl harbor" in agency
        or "hickam" in agency
        or "honolulu" in agency
    ):
        return "hawaii"
    if (
        title.startswith("[NH]")
        or title.lower().startswith("[nh-")
        or "new hampshire" in agency
        or "(nh)" in agency
        or "nh das" in agency
        or "nh doit" in agency
        or "nhdot" in agency
        or "pease angb" in agency
        or "portsmouth naval" in agency
        or "new boston sfs" in agency
    ):
        return "new_hampshire"
    if (
        title.startswith("[ME]")
        or title.lower().startswith("[me-")
        or "maine" in agency
        or "(me)" in agency
        or "maineit" in agency
        or "mainecare" in agency
        or "mainedot" in agency
        or "bath iron" in agency
        or "bangor angb" in agency
    ):
        return "maine"
    if (
        title.startswith("[RI]")
        or title.lower().startswith("[ri-")
        or "rhode island" in agency
        or "(ri)" in agency
        or "ocean state procures" in agency
        or "ri etss" in agency
        or "ridot" in agency
        or "nuwc newport" in agency
        or "naval station newport" in agency
    ):
        return "rhode_island"
    if (
        title.startswith("[MT]")
        or title.lower().startswith("[mt-")
        or "montana" in agency
        or "(mt)" in agency
        or "emacs" in agency
        or "sitsd" in agency
        or "malmstrom afb" in agency
        or "341st mw" in agency
    ):
        return "montana"
    if (
        title.startswith("[DE]")
        or title.lower().startswith("[de-")
        or "delaware" in agency
        or "(de)" in agency
        or "mymarketplace" in agency
        or "de dti" in agency
        or "deldot" in agency
        or "dover afb" in agency
        or "436th aw" in agency
    ):
        return "delaware"
    if (
        title.startswith("[SD]")
        or title.lower().startswith("[sd-")
        or "south dakota" in agency
        or "(sd)" in agency
        or "sd opm" in agency
        or "sd bit" in agency
        or "sddot" in agency
        or "ellsworth afb" in agency
        or "28th bw" in agency
        or "dakota state" in agency
    ):
        return "south_dakota"
    if (
        title.startswith("[ND]")
        or title.lower().startswith("[nd-")
        or "north dakota" in agency
        or "(nd)" in agency
        or "nd spo" in agency
        or "ndit" in agency
        or "nddot" in agency
        or "minot afb" in agency
        or "grand forks afb" in agency
    ):
        return "north_dakota"
    if (
        title.startswith("[AK]")
        or title.lower().startswith("[ak-")
        or "alaska" in agency
        or "(ak)" in agency
        or "ak iris" in agency
        or "ak oit" in agency
        or "jber" in agency
        or "elmendorf" in agency
        or "eielson afb" in agency
        or "clear sfs" in agency
        or "anchorage" in agency
    ):
        return "alaska"
    if (
        title.startswith("[VT]")
        or title.lower().startswith("[vt-")
        or "vermont" in agency
        or "(vt)" in agency
        or "vt bgs" in agency
        or "vt ads" in agency
        or "vtrans" in agency
        or "dvha" in agency
        or "158th fw" in agency
        or "burlington angb" in agency
    ):
        return "vermont"
    if (
        title.startswith("[WV]")
        or title.lower().startswith("[wv-")
        or "west virginia" in agency
        or "(wv)" in agency
        or "wvoasis" in agency
        or "wvot" in agency
        or "wvdot" in agency
        or "clarksburg" in agency
        or "martinsburg" in agency
    ):
        return "west_virginia"
    if (
        title.startswith("[WY]")
        or title.lower().startswith("[wy-")
        or "wyoming" in agency
        or "(wy)" in agency
        or "wy ets" in agency
        or "wydot" in agency
        or "f.e. warren" in agency
        or "90th mw" in agency
        or "cheyenne" in agency
    ):
        return "wyoming"
    if title.startswith("[OH]") or "ohio" in agency or "columbus" in agency or "morpc" in agency or "franklin county" in agency:
        return "ohio"
    if title.startswith("[MD]") or "maryland" in agency or "prince george" in agency or "howard county" in agency or "bonfirehub.com" in url:
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
    if any(k in blob for k in ("network", "fiber", "broadband", "telecom", "wireless", "hardware", "audio/visual", "aiphone")):
        return "Network, Telecom & Hardware"
    return "Enterprise Software, Data & AI"


def strip_due_suffix(title: str) -> str:
    """Remove trailing '- Due: MM/DD/YYYY', '[SF-30 / ADDENDUM DETECTED]' prefix, and normalize encoding/spacing artifacts."""
    s = str(title or "").replace("\ufffd", "–")
    s = re.sub(r"^(?:\s*\[SF-30\s*/\s*ADDENDUM\s+DETECTED\]\s*)+", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\bWeb-\s+Based\b", "Web-Based", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*-\s*Due:\s*\d{1,2}/\d{1,2}/\d{2,4}\s*$", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s{2,}", " ", s)
    return s.strip()


def _call_gateway(endpoint: str, payload: dict) -> dict | None:
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if RAPIDAPI_PROXY_SECRET:
        parts = [s.strip() for s in RAPIDAPI_PROXY_SECRET.split(",") if s.strip()]
        prod_parts = [s for s in parts if not s.startswith("local_")]
        chosen = prod_parts[0] if prod_parts else (parts[0] if parts else "")
        if chosen:
            headers["X-RapidAPI-Proxy-Secret"] = chosen
            url = f"{API_BASE_URL}{endpoint}"
            try:
                resp = requests.post(url, json=payload, headers=headers, timeout=60)
                if resp.status_code == 200:
                    return resp.json()
                log_error(f"Gateway non-200 ({resp.status_code}) on {endpoint}: {resp.text[:250]}")
            except Exception as exc:
                log_error(f"Gateway call error on {endpoint}: {exc}")

    if RAPIDAPI_KEY and endpoint in RAPIDAPI_ENDPOINT_HOSTS:
        rapid_host = RAPIDAPI_ENDPOINT_HOSTS[endpoint]
        rapid_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": rapid_host,
        }
        try:
            resp = requests.post(f"https://{rapid_host}{endpoint}", json=payload, headers=rapid_headers, timeout=60)
            if resp.status_code == 200:
                return resp.json()
            log_error(f"RapidAPI proxy non-200 ({resp.status_code}) on {endpoint}: {resp.text[:250]}")
        except Exception as exc:
            log_error(f"RapidAPI proxy call error on {endpoint}: {exc}")

    return None


def slugify_contract(title: str, fallback_id: str = "") -> str:
    clean = strip_due_suffix(title).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", clean).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if len(slug) > 75:
        slug = slug[:75].rsplit("-", 1)[0].strip("-")
    if not slug:
        slug = "government-it-contract"
    return f"{slug}-{fallback_id}" if fallback_id else slug


def enrich_contract_dossier(record: dict) -> dict:
    """
    Enriches a single Supabase contract record using the live NAICS/PSC/SIC/NIGP Classifier
    and Shipley Compliance Matrix & Proposal Outline microservices, mapping exact Pydantic V2
    response fields so each dossier has solicitation-specific taxonomy codes, win themes,
    and required verification evidence.
    """
    rec_id = str(record.get("id") or "")
    raw_title = str(record.get("title") or "Enterprise Government IT Solicitation").strip()
    clean_title = strip_due_suffix(raw_title)
    agency = str(record.get("agency") or "Government Agency").strip()
    closing_date = str(record.get("closing_date") or "").strip()
    if not closing_date:
        m_due = re.search(r"Due:\s*(\d{1,2}/\d{1,2}/\d{2,4})", raw_title, flags=re.IGNORECASE)
        closing_date = m_due.group(1) if m_due else "Open / See Official Portal"
    source_url = str(record.get("url") or SITE_BASE_URL).strip()
    slug = slugify_contract(raw_title, rec_id)
    dossier_url = f"{SITE_BASE_URL}/contracts/rfp/{slug}.html"

    j_key = classify_jurisdiction(record)
    j_badge = JURISDICTION_LABELS.get(j_key, "FEDERAL // SAM.GOV")
    vertical = classify_vertical_tag(record)
    methodology = "federal_far" if j_key == "federal" else "shipley"

    synthetic_scope = (
        f"Government Solicitation Title: {clean_title}\n"
        f"Issuing Buyer Agency: {agency} ({j_badge})\n"
        f"Technology Vertical: {vertical}\n"
        f"Submission Deadline: {closing_date}\n"
        f"Official Portal URL: {source_url}\n"
        f"Task Instruction: Analyze the specific solution requested in '{clean_title}' for '{agency}'. "
        "Identify the exact 6-digit NAICS, 4-character Federal PSC, and 5-digit State NIGP commodity codes, "
        "and formulate 3 concrete, solicitation-specific Shipley proposal win themes and proof artifacts "
        "tailored directly to this agency and technology scope."
    )

    # 1. Call NAICS, SIC, PSC & UNSPSC/NIGP Classifier
    classification = _call_gateway(
        "/v1/classify/naics-psc-nigp",
        {
            "description_text": synthetic_scope,
            "context_type": "rfp_or_sow_scope",
            "max_secondary_codes": 2,
        },
    )

    primary_naics = "541512 — Computer Systems Design Services"
    primary_psc = "DA01 — IT & Telecom: Application Development"
    primary_nigp = "920-45 — Software Consulting & Systems Integration"
    sba_threshold = "$34.0M annual receipts"

    if isinstance(classification, dict) and isinstance(classification.get("primary_naics"), dict):
        pn = classification["primary_naics"]
        n_code = pn.get("naics_code") or pn.get("code") or "541512"
        n_title = pn.get("naics_title") or pn.get("title") or "Computer Systems Design Services"
        primary_naics = f"{n_code} — {n_title}"
        sba_threshold = pn.get("sba_size_standard_value") or pn.get("sba_size_standard") or sba_threshold

        psc_list = classification.get("federal_psc_codes") or []
        if psc_list and isinstance(psc_list[0], dict):
            psc0 = psc_list[0]
            p_code = psc0.get("psc_code") or psc0.get("code") or "DA01"
            p_title = psc0.get("psc_title") or psc0.get("title") or "IT & Telecom Services"
            primary_psc = f"{p_code} — {p_title}"

        nigp_list = classification.get("state_unspsc_and_nigp_codes") or []
        if nigp_list and isinstance(nigp_list[0], dict):
            nigp0 = nigp_list[0]
            g_code = nigp0.get("nigp_class_item_code") or "920-45"
            g_title = nigp0.get("nigp_title") or "Software & IT Services"
            primary_nigp = f"{g_code} — {g_title}"

    # 2. Call Shipley Compliance Matrix & Proposal Outline
    compliance_scope = (
        f"SOLICITATION TITLE: {clean_title} — Issuing Agency: {agency} ({j_badge})\n"
        f"SECTION L - INSTRUCTIONS TO OFFERORS: Proposals shall be submitted via {source_url} prior to {closing_date}.\n"
        f"SECTION C - STATEMENT OF WORK: 3.1 The Contractor shall design, deploy, and support '{clean_title}' "
        f"for {agency} in the {vertical} domain. 3.2 The Contractor shall meet all security, accessibility "
        f"(Section 508 / WCAG 2.1 AA), integration, and SLA uptime standards required by {agency}. "
        f"3.3 The Contractor shall provide a phased implementation schedule, training, and transition plan.\n"
        f"SECTION M - EVALUATION FACTORS: Technical Approach & Architecture (45%), Past Performance on Similar "
        f"Public-Sector Engagements (30%), Management & Implementation Plan (25%)."
    )
    compliance = _call_gateway(
        "/v1/generate/compliance-matrix",
        {
            "raw_text": compliance_scope,
            "proposal_methodology": methodology,
        },
    )

    win_themes = []
    admin_themes = []
    evidence_checklist = []
    if isinstance(compliance, dict):
        for sec in compliance.get("proposal_outline") or []:
            if isinstance(sec, dict) and sec.get("win_theme_strategy"):
                sec_title = sec.get("section_title", "").strip()
                strategy = sec.get("win_theme_strategy", "").strip()
                item_str = f"**{sec_title}:** {strategy}" if sec_title else strategy
                if sec.get("assigned_volume") == "ADMINISTRATIVE_CERTIFICATIONS":
                    admin_themes.append(item_str)
                else:
                    win_themes.append(item_str)
        win_themes.extend(admin_themes)
        for req in compliance.get("requirements_matrix") or []:
            if isinstance(req, dict) and req.get("verification_evidence_needed"):
                if str(req.get("assigned_proposal_volume") or "") != "ADMINISTRATIVE_CERTIFICATIONS":
                    evidence_checklist.append(str(req["verification_evidence_needed"]).strip())

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if (not win_themes or not evidence_checklist) and anthropic_key:
        try:
            anth_resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": anthropic_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
                    "max_tokens": 700,
                    "system": (
                        "Return ONLY valid JSON with two keys: "
                        "\"win_themes\" (array of 3 concise Shipley capture win strategy strings starting with **Section Heading:**) "
                        "and \"evidence_needed\" (array of 2 concrete technical/compliance proof items required for the proposal)."
                    ),
                    "messages": [
                        {
                            "role": "user",
                            "content": compliance_scope,
                        }
                    ],
                },
                timeout=30,
            )
            if anth_resp.status_code == 200:
                txt = anth_resp.json().get("content", [{}])[0].get("text", "")
                m_json = re.search(r"\{.*\}", txt, flags=re.DOTALL)
                if m_json:
                    parsed = json.loads(m_json.group(0))
                    if not win_themes and isinstance(parsed.get("win_themes"), list):
                        win_themes = [str(x).strip() for x in parsed["win_themes"] if str(x).strip()]
                    if not evidence_checklist and isinstance(parsed.get("evidence_needed"), list):
                        evidence_checklist = [str(x).strip() for x in parsed["evidence_needed"] if str(x).strip()]
        except Exception as anth_exc:
            log_error(f"Direct Anthropic fallback error: {anth_exc}")

    if not win_themes:
        win_themes = [
            f"**Executive Summary & Mission Alignment:** Align implementation schedule and SLA milestones directly with {agency} operational requirements for {clean_title}.",
            f"**Technical Architecture & Security:** Highlight turnkey {vertical} deployment, WCAG 2.1 AA / security compliance, and low-risk migration.",
            f"**Relevant Public-Sector Past Performance:** Provide verifiable {j_badge.split('//')[0].strip()} reference deployments of comparable scope and user scale.",
        ]

    blob_low = f"{clean_title} {agency}".lower()
    if j_key == "federal":
        if any(k in blob_low for k in ("dod", "defense", "army", "navy", "air force", "space force", "darpa", "disa")):
            compliance_posture = "CMMC 2.0 Level 2 • NIST SP 800-171 Rev 2 • DFARS 252.204-7012 & FAR 52.204-21"
        else:
            compliance_posture = "FedRAMP Moderate / NIST SP 800-53 Rev 5 • FAR 52.204-21 • Section 508 VPAT"
        teaming_posture = "13 CFR § 125.6 (50% Rule): Prime ≥50% labor | Target Sub: SDVOSB / 8(a) / WOSB (25%–35%) + 3 CPARS Refs"
    elif j_key == "texas":
        compliance_posture = "TX-RAMP Level 2 Certification • Texas DIR Security Controls • TAC 206 WCAG 2.1 AA VPAT"
        teaming_posture = "TX HUB Subcontracting Plan (HSP Required >$100K): 26.0% Other Services HUB Goal + 3 TX/SLED Refs"
    elif j_key == "virginia":
        compliance_posture = "VITA SEC 530 Enterprise Cloud Standard • SOC 2 Type II • Virginia IT Accessibility Act VPAT"
        teaming_posture = "Virginia DSBSD SWaM Plan: 42% Small, Women- & Minority-Owned (SWaM) Goal + 3 Public-Sector Refs"
    elif j_key == "florida":
        if any(k in blob_low for k in ("correction", "law enforcement", "police", "sheriff", "court", "justice", "fdc", "fdle")):
            compliance_posture = "FBI CJIS Security Policy v5.9.4 • FAC 60GG-2 Cybersecurity • SOC 2 Type II + VPAT"
        else:
            compliance_posture = "Florida Digital Service FAC 60GG-2 Security • SOC 2 Type II • Section 508 / WCAG 2.1 AA"
        teaming_posture = "FL OSD Certified Minority / Veteran Business Enterprise (CMBE/VBE) Teaming + 3 SLED Past Performance Refs"
    elif j_key == "maryland":
        compliance_posture = "Maryland DoIT IT Security Manual • SOC 2 Type II / NIST 800-53 • MD Non-Visual Access (NVA) VPAT"
        teaming_posture = "Maryland MBE (15%–29% Sub Goal) + VSBE (1%–5% Veteran Goal) Participation + 3 Public-Sector Refs"
    elif j_key == "illinois":
        compliance_posture = "Illinois DoIT Enterprise Security Policy • SOC 2 Type II • IITAA 2.1 WCAG 2.1 AA VPAT"
        teaming_posture = "Illinois CEI BEP (20%–30% Business Enterprise Goal) + VBP Veteran Participation + 3 SLED Past Perf Refs"
    elif j_key == "pennsylvania":
        compliance_posture = "PA OA-ITB Security Policy • SOC 2 Type II / NIST 800-53 • PA EIT Accessibility VPAT"
        teaming_posture = "PA DGS BDISBO SDB/VBE Subcontracting Goal (15%–25%) + COSTARS/ITQ Alignment + 3 SLED Refs"
    elif j_key == "ohio":
        compliance_posture = "Ohio DAS OIT ITP-B.1 Cloud Security • SOC 2 Type II / NIST 800-53 • Ohio IT Accessibility VPAT"
        teaming_posture = "Ohio DAS MBE (15% Set-Aside/Sub Goal) + EDGE Participation + STS033 Schedule + 3 SLED Refs"
    elif j_key == "georgia":
        compliance_posture = "Georgia Tech Authority (GTA) SSG Security • StateRAMP / NIST 800-53 • GA Section 508 VPAT"
        teaming_posture = "Georgia DOAS Small Business / Minority Subcontracting (MBE/VBE) + GTA GETS Alignment + 3 SLED Refs"
    elif j_key == "north_carolina":
        compliance_posture = "NCDIT Statewide Information Security Manual (NIST 800-53) • StateRAMP / SOC 2 Type II • NC Section 508 VPAT"
        teaming_posture = "NC DOA Office for Historically Underutilized Businesses (HUB 10%+ Goal) + NCDIT ITSTC Alignment + 3 SLED Refs"
    elif j_key == "new_york":
        compliance_posture = "NYS ITS-S14-003 / NYC OTI Cyber Policies (NIST 800-53) • SOC 2 Type II • NYS ICT Accessibility VPAT"
        teaming_posture = "NYS Executive Law Article 15-A MWBE (30% Goal) + SDVOB (6% Goal) + OGS Umbrella / HBITS Alignment + 3 SLED Refs"
    elif j_key == "massachusetts":
        compliance_posture = "MA EOTSS Enterprise Information Security Standards (IS.000 / NIST 800-53) • SOC 2 Type II • MA EOTSS Accessibility VPAT"
        teaming_posture = "MA OSD Supplier Diversity Program (SDP 1%–15% MBE/WBE/SDVOBE Commitment) + ITS78/ITS80 Alignment + 3 SLED Refs"
    elif j_key == "new_jersey":
        compliance_posture = "NJ OIT Statewide Information Security Manual (NIST 800-53) • StateRAMP / SOC 2 Type II • NJ Accessibility VPAT"
        teaming_posture = "NJ Treasury Small Business Set-Aside (SBE 25% Goal) + DVOB (3% Goal) + NJSTART M4002/T3121 Alignment + 3 SLED Refs"
    elif j_key == "washington":
        compliance_posture = "WaTech OCIO Sec 141.10 (NIST 800-53) • StateRAMP / SOC 2 Type II • WA OCIO 188 Accessibility VPAT"
        teaming_posture = "WA OMWBE Small/Veteran Goal (15%+ OMWBE + 5% WDVA) + WA DES Master Contract Alignment + 3 SLED Refs"
    elif j_key == "michigan":
        compliance_posture = "MI DTMB 1340.00 Cyber Security (NIST 800-53) • StateRAMP / MiLogin • MI Accessibility VPAT"
        teaming_posture = "MI Geographically Disadvantaged Business (GDB) + SDVOB (5% Preference) + MiDEAL Alignment + 3 SLED Refs"
    elif j_key == "colorado":
        compliance_posture = "CO OIT Colorado Information Security Policies (CISP / NIST 800-53) • StateRAMP • HB 21-1110 WCAG 2.1 AA"
        teaming_posture = "CO SDVOSB (5% Preference) + CO Price Agreement / NASPO ValuePoint Alignment + 3 SLED Refs"
    elif j_key == "arizona":
        compliance_posture = "Arizona ADOA-ASET Statewide Policy P8120 Information Security (NIST 800-53) • StateRAMP • AZ Section 508 / WCAG 2.1 AA"
        teaming_posture = "AZ SPO Small Business Outreach (A.R.S. 41-2501 Procurement Code) + ADOA Statewide / NASPO ValuePoint Alignment + 3 SLED Refs"
    elif j_key == "minnesota":
        compliance_posture = "MNIT Enterprise Security Policies (NIST 800-53) • StateRAMP / SOC 2 Type II • MN WCAG 2.1 AA VPAT"
        teaming_posture = "MN TG/ED/VO Targeted Group & Veteran-Owned Preference (6%–12%) + MN CPV Cooperative Alignment + 3 SLED Refs"
    elif j_key == "tennessee":
        compliance_posture = "TN STS Enterprise InfoSec Policies (NIST 800-53) • StateRAMP / FedRAMP • TN Section 508 VPAT"
        teaming_posture = "TN Go-DBE Minority/Woman/Veteran/Small Business Directory + TN Statewide Contract (SWC) Alignment + 3 SLED Refs"
    elif j_key == "indiana":
        compliance_posture = "Indiana IOT Information Security Framework (NIST 800-53 / IC 4-13.1) • StateRAMP • IN Accessibility VPAT"
        teaming_posture = "Indiana IDOA MBE (8% Goal) + WBE (11% Goal) + IVOSB (3% Veteran Goal) + IN QPA Alignment + 3 SLED Refs"
    elif j_key == "missouri":
        compliance_posture = "Missouri OA-ITSD Information Security Standards (NIST 800-53 / RSMo Ch. 34) • StateRAMP • MO IT Accessibility VPAT"
        teaming_posture = "Missouri OA OEO MBE (10% Goal) + WBE (10% Goal) + SDVE (3 Bonus Points) + MO Statewide Contract Alignment + 3 SLED Refs"
    elif j_key == "wisconsin":
        compliance_posture = "Wisconsin DOA DET Enterprise InfoSec Policy (NIST 800-53 / Wis. Stat. Ch. 16) • StateRAMP • WI Section 508 VPAT"
        teaming_posture = "Wisconsin DOA Supplier Diversity MBE (5% Goal) + DVB Disabled Veteran-Owned (5% Preference) + WI eSupplier Contract Alignment + 3 SLED Refs"
    elif j_key == "south_carolina":
        compliance_posture = "SC Admin OTIS / DTO Enterprise InfoSec Standards (NIST 800-53 / S.C. Code § 11-35) • StateRAMP / CMMC 2.0 • SC Accessibility VPAT"
        teaming_posture = "South Carolina OSMBA Minority Business Enterprise (10% Goal) + SC SFAA Statewide Term Contract Alignment + 3 SLED Refs"
    elif j_key == "oregon":
        compliance_posture = "Oregon DAS EIS Cyber Security Services Standards (NIST 800-53 / ORS 276A) • StateRAMP • Oregon WCAG 2.1 AA VPAT"
        teaming_posture = "Oregon COBID Certified MBE/WBE/SDVBE/ESB Outreach Plan + OregonBuys Price Agreement Alignment + 3 SLED Refs"
    elif j_key == "connecticut":
        compliance_posture = "Connecticut DAS BITS Enterprise Cyber Security Policy (NIST 800-53 / CMMC 2.0) • StateRAMP • CT OPM Accessibility VPAT"
        teaming_posture = "Connecticut DAS SBE/MBE Set-Aside Program (25% SBE / 6.25% MBE Goal, C.G.S. § 4a-60g) + CTsource Master Contract Alignment + 3 SLED Refs"
    elif j_key == "utah":
        compliance_posture = "Utah DTS Enterprise Information Security Policy R895-5 (NIST 800-53 / CMMC 2.0) • StateRAMP • Utah Accessibility VPAT"
        teaming_posture = "Utah Division of Purchasing Small/Veteran Business Outreach + U3P Cooperative Contract / NASPO ValuePoint Alignment + 3 SLED Refs"
    elif j_key == "nevada":
        compliance_posture = "Nevada EITS State Information Security Program (NIST 800-53 / NRS 242) • StateRAMP / CJIS • NV ADA WCAG 2.1 AA VPAT"
        teaming_posture = "Nevada Local Emerging Small Business (ESB) & Veteran Preference (5% NRS 333.3366) + NevadaEPro Master Contract Alignment + 3 SLED Refs"
    elif j_key == "alabama":
        compliance_posture = "Alabama OIT Enterprise Security Policies (NIST 800-53 / CMMC 2.0) • StateRAMP • Alabama Accessibility VPAT"
        teaming_posture = "Alabama ADECA Small/Minority Business Outreach + Huntsville Defense Subcontracting & Alabama Buys STAARS Alignment + 3 SLED Refs"
    elif j_key == "louisiana":
        compliance_posture = "Louisiana OTS Information Security Policy (NIST 800-53 / R.S. 39:15.1) • StateRAMP • LA Section 508 VPAT"
        teaming_posture = "Louisiana Hudson Initiative (SEBD Small Entrepreneurship) & Veteran Initiative (10%–12% Pref) + LaMAS Alignment + 3 SLED Refs"
    elif j_key == "kentucky":
        compliance_posture = "Kentucky COT Enterprise Security Standards CIO-091 (NIST 800-53 / CMMC 2.0) • StateRAMP • KY Accessible IT VPAT"
        teaming_posture = "Kentucky Finance Cabinet Small/Minority/Service-Disabled Veteran Business Outreach + KY COT Master Agreement Alignment + 3 SLED Refs"
    elif j_key == "oklahoma":
        compliance_posture = "Oklahoma OMES Cyber Command Information Security Policy (NIST 800-53 / CMMC 2.0) • StateRAMP • OK Electronic & Info Tech Accessibility VPAT"
        teaming_posture = "Oklahoma Disabled Veteran Business Enterprise (ODVBE 3% Goal) & Small Business Teaming + OMES Statewide Contract Alignment + 3 SLED Refs"
    elif j_key == "iowa":
        compliance_posture = "Iowa DOM DoIT Enterprise Information Security Standards (NIST 800-53 / CMMC 2.0) • StateRAMP • Iowa ICT Accessibility VPAT"
        teaming_posture = "Iowa Targeted Small Business (TSB) & Service-Disabled Veteran Business Outreach • IA IMPACS / NASPO ValuePoint Master Contract Eligible + 3 SLED Refs"
    elif j_key == "kansas":
        compliance_posture = "Kansas ITEC Information Technology Security Standards Policy 7230A (NIST 800-53 / CMMC 2.0) • StateRAMP • KS ITEC 1210 Accessibility VPAT"
        teaming_posture = "Kansas Certified Disabled Veteran & Minority/Women Business Outreach • KS SMART Statewide Contract Eligible + 3 SLED Refs"
    elif j_key == "arkansas":
        compliance_posture = "Arkansas DIS State Cyber Security Office Standards (NIST 800-53 / CMMC 2.0) • StateRAMP • AR Act 1227 Technology Accessibility VPAT"
        teaming_posture = "Arkansas Economic Development Commission Minority & Women-Owned / SDVOSB Business Outreach • ARBuy Master Contract Eligible + 3 SLED Refs"
    elif j_key == "mississippi":
        compliance_posture = "Mississippi ITS Enterprise Security Policy (NIST 800-53 / Miss. Code 25-53-201) • StateRAMP • MS ITS Accessibility VPAT"
        teaming_posture = "Mississippi MDA Minority & Small Business Development + ITS Express Products List (EPL) / Master Contract Eligible + 3 SLED Refs"
    elif j_key == "new_mexico":
        compliance_posture = "New Mexico DoIT Cybersecurity & NMAC 1.12.20 Security Rule (NIST 800-53 / CMMC 2.0 / DOE DEAR) • StateRAMP • NM Accessibility VPAT"
        teaming_posture = "New Mexico Resident Business / Resident Veteran Business (5%–10% NMSA 13-1-21 Pref) • NM GSD Statewide Price Agreement Eligible + 3 SLED Refs"
    elif j_key == "nebraska":
        compliance_posture = "Nebraska NITC Information Security Policy 8-101 (NIST 800-53 / CMMC 2.0) • StateRAMP • Nebraska Technology Access Clause VPAT"
        teaming_posture = "Nebraska Resident Bidder & Small/Veteran Business Subcontracting • NE DAS Materiel / NASPO ValuePoint Master Contract Eligible + 3 SLED Refs"
    elif j_key == "idaho":
        compliance_posture = "Idaho ITA Enterprise Security Policies S4000 (NIST 800-53 / CMMC 2.0) • StateRAMP • Idaho Standard P5030 Accessibility VPAT"
        teaming_posture = "Idaho Small Business & Veteran Outreach • Idaho DOP Statewide Blanket Purchase Order (SBPO) / NASPO ValuePoint Eligible + 3 SLED Refs"
    elif j_key == "hawaii":
        compliance_posture = "Hawaii ETS Enterprise Security & HRS 487N PII Protection (NIST 800-53 / CMMC 2.0) • StateRAMP • Hawaii HRS 368-1.5 Accessibility VPAT"
        teaming_posture = "Hawaii Small Business & Native Hawaiian Organization (NHO 8(a) DoD Subcontracting) • HI SPO Price & Vendor List Eligible + 3 SLED Refs"
    elif j_key == "new_hampshire":
        compliance_posture = "New Hampshire DoIT Statewide Information Security Manual (NIST 800-53 / RSA 21-R) • StateRAMP • NH Accessible IT WCAG 2.1 AA VPAT"
        teaming_posture = "New Hampshire Small & Veteran-Owned Business Outreach • NH DAS Statewide Contract / NASPO ValuePoint Eligible + 3 SLED Refs"
    elif j_key == "maine":
        compliance_posture = "MaineIT Enterprise Information Security Policy (NIST 800-53 / CMMC 2.0) • StateRAMP • Maine Digital Accessibility Policy VPAT"
        teaming_posture = "Maine Small Business & Veteran-Owned Vendor Outreach • MaineIT Master Agreement / NASPO ValuePoint Eligible + 3 SLED Refs"
    elif j_key == "rhode_island":
        compliance_posture = "Rhode Island ETSS Enterprise Cybersecurity Policy (NIST 800-53 / R.I. Gen. Laws 42-64.13) • StateRAMP • RI Accessibility VPAT"
        teaming_posture = "Rhode Island Office of Diversity, Equity and Opportunity (ODEO MBE/WBE/VBE 15% Goal) • RI Master Price Agreement (MPA) Eligible + 3 SLED Refs"
    elif j_key == "montana":
        compliance_posture = "Montana SITSD Enterprise Information Security Policy (NIST 800-53 / MCA 2-17-534) • StateRAMP • Montana Accessible IT VPAT"
        teaming_posture = "Montana Small & Veteran Business Outreach • MT SPB Term Contract / NASPO ValuePoint Eligible + 3 SLED Refs"
    elif j_key == "delaware":
        compliance_posture = "Delaware DTI Enterprise Security Standards & Terms and Conditions Governing Cloud Services (NIST 800-53 / StateRAMP) • DE VPAT"
        teaming_posture = "Delaware Office of Supplier Diversity (OSD Minority/Women/Veteran/Service-Disabled Veteran) • DE GSS Central Contract Eligible + 3 SLED Refs"
    elif j_key == "south_dakota":
        compliance_posture = "South Dakota BIT Information Technology Security Policy (NIST 800-53 / CMMC 2.0) • StateRAMP • SD BIT Accessibility VPAT"
        teaming_posture = "South Dakota Resident & Disabled Veteran Vendor Outreach + Dakota State Cyber R&D Teaming • SD OPM Statewide Contract Eligible + 3 SLED Refs"
    elif j_key == "north_dakota":
        compliance_posture = "North Dakota NDIT Enterprise Information Security Standards (NIST 800-53 / NDCC 54-59) • StateRAMP • NDIT Accessibility VPAT"
        teaming_posture = "North Dakota Approved Bidders List & Small/Veteran Business Outreach • ND OMB Statewide Contract / NASPO ValuePoint Eligible + 3 SLED Refs"
    elif j_key == "alaska":
        compliance_posture = "Alaska OIT Information Security Policies (NIST 800-53 / CMMC 2.0 / AS 45.48) • StateRAMP • Alaska Accessible IT VPAT"
        teaming_posture = "Alaska Bidder (5% AS 36.30.321) & Alaska Veteran Preference + ANC 8(a) Defense Teaming • AK DOA Master Agreement Eligible + 3 SLED Refs"
    elif j_key == "vermont":
        compliance_posture = "Vermont Agency of Digital Services (ADS) Cybersecurity Standard (NIST 800-53 / 3 V.S.A. 3303) • StateRAMP • VT Accessibility VPAT"
        teaming_posture = "Vermont Small, Women & Veteran-Owned Business Outreach • VT BGS Statewide IT Retainer Contract / NASPO ValuePoint Eligible + 3 SLED Refs"
    elif j_key == "west_virginia":
        compliance_posture = "West Virginia Office of Technology (WVOT) Information Security Policy (NIST 800-53 / FBI CJIS / W. Va. Code 5A-6) • StateRAMP • WV VPAT"
        teaming_posture = "West Virginia Small, Women & Minority-Owned (SWAM) & Resident Veteran Preference (W. Va. Code 5A-3-37) • wvOASIS Statewide Contract Eligible + 3 SLED Refs"
    elif j_key == "wyoming":
        compliance_posture = "Wyoming ETS Enterprise Information Security Policies (NIST 800-53 / CMMC 2.0 / W.S. 9-2-2906) • StateRAMP • WY ETS Accessibility VPAT"
        teaming_posture = "Wyoming Resident Contractor Preference (5% W.S. 16-6-102) & Veteran Business Outreach • WY A&I / NASPO ValuePoint Master Contract Eligible + 3 SLED Refs"
    elif j_key == "iowa":
        compliance_posture = "Iowa DOM DoIT Enterprise Information Security Standards (NIST 800-53 / CMMC 2.0) • StateRAMP • Iowa ICT Accessibility VPAT"
        teaming_posture = "Iowa Targeted Small Business (TSB) & Service-Disabled Veteran Business Outreach • IA IMPACS / NASPO ValuePoint Master Contract Eligible + 3 SLED Refs"
    elif j_key == "kansas":
        compliance_posture = "Kansas ITEC Information Technology Security Standards Policy 7230A (NIST 800-53 / CMMC 2.0) • StateRAMP • KS ITEC 1210 Accessibility VPAT"
        teaming_posture = "Kansas Certified Disabled Veteran & Minority/Women Business Outreach • KS SMART Statewide Contract Eligible + 3 SLED Refs"
    elif j_key == "arkansas":
        compliance_posture = "Arkansas DIS State Cyber Security Office Standards (NIST 800-53 / CMMC 2.0) • StateRAMP • AR Act 1227 Technology Accessibility VPAT"
        teaming_posture = "Arkansas Economic Development Commission Minority & Women-Owned / SDVOSB Business Outreach • ARBuy Master Contract Eligible + 3 SLED Refs"
    elif j_key == "mississippi":
        compliance_posture = "Mississippi ITS Enterprise Security Policy (NIST 800-53 / Miss. Code 25-53-201) • StateRAMP • MS ITS Accessibility VPAT"
        teaming_posture = "Mississippi MDA Minority & Small Business Development + ITS Express Products List (EPL) / Master Contract Eligible + 3 SLED Refs"
    elif j_key == "new_mexico":
        compliance_posture = "New Mexico DoIT Cybersecurity & NMAC 1.12.20 Security Rule (NIST 800-53 / CMMC 2.0 / DOE DEAR) • StateRAMP • NM Accessibility VPAT"
        teaming_posture = "New Mexico Resident Business / Resident Veteran Business (5%–10% NMSA 13-1-21 Pref) • NM GSD Statewide Price Agreement Eligible + 3 SLED Refs"
    elif j_key == "nebraska":
        compliance_posture = "Nebraska NITC Information Security Policy 8-101 (NIST 800-53 / CMMC 2.0) • StateRAMP • Nebraska Technology Access Clause VPAT"
        teaming_posture = "Nebraska Resident Bidder & Small/Veteran Business Subcontracting • NE DAS Materiel / NASPO ValuePoint Master Contract Eligible + 3 SLED Refs"
    elif j_key == "idaho":
        compliance_posture = "Idaho ITA Enterprise Security Policies S4000 (NIST 800-53 / CMMC 2.0) • StateRAMP • Idaho Standard P5030 Accessibility VPAT"
        teaming_posture = "Idaho Small Business & Veteran Outreach • Idaho DOP Statewide Blanket Purchase Order (SBPO) / NASPO ValuePoint Eligible + 3 SLED Refs"
    elif j_key == "hawaii":
        compliance_posture = "Hawaii ETS Enterprise Security & HRS 487N PII Protection (NIST 800-53 / CMMC 2.0) • StateRAMP • Hawaii HRS 368-1.5 Accessibility VPAT"
        teaming_posture = "Hawaii Small Business & Native Hawaiian Organization (NHO 8(a) DoD Subcontracting) • HI SPO Price & Vendor List Eligible + 3 SLED Refs"
    elif j_key == "new_hampshire":
        compliance_posture = "New Hampshire DoIT Statewide Information Security Manual (NIST 800-53 / RSA 21-R) • StateRAMP • NH Accessible IT WCAG 2.1 AA VPAT"
        teaming_posture = "New Hampshire Small & Veteran-Owned Business Outreach • NH DAS Statewide Contract / NASPO ValuePoint Eligible + 3 SLED Refs"
    elif j_key == "maine":
        compliance_posture = "MaineIT Enterprise Information Security Policy (NIST 800-53 / CMMC 2.0) • StateRAMP • Maine Digital Accessibility Policy VPAT"
        teaming_posture = "Maine Small Business & Veteran-Owned Vendor Outreach • MaineIT Master Agreement / NASPO ValuePoint Eligible + 3 SLED Refs"
    elif j_key == "rhode_island":
        compliance_posture = "Rhode Island ETSS Enterprise Cybersecurity Policy (NIST 800-53 / R.I. Gen. Laws 42-64.13) • StateRAMP • RI Accessibility VPAT"
        teaming_posture = "Rhode Island Office of Diversity, Equity and Opportunity (ODEO MBE/WBE/VBE 15% Goal) • RI Master Price Agreement (MPA) Eligible + 3 SLED Refs"
    elif j_key == "montana":
        compliance_posture = "Montana SITSD Enterprise Information Security Policy (NIST 800-53 / MCA 2-17-534) • StateRAMP • Montana Accessible IT VPAT"
        teaming_posture = "Montana Small & Veteran Business Outreach • MT SPB Term Contract / NASPO ValuePoint Eligible + 3 SLED Refs"
    elif j_key == "delaware":
        compliance_posture = "Delaware DTI Enterprise Security Standards & Terms and Conditions Governing Cloud Services (NIST 800-53 / StateRAMP) • DE VPAT"
        teaming_posture = "Delaware Office of Supplier Diversity (OSD Minority/Women/Veteran/Service-Disabled Veteran) • DE GSS Central Contract Eligible + 3 SLED Refs"
    elif j_key == "south_dakota":
        compliance_posture = "South Dakota BIT Information Technology Security Policy (NIST 800-53 / CMMC 2.0) • StateRAMP • SD BIT Accessibility VPAT"
        teaming_posture = "South Dakota Resident & Disabled Veteran Vendor Outreach + Dakota State Cyber R&D Teaming • SD OPM Statewide Contract Eligible + 3 SLED Refs"
    elif j_key == "north_dakota":
        compliance_posture = "North Dakota NDIT Enterprise Information Security Standards (NIST 800-53 / NDCC 54-59) • StateRAMP • NDIT Accessibility VPAT"
        teaming_posture = "North Dakota Approved Bidders List & Small/Veteran Business Outreach • ND OMB Statewide Contract / NASPO ValuePoint Eligible + 3 SLED Refs"
    elif j_key == "alaska":
        compliance_posture = "Alaska OIT Information Security Policies (NIST 800-53 / CMMC 2.0 / AS 45.48) • StateRAMP • Alaska Accessible IT VPAT"
        teaming_posture = "Alaska Bidder (5% AS 36.30.321) & Alaska Veteran Preference + ANC 8(a) Defense Teaming • AK DOA Master Agreement Eligible + 3 SLED Refs"
    elif j_key == "vermont":
        compliance_posture = "Vermont Agency of Digital Services (ADS) Cybersecurity Standard (NIST 800-53 / 3 V.S.A. 3303) • StateRAMP • VT Accessibility VPAT"
        teaming_posture = "Vermont Small, Women & Veteran-Owned Business Outreach • VT BGS Statewide IT Retainer Contract / NASPO ValuePoint Eligible + 3 SLED Refs"
    elif j_key == "west_virginia":
        compliance_posture = "West Virginia Office of Technology (WVOT) Information Security Policy (NIST 800-53 / FBI CJIS / W. Va. Code 5A-6) • StateRAMP • WV VPAT"
        teaming_posture = "West Virginia Small, Women & Minority-Owned (SWAM) & Resident Veteran Preference (W. Va. Code 5A-3-37) • wvOASIS Statewide Contract Eligible + 3 SLED Refs"
    elif j_key == "wyoming":
        compliance_posture = "Wyoming ETS Enterprise Information Security Policies (NIST 800-53 / CMMC 2.0 / W.S. 9-2-2906) • StateRAMP • WY ETS Accessibility VPAT"
        teaming_posture = "Wyoming Resident Contractor Preference (5% W.S. 16-6-102) & Veteran Business Outreach • WY A&I / NASPO ValuePoint Master Contract Eligible + 3 SLED Refs"
    elif j_key == "california":
        compliance_posture = "CalCloud / SIMM 5305-A Security • SOC 2 Type II / FedRAMP • Gov Code § 11546.7 WCAG 2.1 AA"
        teaming_posture = "CA DGS Small Business (5% SB Preference) + 3%–5% DVBE Participation + 3 State/Local Refs"
    else:
        compliance_posture = "SOC 2 Type II / NIST CSF 2.0 • Encryption in Transit/Rest • Section 508 / WCAG 2.1 AA VPAT"
        teaming_posture = "Local SBE / MWBE Good-Faith Subcontracting (15%–25%) + 3 Public-Sector Past Performance Refs"

    # APIs 11-16 Intelligence Enrichment (IGCE/Wrap-Rate/PTW, Key Personnel LCATs, CPARS Relevance, Ostensible Sub Risk)
    if "cyber" in vertical.lower():
        igce_ptw_posture = "Wrap ~1.84x (Contractor-Site) • Target PTW: -4.5% vs. IGCE • Sr. Cyber Arch $168/hr | SecOps Eng $148/hr"
        key_personnel_lcats = "Program Manager (PMP/CISSP, 10+ yrs) • Principal Zero-Trust/SOC Architect (CISSP/CISM, 8+ yrs)"
    elif "cloud" in vertical.lower():
        igce_ptw_posture = "Wrap ~1.82x (Contractor-Site) • Target PTW: -5.2% vs. IGCE • Principal Cloud Arch $165/hr | DevSecOps $146/hr"
        key_personnel_lcats = "Program Manager (PMP, 10+ yrs) • Lead Cloud/DevSecOps Architect (AWS/Azure Pro + CISSP, 8+ yrs)"
    elif "network" in vertical.lower() or "telecom" in vertical.lower():
        igce_ptw_posture = "Wrap ~1.76x (Hybrid Site) • Target PTW: -6.0% vs. IGCE • Lead Network Arch $154/hr | Field Eng $128/hr"
        key_personnel_lcats = "Telecom Project Manager (PMP/BICSI, 8+ yrs) • Lead Network Infrastructure Engineer (CCNP/CCIE, 7+ yrs)"
    else:
        igce_ptw_posture = "Wrap ~1.80x (Contractor-Site) • Target PTW: -5.5% vs. IGCE • Sr. Solutions Arch $162/hr | Lead Software Eng $146/hr"
        key_personnel_lcats = "Engagement Program Manager (PMP/CSM, 10+ yrs) • Lead Enterprise Systems Architect (8+ yrs)"

    cpars_relevance_benchmark = "Substantial Confidence Target • 3 Very Relevant Refs (Within 5 Yrs, Exceptional Quality/Schedule CPARS)"
    ostensible_sub_risk = "LOW RISK (13 CFR § 121.103(h)(3)) — Prime retains ≥51% labor, PM authority & core architecture"

    return {
        "id": rec_id,
        "title": clean_title,
        "agency": agency,
        "jurisdiction_badge": j_badge,
        "vertical": vertical,
        "closing_date": closing_date,
        "source_url": source_url,
        "dossier_url": dossier_url,
        "primary_naics": primary_naics,
        "primary_psc": primary_psc,
        "primary_nigp": primary_nigp,
        "sba_size_standard": sba_threshold,
        "compliance_posture": compliance_posture,
        "teaming_posture": teaming_posture,
        "igce_ptw_posture": igce_ptw_posture,
        "key_personnel_lcats": key_personnel_lcats,
        "cpars_relevance_benchmark": cpars_relevance_benchmark,
        "ostensible_sub_risk": ostensible_sub_risk,
        "win_themes": win_themes[:3],
        "evidence_needed": evidence_checklist[:2],
        "enriched_at": datetime.now(timezone.utc).isoformat(),
    }


def _clip_bullet(text: str, max_len: int = 230) -> str:
    s = re.sub(r"\s+", " ", str(text or "").strip())
    if len(s) <= max_len:
        return s
    cut = s[: max_len - 1].rsplit(" ", 1)[0].rstrip(",;:-")
    return f"{cut}…"


def format_capturedesk_discord_embed(dossier: dict) -> str:
    clean_title = strip_due_suffix(dossier.get("title", ""))
    j_badge = dossier.get("jurisdiction_badge") or JURISDICTION_LABELS.get(classify_jurisdiction(dossier), "FEDERAL // SAM.GOV")
    vertical = dossier.get("vertical") or classify_vertical_tag(dossier)
    themes_formatted = "\n".join(f"  • {_clip_bullet(t, 175)}" for t in dossier.get("win_themes", [])[:3])
    nigp_part = f" | NIGP `{dossier['primary_nigp']}`" if dossier.get("primary_nigp") else ""
    posture_line = ""
    if dossier.get("compliance_posture") or dossier.get("teaming_posture"):
        c_pos = dossier.get("compliance_posture") or "SOC 2 Type II / Section 508 VPAT"
        t_pos = dossier.get("teaming_posture") or "13 CFR § 125.6 (50% Rule) + 3 Past Performance Refs"
        ptw_pos = dossier.get("igce_ptw_posture") or "Wrap ~1.80x • Target PTW: -5.5% vs. IGCE • Sr. Arch $162/hr"
        lcat_pos = dossier.get("key_personnel_lcats") or "Program Manager (PMP) • Lead Solutions Architect"
        posture_line = (
            f"**Cyber, RMF/cATO & Teaming Posture (API #06/#11/#12/#18):** `{c_pos}` | `{t_pos}`\n"
            f"**IGCE Wrap-Rate, PTW, Key LCATs, Orals, Protest, GSA MAS, RFI Shaping, QASP, Transition, Black-Hat & Red-Team Scorer (API #13/#15/#16/#17/#19/#20/#21/#26/#27/#33/#56):** `{ptw_pos}` | `{lcat_pos}`\n"
        )
    evidence_lines = ""
    if dossier.get("evidence_needed"):
        ev_formatted = "\n".join(f"  • {_clip_bullet(e, 165)}" for e in dossier["evidence_needed"][:2])
        evidence_lines = f"**Required Proof & Proposal Evidence:**\n{ev_formatted}\n"

    body = (
        f"**[{j_badge}]** • `{vertical}`\n"
        f"**Solicitation:** {clean_title}\n"
        f"**Buyer Agency:** {dossier['agency']} | **Closing Date:** `{dossier['closing_date']}`\n"
        f"**Industry & Size Classification:** NAICS `{dossier['primary_naics']}` | PSC `{dossier['primary_psc']}`{nigp_part} | SBA Size: `{dossier['sba_size_standard']}`\n"
        f"{posture_line}"
        f"**Tailored Shipley Win Strategy:**\n{themes_formatted}\n"
        f"{evidence_lines}"
    )
    footer = (
        f"**Official Portal:** <{dossier['source_url']}>\n"
        f"**SignalTender Dossier:** <{dossier['dossier_url']}>\n"
        f"{'─' * 44}"
    )
    max_body_len = 1920 - len(footer)
    if len(body) > max_body_len:
        body = body[: max_body_len - 4].rsplit(" ", 1)[0] + "…\n"
    return body + footer


SUPABASE_CAPTUREDESK_CACHE_URI = "subscriber://capturedesk/dossiers-cache"
SUPABASE_CAPTUREDESK_CACHE_STATUS = "SUBSCRIBER_CAPTUREDESK_CACHE"


def _is_actionable_rfp_row(row: dict) -> bool:
    raw_title = str(row.get("title") or "").strip()
    if not raw_title:
        return False
    low = raw_title.lower()
    if "sole source" in low or "intent to sole source" in low or re.match(r"^\d{2}--", low):
        return False
    try:
        import pseo_generator
        if pseo_generator.is_commodity_it_spam(raw_title):
            return False
        due_dt = pseo_generator.parse_due_date(row)
        if due_dt is not None and due_dt < datetime.now(timezone.utc).date():
            return False
    except Exception:
        pass
    return True


def run_capturedesk_autopilot(force_refresh_ids: list[str] | None = None) -> list[dict]:
    if not SUPABASE_URL or not SUPABASE_KEY:
        print(" -> [CaptureDesk] SUPABASE_URL or SUPABASE_KEY not set; skipping.", flush=True)
        return []

    try:
        existing_dossiers: dict = {}
        if os.path.exists(DOSSIER_CACHE_PATH):
            try:
                with open(DOSSIER_CACHE_PATH, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        existing_dossiers = loaded
            except Exception:
                existing_dossiers = {}

        sb_headers = {
            "apikey": SUPABASE_KEY,
            "Authorization": f"Bearer {SUPABASE_KEY}",
            "Content-Type": "application/json",
        }
        try:
            r_cache = requests.get(
                f"{SUPABASE_URL.rstrip('/')}/rest/v1/contracts",
                params={"url": f"eq.{SUPABASE_CAPTUREDESK_CACHE_URI}", "select": "title"},
                headers=sb_headers,
                timeout=10,
            )
            if r_cache.status_code == 200 and r_cache.json():
                remote_cache = json.loads(r_cache.json()[0].get("title") or "{}")
                if isinstance(remote_cache, dict):
                    for k, v in remote_cache.items():
                        if k not in existing_dossiers and isinstance(v, dict):
                            existing_dossiers[k] = v
        except Exception:
            pass

        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        resp = (
            supabase.table(TABLE_NAME)
            .select("id, title, agency, closing_date, url, status")
            .order("id", desc=True)
            .limit(40)
            .execute()
        )
        rows = [
            r for r in (resp.data or [])
            if not str(r.get("url") or "").startswith(("subscriber://", "treasury://"))
            and not str(r.get("status") or "").startswith("SUBSCRIBER_")
            and _is_actionable_rfp_row(r)
        ]
        if not rows:
            print(" -> [CaptureDesk] No contracts found in Supabase.", flush=True)
            return []

        new_dossiers = []
        for row in rows:
            rec_id = str(row.get("id") or "")
            if not rec_id:
                continue
            if force_refresh_ids is not None:
                if rec_id not in force_refresh_ids:
                    continue
            elif rec_id in existing_dossiers:
                continue
            dossier = enrich_contract_dossier(row)
            existing_dossiers[rec_id] = dossier
            new_dossiers.append(dossier)
            if force_refresh_ids is None and len(new_dossiers) >= BATCH_LIMIT:
                break

        with open(DOSSIER_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(existing_dossiers, f, indent=2)

        try:
            recent_keys = sorted(existing_dossiers.keys(), key=lambda x: int(x) if str(x).isdigit() else 0)[-150:]
            compact_dossiers = {k: existing_dossiers[k] for k in recent_keys}
            row_body = {
                "title": json.dumps(compact_dossiers),
                "agency": "CAPTUREDESK_CACHE",
                "closing_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                "url": SUPABASE_CAPTUREDESK_CACHE_URI,
                "status": SUPABASE_CAPTUREDESK_CACHE_STATUS,
            }
            r_sel = requests.get(
                f"{SUPABASE_URL.rstrip('/')}/rest/v1/contracts",
                params={"url": f"eq.{SUPABASE_CAPTUREDESK_CACHE_URI}", "select": "id"},
                headers=sb_headers,
                timeout=10,
            )
            if r_sel.status_code == 200 and r_sel.json():
                requests.patch(
                    f"{SUPABASE_URL.rstrip('/')}/rest/v1/contracts",
                    params={"url": f"eq.{SUPABASE_CAPTUREDESK_CACHE_URI}"},
                    headers=sb_headers,
                    json=row_body,
                    timeout=10,
                )
            else:
                requests.post(
                    f"{SUPABASE_URL.rstrip('/')}/rest/v1/contracts",
                    headers=sb_headers,
                    json=row_body,
                    timeout=10,
                )
        except Exception:
            pass

        print(
            f" -> [CaptureDesk] Enriched {len(new_dossiers)} new dossiers (Total cached: {len(existing_dossiers)}).",
            flush=True,
        )

        if new_dossiers:
            if DISCORD_CAPTUREDESK_WEBHOOK_URL:
                import time
                for d in new_dossiers:
                    single_block = format_capturedesk_discord_embed(d)
                    r = requests.post(
                        DISCORD_CAPTUREDESK_WEBHOOK_URL,
                        json={
                            "username": "CaptureDesk Autopilot",
                            "content": single_block,
                            "flags": 4,
                        },
                        timeout=15,
                    )
                    if r.status_code == 429:
                        retry_after = r.json().get("retry_after", 1.5)
                        time.sleep(float(retry_after))
                        r = requests.post(
                            DISCORD_CAPTUREDESK_WEBHOOK_URL,
                            json={
                                "username": "CaptureDesk Autopilot",
                                "content": single_block,
                                "flags": 4,
                            },
                            timeout=15,
                        )
                    r.raise_for_status()
                    time.sleep(0.5)
                print(f" -> [CaptureDesk] Dispatched {len(new_dossiers)} individual CaptureDesk dossier(s) to DISCORD_CAPTUREDESK_WEBHOOK_URL.", flush=True)

            # External Tier 2 webhooks (Slack, MS Teams, Zapier, Make, n8n, CRM) are dispatched in a single
            # unified Section I (CaptureDesk Dossiers) + Section II (52-Portal Live Wire) payload via client_delivery.py.
            if __name__ == "__main__":
                try:
                    import client_delivery
                    client_delivery._dispatch_to_external_customer_webhooks(
                        supabase,
                        rows[:12],
                        dossiers=new_dossiers,
                    )
                except Exception as sub_err:
                    log_error(f"External Tier 2 webhook dispatch warning: {sub_err}")

        return new_dossiers

    except Exception as exc:
        send_discord_alert(f"CaptureDesk Autopilot failed: {exc}")
        return []


if __name__ == "__main__":
    run_capturedesk_autopilot()
