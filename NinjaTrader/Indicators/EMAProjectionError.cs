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
	public class EMAProjectionError : Indicator
	{
		private EMAProjection emaProjection;

		protected override void OnStateChange()
		{
			if (State == State.SetDefaults)
			{
				Description									= @"Computes the difference of the projection from the real moving average.";
				Name										= "EMA Projection Error";
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
				ProjectionMethod							= EMAProjectionMethod.PriceHold;
				InverseGraph								= true;

				AddPlot(new Stroke(Brushes.Green, 2), PlotStyle.Bar, "Positive Error");
				AddPlot(new Stroke(Brushes.Red, 2), PlotStyle.Bar, "Negative Error");
			}
			else if (State == State.Configure)
			{
				emaProjection = EMAProjection(false, Period, ProjectionMethod);
			}
		}

		protected override void OnBarUpdate()
		{
			if (CurrentBar == 0) {
				return;
			}
			Series<double> projection = emaProjection.Projection;
			Series<double> ema = emaProjection.EMA;
			double error = (projection[0] - ema[0]) * (InverseGraph ? -1 : 1);
			if (error >= 0.0) {
				PositiveError[0] = error;
			} else {
				NegativeError[0] = error;
			}
		}

		#region Properties
		[NinjaScriptProperty]
		[Range(1, int.MaxValue)]
		[Display(Name="Period", Order=0, GroupName="Parameters")]
		public int Period
		{ get; set; }
		
		[NinjaScriptProperty]
		[Display(Name="Prioritize Moving Average", Order=1, GroupName="Parameters")]
		public bool InverseGraph
		{ get; set; }

		[NinjaScriptProperty]
		[Display(Name="Projection Method", Order=2, GroupName="Parameters")]
		public EMAProjectionMethod ProjectionMethod
		{ get; set; }

		[Browsable(false)]
		[XmlIgnore]
		public Series<double> PositiveError
		{
			get { return Values[0]; }
		}
		
		[Browsable(false)]
		[XmlIgnore]
		public Series<double> NegativeError
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
		private EMAProjectionError[] cacheEMAProjectionError;
		public EMAProjectionError EMAProjectionError(int period, bool inverseGraph, NinjaTrader.NinjaScript.Indicators.EMAProjectionMethod projectionMethod)
		{
			return EMAProjectionError(Input, period, inverseGraph, projectionMethod);
		}

		public EMAProjectionError EMAProjectionError(ISeries<double> input, int period, bool inverseGraph, NinjaTrader.NinjaScript.Indicators.EMAProjectionMethod projectionMethod)
		{
			if (cacheEMAProjectionError != null)
				for (int idx = 0; idx < cacheEMAProjectionError.Length; idx++)
					if (cacheEMAProjectionError[idx] != null && cacheEMAProjectionError[idx].Period == period && cacheEMAProjectionError[idx].InverseGraph == inverseGraph && cacheEMAProjectionError[idx].ProjectionMethod == projectionMethod && cacheEMAProjectionError[idx].EqualsInput(input))
						return cacheEMAProjectionError[idx];
			return CacheIndicator<EMAProjectionError>(new EMAProjectionError(){ Period = period, InverseGraph = inverseGraph, ProjectionMethod = projectionMethod }, input, ref cacheEMAProjectionError);
		}
	}
}

namespace NinjaTrader.NinjaScript.MarketAnalyzerColumns
{
	public partial class MarketAnalyzerColumn : MarketAnalyzerColumnBase
	{
		public Indicators.EMAProjectionError EMAProjectionError(int period, bool inverseGraph, NinjaTrader.NinjaScript.Indicators.EMAProjectionMethod projectionMethod)
		{
			return indicator.EMAProjectionError(Input, period, inverseGraph, projectionMethod);
		}

		public Indicators.EMAProjectionError EMAProjectionError(ISeries<double> input , int period, bool inverseGraph, NinjaTrader.NinjaScript.Indicators.EMAProjectionMethod projectionMethod)
		{
			return indicator.EMAProjectionError(input, period, inverseGraph, projectionMethod);
		}
	}
}

namespace NinjaTrader.NinjaScript.Strategies
{
	public partial class Strategy : NinjaTrader.Gui.NinjaScript.StrategyRenderBase
	{
		public Indicators.EMAProjectionError EMAProjectionError(int period, bool inverseGraph, NinjaTrader.NinjaScript.Indicators.EMAProjectionMethod projectionMethod)
		{
			return indicator.EMAProjectionError(Input, period, inverseGraph, projectionMethod);
		}

		public Indicators.EMAProjectionError EMAProjectionError(ISeries<double> input , int period, bool inverseGraph, NinjaTrader.NinjaScript.Indicators.EMAProjectionMethod projectionMethod)
		{
			return indicator.EMAProjectionError(input, period, inverseGraph, projectionMethod);
		}
	}
}

#endregion
