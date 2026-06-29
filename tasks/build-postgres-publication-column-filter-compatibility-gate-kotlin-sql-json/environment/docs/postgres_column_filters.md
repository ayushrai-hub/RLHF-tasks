PostgreSQL publication column lists are written as `schema.table (column_a, column_b)` inside `CREATE PUBLICATION` or `ALTER PUBLICATION ... ADD TABLE` statements. A table without a column list sends all columns.

This workspace treats filtered publications conservatively during migrations: subscriber-required columns and primary key columns must remain available, and `REPLICA IDENTITY FULL` tables with a column list require human review before cutover.
