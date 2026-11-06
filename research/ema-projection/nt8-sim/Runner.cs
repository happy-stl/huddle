using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Indicators;

namespace Nt8Sim
{
	// Holds the indicators under test, created through NinjaTrader's generated factory methods.
	public class Host : Indicator
	{
		public EMAProjectionMethod Method;
		public int ProjectionPeriod = 14;
		public EMAProjection Projection;
		public EMAProjectionTrend Trend;
		public EMAProjectionError Error;
		public SMAProjection SmaProjection;
		public SMAProjectionTrend SmaTrend;

		protected override void OnStateChange()
		{
			if (State == State.Configure)
			{
				Projection = EMAProjection(false, ProjectionPeriod, Method);
				Trend = EMAProjectionTrend(ProjectionPeriod, Method);
				Error = EMAProjectionError(ProjectionPeriod, true, Method);
				SmaProjection = SMAProjection(false, ProjectionPeriod);
				SmaTrend = SMAProjectionTrend(ProjectionPeriod);
			}
		}
	}

	public static class Program
	{
		// Usage: Nt8Sim <data folder> <output folder> [period]
		// Replays every data/*.csv bar by bar and writes <output>/<series>_<method>.csv with each plot's
		// value per bar (empty where the indicator did not set it).
		public static int Main(string[] args)
		{
			string dataDir = args.Length > 0 ? args[0] : "../data";
			string outDir = args.Length > 1 ? args[1] : "out";
			int period = args.Length > 2 ? int.Parse(args[2], CultureInfo.InvariantCulture) : 14;
			Directory.CreateDirectory(outDir);

			foreach (string path in Directory.GetFiles(dataDir, "*.csv").OrderBy(p => p, StringComparer.Ordinal))
			{
				double[] closes = File.ReadLines(path).Skip(1)
					.Select(line => double.Parse(line.Split(',')[4], CultureInfo.InvariantCulture))
					.ToArray();
				foreach (EMAProjectionMethod method in Enum.GetValues(typeof(EMAProjectionMethod)))
				{
					Series<double>.UnsetReads = 0;
					Bars bars = new Bars(closes);
					Host host = new Host() { Method = method, ProjectionPeriod = period };
					host.Attach(bars, new PriceSeries(bars));

					var columns = new List<KeyValuePair<string, Series<double>>>
					{
						Column("EMAProjection.EMA", host.Projection.EMA),
						Column("EMAProjection.Projection", host.Projection.Projection),
						Column("EMAProjectionTrend.TrendUp", host.Trend.TrendUp),
						Column("EMAProjectionTrend.TrendDown", host.Trend.TrendDown),
						Column("EMAProjectionError.PositiveError", host.Error.PositiveError),
						Column("EMAProjectionError.NegativeError", host.Error.NegativeError),
						Column("SMAProjection.SMA", host.SmaProjection.SMA),
						Column("SMAProjection.Projection", host.SmaProjection.Projection),
						Column("SMAProjectionTrend.TrendUp", host.SmaTrend.TrendUp),
						Column("SMAProjectionTrend.TrendDown", host.SmaTrend.TrendDown),
					};
					for (int bar = 0; bar < closes.Length; bar++)
					{
						bars.CurrentBar = bar;
						host.Update();
					}

					string name = Path.GetFileNameWithoutExtension(path) + "_" + method;
					using (var w = new StreamWriter(Path.Combine(outDir, name + ".csv")))
					{
						w.WriteLine("bar," + string.Join(",", columns.Select(c => c.Key)));
						for (int bar = 0; bar < closes.Length; bar++)
							w.WriteLine(bar + "," + string.Join(",", columns.Select(c =>
								c.Value.IsValidDataPointAt(bar) ? c.Value.GetValueAt(bar).ToString("R", CultureInfo.InvariantCulture) : "")));
					}
					Console.WriteLine("{0}: {1} bars, {2} reads of unset values", name, closes.Length, Series<double>.UnsetReads);
				}
			}
			return 0;
		}

		private static KeyValuePair<string, Series<double>> Column(string name, Series<double> series)
		{
			return new KeyValuePair<string, Series<double>>(name, series);
		}
	}
}
