// The namespaces the indicators' using declarations name. NinjaTrader and WPF fill these with real
// types; the indicators only need the few defined in the other stub files, so the rest hold a
// placeholder so that each `using` resolves.

namespace System.Windows { internal static class Nt8SimPlaceholder { } }
namespace System.Windows.Input { internal static class Nt8SimPlaceholder { } }
namespace NinjaTrader.Cbi { internal static class Nt8SimPlaceholder { } }
namespace NinjaTrader.Gui.SuperDom { internal static class Nt8SimPlaceholder { } }
namespace NinjaTrader.Gui.Tools { internal static class Nt8SimPlaceholder { } }
namespace NinjaTrader.Core.FloatingPoint { internal static class Nt8SimPlaceholder { } }
namespace NinjaTrader.NinjaScript.DrawingTools { internal static class Nt8SimPlaceholder { } }

namespace NinjaTrader.Custom
{
	// The resource class the [Display(ResourceType = ...)] attributes name.
	public class Resource { }
}

namespace System.Windows.Media
{
	public class Brush
	{
		public Brush(string name) { Name = name; }
		public string Name { get; private set; }
	}

	public static class Brushes
	{
		public static readonly Brush Aquamarine = new Brush("Aquamarine");
		public static readonly Brush Goldenrod = new Brush("Goldenrod");
		public static readonly Brush Green = new Brush("Green");
		public static readonly Brush Red = new Brush("Red");
	}
}

namespace NinjaTrader.Gui
{
	public enum PlotStyle { Line, Bar, Dot, Hash, Square, TriangleUp, TriangleDown }

	public class Stroke
	{
		public Stroke(System.Windows.Media.Brush brush, float width) { Brush = brush; Width = width; }
		public System.Windows.Media.Brush Brush { get; private set; }
		public float Width { get; private set; }
	}

	public class Plot
	{
		public Plot(Stroke stroke, PlotStyle style, string name) { Stroke = stroke; PlotStyle = style; Name = name; }
		public Stroke Stroke { get; private set; }
		public PlotStyle PlotStyle { get; private set; }
		public string Name { get; private set; }
		public bool AutoWidth { get; set; }
	}
}

namespace NinjaTrader.Gui.Chart
{
	public enum ScaleJustification { Left, Right, Overlay }
}
