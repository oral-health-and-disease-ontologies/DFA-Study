"""
superdataset_utils.py
---------------------
Utility functions for loading and preparing the superdataset for modelling.
"""

import pandas as pd
from sklearn.model_selection import train_test_split


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
        df = dfs_df[dfs_df['source'] != 'cohra2'] 
    
    # subset to only participant demographic, DFS questions, and DFS subscale/total columns
    dfs_df = dfs_df[PARTICIPANT_COLS + DFS_QUESTION_COLS + DFS_SUBSCALE_AND_TOTAL_COLS]

    # drop missing DFS items, if requested (default true)
    if drop_missing_dfs:
        dfs_df = dfs_df[(dfs_df[DFS_QUESTION_COLS] > 0).any(axis=1)] 

    return dfs_df

