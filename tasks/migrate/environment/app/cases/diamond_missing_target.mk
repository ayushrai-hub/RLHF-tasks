packfile.o: packfile.c
bisect.o: bisect.c packfile.o
revert.o: revert.c packfile.o
git_package: bisect.o revert.o
