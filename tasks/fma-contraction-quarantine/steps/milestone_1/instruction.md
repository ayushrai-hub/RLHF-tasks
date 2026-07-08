The geokern library in /app holds ten small double precision kernels plus a shared helper, and it builds two ways. The Makefile carries a strict profile and the aggressive release profile the performance team switched on for shipping. Same source, two flag sets, and sometimes two different answers come out.

Your first job is to find, for every kernel, whether the release build and the strict build actually produce different bits on some input. The arguments under samples were picked to look clean, so do not trust them to settle the question. When a kernel does differ, you need one concrete input that shows it.

Write your answer to /app/output/result_1.json, a JSON object mapping each kernel name to an object with a boolean diverges and, when that is true, a witness array holding the input arguments that make the two builds disagree. Anything you leave on disk stays readable later.
