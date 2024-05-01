import pandas as pd
import openpyxl
import io
import tempfile
from sklearn.metrics import mean_squared_error  
import json
import pandas as pd
from sklearn.preprocessing import OneHotEncoder
from sklearn.metrics import mean_squared_error  
import numpy as np 
from sklearn.metrics import accuracy_score

class AbstractModel:
    
    color_mapping = {}
    features = ["date_code" ,'name_code' ,"color_code" , 'value' ]
    target = 'next_color_binary'
    last_long_df = None
    preferred_color = ['D5A6BD' , 'FFC000' ]      
    # ['A9D08E' green , '9BC2E6' blue , 'FFC000' orange, 'FFFF00' yellow, 'D5A6BD' purple, 'FF0000' red, '8EA9DB' blue]
    last_df = None

    def preprocess_excel(self , uploaded_file):
        # Load the workbook
        wb = openpyxl.load_workbook(filename=uploaded_file)
        ws = wb.active

        # Iterate through the cells, skipping the first row and the first column
        for row in ws.iter_rows(min_row=2, min_col=2):
            for cell in row:
                # Check for background color's hex code
                color_hex = cell.fill.start_color.index[2:] if cell.fill.start_color.index else 'None'

                # Combine the value with the color hex code within the same cell
                cell.value = f"{cell.value} | {color_hex}"

        # Save the updated workbook to a temporary file and return it
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
            wb.save(tmp.name)
            tmp.seek(0)
            df = pd.read_excel(io.BytesIO(tmp.read()))
            # Get the first and last columns as Series
            first_column = df.iloc[:, 0]
            last_column = df.iloc[:, -1]

            # Concatenate the Series into a new DataFrame
            self.last_df = pd.concat([first_column, last_column], axis=1)
            self.row_count =  df.shape[0]
            
            return df
        



    def color_change(self , x):
        if x in self.preferred_color:
            return 1
        else:
            return 0

    def process_data(self ,df):
        if self.color_mapping:
            raise Exception("data process has already processed")
        # Processing the DataFrame 'data' to have "date", "name", "color_value" columns
        long_df = pd.melt(df, id_vars=['NAME'], var_name='date', value_name='color_and_value')

        # Convert dates and name to a numerical value, 
        long_df['name_code'] = long_df['NAME'].str.extract(r'(\d+)').astype(int)
        # long_df = long_df[long_df['name_code'] ==  101]
        long_df['date'] = pd.to_datetime(long_df['date'])
        # Get day of the month
        long_df['day_of_month'] = long_df['date'].dt.day

        # Get day of the week (Monday=0, Sunday=6)
        long_df['day_of_week'] = long_df['date'].dt.dayofweek


        codes, uniques = pd.factorize(long_df['date'])
        long_df['date_code'] = codes

        long_df['day_of_year'] = long_df['date'].dt.dayofyear.astype(int)

        long_df['date'] = long_df['date'].astype(int) 
        
        long_df[['value', 'color']] = long_df['color_and_value'].str.split(' \| ', expand=True)
        long_df['value'] =  long_df['value'].astype(float)

        codes, uniques = pd.factorize(long_df['color'])
        
        # Add 1 to codes to start numbering from 1 instead of 0
        long_df['color_code'] = codes 
        long_df['next_color_code'] = long_df.groupby('name_code')['color_code'].shift(-1)
        long_df['previous_color_code'] = long_df.groupby('name_code')['color_code'].shift(1)
       
        long_df['color_binary'] = long_df['color'].map(lambda x : self.color_change(x)).astype(int)
        
        long_df['next_color_binary'] = long_df.groupby('name_code')['color_binary'].shift(-1)

        
        

        return long_df 


    def process_excel(self ,uploaded_file):
        df = self.preprocess_excel(uploaded_file)
        return self.process_data(df)
    

    def set_metrics(self, predictions , y_test):
       
        self.mse = mean_squared_error(y_test, predictions)
        self.accuracy  = accuracy_score(y_test, predictions)
        correct = 0
        self.predictions_count = 0
        self.y_test_count = 0
        for t, p in zip(y_test, predictions):
            # If the predicted color is not in the allowed values, count it (regardless of it being correct)
            # OR
            # If the predicted color is an allowed value and matches the true color, count it
            if  t == p and t == 1:
                correct += 1
            if p  == 1:
                self.predictions_count += 1
            if t == 1:
                self.y_test_count +=1 

        self.preferred_accuracy = correct / self.predictions_count if  self.predictions_count != 0 else 0 


       
    
    
    
    def color_mapper(self , x):
        if x in self.color_mapping:
            return self.color_mapping[x]
        else:
            last_key = sorted(self.color_mapping.keys())[-1]
            return self.color_mapping[last_key]

    def predict_last(self):
        if  self.last_long_df is None:
            raise Exception('Must be trained')
        predictions = self.predict(self.last_long_df)
        predicted_df = self.last_df
        predicted_df['color_and_value'] =  self.last_long_df['color_and_value'].values
        predicted_df['next_color_code'] =  predictions
        return predicted_df
    

    def train_test_split(self, long_df):
        # Prepare the dataset for Linear Regression
        # Updated to include 'name_as_number' as an additional feature
        self.last_long_df = long_df[-self.row_count:]
        long_df = long_df.dropna(axis=0)
        X = long_df[self.features].values # Features
        y = long_df[self.target].values  # Target

        
        return  X, y
    def predict(self , X):
        raise Exception('Not emplemented')
    
    