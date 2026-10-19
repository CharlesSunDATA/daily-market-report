# Weekly earnings and major US economic diary

Two new dynamic cards have been added to the homepage and to the latest (2026-10-19) report. Dated reports remain historical documents; the injected calendar cards are explicitly labeled **live/current**, not claims about the report's original creation date. Future hand-written report HTML files should add the same two placeholder sections and the script:

`<div id="weeklyEarnings"></div><div id="weeklyMacro"></div>`
`<script src="../../../weekly-calendar.js" data-root="../../../" defer></script>`

The shared JSON stores originally company-IR-verified earnings events, and official Fed/BLS/BEA/New York Fed release dates. A Nasdaq calendar feed **may** add additional provisional earnings; these are marked provider_unverified and **never overwrite a manually confirmed company's date**. The BLS iCalendar feed expands macro coverage; errors are visible in weekly-calendar-status.json. No invented exact release times. A conference-call time must not be mistaken for the earnings-release time.

The workflow attempts to refresh daily at ~09:00 Adelaide, adjusted for daylight saving; GitHub schedule delays and feed blocks are possible. The original verified snapshot remains available even if providers fail. Earnings after the seeded week might be incomplete if Nasdaq is unavailable: the UI explicitly says so. Please cross-check company IR before acting.

Unit tests: `python -m unittest discover -s tests -v`.

For all future reports: the Deploy Pages workflow runs `scripts/inject_calendar.py`, adding the same two dynamic cards to **only the latest dated HTML report** in the Pages build if that report has not already included them. Historical source files are not rewritten.
