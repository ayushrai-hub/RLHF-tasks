CREATE TABLE deleted_files (
  path TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  deleted_at TEXT NOT NULL,
  size INTEGER NOT NULL,
  recovered_from TEXT NOT NULL
);
INSERT INTO deleted_files VALUES ('/srv/payroll/q2.csv','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','2026-06-10T02:39:00Z',129024,'journal');
INSERT INTO deleted_files VALUES ('/var/backups/customer.db','bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb','2026-06-10T02:39:20Z',309248,'journal');
INSERT INTO deleted_files VALUES ('/etc/ssh/sshd_config','cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc','2026-06-10T02:16:00Z',2418,'git');
