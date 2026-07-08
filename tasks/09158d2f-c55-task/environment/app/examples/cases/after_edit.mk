notes.o: notes.c git_config.h
checkout.o: checkout.c git_config.h
revwalk.o: revwalk.c
git_tool: revwalk.o checkout.o notes.o
git_binary: git_tool checkout.o
