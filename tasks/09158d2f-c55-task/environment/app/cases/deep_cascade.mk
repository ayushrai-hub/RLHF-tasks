# Deep cascade: types.h is phony, lex.c is missing -> full chain rebuilds
object_types.h:
bundle.o: bundle.c object_types.h
blame.o: blame.c object_types.h
index.o: index.c bundle.o blame.o
merge.o: merge.c index.o
tag.o: tag.c index.o merge.o
git_bin: tag.o merge.o
