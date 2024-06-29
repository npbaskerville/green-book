import matplotlib.pyplot as plt
from typing import Sequence
from pathlib import Path

from greenbook.data.show import Entry


def render_entries(contestant_name: str, entries: Sequence[Entry]) -> plt.Figure:
    fig, ax = plt.subplots(figsize=(8.27, 11.69), dpi=100)
    y = 0.95
    x = 0.1
    for i, entry in enumerate(entries):
        class_id_str = entry.class_id
        if len(class_id_str) == 1:
            class_id_str = f" {class_id_str}"
        contest_id_str = str(entry.contestant_id)
        if len(contest_id_str) == 1:
            contest_id_str = f" {contest_id_str}"
        plt.text(
            x,
            y,
            f"Class: {class_id_str}\n\nEntry: {contest_id_str}",
            size=15,
            ha="right",
            va="top",
            bbox=dict(
                boxstyle="square",
                fc="w",
                pad=0.9,
            ),
        )
        y -= 0.15
        if y < 0.1:
            y = 0.95
            x += 0.2
    ax.axis("off")
    ax.set_title(f"Entries for {contestant_name}")
    return fig


def render_contestant_to_file(contestant_name: str, entries: Sequence[Entry], directory: Path):
    directory.mkdir(parents=True, exist_ok=True)
    fig = render_entries(contestant_name, entries)
    filename = directory / f"{contestant_name}.png"
    fig.savefig(filename)
    plt.close(fig)
