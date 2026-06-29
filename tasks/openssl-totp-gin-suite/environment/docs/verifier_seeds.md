# Verifier seed manifest

Path: `/app/environment/data/verifier_seeds.json`

```json
{
  "scenarios": [
    {
      "name": "<scenario id>",
      "handle": "<enrollment handle>",
      "expect_status": "<ledger status token>",
      "clock_epoch": 1700000040,
      "clock_offset_steps": 0,
      "duplicate_enroll": false,
      "tamper_token": false,
      "rotate_signing": false,
      "rotate_stale_seal": false,
      "check_store_mode": false,
      "bad_passcode": false
    }
  ]
}
```

Optional fields default to `false` or `0` when omitted. `clock_offset_steps` advances the host grading clock by `clock_offset_steps * 30` seconds after `clock_epoch` while keeping passcode materialization at `clock_epoch`. The suite exports `K9_CLOCK_EPOCH` and `K9_PASSCODE_EPOCH` for MFA commands when they differ. When `rotate_stale_seal` is true, the driver rotates signing material and verifies the pre-rotation session seal without minting a replacement token.
