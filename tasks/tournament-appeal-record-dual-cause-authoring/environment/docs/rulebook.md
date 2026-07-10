# Rookline tournament rules

Rookline match files are line-oriented tournament records. A case begins with `case <id>` and ends with `endcase`. Player ledger rows use `player <id> key=<key> registered=<epoch> revoked=<epoch|none>`. Match rows use `match <id> epoch=<epoch> format=<v1|v2> home=<player> away=<player> sig=<signature> declared=<home|away|draw> moves=<move-list>`. Appeal rows use `appeal <id> target=<match-id> epoch=<appeal-epoch> replay_epoch=<epoch> sig=<signature> declared=<home|away|draw> moves=<move-list>`.

A v2 signature is `SIG:<match-id>:<home>:<away>:<epoch>:<home-key>:<away-key>`. A v1 signature is `LEGACY:<match-id>:<home>:<away>:<epoch>:<home-key>:<away-key>`. A player is eligible at a scored epoch when the epoch is at least the registration epoch and is strictly earlier than the revocation epoch, when one is present. Legacy v1 records are still authoritative for records made before revocation.

Moves are comma-separated tokens such as `H2[clean]` or `A1[tempo]`. `H` scores for the home player and `A` scores for the away player. Each move awards one or two points. The annotation label is case-insensitive after trimming, but the canonical label must be exactly one of `clean`, `tempo`, `appeal`, or `legacy`; hyphenated extensions are not aliases. The declared result must agree with the scored moves.

When an appeal targets a match, the original match is vacated and the appeal's replay record is scored instead. The replay uses the original match id, players, and signature format, but it uses the appeal's replay epoch, signature, declared result, and move list. If the replay is not authoritative, the vacated match contributes no standings entry.
