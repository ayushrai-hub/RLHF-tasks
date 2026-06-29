# FITS header lexer

Primary HDU header is read in 2880-byte blocks of 80-character cards until END.

Each card has keyword columns 1-8, equals sign at column 9, value from column 11.

CONTINUE cards append their string value (columns 11-80 trimmed) to the previous keyword value. When a string value spans cards, the opening card may omit its closing quote and the final CONTINUE fragment supplies the closing quote.

HIERARCH keywords preserve embedded spaces in the value portion. For cards beginning with HIERARCH in columns 1-8, the keyword name is the text between HIERARCH and the equals sign (trimmed). The value begins after the equals sign at column 11 or later.

String values retain surrounding quotes in the cards array value field but not in canonical.

Numeric values are stored as decimal strings without leading padding spaces.
