from pandas import isnull


# {args} df: df, time: [int] or int, average: boolean
# {returns} df or float
def get_speed(df, time, average=False):
    if isinstance(time, list):
        for t in time:
            df[f'{t}_speed'] = df.apply(
                lambda row: row['distance_start_cinema'] / row[f'{t}_total_duration'] if isinstance(
                    row[f'{t}_total_duration'], float) else 'no duration available', axis=1)
        return df.apply(lambda row: sum([row[f'{t2}_speed'] / len(time) for t2 in time]), axis=1)
    else:
        speed = df.apply(
            lambda row: row['distance_start_cinema'] / row[f'{time}_total_duration'] if isinstance(
                row[f'{time}_total_duration'], float) else 'no duration available', axis=1)
        if average:
            return speed.mean(numeric_only=True)
        else:
            return speed


# {args} df: df, time: [int] or int
# {returns} df or float
def get_avg_time(df, time):
    if isinstance(time, list):
        return df.apply(lambda row: sum([row[f'{t}_total_duration'] for t in time]), axis=1)
    elif isinstance(time, int):
        return df[f'{time}_total_duration'].mean()


# {args} df: df, time: int, average: boolean
# {returns} float or df
def get_transit_time(df, time, average=False):
    transit = df.apply(lambda row: row[f'{time}_total_duration'] - (row[f'{time}_walk_to'] + row[f'{time}_walk_from']),
                       axis=1)
    if average:
        return transit.mean(numeric_only=True)
    else:
        return transit


# {args} df: df, time: int, average: boolean
# {returns} float or df
def get_walk_time(df, time, average=False):
    walk = df.apply(lambda row: row[f'{time}_walk_to'] + row[f'{time}_walk_from'], axis=1)
    if average:
        return walk.mean(numeric_only=True)
    else:
        return walk


# {args} df: df, time: int, result: str or int
# {returns} df or float
def get_walk_percent(df, time, result=None):
    df2 = df.assign(walk=get_walk_time(df, time))
    percent = df2.apply(lambda row: 100 / row[f'{time}_total_duration'] * row['walk'], axis=1)

    if result == 'column':
        return percent
    elif result == 'avg':
        return percent.mean()
    elif result == 'max':
        return percent.max()
    elif result == 'min':
        return percent.min()
    elif isinstance(result, int):
        cutoff = list(filter(lambda item: item < result, percent.values))
        return len(cutoff) / len(percent) if len(percent) else None


# {args} df: df, time: [int] or int
# {returns} df or float
def get_avg_changes(df, time):
    if isinstance(time, list):
        return df.apply(lambda row: sum([row[f'{t}_total_changes'] for t in time]), axis=1)
    else:
        return df[f'{time}_total_changes'].mean()


# {args} df: df, time: int
# {returns} int
def get_max_changes(df, time):
    return df[f'{time}_total_changes'].max()


# {args} df: df, time: [int] or int, average: boolean
# {returns} df or float
def get_car_compare(df, time, average=False):
    if isinstance(time, list):
        return df.apply(lambda row: row['average duration'] - row['car_duration'], axis=1)
    else:
        diff = df.apply(lambda row: row[f'{time}_total_duration'] - row['car_duration'], axis=1)
        if average:
            return diff.mean(numeric_only=True)
        else:
            return diff


# {args} df: df, time: int, column: str
# {returns} df or float
def get_fastest_mode(df, time, column='fastest_mode'):
    counts = df[f'{time}_{column}'].value_counts()
    transit_count = counts['transit'] if 'transit' in counts.index else 0
    return 100 / len(df) * transit_count


# {args} df: df, time: int, percent: boolean
# {returns} float or int
def get_valid_entries(df, time, percent=False):
    valid = list(filter(lambda item: not isnull(item), df[f'{time}_total_duration']))
    if percent:
        return len(valid) / len(df) if len(df) else None
    else:
        return len(valid)


# {args} df: df, time: int, column: str
# {returns} str
def get_majority_mode(df, time, column='fastest_mode'):
    counts = df[f'{time}_{column}'].value_counts()
    mode = 'transit' if 'transit' in counts.index and counts['transit'] > len(df)/2\
        else 'foot' if 'foot' in counts.index and counts['foot'] > len(df)/2 else 'both'
    return mode


# {args} df: df, time: int, value: str
# {returns} [int, str]
def get_min_max_cinema(df, time, value='min'):
    if value == 'min':
        dur = df[f'{time}_total_duration'].min()
    elif value == 'max':
        dur = df[f'{time}_total_duration'].max()
    else:
        raise ValueError('min or max not given')

    cinema = df[df[f'{time}_total_duration'] == dur]['cinema_name']
    if cinema is None or len(cinema) == 0:
        name = 'NaN'
    else:
        name = cinema.values[0]

    return [dur, name]
