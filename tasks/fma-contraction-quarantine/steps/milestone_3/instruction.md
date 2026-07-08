The team wants to keep the release optimization on every file that tolerates it and pull it back only where it actually breaks a contract, one file at a time rather than all or nothing.

Produce the smallest set of per-file flag removals that makes every kernel's invariant hold under the release inputs. Smallest matters: if you can put any dropped flag back on its file and nothing breaks, that removal did not belong in the set. Turning the whole bundle off, or dropping one flag everywhere, will not pass. And remember the optimization lands where the compiler applies it, which is not always the file that defines the kernel.

Write /app/output/result_3.json mapping each translation unit that needs a removal to the list of flag names to drop for it. The flags you may drop are ffp-contract, fassociative-math, freciprocal-math, fno-signed-zeros, and ffinite-math-only. Key every entry by the bare source file name, so accum or accum.c, never a directory path.
