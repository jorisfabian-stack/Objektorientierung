from pathlib import Path

import matplotlib
matplotlib.use("TkAgg", force=True)
import matplotlib.pyplot as plt
import pandas as pd

from Leistungskurve import create_power_curve
from Plot import plot_power_curve


def main() -> None:
    project_root = Path(__file__).resolve().parent
    data_file = project_root / "data" / "activity.csv"

    df = pd.read_csv(data_file)
    power_curve = create_power_curve(df)
    print(power_curve.head())

    fig = plot_power_curve(power_curve["duration_s"], power_curve["power_w"])
    plt.show(block=True)


if __name__ == "__main__":
    main()
