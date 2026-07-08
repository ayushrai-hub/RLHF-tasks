git_config.h:
revwalk.o: revwalk.c git_config.h
fsck.o: fsck.c
apply.o: apply.c
git_tool: apply.o fsck.o revwalk.o git_config.h
git_binary: git_tool fsck.o
