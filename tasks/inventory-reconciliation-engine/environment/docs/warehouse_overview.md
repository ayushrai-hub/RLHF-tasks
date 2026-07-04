# Warehouse inventory overview

Inventory changes arrive as append-only supplier events. Operations teams replay
streams to rebuild on-hand counts before publishing to the storefront API.

## Historical note

An earlier prototype sorted by file line number. That was retired in 2024 but some
deployed images still use ingestion order.

Another retired prototype tracked supplier `version` separately per operation type
(`ADD` vs `SET` vs `DELETE`). Current deployments use one monotonic version counter
per `(product_id, supplier_id)` stream.

## Operations (informal)

- ADD / REMOVE adjust counts
- SET replaces count
- DELETE hides a SKU from the catalog feed
- RESTORE brings a deleted SKU back (any supplier may issue RESTORE — retired policy)
- ROLLBACK compensates a prior change

Exact validation ordering and conflict rules live in the deployment contract, not
this overview.
