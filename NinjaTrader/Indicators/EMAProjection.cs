#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Gui.SuperDom;
using NinjaTrader.Gui.Tools;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.Core.FloatingPoint;
using NinjaTrader.NinjaScript.DrawingTools;
#endregion

//This namespace holds Indicators in this folder and is required. Do not change it. 
namespace NinjaTrader.NinjaScript.Indicators
{
	// How EMAProjection estimates the EMA's change over the next bar.
	public enum EMAProjectionMethod
	{
		// The EMA the next bar gives if it closes where the last bar closed.
		PriceHold,
		// The EMA's average change per bar over the last Period bars.
		AverageSlope
	}

	public class EMAProjection : Indicator
	{
		private EMA ema;
		
		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description									= @"Computes the EMA and projects it one bar ahead from the EMA's recent slope.";
				Name										= "EMA Projection";
				Calculate									= Calculate.OnPriceChange;
				IsOverlay									= false;
				DisplayInDataBox							= true;
				DrawOnPricePanel							= true;
				DrawHorizontalGridLines						= true;
				DrawVerticalGridLines						= true;
				PaintPriceMarkers							= true;
				ScaleJustification							= NinjaTrader.Gui.Chart.ScaleJustification.Right;
				//Disable this property if your indicator requires custom values that cumulate with each new market data event. 
				//See Help Guide for additional information.
				IsSuspendedWhileInactive					= true;
				Period										= 14;
				PrintOutput									= false;
				ProjectionMethod							= EMAProjectionMethod.PriceHold;

				AddPlot(Brushes.Goldenrod, "EMA");
				AddPlot(Brushes.Aquamarine, "Projection");
			}
			else if (State == State.Configure)
			{
				ema = EMA(Period);
			}
		}

		protected override void OnBarUpdate()
		{
			double ema0 = ema[0];
			EMA[0] = ema0;
			
			// The projection for this bar only uses closed bars: ema[1] back to ema[lookback].
			int lookback = ProjectionMethod == EMAProjectionMethod.AverageSlope ? Period + 1 : 2;
			if (CurrentBar < lookback) {
				return;
			}
			
			double ema1 = ema[1];
			double slope;
			if (ProjectionMethod == EMAProjectionMethod.AverageSlope) {
				// ema[1] back to ema[Period + 1] spans Period bars.
				double emaX = ema[Period + 1];
				slope = (ema1 - emaX) / Period;
			} else {
				// PriceHold: if this bar closes where the last one did, the EMA moves by
				// k * (Input[1] - ema1), which by the EMA's recursion is (1 - k) * (ema1 - ema2).
				double k = 2.0 / (1 + Period);
				double ema2 = ema[2];
				slope = (1 - k) * (ema1 - ema2);
			}
			Projection[0] = ema1 + slope;
			
			#region Debugging
			if (PrintOutput) {
				Print(string.Format(
					"{{" +
						"\"CurrentBar\": {0}, " +
						"\"method\": \"{1}\", " +
						"\"ema1\": {2:0.00}, " +
						"\"period\": {3}, " +
						"\"slope\": {4:0.00}, " +
						"\"projection\": {5:0.00}" +
					"}}",
					CurrentBar, ProjectionMethod, ema1, Period, slope, Projection[0]
				));
			}
			#endregion
		}

		#region Properties
		[NinjaScriptProperty]
		[Display(ResourceType = typeof(Custom.Resource), Name = "Print Output", GroupName = "NinjaScriptParameters", Order = 0)]
		public bool PrintOutput { get; set; }
		
		[Range(1, int.MaxValue), NinjaScriptProperty]
		[Display(ResourceType = typeof(Custom.Resource), Name = "Period", GroupName = "NinjaScriptParameters", Order = 0)]
		public int Period { get; set; }
		
		[NinjaScriptProperty]
		[Display(ResourceType = typeof(Custom.Resource), Name = "Projection Method", GroupName = "NinjaScriptParameters", Order = 1)]
		public EMAProjectionMethod ProjectionMethod { get; set; }
		
		[Browsable(false)]
		[XmlIgnore()]
		public Series<double> EMA
		{
			get { return Values[0]; }
		}
		
		[Browsable(false)]
		[XmlIgnore()]
		public Series<double> Projection
		{
			get { return Values[1]; }
		}
		#endregion
	}
}

#region NinjaScript generated code. Neither change nor remove.

namespace NinjaTrader.NinjaScript.Indicators
{
	public partial class Indicator : NinjaTrader.Gui.NinjaScript.IndicatorRenderBase
	{
		private EMAProjection[] cacheEMAProjection;
		public EMAProjection EMAProjection(bool printOutput, int period, NinjaTrader.NinjaScript.Indicators.EMAProjectionMethod projectionMethod)
		{
			return EMAProjection(Input, printOutput, period, projectionMethod);
		}

		public EMAProjection EMAProjection(ISeries<double> input, bool printOutput, int period, NinjaTrader.NinjaScript.Indicators.EMAProjectionMethod projectionMethod)
		{
			if (cacheEMAProjection != null)
				for (int idx = 0; idx < cacheEMAProjection.Length; idx++)
					if (cacheEMAProjection[idx] != null && cacheEMAProjection[idx].PrintOutput == printOutput && cacheEMAProjection[idx].Period == period && cacheEMAProjection[idx].ProjectionMethod == projectionMethod && cacheEMAProjection[idx].EqualsInput(input))
						return cacheEMAProjection[idx];
			return CacheIndicator<EMAProjection>(new EMAProjection(){ PrintOutput = printOutput, Period = period, ProjectionMethod = projectionMethod }, input, ref cacheEMAProjection);
		}
	}
}

namespace NinjaTrader.NinjaScript.MarketAnalyzerColumns
{
	public partial class MarketAnalyzerColumn : MarketAnalyzerColumnBase
	{
		public Indicators.EMAProjection EMAProjection(bool printOutput, int period, NinjaTrader.NinjaScript.Indicators.EMAProjectionMethod projectionMethod)
		{
			return indicator.EMAProjection(Input, printOutput, period, projectionMethod);
		}

		public Indicators.EMAProjection EMAProjection(ISeries<double> input , bool printOutput, int period, NinjaTrader.NinjaScript.Indicators.EMAProjectionMethod projectionMethod)
		{
			return indicator.EMAProjection(input, printOutput, period, projectionMethod);
		}
	}
}

namespace NinjaTrader.NinjaScript.Strategies
{
	public partial class Strategy : NinjaTrader.Gui.NinjaScript.StrategyRenderBase
	{
		public Indicators.EMAProjection EMAProjection(bool printOutput, int period, NinjaTrader.NinjaScript.Indicators.EMAProjectionMethod projectionMethod)
		{
			return indicator.EMAProjection(Input, printOutput, period, projectionMethod);
		}

		public Indicators.EMAProjection EMAProjection(ISeries<double> input , bool printOutput, int period, NinjaTrader.NinjaScript.Indicators.EMAProjectionMethod projectionMethod)
		{
			return indicator.EMAProjection(input, printOutput, period, projectionMethod);
		}
	}
}

#endregion
