git_version:
gen_config:
reflog.o: reflog.c git_version gen_config
fetch.o: fetch.c gen_config
stash.o: stash.c
blob.o: blob.c fetch.o
submodule.o: submodule.c reflog.o stash.o blob.o
git_tool: submodule.o reflog.o
