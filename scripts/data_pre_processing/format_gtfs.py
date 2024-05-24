from os import path, listdir
from pandas import read_csv

from scripts.utils import create_zip, remove_dir
from scripts.constants import SELECTED, EXTRACTED_NAME, EXTRACTED_CHANGED


# replace na values with 0, assign value types to columns and save gtfs txt files in zip archive
# {args} gtfs: str, level: str, unzipped: boolean
# {returns} None, creates zip archives
def filter_gtfs_na(gtfs):
    output_path = path.join('data', 'gtfs_files', gtfs)

    file_names = ('stops.txt', 'stop_times.txt', 'trips.txt', 'routes.txt', 'calendar.txt', 'calendar_dates.txt')

    for fid, file in enumerate(file_names):
        if file in listdir(output_path):
            df = read_csv(path.join(output_path, file))
            int_df = df.fillna(0)
            if fid == 0:
                int_df = int_df.astype({'location_type': 'int'})
            elif fid == 1:
                int_df['stop_headsign'] = df['stop_headsign'].apply(lambda x: 'no value' if x == 0 else x)
                int_df = int_df.astype({'stop_headsign': 'str', 'pickup_type': 'int', 'drop_off_type': 'int'})

            int_df.to_csv(path.join(output_path, file_names[fid]), index=False)
    create_zip(output_path, f'{gtfs}_filtered.zip')
    remove_dir(output_path)


# filter extracted gtfs feeds for all selected areas
# {args} full_gtfs: str, level: str, unzipped: boolean
# {returns} None, creates zip archives
def filter_all(full_gtfs, level):
    for area in SELECTED[level]:
        if area in EXTRACTED_CHANGED:
            name = EXTRACTED_NAME[EXTRACTED_CHANGED[area]]
        else:
            name = area

        gtfs_name = f'{name}_{full_gtfs}'
        if path.isdir(path.join('data', 'gtfs_files', gtfs_name)):
            filter_gtfs_na(gtfs_name)
        else:
            print(f'{gtfs_name} is not a directory.')
    print('finished filtering all extracted')


if __name__ == "__main__":
    for centrality in ['top', 'mid', 'base']:
        gtfs_filename = 'opnv_240218'
        filter_all(gtfs_filename, centrality)
