// Pont Kinect v1 -> page web du module 4, sous Windows avec le Kinect for Windows SDK 1.8
// (vrai squelette : 20 articulations). Même format que kinect_bridge.py :
//   {"bodies":[{"center":[x,y],"z":m,"joints":{"head":[x,y],"handL":[x,y],...}}]}
// Coordonnées normalisées 0..1, image en miroir, y vers le bas. Servi sur ws://localhost:8765/.
// Compilation : build.bat (aucun Visual Studio requis).
using System;
using System.Globalization;
using System.Linq;
using System.Net;
using System.Net.WebSockets;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.Kinect;

class KinectBridge
{
    const string EMPTY = "{\"bodies\":[]}";
    static volatile string latest = EMPTY;
    static DateTime lastFrame = DateTime.MinValue;
    static KinectSensor sensor;
    static Skeleton[] skeletons;

    static readonly string[] NAMES = { "head", "neck", "shoulderL", "shoulderR", "elbowL", "elbowR",
        "handL", "handR", "hip", "kneeL", "kneeR", "footL", "footR" };
    static readonly JointType[] TYPES = { JointType.Head, JointType.ShoulderCenter, JointType.ShoulderLeft,
        JointType.ShoulderRight, JointType.ElbowLeft, JointType.ElbowRight, JointType.HandLeft,
        JointType.HandRight, JointType.HipCenter, JointType.KneeLeft, JointType.KneeRight,
        JointType.FootLeft, JointType.FootRight };

    static void Main(string[] args)
    {
        var listener = new HttpListener();
        listener.Prefixes.Add("http://localhost:8765/");
        listener.Start();
        Task.Run(() => AcceptLoop(listener));
        Console.WriteLine("Pont Kinect sur ws://localhost:8765/");

        while (true)
        {
            if (sensor == null || sensor.Status != KinectStatus.Connected) Connect();
            Thread.Sleep(2000);
        }
    }

    static void Connect()
    {
        if (sensor != null) { try { sensor.Stop(); } catch { } sensor = null; }
        sensor = KinectSensor.KinectSensors.FirstOrDefault(s => s.Status == KinectStatus.Connected);
        if (sensor == null) { Console.WriteLine("En attente de la Kinect..."); return; }
        sensor.DepthStream.Enable(DepthImageFormat.Resolution640x480Fps30);
        sensor.SkeletonStream.Enable(new TransformSmoothParameters {
            Smoothing = 0.5f, Correction = 0.5f, Prediction = 0.4f, JitterRadius = 0.05f, MaxDeviationRadius = 0.04f });
        skeletons = new Skeleton[sensor.SkeletonStream.FrameSkeletonArrayLength];
        sensor.SkeletonFrameReady += OnFrame;
        sensor.Start();
        Console.WriteLine("Kinect connectee.");
    }

    static void OnFrame(object s, SkeletonFrameReadyEventArgs e)
    {
        using (var frame = e.OpenSkeletonFrame())
        {
            if (frame == null) return;
            frame.CopySkeletonDataTo(skeletons);
        }
        lastFrame = DateTime.Now;
        // La personne la plus proche du centre (donc de la croix)
        var sk = skeletons.Where(k => k.TrackingState == SkeletonTrackingState.Tracked)
                          .OrderBy(k => Math.Abs(k.Position.X)).FirstOrDefault();
        if (sk == null) { latest = EMPTY; return; }

        var sb = new StringBuilder("{\"bodies\":[{");
        var hip = Map(sk.Joints[JointType.HipCenter].Position);
        sb.Append("\"center\":").Append(Pt(hip));
        sb.Append(",\"z\":").Append(sk.Position.Z.ToString("0.00", CultureInfo.InvariantCulture));
        sb.Append(",\"joints\":{");
        for (int i = 0; i < NAMES.Length; i++)
        {
            var j = sk.Joints[TYPES[i]];
            if (j.TrackingState == JointTrackingState.NotTracked) continue;
            if (sb[sb.Length - 1] != '{') sb.Append(',');
            sb.Append('"').Append(NAMES[i]).Append("\":").Append(Pt(Map(j.Position)));
        }
        sb.Append("}}]}");
        latest = sb.ToString();
    }

    // Point 3D -> image de profondeur 640×480, normalisé et en miroir
    static double[] Map(SkeletonPoint p)
    {
        var d = sensor.CoordinateMapper.MapSkeletonPointToDepthPoint(p, DepthImageFormat.Resolution640x480Fps30);
        return new double[] { 1 - d.X / 640.0, d.Y / 480.0 };
    }

    static string Pt(double[] p)
    {
        return "[" + p[0].ToString("0.0000", CultureInfo.InvariantCulture) + ","
                   + p[1].ToString("0.0000", CultureInfo.InvariantCulture) + "]";
    }

    static async Task AcceptLoop(HttpListener listener)
    {
        while (true)
        {
            var ctx = await listener.GetContextAsync();
            if (!ctx.Request.IsWebSocketRequest) { ctx.Response.StatusCode = 400; ctx.Response.Close(); continue; }
            var wsc = await ctx.AcceptWebSocketAsync(null);
            var ignored = Task.Run(() => ClientLoop(wsc.WebSocket));
        }
    }

    // Envoie la dernière image ~30 fois par seconde ; liste vide si la Kinect ne répond plus.
    static async Task ClientLoop(WebSocket ws)
    {
        try
        {
            while (ws.State == WebSocketState.Open)
            {
                var msg = (DateTime.Now - lastFrame).TotalMilliseconds < 500 ? latest : EMPTY;
                var b = Encoding.UTF8.GetBytes(msg);
                await ws.SendAsync(new ArraySegment<byte>(b), WebSocketMessageType.Text, true, CancellationToken.None);
                await Task.Delay(33);
            }
        }
        catch { }
    }
}
