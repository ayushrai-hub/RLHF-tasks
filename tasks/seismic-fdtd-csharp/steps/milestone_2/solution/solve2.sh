#!/bin/bash
set -euo pipefail

mkdir -p /app/Seismic /app/output

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

    public static (float[] Data, int[] Shape) Read(string path)
    {
        using var fs = File.OpenRead(path);
        var magic = new byte[6];
        fs.ReadExactly(magic);
        if (magic[0] != 0x93 || magic[1] != (byte)'N' || magic[2] != (byte)'U' || magic[3] != (byte)'M')
            throw new IOException("Not an NPY file: " + path);
        int major = fs.ReadByte();
        fs.ReadByte();
        int headerLen;
        if (major == 1)
        {
            int lo = fs.ReadByte();
            int hi = fs.ReadByte();
            headerLen = lo | (hi << 8);
        }
        else
        {
            var hb = new byte[4];
            fs.ReadExactly(hb);
            headerLen = hb[0] | (hb[1] << 8) | (hb[2] << 16) | (hb[3] << 24);
        }
        var hbytes = new byte[headerLen];
        fs.ReadExactly(hbytes);
        var header = Encoding.ASCII.GetString(hbytes);
        int sIdx = header.IndexOf("'shape'", StringComparison.Ordinal);
        int sOpen = header.IndexOf('(', sIdx);
        int sClose = header.IndexOf(')', sOpen);
        var shapeStr = header.Substring(sOpen + 1, sClose - sOpen - 1).Trim();
        var parts = shapeStr.Split(',');
        var shapeList = new System.Collections.Generic.List<int>();
        foreach (var p in parts)
        {
            var pt = p.Trim();
            if (pt.Length == 0) continue;
            shapeList.Add(int.Parse(pt));
        }
        int n = 1;
        foreach (var d in shapeList) n *= d;
        var raw = new byte[n * 4];
        fs.ReadExactly(raw);
        var data = new float[n];
        Buffer.BlockCopy(raw, 0, data, 0, raw.Length);
        return (data, shapeList.ToArray());
    }

    public static float[,] Read2D(string path)
    {
        var (data, shape) = Read(path);
        if (shape.Length != 2) throw new ArgumentException("expected 2D array: " + path);
        int nz = shape[0], nx = shape[1];
        var arr = new float[nz, nx];
        for (int iz = 0; iz < nz; iz++)
            for (int ix = 0; ix < nx; ix++)
                arr[iz, ix] = data[iz * nx + ix];
        return arr;
    }

    public static float[] Read1D(string path)
    {
        var (data, shape) = Read(path);
        return data;
    }
}
CSEOF

cat > /app/Seismic/Fdtd.cs <<'CSEOF'
using System;

namespace Seismic;

public sealed class FdtdSim
{
    public int Nz;
    public int Nx;
    public double Dx;
    public double Dz;
    public double Dt;

    public float[,] Rho;
    public float[,] Qp;
    public float[,] Lam;
    public float[,] Mu;

    public float[,] Vx;
    public float[,] Vz;
    public float[,] Sxx;
    public float[,] Szz;
    public float[,] Sxz;

    public bool PmlEnabled;
    public bool AttenEnabled;
    public float[,] DampMul;
    public float[,] AttenMul;

    public FdtdSim(int nz, int nx, double dx, double dz, double dt,
                   float[,] vp, float[,] vs, float[,] rho, float[,] qp)
    {
        Nz = nz; Nx = nx; Dx = dx; Dz = dz; Dt = dt;
        Rho = rho; Qp = qp;
        Lam = new float[nz, nx];
        Mu = new float[nz, nx];
        for (int iz = 0; iz < nz; iz++)
        {
            for (int ix = 0; ix < nx; ix++)
            {
                double vpv = vp[iz, ix];
                double vsv = vs[iz, ix];
                double r = rho[iz, ix];
                double mu = r * vsv * vsv;
                double lam = r * vpv * vpv - 2.0 * mu;
                Lam[iz, ix] = (float)lam;
                Mu[iz, ix] = (float)mu;
            }
        }
        Vx = new float[nz, nx];
        Vz = new float[nz, nx];
        Sxx = new float[nz, nx];
        Szz = new float[nz, nx];
        Sxz = new float[nz, nx];
        DampMul = new float[nz, nx];
        AttenMul = new float[nz, nx];
        for (int iz = 0; iz < nz; iz++)
            for (int ix = 0; ix < nx; ix++)
            {
                DampMul[iz, ix] = 1.0f;
                AttenMul[iz, ix] = 1.0f;
            }
    }

    public void EnablePml(int thickness, double rCoeff)
    {
        PmlEnabled = true;
        double absLogR = Math.Abs(Math.Log(rCoeff));
        double dMax = 3.0 * absLogR / (thickness * Dt);
        for (int iz = 0; iz < Nz; iz++)
        {
            int dz_in = 0;
            if (iz < thickness) dz_in = Math.Max(dz_in, thickness - iz);
            if (iz >= Nz - thickness) dz_in = Math.Max(dz_in, iz - (Nz - thickness - 1));
            for (int ix = 0; ix < Nx; ix++)
            {
                int dx_in = 0;
                if (ix < thickness) dx_in = Math.Max(dx_in, thickness - ix);
                if (ix >= Nx - thickness) dx_in = Math.Max(dx_in, ix - (Nx - thickness - 1));
                int d = Math.Max(dx_in, dz_in);
                if (d > 0)
                {
                    double depth = (double)d / thickness;
                    double damping = dMax * depth * depth;
                    DampMul[iz, ix] = (float)Math.Exp(-damping * Dt);
                }
            }
        }
    }

    public void EnableAttenuation(double fRef)
    {
        AttenEnabled = true;
        double piF = Math.PI * fRef * Dt;
        for (int iz = 0; iz < Nz; iz++)
        {
            for (int ix = 0; ix < Nx; ix++)
            {
                double q = Qp[iz, ix];
                if (q <= 0 || double.IsInfinity(q) || q > 1e5)
                {
                    AttenMul[iz, ix] = 1.0f;
                    continue;
                }
                AttenMul[iz, ix] = (float)Math.Exp(-piF / q);
            }
        }
    }

    public void Step(double sourceVal, int srcIz, int srcIx, string srcKind)
    {
        double invDx = 1.0 / Dx;
        double invDz = 1.0 / Dz;

        for (int iz = 1; iz < Nz - 1; iz++)
        {
            for (int ix = 0; ix < Nx - 1; ix++)
            {
                double dSxxDx = (Sxx[iz, ix + 1] - Sxx[iz, ix]) * invDx;
                double dSxzDz = (Sxz[iz, ix] - Sxz[iz - 1, ix]) * invDz;
                double r = Rho[iz, ix];
                if (r > 0)
                    Vx[iz, ix] += (float)(Dt * (dSxxDx + dSxzDz) / r);
            }
        }
        for (int iz = 0; iz < Nz - 1; iz++)
        {
            for (int ix = 1; ix < Nx - 1; ix++)
            {
                double dSxzDx = (Sxz[iz, ix] - Sxz[iz, ix - 1]) * invDx;
                double dSzzDz = (Szz[iz + 1, ix] - Szz[iz, ix]) * invDz;
                double r = Rho[iz, ix];
                if (r > 0)
                    Vz[iz, ix] += (float)(Dt * (dSxzDx + dSzzDz) / r);
            }
        }

        if (srcKind == "vz")
        {
            Vz[srcIz, srcIx] += (float)sourceVal;
        }

        if (PmlEnabled)
        {
            for (int iz = 0; iz < Nz; iz++)
            {
                for (int ix = 0; ix < Nx; ix++)
                {
                    float m = DampMul[iz, ix];
                    if (m != 1.0f)
                    {
                        Vx[iz, ix] *= m;
                        Vz[iz, ix] *= m;
                    }
                }
            }
        }

        for (int iz = 1; iz < Nz; iz++)
        {
            for (int ix = 1; ix < Nx; ix++)
            {
                double dVxDx = (Vx[iz, ix] - Vx[iz, ix - 1]) * invDx;
                double dVzDz = (Vz[iz, ix] - Vz[iz - 1, ix]) * invDz;
                double l = Lam[iz, ix];
                double m = Mu[iz, ix];
                Sxx[iz, ix] += (float)(Dt * ((l + 2 * m) * dVxDx + l * dVzDz));
                Szz[iz, ix] += (float)(Dt * (l * dVxDx + (l + 2 * m) * dVzDz));
            }
        }
        for (int iz = 0; iz < Nz - 1; iz++)
        {
            for (int ix = 0; ix < Nx - 1; ix++)
            {
                double dVxDz = (Vx[iz + 1, ix] - Vx[iz, ix]) * invDz;
                double dVzDx = (Vz[iz, ix + 1] - Vz[iz, ix]) * invDx;
                double m = Mu[iz, ix];
                Sxz[iz, ix] += (float)(Dt * m * (dVxDz + dVzDx));
            }
        }

        if (srcKind == "pressure")
        {
            Sxx[srcIz, srcIx] += (float)sourceVal;
            Szz[srcIz, srcIx] += (float)sourceVal;
        }

        if (AttenEnabled)
        {
            for (int iz = 0; iz < Nz; iz++)
            {
                for (int ix = 0; ix < Nx; ix++)
                {
                    float m = AttenMul[iz, ix];
                    if (m != 1.0f)
                    {
                        Sxx[iz, ix] *= m;
                        Szz[iz, ix] *= m;
                        Sxz[iz, ix] *= m;
                    }
                }
            }
        }

        if (PmlEnabled)
        {
            for (int iz = 0; iz < Nz; iz++)
            {
                for (int ix = 0; ix < Nx; ix++)
                {
                    float m = DampMul[iz, ix];
                    if (m != 1.0f)
                    {
                        Sxx[iz, ix] *= m;
                        Szz[iz, ix] *= m;
                        Sxz[iz, ix] *= m;
                    }
                }
            }
        }
    }
}
CSEOF

cat > /app/Seismic/SimulateCommand.cs <<'CSEOF'
using System;
using System.IO;
using System.Text.Json;

namespace Seismic;

public static class SimulateCommand
{
    public static int Run(string configPath, string outputDir)
    {
        Directory.CreateDirectory(outputDir);
        var cfg = JsonHelpers.Load(configPath);
        string modelDir = cfg.GetS("model_dir");
        var grid = cfg.GetProperty("grid");
        double dx = grid.GetD("dx");
        double dz = grid.GetD("dz");
        var srcCfg = cfg.GetProperty("source");
        string srcPath = srcCfg.GetS("path");
        double srcX = srcCfg.GetD("x");
        double srcZ = srcCfg.GetD("z");
        string srcKind = srcCfg.GetS("kind");
        var recvCfg = cfg.GetProperty("receivers");
        double rxStart = recvCfg.GetD("x_start");
        double rxEnd = recvCfg.GetD("x_end");
        int nRx = recvCfg.GetI("n");
        double rxZ = recvCfg.GetD("z");
        double dt = cfg.GetD("time_step_s");
        int nSteps = cfg.GetI("n_steps");
        var pml = cfg.GetProperty("pml");
        bool pmlEnabled = pml.GetProperty("enabled").GetBoolean();
        int pmlT = pml.GetI("thickness");
        double rCoeff = pml.GetD("r_coeff");
        var atten = cfg.GetProperty("attenuation");
        bool attenEnabled = atten.GetProperty("enabled").GetBoolean();
        double fRef = atten.GetD("reference_frequency_hz");
        int snapInt = cfg.GetI("snapshot_interval");

        var vp = NpyIo.Read2D(Path.Combine(modelDir, "vp.npy"));
        var vs = NpyIo.Read2D(Path.Combine(modelDir, "vs.npy"));
        var rho = NpyIo.Read2D(Path.Combine(modelDir, "rho.npy"));
        var qp = NpyIo.Read2D(Path.Combine(modelDir, "qp.npy"));
        int nz = vp.GetLength(0);
        int nx = vp.GetLength(1);

        var sim = new FdtdSim(nz, nx, dx, dz, dt, vp, vs, rho, qp);
        if (pmlEnabled) sim.EnablePml(pmlT, rCoeff);
        if (attenEnabled) sim.EnableAttenuation(fRef);

        var source = NpyIo.Read1D(srcPath);
        int srcIx = (int)Math.Round(srcX / dx);
        int srcIz = (int)Math.Round(srcZ / dz);
        if (srcIx < 0) srcIx = 0; if (srcIx >= nx) srcIx = nx - 1;
        if (srcIz < 0) srcIz = 0; if (srcIz >= nz) srcIz = nz - 1;

        var rxIx = new int[nRx];
        int rxIz = (int)Math.Round(rxZ / dz);
        if (rxIz < 0) rxIz = 0; if (rxIz >= nz) rxIz = nz - 1;
        if (nRx == 1)
        {
            rxIx[0] = (int)Math.Round(rxStart / dx);
        }
        else
        {
            for (int r = 0; r < nRx; r++)
            {
                double x = rxStart + (rxEnd - rxStart) * r / (nRx - 1);
                rxIx[r] = (int)Math.Round(x / dx);
                if (rxIx[r] < 0) rxIx[r] = 0;
                if (rxIx[r] >= nx) rxIx[r] = nx - 1;
            }
        }

        var gather = new float[nSteps, nRx];
        var time = new float[nSteps];
        string snapDir = Path.Combine(outputDir, "snapshots");
        if (snapInt > 0) Directory.CreateDirectory(snapDir);

        for (int it = 0; it < nSteps; it++)
        {
            time[it] = (float)(it * dt);
            for (int r = 0; r < nRx; r++)
            {
                gather[it, r] = sim.Vz[rxIz, rxIx[r]];
            }
            if (snapInt > 0 && it % snapInt == 0)
            {
                string p = Path.Combine(snapDir, $"snap_{it:D6}.npy");
                NpyIo.Write2D(p, sim.Vz);
            }
            double s = (it < source.Length) ? source[it] : 0.0;
            sim.Step(s, srcIz, srcIx, srcKind);
        }

        NpyIo.Write2D(Path.Combine(outputDir, "shot_gather.npy"), gather);
        NpyIo.Write1D(Path.Combine(outputDir, "time.npy"), time);
        return 0;
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
                case "simulate":
                    if (args.Length < 3) { Console.Error.WriteLine("usage: seismic simulate <input.json> <output_dir>"); return 1; }
                    return SimulateCommand.Run(args[1], args[2]);
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

/app/seismic model /app/fixtures/model_homo.json /app/output/model_homo
/app/seismic model /app/fixtures/model_homo_elastic.json /app/output/model_homo_elastic
/app/seismic model /app/fixtures/model_two_layer.json /app/output/model_two_layer
/app/seismic source /app/fixtures/source_ricker25.json /app/output/source_ricker25.npy
/app/seismic source /app/fixtures/source_ricker20.json /app/output/source_ricker20.npy

/app/seismic simulate /app/fixtures/sim_homo_off.json /app/output/sim_homo_off
/app/seismic simulate /app/fixtures/sim_homo_on.json /app/output/sim_homo_on
/app/seismic simulate /app/fixtures/sim_homo_attn.json /app/output/sim_homo_attn
/app/seismic simulate /app/fixtures/sim_homo_vz.json /app/output/sim_homo_vz
/app/seismic simulate /app/fixtures/sim_homo_swave.json /app/output/sim_homo_swave
/app/seismic simulate /app/fixtures/sim_two_layer.json /app/output/sim_two_layer

find /tmp -mindepth 1 -delete 2>/dev/null || true
