apply.o: apply.c git_config.h
tree.o: tree.c git_config.h
filter.o: filter.c
delta.o: delta.c git_config.h
git_tool: filter.o delta.o apply.o tree.o
