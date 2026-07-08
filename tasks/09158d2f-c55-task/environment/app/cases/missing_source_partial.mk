git_config.h:
remote.o: remote.c git_config.h
prune.o: prune.c libgit_backend.h
repack.o: repack.c
git_daemon: remote.o prune.o repack.o
git_client: remote.o repack.o
