using System;

namespace Seismic;

public static class Program
{
    public static int Main(string[] args)
    {
        if (args.Length == 0)
        {
            Console.Error.WriteLine("usage: seismic <subcommand> [args...]");
            Console.Error.WriteLine("subcommands: model, source, simulate, image, avo, qc, sweep");
            return 1;
        }

        Console.Error.WriteLine("subcommand not implemented: " + args[0]);
        return 1;
    }
}
