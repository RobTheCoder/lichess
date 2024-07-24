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
    USERNAME:str = 'LICHESS_USERNAME'
    TOKEN:str = 'LICHESS_TOKEN'
    CSV:str = 'LICHESS_CSV'

@lru_cache(maxsize=32)
def get_required_os_enviroment_variable(variable_key: str)->str:
    """ Retreives an environment variable by key and throws an exception if not set
        raises ValueError if the environment variable is not set """
    required_value:str = os.environ.get(variable_key, False) 
    if not required_value:
        raise ValueError(f'Environment Variable {variable_key} is not set.')
    return required_value

def get_username()->str:
   """ Retreives the usename from enviroment variables """
   return get_required_os_enviroment_variable(EnviromentVariableKey.USERNAME.value)

def get_token()->str:
    """ Retreives the token from rnvironment variables """
    return get_required_os_enviroment_variable(EnviromentVariableKey.TOKEN.value)

def get_csv_url()->str:
    """ Retreives the URL for a CSV file """
    return get_required_os_enviroment_variable(EnviromentVariableKey.CSV.value)

def get_games()->list[iter]:
    """ Returns a list of games via API """
    session:berserk.TokenSession = berserk.TokenSession(get_token())
    client:berserk.Client = berserk.Client(session=session)
    games:iter = client.games.export_by_player(get_username(), as_pgn=False, since=None, until=None, 
                                          max=199, vs=None, rated=True, perf_type='rapid', color=None, 
                                          analysed=None, moves=False, tags=False, evals=False, opening=False)
    return list(games)

def get_player_colors(white_player_usename: str)->tuple[str,str]:
    """ Determines the players colors based on username """
    my_color:str = 'White' if white_player_usename == get_username() else 'Black'
    opponent_color:str = 'White' if my_color == 'Black' else 'White'
    return (my_color, opponent_color)

def calc_my_score(winner: pd.Series, my_color: str)->float:
    """ Calculate a contexual score for the user """
    if winner.isna():
        return 0.5
    return 1 if winner == my_color else 0


def flatten_games(games: list)->pd.DataFrame:
    """ Takes a list of json games and flattens them into a data frame with contextual information. """
    flattened_games:list = []
    for game in games:
        my_color:str; opponent_color:str = get_player_colors(game['players']['white']['user']['id'])
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

def add_calculated_columns(df:pd.DataFrame, k:int = 100)->pd.DataFrame:
    """ Adds a set of columns with calculated values to the data frame"""
    df['New Rating'] = df['My Rating'] + df['Rating Fluctuation']
    df['Result'] = df[['My Color', 'Winner']].apply(calc_my_score)
    df['Ra'] = df['Opponent Rating'].rolling(k).mean()
    df['p'] = round(df['Result'].rolling(k).sum()/k, 2)
    return df

def add_performance_column(df:pd.DataFrame)->pd.DataFrame:
        """ Adds a column to the data frame """
        df['Performance'] = round(['Ra'] + df['dp'], 0)
        return df

def drop_unused_columns(df:pd.DataFrame)->pd.DataFrame:
    """ Removes a predetermined list of columns that are no longer used """
    columns_to_drop:list = ['level_0','index', 'Ra', 'dp', 'p', 'My Rating', 
                       'Rating Fluctuation', 'Opponent Rating', 'Winner', 'My Color', 'Unnamed: 0']
    df.drop(columns = columns_to_drop, inplace = True)
    return df

def get_url_df(url:str)->pd.DataFrame:
    return pd.read_csv(url)

def csv_merge(chess_df:pd.DataFrame, csv_data:pd.DataFrame)->pd.DataFrame:
    """ Takes two data frames and merges them """
    chess_df:pd.DataFrame = chess_df.merge(csv_data, on='p')
    chess_df.sort_values('index', inplace = True)
    chess_df.reset_index(inplace = True)
    return chess_df

def get_plot(serires:pd.Series)->str:
    """ Returns a plot based on settings """
    config:dict = {'height': 15, 'format':'{:4.0f}'}
    return ac.plot(serires, config)

def main()->None:
    api_games:list = get_games()
    flattened_api_games:pd.DataFrame = flatten_games(api_games)
    csv_url:str = get_csv_url()
    csv_data:pd.DataFrame = get_url_df(csv_url)
    combined_games:pd.DataFrame = csv_merge(flattened_api_games, csv_data)
    drop_unused_columns(combined_games)
    last_hundred_ratings:pd.DataFrame = combined_games['New Rating'][-100:]
    last_hundred_performance:list = list(combined_games['Performance'])[-100:]
    last_hundred_results:pd.DataFrame = combined_games['Result'][-100:]
    last_time_stamp:str = list(combined_games['Played'])[-1].strftime('%a, %d-%b-%Y %I:%M %p %Z')

    wins:pd.Series = last_hundred_results.value_counts()[1]
    draws:pd.Series = last_hundred_results.value_counts()[0.5]
    losses:pd.Series = last_hundred_results.value_counts()[0]
    last_performance: int = int(last_hundred_performance[-1])
    last_rating:int = last_hundred_ratings[-1]
    print(get_plot(last_hundred_ratings))
    print('Wins', 'Draws', 'Losses', 'Performance Rating', 'Current Rating', 'Highest Rating', 'Average Rating', sep = ' '*6)
    print((' '*2+' '+'{}'+' ').format(wins), 
              (' '*2+'{}'+' '*2).format(draws), 
              (' '*2+'{}'+' '*2).format(losses), 
              (' '*7+'{}'+' '*7).format(last_performance),
              (' '*5+'{}'+' '*5).format(last_rating), 
              (' '*5+'{}'+' '*5).format(last_hundred_ratings.max()), 
              (' '*5+'{}'+' '*5).format(round(last_hundred_ratings.mean())), 
              sep = ' '*6, end = '\n\n')

    print('Last Game Played On:', last_time_stamp)


if __name__ == "__main__":
    main()
