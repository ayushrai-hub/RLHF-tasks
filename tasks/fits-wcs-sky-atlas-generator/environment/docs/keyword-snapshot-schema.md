# keyword snapshot schema

File: /app/var/wcs-keyword-snapshot.json

Written before atlas export on every successful build.

Fields:

- version: integer 1
- cards: array of objects with keyword (standard 8-char or HIERARCH child name with spaces), value (string), comment (string)
- canonical: single string joining keyword=value pairs in card order separated by semicolons

CONTINUE and HIERARCH cards must be merged before appearing in cards and canonical.
