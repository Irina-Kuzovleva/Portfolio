# -*- coding: utf-8 -*-
"""@irina_kuzovleva - Kuzovleva_Irina-Copy1.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1heIITthS1fGFv6WQ0cTKx3db42LiCE4j

# Введение

Музыкальный стриминговый сервис "МиФаСоль" расширяет работу с новыми артистами и музыкантами. В связи с этим возникла задача -- правильно классифицировать новые музыкальные треки, чтобы улучшить работу рекомендательной системы.

В данном исследовании будет проанализирован датасет, в котором собраны некоторые характеристики музыкальных произведений и их жанры.

Задача - разработать модель, позволяющую классифицировать музыкальные произведения по жанрам.

# Обработка данных

## Загрузка библиотек
"""

!pip install phik

!pip install scikit-learn==1.1.3

!pip install catboost

import pandas as pd
import numpy as np

import seaborn as sns
import matplotlib.pyplot as plt

import phik
from phik.report import plot_correlation_matrix
from phik import report

from sklearn.preprocessing import (
    StandardScaler,
    OneHotEncoder
)

from sklearn.model_selection import (
    train_test_split,
    RandomizedSearchCV
)

from sklearn.ensemble import RandomForestClassifier
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from sklearn.metrics import f1_score
from catboost import CatBoost
from sklearn.preprocessing import LabelEncoder
#from google.colab import files
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.compose import make_column_selector, make_column_transformer, ColumnTransformer

"""## Загрузка и ознакомление с данными

Загрузим тренировочный датасет.
"""

df_full = pd.read_csv('https://docs.google.com/spreadsheets/d/e/2PACX-1vRDDAAQ95Yc123yzPRDOzkGT7_zCMl_52OzikUJk4mwrLBvGlKTZxjsO5vrzNClh7tgIJWGTC7JwtXc/pub?gid=974732063&single=true&output=csv', sep=',')
df_full.head()

df_full.info()

"""Всего 15 признаков и 20394 наблюдений. Пропущенные значения есть в трех переменных (расммотрим заполнение пропусков в следующем разделе).

Загрузим тестовый датасет.
"""

df_test = pd.read_csv('https://docs.google.com/spreadsheets/d/e/2PACX-1vRK28C35dCvCWKDv-8Ee7MbXZjsHHn-VMPFn_9xG3ckkkF_U3nSn4l1pPvdf6eGctwXZrTzqRSL8X4w/pub?output=csv', sep=',')
df_test.head()

df_test.info()

#сохраним идентификатор трека в тестовом наборе
df_test_id = df_test['instance_id']

"""## Создание новых признаков

В базах есть столбец с названиями треков. Они уникальны и в числовой вид перекодировать будет трудно. Создадим новую переменную с количеством симоволов в названии трека.
"""

#кол-во символов в названии трека
df_full['symbol_count'] = df_full['track_name'].apply(lambda x: len(x))

#кол-во символов в названии трека
df_test['symbol_count'] = df_test['track_name'].apply(lambda x: len(x))

"""## Отбор финального набора обучающих признаков

Рассмотрим переменную 'obtained_date' - когда были загружены треки.
"""

df_full['obtained_date'].unique()

"""В переменной содержатся данные только за 4 дня. Так как они идут подряд, то существенной информации не несут. Далее удалим эту переменную из анализа.

Также не понадобятся данные о клиентском id, полном названии треков.

Финальный вариант данных в обучающей выборке:
"""

df = df_full.loc[:, 'acousticness':'symbol_count']

df = df.drop('obtained_date', axis= 1)
df.head()

"""В тестовой:"""

#удаляем лишние столбцы

df_test = df_test.loc[:, 'acousticness':'symbol_count']

df_test = df_test.drop('obtained_date', axis= 1)
df_test.head()

"""В разделе обучения моделей была проанализирована важность признаков. Не все признаки внесли одинаковый вклад в построении модели. Тем не менее, удаление менее важных признаков не привело к улучшению качества моделей (даже немного его ухудшило). Поэтому этот набор признаков является финальным.

## Обработка выбросов

Рассмотрим каждую переменную - ее распределение, обработаем аномальные значения.

### acousticness
"""

print(df['acousticness'].hist(bins=80, figsize=(20, 15)))
print(df['acousticness'].describe())

plt.boxplot(x=df['acousticness'])

"""Значения изменяются в промежутке от 0 до 1. Резких и выбивающихся значений нет, переменную трогать не будем.

### danceability
"""

print(df['danceability'].hist(bins=80, figsize=(20, 15)))
print(df['danceability'].describe())

plt.boxplot(x=df['danceability'])
plt.grid(True)

"""Танцевальность - тут также значения находятся в промежутке от 0 до 1, причем значения, близкие к нулю выходят за пределы "усов". Выбросов немного, они находятся близко к "усам", поэтому оставляем все как есть.

### duration_ms
"""

print(df['duration_ms'].hist(bins=80, figsize=(20, 15)))
print(df['duration_ms'].describe())

plt.boxplot(x=df['duration_ms'])
plt.grid(True)
plt.ylim(200000, 2000000)

df.query('duration_ms > 400000').count()

#заменим -1 на медиану
df.loc[df['duration_ms'] < 0 , 'duration_ms'] = df['duration_ms'].median()

#удалим очень длинные треки
df = df.query('duration_ms < 1000000')

"""В переменной есть значения, равные -1. Длительность звучания не может быть меньше нуля - заменим эти значения медианой.

Также удалим очень длинные треки - длиной больше 1000000 мс. За пределами "усов" находятся меньшие значения, но удалять их не будем, так как тогда получится очень много удаленных наблюдений (более 900).

### energy
"""

print(df['energy'].hist(bins=80, figsize=(20, 15)))
print(df['energy'].describe())

"""Значения этой переменной находятся в промежутке от 0 до 1. Оставляем переменную в этом виде.

### instrumentalness
"""

print(df['instrumentalness'].hist(bins=80, figsize=(20, 15)))
print(df['instrumentalness'].describe())

"""Здесь также видим значения от 0 до 1, переменную не трогаем.

### key
"""

df.groupby('key')['key'].count().plot(kind='bar');

"""Ключ произведения - категориальный признак. Чтобы не заполнять пропуски ошибочной информацией, создадим для пропусков отдельную категорию - 'Other' (в следующем разделе).

### liveness
"""

print(df['liveness'].hist(bins=80, figsize=(20, 15)))
print(df['liveness'].describe())

"""Значения находятся в промежутке от 0 до 1, оставляем в том виде, в каком сейчас переменная.

### loudness
"""

print(df['loudness'].hist(bins=80, figsize=(20, 15)))
print(df['loudness'].describe())

"""Громкость измеряется и положительными величинами, и отрицательными. Переменную не трогаем.

### mode
"""

df.groupby('mode')['mode'].count().plot(kind='bar')

"""Тональность бывает мажорная и минорная, все верно.

### speechiness
"""

print(df['speechiness'].hist(bins=80, figsize=(20, 15)))
print(df['speechiness'].describe())

plt.boxplot(x=df['speechiness'])
plt.grid(True)
plt.ylim(0.15, 0.6)

df.query('speechiness > 0.30').count()

#удалим выбросы в speechiness
df = df.query('speechiness < 0.55')

"""Переменная, связанная с речью в треках находится в промежутке от 0 до 1. Видно много отличающихся от среднего значений. Удалим значения, меньшие 0.55. Это самые высокие выбросы.

### tempo
"""

print(df['tempo'].hist(bins=80, figsize=(20, 15)))
print(df['tempo'].describe())

df.query('tempo > 208').count()

#удалим выбросы в tempo
df = df.query('tempo < 208')

"""Оставим только наблюдения, темп которых меньше 208.

### valence
"""

print(df['valence'].hist(bins=80, figsize=(20, 15)))
print(df['valence'].describe())

"""Привлекательность произведения для пользователей сервиса находится в промежутке от 0 до 1. Не трогаем переменную.

### music_genre - целевой признак
"""

df.groupby('music_genre')['acousticness'].count().sort_values(ascending=False).plot(kind='bar')

"""Целевой признак - музыкальный жанр - это категориальная переменная. Всего 10 жанров.
Заметен дисбаланс между разными классами. Треков жанра хип-хоп почти в 2 раза меньше, чем треков жанра блюз.

Далее будем учитывать этот дисбалан при разделении выборки, а также подбирая гиперпараметры моделей.

## Корреляция между признаками

Посмотрим, насколько связаны рассматриваемые признаки. Сначала посмтрим на переменные визуально:
"""

sns.pairplot(df, hue='music_genre');

"""Каких-то ярких закономерностей не видно. Только между переменными энергичность и громкость.

Построим матрицу корреляции с помощью библиотеки Phik.
"""

phik_overview = df.phik_matrix()
phik_overview.round(2)

"""И визуализируем ее:"""

plot_correlation_matrix(phik_overview.values,
                        x_labels=phik_overview.columns,
                        y_labels=phik_overview.index,
                        vmin=0, vmax=1, color_map="Greens",
                        title=r"correlation $\phi_K$",
                        fontsize_factor=1.3,
                        figsize=(10, 8))
plt.tight_layout()

"""Громкость и энергичность действительно имеют самый высокий коэффициент корреляции среди представленных переменных.

Также высокие коэффициенты между целевым признаком (жанры произведений) и акустичностью, танцевальностью, энергичностью, громкостью и инструментальностью. Все эти связи статистически значимы (см.ниже).
"""

interval_cols = df.select_dtypes(include=['float64', 'int64']).columns.tolist()

significance_overview = df.significance_matrix(interval_cols=interval_cols)
plot_correlation_matrix(significance_overview.fillna(0).values,
                        x_labels=significance_overview.columns,
                        y_labels=significance_overview.index,
                        vmin=-5, vmax=5, title="Significance of the coefficients",
                        usetex=False, fontsize_factor=1.3, figsize=(14, 10))
plt.tight_layout()

"""Посмотрим общий коэффициент корреляции - какие переменные наибольшим образом связаны с другими."""

global_correlation, global_labels = df.global_phik(interval_cols=interval_cols)

plot_correlation_matrix(global_correlation,
                        x_labels=[''], y_labels=global_labels,
                        vmin=0, vmax=1, figsize=(3.5,4),
                        color_map="Greens", title=r"$g_k$",
                        fontsize_factor=1.3)
plt.tight_layout()

"""Музыкальный жанр (целевая переменная), громкость, энергичность и акустичность в большей степени корреляруют с другими переменными.

## Пропущенные значения

Запоним пропуски в числовом признаке 'tempo' медианным значением по жанрам:
"""

df['tempo'] = df['tempo'].fillna(df.groupby('music_genre')['tempo'].transform('median'))
df_test['tempo'] = df_test['tempo'].fillna(df.groupby('music_genre')['tempo'].transform('median'))

"""Пропущенные значения в категориальных признаках заполним новой категорией "Другое". Обучающая выборка:"""

df['key'] = df['key'].fillna('Other')
df['mode'] = df['mode'].fillna('Other')

"""Тестовая выборка:"""

df_test['key'] = df_test['key'].fillna('Other')
df_test['mode'] = df_test['mode'].fillna('Other')

"""## Вывод

В данном разделе были загружены базы данных, удалены аномальные значения, заполнены пропуски. Также были отобраны признаки для анализа и проверена их корреляция.

# Построение моделей

Построим три модели (RandomForestClassifier - случайный лес, LGBMClassifier на основе градиентного бустинга и CatBoostClassifier), подберем параметры с помощью кросс-валидации (RandomizedSearchCV) и посмотрим на лучшую метрику f1-micro.

## Разделение на выборки

Перекодируем целевой признак:
"""

le = LabelEncoder()
le.fit(df['music_genre'])
le.classes_
music_genre_transform = le.transform(df['music_genre'])
music_genre_transform

"""Разделим обучающую выборку на две - обучающую и валидационную (10%). Так как у нас есть дисбаланс в целевом признаке, при разбиении укажем параметр stratify."""

target = music_genre_transform
features = df.drop('music_genre', axis=1)

features_train, features_valid, target_train, target_valid \
= train_test_split(features, target, test_size=0.1, random_state=12345, stratify=target)

print('features_train:')
print(features_train.shape[0])

print('features_valid:')
print(features_valid.shape[0])

"""Выделим категориальные и числовые признаки:"""

cat_columns = features.select_dtypes(include='object').columns.tolist()
num_columns = features.select_dtypes(include=['float64', 'int64']).columns.tolist()

"""## RandomForestClassifier

Проведем обработку данных и построим модели с помощью pipeline. Обработка столбцов будет одинаковой для всех моделей:
"""

column_transformer = make_column_transformer((StandardScaler(), num_columns),
                                             (OneHotEncoder(drop='first'), cat_columns),
                                              remainder='passthrough')

model_forest = RandomForestClassifier(random_state=1234)
pipeline_forest = make_pipeline(column_transformer, model_forest)
pipeline_forest

"""Параметры"""

params_forest = {'randomforestclassifier__n_estimators': range(10, 100),
                 'randomforestclassifier__max_depth': range(2, 15)
         }

# Commented out IPython magic to ensure Python compatibility.
# %%time
# 
# randomdearch_forest = RandomizedSearchCV(pipeline_forest, params_forest, cv=5, scoring='f1_micro', random_state=12345)
# randomdearch_forest.fit(features_train, target_train)
# 
# print('f1-micro:', randomdearch_forest.best_score_)
# print('Лучшие параметры модели:', randomdearch_forest.best_params_)

"""## LGBMClassifier"""

model = LGBMClassifier(random_state=1234)
pipeline = make_pipeline(column_transformer, model)
pipeline

params = {'lgbmclassifier__n_estimators': range(10, 100),
          'lgbmclassifier__objective': ['multiclass', 'multiclassova'],
          'lgbmclassifier__max_depth': range(2, 20),
          'lgbmclassifier__subsample_for_bin': [200000, 300000],
          'lgbmclassifier__verbose': [-1]
         }

# Commented out IPython magic to ensure Python compatibility.
# %%time
# 
# randomsearch = RandomizedSearchCV(pipeline, params, cv=5, scoring='f1_micro', random_state=12345)
# randomsearch.fit(features_train, target_train)
# 
# print('f1-micro:', randomsearch.best_score_)
# print('Лучшие параметры модели:', randomsearch.best_params_)

"""## CatBoostClassifier"""

model_cat = CatBoostClassifier(random_state=1234)
pipeline_cat = make_pipeline(column_transformer, model_cat)
pipeline_cat

params_cat = {'catboostclassifier__iterations': range(10, 100),
              'catboostclassifier__depth': range(2, 15),
              'catboostclassifier__verbose': [False]
         }

# Commented out IPython magic to ensure Python compatibility.
# %%time
# 
# randomsearch_cat = RandomizedSearchCV(pipeline_cat, params_cat, cv=5, scoring='f1_micro', random_state=12345)
# randomsearch_cat.fit(features_train, target_train)
# 
# print('f1-micro:', randomsearch_cat.best_score_)
# print('Лучшие параметры модели:', randomsearch_cat.best_params_)

"""## Проверка на валидационной выборке"""

lgbm_valid = randomsearch.predict(features_valid)
result_f1 = f1_score(target_valid, lgbm_valid, average='micro')
print('F1 на валидационной выборке:', result_f1)

"""На валидационной выборке (10% от исходного датасета) качество модели немного хуже, чем на тренировочной. Разница в 1% не очень велика, поэтому можно сказать, что модель работает стабильно.

## Важность признаков

Посмотрим, какие признаки наиболее важны при определении целевой переменной - музыкального жанра.
"""

pipeline.fit(features_train, target_train)

feature_importance = pipeline.named_steps['lgbmclassifier'].feature_importances_
feature_names = column_transformer.get_feature_names_out()
features_model_lgbm = pd.DataFrame(feature_names, feature_importance)
features_model_lgbm.columns = ['features_names']
features_model_lgbm.sort_index(ascending=False)

"""Высокое значение важности означает, что значение признака вносит большой вклад в определение музыкального жанра.

Можно заметить, что категориальные признаки - тональность и ключ - практически не играют роли в определении целевой переменной. Наиболее значимы - количественные признаки.

На первом месте - danceability(танцевальность). Далее идут speechiness(выразительность), valence(привлекательность произведения для пользователей сервиса), acousticness(акустичность), duration_ms(длительность в миллисекундах).

Интересно, что новый созданный признак - длина названия трека(symbol_count) - тоже вносит достаточный вклад в классификацию музыки.

## Вывод

Было рассмотрено три модели, они показали примерно одинаковое качество - 0.471-0.482. Лучшее качество у LGBMClassifier - 0.482, худшее - у CatBoostClassifier - 0.47.

Параметры лучшей модели LGBMClassifier:

{'subsample_for_bin': 200000,

'objective': 'multiclassova',

'n_estimators': 43,

'max_depth': 13}

На валидационной выборке качество получилось на 1% хуже, чем на тренировочной. Это значит, что модель работает стабильно и ее можно использовать.

Самые важные признаки, которые влияют на целевую переменную, это:  danceability(танцевальность), speechiness(выразительность), valence(привлекательность произведения для пользователей сервиса), acousticness(акустичность), duration_ms(длительность в миллисекундах)

# Предсказания на тестовой выборке

Решим поставленную задачу - классифицируем треки, представленные в тестовой базе.
"""

features_test = df_test
lgbm_model_predictions_test = randomsearch.predict(features_test)

lgbm_model_predictions_test = pd.DataFrame(data=lgbm_model_predictions_test)
test_result = pd.concat([df_test, df_test_id, lgbm_model_predictions_test], axis=1)
test_result.head()

test_result = pd.DataFrame(test_result)
test_result = test_result.iloc[:, [13, 14]]
test_result.columns = ['instance_id', 'music_genre']
test_result['music_genre'] = le.inverse_transform(test_result['music_genre'])
test_result.head()

"""Выше - часть итоговой таблицы. Значение F1- mini равно 0.47764, что близко к показателю, значит, модель работает достаточно стабильно.

# Вывод

Сначала были загружены базы данных, удалены аномальные значения, заполнены пропуски. Также были отобраны признаки для анализа и проверена их корреляция.

Было рассмотрено три модели, они показали примерно одинаковое качество метрики F1-микро - 0.471-0.482. Лучшее качество у модели LGBMClassifier - 0.482.

На валидационной выборке качество получилось на 1% хуже, чем на тренировочной. Это значит, что модель работает стабильно и ее можно использовать.

Это показала и тестовая выборка, метрика F1-микро на которой равна 0.477, что примерно на 0.5% хуже, чем показала тренировочная выборка.

Самые важные признаки, которые влияют на целевую переменную, это: danceability(танцевальность), speechiness(выразительность), valence(привлекательность произведения для пользователей сервиса), acousticness(акустичность), duration_ms(длительность в миллисекундах).
"""