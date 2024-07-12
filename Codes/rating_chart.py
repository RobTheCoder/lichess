import datetime
import pandas as pd
import numpy as np
import berserk
import os
import math
import pytz
import time
#import asciichartpy as ac
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


def data_formation(main_dict):
    url = 'https://github.com/Laxman-Lakhan/Laxman-Lakhan/blob/d72c599f65d5d4d91742b5ba0842e758094ec852/Codes/dP.csv?raw=true'
    dP = pd.read_csv(url)
    dP.drop(['Unnamed: 0'], axis = 1, inplace = True)
    Chess_df = pd.DataFrame.from_dict(main_dict, orient ='columns')
    Chess_df.reset_index(inplace = True)
    Chess_df['New Rating'] = Chess_df['My Rating'] + Chess_df['Rating Fluctuation']
    Chess_df.loc[Chess_df['Winner'] == Chess_df['My Color'], 'Result'] = 1
    Chess_df.loc[(Chess_df['Winner'] != Chess_df['My Color']) & (Chess_df['Winner'] != None), 'Result'] = 0
    Chess_df.loc[Chess_df['Winner'].isna(), 'Result'] = 0.5
    Chess_df.drop(['Winner', 'My Color'], axis = 1, inplace = True)
    
    k = 100
    Chess_df['Ra'] = Chess_df['Opponent Rating'].rolling(k).mean()
    Chess_df['p'] = round(Chess_df['Result'].rolling(k).sum()/k, 2)
    Chess_df = Chess_df.merge(dP, on='p')
    Chess_df['Performance'] = round(Chess_df['Ra'] + Chess_df['dp'], 0)
    Chess_df.sort_values('index', inplace = True)
    Chess_df.reset_index(inplace = True)
    Chess_df.drop(columns = ['level_0', 'index', 'Ra', 'dp', 'p', 'My Rating', 
                       'Rating Fluctuation', 'Opponent Rating'], inplace = True)
    return Chess_df


    
def main():
    games:list = get_games()
    flat_games:pd.DataFrame = flatten_games(games)

    #Chess_df = data_formation(dict_formation(data_extractor()))
    #ratings_list = list(Chess_df['New Rating'])[::-1][0:100][::-1]
    #performance_list = list(Chess_df['Performance'])[::-1][0:100][::-1]
    #result_list = Chess_df['Result'][::-1][0:100][::-1]
    #return (ac.plot(ratings_list, {'height': 15, 'format':'{:4.0f}'})), ratings_list, performance_list, \
    #    result_list, list(Chess_df['Played'])[::-1][0].strftime('%a, %d-%b-%Y %I:%M %p %Z')


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
    
