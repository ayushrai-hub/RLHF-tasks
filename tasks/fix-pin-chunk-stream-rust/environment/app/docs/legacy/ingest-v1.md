# Ingest v1 (archived)

v1 replay fed entire schedules in one frame before draining. That path was retired for schedules longer than one chunk block.

Short schedules also used a single feed in early QA harnesses. Current staging uses framed ingest instead.
