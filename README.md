# broken-needle-algorithm

## Find a broken needle in a haystack

For a set of candidate needles (signal), and a haystack (signal + noise), returns both the array of matches (for each needle: start,length,stop) and the list of possibles (for each haystack position: the valid needles) without cleaning the haystack, without inferring anything about the haystack or the corruption that has happened to the haystack

## Example 1:

Non garbled input: 
> NEW ORLEANS,ORLEANS,NEW YORK,NEW YORK CITY,YORKTOWN,NEW YORKTOWN,YORK,WALES,SOUTH WALES,NEW SOUTH WALES
,SYDNEY,AUSTRALIA,AUSTRIA

Known needles:
<pre>
    'TOTALLY NOT THERE': '00',  # not present in the haystack, LOL
    'NEW ORLEANS': '01',        # NOLA, Mardi Gras city
    'ORLEANS': '02',            # the european city
    'NEW YORK': '03',           # the state
    'NEW YORK CITY': '04',      # the city that never sleeps
    'YORKTOWN': '05',           # in Virginia, which had a famous civil war battle in 1781
    'NEW YORKTOWN': '06',       # a city that should exist?
    'YORK': '07',               # in England
    'WALES': '08',              # the country next to England, part of the UK
    'SOUTH WALES': '09',        # De Cymru, the loosely defined region of Wales bordered by England to the east and mid Wales to the north
    'NEW SOUTH WALES': '10',    # in Australia, where the city Syndey is
    'SYDNEY': '11',             # Yes, this city
    'AUSTRALIA': '12',          # Yes, in this country
    'AUSTRIA': '13',            # No, not this one, and why Levenstein would be of limited help
    '*': '55',                  # Some unsanitized thing that could cause issues with regex
    'N*': '66',                 # Another
    'A': '77',                  # "A" typo actually
    'YO': '88',                 # Because YOLO! (and matches York)
    'NEW': '99'                 # A wild match
</pre>

Haystack used:
`NEW,ORLEANS,ORLEANS,NEW,YORK,NEW,YORK,CITY,YORKTOWN,NEW,YORKTOWN,YORK,WALES,SOUTH,WALES,NEW,SOUTH,WALES,SYDNEY,AUSTRALIA,AUSTRIA`

Non subsetting neddles (naive approach):

`{'NEW ORLEANS': [['0', '11', '10']], 'ORLEANS': [['12', '7', '18']], 'NEW YORK': [['20', '8', '27']], 'NEW YORK CITY': [['29', '13', '41']], 'YORKTOWN': [['43', '8', '50']], 'NEW YORKTOWN': [['52', '12', '63']], 'YORK': [['65', '4', '68']], 'WALES': [['70', '5', '74']], 'SOUTH WALES': [['76', '11', '86']], 'NEW SOUTH WALES': [['88', '15', '102']], 'SYDNEY': [['104', '6', '109']], 'AUSTRALIA': [['111', '9', '119']], 'AUSTRIA': [['121', '7', '127']]}`

Recovered haystack:

NEW ORLEANS,ORLEANS,NEW YORK,NEW YORK CITY,YORKTOWN,NEW YORKTOWN,YORK,WALES,SOUTH WALES,NEW SOUTH WALES,SYDNEY,AUSTRALIA,AUSTRIA

Encoded haystack:
>           01,     02,      03,           04,      05,          06,  07,   08,         09,             10,    11,       12,     13`

Without spaces:
01, 02, 03, 04, 05, 06, 07, 08, 09, 10, 11, 12, 13

## Example 2:

Haystack used:
`'NEW','ORLEANS...ORLEANS','NEW','YORK','NEW','YORK!!!!CITY','YORKTOWN','NEW*YORKTOWN','YORK!!!!WALES','SOUTH~~~WALES','NEW','SOUTH~WALES','SYDNEY','AUSTRALIA','AUSTRIA'`

Non subsetting neddles (naive approach):

`{'NEW ORLEANS': [['1', '11', '13']], 'ORLEANS': [['17', '7', '23']], 'NEW YORK': [['27', '8', '36']], 'NEW YORK CITY': [['40', '13', '57']], 'YORKTOWN': [['61', '8', '68']], 'NEW YORKTOWN': [['72', '12', '83']], 'YORK': [['87', '4', '90']], 'WALES': [['95', '5', '99']], 'SOUTH WALES': [['103', '11', '115']], 'NEW SOUTH WALES': [['119', '15', '135']], 'SYDNEY': [['139', '6', '144']], 'AUSTRALIA': [['148', '9', '156']], 'AUSTRIA': [['160', '7', '166']]}`
