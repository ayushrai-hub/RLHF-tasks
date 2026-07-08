version_stamp:
commit.o: commit.c version_stamp
pack.o: pack.c version_stamp
diff.o: diff.c version_stamp
rebase.o: rebase.c
branch.o: branch.c
libgit: commit.o pack.o diff.o rebase.o branch.o
