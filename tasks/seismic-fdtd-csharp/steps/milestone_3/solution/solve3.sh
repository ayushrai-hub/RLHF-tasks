#!/bin/bash
set -euo pipefail

mkdir -p /app/Seismic /app/output

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

cat > /app/Seismic/ImagingCommand.cs <<'CSEOF'
using System;
using System.IO;
using System.Text.Json;

namespace Seismic;

public static class ImagingCommand
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
        var recvCfg = cfg.GetProperty("receivers");
        double rxStart = recvCfg.GetD("x_start");
        double rxEnd = recvCfg.GetD("x_end");
        int nRx = recvCfg.GetI("n");
        double rxZ = recvCfg.GetD("z");
        string gatherPath = cfg.GetS("shot_gather");
        double dt = cfg.GetD("time_step_s");
        int nSteps = cfg.GetI("n_steps");
        var pml = cfg.GetProperty("pml");
        int pmlT = pml.GetI("thickness");
        double rCoeff = pml.GetD("r_coeff");

        var vp = NpyIo.Read2D(Path.Combine(modelDir, "vp.npy"));
        var vs = NpyIo.Read2D(Path.Combine(modelDir, "vs.npy"));
        var rho = NpyIo.Read2D(Path.Combine(modelDir, "rho.npy"));
        var qp = NpyIo.Read2D(Path.Combine(modelDir, "qp.npy"));
        int nz = vp.GetLength(0);
        int nx = vp.GetLength(1);

        int srcIx = (int)Math.Round(srcX / dx);
        int srcIz = (int)Math.Round(srcZ / dz);
        var rxIx = new int[nRx];
        int rxIz = (int)Math.Round(rxZ / dz);
        for (int r = 0; r < nRx; r++)
        {
            double x = rxStart + (rxEnd - rxStart) * r / (nRx - 1);
            rxIx[r] = (int)Math.Round(x / dx);
        }

        var source = NpyIo.Read1D(srcPath);
        var (gatherFlat, gatherShape) = NpyIo.Read(gatherPath);
        int nT = gatherShape[0];
        int nR = gatherShape[1];
        if (nT < nSteps) nSteps = nT;

        var forward = new float[nSteps][,];
        var simF = new FdtdSim(nz, nx, dx, dz, dt, vp, vs, rho, qp);
        simF.EnablePml(pmlT, rCoeff);
        for (int it = 0; it < nSteps; it++)
        {
            var snap = new float[nz, nx];
            for (int iz = 0; iz < nz; iz++)
                for (int ix = 0; ix < nx; ix++)
                    snap[iz, ix] = simF.Vz[iz, ix];
            forward[it] = snap;
            double s = (it < source.Length) ? source[it] : 0.0;
            simF.Step(s, srcIz, srcIx, "pressure");
        }

        var image = new float[nz, nx];
        var simB = new FdtdSim(nz, nx, dx, dz, dt, vp, vs, rho, qp);
        simB.EnablePml(pmlT, rCoeff);
        for (int it = 0; it < nSteps; it++)
        {
            int tRev = nSteps - 1 - it;
            for (int r = 0; r < nR; r++)
            {
                simB.Vz[rxIz, rxIx[r]] += gatherFlat[tRev * nR + r];
            }
            simB.Step(0.0, 0, 0, "none");
            var fSnap = forward[tRev];
            for (int iz = 0; iz < nz; iz++)
                for (int ix = 0; ix < nx; ix++)
                    image[iz, ix] += fSnap[iz, ix] * simB.Vz[iz, ix];
        }

        NpyIo.Write2D(Path.Combine(outputDir, "image.npy"), image);
        return 0;
    }
}
CSEOF

cat > /app/Seismic/AvoCommand.cs <<'CSEOF'
using System;
using System.Globalization;
using System.IO;
using System.Text;
using System.Text.Json;

namespace Seismic;

public static class AvoCommand
{
    public static int Run(string configPath, string outputPath)
    {
        var cfg = JsonHelpers.Load(configPath);
        string gatherPath = cfg.GetS("shot_gather");
        string timePath = cfg.GetS("time_axis");
        double srcX = cfg.GetD("source_x");
        double srcZ = cfg.GetD("source_z");
        var recvCfg = cfg.GetProperty("receivers");
        double rxStart = recvCfg.GetD("x_start");
        double rxEnd = recvCfg.GetD("x_end");
        int nRx = recvCfg.GetI("n");
        double reflDepth = cfg.GetD("reflector_depth_m");
        var pw = cfg.GetProperty("pick_window_s");
        double tMin = pw[0].GetDouble();
        double tMax = pw[1].GetDouble();

        var (gatherFlat, shape) = NpyIo.Read(gatherPath);
        int nT = shape[0];
        int nR = shape[1];
        var time = NpyIo.Read1D(timePath);

        int idxLo = 0, idxHi = nT - 1;
        for (int i = 0; i < nT; i++)
        {
            if (time[i] < tMin) idxLo = i + 1;
            if (time[i] <= tMax) idxHi = i;
        }
        if (idxHi < idxLo) idxHi = idxLo;

        var offsets = new double[nRx];
        var angles = new double[nRx];
        var amps = new double[nRx];
        for (int r = 0; r < nRx; r++)
        {
            double xr = (nRx == 1) ? rxStart : rxStart + (rxEnd - rxStart) * r / (nRx - 1);
            double off = Math.Abs(xr - srcX);
            offsets[r] = off;
            double dEff = reflDepth - srcZ;
            angles[r] = Math.Atan((off * 0.5) / Math.Max(1e-9, dEff));
            double peak = 0;
            for (int t = idxLo; t <= idxHi; t++)
            {
                float v = gatherFlat[t * nR + r];
                double a = (v < 0) ? -v : v;
                if (a > peak) peak = a;
            }
            amps[r] = peak;
        }

        double sumX = 0, sumY = 0, sumXX = 0, sumXY = 0;
        int n = nRx;
        for (int r = 0; r < n; r++)
        {
            double x = Math.Sin(angles[r]);
            x = x * x;
            double y = amps[r];
            sumX += x; sumY += y; sumXX += x * x; sumXY += x * y;
        }
        double denom = n * sumXX - sumX * sumX;
        double B = (denom == 0) ? 0 : (n * sumXY - sumX * sumY) / denom;
        double A = (sumY - B * sumX) / n;

        var sb = new StringBuilder();
        sb.Append("offset_m,angle_rad,amplitude\n");
        for (int r = 0; r < n; r++)
        {
            sb.Append(offsets[r].ToString("G", CultureInfo.InvariantCulture));
            sb.Append(',');
            sb.Append(angles[r].ToString("G", CultureInfo.InvariantCulture));
            sb.Append(',');
            sb.Append(amps[r].ToString("G", CultureInfo.InvariantCulture));
            sb.Append('\n');
        }
        sb.Append("fit,");
        sb.Append(A.ToString("G", CultureInfo.InvariantCulture));
        sb.Append(',');
        sb.Append(B.ToString("G", CultureInfo.InvariantCulture));
        sb.Append('\n');

        var dir = Path.GetDirectoryName(outputPath);
        if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
        File.WriteAllText(outputPath, sb.ToString());
        return 0;
    }
}
CSEOF

cat > /app/Seismic/QcCommand.cs <<'CSEOF'
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using System.Text.Json;

namespace Seismic;

public static class QcCommand
{
    public static int Run(string configPath, string outputPath)
    {
        var cfg = JsonHelpers.Load(configPath);
        string gatherPath = cfg.GetS("shot_gather");
        string timePath = cfg.GetS("time_axis");
        var srcCfg = cfg.GetProperty("source");
        double srcX = srcCfg.GetD("x");
        double srcZ = srcCfg.GetD("z");
        double fDom = srcCfg.GetD("dominant_frequency_hz");
        var recvCfg = cfg.GetProperty("receivers");
        double rxStart = recvCfg.GetD("x_start");
        double rxEnd = recvCfg.GetD("x_end");
        int nRx = recvCfg.GetI("n");
        double overVp = cfg.GetD("overburden_vp_m_s");
        var nw = cfg.GetProperty("noise_window_s");
        double nLo = nw[0].GetDouble();
        double nHi = nw[1].GetDouble();
        var depths = new List<double>();
        foreach (var d in cfg.GetProperty("target_depths_m").EnumerateArray()) depths.Add(d.GetDouble());
        var xs = new List<double>();
        foreach (var x in cfg.GetProperty("target_xs_m").EnumerateArray()) xs.Add(x.GetDouble());

        var (gatherFlat, shape) = NpyIo.Read(gatherPath);
        int nT = shape[0];
        int nR = shape[1];
        var time = NpyIo.Read1D(timePath);

        double peak = 0;
        for (int i = 0; i < gatherFlat.Length; i++)
        {
            double v = gatherFlat[i];
            if (v < 0) v = -v;
            if (v > peak) peak = v;
        }

        int nLoIdx = 0, nHiIdx = nT - 1;
        for (int i = 0; i < nT; i++)
        {
            if (time[i] < nLo) nLoIdx = i + 1;
            if (time[i] <= nHi) nHiIdx = i;
        }
        double sumSq = 0;
        int cnt = 0;
        for (int t = nLoIdx; t <= nHiIdx; t++)
        {
            for (int r = 0; r < nR; r++)
            {
                double v = gatherFlat[t * nR + r];
                sumSq += v * v;
                cnt++;
            }
        }
        double rms = (cnt > 0) ? Math.Sqrt(sumSq / cnt) : 0.0;
        double snrDb = (rms > 0) ? 20.0 * Math.Log10(peak / rms) : 0.0;
        double lambda = overVp / Math.Max(1e-9, fDom);
        double vertRes = lambda / 4.0;

        var rxs = new double[nRx];
        for (int r = 0; r < nRx; r++)
        {
            rxs[r] = (nRx == 1) ? rxStart : rxStart + (rxEnd - rxStart) * r / (nRx - 1);
        }

        double dxCell = (nRx > 1) ? (rxEnd - rxStart) / (nRx - 1) : 1.0;
        double half = dxCell * 0.5;
        double maxAngle = Math.PI / 4;

        var sb = new StringBuilder();
        sb.Append("{\n");
        sb.Append("  \"snr_db\": ");
        sb.Append(snrDb.ToString("G", CultureInfo.InvariantCulture));
        sb.Append(",\n  \"dominant_wavelength_m\": ");
        sb.Append(lambda.ToString("G", CultureInfo.InvariantCulture));
        sb.Append(",\n  \"vertical_resolution_m\": ");
        sb.Append(vertRes.ToString("G", CultureInfo.InvariantCulture));
        sb.Append(",\n  \"illumination\": [\n");
        bool first = true;
        foreach (var d in depths)
        {
            foreach (var tx in xs)
            {
                int nRays = 0;
                for (int r = 0; r < nRx; r++)
                {
                    double mid = 0.5 * (srcX + rxs[r]);
                    if (Math.Abs(mid - tx) > half) continue;
                    double halfOff = 0.5 * Math.Abs(rxs[r] - srcX);
                    double depthEff = d;
                    double ang = Math.Atan2(halfOff, depthEff);
                    if (ang <= maxAngle) nRays++;
                }
                if (!first) sb.Append(",\n");
                first = false;
                sb.Append("    {\"x\": ");
                sb.Append(tx.ToString("G", CultureInfo.InvariantCulture));
                sb.Append(", \"z\": ");
                sb.Append(d.ToString("G", CultureInfo.InvariantCulture));
                sb.Append(", \"n_rays\": ");
                sb.Append(nRays.ToString(CultureInfo.InvariantCulture));
                sb.Append('}');
            }
        }
        sb.Append("\n  ]\n}\n");

        var dir = Path.GetDirectoryName(outputPath);
        if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
        File.WriteAllText(outputPath, sb.ToString());
        return 0;
    }
}
CSEOF

cat > /app/Seismic/SweepCommand.cs <<'CSEOF'
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using System.Text.Json;

namespace Seismic;

public static class SweepCommand
{
    public static int Run(string configPath, string outputDir)
    {
        Directory.CreateDirectory(outputDir);
        var cfg = JsonHelpers.Load(configPath);
        var baseCfg = cfg.GetProperty("base_config");
        var recvCfg = baseCfg.GetProperty("receivers");

        double rxStart = recvCfg.GetD("x_start");
        double rxEnd = recvCfg.GetD("x_end");
        int nRx = recvCfg.GetI("n");
        double dxCell = (nRx > 1) ? (rxEnd - rxStart) / (nRx - 1) : 1.0;
        double surveyLo = cfg.GetD("survey_x_start");
        double surveyHi = cfg.GetD("survey_x_end");
        double depth = cfg.GetD("target_depth_m");
        var xs = new List<double>();
        foreach (var x in cfg.GetProperty("target_xs_m").EnumerateArray()) xs.Add(x.GetDouble());
        var spacings = new List<double>();
        foreach (var s in cfg.GetProperty("source_spacings_m").EnumerateArray()) spacings.Add(s.GetDouble());

        var rxs = new double[nRx];
        for (int r = 0; r < nRx; r++)
        {
            rxs[r] = (nRx == 1) ? rxStart : rxStart + (rxEnd - rxStart) * r / (nRx - 1);
        }

        double half = dxCell * 0.5;
        double maxAngle = Math.PI / 4;
        int nSp = spacings.Count;
        int nXs = xs.Count;
        var map = new float[nSp, nXs];
        var counts = new int[nSp];

        for (int s = 0; s < nSp; s++)
        {
            double sp = spacings[s];
            var sources = new List<double>();
            double mid = 0.5 * (surveyLo + surveyHi);
            sources.Add(mid);
            for (int k = 1; ; k++)
            {
                double left = mid - k * sp;
                double right = mid + k * sp;
                bool addedAny = false;
                if (left >= surveyLo) { sources.Add(left); addedAny = true; }
                if (right <= surveyHi) { sources.Add(right); addedAny = true; }
                if (!addedAny) break;
            }
            counts[s] = sources.Count;
            for (int j = 0; j < nXs; j++)
            {
                int total = 0;
                foreach (var srcX in sources)
                {
                    for (int r = 0; r < nRx; r++)
                    {
                        double midxr = 0.5 * (srcX + rxs[r]);
                        if (Math.Abs(midxr - xs[j]) > half) continue;
                        double halfOff = 0.5 * Math.Abs(rxs[r] - srcX);
                        double ang = Math.Atan2(halfOff, depth);
                        if (ang <= maxAngle) total++;
                    }
                }
                map[s, j] = total;
            }
        }

        NpyIo.Write2D(Path.Combine(outputDir, "illumination_map.npy"), map);

        var sb = new StringBuilder();
        sb.Append("spacing_m,n_sources\n");
        for (int s = 0; s < nSp; s++)
        {
            sb.Append(spacings[s].ToString("G", CultureInfo.InvariantCulture));
            sb.Append(',');
            sb.Append(counts[s].ToString(CultureInfo.InvariantCulture));
            sb.Append('\n');
        }
        File.WriteAllText(Path.Combine(outputDir, "parameters.csv"), sb.ToString());
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
                case "image":
                    if (args.Length < 3) { Console.Error.WriteLine("usage: seismic image <input.json> <output_dir>"); return 1; }
                    return ImagingCommand.Run(args[1], args[2]);
                case "avo":
                    if (args.Length < 3) { Console.Error.WriteLine("usage: seismic avo <input.json> <output.csv>"); return 1; }
                    return AvoCommand.Run(args[1], args[2]);
                case "qc":
                    if (args.Length < 3) { Console.Error.WriteLine("usage: seismic qc <input.json> <output.json>"); return 1; }
                    return QcCommand.Run(args[1], args[2]);
                case "sweep":
                    if (args.Length < 3) { Console.Error.WriteLine("usage: seismic sweep <input.json> <output_dir>"); return 1; }
                    return SweepCommand.Run(args[1], args[2]);
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

/app/seismic model /app/fixtures/model_two_layer.json /app/output/model_two_layer
/app/seismic source /app/fixtures/source_ricker20.json /app/output/source_ricker20.npy
/app/seismic simulate /app/fixtures/sim_two_layer.json /app/output/sim_two_layer

/app/seismic image /app/fixtures/rtm_two_layer.json /app/output/rtm_two_layer
/app/seismic avo /app/fixtures/avo_two_layer.json /app/output/avo_two_layer.csv
/app/seismic qc /app/fixtures/qc_two_layer.json /app/output/qc_two_layer.json
/app/seismic sweep /app/fixtures/sweep_two_layer.json /app/output/sweep_two_layer

find /tmp -mindepth 1 -delete 2>/dev/null || true
