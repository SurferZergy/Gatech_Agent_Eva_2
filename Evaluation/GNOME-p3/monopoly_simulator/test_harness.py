import numpy as np
from monopoly_simulator import gameplay_server
from monopoly_simulator import novelty_generator
from monopoly_simulator.logging_info import log_file_create
import os
import shutil
import json


def play_tournament_without_novelty(tournament_log_folder=None, meta_seed=5, num_games=100):
    """
    Tournament logging is not currently supported, but will be soon.
    :param tournament_log_folder: String. The path to a folder.
    :param meta_seed: This is the seed we will use to generate a sequence of seeds, that will (in turn) spawn the games in gameplay/simulate_game_instance
    :param num_games: The number of games to simulate in a tournament
    :return: None. Will print out the win-loss metrics, and will write out game logs
    """

    if not tournament_log_folder:
        print("No logging folder specified, cannot log tournaments. Provide a logging folder path.")
        raise Exception

    np.random.seed(meta_seed)
    big_list = list(range(0,1000000))
    np.random.shuffle(big_list)
    tournament_seeds = big_list[0:num_games]
    winners = list()
    count = 1

    folder_name = "../tournament_logs" + tournament_log_folder
    try:
        os.makedirs(folder_name)
        print('Logging gameplay')
    except:
        print('Given logging folder already exists. Clearing folder before logging new files.')
        shutil.rmtree(folder_name)
        os.makedirs(folder_name)

    metadata_dict = {
        "function": "play_tournament_without_novelty",
        "parameters": {
            "meta_seed": meta_seed,
            "num_game": num_games
        }
    }

    json_filename = folder_name + "tournament_meta_data.json"
    out_file = open(json_filename, "w")
    json.dump(metadata_dict, out_file, indent=4)
    out_file.close()
    for t in tournament_seeds:
        print('Logging gameplay for seed: ', str(t), ' ---> Game ' + str(count))
        filename = folder_name + "meta_seed_" + str(meta_seed) + '_num_games_' + str(count) + '.log'
        logger = log_file_create(filename)
        winners.append(gameplay_server.play_game_in_tournament(t))
        handlers_copy = logger.handlers[:]
        for handler in handlers_copy:
            logger.removeHandler(handler)
            handler.close()
            handler.flush()
        count += 1

    print(winners)
    wins = 0
    for i in winners:
        if i == 'player_1':
            wins += 1

    print(wins)


def play_tournament_with_novelty_1(tournament_log_folder=None, meta_seed=5, num_games=100, novelty_index=23):
    """

    :param tournament_log_folder:
    :param meta_seed:
    :param num_games:
    :param novelty_index: an integer between 1 and num_games-1. We will play this many games BEFORE introducing novelty.
    :return:
    """

    if not tournament_log_folder:
        print("No logging folder specified, cannot log tournaments. Provide a logging folder path.")
        raise Exception

    np.random.seed(meta_seed)
    big_list = list(range(0, 1000000))
    np.random.shuffle(big_list)
    tournament_seeds = big_list[0:num_games]
    winners = list()
    count = 1

    folder_name = "../tournament_logs" + tournament_log_folder
    try:
        os.makedirs(folder_name)
        print('Logging gameplay')
    except:
        print('Given logging folder already exists. Clearing folder before logging new files.')
        shutil.rmtree(folder_name)
        os.makedirs(folder_name)

    metadata_dict = {
        "function": "play_tournament_with_novelty_1",
        "parameters": {
            "meta_seed": meta_seed,
            "novelty_index": novelty_index,
            "num_game": num_games
        }
    }

    json_filename = folder_name + "tournament_meta_data.json"
    out_file = open(json_filename, "w")
    json.dump(metadata_dict, out_file, indent=4)
    out_file.close()

    for t in range(0,novelty_index):
        print('Logging gameplay without novelty for seed: ', str(t), ' ---> Game ' + str(count))
        filename = folder_name + "meta_seed_" + str(meta_seed) + '_without_novelty' + '_num_games_' + str(count) + '.log'
        logger = log_file_create(filename)
        winners.append(gameplay_server.play_game_in_tournament(tournament_seeds[t]))
        handlers_copy = logger.handlers[:]
        for handler in handlers_copy:
            logger.removeHandler(handler)
            handler.close()
            handler.flush()
        count += 1

    new_winners = list()
    for t in range(novelty_index, len(tournament_seeds)):
        print('Logging gameplay with novelty for seed: ', str(t), ' ---> Game ' + str(count))
        filename = folder_name + "meta_seed_" + str(meta_seed) + '_with_novelty' + '_num_games_' + str(count) + '.log'
        logger = log_file_create(filename)
        new_winners.append(gameplay_server.play_game_in_tournament(tournament_seeds[t], class_novelty_1))
        handlers_copy = logger.handlers[:]
        for handler in handlers_copy:
            logger.removeHandler(handler)
            handler.close()
            handler.flush()
        count += 1

    print('pre_novelty winners', winners)
    print('post_novelty_winners', new_winners)


def class_novelty_1(current_gameboard):
    # classCardNovelty = novelty_generator.TypeClassNovelty()
    # novel_cc = dict()
    # novel_cc["street_repairs"] = "alternate_contingency_function_1"
    # novel_chance = dict()
    # novel_chance["general_repairs"] = "alternate_contingency_function_1"
    # classCardNovelty.card_novelty(current_gameboard, novel_cc, novel_chance)
    inanimateNovelty = novelty_generator.InanimateAttributeNovelty()
    inanimateNovelty.rent_novelty(current_gameboard['location_objects']['Indiana Avenue'], {'rent': 50, 'rent_1_house': 150})

#All the tournaments get logged in seperate folders inside ../tournament_logs folder
try:
    os.makedirs("../tournament_logs/")
except:
    pass

#Specify the name of the folder in which the tournament games has to be logged in the following format: "/name_of_your_folder/"
play_tournament_without_novelty('/tournament_without_novelty_4/', meta_seed=1, num_games=1000)
# play_tournament_with_novelty_1('/tournament_with_novelty/', meta_seed=10, num_games=200, novelty_index=100)
