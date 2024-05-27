from os import path
from pandas import read_csv
from plotly.express import histogram

from scripts.constants import RESULTS_PATH, IMAGES_PATH, SELECTED

AREA_ORDER = ['Aachen', 'Halle (Saale)', 'Heidelberg', 'Osnabrück', 'Alfeld (Leine)', 'Aue-Bad Schlema',
              'Bad Soden am Taunus', 'Landau in der Pfalz', 'Ankum', 'Kandern', 'Kühlungsborn', 'Seefeld']
GROUP_ORDER = ['children 10-17', '45-64', '65 and over', 'men', 'women']


def bar_chart(column, color, x, filespec, prefix='analysis', path_end='15-18-21_Sat_104', filename=None,
              folder='analysis', assigned_color=None, title=None, labels=None, order=None, img_height=None, norm=None):
    df = read_csv(path.join(RESULTS_PATH, folder, f'{prefix}_{filespec}_{path_end}.csv'))
    sorted_df = df.sort_values(by=color)

    if title is None and column is not None:
        title = f'{column.replace("_", " ")} in {filespec.replace("_", " ")}'

    if x == 'departure time':
        sorted_df['departure time'] = sorted_df['departure time'].astype(str)

    fig = histogram(sorted_df, x=x, y=column, color=color, color_discrete_map=assigned_color, title=title,
                    labels=labels, category_orders=order, barnorm=norm)
    fig.update_layout(bargap=0.5)

    if filename is None:
        fig.show()
    else:
        if prefix == 'all':
            img_height = 400
        fig.write_image(path.join(IMAGES_PATH, f'{filename}_{column}.jpeg'), height=img_height, scale=1.8)


if __name__ == "__main__":
    pe = '15-18-21_Sat_104'

    bar_chart('average duration', 'level', 'area', 'starts_variables_filled', 'all', pe, 'all_overview',
              title='average duration per start point',
              labels={
                  'average duration': 'average duration (in s)',
                  'level': 'regional centrality'},
              order={'area': AREA_ORDER})

    for name in SELECTED['top']:
        print(name)

        # compare departure times
        for var in ['fastest mode', 'fastest overall mode']:
            bar_chart(None, var, 'departure time', name, 'time_analysis', pe, f'{var}_{name}',
                      assigned_color={'car': '#00cc96', 'transit': '#636efa', 'foot': '#ef553b'})

        # groups analysis
        for var in ['likely', 'possible']:
            bar_chart('average travel time', f'average {var}', 'group', name, 'groups', '[15, 18, 21]', f'{var}_{name}',
                      'groups',
                      assigned_color={'yes': '#00cc96', 'no': '#ef553b', 'no data': 'grey'},
                      labels={
                          'average travel time': 'average travel time (in s)',
                          'average likely': 'cinema is accessible<br>within "social life and<br>entertainment" time',
                          'average possible': 'cinema is accessible<br>within total leisure time'},
                      order={'group': GROUP_ORDER})
