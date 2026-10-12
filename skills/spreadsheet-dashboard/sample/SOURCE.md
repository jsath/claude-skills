# Sample data: where it comes from

`sales_jan_messy.xlsx` (Jan 2011, 677 rows) and `sales_feb_messy.xlsx`
(Feb 2011, 434 rows) are the files from the reel demo, so you can try the
skill before using your own sheet.

Source: Chen, D. (2015). Online Retail [Dataset]. UCI Machine Learning
Repository. https://doi.org/10.24432/C5BW33
Licence: CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/)

Changes made: only the France orders from January and February 2011 were
kept, then the files were made messy on purpose: dates typed five ways,
some product names in capitals, lower case or with a letter missing, prices
stored as text with a currency sign or a decimal comma, 8 duplicate rows
per month, blank rows, and test or dummy rows (4 in January, 2 in
February). Customer IDs are the anonymous numbers from the original dataset.

Try it: copy both files into an empty folder, start Claude Code there and
say "clean sales_jan_messy.xlsx and build me a dashboard". Next, say "new
month, add sales_feb_messy.xlsx".
