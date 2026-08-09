import argparse
import math
import os

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages
from PIL import Image


# Arguments

parser = argparse.ArgumentParser(description="Generate daily pitcher reports from TrackMan CSV data.")
parser.add_argument("file", help="Path to a TrackMan CSV file")
parser.add_argument("--team", help="Optional PitcherTeam value used to filter pitchers")
parser.add_argument("--logo", help="Optional path to a logo image")
parser.add_argument("--output-dir", default="reports", help="Directory where the generated PDF will be saved")
args = parser.parse_args()


# Load file

if not os.path.isfile(args.file):
    raise FileNotFoundError(f"CSV file not found: {args.file}")

df = pd.read_csv(args.file)

if df.empty:
    raise ValueError("The provided CSV file contains no rows.")

if "Date" not in df.columns:
    raise ValueError("The required 'Date' column was not found in the CSV file.")

raw_date = str(df["Date"].iloc[0]).replace("/", "-")
parsed_date = pd.to_datetime(raw_date, errors="coerce")

if pd.isna(parsed_date):
    raise ValueError(f"Unable to parse game date: {raw_date}")

date = parsed_date.strftime("%m-%d-%Y")


# Optional team filter

if args.team:
    if "PitcherTeam" not in df.columns:
        raise ValueError("The 'PitcherTeam' column is required when using --team.")

    df = df[df["PitcherTeam"] == args.team]

    if df.empty:
        raise ValueError(f"No pitches found for team '{args.team}'.")


# Optional logo

img = None

if args.logo:
    if not os.path.isfile(args.logo):
        raise FileNotFoundError(f"Logo file not found: {args.logo}")

    img = Image.open(args.logo)
    img = img.resize((150, 150), Image.Resampling.LANCZOS)
    img = img.convert("RGB")


# Pitch colors/order

pitch_colors = {
    "ChangeUp": "blue",
    "Fastball": "#FF69B4",
    "Slider": "#FFDF00",
    "Curveball": "green",
    "TwoSeamFastBall": "orange",
    "Sinker": "turquoise",
    "FourSeamFastBall": "red",
    "Undefined": "grey",
    "Splitter": "brown",
    "Sweeper": "#00BFFF",
    "Cutter": "purple",
    "Other": "gray",
}

pitch_order = [
    "FourSeamFastBall", "Fastball", "TwoSeamFastBall", "Sinker",
    "Cutter", "Splitter", "ChangeUp", "Slider", "Curveball",
    "Sweeper", "Other", "Undefined"
]


# Create output path

os.makedirs(args.output_dir, exist_ok=True)
pdf_path = os.path.join(args.output_dir, f"Pitcher_Report_{date}.pdf")

print(f"Generating report for {date}")
print(f"Output: {pdf_path}")


# Create PDF

with PdfPages(pdf_path) as pdf:

    for pitcher_name in df["Pitcher"].dropna().unique():

        # Filter data for current pitcher
        pitcher_data = df[df["Pitcher"] == pitcher_name].copy()

        if pitcher_data.empty:
            continue

        # Create page
        fig = plt.figure(figsize=(8.5, 11), facecolor="white")
        fig.subplots_adjust(left=0.07, right=0.98, top=0.86, bottom=0.12, wspace=0.4, hspace=0.7)

        if img is not None:
            fig.figimage(img, xo=40, yo=980, zorder=10)

        fig.suptitle(
            f"\n{pitcher_name}\nDaily Pitching Summary\n{date}",
            fontsize=16,
            fontweight="bold",
            color="black"
        )

        # Grid layout
        outer = fig.add_gridspec(nrows=2, ncols=1, height_ratios=[3, 1], hspace=0.35)
        top = outer[0].subgridspec(nrows=1, ncols=2, width_ratios=[1.0, 1.0], wspace=0.28)


        # Pitch movement

        ax_breaks = fig.add_subplot(top[0, 0])

        present_pitch_types = pitcher_data["TaggedPitchType"].dropna().unique()
        movement_palette = {pitch: pitch_colors.get(pitch, "gray") for pitch in present_pitch_types}

        sns.scatterplot(
            data=pitcher_data,
            x="HorzBreak",
            y="InducedVertBreak",
            hue="TaggedPitchType",
            palette=movement_palette,
            ax=ax_breaks
        )

        ax_breaks.set_title("Pitch Movement")
        ax_breaks.set_xlabel("Horizontal Break (in)")
        ax_breaks.set_ylabel("Induced Vertical Break (in)")

        ax_breaks.axhline(y=0, color="#808080", alpha=0.5, linestyle="--", zorder=1)
        ax_breaks.axvline(x=0, color="#808080", alpha=0.5, linestyle="--", zorder=1)

        ax_breaks.set_xlim(-25, 25)
        ax_breaks.set_ylim(-25, 25)
        ax_breaks.set_aspect("equal", adjustable="box")
        ax_breaks.set_xticks(range(-25, 26, 5))
        ax_breaks.set_yticks(range(-25, 26, 5))

        try:
            ax_breaks.set_box_aspect(1)
        except Exception:
            pass

        ax_breaks.legend(
            title="Pitch Type",
            loc="lower center",
            bbox_to_anchor=(0.5, -0.4),
            frameon=True,
            ncol=max(1, len(present_pitch_types) // 2)
        )


        # Pitch locations

        pitch_types_for_p = pitcher_data["TaggedPitchType"].dropna().unique()
        n_pitch_types = len(pitch_types_for_p)

        if n_pitch_types > 0:
            n_cols = 2 if n_pitch_types <= 4 else 3
            n_rows = math.ceil(n_pitch_types / n_cols)

            wspace = 0.45 if n_cols == 3 else 0.28
            hspace = 0.28

            loc_grid = top[0, 1].subgridspec(
                nrows=n_rows,
                ncols=n_cols,
                wspace=wspace,
                hspace=hspace
            )

            for i, pitch_type in enumerate(pitch_types_for_p):
                row = i // n_cols
                col = i % n_cols

                ax_location = fig.add_subplot(loc_grid[row, col])
                pitch_data = pitcher_data[pitcher_data["TaggedPitchType"] == pitch_type]

                sns.scatterplot(
                    data=pitch_data,
                    x=pitch_data["PlateLocSide"] * 12,
                    y=pitch_data["PlateLocHeight"] * 12,
                    color=pitch_colors.get(pitch_type, "gray"),
                    ax=ax_location
                )

                ax_location.set_title(str(pitch_type))
                ax_location.set_xlabel("")
                ax_location.set_ylabel("")
                ax_location.set_xlim(-20, 20)
                ax_location.set_ylim(0, 60)

                strike_zone = plt.Rectangle(
                    (-8.5, 18),
                    17,
                    24,
                    linewidth=2,
                    edgecolor="blue",
                    facecolor="none",
                    linestyle="--"
                )

                ax_location.add_patch(strike_zone)

                legend = ax_location.get_legend()
                if legend is not None:
                    legend.remove()

                ax_location.set_aspect("equal", adjustable="box")


        # Metrics table

        ax_table = fig.add_subplot(outer[1, 0])
        ax_table.axis("off")

        strike_labels = [
            "StrikeCalled",
            "StrikeSwinging",
            "FoulBallNotFieldable",
            "FoulBallFieldable",
            "InPlay"
        ]

        g = pitcher_data.copy()

        g["is_strike"] = g["PitchCall"].isin(strike_labels)
        g["is_swinging_strike"] = g["PitchCall"].eq("StrikeSwinging")

        g["InZone"] = (
            (g["PlateLocSide"].abs() <= 0.7083)
            & (g["PlateLocHeight"] >= 1.5)
            & (g["PlateLocHeight"] <= 3.5)
        )

        HIT_RESULTS = {"Single", "Double", "Triple", "HomeRun"}
        AB_RESULTS = HIT_RESULTS | {"Out", "FieldersChoice", "Error", "Strikeout"}
        NON_AB_RESULTS = {"Walk", "HitByPitch", "CatcherInterference", "Sacrifice"}

        g["AB"] = (
            (g["PlayResult"].isin(AB_RESULTS) | g["KorBB"].eq("Strikeout"))
            & ~g["PlayResult"].isin(NON_AB_RESULTS)
        )

        g["is_hit"] = g["PlayResult"].isin(HIT_RESULTS)

        total_pitches = len(g) if len(g) else 1


        # Metrics by pitch type

        metrics = (
            g.groupby("TaggedPitchType", dropna=False)
            .apply(lambda x: pd.Series({
                "#": len(x),
                "% Thrown": f"{(len(x) / total_pitches) * 100:.1f}%",
                "Strike %": f"{x['is_strike'].mean() * 100:.1f}%",
                "Zone %": f"{x['InZone'].mean() * 100:.1f}%",
                "Velo": round(x["RelSpeed"].mean(), 1),
                "Max Velo": (
                    lambda s: "" if s.empty else round(s.max(), 1)
                )(pd.to_numeric(x["RelSpeed"], errors="coerce").dropna()),
                "Spin Rate": round(x["SpinRate"].mean(), 1),
                "Spin Axis": round(x["SpinAxis"].mean(), 1),
                "IVB": round(x["InducedVertBreak"].mean(), 1),
                "HB": round(x["HorzBreak"].mean(), 1),
                "Rel Side": round(x["RelSide"].mean(), 1),
                "Rel Height": round(x["RelHeight"].mean(), 1),
                "SwStr %": f"{x['is_swinging_strike'].mean() * 100:.1f}%",
                "BAA": (
                    "N/A"
                    if x["AB"].sum() == 0
                    else f"{x['is_hit'].sum() / x['AB'].sum():.3f}"
                ),
                **(lambda inplay: {
                    "EV": (
                        lambda s: "N/A" if s.empty else f"{s.mean():.1f}"
                    )(
                        pd.to_numeric(
                            x.loc[
                                inplay & ~x["TaggedHitType"].eq("Bunt"),
                                "ExitSpeed"
                            ],
                            errors="coerce"
                        ).dropna()
                    ),
                    "GB %": (
                        "N/A"
                        if inplay.sum() == 0
                        else f"{x.loc[inplay, 'TaggedHitType'].eq('GroundBall').mean() * 100:.1f}%"
                    ),
                    "FB %": (
                        "N/A"
                        if inplay.sum() == 0
                        else f"{x.loc[inplay, 'TaggedHitType'].eq('FlyBall').mean() * 100:.1f}%"
                    ),
                })(x["PitchCall"].eq("InPlay"))
            }))
            .reset_index()
        )


        # Remove Other/Undefined
        if "TaggedPitchType" in metrics.columns:
            metrics = metrics[~metrics["TaggedPitchType"].isin(["Other", "Undefined"])]

        metrics = metrics.rename(columns={"TaggedPitchType": "Pitch"})

        metrics["Pitch"] = pd.Categorical(
            metrics["Pitch"],
            categories=pitch_order,
            ordered=True
        )

        metrics = metrics.sort_values("Pitch").reset_index(drop=True)

        desired_cols = [
            "Pitch",
            "#",
            "% Thrown",
            "Strike %",
            "Velo",
            "Max Velo",
            "Spin Rate",
            "Spin Axis",
            "IVB",
            "HB",
            "Rel Side",
            "Rel Height",
            "EV",
            "GB %",
            "FB %",
            "BAA",
            "SwStr %"
        ]

        metrics = metrics[[col for col in desired_cols if col in metrics.columns]]

        # Total row

        if not metrics.empty:
            total_row = {"Pitch": "Total"}
            total_pitch_count = metrics["#"].astype(float).sum()

            for col in metrics.columns:
                if col == "#":
                    total_row[col] = int(total_pitch_count)

                elif col == "% Thrown":
                    total_row[col] = "100%"

                elif col in ["Strike %", "Zone %", "SwStr %"]:
                    vals = metrics[col].str.rstrip("%").astype(float)
                    weights = metrics["#"].astype(float)

                    weighted_mean = (
                        (vals * weights).sum() / weights.sum()
                        if weights.sum() > 0
                        else 0
                    )

                    total_row[col] = f"{weighted_mean:.1f}%"

                else:
                    total_row[col] = ""

            inplay = g["PitchCall"].eq("InPlay")

            if "EV" in metrics.columns:
                ev_series = pd.to_numeric(
                    g.loc[
                        inplay & ~g["TaggedHitType"].eq("Bunt"),
                        "ExitSpeed"
                    ],
                    errors="coerce"
                ).dropna()

                total_row["EV"] = "N/A" if ev_series.empty else f"{ev_series.mean():.1f}"

            if "GB %" in metrics.columns:
                if inplay.sum() == 0:
                    total_row["GB %"] = "N/A"
                else:
                    gb_rate = g.loc[inplay, "TaggedHitType"].eq("GroundBall").mean() * 100
                    total_row["GB %"] = f"{gb_rate:.1f}%"

            if "FB %" in metrics.columns:
                if inplay.sum() == 0:
                    total_row["FB %"] = "N/A"
                else:
                    fb_rate = g.loc[inplay, "TaggedHitType"].eq("FlyBall").mean() * 100
                    total_row["FB %"] = f"{fb_rate:.1f}%"

            if "BAA" in metrics.columns:
                ab_total = g["AB"].sum()
                hit_total = g["is_hit"].sum()
                total_row["BAA"] = "N/A" if ab_total == 0 else f"{hit_total / ab_total:.3f}"

            metrics = pd.concat([metrics, pd.DataFrame([total_row])], ignore_index=True)

        # Draw table

        if metrics.empty:
            ax_table.text(
                0.5,
                0.5,
                "No pitches for table.",
                ha="center",
                va="center",
                fontsize=10
            )

        else:
            table = ax_table.table(
                cellText=metrics.values,
                colLabels=metrics.columns,
                cellLoc="center",
                loc="center",
                bbox=[-0.072, 0.0, 1.09, 1.0]
            )

            table.auto_set_font_size(False)
            table.set_fontsize(8)
            table.auto_set_column_width(col=list(range(len(metrics.columns))))

            for (r, c), cell in table.get_celld().items():
                if r == 0:
                    cell.set_fontsize(8)
                    cell.set_text_props(weight="bold")
                else:
                    cell.set_height(cell.get_height() * 1.15)


        # Save PDF page

        pdf.savefig(fig)
        plt.close(fig)


print(f"Report successfully created: {pdf_path}")