apply.o: apply.c git_config.h
filter.o: filter.c
refs.o: refs.c
git_tool: apply.o refs.o
git_binary: git_tool refs.o
