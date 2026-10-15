Project Rules File (project\_rules.md)



Core Stack: Python 3, playwright.async\_api, playwright\_stealth, pyairtable.



Scraping Protocols:



All scrapers must use asyncio.



SLED/Commercial sites require the Decodo residential proxy format (us.decodo.com:10000/10001).



Federal (.gov) sites strictly bypass proxies and use a direct connection to avoid Akamai/Cloudflare tarpitting.



Error Handling: Every try/except block must write to error\_log.txt and execute the send\_discord\_alert() function. Fatal UI timeouts must trigger a Playwright full-page screenshot saved to the root directory.



Data Integrity: All extracted text must pass through the tech\_keywords regex array before touching the Airtable API. Never push raw, unvetted firehose data.



Editing Rules: When refactoring, only modify the specific functions requested. Never truncate existing working code, and never hardcode API keys (always use os.getenv).

