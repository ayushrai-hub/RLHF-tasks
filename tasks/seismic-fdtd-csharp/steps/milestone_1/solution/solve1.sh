#!/bin/bash
set -euo pipefail

mkdir -p /app/Seismic

cat > /app/Seismic/Models.cs <<'CSEOF'
using System.Collections.Generic;

namespace Seismic;

public sealed class LayerSpec
{
    public double TopZ;
    public double BottomZ;
    public double Vp;
    public double Vs;
    public double Rho;
    public double Qp;
    public double Qs;
}

public sealed class SaltBody
{
    public List<(double X, double Z)> Polygon = new();
    public double Vp;
    public double Vs;
    public double Rho;
    public double Qp;
    public double Qs;
}

public sealed class FaultSpec
{
    public double X0;
    public double Z0;
    public double X1;
    public double Z1;
    public double Throw;
}

public sealed class ModelSpec
{
    public int Nx;
    public int Nz;
    public double Dx;
    public double Dz;
    public List<LayerSpec> Layers = new();
    public List<SaltBody> Salts = new();
    public List<FaultSpec> Faults = new();
}
CSEOF

cat > /app/Seismic/JsonHelpers.cs <<'CSEOF'
using System.IO;
using System.Text.Json;

namespace Seismic;

public static class JsonHelpers
{
    public static JsonElement Load(string path)
    {
        using var doc = JsonDocument.Parse(File.ReadAllText(path));
        return doc.RootElement.Clone();
    }

    public static double GetD(this JsonElement e, string name)
    {
        return e.GetProperty(name).GetDouble();
    }

    public static int GetI(this JsonElement e, string name)
    {
        return e.GetProperty(name).GetInt32();
    }

    public static string GetS(this JsonElement e, string name)
    {
        return e.GetProperty(name).GetString() ?? "";
    }

    public static bool Has(this JsonElement e, string name, out JsonElement v)
    {
        return e.TryGetProperty(name, out v);
    }
}
CSEOF

cat > /app/Seismic/NpyIo.cs <<'CSEOF'
using System;
using System.IO;
using System.Text;

namespace Seismic;

public static class NpyIo
{
    public static void Write1D(string path, float[] data)
    {
        var header = $"{{'descr': '<f4', 'fortran_order': False, 'shape': ({data.Length},), }}";
        using var fs = File.Create(path);
        WriteHeader(fs, header);
        var bytes = new byte[data.Length * 4];
        Buffer.BlockCopy(data, 0, bytes, 0, bytes.Length);
        fs.Write(bytes);
    }

    public static void Write2D(string path, float[,] data)
    {
        int nz = data.GetLength(0);
        int nx = data.GetLength(1);
        var header = $"{{'descr': '<f4', 'fortran_order': False, 'shape': ({nz}, {nx}), }}";
        using var fs = File.Create(path);
        WriteHeader(fs, header);
        var rowFloats = new float[nx];
        var rowBytes = new byte[nx * 4];
        for (int iz = 0; iz < nz; iz++)
        {
            for (int ix = 0; ix < nx; ix++) rowFloats[ix] = data[iz, ix];
            Buffer.BlockCopy(rowFloats, 0, rowBytes, 0, rowBytes.Length);
            fs.Write(rowBytes);
        }
    }

    private static void WriteHeader(Stream fs, string header)
    {
        fs.Write(new byte[] { 0x93, (byte)'N', (byte)'U', (byte)'M', (byte)'P', (byte)'Y' });
        fs.WriteByte(1);
        fs.WriteByte(0);
        int unpadded = 10 + header.Length + 1;
        int target = ((unpadded + 63) / 64) * 64;
        int totalHeader = target - 10;
        int padLen = totalHeader - header.Length - 1;
        fs.WriteByte((byte)(totalHeader & 0xff));
        fs.WriteByte((byte)((totalHeader >> 8) & 0xff));
        fs.Write(Encoding.ASCII.GetBytes(header));
        for (int i = 0; i < padLen; i++) fs.WriteByte((byte)' ');
        fs.WriteByte((byte)'\n');
    }
}
CSEOF

cat > /app/Seismic/ModelBuilder.cs <<'CSEOF'
using System.Collections.Generic;
using System.Text.Json;

namespace Seismic;

public static class ModelBuilder
{
    public static ModelSpec Parse(string path)
    {
        var root = JsonHelpers.Load(path);
        var grid = root.GetProperty("grid");
        var m = new ModelSpec
        {
            Nx = grid.GetI("nx"),
            Nz = grid.GetI("nz"),
            Dx = grid.GetD("dx"),
            Dz = grid.GetD("dz"),
        };

        foreach (var l in root.GetProperty("layers").EnumerateArray())
        {
            m.Layers.Add(new LayerSpec
            {
                TopZ = l.GetD("top_z"),
                BottomZ = l.GetD("bottom_z"),
                Vp = l.GetD("vp"),
                Vs = l.GetD("vs"),
                Rho = l.GetD("rho"),
                Qp = l.GetD("qp"),
                Qs = l.GetD("qs"),
            });
        }

        if (root.Has("salt_bodies", out var salts) && salts.ValueKind == JsonValueKind.Array)
        {
            foreach (var s in salts.EnumerateArray())
            {
                var sb = new SaltBody
                {
                    Vp = s.GetD("vp"),
                    Vs = s.GetD("vs"),
                    Rho = s.GetD("rho"),
                    Qp = s.GetD("qp"),
                    Qs = s.GetD("qs"),
                };
                foreach (var v in s.GetProperty("polygon").EnumerateArray())
                {
                    sb.Polygon.Add((v[0].GetDouble(), v[1].GetDouble()));
                }
                m.Salts.Add(sb);
            }
        }

        if (root.Has("faults", out var faults) && faults.ValueKind == JsonValueKind.Array)
        {
            foreach (var f in faults.EnumerateArray())
            {
                m.Faults.Add(new FaultSpec
                {
                    X0 = f.GetD("x0"),
                    Z0 = f.GetD("z0"),
                    X1 = f.GetD("x1"),
                    Z1 = f.GetD("z1"),
                    Throw = f.GetD("throw"),
                });
            }
        }
        return m;
    }

    public static (float[,] Vp, float[,] Vs, float[,] Rho, float[,] Qp, float[,] Qs) Rasterize(ModelSpec m)
    {
        int nz = m.Nz, nx = m.Nx;
        var vp = new float[nz, nx];
        var vs = new float[nz, nx];
        var rho = new float[nz, nx];
        var qp = new float[nz, nx];
        var qs = new float[nz, nx];

        for (int iz = 0; iz < nz; iz++)
        {
            double cz = iz * m.Dz;
            for (int ix = 0; ix < nx; ix++)
            {
                double cx = ix * m.Dx;
                double lookupZ = cz;
                foreach (var f in m.Faults)
                {
                    double cross = (f.Z1 - f.Z0) * (cx - f.X0) - (f.X1 - f.X0) * (cz - f.Z0);
                    if (cross > 0)
                    {
                        lookupZ -= f.Throw;
                    }
                }
                var layer = FindLayer(m.Layers, lookupZ);
                double Pv = layer.Vp, Sv = layer.Vs, R = layer.Rho, QP = layer.Qp, QS = layer.Qs;
                foreach (var s in m.Salts)
                {
                    if (PointInPolygon(s.Polygon, cx, cz))
                    {
                        Pv = s.Vp; Sv = s.Vs; R = s.Rho; QP = s.Qp; QS = s.Qs;
                        break;
                    }
                }
                vp[iz, ix] = (float)Pv;
                vs[iz, ix] = (float)Sv;
                rho[iz, ix] = (float)R;
                qp[iz, ix] = (float)QP;
                qs[iz, ix] = (float)QS;
            }
        }
        return (vp, vs, rho, qp, qs);
    }

    private static LayerSpec FindLayer(List<LayerSpec> layers, double z)
    {
        foreach (var l in layers)
        {
            if (l.TopZ <= z && z < l.BottomZ) return l;
        }
        if (z < layers[0].TopZ) return layers[0];
        return layers[^1];
    }

    private static bool PointInPolygon(List<(double X, double Z)> poly, double px, double pz)
    {
        bool inside = false;
        int n = poly.Count;
        for (int i = 0, j = n - 1; i < n; j = i++)
        {
            var (xi, zi) = poly[i];
            var (xj, zj) = poly[j];
            bool crosses = ((zi > pz) != (zj > pz)) && (px < (xj - xi) * (pz - zi) / (zj - zi) + xi);
            if (crosses) inside = !inside;
        }
        return inside;
    }
}
CSEOF

cat > /app/Seismic/SourceWavelets.cs <<'CSEOF'
using System;

namespace Seismic;

public static class SourceWavelets
{
    public static float[] Generate(string path)
    {
        var root = JsonHelpers.Load(path);
        string type = root.GetS("type");
        double sr = root.GetD("sample_rate_hz");
        double T = root.GetD("duration_s");
        int n = (int)Math.Round(T * sr);
        double dt = 1.0 / sr;
        var w = new float[n];
        switch (type)
        {
            case "ricker":
                Ricker(w, dt, root.GetD("dominant_frequency_hz"), root.GetD("delay_s"));
                break;
            case "explosive":
                Explosive(w, dt, root.GetD("dominant_frequency_hz"), root.GetD("delay_s"));
                break;
            case "vibroseis":
                Vibroseis(w, dt, T, root.GetD("f_start_hz"), root.GetD("f_end_hz"), root.GetD("taper_fraction"));
                break;
            default:
                throw new ArgumentException("unknown source type: " + type);
        }
        Normalize(w);
        return w;
    }

    private static void Ricker(float[] w, double dt, double f, double t0)
    {
        double pf = Math.PI * f;
        for (int i = 0; i < w.Length; i++)
        {
            double t = i * dt - t0;
            double a = pf * t;
            double a2 = a * a;
            w[i] = (float)((1.0 - 2.0 * a2) * Math.Exp(-a2));
        }
    }

    private static void Explosive(float[] w, double dt, double f, double t0)
    {
        double alpha = 2.0 * Math.PI * Math.PI * f * f;
        for (int i = 0; i < w.Length; i++)
        {
            double t = i * dt - t0;
            w[i] = (float)(-2.0 * alpha * t * Math.Exp(-alpha * t * t));
        }
    }

    private static void Vibroseis(float[] w, double dt, double T, double f0, double f1, double taperFrac)
    {
        double k = (f1 - f0) / T;
        int n = w.Length;
        int taperN = (int)Math.Round(taperFrac * n);
        if (taperN < 0) taperN = 0;
        if (taperN > n / 2) taperN = n / 2;
        for (int i = 0; i < n; i++)
        {
            double t = i * dt;
            double phase = 2.0 * Math.PI * (f0 * t + 0.5 * k * t * t);
            double signal = Math.Sin(phase);
            double window = 1.0;
            if (taperN > 0)
            {
                if (i < taperN)
                {
                    window = 0.5 * (1.0 - Math.Cos(Math.PI * i / taperN));
                }
                else if (i >= n - taperN)
                {
                    int j = i - (n - taperN);
                    window = 0.5 * (1.0 + Math.Cos(Math.PI * j / taperN));
                }
            }
            w[i] = (float)(window * signal);
        }
    }

    private static void Normalize(float[] w)
    {
        float m = 0;
        for (int i = 0; i < w.Length; i++)
        {
            float a = Math.Abs(w[i]);
            if (a > m) m = a;
        }
        if (m > 0)
        {
            for (int i = 0; i < w.Length; i++) w[i] /= m;
        }
    }
}
CSEOF

cat > /app/Seismic/Program.cs <<'CSEOF'
using System;
using System.IO;

namespace Seismic;

public static class Program
{
    public static int Main(string[] args)
    {
        if (args.Length == 0)
        {
            Console.Error.WriteLine("usage: seismic <subcommand> [args...]");
            return 1;
        }
        try
        {
            switch (args[0])
            {
                case "model":
                    if (args.Length < 3) { Console.Error.WriteLine("usage: seismic model <input.json> <output_dir>"); return 1; }
                    return ModelCommand.Run(args[1], args[2]);
                case "source":
                    if (args.Length < 3) { Console.Error.WriteLine("usage: seismic source <input.json> <output.npy>"); return 1; }
                    return SourceCommand.Run(args[1], args[2]);
                default:
                    Console.Error.WriteLine("unknown subcommand: " + args[0]);
                    return 1;
            }
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("error: " + ex.Message);
            return 2;
        }
    }
}

public static class ModelCommand
{
    public static int Run(string inputPath, string outputDir)
    {
        Directory.CreateDirectory(outputDir);
        var spec = ModelBuilder.Parse(inputPath);
        var (vp, vs, rho, qp, qs) = ModelBuilder.Rasterize(spec);
        NpyIo.Write2D(Path.Combine(outputDir, "vp.npy"), vp);
        NpyIo.Write2D(Path.Combine(outputDir, "vs.npy"), vs);
        NpyIo.Write2D(Path.Combine(outputDir, "rho.npy"), rho);
        NpyIo.Write2D(Path.Combine(outputDir, "qp.npy"), qp);
        NpyIo.Write2D(Path.Combine(outputDir, "qs.npy"), qs);
        return 0;
    }
}

public static class SourceCommand
{
    public static int Run(string inputPath, string outputPath)
    {
        var w = SourceWavelets.Generate(inputPath);
        var dir = Path.GetDirectoryName(outputPath);
        if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
        NpyIo.Write1D(outputPath, w);
        return 0;
    }
}
CSEOF

cd /app/Seismic
dotnet build -c Release --nologo --verbosity quiet

cat > /app/seismic <<'WRAPEOF'
#!/bin/bash
exec dotnet /app/Seismic/bin/Release/net8.0/Seismic.dll "$@"
WRAPEOF
chmod +x /app/seismic

find /tmp -mindepth 1 -delete 2>/dev/null || true
