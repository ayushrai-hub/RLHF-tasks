checkout.o: checkout.c
tree.o: tree.c git_config.h
filter.o: filter.c
git_tool: tree.o filter.o checkout.o
