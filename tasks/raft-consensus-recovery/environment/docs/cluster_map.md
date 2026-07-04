# Cluster Map

Five-node cluster `n1`–`n5` in region `us-east`.

| Node | Role hint        | Notes                          |
|------|------------------|--------------------------------|
| n1   | initial leader   | Majority side during partition |
| n2   | follower         | Majority                       |
| n3   | follower         | Majority                       |
| n4   | stale candidate  | Minority during partition      |
| n5   | stale candidate  | Minority during partition      |

Quorum size: 3. Client writes flow through the elected leader only.
