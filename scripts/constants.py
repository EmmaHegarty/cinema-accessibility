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
