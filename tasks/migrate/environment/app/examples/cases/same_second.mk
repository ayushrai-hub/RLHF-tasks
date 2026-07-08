checkout.o: checkout.c git_config.h
refs.o: refs.c
apply.o: apply.c git_config.h
notes.o: notes.c
git_tool: checkout.o apply.o notes.o refs.o
git_binary: git_tool notes.o
