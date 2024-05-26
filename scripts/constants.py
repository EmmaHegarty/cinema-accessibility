from os import path

INKAR_PATH = path.join('data', 'inkar')
RESULTS_PATH = 'results'

SELECTED = {'top': ['Heidelberg', 'Halle (Saale)', 'Osnabrück', 'Aachen'],
            'mid': ['Landau in der Pfalz', 'Bad Soden am Taunus', 'Aue-Bad Schlema', 'Alfeld (Leine)'],
            'base': ['Kandern', 'Kühlungsborn', 'Seefeld', 'Ankum']}

EXTRACTED_NAME = ['Heidelberg', 'Halle-Saale', 'Osnabrück', 'Aachen',
                  'Landau-in-der-Pfalz', 'Bad-Soden-am-Taunus', 'Aue-Bad-Schlema', 'Alfeld-Leine',
                  'Kandern', 'Kühlungsborn', 'Seefeld', 'Ankum']
EXTRACTED_CHANGED = {'Halle (Saale)': 1, 'Landau in der Pfalz': 4, 'Bad Soden am Taunus': 5,
                     'Aue-Bad Schlema': 6, 'Alfeld (Leine)': 7}

# in seconds
LEISURE_TIME = {'typical': {'women': 6840, 'men': 6300,
                            'children 10-17': 7980, '45-64': 5940, '65 and over': 6480},
                'available': {'women': 20640, 'men': 22380,
                              'children 10-17': 24480, '45-64': 20340, '65 and over': 25680}}

LVL_DUMMY = {'top': 3, 'mid': 2, 'base': 1}
