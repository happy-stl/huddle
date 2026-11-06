using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Windows.Media;
using NinjaTrader.Gui;

namespace NinjaTrader.NinjaScript
{
	public enum State { SetDefaults, Configure, Active, DataLoaded, Historical, Transition, Realtime, Terminated, Finalized }

	public enum Calculate { OnBarClose, OnEachTick, OnPriceChange }

	[AttributeUsage(AttributeTargets.Property)]
	public class NinjaScriptPropertyAttribute : Attribute { }

	// What NinjaTrader's indicator base does for these indicators, replayed on historical bars:
	// - creating an indicator runs OnStateChange in State.SetDefaults, so object initializers
	//   (as in the generated factory methods) override the defaults;
	// - an indicator gets State.Configure and State.DataLoaded when it is attached to bars:
	//   the runner attaches the top indicator, and CacheIndicator attaches each indicator another
	//   one creates, sharing its parent's bars;
	// - on each bar, the indicators an indicator created update first, then its OnBarUpdate runs,
	//   once per bar, as Calculate.OnBarClose does on historical data.
	public abstract class IndicatorBase : ISeries<double>
	{
		private readonly List<Plot> plots = new List<Plot>();
		private readonly List<Series<double>> values = new List<Series<double>>();
		private readonly List<IndicatorBase> children = new List<IndicatorBase>();
		private int lastUpdatedBar = -1;

		protected IndicatorBase()
		{
			Values = new Series<double>[0];
			Plots = new Plot[0];
			SetState(State.SetDefaults);
		}

		public State State { get; private set; }
		public string Name { get; set; }
		public string Description { get; set; }
		public Calculate Calculate { get; set; }
		public bool IsOverlay { get; set; }
		public bool DisplayInDataBox { get; set; }
		public bool DrawOnPricePanel { get; set; }
		public bool DrawHorizontalGridLines { get; set; }
		public bool DrawVerticalGridLines { get; set; }
		public bool PaintPriceMarkers { get; set; }
		public NinjaTrader.Gui.Chart.ScaleJustification ScaleJustification { get; set; }
		public bool IsSuspendedWhileInactive { get; set; }

		public NinjaTrader.Data.Bars Bars { get; private set; }
		public ISeries<double> Input { get; private set; }
		public int CurrentBar { get { return Bars.CurrentBar; } }
		public bool IsFirstTickOfBar { get { return true; } }

		public Series<double>[] Values { get; private set; }
		public Series<double> Value { get { return Values[0]; } }
		public Plot[] Plots { get; private set; }

		public double this[int barsAgo] { get { return Value[barsAgo]; } }
		public int Count { get { return Bars.CurrentBar + 1; } }

		protected virtual void OnStateChange() { }
		protected virtual void OnBarUpdate() { }

		public void AddPlot(Brush brush, string name) { AddPlot(new Stroke(brush, 1), PlotStyle.Line, name); }

		public void AddPlot(Stroke stroke, PlotStyle plotStyle, string name)
		{
			plots.Add(new Plot(stroke, plotStyle, name));
			values.Add(new Series<double>(() => Bars));
			Plots = plots.ToArray();
			Values = values.ToArray();
		}

		public void Print(object value) { Console.Error.WriteLine(value); }

		public bool EqualsInput(ISeries<double> input) { return ReferenceEquals(Input, input); }

		// Attaches this indicator to bars and runs State.Configure and State.DataLoaded.
		public void Attach(NinjaTrader.Data.Bars bars, ISeries<double> input)
		{
			Bars = bars;
			Input = input;
			SetState(State.Configure);
			SetState(State.DataLoaded);
			SetState(State.Historical);
		}

		// Processes the bar Bars.CurrentBar.
		public void Update()
		{
			if (lastUpdatedBar == Bars.CurrentBar)
				return;
			foreach (IndicatorBase child in children)
				child.Update();
			lastUpdatedBar = Bars.CurrentBar;
			OnBarUpdate();
		}

		protected T CacheIndicator<T>(T indicator, ISeries<double> input, ref T[] cache) where T : IndicatorBase
		{
			indicator.Attach(Bars, input);
			children.Add(indicator);
			T[] grown = new T[cache == null ? 1 : cache.Length + 1];
			if (cache != null)
				Array.Copy(cache, grown, cache.Length);
			grown[grown.Length - 1] = indicator;
			cache = grown;
			return indicator;
		}

		private void SetState(State state)
		{
			State = state;
			OnStateChange();
		}
	}

	public abstract class MarketAnalyzerColumnBase
	{
		protected NinjaTrader.NinjaScript.Indicators.Indicator indicator = new NinjaTrader.NinjaScript.Indicators.Indicator();
		public ISeries<double> Input { get; set; }
	}
}

namespace NinjaTrader.Gui.NinjaScript
{
	public abstract class IndicatorRenderBase : global::NinjaTrader.NinjaScript.IndicatorBase { }

	public abstract class StrategyRenderBase
	{
		protected global::NinjaTrader.NinjaScript.Indicators.Indicator indicator = new global::NinjaTrader.NinjaScript.Indicators.Indicator();
		public global::NinjaTrader.NinjaScript.ISeries<double> Input { get; set; }
	}
}

namespace NinjaTrader.NinjaScript.Indicators
{
	public partial class Indicator : NinjaTrader.Gui.NinjaScript.IndicatorRenderBase { }

	// NinjaTrader 8's built-in EMA.
	public class EMA : Indicator
	{
		private double constant1;
		private double constant2;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Name = "EMA";
				IsOverlay = true;
				IsSuspendedWhileInactive = true;
				Period = 14;
				AddPlot(Brushes.Goldenrod, "EMA");
			}
			else if (State == State.Configure)
			{
				constant1 = 2.0 / (1 + Period);
				constant2 = 1 - (2.0 / (1 + Period));
			}
		}

		protected override void OnBarUpdate()
		{
			Value[0] = (CurrentBar == 0 ? Input[0] : Input[0] * constant1 + constant2 * Value[1]);
		}

		[Range(1, int.MaxValue), NinjaScriptProperty]
		public int Period { get; set; }
	}

	// NinjaTrader 8's built-in SMA, on bars that do not support removing the last bar (time bars):
	// a running sum, averaging the bars so far until there are Period of them.
	public class SMA : Indicator
	{
		private double priorSum;
		private double sum;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Name = "SMA";
				IsOverlay = true;
				IsSuspendedWhileInactive = true;
				Period = 14;
				AddPlot(Brushes.Goldenrod, "SMA");
			}
			else if (State == State.Configure)
			{
				priorSum = 0;
				sum = 0;
			}
		}

		protected override void OnBarUpdate()
		{
			if (IsFirstTickOfBar)
				priorSum = sum;
			sum = priorSum + Input[0] - (CurrentBar >= Period ? Input[Period] : 0);
			Value[0] = sum / (CurrentBar < Period ? CurrentBar + 1 : Period);
		}

		[Range(1, int.MaxValue), NinjaScriptProperty]
		public int Period { get; set; }
	}

	// The factory methods NinjaTrader generates for its built-in EMA and SMA.
	public partial class Indicator
	{
		private EMA[] cacheEMA;
		public EMA EMA(int period) { return EMA(Input, period); }
		public EMA EMA(ISeries<double> input, int period)
		{
			if (cacheEMA != null)
				for (int idx = 0; idx < cacheEMA.Length; idx++)
					if (cacheEMA[idx] != null && cacheEMA[idx].Period == period && cacheEMA[idx].EqualsInput(input))
						return cacheEMA[idx];
			return CacheIndicator<EMA>(new EMA() { Period = period }, input, ref cacheEMA);
		}

		private SMA[] cacheSMA;
		public SMA SMA(int period) { return SMA(Input, period); }
		public SMA SMA(ISeries<double> input, int period)
		{
			if (cacheSMA != null)
				for (int idx = 0; idx < cacheSMA.Length; idx++)
					if (cacheSMA[idx] != null && cacheSMA[idx].Period == period && cacheSMA[idx].EqualsInput(input))
						return cacheSMA[idx];
			return CacheIndicator<SMA>(new SMA() { Period = period }, input, ref cacheSMA);
		}
	}
}
