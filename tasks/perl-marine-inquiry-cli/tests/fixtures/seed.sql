PRAGMA foreign_keys = OFF;

DROP TABLE IF EXISTS config;
DROP TABLE IF EXISTS exits;
DROP TABLE IF EXISTS prompts;
DROP TABLE IF EXISTS records;
DROP TABLE IF EXISTS sections;
DROP TABLE IF EXISTS parties;
DROP TABLE IF EXISTS sessions;
DROP TABLE IF EXISTS truth;

CREATE TABLE config (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE sections (
    id                TEXT PRIMARY KEY,
    name              TEXT NOT NULL,
    sort_order        INTEGER NOT NULL DEFAULT 0,
    short_description TEXT NOT NULL,
    long_description  TEXT NOT NULL
);

CREATE TABLE exits (
    from_section TEXT NOT NULL,
    to_section   TEXT NOT NULL,
    direction    TEXT NOT NULL,
    PRIMARY KEY (from_section, to_section)
);

CREATE TABLE parties (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    role        TEXT NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    description TEXT NOT NULL
);

CREATE TABLE records (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    section_id  TEXT NOT NULL,
    description TEXT NOT NULL,
    tags        TEXT NOT NULL DEFAULT '[]'
);

-- The case office's sealed finding. Intentionally EMPTY in the shipped image:
-- the answer is not present anywhere the investigator can read it. POST /finding
-- records the submission and returns verdict "pending" when no truth row is
-- present; the finding is adjudicated only at submission review, when the case
-- office supplies its own sealed conclusion. The answer must be reasoned from the
-- record, not looked up.
CREATE TABLE truth (
    id     INTEGER PRIMARY KEY,
    party  TEXT NOT NULL,
    means  TEXT NOT NULL,
    place  TEXT NOT NULL,
    minute TEXT NOT NULL
);

CREATE TABLE sessions (
    id              TEXT PRIMARY KEY,
    current_section TEXT NOT NULL,
    day_number      INTEGER NOT NULL,
    retrieved       TEXT NOT NULL DEFAULT '[]',
    journal         TEXT NOT NULL DEFAULT '[]',
    status          TEXT NOT NULL DEFAULT 'active'
);

INSERT INTO config (key, value) VALUES
    ('schema_version', '"inquiry-api-1924.11"'),
    ('case_title', '"In the Matter of the Loss of the Steamship Marisol"'),
    ('case_date', '"1924-11-14"'),
    ('inquiry_days', '5'),
    ('min_days_before_finding', '1'),
    ('accepted_means', '["accident","stranding","scuttle-seacock","fire","collision"]'),
    ('accepted_places', '["loc-engine-room","loc-stokehold","loc-bridge","loc-holds","loc-boat-deck","loc-shoal"]'),
    ('required_record_ids', '["rec-salvage-diver","rec-cargo-tally","rec-policy","rec-owner-letters","rec-manifest"]');

INSERT INTO sections (id, name, sort_order, short_description, long_description) VALUES
    ('sec-records-room', 'Records Room', 10,
     'The central records room of the Board of Trade inquiry; depositions and ship papers are tabled here.',
     'A long room with green-shaded lamps and a baize table where the assessor lays out the day''s papers. The manifest, the deck log, the weather log, and the wireless log are tabled here. Passages lead to the surveyor''s office, the owners'' file room, the salvage store, and the survivors'' hall.'),
    ('sec-surveyors-office', 'Surveyor''s Office', 20,
     'The cargo surveyor''s office, holding the loading tallies and the load-line certificate.',
     'A cramped office stacked with tally books. Surveyor Cardew''s Liverpool loading tally for the Marisol is here, with the load-line certificate and the boiler-room inspection report.'),
    ('sec-owners-office', 'Owners'' File Room', 30,
     'The file room holding Veil and Penhallow''s correspondence and the insurance papers.',
     'The managing owners'' files, subpoenaed for the inquiry: the insurance policy schedule and a bundle of the owner''s letters and cables touching the voyage and the cover.'),
    ('sec-salvage-store', 'Salvage Store', 40,
     'Where the salvage divers'' report and the recovered fittings are held.',
     'A cold store smelling of weed and oil. The salvage company''s diver''s report on the wreck on the Carrack Shoal is here, with a few recovered fittings tagged as exhibits.'),
    ('sec-survivors-hall', 'Survivors'' Hall', 50,
     'The hall where the survivors were deposed.',
     'A bare hall with benches where the master, the officers, and the surviving crew were deposed in turn. Their statements are filed here.');

INSERT INTO exits (from_section, to_section, direction) VALUES
    ('sec-records-room', 'sec-surveyors-office', 'east'),
    ('sec-records-room', 'sec-owners-office', 'north'),
    ('sec-records-room', 'sec-salvage-store', 'west'),
    ('sec-records-room', 'sec-survivors-hall', 'south'),
    ('sec-surveyors-office', 'sec-records-room', 'west'),
    ('sec-owners-office', 'sec-records-room', 'south'),
    ('sec-salvage-store', 'sec-records-room', 'east'),
    ('sec-survivors-hall', 'sec-records-room', 'north');

INSERT INTO parties (id, name, role, sort_order, description) VALUES
    ('par-frane', 'Aldous Frane', 'master of the Marisol', 10,
     'Master of the lost vessel. The Board''s preliminary view and the waterfront rumour lean on him: that he hazarded the ship in fog and abandoned her too soon. He has commanded for twenty years without a loss before this.'),
    ('par-veil', 'Marcus Veil', 'managing owner', 20,
     'Managing owner of the Marisol, of Veil and Penhallow, ashore in Liverpool throughout. He declared the cargo and arranged the insurance, and stood to be paid on the loss. He never went near the ship.'),
    ('par-lund', 'Edvard Lund', 'second engineer', 30,
     'Second engineer, shipped at Liverpool for this voyage only and on the owner''s recommendation. Was below at the time of the loss and gives a thin account of his movements.'),
    ('par-okonkwo', 'Daniel Okonkwo', 'first mate', 40,
     'First mate, a careful and literal witness who kept the deck log. His account of the loading and of the night, read closely, does not sit with an ordinary stranding.'),
    ('par-such', 'Tomas Such', 'chief engineer', 50,
     'Chief engineer, off watch and asleep when the water came in. Speaks well of his pumps: they were sound and had been tested at Liverpool.'),
    ('par-cardew', 'Hester Cardew', 'cargo surveyor', 60,
     'Independent cargo surveyor at Liverpool who tallied what actually went into the holds. A meticulous record-keeper.'),
    ('par-mercer', 'Josiah Mercer', 'underwriter''s agent', 70,
     'Agent for the underwriters who carried the risk; produced the policy schedule under subpoena.');

INSERT INTO records (id, name, section_id, description, tags) VALUES
    ('rec-manifest', 'cargo manifest', 'sec-records-room',
     'The Marisol''s declared cargo manifest for the voyage: forty crates of machine tools consigned to Lisbon, valued high, together with a quantity of tinned goods. Signed off by the managing owner''s office.',
     '["cargo","declared","owner-signed"]'),
    ('rec-cargo-tally', 'surveyor''s loading tally', 'sec-surveyors-office',
     'Surveyor Cardew''s independent tally of what was actually struck below at Liverpool. It records the tinned goods and a great deal of ballast, but NO machine-tool crates: the forty crates on the manifest never came alongside and were never loaded. The declared high-value cargo was fictitious.',
     '["cargo","decisive","fictitious-cargo","never-loaded"]'),
    ('rec-policy', 'insurance policy schedule', 'sec-owners-office',
     'The underwriters'' policy schedule: hull and the declared cargo insured together for a sum far above the ageing vessel''s real worth and above any honest valuation of what she truly carried. The cargo line is written against the manifest''s machine tools.',
     '["insurance","over-insured","motive"]'),
    ('rec-owner-letters', 'managing owner''s correspondence', 'sec-owners-office',
     'A bundle of Marcus Veil''s letters and cables. They show him pressing the high cargo valuation on the underwriters before sailing, and a private instruction placing the new second engineer, Lund, aboard to "see the voyage through as we discussed." Taken together the correspondence shows the owner arranged the over-insurance and put his own man below.',
     '["owner","veil","pre-arranged","instructed-lund","motive"]'),
    ('rec-weather-log', 'coastguard weather log', 'sec-records-room',
     'The shore station''s weather log for the night: thick fog on the coast, light airs, a low swell. Poor visibility, but no gale and no sea heavy enough to break a sound hull.',
     '["weather","fog","no-gale"]'),
    ('rec-wireless-log', 'wireless traffic log', 'sec-records-room',
     'The wireless log: the Marisol made no distress call until the water was already over the stokehold plates, then a single hurried CQD. The interval between aground and foundering was far shorter than a grounding alone would explain.',
     '["wireless","timing","foundered-fast"]'),
    ('rec-deck-log', 'deck log', 'sec-records-room',
     'The deck log in the mate''s hand: course and soundings through the evening, the stranding on the shoal at about eleven, then the order to sound the wells and work the pumps, then the rapid flooding and the order to abandon. The entries are orderly and consistent with a master doing his duty.',
     '["deck-log","stranding","abandon-proper"]'),
    ('rec-boiler-report', 'boiler and pump inspection', 'sec-surveyors-office',
     'The pre-voyage inspection of the engine and boiler room at Liverpool: the bilge pumps were tested and found sound, well able to hold against any ordinary leak. Nothing in the machinery explains a sound ship foundering in minutes off a soft shoal.',
     '["pumps-sound","engine-room"]'),
    ('rec-salvage-diver', 'salvage diver''s report', 'sec-salvage-store',
     'The salvage company''s diver went down on the wreck on the Carrack Shoal. He found the hull barely holed by the grounding, yet the main injection sea-cock standing WIDE OPEN, and the bilge-pump suction valves WIRED SHUT so they could not draw. No grounding does this. The Marisol was deliberately opened to the sea and her pumps disabled: she was scuttled.',
     '["decisive","salvage","seacock-open","pumps-wired","scuttle"]'),
    ('rec-loadline-cert', 'load-line certificate', 'sec-surveyors-office',
     'The Marisol''s load-line certificate, in order. She was not overloaded; she floated above her marks on a cargo far lighter than the manifest declared.',
     '["loadline","not-overloaded"]'),
    ('rec-frane-deposition', 'deposition of Captain Frane', 'sec-survivors-hall',
     'The master''s deposition. He took the inshore course in fog on the soundings, struck the shoal, set the pumps going, and when the water gained beyond the pumps he abandoned to save his people, all of whom were saved. He knew nothing of any sea-cock, nor that the machine tools were not below; he had the manifest like any master and trusted it.',
     '["master","abandon-proper","knew-nothing","innocent"]'),
    ('rec-lund-deposition', 'deposition of second engineer Lund', 'sec-survivors-hall',
     'The second engineer''s deposition is brief and unwilling. He says he was about the engine room when she struck and cannot account closely for his movements before the flooding. He shipped only for this voyage and on the owner''s word.',
     '["lund","thin-account","owner-placed","instrument"]'),
    ('rec-okonkwo-deposition', 'deposition of First Mate Okonkwo', 'sec-survivors-hall',
     'The first mate''s deposition. He oversaw the loading and is certain the heavy crates never came down to the quay; he questioned it and was told by the owner''s office it was arranged otherwise. On the night, he is clear the pumps were started promptly and yet the water rose as if the ship were open below, faster than any leak he has known.',
     '["mate","cargo-never-came","flooded-too-fast","honest"]'),
    ('rec-survivor-accounts', 'survivors'' accounts', 'sec-survivors-hall',
     'The crew''s accounts. One fireman deposes that he saw the second engineer Lund down at the main sea-cock and the bilge manifold shortly before the water came in -- at about a quarter past eleven, 23:15 by the engine-room clock, a few minutes after she struck and while the chief was still in his bunk -- and thought nothing of it at the time. The rest speak of the suddenness of the flooding and the good order of the boats.',
     '["survivors","lund-at-seacock","decisive-minute","sudden-flooding"]');

-- truth table intentionally left EMPTY (see comment above).
