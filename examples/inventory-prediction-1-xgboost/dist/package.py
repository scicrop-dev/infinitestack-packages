import numpy as np
import sys
from pathlib import Path
import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sb
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn import metrics
from sklearn.svm import SVC
from xgboost import XGBRegressor
from sklearn.linear_model import LinearRegression, Lasso, Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error as mae
from datetime import date
import holidays
from datetime import datetime
from sklearn.metrics import mean_absolute_error as mae, r2_score
from xgboost import XGBRegressor
import psycopg2


def generate_future_dataframe(month, year, df):
    stores = df['store'].unique()
    items  = df['item'].unique()
    future_records = []
    for store in stores:
        for item in items:
            for day in range(1, 32):
                try:
                    d = datetime(year, month, day)
                    weekday = d.weekday()
                    weekend = 1 if weekday >= 5 else 0
                    m1 = np.sin(month * (2*np.pi/12))
                    m2 = np.cos(month * (2*np.pi/12))
                    holiday = is_holiday(d.strftime("%Y-%m-%d"))

                    future_records.append({
                        'store':    store,
                        'item':     item,
                        'month':    month,
                        'day':      day,        # ← adicione esta linha
                        'weekday':  weekday,
                        'weekend':  weekend,
                        'holidays': holiday,
                        'm1':       m1,
                        'm2':       m2
                    })
                except:
                    continue
    return pd.DataFrame(future_records)

def is_holiday(x):
  india_holidays = holidays.country_holidays('IN')
  if india_holidays.get(x):
    return 1
  else:
    return 0

def which_day(year, month, day):
    d = datetime(year,month,day)
    return d.weekday()

def process(train, future):
    df = pd.DataFrame(train)
    df['date'] = df['date'].astype(str)
    parts = df['date'].str.split('-', expand=True)
    df["year"]= parts[0].astype('int')
    df["month"]= parts[1].astype('int')
    df["day"]= parts[2].astype('int')
    df['holidays'] = df['date'].apply(is_holiday)
    df['m1'] = np.sin(df['month'] * (2 * np.pi / 12))
    df['m2'] = np.cos(df['month'] * (2 * np.pi / 12))
    df['weekday'] = df.apply(lambda x: which_day(x['year'], x['month'], x['day']), axis=1)
    df.drop('date', axis=1, inplace=True)
    df['store'].nunique(), df['item'].nunique()
    df['weekend'] = df['weekday'].apply(lambda x: 1 if x >= 5 else 0)
    features = ['store', 'year', 'month', 'weekday', 'weekend', 'holidays']



    window_size = 30
    data = df[df['year']==2013]
    windows = data['sales'].rolling(window_size)
    sma = windows.mean()
    sma = sma[window_size - 1:]

    df = df[df['sales']<140]

    features = df.drop(['sales', 'year'], axis=1)
    target = df['sales'].values

    X_train, X_val, Y_train, Y_val = train_test_split(features, target,
                                                    test_size = 0.05,
                                                    random_state=22)
    #X_train.shape, X_val.shape


    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_val = scaler.transform(X_val)

    model = XGBRegressor()

    # Treina o modelo
    model.fit(X_train, Y_train)

    print('XGBRegressor : ')

    # Usa o mesmo modelo para prever
    train_preds = model.predict(X_train)
    val_preds = model.predict(X_val)

    # Avalia
    train_error = mae(Y_train, train_preds)
    val_error = mae(Y_val, val_preds)
    r2_train = r2_score(Y_train, train_preds)
    r2_val = r2_score(Y_val, val_preds)

    print(f'Training Error (MAE): {train_error:.4f}')
    print(f'Validation Error (MAE): {val_error:.4f}')
    print(f'Training R²: {r2_train * 100:.2f}%')
    print(f'Validation R²: {r2_val * 100:.2f}%')
    print()
    '''
    count = 0
    for fpe in future:
        future_df = generate_future_dataframe(fpe['future_month'], fpe['future_year'], df)
        feature_cols = df.drop(['sales', 'year'], axis=1).columns.tolist()
        future_scaled = scaler.transform(future_df[feature_cols])
        future_predictions = model.predict(future_scaled)
        future_df['predicted_sales'] = future_predictions
        future_df.to_excel('/tmp/is/fp-'+str(count)+'.xlsx', index=False)
        count = count + 1
    '''
    conn = psycopg2.connect(
        dbname="isdb",
        user="is",
        password="oliveira",
        host="localhost",  # ou outro host
        port=5432
    )
    cur = conn.cursor()

    # 2) Inserir na model_train e obter o model_id
    cur.execute("""
            INSERT INTO model_train(model_name, mae_v, mae_t, r_square_v, r_square_t)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """, (
        "xgboost",
        val_error,  # erro na validação
        train_error,  # erro no treino
        r2_val,  # R² validação
        r2_train  # R² treino
    ))
    model_id = cur.fetchone()[0]

    # 3) Para cada cenário de predição, insere em model_inference
    for count, fpe in enumerate(future):
        inference_dict = json.dumps(fpe)
        cur.execute("""
                INSERT INTO model_inference(model_id, inference_dict)
                VALUES (%s, %s)
                RETURNING id
            """, (model_id, inference_dict))
        inference_id = cur.fetchone()[0]

        # gera future_df, future_predictions...
        future_df = generate_future_dataframe(
            fpe['future_month'], fpe['future_year'], df)
        feature_cols = df.drop(['sales', 'year'], axis=1).columns.tolist()
        future_scaled = scaler.transform(future_df[feature_cols])
        future_predictions = model.predict(future_scaled)
        future_df['predicted_sales'] = future_predictions
        future_df.to_excel('/tmp/is/fp-' + str(count) + '.xlsx', index=False)

        # 4) Popula inference_results linha a linha
        for _, row in future_df.iterrows():
            key = f"{row['store']}_{row['item']}_{row['day']}"
            cur.execute("""
                    INSERT INTO inference_results(inference_id, inference_key, predicted_value)
                    VALUES (%s, %s, %s)
                """, (inference_id, key, row['predicted_sales']))

        # 5) Calcular a média histórica por item e inserir em model_mean
        hist_totals = (
            df[df['month'] == fpe['future_month']]
            .groupby(['item', 'year'])['sales']
            .sum()
            .reset_index()
        )
        hist_mean = (
            hist_totals
            .groupby('item')['sales']
            .mean()
        )
        for item_id, mean_val in hist_mean.items():
            cur.execute("""
                    INSERT INTO model_mean(model_id, inference_key, mean_value)
                    VALUES (%s, %s, %s)
                """, (model_id, str(item_id), mean_val))

        # 6) Commit e fecha conexão
        conn.commit()
        cur.close()
        conn.close()

def main(workflow_id: str):
    filePath = Path(f'/tmp/is/{workflow_id}.json')
    if not filePath.exists():
        raise FileNotFoundError(f'File {filePath} not found')
        exit(1)

    with open(filePath, 'r') as f:
        data = json.load(f)
        future = data['future']
        train = data['train']
        print(future)
        process(train, future)


def run_local_test():
    future = None
    train = None
    with open('train.json', 'r') as f:
        train = json.load(f)
    with open('future.json', 'r') as f:
        future = json.load(f)
    process(train, future)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        run_local_test()

