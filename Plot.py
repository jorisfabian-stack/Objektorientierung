import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter, LogLocator


def plot_power_curve(duration_s, power_w):
    duration_s, power_w = map(
    lambda x: np.asarray(x, dtype=float),
    (duration_s, power_w)
)

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(duration_s, power_w, "o-", lw=1.5, ms=3)

    ax.set_xscale("log")
    ax.xaxis.set_major_locator(LogLocator(base=10.0, numticks=6, subs=(1.0,)))
    ax.xaxis.set_minor_locator(LogLocator(base=10.0, subs="auto", numticks=12))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{int(x):d}" if x >= 1 and float(int(x)) == x else f"{x:.0f}"))
    ax.tick_params(axis="x", which="major", labelsize=10)

    annotation = ax.annotate(
        "",
        xy=(0.98, 0.98),
        xycoords="axes fraction",
        horizontalalignment="right",
        verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.3", fc="white", alpha=0.95, edgecolor="black"),
        fontsize=9,
        visible=False,
        zorder=20,
    )

    vline = ax.axvline(color="gray", linestyle="--", linewidth=0.8, alpha=0.7, visible=False)

    x_values = duration_s
    y_values = power_w

    def on_move(event):
        if event.inaxes != ax or event.xdata is None or event.ydata is None:
            annotation.set_visible(False)
            vline.set_visible(False)
            fig.canvas.draw_idle()
            return

        if event.xdata <= 0:
            annotation.set_visible(False)
            vline.set_visible(False)
            fig.canvas.draw_idle()
            return

        idx = int(np.argmin(np.abs(np.log10(x_values) - np.log10(event.xdata))))
        x_val = x_values[idx]
        y_val = y_values[idx]

        annotation.set_text(f"Zeit: {x_val:.1f} s\nLeistung: {y_val:.1f} W")
        annotation.set_visible(True)
        vline.set_xdata([x_val, x_val])
        vline.set_visible(True)
        fig.canvas.draw_idle()

    fig.canvas.mpl_connect("motion_notify_event", on_move)

    ax.set_xlabel("Zeit [s]")
    ax.set_ylabel("Leistung [W]")
    ax.set_title("Power Duration Curve")
    ax.grid(True)

    fig.tight_layout()
    return fig
