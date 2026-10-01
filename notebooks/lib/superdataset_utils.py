"""
superdataset_utils.py
---------------------
Utility functions for loading and preparing the superdataset for modelling.
"""

import pandas as pd
from sklearn.model_selection import train_test_split
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import textwrap 
import numpy as np
import seaborn as sns


# DFS subscale and total columns
DFS_SUBSCALE_AND_TOTAL_COLS = [
    'dfs_avoidance_fear',
    'dfs_specific_stimuli_fear',
    'dfs_physiological_arousal',
    'dfs_total_score'
]


# DFS individual item question columns (dfs1–dfs20)
DFS_QUESTION_COLS = [f'dfs{i}' for i in range(1, 21)]

# Participant-level demographic / administrative columns kept in subset
PARTICIPANT_COLS = [
    'Participant_id', 
    'Last_Dental_Visit', 
    'Sex', 
    'Age'
]


def load_superdataset(filepath: str) -> pd.DataFrame:
    """Load the superdataset CSV, treating Participant_id as a string.

    Parameters
    ----------
    filepath : str
        Path to the merged/cleaned superdataset CSV file.

    Returns
    -------
    pd.DataFrame
        Raw superdataset DataFrame.
    """
    return pd.read_csv(filepath, dtype={"Participant_id": "str"})


def load_dfs_subset(filepath: str, drop_cohra2: bool = False, drop_missing_dfs: bool = True) -> pd.DataFrame:
    """Load the superdataset CSV, treating Participant_id as a string, and
    filter to only participants who completed the DFS.

    Parameters
    ----------
    filepath : str
        Path to the merged/cleaned superdataset CSV file.
    drop_cohra2 : bool, default False
        If ``True``, exclude participants from the ``cohra2`` study. The cohra2 cohort is female-only, which skews the sex distribution of the superdataset.
    drop_missing_dfs : bool, default True
        If ``True``, drop participants with any negative sentinel values (e.g. ``-9999`` for missing) in any of the DFS question item columns.

    Returns
    -------
    pd.DataFrame
        Subset of the superdataset DataFrame containing only participants
        who completed the DFS.
    """
    df = load_superdataset(filepath) # load the full superdataset
    dfs_df = df[df['dfs_flag'] == 1].copy() # filter to only participants who completed the DFS 

    # drop cohra2 participants, if requested (default false)
    # The cohra2 cohort is female-only, which skews the sex distribution of the superdataset.
    if drop_cohra2:
        dfs_df = dfs_df[dfs_df['source'] != 'cohra2'] 
    
    # subset to only participant demographic, DFS questions, and DFS subscale/total columns
    dfs_df = dfs_df[PARTICIPANT_COLS + DFS_QUESTION_COLS + DFS_SUBSCALE_AND_TOTAL_COLS]

    # drop missing DFS items, if requested (default true)
    if drop_missing_dfs:
        dfs_df = dfs_df[(dfs_df[DFS_QUESTION_COLS] > 0).all(axis=1)] 

    return dfs_df

## helper functions for visualizations
def shap_ranking(shap_values, feature_names):
    # accept an Explanation, an array, or a list of per-class arrays
    if hasattr(shap_values, "values"):
        arr = shap_values.values
    elif isinstance(shap_values, list):
        arr = np.stack(shap_values, axis=-1)          # -> (n, f, K)
    else:
        arr = np.asarray(shap_values)

    imp = np.abs(arr).mean(axis=0)                    # (f,) or (f, K)
    if imp.ndim == 2:
        imp = imp.sum(axis=1)                         # combine classes, as in the stacked bar plot

    return pd.Series(imp, index=feature_names).sort_values(ascending=False).index.tolist()


def native_ranking(importances, feature_names):
    imp = np.abs(np.asarray(importances))
    if imp.ndim == 2:                 # multinomial LR: coef_ is (n_classes, n_features)
        imp = imp.mean(axis=0)
    return pd.Series(imp, index=feature_names).sort_values(ascending=False).index.tolist()


def get_shap_array(shap_values):
    return shap_values.values if hasattr(shap_values, 'values') else shap_values


def rank_feature_counts_long(rank_df, top_n=None, include_models=False):
    """
    Long-format hierarchical table: (Rank, Feature) -> Count [, Models].
    Excludes zero-count entries automatically.
    """
    df = rank_df.head(top_n) if top_n else rank_df

    records = []
    for rank in df.index:
        row = df.loc[rank]
        for feature in row.unique():
            models = row[row == feature].index.tolist()
            record = {'Rank': rank, 'Feature': feature, 'Count': len(models)}
            if include_models:
                record['Models'] = ', '.join(models)
            records.append(record)

    result = pd.DataFrame(records)
    result = result.sort_values(['Rank', 'Count'], ascending=[True, False])
    result = result.set_index(['Rank', 'Feature'])
    return result


def soften_color(hex_color, amount=0.55):
    """Blend a color toward white. amount=0 -> no change, amount=1 -> pure white."""
    rgb = mcolors.to_rgb(hex_color)
    white = (1, 1, 1)
    softened = tuple(c + (w - c) * amount for c, w in zip(rgb, white))
    return mcolors.to_hex(softened)


def build_feature_color_map(*dfs, cmap_name='tab20', softness=0.55):
    """Build a consistent feature -> soft color mapping across one or more ranking DataFrames."""
    all_features = pd.unique(pd.concat([pd.Series(df.values.ravel()) for df in dfs]))

    cmap1 = plt.get_cmap('tab20')
    cmap2 = plt.get_cmap('tab20b')
    combined_colors = [cmap1(i) for i in range(20)] + [cmap2(i) for i in range(20)]
    colors = [mcolors.to_hex(c) for c in combined_colors[:len(all_features)]]
    colors = [soften_color(c, amount=softness) for c in colors]

    return dict(zip(all_features, colors))


def style_rank_table(df, feature_color_map):
    """Apply consistent per-feature background coloring to a ranking DataFrame."""
    def color_by_feature(val):
        color = feature_color_map.get(val, '#ffffff')
        rgb = mcolors.to_rgb(color)
        luminance = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
        text_color = 'black' if luminance > 0.5 else 'white'
        return f'background-color: {color}; color: {text_color}'

    return df.style.map(color_by_feature)


def top_n_feature_counts(rank_df, top_n=5):
    """Count how many models rank each feature in their top N."""
    return pd.Series(rank_df.head(top_n).values.ravel()).value_counts()


def rank_position_counts(rank_df, top_n=None):
    """Count how many models assign each feature to each rank position."""
    df = rank_df.head(top_n) if top_n else rank_df
    counts = df.apply(pd.Series.value_counts, axis=1).fillna(0).astype(int)
    counts = counts.loc[:, (counts != 0).any(axis=0)]  # drop all-zero columns
    return counts


def compare_top_n_counts(rank_df_a, rank_df_b, top_n=5, names=('a', 'b')):
    """Compare top-N frequency between two ranking tables (e.g., native vs. SHAP)."""
    counts_a = top_n_feature_counts(rank_df_a, top_n=top_n)
    counts_b = top_n_feature_counts(rank_df_b, top_n=top_n)

    comparison = pd.DataFrame({
        f'{names[0]}_count': counts_a,
        f'{names[1]}_count': counts_b,
    }).fillna(0).astype(int)

    comparison = comparison.sort_values(f'{names[0]}_count', ascending=False)
    return comparison


def plot_top_n_counts(counts, top_n=5, title=None, figsize=(6, 3)):
    """Bar plot of feature frequency within top N across models."""
    counts.sort_values().plot(kind='barh', figsize=figsize)
    plt.xlabel(f'Number of models (top {top_n})')
    plt.title(title or f'Feature Frequency in Top {top_n} Across Models')
    # plt.tight_layout()
    plt.show()


def build_model_annotations(rank_df, top_n=None, model_abbrev=None):
    """
    Build a (counts, annotations) pair for a rank heatmap where each cell
    shows both the count and the list of models that assigned that
    feature to that rank, e.g. "3\nRF, XGB, LGB".

    Parameters
    ----------
    rank_df : pd.DataFrame
        A ranking table like native_rank_df or shap_rank_df: rows are
        rank positions (1, 2, 3, ...), columns are model names, and each
        cell holds the feature name that model ranked at that position.

    top_n : int or None, default None
        If set, only build annotations for the top N ranks. If None,
        uses all ranks in rank_df.

    model_abbrev : dict or None, default None
        Optional mapping of {full_model_name: short_name} used to shorten
        model names in the annotation text, e.g.
        {"RandomForest": "RF", "XGBoost": "XGB"}. Any model not in the
        dict is shown with its full name. If None, full names are used.

    Returns
    -------
    counts : pd.DataFrame
        Rank x Feature grid of counts (how many models ranked each
        feature at each rank). Used to drive the heatmap's color scale.

    annot : pd.DataFrame
        Same shape as counts, but each cell is a string like
        "3\nRF, XGB, LGB" (or '' where the count is 0). Pass this to
        plot_rank_heatmap(..., annot=annot) to show model names inside
        each cell instead of just the count.

    Example
    -------
    >>> counts, annot = build_model_annotations(native_rank_df, top_n=5, model_abbrev=model_abbrev)
    >>> plot_rank_heatmap(counts, annot=annot, title='Native — Rank Frequency & Models')
    """
    long_df = rank_feature_counts_long(rank_df, top_n=top_n, include_models=True)

    counts = long_df['Count'].unstack(fill_value=0)
    annot = counts.astype(str).copy()

    for (rank, feature), row in long_df.iterrows():
        models_list = [m.strip() for m in row['Models'].split(',')]
        if model_abbrev:
            models_list = [model_abbrev.get(m, m) for m in models_list]
        models_str = ', '.join(models_list)
        annot.loc[rank, feature] = f"{row['Count']}\n{models_str}"

    annot = annot.where(counts != 0, '')  # blank out cells with no models
    return counts, annot


def plot_rank_heatmap(
    rank_counts, annot=None, figsize=(12, 5), cmap='Blues',
    title='Feature Rank Frequency Across Models', annot_fontsize=8,
):
    """
    Draw a single heatmap of rank_counts (rank x feature -> count of
    models).

    Parameters
    ----------
    rank_counts : pd.DataFrame
        Rank x Feature grid of counts, e.g. from rank_position_counts()
        or the first element returned by build_model_annotations().
        Drives both the cell color and (if annot is None) the displayed
        number.

    annot : pd.DataFrame or None, default None
        Optional string DataFrame the same shape as rank_counts (e.g.
        the second element returned by build_model_annotations()). If
        given, its text is shown in each cell instead of the raw count
        — typically "count\nmodel names". If None, the plain count is
        shown in each cell.

    figsize : tuple, default (12, 5)
        Figure size in inches (width, height). Widen this if annot text
        (model names) is getting cut off or crowded.

    cmap : str, default 'Blues'
        Matplotlib/seaborn colormap for the heatmap's color scale.

    title : str, default 'Feature Rank Frequency Across Models'
        Plot title.

    annot_fontsize : int, default 8
        Font size for the text inside each cell. Lower this if cells
        with model names look cramped.

    Example
    -------
    >>> # counts only
    >>> plot_rank_heatmap(rank_position_counts(native_rank_df, top_n=5))

    >>> # counts + model names
    >>> counts, annot = build_model_annotations(native_rank_df, top_n=5, model_abbrev=model_abbrev)
    >>> plot_rank_heatmap(counts, annot=annot, figsize=(14, 6))
    """
    plt.figure(figsize=figsize)
    sns.heatmap(
        rank_counts,
        annot=annot if annot is not None else True,
        fmt='' if annot is not None else 'd',
        cmap=cmap,
        cbar_kws={'label': 'Number of models'},
        annot_kws={'fontsize': annot_fontsize},
    )
    plt.xlabel('Feature')
    plt.ylabel('Rank')
    plt.title(title)
    plt.tight_layout()
    plt.show()


def plot_rank_heatmaps_side_by_side(
    rank_counts_list, titles, annot_list=None, figsize=(16, 5), cmap='Blues', annot_fontsize=8,
):
    """
    Draw multiple rank-count heatmaps side by side, sharing one color
    scale and one colorbar — useful for comparing e.g. native importance
    vs. SHAP rank frequency.

    Parameters
    ----------
    rank_counts_list : list of pd.DataFrame
        A list of Rank x Feature count grids (e.g.
        [native_counts, shap_counts]), one per panel. All panels share
        the same color scale, computed from the combined min/max across
        every table in this list.

    titles : list of str
        Panel titles, one per entry in rank_counts_list, in the same
        order.

    annot_list : list of pd.DataFrame or None, default None
        Optional list of string DataFrames (same shapes as
        rank_counts_list) to show model names in each panel's cells,
        e.g. [native_annot, shap_annot] from build_model_annotations().
        If None, plain counts are shown in every panel.

    figsize : tuple, default (16, 5)
        Overall figure size in inches (width, height). Widen this when
        annot_list is used, since model-name text needs more room per
        cell.

    cmap : str, default 'Blues'
        Matplotlib/seaborn colormap shared by all panels.

    annot_fontsize : int, default 8
        Font size for the text inside each cell across all panels.

    Example
    -------
    >>> native_counts, native_annot = build_model_annotations(native_rank_df, top_n=5, model_abbrev=model_abbrev)
    >>> shap_counts, shap_annot = build_model_annotations(shap_rank_df, top_n=5, model_abbrev=model_abbrev)
    >>> plot_rank_heatmaps_side_by_side(
    ...     [native_counts, shap_counts],
    ...     titles=['Native Importance', 'SHAP'],
    ...     annot_list=[native_annot, shap_annot],
    ...     figsize=(20, 6),
    ... )
    """
    n = len(rank_counts_list)
    vmin = min(rc.values.min() for rc in rank_counts_list)
    vmax = max(rc.values.max() for rc in rank_counts_list)

    fig, axes = plt.subplots(
        1, n + 1, figsize=figsize,
        gridspec_kw={'width_ratios': [1] * n + [0.05]},
        constrained_layout=True,
    )
    heatmap_axes, cbar_ax = axes[:n], axes[n]

    for i, (ax, rank_counts, title) in enumerate(zip(heatmap_axes, rank_counts_list, titles)):
        annot = annot_list[i] if annot_list else True
        fmt = '' if annot_list else 'd'
        sns.heatmap(
            rank_counts, annot=annot, fmt=fmt, cmap=cmap,
            vmin=vmin, vmax=vmax, ax=ax,
            cbar=(i == n - 1), cbar_ax=cbar_ax if i == n - 1 else None,
            annot_kws={'fontsize': annot_fontsize},
        )
        ax.set_xlabel('Feature')
        ax.set_ylabel('Rank')
        ax.set_title(title)

    cbar_ax.set_ylabel('Number of models')
    plt.show()


def align_rank_counts(*rank_counts_list):
    """Reindex a list of rank-count DataFrames to share the same columns and row order."""
    all_features = sorted(set().union(*(rc.columns for rc in rank_counts_list)))
    return [rc.reindex(columns=all_features, fill_value=0) for rc in rank_counts_list]


def bar_plot_rank_composition(
    long_df,
    figsize=(10, 5),
    cmap_name='tab20',
    softness=0.45,
    fontsize=12,
    fontweight='normal',
    show_models=True,
    models_fontsize=None,
    wrap_width=30,
    model_abbrev=None,
    show_legend=True,
    legend_fontsize=None,
    legend_loc='right',   # 'right' or 'bottom'
    legend_cols=4,        # only used when legend_loc='bottom'
):
    """
    Stacked horizontal bar chart showing, for each rank position, which
    features were assigned that rank by how many models (and by which
    models).

    Parameters
    ----------
    long_df : pd.DataFrame
        Output of rank_feature_counts_long(rank_df, top_n=..., include_models=True).
        Must have a MultiIndex (Rank, Feature) and a 'Count' column.
        Include a 'Models' column (via include_models=True) to show model
        names under each segment and to enable the legend.

    figsize : tuple, default (10, 5)
        Overall figure size in inches (width, height). Increase width if
        legend_loc='right' and the legend feels cramped.

    cmap_name : str, default 'tab20'
        Matplotlib colormap used to assign a distinct base color to each
        feature before softening.

    softness : float, default 0.45
        How much to blend each feature's color toward white (0 = full
        saturation, 1 = white). Higher = softer/lighter bar colors.

    fontsize : int, default 10
        Base font size for the "{feature} ({count})" labels, axis ticks,
        and y-axis rank labels. Title is fontsize + 2.

    fontweight : str, default 'normal'
        Font weight for the feature/count labels (e.g., 'normal', 'bold').

    show_models : bool, default True
        If True and long_df has a 'Models' column, prints the list of
        models under each segment's feature/count label.

    models_fontsize : int or None, default None
        Font size for the models text under each segment. Defaults to
        fontsize - 2 (minimum 6) if not set.

    wrap_width : int, default 20
        Max characters per line before wrapping the models text. Lower
        this if model names are long or segments are narrow.

    model_abbrev : dict or None, default None
        Optional mapping of {full_model_name: short_name} used to shorten
        model names in both the models text and the legend, e.g.
        {"RandomForest": "RF", "XGBoost": "XGB"}. Any model not in the
        dict is shown with its full name.

    show_legend : bool, default True
        If True, show_models=True, and model_abbrev is provided, adds a
        legend mapping each abbreviation back to its full model name.

    legend_fontsize : int or None, default None
        Font size for the legend text. Defaults to fontsize if not set.

    legend_loc : str, default 'right'
        Where to place the legend: 'right' (vertical list beside the
        plot, avoids overlapping the x-axis) or 'bottom' (grid below
        the plot).

    legend_cols : int, default 4
        Number of abbreviation entries per row. Only used when
        legend_loc='bottom'.

    Example
    -------
    >>> native_long = rank_feature_counts_long(native_rank_df, top_n=5, include_models=True)
    >>> model_abbrev = {
    ...     "RandomForest": "RF", "XGBoost": "XGB", "LightGBM": "LGB",
    ...     "HistGB": "HGB", "ElasticNet": "EN", "Ridge": "Ridge",
    ...     "Lasso": "Lasso", "SVR": "SVR",
    ... }
    >>> bar_plot_rank_composition(
    ...     native_long,
    ...     figsize=(13, 6),
    ...     model_abbrev=model_abbrev,
    ...     show_legend=True,
    ...     legend_loc='right',
    ... )

    Minimal call (no models text, no legend):
    >>> bar_plot_rank_composition(native_long, show_models=False, show_legend=False)
    """
    ranks = long_df.index.get_level_values('Rank').unique().sort_values()
    all_features = long_df.index.get_level_values('Feature').unique()

    cmap = plt.colormaps.get_cmap(cmap_name).resampled(len(all_features))
    feature_colors = {
        f: soften_color(mcolors.to_hex(cmap(i)), amount=softness)
        for i, f in enumerate(all_features)
    }

    models_fontsize = models_fontsize or max(fontsize - 2, 6)
    legend_fontsize = legend_fontsize or fontsize
    has_models_col = 'Models' in long_df.columns
    model_abbrev = model_abbrev or {}

    fig, ax = plt.subplots(figsize=figsize)

    for rank in ranks:
        left = 0
        row_data = long_df.loc[rank]
        for feature, data in row_data.iterrows():
            count = data['Count']
            color = feature_colors[feature]

            ax.barh(rank, count, left=left, color=color, edgecolor='white')

            rgb = mcolors.to_rgb(color)
            luminance = 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]
            text_color = 'black' if luminance > 0.6 else 'white'

            ax.text(
                left + count / 2, rank - 0.15,
                f"{feature} ({count})",
                ha='center', va='center',
                fontsize=fontsize, fontweight=fontweight, color=text_color,
            )

            if show_models and has_models_col:
                models_list = [m.strip() for m in data['Models'].split(',')]
                models_list = [model_abbrev.get(m, m) for m in models_list]
                models_str = ', '.join(models_list)
                wrapped_models = '\n'.join(textwrap.wrap(models_str, width=wrap_width))
                ax.text(
                    left + count / 2, rank + 0.2,
                    wrapped_models,
                    ha='center', va='top',
                    fontsize=models_fontsize, color=text_color,
                )

            left += count

    ax.set_yticks(ranks)
    ax.set_yticklabels([f'Rank {r}' for r in ranks], fontsize=fontsize)
    ax.invert_yaxis()
    ax.set_xlabel('Number of models', fontsize=fontsize)
    ax.set_title('Feature Composition by Rank', fontsize=fontsize + 2)
    ax.tick_params(axis='x', labelsize=fontsize)

    if show_legend and show_models and model_abbrev:
        items = [f"{abbrev} = {full}" for full, abbrev in model_abbrev.items()]

        if legend_loc == 'right':
            legend_text = '\n'.join(items)
            fig.subplots_adjust(right=0.78)
            fig.text(
                0.80, 0.5, legend_text,
                ha='left', va='center', fontsize=legend_fontsize,
                linespacing=2.0,
            )
        else:  # 'bottom'
            n_rows = -(-len(items) // legend_cols)  # ceil division
            rows = [items[i:i + legend_cols] for i in range(0, len(items), legend_cols)]
            legend_text = '\n'.join('     '.join(row) for row in rows)

            bottom_margin = 0.08 + 0.05 * n_rows
            fig.subplots_adjust(bottom=bottom_margin)
            fig.text(
                0.5, bottom_margin - 0.05, legend_text,
                ha='center', va='top', fontsize=legend_fontsize,
                linespacing=1.8,
            )

    plt.show()


