import pandas as pd
import re
from translate import Translator
import os
import warnings
from pandas.errors import SettingWithCopyWarning

warnings.simplefilter(action='ignore', category=SettingWithCopyWarning)


def typo_detector(str1nome, str2nome, str1cognome, str2cognome):
    str1 = str1nome + str1cognome
    str2 = str2nome + str2cognome
    if str1 in str2 or str2 in str1:
        return True
    if(sum(1 for x, y in zip(str1, str2) if x != y) <= 2):
        return True
    return False

def ids(df_raw):

    df_raw['First Name'] = df_raw['First Name'].astype(str)
    df_raw['Last Name'] = df_raw['Last Name'].astype(str)

    df_raw['First Name_lower'] = df_raw['First Name'].str.lower()
    df_raw['Last Name_lower'] = df_raw['Last Name'].str.lower()

    if os.path.exists("names_ids.xlsx"):
        df_nomi = pd.read_excel("names_ids.xlsx")

        if not df_nomi.empty:
            df_nomi['First Name'] = df_nomi['First Name'].astype(str)
            df_nomi['Last Name'] = df_nomi['Last Name'].astype(str)

            df_nomi['First Name_lower'] = df_nomi['First Name'].str.lower()
            df_nomi['Last Name_lower'] = df_nomi['Last Name'].str.lower()

            max_id = df_nomi['Player ID'].max()
        else:
            max_id = 0
    else:
        df_nomi = pd.DataFrame(columns=['First Name', 'Last Name', 'Player ID', 'First Name_lower', 'Last Name_lower'])
        max_id = 0
    
    lista_presenti = []
    for nome_raw, cognome_raw in df_raw[['First Name_lower', 'Last Name_lower']].itertuples(index=False):
        match = False
        for _, (str2nome, str2cognome) in df_nomi[['First Name_lower', 'Last Name_lower']].iterrows():
            if typo_detector(nome_raw, str2nome, cognome_raw, str2cognome):
                match = True
                break
        lista_presenti = lista_presenti + [match]
    df_raw['is_present'] = lista_presenti

    nomi_mancanti = df_raw[df_raw['is_present'] == False]

    for _, row in nomi_mancanti.iterrows():
        max_id += 1
        df_nomi.loc[len(df_nomi)] = [row['First Name'], row['Last Name'], max_id, row['First Name_lower'], row['Last Name_lower']]

    if not nomi_mancanti.empty:
        df_nomi_notlower = df_nomi.copy()
        df_nomi_notlower = df_nomi_notlower.drop(columns=['First Name_lower', 'Last Name_lower'])
        df_nomi_notlower.to_excel("names_ids.xlsx", index=False)

    mapping_nomi_id = dict(zip(df_nomi['First Name_lower'] + df_nomi['Last Name_lower'], df_nomi['Player ID']))

    df_raw.loc[:, 'Player ID'] = (df_raw['First Name_lower'] + df_raw['Last Name_lower']).map(mapping_nomi_id)
    df_raw = df_raw.drop(columns=['First Name_lower', 'Last Name_lower'])

    return df_raw

def sortColumns(processed_df):
    
    sorting_prefixes = ['Submission ID', 'User ID', 'Submission Date and Time', 'First Name',
       'Last Name', 'Player ID', 'Email',
       'Are you expected to be a starter,',
       'Is the game home or away?', 'Sleep quality of the week',
       'How focused do you feel?',
       "How clear are the coach's game plans to me?",
       "How well do I know the opponent for the next game?",
       'How tense am I about the next game?',
       "The quality of the week's training",
       'How technically ready am I for this match?',
       'How ready am I mentally for this game?',
       'How ready am I tactically for this match?',
       'How ready am I physically for this game?',
       "How confident am I in the team's performance for the next game?",
       'How confident am I in my performance against the next team?',
       'do I feel I can guarantee at high performance?',
       'Personal WORK RATE forecast',
       'What is the best technical quality of the team for the game?',
       "What is the team's best mental quality for the game?",
       'Team WORK RATE Forecast',
       'Specify',
       'What do I wanna share with the coach',
       'IP Address', 'Administrator Remarks', 'Score',
       'Max Score', 'Referer', 'URL Track', 'Time', 'Link', 'Time 1', 'Time 2',
       'Time 3', 'Time 4', 'Time 5', 'Time 6', 'Time 7', 'Time 8', 'Time 9',
       'Time 10']
    
    sorted_columns = [match_column_with_prefix(processed_df, prefix) for prefix in sorting_prefixes]

    sorted_columns = []
    for prefix in sorting_prefixes:
        matched_column = match_column_with_prefix(processed_df, prefix)
        if matched_column == "":
            print(prefix + " column is not present in the dataset. Skipping it...")
        else:
            sorted_columns.append(matched_column)

    return processed_df[sorted_columns]

def match_column_with_prefix(df, prefix):
    list = [col for col in df.columns if col.find(prefix) != -1]
    if len(list) == 0:
        return ""
    return [col for col in df.columns if col.find(prefix) != -1][0]

def translate(text):  
    translator = Translator(from_lang="autodetect", to_lang="it", email="alessandro.tenani@socialthingum.com")
    translation = translator.translate(text)
    if translation == 'PLEASE SELECT TWO DISTINCT LANGUAGES':
        return text
    elif translation.startswith('MYMEMORY WARNING:'):
        print("Reached translation limit for the day.")
        return text
    elif translation == 'Nada' or translation == 'nada':
        return 'Niente'
    return translation

def extract_number_from_rate(rate_string):
    match = re.search(r':(\d+)', rate_string)
    if match:
        return int(match.group(1))
    return 0

def adjust_rating_columns(data):
    data_dict = {}
    pattern = re.compile(r'^(.*?)\s*:\s*(\d+)$', re.MULTILINE)
    matches = pattern.findall(data)

    for match in matches:
        column_title = match[0].strip()
        value = int(match[1].strip())
        data_dict[column_title] = value

    df = pd.DataFrame([data_dict])
    return df

def main(nome_file):
    raw = pd.read_excel(nome_file)

    how_focused = []
    how_focused_column = match_column_with_prefix(raw, "How focused do you feel")

    if how_focused_column == "":
        return "The dataset is not processable: a column is missing."

    for value in raw[how_focused_column]:
        how_focused.append(extract_number_from_rate(value))

    raw[how_focused_column] = how_focused

    ratings_df = pd.DataFrame()
    rate_column = match_column_with_prefix(raw, "Rate")

    if rate_column == "":
        return "The dataset is not processable: a column is missing."
    
    for value in raw[rate_column]:
        if ratings_df.empty:
            ratings_df = adjust_rating_columns(value)
        else:
            ratings_df = pd.concat([ratings_df, adjust_rating_columns(value)], ignore_index=True)        
    ratings_df['Submission ID'] = raw['Submission ID']
    
    raw.drop(columns=[rate_column])
    processed_df = pd.merge(raw, ratings_df, on='Submission ID', how='inner')

    ids_df = ids(raw[['First Name', 'Last Name']])
    processed_df = pd.merge(processed_df, ids_df, on=['Last Name', 'First Name'], how='inner')

    translated = []
    share_with_coach_column = match_column_with_prefix(processed_df, 'What do I wanna share with the coach')
    if how_focused_column == "":
        print("No text data is available. Skipping translation...")
    else:
        for text in processed_df[share_with_coach_column]:
            translation = translate(text)
            translated.append(translation)
        
        processed_df[share_with_coach_column] = translated


    sorted = sortColumns(processed_df)
    excel_file = sorted.to_excel("processed/" + nome_file + "_processed.xlsx", index=False)

    return excel_file

           
for i in range(1,19):
    print(i)
    nome_file = str(i) + "° prematch.xlsx"
    main(nome_file)

