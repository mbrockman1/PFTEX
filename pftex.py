# %%
import tabula
import pandas as pd
import PyPDF2
import glob
from itertools import chain

import numpy as np
import matplotlib.pyplot as plt

# %%


# %%
def st_to_float(val):
    if type(val) == str:
        return(float(val.replace('*', '')))
    else:
        return(val)

# %%
file_list = glob.glob('pfts/*.pdf', recursive=True)

# %%
class Patient(object):
    def __init__(self, data_loc):
        self.data_loc = data_loc
        self.raw_tabula = tabula.io.read_pdf(self.data_loc, pages="all")[0:]
        if len(self.raw_tabula) == 1:
            self.raw_data = self.raw_tabula[0]
        else:
            table_1 = self.raw_tabula[0]
            table_2 = self.raw_tabula[1]
            base_columns = table_1.columns
            table_2.columns = base_columns[0: len(table_2.columns)]
            table_2 = table_2.dropna(subset=['Unnamed: 0'])
            self.raw_tabula = pd.concat([table_1, table_2])
            self.raw_data = self.raw_tabula.drop_duplicates()
        self.cleaned_data = self._data_cleaner(self.raw_data).set_index('measured')
        self.to_excel = self.cleaned_data.stack().to_frame().T
        self._name_dob_mrn_parser()
        self._diagnosis_cough_wheeze_parser()
        self.to_excel.columns = self.to_excel.columns.map('_'.join)
        self.to_excel.insert(0, "Interpretation", self.interpretation, True)
        self.to_excel.insert(0, "Wheeze Status", self.wheeze_status, True)
        self.to_excel.insert(0, "Smoke Status", self.smoke_status, True)
        self.to_excel.insert(0, "Cough Status", self.cough_status, True)
        self.to_excel.insert(0, "BMI", self.bmi, True)
        self.to_excel.insert(0, "Race", self.race, True)
        self.to_excel.insert(0, "Gender", self.gender, True)
        self.to_excel.insert(0, "DOB", self.dob, True)
        self.to_excel.insert(0, "Study Date", self.study_data, True)
        self.to_excel.insert(0, "MRN", self.mrn, True)
        
        
    def _name_dob_mrn_parser(self):
        pdfFileObj = open(self.data_loc, 'rb')
        # creating a pdf reader object
        pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
        # creating a page object
        pageObj = pdfReader.getPage(0)
        # extracting text from page
        extracted_txt = pageObj.extractText().split('\n')
        
        raw_line = [line for line in extracted_txt if line.startswith('Name')][0]
        self.last_name = raw_line.split(': ')[1].split(',')[0]
        self.dob = raw_line.split(' Birth Date')[0][-10:-1]
        self.first_name = raw_line.split(self.dob)[0].split(', ')[1]
        self.mrn, self.age = raw_line.split(' Age:')[0].split(' ')[-2:]
        self.study_data = extracted_txt[2].split(' ')[-2]
        pdfFileObj.close()
        
    def _wheeze_no_wheeze(self, string):
        if ' No Wheeze ' in string:
            self.wheeze_status = 'No Wheeze'
        elif ' Frequent ' in string:
            self.wheeze_status = 'Frequent'
        elif ' Constant ' in string:
            self.wheeze_status = 'Constant'
        elif ' Rare ' in string:
            self.wheeze_status = 'Rare'
        else:
            self.wheeze_status = 'None'

    def _cough_no_cough(self, string):
        if ' No Cough ' in string:
            self.cough_status = 'No Cough'
        elif ' Productive ' in string:
            self.cough_status = 'Productive'
        elif ' Non-Productive ' in string:
            self.cough_status = 'Non-Productive'
        

    def _cig_no_cig(self, string):
        if ' Never Smoked ' in string:
            self.smoke_status = 'Never Smoked'
        elif ' Cigarette ' in string:
            self.smoke_status = 'Cigarette'
        elif ' Marijuana ' in string:
            self.smoke_status = 'Marijuana'
        elif ' Vapping ' in string:
            self.smoke_status = 'Vapping'
            
    def _gender(self, string):
        if 'Female' in string:
            self.gender = 'Female'
        elif ' Male ' in string:
            self.gender = 'Male'

    def _bmi(self, string):
        self.bmi = string.split(' ')[
            string.split(' ').index('BMI:') + 1]
        
    def _race_id(self, string):
        self.race = string.split(' ')[
            string.split(' ').index('Race:') + 1]

    def _diagnosis_cough_wheeze_parser(self):
        pdfFileObj = open(self.data_loc, 'rb')
        # creating a pdf reader object
        pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
        # creating a page object
        pageObj = pdfReader.getPage(0)
        # extracting text from page
        extracted_txt = pageObj.extractText().split('\n')
        
        for line in extracted_txt:
            if 'Cough: ' in line and 'Wheeze: ':
                line = line.replace('Cough: ','').replace('Wheeze: ', '')
                self._cough_no_cough(line)
                self._wheeze_no_wheeze(line)
            if 'Smoked: ' in line:
                line = line.replace('Smoked: ','')
                self._cig_no_cig(line)
            if 'Gender: ' in line:
                self._gender(line)
            if 'BMI: ' in line:
                self._bmi(line)
            if 'Race: ' in line:
                self._race_id(line)
        
        extracted_txt = ''
        for i in range(pdfReader.numPages):
            page = pdfReader.getPage(i)
            extracted_txt += page.extractText()
        extracted_txt = extracted_txt.split('\n')

        interpretation_index = [0, 0]
        for index, line in enumerate(extracted_txt):
            if line.startswith('Spirometry '):
                interpretation_index[0] = index
            elif line.startswith(
                '««This interpretation has been electronically signed:'):
                interpretation_index[1] = index
        self.interpretation = extracted_txt[
            interpretation_index[0]:
            interpretation_index[1] + 1]
        self.interpretation = ' '.join([
            str(elem) for elem in self.interpretation])
        
        
        pdfFileObj.close()
        
    def _data_cleaner(self, df):
        df = df[df['Unnamed: 0'].notna()]
        df = df[df['Unnamed: 0'].str.contains('SPIROMETRY')==False]
        df = df[df['Unnamed: 0'].str.contains('LUNG VOLUMES')==False]
        df = df[df['Unnamed: 0'].str.contains('AIRWAYS RESISTANCE')==False]
        df = df[df['Unnamed: 0'].str.contains('DIFFUSION')==False]
        df.rename(columns = {
                    'Unnamed: 0':'measured',
                    'Actual':'prebronch-actual',
                    'Pred':'prebronch-pred',
                    '%Pred':'prebronch-%pred',
                    'Actual.1':'postbronch-actual',
                    '%Chng':'%change',
                    '%Pred.1':'postbronch-%pred',},
                  inplace = True)
        return df

# %%





# %%
pt_list = []
for index, file in enumerate(file_list):
    try:
        pt_list.append(Patient(file))
    except:
        print('Failure: %s at index: %s' % (file, index))

# %%
count = pd.Series([pt.mrn for pt in pt_list]).value_counts()
print("Element Count")
for index, val in count.iteritems():
    if val > 1:
        print(index, val)

# %%
excel_list = [pt.to_excel for pt in pt_list]

# %%
list_of_dicts = [cur_df.T.to_dict().values() for cur_df in excel_list]    
results = pd.DataFrame(list(chain(*list_of_dicts))) 

# %%
results

# %%
results.to_excel('./output.xlsx')


