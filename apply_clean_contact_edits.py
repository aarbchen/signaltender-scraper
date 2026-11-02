from pathlib import Path
import re

# 1. Fix the single remaining line in build_camberdesk_site.py and build_rubricward_site.py
for py_path in [
    Path(r"d:\CamberDesk\build_camberdesk_site.py"),
    Path(r"d:\RubricWard\build_rubricward_site.py"),
]:
    txt = py_path.read_text(encoding="utf-8")
    new_txt, n = re.subn(
        r'text:\s*"Need to speak with a real person\?[^"\n]*"',
        'text: "To send a message, click \'Contact\' below to open the Contact form."',
        txt,
    )
    print(f"{py_path.name}: replaced {n} concierge fallback line(s)")
    py_path.write_text(new_txt, encoding="utf-8")

# 2. Apply exact substring edits to d:\Daas\index.html
idx_path = Path(r"d:\Daas\index.html")
idx = idx_path.read_text(encoding="utf-8")

# 2a. Remove Contact from desktop headers
old_desk_1 = '          <a href="#contact" class="flex-1 inline-flex items-center justify-center px-1.5 xl:px-2.5 2xl:px-3 py-1.5 xl:py-2 rounded-lg text-[11px] xl:text-xs 2xl:text-[13px] font-medium text-slate-300 hover:text-white hover:bg-slate-800/80 border border-transparent transition-all whitespace-nowrap">Contact</a>\n'
assert old_desk_1 in idx, "Missing old_desk_1"
idx = idx.replace(old_desk_1, "")

old_desk_2 = '          <a href="#contact" class="flex-1 inline-flex items-center justify-center px-1.5 xl:px-2.5 2xl:px-3 py-1.5 xl:py-2 rounded-lg text-[11px] xl:text-xs 2xl:text-[13px] font-semibold text-white bg-sky-500/15 border border-sky-500/40 shadow-sm transition-all whitespace-nowrap">Contact</a>\n'
assert old_desk_2 in idx, "Missing old_desk_2"
idx = idx.replace(old_desk_2, "")

# 2b. Remove Contact from mobile headers (grid-cols-5 -> grid-cols-4)
old_mob_1 = '          <a href="#contact" class="px-1 sm:px-2 py-1 rounded-md bg-navy-950 text-slate-200 hover:text-sky-400 border border-slate-800 tracking-tight whitespace-nowrap">Contact</a>\n'
assert old_mob_1 in idx, "Missing old_mob_1"
idx = idx.replace(old_mob_1, "")

old_mob_2 = '          <a href="#contact" class="px-1 sm:px-2 py-1 rounded-md bg-sky-500/20 text-white border border-sky-500/40 font-semibold tracking-tight whitespace-nowrap">Contact</a>\n'
assert old_mob_2 in idx, "Missing old_mob_2"
idx = idx.replace(old_mob_2, "")

old_mob_grid = 'aria-label="Mobile Site Navigation" class="max-w-[1600px] mx-auto px-2.5 sm:px-4 py-1.5 grid grid-cols-5 gap-1'
assert old_mob_grid in idx, "Missing old_mob_grid"
idx = idx.replace(old_mob_grid, 'aria-label="Mobile Site Navigation" class="max-w-[1600px] mx-auto px-2.5 sm:px-4 py-1.5 grid grid-cols-4 gap-1')

# 2c. Update footer links in index.html:
# Replace "Contact &amp; Support" with "Contact", and point "Instant AI Support Concierge" to "#concierge"
idx = idx.replace(
    '<li><a href="#contact" class="hover:text-sky-400 transition-colors">Contact &amp; Support</a></li>',
    '<li><a href="#contact" class="hover:text-sky-400 transition-colors">Contact</a></li>',
)
idx = idx.replace(
    '<li><a href="#contact" class="hover:text-sky-400 transition-colors">Instant AI Support Concierge</a></li>',
    '<li><a href="#concierge" class="hover:text-sky-400 transition-colors">Instant AI Support Concierge</a></li>',
)
idx = idx.replace(
    '<a href="#contact" class="hover:text-sky-400 transition-colors">Contact &amp; Support</a>',
    '<a href="#contact" class="hover:text-sky-400 transition-colors">Contact</a>',
)
idx = idx.replace(
    '<a href="#contact" class="hover:text-sky-400 transition-colors">AI Support Concierge</a>',
    '<a href="#concierge" class="hover:text-sky-400 transition-colors">AI Support Concierge</a>',
)
idx = re.sub(
    r'(<a[^>]*id="st-floating-concierge-btn"[^>]*href=")#contact(")',
    r'\1#concierge\2',
    idx,
)
idx = re.sub(
    r'(<a[^>]*href=")#contact("[^>]*id="st-floating-concierge-btn")',
    r'\1#concierge\2',
    idx,
)

# 2d. Split the #page-trust tab switcher bar into #concierge ("Instant AI Support Concierge") and #contact ("Contact")
old_trust_tab_btn = """            <a
              href="#contact"
              id="trust-tab-btn-contact"
              data-trust-tab="contact"
              class="trust-tab-btn px-3.5 py-2 rounded-xl bg-navy-950 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-all cursor-pointer"
            >
              Instant AI Support Concierge
            </a>"""
new_trust_tab_btns = """            <a
              href="#concierge"
              id="trust-tab-btn-concierge"
              data-trust-tab="concierge"
              class="trust-tab-btn px-3.5 py-2 rounded-xl bg-navy-950 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-all cursor-pointer"
            >
              Instant AI Support Concierge
            </a>
            <a
              href="#contact"
              id="trust-tab-btn-contact"
              data-trust-tab="contact"
              class="trust-tab-btn px-3.5 py-2 rounded-xl bg-navy-950 hover:bg-slate-800 text-slate-300 border border-slate-800 transition-all cursor-pointer"
            >
              Contact
            </a>"""
assert old_trust_tab_btn in idx, "Missing old_trust_tab_btn"
idx = idx.replace(old_trust_tab_btn, new_trust_tab_btns, 1)

# 2e. Replace the exact slice between PANEL 3 (#contact) and PANEL 4 (#feedback)
start_marker = """                                <!-- ===============================================================
             PANEL 3 (#contact): CONTACT SUPPORT & ENGINEERING TEAM + AI CONCIERGE
             =============================================================== -->
        <div id="trust-panel-contact" class="hidden space-y-6">"""
end_marker = """        <!-- ===============================================================
             PANEL 4 (#feedback): HARDENED FEEDBACK & PORTAL REQUEST FORM
             =============================================================== -->"""

assert start_marker in idx, "Missing start_marker"
assert end_marker in idx, "Missing end_marker"
s_pos = idx.index(start_marker)
e_pos = idx.index(end_marker)
assert s_pos < e_pos and (e_pos - s_pos) < 20000, f"Unexpected slice range: {s_pos}..{e_pos}"

new_panels_block = """        <!-- ===============================================================
             PANEL 3A (#concierge): INSTANT AI SUPPORT CONCIERGE & SELF-SERVE DESK
             =============================================================== -->
        <div id="trust-panel-concierge" class="hidden space-y-6">
          <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">

            <!-- Left 5 Cols: Instant Self-Serve Actions -->
            <div class="lg:col-span-5 p-6 rounded-2xl bg-navy-900 border border-slate-800 space-y-5">
              <div class="space-y-1.5">
                <div class="text-xs font-mono uppercase text-indigo-300 font-bold">// SELF-SERVE DESK</div>
                <h2 class="text-xl font-extrabold text-white">Instant Account &amp; Billing Controls</h2>
                <p class="text-xs text-slate-300 leading-relaxed">
                  SignalTender is engineered as a 100% self-serve SaaS &amp; API platform so you can manage your subscription, webhooks, and API keys immediately.
                </p>
              </div>

              <div class="space-y-3 text-xs">
                <a href="#account" class="p-4 rounded-xl bg-navy-950 hover:bg-slate-900 border border-slate-800 hover:border-sky-500/40 block transition-all">
                  <div class="font-mono font-bold text-sky-400">Manage Plan, Invoices &amp; 1-Click Cancel &rarr;</div>
                  <div class="text-slate-400 mt-1">Download B2B tax receipts, switch Monthly/Annual billing, or cancel anytime in 1 click inside the Client Account Portal.</div>
                </a>
                <a href="#account" class="p-4 rounded-xl bg-navy-950 hover:bg-slate-900 border border-slate-800 hover:border-emerald-500/40 block transition-all">
                  <div class="font-mono font-bold text-emerald-400">Configure Slack, Teams, CRM, Email &amp; Discord Routing &rarr;</div>
                  <div class="text-slate-400 mt-1">Update your Slack/Teams/CRM webhook URLs, 52-portal territory filters, Team CC email seats, and Discord handle with instant test dispatches.</div>
                </a>
                <a href="#apis" class="p-4 rounded-xl bg-navy-950 hover:bg-slate-900 border border-slate-800 hover:border-indigo-500/40 block transition-all">
                  <div class="font-mono font-bold text-indigo-300">Test All 58 APIs &amp; MCP Server Live &rarr;</div>
                  <div class="text-slate-400 mt-1">Open the in-browser Studio Playground or copy your Claude Desktop / Cursor MCP JSON configuration.</div>
                </a>
                <a href="#contact" class="p-4 rounded-xl bg-navy-950 hover:bg-slate-900 border border-slate-800 hover:border-sky-500/40 block transition-all">
                  <div class="font-mono font-bold text-sky-300">Contact &rarr;</div>
                  <div class="text-slate-400 mt-1">Open the separate Contact tab to submit a message via the Contact form.</div>
                </a>
              </div>
            </div>

            <!-- Right 7 Cols: Live Autonomous AI Solutions & Support Concierge -->
            <div class="lg:col-span-7 p-6 sm:p-7 rounded-2xl bg-navy-900 border border-indigo-500/40 shadow-2xl space-y-5">
              <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-4">
                <div>
                  <div class="text-xs font-mono uppercase text-emerald-400 font-bold">&check; AUTONOMOUS AI CONCIERGE &bull; INSTANT ON-SCREEN RESOLUTION</div>
                  <h2 class="text-xl font-extrabold text-white mt-0.5">Ask the SignalTender AI Support Concierge</h2>
                </div>
                <span class="px-2.5 py-1 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 text-[11px] font-mono font-semibold">
                  Instant On-Screen Answer
                </span>
              </div>

              <!-- Quick Question Preset Pills -->
              <div class="space-y-1.5">
                <div class="text-[11px] font-mono text-slate-400 uppercase">Click a common question or type your own below:</div>
                <div class="flex flex-wrap gap-1.5 font-mono text-[11px]">
                  <button type="button" onclick="window.prefillConciergeQuestion('plans_and_pricing', 'What is the difference between Tier 1 ($99), Tier 2 ($399), Tier 3 Proposal Autopilot ($1,499), and Tier 4 Enterprise OEM & FOIA Vault ($2,499)?')" class="px-2.5 py-1 rounded-lg bg-navy-950 hover:bg-slate-800 text-sky-300 border border-slate-800 cursor-pointer">Compare All 4 Tiers?</button>
                  <button type="button" onclick="window.prefillConciergeQuestion('billing_and_cancellation', 'How do I download a corporate B2B tax receipt or cancel my subscription in 1 click?')" class="px-2.5 py-1 rounded-lg bg-navy-950 hover:bg-slate-800 text-emerald-300 border border-slate-800 cursor-pointer">Receipts &amp; 1-Click Cancel?</button>
                  <button type="button" onclick="window.prefillConciergeQuestion('api_and_mcp_integration', 'How do I connect all 58 GovCon APIs to Claude Desktop or Cursor via MCP?')" class="px-2.5 py-1 rounded-lg bg-navy-950 hover:bg-slate-800 text-indigo-300 border border-slate-800 cursor-pointer">Claude / Cursor MCP Setup?</button>
                  <button type="button" onclick="window.prefillConciergeQuestion('security_and_compliance', 'Does SignalTender store our RFP uploads or train AI models on our company data?')" class="px-2.5 py-1 rounded-lg bg-navy-950 hover:bg-slate-800 text-amber-300 border border-slate-800 cursor-pointer">Zero-Retention Security?</button>
                </div>
              </div>

              <form id="form-ai-concierge" onsubmit="event.preventDefault(); window.submitAiConciergeContact();" class="space-y-4" autocomplete="off">
                <!-- Anti-Bot Honeypot (Hidden from humans) -->
                <div class="hidden" aria-hidden="true">
                  <label for="concierge-honeypot">Leave this field blank</label>
                  <input id="concierge-honeypot" type="text" name="website_url_honeypot" tabindex="-1" autocomplete="off" value="" />
                </div>

                <div class="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div class="space-y-1">
                    <label for="concierge-topic" class="block text-[11px] font-mono uppercase text-slate-300">Inquiry Topic</label>
                    <select id="concierge-topic" class="w-full px-3 py-2.5 rounded-lg bg-navy-950 border border-slate-700 text-xs font-mono text-white">
                      <option value="plans_and_pricing">Plans &amp; Pricing ($0 / $99 / $399 / $1,499 / $2,499)</option>
                      <option value="billing_and_cancellation">Billing, Receipts &amp; 1-Click Cancel</option>
                      <option value="api_and_mcp_integration">58 APIs, RapidAPI &amp; MCP Server</option>
                      <option value="portal_coverage_and_sled">52 Portals &amp; State SLED Coverage</option>
                      <option value="security_and_compliance">Security, Privacy &amp; Zero-Retention</option>
                      <option value="enterprise_and_custom">Enterprise Multi-Seat / Custom</option>
                      <option value="technical_support">Technical Troubleshooting</option>
                    </select>
                  </div>
                  <div class="space-y-1">
                    <label for="concierge-email" class="block text-[11px] font-mono uppercase text-slate-300">Work Email (Optional)</label>
                    <input
                      id="concierge-email"
                      type="email"
                      maxlength="120"
                      placeholder="you@company.com (optional)"
                      class="w-full px-3 py-2.5 rounded-lg bg-navy-950 border border-slate-700 text-xs font-mono text-white placeholder-slate-500"
                    />
                  </div>
                  <div class="space-y-1">
                    <label for="concierge-company" class="block text-[11px] font-mono uppercase text-slate-300">Organization (Optional)</label>
                    <input
                      id="concierge-company"
                      type="text"
                      maxlength="100"
                      placeholder="Your Firm LLC"
                      class="w-full px-3 py-2.5 rounded-lg bg-navy-950 border border-slate-700 text-xs font-mono text-white placeholder-slate-500"
                    />
                  </div>
                </div>

                <div class="space-y-1">
                  <div class="flex items-center justify-between text-[11px] font-mono">
                    <label for="concierge-question" class="uppercase text-slate-300">Your Question (Plain Text Only &bull; No HTML or Links)</label>
                    <span class="text-emerald-400">WAF Protected</span>
                  </div>
                  <textarea
                    id="concierge-question"
                    rows="3"
                    maxlength="1000"
                    required
                    placeholder="Ask anything about SignalTender plans, 52-portal SLED coverage, API quotas, webhook setup, or security compliance..."
                    class="w-full p-3.5 rounded-xl bg-navy-950 border border-slate-700 focus:border-indigo-500 focus:outline-none text-xs font-mono text-white placeholder-slate-500 leading-relaxed"
                  ></textarea>
                </div>

                <button
                  type="submit"
                  id="btn-concierge-submit"
                  class="w-full py-3 px-5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-mono text-xs font-bold border border-indigo-400/40 shadow-lg transition-all cursor-pointer"
                >
                  Get Instant AI Concierge Answer &rarr;
                </button>
              </form>

              <!-- Instant AI Answer Output Container -->
              <div id="concierge-answer-box" class="hidden p-5 rounded-xl bg-navy-950 border border-emerald-500/40 space-y-3">
                <div class="flex flex-wrap items-center justify-between gap-2 text-[11px] font-mono border-b border-slate-800 pb-2">
                  <span id="concierge-answer-badge" class="text-emerald-400 font-bold">&check; INSTANT CONCIERGE RESPONSE</span>
                  <span id="concierge-security-badge" class="text-slate-400">WAF Verified</span>
                </div>
                <div id="concierge-answer-text" class="text-xs sm:text-sm text-slate-200 font-mono whitespace-pre-line leading-relaxed"></div>
                <div id="concierge-answer-actions" class="pt-2 flex flex-wrap gap-2"></div>
              </div>
            </div>

          </div>
        </div>

        <!-- ===============================================================
             PANEL 3B (#contact): STANDALONE CONTACT FORM
             =============================================================== -->
        <div id="trust-panel-contact" class="hidden space-y-6">
          <div id="human-support-escalation-card" class="max-w-3xl mx-auto p-6 sm:p-7 rounded-2xl bg-navy-900 border-2 border-sky-500/50 shadow-2xl space-y-5">
            <div class="border-b border-slate-800 pb-4">
              <div class="text-xs font-mono uppercase text-sky-400 font-bold">// CONTACT</div>
              <h2 class="text-xl sm:text-2xl font-extrabold text-white mt-0.5">Contact</h2>
              <p class="text-xs text-slate-300 mt-1">Use the form below to send a message.</p>
            </div>

            <form id="form-human-escalation" onsubmit="event.preventDefault(); window.submitHumanSupportEscalation();" class="space-y-4" autocomplete="off">
              <div class="hidden" aria-hidden="true">
                <label for="escalate-honeypot">Leave blank</label>
                <input id="escalate-honeypot" type="text" name="website_url_honeypot" tabindex="-1" autocomplete="off" value="" />
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div class="space-y-1">
                  <label for="escalate-name" class="block text-[11px] font-mono uppercase text-slate-300">Your Name</label>
                  <input id="escalate-name" type="text" maxlength="100" placeholder="Jane Doe" class="w-full px-3 py-2.5 rounded-lg bg-navy-950 border border-slate-700 text-xs font-mono text-white placeholder-slate-500" />
                </div>
                <div class="space-y-1">
                  <label for="escalate-email" class="block text-[11px] font-mono uppercase text-sky-300 font-bold">Work Email *</label>
                  <input id="escalate-email" type="email" maxlength="120" required placeholder="you@company.com" class="w-full px-3 py-2.5 rounded-lg bg-navy-950 border border-sky-500/50 text-xs font-mono text-white placeholder-slate-500" />
                </div>
                <div class="space-y-1">
                  <label for="escalate-company" class="block text-[11px] font-mono uppercase text-slate-300">Organization</label>
                  <input id="escalate-company" type="text" maxlength="100" placeholder="Your GovCon Firm LLC" class="w-full px-3 py-2.5 rounded-lg bg-navy-950 border border-slate-700 text-xs font-mono text-white placeholder-slate-500" />
                </div>
                <div class="space-y-1">
                  <label for="escalate-urgency" class="block text-[11px] font-mono uppercase text-slate-300">Topic</label>
                  <select id="escalate-urgency" class="w-full px-3 py-2.5 rounded-lg bg-navy-950 border border-slate-700 text-xs font-mono text-white">
                    <option value="general_inquiry">General Inquiry</option>
                    <option value="billing_inquiry">Billing or Subscription Inquiry</option>
                    <option value="technical_inquiry">Technical / API / MCP Inquiry</option>
                    <option value="enterprise_custom">Enterprise Multi-Seat / Custom Deployment</option>
                  </select>
                </div>
              </div>

              <div class="space-y-1">
                <div class="flex items-center justify-between text-[11px] font-mono">
                  <label for="escalate-message" class="uppercase text-slate-300">Message *</label>
                  <span class="text-sky-400">Encrypted TLS 1.3</span>
                </div>
                <textarea id="escalate-message" rows="4" maxlength="2000" required placeholder="Enter your message..." class="w-full p-3.5 rounded-xl bg-navy-950 border border-slate-700 focus:border-sky-500 focus:outline-none text-xs font-mono text-white placeholder-slate-500 leading-relaxed"></textarea>
              </div>

              <button type="submit" id="btn-escalate-submit" class="w-full py-3 px-5 rounded-xl bg-sky-600 hover:bg-sky-500 text-white font-mono text-xs font-bold border border-sky-400/40 shadow-lg transition-all cursor-pointer">
                Send Message &rarr;
              </button>
            </form>

            <div id="escalate-confirmation-box" class="hidden p-5 rounded-xl bg-navy-950 border border-emerald-500/40 space-y-2 text-xs font-mono"></div>
          </div>
        </div>

"""

idx = idx[:s_pos] + new_panels_block + idx[e_pos:]

# 2f. Update JS in index.html
old_trust_js = """      var trustHashes = {
        '#status': 'status',
        '#security': 'security',
        '#trust': 'security',
        '#contact': 'contact',
        '#support': 'contact',
        '#feedback': 'feedback',
        '#terms': 'terms',
        '#privacy': 'privacy',
        '#dpa': 'privacy',
        '#sla': 'status'
      };"""
new_trust_js = """      var trustHashes = {
        '#status': 'status',
        '#security': 'security',
        '#trust': 'security',
        '#concierge': 'concierge',
        '#contact': 'contact',
        '#support': 'concierge',
        '#feedback': 'feedback',
        '#terms': 'terms',
        '#privacy': 'privacy',
        '#dpa': 'privacy',
        '#sla': 'status'
      };"""
assert old_trust_js in idx, "Missing old_trust_js"
idx = idx.replace(old_trust_js, new_trust_js, 1)

old_switch_js = """      window.switchTrustTab = function (tabKey) {
        var key = tabKey || 'status';
        var panels = ['status', 'security', 'contact', 'feedback', 'terms', 'privacy'];
        var titles = {
          status: 'Live System Status & 52-Portal SLA Telemetry',
          security: 'Enterprise Security, Zero-Retention AI & GovCon Trust Center',
          contact: 'Autonomous AI Solutions & Support Concierge (Instant Resolution)',
          feedback: 'Hardened Product Feedback & State SLED Portal Request Queue',
          terms: 'SignalTender Enterprise B2B Terms of Service & SLA',
          privacy: 'SignalTender Privacy Policy, Zero-Retention DPA & Sub-Processors'
        };"""
new_switch_js = """      window.switchTrustTab = function (tabKey) {
        var key = tabKey || 'status';
        var panels = ['status', 'security', 'concierge', 'contact', 'feedback', 'terms', 'privacy'];
        var titles = {
          status: 'Live System Status & 52-Portal SLA Telemetry',
          security: 'Enterprise Security, Zero-Retention AI & GovCon Trust Center',
          concierge: 'Autonomous AI Solutions & Support Concierge',
          contact: 'Contact',
          feedback: 'Hardened Product Feedback & State SLED Portal Request Queue',
          terms: 'SignalTender Enterprise B2B Terms of Service & SLA',
          privacy: 'SignalTender Privacy Policy, Zero-Retention DPA & Sub-Processors'
        };"""
assert old_switch_js in idx, "Missing old_switch_js"
idx = idx.replace(old_switch_js, new_switch_js, 1)

old_concierge_btn = """            buttonsHtml += '<button type="button" onclick="window.prefillHumanEscalationFromAi()" class="px-3 py-1.5 rounded-lg bg-sky-600/25 hover:bg-sky-600/40 text-sky-200 border border-sky-500/40 text-xs font-mono font-semibold transition-all cursor-pointer">Need Human Help? Contact Support Team &rarr;</button>';"""
new_concierge_btn = """            buttonsHtml += '<button type="button" onclick="window.prefillHumanEscalationFromAi()" class="px-3 py-1.5 rounded-lg bg-sky-600/25 hover:bg-sky-600/40 text-sky-200 border border-sky-500/40 text-xs font-mono font-semibold transition-all cursor-pointer">Contact &rarr;</button>';"""
assert old_concierge_btn in idx, "Missing old_concierge_btn"
idx = idx.replace(old_concierge_btn, new_concierge_btn, 1)

old_escalation_js = """      window.prefillHumanEscalationFromAi = function () {
        var qEl = document.getElementById('concierge-question');
        var emEl = document.getElementById('concierge-email');
        var coEl = document.getElementById('concierge-company');
        var escEm = document.getElementById('escalate-email');
        var escCo = document.getElementById('escalate-company');
        var escMsg = document.getElementById('escalate-message');
        var card = document.getElementById('human-support-escalation-card');
        if (emEl && emEl.value && escEm && !escEm.value) escEm.value = emEl.value.trim();
        if (coEl && coEl.value && escCo && !escCo.value) escCo.value = coEl.value.trim();
        if (qEl && qEl.value && escMsg && !escMsg.value) {
          escMsg.value = 'Following up on my AI Concierge question: ' + qEl.value.trim();
        }
        if (card && card.scrollIntoView) {
          card.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        if (escEm && !escEm.value) {
          escEm.focus();
        } else if (escMsg) {
          escMsg.focus();
        }
      };

      window.submitHumanSupportEscalation = function () {
        var hpEl = document.getElementById('escalate-honeypot');
        var nmEl = document.getElementById('escalate-name');
        var emEl = document.getElementById('escalate-email');
        var coEl = document.getElementById('escalate-company');
        var urgEl = document.getElementById('escalate-urgency');
        var msgEl = document.getElementById('escalate-message');
        var aiQEl = document.getElementById('concierge-question');
        var btnEl = document.getElementById('btn-escalate-submit');
        var boxEl = document.getElementById('escalate-confirmation-box');

        if (hpEl && hpEl.value) return false;
        if (!boxEl) return false;
        var emailVal = emEl ? emEl.value.trim() : '';
        var rawMsg = msgEl ? msgEl.value.trim() : '';
        if (!emailVal || emailVal.indexOf('@') === -1) {
          boxEl.classList.remove('hidden');
          boxEl.className = 'p-4 rounded-xl bg-navy-950 border border-sky-500/40 text-xs font-mono text-sky-400';
          boxEl.textContent = 'Please enter a valid work email address so our team can reply directly to you.';
          return false;
        }
        if (!rawMsg || rawMsg.length < 8) {
          boxEl.classList.remove('hidden');
          boxEl.className = 'p-4 rounded-xl bg-navy-950 border border-sky-500/40 text-xs font-mono text-sky-400';
          boxEl.textContent = 'Please provide at least 8 characters describing how our Support & Engineering Team can help.';
          return false;
        }
        if (/(<\\s*script|javascript\\s*:|union\\s+select|drop\\s+table)/i.test(rawMsg)) {
          boxEl.classList.remove('hidden');
          boxEl.className = 'p-4 rounded-xl bg-navy-950 border border-sky-500/40 text-xs font-mono text-sky-400';
          boxEl.textContent = 'Blocked by SignalTender WAF: please submit plain text only.';
          return false;
        }

        var nameVal = nmEl ? nmEl.value.trim() : '';
        var compVal = coEl ? coEl.value.trim() : '';
        var urgVal = urgEl ? urgEl.value : 'priority_support';
        var aiCtx = aiQEl && aiQEl.value ? aiQEl.value.trim() : '';

        if (btnEl) {
          btnEl.disabled = true;
          btnEl.textContent = 'Dispatching to Support & Engineering Team Queue...';
        }
        boxEl.classList.remove('hidden');
        boxEl.className = 'p-4 rounded-xl bg-navy-950 border border-sky-500/40 text-xs font-mono text-sky-300';
        boxEl.textContent = 'Encrypting and routing your support ticket to the Support & Engineering Team queue...';

        var fallbackTicket = 'ST-SUP-' + Math.random().toString(16).substring(2, 10).toUpperCase();
        if (typeof fetch !== 'function') {
          boxEl.className = 'p-5 rounded-xl bg-navy-950 border border-emerald-500/40 space-y-2 text-xs font-mono text-slate-200';
          boxEl.innerHTML = '<div class="text-emerald-400 font-bold">&check; DIRECT SUPPORT TICKET LOGGED (' + fallbackTicket + ')</div><div>Your message has been queued for our Founder &amp; Engineering Support desk. You can also email <strong class="text-white">aaron@getsignaltender.com</strong> directly referencing <strong class="text-sky-300">' + fallbackTicket + '</strong>.</div>';
          return true;
        }

        fetch('https://b2b-contract-parser-api.onrender.com/v1/support/escalate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            brand: 'signaltender',
            name: nameVal,
            email: emailVal,
            company: compVal,
            urgency: urgVal,
            message: rawMsg,
            ai_chat_context: aiCtx,
            website_url_honeypot: '',
            client_elapsed_ms: Math.max(2500, Date.now() - __trustFormInitMs)
          })
        })
          .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
          .then(function (res) {
            if (btnEl) {
              btnEl.disabled = false;
              btnEl.textContent = 'Send Message to Support & Engineering Team →';
            }
            var tId = (res.ok && res.data && res.data.ticket_id) ? res.data.ticket_id : fallbackTicket;
            if (msgEl) msgEl.value = '';
            boxEl.className = 'p-5 rounded-xl bg-navy-950 border border-emerald-500/40 space-y-2 text-xs font-mono text-slate-200';
            boxEl.innerHTML = '<div class="text-emerald-400 font-bold">&check; PRIORITY SUPPORT TICKET DISPATCHED (' + tId + ')</div>' +
              '<div>Your message has been securely delivered to our Support &amp; Engineering Team queue. Our team will reply directly to <strong class="text-white">' + emailVal.replace(/</g, '&lt;') + '</strong> within 2 business hours.</div>' +
              '<div class="text-slate-400">Reference Ticket ID: <strong class="text-white">' + tId + '</strong></div>';
          })
          .catch(function () {
            if (btnEl) {
              btnEl.disabled = false;
              btnEl.textContent = 'Send Message to Support & Engineering Team →';
            }
            boxEl.className = 'p-5 rounded-xl bg-navy-950 border border-emerald-500/40 space-y-2 text-xs font-mono text-slate-200';
            boxEl.innerHTML = '<div class="text-emerald-400 font-bold">&check; PRIORITY SUPPORT TICKET LOGGED (' + fallbackTicket + ')</div>' +
              '<div>Your support ticket (<strong class="text-white">' + fallbackTicket + '</strong>) has been logged for our Support &amp; Engineering Team. We will reply directly to <strong class="text-white">' + emailVal.replace(/</g, '&lt;') + '</strong>.</div>';
          });
        return true;
      };"""

new_escalation_js = """      window.prefillHumanEscalationFromAi = function () {
        var qEl = document.getElementById('concierge-question');
        var emEl = document.getElementById('concierge-email');
        var coEl = document.getElementById('concierge-company');
        var escEm = document.getElementById('escalate-email');
        var escCo = document.getElementById('escalate-company');
        var escMsg = document.getElementById('escalate-message');
        var card = document.getElementById('human-support-escalation-card');
        if (emEl && emEl.value && escEm && !escEm.value) escEm.value = emEl.value.trim();
        if (coEl && coEl.value && escCo && !escCo.value) escCo.value = coEl.value.trim();
        if (qEl && qEl.value && escMsg && !escMsg.value) {
          escMsg.value = 'Following up on my AI Concierge question: ' + qEl.value.trim();
        }
        window.switchTrustTab('contact');
        if (window.location) window.location.hash = '#contact';
        if (card && card.scrollIntoView) {
          card.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        if (escEm && !escEm.value) {
          escEm.focus();
        } else if (escMsg) {
          escMsg.focus();
        }
      };

      window.submitHumanSupportEscalation = function () {
        var hpEl = document.getElementById('escalate-honeypot');
        var nmEl = document.getElementById('escalate-name');
        var emEl = document.getElementById('escalate-email');
        var coEl = document.getElementById('escalate-company');
        var urgEl = document.getElementById('escalate-urgency');
        var msgEl = document.getElementById('escalate-message');
        var aiQEl = document.getElementById('concierge-question');
        var btnEl = document.getElementById('btn-escalate-submit');
        var boxEl = document.getElementById('escalate-confirmation-box');

        if (hpEl && hpEl.value) return false;
        if (!boxEl) return false;
        var emailVal = emEl ? emEl.value.trim() : '';
        var rawMsg = msgEl ? msgEl.value.trim() : '';
        if (!emailVal || emailVal.indexOf('@') === -1) {
          boxEl.classList.remove('hidden');
          boxEl.className = 'p-4 rounded-xl bg-navy-950 border border-sky-500/40 text-xs font-mono text-sky-400';
          boxEl.textContent = 'Please enter a valid work email address.';
          return false;
        }
        if (!rawMsg || rawMsg.length < 8) {
          boxEl.classList.remove('hidden');
          boxEl.className = 'p-4 rounded-xl bg-navy-950 border border-sky-500/40 text-xs font-mono text-sky-400';
          boxEl.textContent = 'Please provide at least 8 characters in your message.';
          return false;
        }
        if (/(<\\s*script|javascript\\s*:|union\\s+select|drop\\s+table)/i.test(rawMsg)) {
          boxEl.classList.remove('hidden');
          boxEl.className = 'p-4 rounded-xl bg-navy-950 border border-sky-500/40 text-xs font-mono text-sky-400';
          boxEl.textContent = 'Blocked by SignalTender WAF: please submit plain text only.';
          return false;
        }

        var nameVal = nmEl ? nmEl.value.trim() : '';
        var compVal = coEl ? coEl.value.trim() : '';
        var urgVal = urgEl ? urgEl.value : 'general_inquiry';
        var aiCtx = aiQEl && aiQEl.value ? aiQEl.value.trim() : '';

        if (btnEl) {
          btnEl.disabled = true;
          btnEl.textContent = 'Sending Message...';
        }
        boxEl.classList.remove('hidden');
        boxEl.className = 'p-4 rounded-xl bg-navy-950 border border-sky-500/40 text-xs font-mono text-sky-300';
        boxEl.textContent = 'Sending your message...';

        var fallbackTicket = 'ST-MSG-' + Math.random().toString(16).substring(2, 10).toUpperCase();
        if (typeof fetch !== 'function') {
          boxEl.className = 'p-5 rounded-xl bg-navy-950 border border-emerald-500/40 space-y-2 text-xs font-mono text-slate-200';
          boxEl.innerHTML = '<div class="text-emerald-400 font-bold">&check; MESSAGE SUBMITTED (' + fallbackTicket + ')</div><div>Your message has been submitted (Reference: <strong class="text-sky-300">' + fallbackTicket + '</strong>).</div>';
          return true;
        }

        fetch('https://b2b-contract-parser-api.onrender.com/v1/support/escalate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            brand: 'signaltender',
            name: nameVal,
            email: emailVal,
            company: compVal,
            urgency: urgVal,
            message: rawMsg,
            ai_chat_context: aiCtx,
            website_url_honeypot: '',
            client_elapsed_ms: Math.max(2500, Date.now() - __trustFormInitMs)
          })
        })
          .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, data: d }; }); })
          .then(function (res) {
            if (btnEl) {
              btnEl.disabled = false;
              btnEl.textContent = 'Send Message →';
            }
            var tId = (res.ok && res.data && res.data.ticket_id) ? res.data.ticket_id : fallbackTicket;
            if (msgEl) msgEl.value = '';
            boxEl.className = 'p-5 rounded-xl bg-navy-950 border border-emerald-500/40 space-y-2 text-xs font-mono text-slate-200';
            boxEl.innerHTML = '<div class="text-emerald-400 font-bold">&check; MESSAGE SUBMITTED (' + tId + ')</div>' +
              '<div>Your message has been submitted.</div>' +
              '<div class="text-slate-400">Reference ID: <strong class="text-white">' + tId + '</strong></div>';
          })
          .catch(function () {
            if (btnEl) {
              btnEl.disabled = false;
              btnEl.textContent = 'Send Message →';
            }
            boxEl.className = 'p-5 rounded-xl bg-navy-950 border border-emerald-500/40 space-y-2 text-xs font-mono text-slate-200';
            boxEl.innerHTML = '<div class="text-emerald-400 font-bold">&check; MESSAGE SUBMITTED (' + fallbackTicket + ')</div>' +
              '<div>Your message (<strong class="text-white">' + fallbackTicket + '</strong>) has been recorded.</div>';
          });
        return true;
      };"""
assert old_escalation_js in idx, "Missing old_escalation_js"
idx = idx.replace(old_escalation_js, new_escalation_js, 1)

# 2g. Update quick-jump rail rawItems for trust page
old_rail_trust = "            { icon: 'chat', id: 'trust-panel-contact', label: 'AI Support Concierge', kw: 'contact support ai concierge help questions billing', color: 'text-indigo-300', action: 'trust_contact' },"
new_rail_trust = """            { icon: 'chat', id: 'trust-panel-concierge', label: 'AI Support Concierge', kw: 'ai concierge help questions billing', color: 'text-indigo-300', action: 'trust_concierge' },
            { icon: 'chat', id: 'trust-panel-contact', label: 'Contact', kw: 'contact message form', color: 'text-sky-300', action: 'trust_contact' },"""
assert old_rail_trust in idx, "Missing old_rail_trust"
idx = idx.replace(old_rail_trust, new_rail_trust, 1)

idx_path.write_text(idx, encoding="utf-8")
print("Successfully updated d:\\Daas\\index.html!")