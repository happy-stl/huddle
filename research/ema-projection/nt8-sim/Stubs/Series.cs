using System;
using System.Collections.Generic;

namespace NinjaTrader.Data
{
	// The bars being replayed: closes in time order and the bar being processed.
	public class Bars
	{
		public Bars(double[] closes) { Closes = closes; CurrentBar = -1; }
		public double[] Closes { get; private set; }
		public int CurrentBar { get; set; }
	}
}

namespace NinjaTrader.NinjaScript
{
	public interface ISeries<T>
	{
		T this[int barsAgo] { get; }
		int Count { get; }
	}

	// NinjaTrader's [barsAgo] indexing: [0] is the bar being processed, [n] the bar n bars earlier.
	// Like NinjaTrader, reaching before the first bar or into the future throws.
	internal static class BarsAgo
	{
		public static int Index(NinjaTrader.Data.Bars bars, int barsAgo)
		{
			int index = bars.CurrentBar - barsAgo;
			if (barsAgo < 0 || index < 0)
				throw new ArgumentOutOfRangeException("barsAgo",
					string.Format("barsAgo {0} on bar {1}: NinjaTrader would stop the indicator here", barsAgo, bars.CurrentBar));
			return index;
		}
	}

	// The closes as an input series.
	public class PriceSeries : ISeries<double>
	{
		private readonly NinjaTrader.Data.Bars bars;
		public PriceSeries(NinjaTrader.Data.Bars bars) { this.bars = bars; }
		public double this[int barsAgo] { get { return bars.Closes[BarsAgo.Index(bars, barsAgo)]; } }
		public int Count { get { return bars.CurrentBar + 1; } }
	}

	// A value per bar. A bar whose value was never set reads as NaN and is counted in UnsetReads,
	// so the runner can show where an indicator read a value it had not set.
	public class Series<T> : ISeries<T>
	{
		public static int UnsetReads;

		private readonly Func<NinjaTrader.Data.Bars> bars;
		private readonly List<T> values = new List<T>();
		private readonly List<bool> set = new List<bool>();

		public Series(Func<NinjaTrader.Data.Bars> bars) { this.bars = bars; }

		public int Count { get { return bars().CurrentBar + 1; } }

		public T this[int barsAgo]
		{
			get
			{
				int i = BarsAgo.Index(bars(), barsAgo);
				if (i >= set.Count || !set[i])
				{
					UnsetReads++;
					return (T)(object)double.NaN;
				}
				return values[i];
			}
			set
			{
				if (barsAgo != 0)
					throw new InvalidOperationException("the indicators only set [0]");
				int i = BarsAgo.Index(bars(), 0);
				while (values.Count <= i) { values.Add(default(T)); set.Add(false); }
				values[i] = value;
				set[i] = true;
			}
		}

		// NinjaTrader's Series<T>.IsValidDataPoint: whether the value barsAgo was set.
		public bool IsValidDataPoint(int barsAgo)
		{
			int i = BarsAgo.Index(bars(), barsAgo);
			return i < set.Count && set[i];
		}

		public bool IsValidDataPointAt(int barIndex) { return barIndex < set.Count && set[barIndex]; }
		public T GetValueAt(int barIndex) { return values[barIndex]; }
	}
}
