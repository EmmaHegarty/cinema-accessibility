from os import path

from scripts.utils import germany_admin, get_polygon_bbox
from scripts.constants import SELECTED, EXTRACTED_NAME, EXTRACTED_CHANGED


# create command to extract a subset from an osm.pbf file with the osmium library
# {args} bbox_string: str, name: str, full_gtfs: str
# {returns} command string
def osmium_command(bbox_string, name):
    return f'osmium extract --bbox {bbox_string} --output {name}-extract.osm.pbf'


# create command to extract a subset from a gtfs feed with the gtfs-general library
# {args} bbox_string: str, name: str, full_gtfs: str
# {returns} command string
def gtfs_general_command(bbox_string, name, full_gtfs):
    gtfs_path = path.join('data', 'gtfs_files')
    input_zip = path.join(gtfs_path, f'{full_gtfs}.zip')
    filtered = path.join(gtfs_path, f'{name}_{full_gtfs}')

    if path.isfile(path.join(gtfs_path, f'{filtered}.zip')):
        return 'exists'

    poetry_cmd = f'poetry run gtfs-general extract-bbox --input-object {input_zip} --output-folder {filtered} --bbox {bbox_string}'

    return poetry_cmd


# get extraction commands for all selected areas and write them into a txt file
# {args} full_gtfs: str, level: str
# {returns} command string
def get_commands_for_selected(full_gtfs, level):
    osm_commands = []
    gtfs_commands = []
    # loop through files in folder, each file should contain the selected areas of one class
    for name in SELECTED[level]:
        print(name)
        krs = germany_admin('GEM')
        area = krs[krs['GEN'] == name]

        bbox_string = get_polygon_bbox(area['geometry'].iloc[0], 25832, True)
        area_name = area['GEN'].values[0]

        # gtfs_general commands do not take spaces or brackets, so the changed filenames are saved in a constant
        if area_name in EXTRACTED_CHANGED:
            name = EXTRACTED_NAME[EXTRACTED_CHANGED[area_name]]
        else:
            name = area_name

        # gtfs_general commands do not take spaces or brackets, so the changed filenames are saved in a constant
        if area_name in EXTRACTED_CHANGED:
            name = EXTRACTED_NAME[EXTRACTED_CHANGED[area_name]]
        else:
            name = area_name

        osm_commands.append(osmium_command(bbox_string, name))
        gtfs_commands.append(gtfs_general_command(bbox_string, name, full_gtfs))

    with open(f'data/commands/osmium_commands_selected_{level}.txt', 'w') as txt_file:
        for line in osm_commands:
            txt_file.write(''.join(line) + "\n")

    with open(f'data/commands/extract_commands_selected_{level}.txt', 'w') as txt_file:
        for line in gtfs_commands:
            txt_file.write(''.join(line) + "\n")


if __name__ == "__main__":
    for centrality in ['top', 'mid', 'base']:
        gtfs_filename = 'opnv_240218'
        get_commands_for_selected(gtfs_filename, centrality)
