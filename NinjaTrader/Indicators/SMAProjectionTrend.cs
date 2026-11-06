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
	public class SMAProjectionTrend : Indicator
	{
		private SMAProjection smaProjection;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description									= @"Enter the description for your new custom Indicator here.";
				Name										= "SMA Projection Trend";
				Calculate									= Calculate.OnPriceChange;
				IsOverlay									= false;
				DisplayInDataBox							= true;
				DrawOnPricePanel							= false;
				DrawHorizontalGridLines						= false;
				DrawVerticalGridLines						= false;
				PaintPriceMarkers							= false;
				ScaleJustification							= NinjaTrader.Gui.Chart.ScaleJustification.Right;
				//Disable this property if your indicator requires custom values that cumulate with each new market data event. 
				//See Help Guide for additional information.
				IsSuspendedWhileInactive					= true;
				Period										= 14;

				AddPlot(new Stroke(Brushes.Green, 2), PlotStyle.Bar, "Trend Up");
				AddPlot(new Stroke(Brushes.Red, 2), PlotStyle.Bar, "Trend Down");
				Plots[0].AutoWidth = true;
				Plots[1].AutoWidth = true;
			}
			else if (State == State.DataLoaded)
			{				
				smaProjection = SMAProjection(false, Period);
			}
		}

		protected override void OnBarUpdate()
		{
			Series<double> projection = smaProjection.Projection;
			// The projection starts after its warm-up bars; a trend needs it on this bar and the last.
			if (CurrentBar == 0 || !projection.IsValidDataPoint(0) || !projection.IsValidDataPoint(1)) {
				return;
			}
			double trend = projection[0] - projection[1];
			TrendUp[0] = trend > 0 ? trend : 0;
			TrendDown[0] = trend < 0 ? trend : 0;
		}

		#region Properties
		[NinjaScriptProperty]
		[Range(1, int.MaxValue)]
		[Display(Name="Period", Order=2, GroupName="Parameters")]
		public int Period
		{ get; set; }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> TrendUp
		{
			get { return Values[0]; }
		}
		
		[Browsable(false)]
		[XmlIgnore]
		public Series<double> TrendDown
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
		private SMAProjectionTrend[] cacheSMAProjectionTrend;
		public SMAProjectionTrend SMAProjectionTrend(int period)
		{
			return SMAProjectionTrend(Input, period);
		}

		public SMAProjectionTrend SMAProjectionTrend(ISeries<double> input, int period)
		{
			if (cacheSMAProjectionTrend != null)
				for (int idx = 0; idx < cacheSMAProjectionTrend.Length; idx++)
					if (cacheSMAProjectionTrend[idx] != null && cacheSMAProjectionTrend[idx].Period == period && cacheSMAProjectionTrend[idx].EqualsInput(input))
						return cacheSMAProjectionTrend[idx];
			return CacheIndicator<SMAProjectionTrend>(new SMAProjectionTrend(){ Period = period }, input, ref cacheSMAProjectionTrend);
		}
	}
}

namespace NinjaTrader.NinjaScript.MarketAnalyzerColumns
{
	public partial class MarketAnalyzerColumn : MarketAnalyzerColumnBase
	{
		public Indicators.SMAProjectionTrend SMAProjectionTrend(int period)
		{
			return indicator.SMAProjectionTrend(Input, period);
		}

		public Indicators.SMAProjectionTrend SMAProjectionTrend(ISeries<double> input , int period)
		{
			return indicator.SMAProjectionTrend(input, period);
		}
	}
}

namespace NinjaTrader.NinjaScript.Strategies
{
	public partial class Strategy : NinjaTrader.Gui.NinjaScript.StrategyRenderBase
	{
		public Indicators.SMAProjectionTrend SMAProjectionTrend(int period)
		{
			return indicator.SMAProjectionTrend(Input, period);
		}

		public Indicators.SMAProjectionTrend SMAProjectionTrend(ISeries<double> input , int period)
		{
			return indicator.SMAProjectionTrend(input, period);
		}
	}
}

#endregion
