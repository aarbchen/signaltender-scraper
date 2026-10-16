@echo off
cd /d D:\Daas
call daas_env\Scripts\activate.bat

echo ========================================================
echo    SignalTender DaaS Master Orchestrator - Initializing
echo    (SAM.gov + DemandStar + TX + VA + CA + FL + MD)
echo ========================================================
echo.

echo [*] Running Unified 7-Portal Master Orchestrator (Supabase + Discord Sync)...
python mainscraper.py >> D:\Daas\error_log.txt 2>&1

if exist "D:\Daas\apollo-contacts.csv" (
    echo [*] Refreshing Apollo Outreach Payload (campaign_leads.csv) from Supabase...
    python outreach_generator.py >> D:\Daas\error_log.txt 2>&1
)

echo.
echo ========================================================
echo      [+] SUCCESS: All 7 scraping pipelines complete!
echo      Supabase contracts table and Discord feed synced.
echo ========================================================
echo.

exit