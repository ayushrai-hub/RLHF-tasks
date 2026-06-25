# Architecture

The Seismic project at /app/Seismic is a single .NET 8 executable. It exposes a
small set of subcommands invoked through the shell wrapper at /app/seismic.

The build pipeline is plain `dotnet build -c Release` from /app/Seismic. The
wrapper script forwards arguments to the built dll. The compiled dll lives at
/app/Seismic/bin/Release/net8.0/Seismic.dll.

Inputs and outputs use simple text or binary formats so they are easy to
inspect from Python or the shell:

- JSON for configuration (model definitions, source specs, sim configs)
- NumPy NPY for floating-point arrays (model grids, snapshots, shot gathers,
  RTM images)
- CSV for tabular outputs (AVO trend points)

NPY format details are in /app/docs/npy_format.md.

The codebase grows over three milestones. Milestone 1 stands up the model and
source specification layer. Milestone 2 adds the FDTD engine with boundary and
attenuation logic. Milestone 3 builds the imaging, QC, and parametric study
tooling on top.
