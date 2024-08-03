import pandas as pd
from typing import Tuple, Sequence
from pathlib import Path
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


def render_class_results(class_results: Sequence[Tuple[str, str, pd.DataFrame]], directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    file_loc = directory / "final-class-report.pdf"
    # plot each table as a new page in the PDF
    with PdfPages(file_loc) as pp:
        for class_id, class_name, df in class_results:
            fig, ax = plt.subplots()
            ax.axis("off")
            ax.table(cellText=df.values, colLabels=df.columns, rowLabels=df.index, loc="center")
            ax.set_title(f"Results for class {class_id} --- {class_name}")
            pp.savefig(fig)
            plt.close(fig)


def render_prizes(prize_results: Sequence[str], directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    file_loc = directory / "final-prize-report.pdf"
    fig, ax = plt.subplots()
    for idx, prize in enumerate(prize_results):
        ax.axis("off")
        ax.text(0.5, 0.9 - idx * 0.1, prize, ha="center", va="top", size=10)
    ax.set_title("Prize Winners")
    fig.savefig(file_loc)
    plt.close(fig)
