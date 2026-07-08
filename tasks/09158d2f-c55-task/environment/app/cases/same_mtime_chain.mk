diff.o: diff.c
commit.o: commit.c pack.c
libgit: commit.o diff.o
git_tool: libgit apply.o
apply.o: apply.c
