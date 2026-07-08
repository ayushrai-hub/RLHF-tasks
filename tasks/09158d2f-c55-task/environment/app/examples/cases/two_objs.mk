tree.o: tree.c git_config.h
fsck.o: fsck.c git_config.h
worktree.o: worktree.c git_config.h
apply.o: apply.c git_config.h
git_tool: worktree.o
git_binary: git_tool fsck.o
