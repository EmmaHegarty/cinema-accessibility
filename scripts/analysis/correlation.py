from os import path
from pandas import read_csv, DataFrame
from scipy.stats import pearsonr

from scripts.constants import RESULTS_PATH, SELECTED


# calculate pearson correlation coefficient
# {args} dependent: [str], area: str, prefix: str, path_end: str
# {returns} None, writes new file
def get_corr(dependents, area, prefix='analysis', path_end='15-18-21_Sat_104'):
    df = read_csv(path.join(RESULTS_PATH, 'analysis', f'{prefix}_{area}_{path_end}.csv'))
    deps = []
    feats = []
    corrs = []
    p_values = []

    numeric_cols = [col for col in df.columns if
                    any(substr in col for substr in
                        ['duration', 'changes', 'distance_start_centroid', 'distance_start_cinema', 'speed',
                         'walk_share', 'population', 'built-up', 'transit', 'dummy'])]

    for dep in dependents:
        for feat in numeric_cols:
            if feat != dep:
                deps.append(dep)
                feats.append(feat)
                clean_df = df.dropna(subset=[feat, dep])
                corr, p_value = pearsonr(clean_df[feat], clean_df[dep])
                corrs.append(corr)
                p_values.append(p_value)

    res = DataFrame({'variable': feats, 'dependent': deps,  'correlation': corrs, 'p_value': p_values})
    res.to_csv(path.join(RESULTS_PATH, 'correlation', f'corr_{area}_{path_end}.csv'))


if __name__ == "__main__":
    get_corr(['average duration', 'average speed', 'transit is reasonable'], 'variables', 'all')
    get_corr(['average duration', 'average speed'], 'starts_variables', 'all')

    for name in SELECTED['top']:
        get_corr(['average duration', 'average speed', '15 transit is reasonable'], name, 'starts_variables')
