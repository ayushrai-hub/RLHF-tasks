# ts=2026-06-10T02:35:10Z seq=4020 host=db-3 user=root
cat /var/backups/customer.db > /tmp/customer.db
# ts=2026-06-10T02:37:08Z seq=4021 host=db-3 user=root
scp /tmp/customer.db backup@edge-1:/tmp/customer.db
