Milestone 6: Implement `python3 /app/tools/entitlement_audit.py risk-register /app/bundles /app/policy/signing-policy.json /app/out/entitlement-risk-register.json`. The command must reuse the current bundle discovery, entitlement sidecar selection, effective policy, planning, and verification rules from the earlier milestones. It must not modify any file.

The command must scan Objective-C source files directly inside each bundle directory. Include files ending in `.m`, `.mm`, or `.h`, sorted by path. Detect these capability markers by substring match:

- `push`: `registerForRemoteNotifications` or `UNUserNotificationCenter`
- `app_group`: `containerURLForSecurityApplicationGroupIdentifier` or `initWithSuiteName`
- `associated_domain`: `NSUserActivityTypeBrowsingWeb` or `continueUserActivity`
- `keychain`: `SecItemAdd` or `SecItemCopyMatching`

The output must be JSON with `risks`, `summary`, and `source_index`. Sort risk rows by risk level severity (`critical`, then `high`, then `medium`, then `low`) and then by bundle id. Each risk row must include `bundle_id`, `status`, `risk_level`, `capabilities_used`, `missing_runtime_support`, `policy_conflicts`, `remediation_required`, `source_files`, and `evidence`.

`status` is the same current status used by `verify-remediation`: `blocked`, `drift`, or `compliant`. When deriving that status and `policy_conflicts`, preserve the plan rule that a missing `aps-environment` key skips the push-environment mismatch check; a present but wrong value still produces `push environment profile mismatch`. `capabilities_used` is the sorted list of detected capability names in this order: `push`, `app_group`, `associated_domain`, `keychain`. `source_files` is the sorted list of matching source file paths relative to the bundle directory. Each evidence row must include `capability`, `file`, `line`, and `marker`, where `file` is relative to the bundle directory and `line` is 1-based. Sort evidence rows by the same capability order used for `capabilities_used`, then by `file`, then by `line`, then by `marker`.

`missing_runtime_support` must list capability names that are used in source but are not backed by the current selected entitlement sidecar after applying the normalized entitlement mapping from `inventory`: `push` requires a non-null `aps_environment`, `app_group` requires at least one `app_groups` value, `associated_domain` requires at least one `associated_domains` value, and `keychain` requires at least one `keychain_groups` value. Use these normalized field names for this check rather than raw plist key names. `policy_conflicts` is the current plan reason list for the bundle. `remediation_required` is true when the status is not `compliant` or `missing_runtime_support` is not empty.

Set `risk_level` to `critical` when `missing_runtime_support` is not empty, or when a blocked bundle has any detected capability usage. Otherwise set it to `high` when a drift bundle has any detected capability usage, `medium` when the status is `blocked` or `drift`, and `low` for compliant bundles.

The `summary` object must include `total`, `by_risk_level`, `by_status`, `bundles_with_source_usage`, `missing_runtime_support_count`, and `policy_conflict_count`. Include zero-count keys for every risk level and status. `missing_runtime_support_count` is the total number of missing capability entries across all rows. `policy_conflict_count` is the total number of plan reasons across all rows. The `source_index` object must include every capability name with a sorted list of bundle ids that use that capability.
