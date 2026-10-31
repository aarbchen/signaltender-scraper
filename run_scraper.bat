@echo off
cd /d D:\Daas
call daas_env\Scripts\activate.bat

echo ========================================================
echo    SignalTender DaaS Master Orchestrator - Initializing
echo    (SAM.gov + DemandStar + TX + VA + CA + FL + MD + IL + PA + OH + GA + NC + NY + MA + NJ + WA + MI + CO + AZ + MN + TN + IN + MO + WI + SC + OR + CT + UT + NV + AL + LA + KY + OK + IA + KS + AR + MS + NM + NE + ID + HI + NH + ME + RI + MT + DE + SD + ND + AK + VT + WV + WY)
echo ========================================================
echo.

echo [*] Running Unified 52-Portal Master Orchestrator (Supabase + Discord + pSEO Sync)...
python mainscraper.py >> D:\Daas\pipeline_run.log 2>&1

echo [*] Ensuring Programmatic SEO Static Pages and Sitemap are up to date...
python pseo_generator.py >> D:\Daas\pipeline_run.log 2>&1

if exist "D:\Daas\govcon_prospects.csv" (
    echo [*] Refreshing Outbound Outreach Payload (campaign_leads.csv & outbox_ready_queue.json) from Supabase...
    python outreach_generator.py >> D:\Daas\pipeline_run.log 2>&1
) else if exist "D:\Daas\apollo-contacts.csv" (
    echo [*] Refreshing Apollo Outreach Payload (campaign_leads.csv) from Supabase...
    python outreach_generator.py >> D:\Daas\pipeline_run.log 2>&1
)

echo.
echo ========================================================
echo      [+] SUCCESS: All 52 scraping & pSEO pipelines complete!
echo      Supabase, Discord feed, and /contracts SEO pages synced.
echo ========================================================
echo.

exit
