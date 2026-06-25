# Build

The .NET 8 SDK is preinstalled and NuGet is restored offline at image-build
time. Internet access is blocked at runtime, so do not add new package
references.

Standard build commands from /app/Seismic:

    dotnet build -c Release --nologo --verbosity quiet

The compiled dll lands at /app/Seismic/bin/Release/net8.0/Seismic.dll.

The wrapper script at /app/seismic should be a one-line bash script that execs
the dll with all forwarded arguments. Mark it executable.

The /app/scripts/build.sh helper rebuilds the project from a clean working
directory. /app/scripts/clean.sh deletes bin/obj. /app/scripts/run.sh is a
convenience wrapper around the dll.
