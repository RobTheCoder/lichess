import datetime
import pandas as pd
import numpy as np
import berserk
import os
import math
import pytz
import time
import asciichartpy as ac
from functools import lru_cache
from enum import Enum

class EnviromentVariableKey(Enum):
    USERNAME = 'LICHESS_USERNAME'
    TOKEN = 'LICHESS_TOKEN'

@lru_cache(maxsize=32)
def get_required_os_enviroment_variable(variable_key: str)->str:
    """ Retreives an environment variable by key and throws an exception if not set
        raises ValueError if the environment variable is not set """
    required_value = os.environ.get(variable_key, False) 
    if not required_value:
        raise ValueError(f'Environment Variable {variable_key} is not set.')
    return required_value

def get_username()->str:
   return get_required_os_enviroment_variable(EnviromentVariableKey.USERNAME.value)

def get_token()->str:
    return get_required_os_enviroment_variable(EnviromentVariableKey.TOKEN.value)

def get_games()->list:
    session = berserk.TokenSession(get_token())
    client = berserk.Client(session=session)
    games = client.games.export_by_player(get_username(), as_pgn=False, since=None, until=None, 
                                          max=199, vs=None, rated=True, perf_type='rapid', color=None, 
                                          analysed=None, moves=False, tags=False, evals=False, opening=False)
    return list(games)

def get_player_colors(white_player_usename: str)->tuple:
    my_color = 'White' if white_player_usename == getUsername() else 'Black'
    opponent_color = 'White' if my_color == 'Black' else 'White'
    return (my_color, opponent_color)

def calc_my_score(winner: pd.Series, my_color: str):
    if winner.isna():
        return 0.5
    return 1 if winner == my_color else 0


def flatten_games(games: list)->pd.DataFrame:
    flattened_games:list = []
    for game in games:
        my_color, opponent_color = get_player_colors(game['players']['white']['user']['id'])
        my_rating:str = game['players'][my_color]['rating']
        rating_diff:str = game['players'][my_color].get('ratingDiff', 0)
        opponent_rating:str = game['players'][opponent_color]['rating']
        last_moved_timestamp:str = game['lastMoveAt'].astimezone(pytz.timezone('Asia/Kolkata'))
        winner:str = game.get('winner', '').capitalize()
        new_row:dict = {'My Color': my_color,
                   'My Rating': my_rating,
                   'Opponent Rating': opponent_rating,
                   'Rating Fluctuation': rating_diff,
                   'Played': last_moved_timestamp,
                   'Winner': winner}
        flattened_games.append(new_row)
    return pd.DataFrame(flattened_games)

def add_calculated_columns(df, k = 100):
    df['New Rating'] = df['My Rating'] + df['Rating Fluctuation']
    df['Result'] = df[['My Color', 'Winner']].apply(calc_my_score)
    df['Ra'] = df['Opponent Rating'].rolling(k).mean()
    df['p'] = round(df['Result'].rolling(k).sum()/k, 2)
    return df

def add_performance_column(df):
        df['Performance'] = round(['Ra'] + df['dp'], 0)
        return df

def drop_unused_columns(df: pd.DataFrame):
    columns_to_drop = ['level_0','index', 'Ra', 'dp', 'p', 'My Rating', 
                       'Rating Fluctuation', 'Opponent Rating', 'Winner', 'My Color', 'Unnamed: 0']
    df.drop(columns = columns_to_drop, inplace = True)
    return df

def get_url_df(url):
    url = 'https://github.com/Laxman-Lakhan/Laxman-Lakhan/blob/d72c599f65d5d4d91742b5ba0842e758094ec852/Codes/dP.csv?raw=true'
    return pd.read_csv(url)

def csv_merge(chess_df:pd.DataFrame, csv_data:pd.DataFrame)->pd.DataFrame:
    chess_df = chess_df.merge(csv_data, on='p')
    chess_df.sort_values('index', inplace = True)
    chess_df.reset_index(inplace = True)
    return chess_df

def get_plot(serires):
    config = {'height': 15, 'format':'{:4.0f}'}
    return ac.plot(serires, config)

def main():
    api_games:list = get_games()
    flattened_api_games:pd.DataFrame = flatten_games(api_games)
    csv_data:pd.DataFrame = get_url_df()
    combined_games = csv_merge(flattened_api_games, csv_data)
    drop_unused_columns(combined_games)
    last_hundred_ratings:list = list(combined_games['New Rating'])[-100:]
    last_hundred_performance:list = list(combined_games['Performance'])[-100:]
    last_hundred_results:list = list(combined_games['Result'][-100:])
    last_time_stamp:str = list(combined_games['Played'])[-1].strftime('%a, %d-%b-%Y %I:%M %p %Z')
    return (get_plot(last_hundred_ratings)), last_hundred_ratings, last_hundred_performance, last_hundred_results, last_time_stamp


if __name__ == "__main__":
    main()
    exit()
    plot, rl, pl, res_l, date = main()
    W = res_l.value_counts()[1]
    D = res_l.value_counts()[0.5]
    L = res_l.value_counts()[0]

    print (plot, '\n')

    print('Wins', 'Draws', 'Losses', 'Performance Rating', 'Current Rating', 'Highest Rating', 'Average Rating', sep = ' '*6)
    if len(str(D)) == 1:
        print((' '*2+' '+'{}'+' ').format(W), 
              (' '*2+'{}'+' '*2).format(D), 
              (' '*2+'{}'+' '*2).format(L), 
              (' '*7+'{}'+' '*7).format(int(pl[-1])),
              (' '*5+'{}'+' '*5).format(rl[-1]), 
              (' '*5+'{}'+' '*5).format(max(rl)), 
              (' '*5+'{}'+' '*5).format(round(np.mean(rl))), 
              sep = ' '*6, end = '\n\n')
    else:
        print((' '*2+' '+'{}'+' ').format(W), 
              (' '*2+'{}'+' '*2).format(D), 
              (' '*1+'{}'+' '*2).format(L), 
              (' '*7+'{}'+' '*7).format(int(pl[-1])),
              (' '*5+'{}'+' '*5).format(rl[-1]), 
              (' '*5+'{}'+' '*5).format(max(rl)), 
              (' '*5+'{}'+' '*5).format(round(np.mean(rl))), 
              sep = ' '*6, end = '\n\n')

    print('Last Game Played On:',date)
    
