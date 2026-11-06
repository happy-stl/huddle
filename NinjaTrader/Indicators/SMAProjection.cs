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
	public class SMAProjection : Indicator
	{
		private SMA sma;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description									= @"Computes the SMA with an additional factor of prediction based on the slope of the T-1 and T-2 prices.";
				Name										= "SMA Projection";
				Calculate									= Calculate.OnPriceChange;
				IsOverlay									= true;
				IsSuspendedWhileInactive					= true;
				Period										= 14;
				PrintOutput									= false;

				AddPlot(Brushes.Goldenrod, "SMA");
				AddPlot(Brushes.Aquamarine, "Projection");
			}
			else if (State == State.DataLoaded)
			{
				sma = SMA(Period);
			}
		}

		protected override void OnBarUpdate()
		{
			double sma0 = sma[0];
			SMA[0] = sma0;
			
			// Since we are looking at our past SMA, we need at least N+1 periods so we have enough
			// data to look over sma[1] to sma[N+1].
			if (CurrentBar < Period + 1) {
				return;
			}
			
			double sma1 = sma[1];
			double smaX = sma[Period + 1];
			// sma[1] back to sma[Period + 1] spans Period bars.
			double dx = sma1 - smaX;
			int dy = Period;
			double slope = dx / dy;
			Projection[0] = sma1 + slope;
			
			#region Debugging
			if (PrintOutput) {
				Print(string.Format(
					"{{" +
						"\"CurrentBar\": {0}, " +
						"\"sma{1}\": {2:0.00}, " +
						"\"sma1\": {3:0.00}, " +
						"\"period\": {4}, " +
						"\"slope\": {5:0.00}, " +
						"\"projection\": {6:0.00}" +
					"}}",
					CurrentBar, Period + 1, smaX, sma1, Period, slope, Projection[0]
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
		
		[Browsable(false)]
		[XmlIgnore()]
		public Series<double> SMA
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
		private SMAProjection[] cacheSMAProjection;
		public SMAProjection SMAProjection(bool printOutput, int period)
		{
			return SMAProjection(Input, printOutput, period);
		}

		public SMAProjection SMAProjection(ISeries<double> input, bool printOutput, int period)
		{
			if (cacheSMAProjection != null)
				for (int idx = 0; idx < cacheSMAProjection.Length; idx++)
					if (cacheSMAProjection[idx] != null && cacheSMAProjection[idx].PrintOutput == printOutput && cacheSMAProjection[idx].Period == period && cacheSMAProjection[idx].EqualsInput(input))
						return cacheSMAProjection[idx];
			return CacheIndicator<SMAProjection>(new SMAProjection(){ PrintOutput = printOutput, Period = period }, input, ref cacheSMAProjection);
		}
	}
}

namespace NinjaTrader.NinjaScript.MarketAnalyzerColumns
{
	public partial class MarketAnalyzerColumn : MarketAnalyzerColumnBase
	{
		public Indicators.SMAProjection SMAProjection(bool printOutput, int period)
		{
			return indicator.SMAProjection(Input, printOutput, period);
		}

		public Indicators.SMAProjection SMAProjection(ISeries<double> input , bool printOutput, int period)
		{
			return indicator.SMAProjection(input, printOutput, period);
		}
	}
}

namespace NinjaTrader.NinjaScript.Strategies
{
	public partial class Strategy : NinjaTrader.Gui.NinjaScript.StrategyRenderBase
	{
		public Indicators.SMAProjection SMAProjection(bool printOutput, int period)
		{
			return indicator.SMAProjection(Input, printOutput, period);
		}

		public Indicators.SMAProjection SMAProjection(ISeries<double> input , bool printOutput, int period)
		{
			return indicator.SMAProjection(input, printOutput, period);
		}
	}
}

#endregion
