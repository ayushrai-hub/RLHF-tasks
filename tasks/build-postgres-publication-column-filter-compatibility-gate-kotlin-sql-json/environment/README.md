This workspace contains a small internal command line tool used during logical replication cutover reviews. It reads PostgreSQL schema dumps, publication definitions, and subscriber snapshots, then produces compatibility reports for release automation.

The shipped implementation is intentionally incomplete. The scripts in `/app/scripts` show the normal operator entry points, and the data in `/app/input` is a representative cutover bundle.
