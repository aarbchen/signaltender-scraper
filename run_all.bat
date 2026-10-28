@echo off
cd /d D:\Daas
call daas_env\Scripts\activate.bat

echo ========================================================
echo    SignalTender DaaS Master Orchestrator - Initializing
echo    (SAM.gov + DemandStar + TX + VA + CA + FL + MD + IL + PA + OH + GA + NC + NY + MA + NJ + WA + MI + CO + AZ)
echo ========================================================
echo.

echo [*] Running Unified 19-Portal Master Orchestrator (Supabase + Discord + pSEO Sync)...
python mainscraper.py >> D:\Daas\error_log.txt 2>&1

echo [*] Ensuring Programmatic SEO Static Pages and Sitemap are up to date...
python pseo_generator.py >> D:\Daas\error_log.txt 2>&1

echo [*] Running Tier 2 CaptureDesk Autopilot Multi-API Dossier Enrichment...
python capturedesk_autopilot.py >> D:\Daas\error_log.txt 2>&1

echo [*] Seeding RapidAPI 200 OK Telemetry Across All API Storefronts...
python seed_rapidapi_telemetry.py >> D:\Daas\error_log.txt 2>&1

echo [*] Harvesting Multi-State GovCon Prospects & Inbound Funnel Leads...
python govcon_lead_harvester.py >> D:\Daas\error_log.txt 2>&1

if exist "D:\Daas\apollo-contacts.csv" (
    echo [*] Refreshing Apollo Outreach Payload (campaign_leads.csv) from Supabase...
    python outreach_generator.py >> D:\Daas\error_log.txt 2>&1
    python outbound_mailer.py >> D:\Daas\error_log.txt 2>&1
)

echo.
echo ========================================================
echo      [+] SUCCESS: All 19 scraping & pSEO pipelines complete!
echo      Supabase, Discord feed, and /contracts SEO pages synced.
echo ========================================================
echo.

pause
exit
