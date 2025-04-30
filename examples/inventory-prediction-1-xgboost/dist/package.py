import sys
import json
from pathlib import Path
from datetime import datetime
import os

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import mean_absolute_error as mae, r2_score
from xgboost import XGBRegressor
import holidays
import psycopg2


def is_holiday(date_str):
    india_holidays = holidays.country_holidays('IN')
    return 1 if india_holidays.get(date_str) else 0


def which_day(year, month, day):
    return datetime(year, month, day).weekday()


def generate_future_dataframe(month, year, df):
    """
    Gera DataFrame de previsão para todas as lojas e itens em um mês/ano.
    """
    stores = df['store'].unique()
    items = df['item'].unique()
    records = []
    for store in stores:
        for item in items:
            for day in range(1, 32):
                try:
                    d = datetime(year, month, day)
                except ValueError:
                    break  # dia inválido para o mês
                weekday = d.weekday()
                weekend = 1 if weekday >= 5 else 0
                m1 = np.sin(month * 2 * np.pi / 12)
                m2 = np.cos(month * 2 * np.pi / 12)
                holiday = is_holiday(d.strftime('%Y-%m-%d'))
                records.append({
                    'store': store,
                    'item': item,
                    'month': month,
                    'day': day,
                    'weekday': weekday,
                    'weekend': weekend,
                    'holidays': holiday,
                    'm1': m1,
                    'm2': m2
                })
    return pd.DataFrame(records)


def process(train_records, future_scenarios):
    # Carrega dados de treino
    df = pd.DataFrame(train_records)
    df['date'] = pd.to_datetime(df['date'])
    df['year'] = df['date'].dt.year
    df['month'] = df['date'].dt.month
    df['day'] = df['date'].dt.day

    # Features temporais
    df['holidays'] = df['date'].dt.strftime('%Y-%m-%d').apply(is_holiday)
    df['m1'] = np.sin(df['month'] * 2 * np.pi / 12)
    df['m2'] = np.cos(df['month'] * 2 * np.pi / 12)
    df['weekday'] = df.apply(lambda x: which_day(x['year'], x['month'], x['day']), axis=1)
    df['weekend'] = (df['weekday'] >= 5).astype(int)
    df.drop('date', axis=1, inplace=True)

    # Remove outliers
    df = df[df['sales'] < 140]

    # Prepara X e y
    feature_cols = [c for c in df.columns if c not in ('sales', 'year')]
    X = df[feature_cols]
    y = df['sales'].values

    # Split e normalização
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.05, random_state=22
    )
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train)
    X_val = scaler.transform(X_val)

    # Treina modelo XGBoost
    model = XGBRegressor()
    model.fit(X_train, y_train)

    # Avalia desempenho
    train_preds = model.predict(X_train)
    val_preds = model.predict(X_val)
    train_error = mae(y_train, train_preds)
    val_error = mae(y_val, val_preds)
    r2_train = r2_score(y_train, train_preds)
    r2_val = r2_score(y_val, val_preds)

    print('Model trained: XGBRegressor')
    print(f'Training MAE: {train_error:.4f}, R2: {r2_train:.4f}')
    print(f'Validation MAE: {val_error:.4f}, R2: {r2_val:.4f}')

    # Conecta ao banco
    conn = psycopg2.connect(
        dbname='isdb', user='is', password='oliveira',
        host='localhost', port=5432
    )
    cur = conn.cursor()

    # Insere meta-modelo
    cur.execute(
        '''INSERT INTO model_train(model_name, mae_v, mae_t, r_square_v, r_square_t)
           VALUES (%s, %s, %s, %s, %s) RETURNING id''',
        ('xgboost', val_error, train_error, r2_val, r2_train)
    )
    model_id = cur.fetchone()[0]

    # Processa cada cenário de inferência
    for idx, scenario in enumerate(future_scenarios):
        month = scenario['future_month']
        year = scenario['future_year']
        # Insere metadados de inferência
        inf_dict = json.dumps(scenario)
        cur.execute(
            '''INSERT INTO model_inference(model_id, inference_dict)
               VALUES (%s, %s) RETURNING id''',
            (model_id, inf_dict)
        )
        inference_id = cur.fetchone()[0]

        # Gera previsões
        fut_df = generate_future_dataframe(month, year, df)
        X_fut = scaler.transform(fut_df[feature_cols])
        fut_preds = model.predict(X_fut)
        fut_df['predicted_sales'] = fut_preds

        # Agrega total previsto por item e loja
        agg_df = fut_df.groupby(['store', 'item'])['predicted_sales'].sum().reset_index()

        # Salva Excel com colunas store, item, predicted_sales
        os.makedirs('/tmp/is', exist_ok=True)
        agg_df.to_excel(f'/tmp/is/fp-{idx}.xlsx', index=False, columns=['store', 'item', 'predicted_sales'])

        # Insere inference_results: uma linha por item
        for _, row in agg_df.iterrows():
            cur.execute(
                '''INSERT INTO inference_results(inference_id, inference_key, predicted_value)
                   VALUES (%s, %s, %s)''',
                (inference_id, str(row['item']), float(row['predicted_sales']))
            )

        # Calcula média histórica mensal por item
        hist_totals = (
            df[df['month'] == month]
              .groupby(['item','year'])['sales']
              .sum()
        )
        hist_mean = hist_totals.groupby('item').mean()
        for item_id, mean_val in hist_mean.items():
            cur.execute(
                '''INSERT INTO model_mean(model_id, inference_key, mean_value)
                   VALUES (%s, %s, %s)''',
                (model_id, str(item_id), float(mean_val))
            )

    # Salva e fecha conexão
    conn.commit()
    cur.close()
    conn.close()


def main(workflow_id: str):
    path = Path(f'/tmp/is/{workflow_id}.json')
    if not path.exists():
        raise FileNotFoundError(f'File {path} not found')

    data = json.loads(path.read_text())
    process(data['train'], data['future'])


if __name__ == '__main__':
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        # Teste local
        train = json.load(open('train.json'))
        future = json.load(open('future.json'))
        process(train, future)
