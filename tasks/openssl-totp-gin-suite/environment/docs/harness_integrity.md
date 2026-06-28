# Harness integrity pins

Graded orchestration scripts must remain the live entry points that invoke the rebuilt CLI against seeded scenarios. SHA-256 fingerprints:

| path | sha256 |
|------|--------|
| `/app/environment/scripts/step_driver.py` | `809d77cfdc28dbe92da49ddb2906b7e165b94e30e33a61b86a1f5e7c4cba3466` |
| `/app/environment/scripts/grad_driver.sh` | `bf48794391e1655781a2f96864d49659a5e818a9c351663d98ee68363af29db8` |

Manual ledger fabrication or edits to these scripts to synthesize rows are insufficient.
