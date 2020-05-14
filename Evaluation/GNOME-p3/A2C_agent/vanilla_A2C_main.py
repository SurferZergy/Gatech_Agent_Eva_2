# Without knowledge graph development
# Only consider 2 actions
# Only take one action each time
import os
import sys
upper_path_eva = '/media/becky/GNOME-p3'
sys.path.append(upper_path_eva)

from monopoly_simulator_background.vanilla_A2C import *
from configparser import ConfigParser
import graphviz
from torchviz import make_dot
from monopoly_simulator_background.gameplay_tf import *
# import logger

from itertools import product
import argparse
import warnings
warnings.filterwarnings('ignore')

from monopoly_simulator_background.interface import Interface
upper_path = '/'.join(os.getcwd().split('/')[:-1])
from monopoly_simulator.server_agent import ServerAgent
# os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
#
# class Config:
#     device = torch.device('cuda:3')

######
import os, sys
upper_path = '/'.join(os.getcwd().split('/')[:-1])
sys.path.append(upper_path)
from monopoly_simulator.agent import Agent
from multiprocessing.connection import Client
import A2C_agent.RL_agent_v1 as RL_agent_v1
from A2C_agent.novelty_detection import KG_OpenIE_eva
from A2C_agent.interface_eva import Interface_eva
import torch
from A2C_agent.vanilla_A2C import *
from monopoly_simulator import action_choices
from configparser import ConfigParser
# from A2C_agent.vanilla_A2C_main import MonopolyTrainer
######
class HiddenPrints:
    def __enter__(self):

        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout

# def largest_prob(prob, masked_actions):
#     prob = prob.cpu().detach().numpy().reshape(-1,)
#     # print('prob', prob)
#     #Check if the action is valid
#     action_Invalid = True
#     largest_num = -1
#     while action_Invalid:
#         a = prob.argsort()[largest_num:][0]
#         action_Invalid = True if masked_actions[a] == 0 else False
#         largest_num -= 1
#     return a
class MonopolyTrainer:
    def __init__(self, params, device_id, gameboard=None, kg_use=True):
        self._device_id = device_id
        self.params = params
        self.PRINT_INTERVAL = self.params['print_interval']
        self.n_train_processes = self.params['n_train_processes']  # batch size
        self.learning_rate = self.params['learning_rate']
        self.update_interval = self.params['update_interval']
        self.gamma = self.params['gamma']
        self.max_train_steps = self.params['max_train_steps']
        self.hidden_state = self.params['hidden_state']
        self.action_space = self.params['action_space']
        self.state_num = self.params['state_num']
        self.actor_loss_coefficient = self.params['actor_loss_coefficient']
        self.kg_vector = []
        self.interface = Interface()
        self.save_path = self.params['save_path']


        # # config logger
        # hyper_config_str = '_n' + str(self.n_train_processes) + '_lr' + str(self.learning_rate) + '_ui' + str(
        #     self.update_interval) \
        #                    + '_y' + str(self.gamma) + '_s' + str(self.max_train_steps) + '_hs' + str(self.hidden_state) \
        #                    + '_as' + str(self.action_space) + '_sn' + str(self.state_num) \
        #                    + '_ac' + str(self.actor_loss_coefficient)
        # self.TB = logger.Logger(None, [logger.make_output_format('csv', 'logs/', log_suffix=hyper_config_str)])

        if not self._device_id:  # use all available devices
            use_cuda = torch.cuda.is_available()
            self.device = torch.device("cuda" if use_cuda else "cpu")
        else:
            os.environ["CUDA_VISIBLE_DEVICES"] = str(self._device_id)
            self.device = torch.device('cuda:0')

        ###set to cpu for evaluation
        self.device = torch.device('cuda:0')
            #######################################

        with HiddenPrints():
            self.envs = ParallelEnv(self.n_train_processes, gameboard, kg_use)

        self.config_model = ConfigParser()
        self.config_model.hidden_state = self.params['hidden_state']
        self.config_model.action_space = self.params['action_space']
        self.config_model.state_num = self.params['state_num']

        if gameboard:
            self.interface.set_board(gameboard)
            self.config_model.state_num = len(self.interface.board_to_state(gameboard))


        self.model = ActorCritic(self.config_model)  # A2C model
        self.model.to(self.device)
        self.loss = 0
        self.optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate)

        self.memory = Memory()

    def train(self):
        step_idx = 0
        with HiddenPrints():
            reset_array = self.envs.reset()

            s, masked_actions = [reset_array[i][0] for i in range(len(reset_array))], \
                                [reset_array[i][1] for i in range(len(reset_array))]

        loss_train = torch.tensor(0, device=self.device).float()
        while step_idx < self.max_train_steps:
            loss = torch.tensor(0, device=self.device).float()

            for _ in range(self.update_interval):
                # print('location', s[0][-10])
                # move form last layer
                entropy = 0
                log_probs, masks, rewards, values = [], [], [], []

                # s = s.reshape(n_train_processes, -1)
                prob = self.model.actor(torch.tensor(s, device=self.device).float())  # s => tensor #output = prob for actions
                # print(prob)
                # prob = model.actor(torch.from_numpy(s,device=device).float()) # s => tensor #output = prob for actions
                # use the action from the distribution if it is in masked

                a = []
                for i in range(self.n_train_processes):
                    # action_Invalid = True
                    # num_loop = 0
                    a_once = Categorical(prob).sample().cpu().numpy()[i]  # substitute
                    if masked_actions[i][a_once] == 0:
                        a_once = 1
                    # while action_Invalid:
                    #     a_once = Categorical(prob).sample().cpu().numpy()[i] #substitute
                    #     action_Invalid = True if masked_actions[i][a_once] == 0 else False
                    #     num_loop += 1

                    # if num_loop > 5:
                    #     a_once = largest_prob(prob[i], masked_actions)
                    #     break
                    a.append(a_once)
                # print('a', a)
                # while opposite happens. Step won't change env, step_nochange changes the env\
                s_prime_cal, r, done, info = self.envs.step_nochange(a)
                # s_prime_cal = torch.tensor(s_prime_cal, device=self.device).float()

                values.append(self.model.critic(torch.tensor(s, device=self.device).float()))

                log_prob = Categorical(prob).log_prob(torch.tensor(a, device=self.device))
                entropy += Categorical(prob).entropy().mean()
                log_probs.append(log_prob)
                rewards.append(torch.FloatTensor(r).unsqueeze(1).to(self.device))

                done = [[0] if i > 0 else [1] for i in done]
                masks.append(torch.tensor(done, device=self.device).float())


                # Teacher forcing part #
                a_tf = []
                for i in range(self.n_train_processes):
                    if masked_actions[i][0] == 1:
                        a_tf.append(0)
                    else:
                        a_tf.append(1)

                # a_tf = [0 for i in range(self.n_train_processes)]
                # print('a_tf', a_tf)
                s_prime, _, _, info = self.envs.step_after_nochange(a_tf)
                #########################
                masked_actions = [info_[0] for info_ in info]  # Update masked actions
                # print('masked_actions',masked_actions, info[-1],s_prime[-1][-10])

                s = s_prime

                ##########
                s_prime_cal = torch.tensor(s_prime_cal, device=self.device).float()

                # loss cal
                log_probs = torch.cat(log_probs)
                returns = compute_returns(self.model.critic(s_prime_cal), rewards, masks, gamma=0.99)
                # print(s_prime_cal)
                # print(self.model.critic(s_prime_cal))

                returns = torch.cat(returns).detach()
                # print('returns',returns)
                values = torch.cat(values)
                advantage = returns - values
                # print('log_probs',log_probs)
                actor_loss = -(log_probs * advantage.detach()).mean()
                # print('actor_loss',actor_loss)
                critic_loss = advantage.pow(2).mean()
                # print('critic_loss',critic_loss)
                loss += actor_loss + 0.5 * critic_loss - 0.001 * entropy
                self.memory.clear()
                # print('loss',loss)

            loss /= self.update_interval
            self.loss = loss
            loss_train += loss
            print('loss', loss)
            if loss != torch.tensor(0, device=self.device):
                self.optimizer.zero_grad()
                self.loss.backward()
                self.optimizer.step()

            # if step_idx % self.PRINT_INTERVAL == 0:
            #     print('loss_train ===>', loss_train / self.PRINT_INTERVAL)
            #     self.TB.logkv('step_idx', step_idx)
            #     self.TB.logkv('loss_train', round(float(loss_train) / self.PRINT_INTERVAL, 3))
            #     loss_train = torch.tensor(0, device=self.device).float()
            #     # if step_idx % PRINT_INTERVAL == 0:
            #     avg_score, avg_winnning = test(step_idx, self.model, self.device, num_test=1)
            #     self.TB.logkv('avg_score', avg_score)
            #     self.TB.logkv('avg_winning', avg_winnning)
            #     self.TB.dumpkvs()
                # save weights of A2C
                if step_idx % self.PRINT_INTERVAL == 0:
                    save_name = upper_path + self.save_path + '/push_buy_tf_ne_v3_' + str(int(step_idx / self.PRINT_INTERVAL)) + '.pkl'
                    torch.save(self.model, save_name)

            step_idx += 1
            # print('step_idx',step_idx)
        self.envs.close()


if __name__ == '__main__':
    # read the config file and set the hyper-param
    config_file = 'config.ini'
    config_data = ConfigParser()
    config_data.read(config_file)

    # set param_list: a list of dictionary
    all_params = {}
    # print('config_data',config_data['hyper'])
    for key in config_data['hyper']:
        v = eval(config_data['hyper'][key])
        if not isinstance(v, tuple):
            all_params[key] = (v,)
        else:
            all_params[key] = v


    def dict_product(d):
        param_list = []
        keys = d.keys()
        for element in product(*d.values()):
            param_list.append(dict(zip(keys, element)))
        return param_list


    param_list = dict_product(all_params)

    # specify device
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", type=int)
    args = parser.parse_args()
    device_id = args.device
    print(device_id)

# set board for debug
    ####set up board####
    player_decision_agents = dict()
    # player_decision_agents['player_1'] = P1Agent()

    # Assign the beckground agents to the players
    # name_num = 0
    # num_player = 4
    # while name_num < num_player:
    #     name_num += 1
    #     player_decision_agents['player_' + str(name_num)] = None
    #
    # gameboard_initial = set_up_board('/media/becky/GNOME-p3/monopoly_game_schema_v1-1.json',
    #                                  player_decision_agents) #, num_player)
    # print(gameboard_initial.keys())
    ########
    import pickle
    with open('/media/becky/GNOME-p3/Evaluation/GNOME-p3/A2C_agent/gameboard.pickle', 'rb') as f:
        gameboard_initial = pickle.load(f)
        print(gameboard_initial)

    for params in param_list:  # run different hyper parameters in sequence
        trainer = MonopolyTrainer(params, device_id, gameboard=gameboard_initial, kg_use=False)
        trainer.train()

# if __name__ == '__main__':
#     config_file = '/media/becky/Novelty-Generation-Space-A2C/Vanilla-A2C/config.ini'
#     config_data = ConfigParser()
#     config_data.read(config_file)
#     # print('config_data.items', config_data.sections())
#     # Hyperparameters
#     n_train_processes = 1
#     learning_rate = 0.0002
#     update_interval = 5
#     gamma = 0.98
#     max_train_steps = 60000
#     PRINT_INTERVAL = 100
#     config = Config()
#     config.hidden_state = 256
#     config.action_space = 2
#     config.state_num = 56
#     actor_loss_coefficient = 1
#     save_dir = '/media/becky/GNOME-p3/monopoly_simulator'
#     use_cuda = torch.cuda.is_available()
#     device = torch.device("cuda:3" if use_cuda else "cpu")
#     save_name = '/push_buy'
#     import os
#     os.environ["CUDA_VISIBLE_DEVICES"] = '3'
#
#     #######################################
#     with HiddenPrints():
#         envs = ParallelEnv(n_train_processes)
#     model = ActorCritic(config) #A2C model
#     model.to(device)
#     optimizer = optim.Adam(model.parameters(), lr=learning_rate)
#
#     step_idx = 0
#
#     with HiddenPrints():
#         reset_array = envs.reset()
#         s, masked_actions = [reset_array[i][0] for i in range(len(reset_array))], \
#                             [reset_array[i][1] for i in range(len(reset_array))]
#
#     # print('s',s)
#     # print('mask', masked_actions)
#
#         # s = torch.tensor(s, device=device).float()
#         # masked_actions = torch.tensor(masked_actions, device=device)
#     loss_train = torch.tensor(0, device=device).float()
#     while step_idx < max_train_steps:
#         loss = torch.tensor(0, device=device).float()
#         for _ in range(update_interval):
#             #move form last layer
#             entropy = 0
#             log_probs, masks, rewards, values = [], [], [], []
#
#             # s = s.reshape(n_train_processes, -1)
#             prob = model.actor(torch.tensor(s, device=device).float())  # s => tensor #output = prob for actions
#             # prob = model.actor(torch.from_numpy(s,device=device).float()) # s => tensor #output = prob for actions
#             #use the action from the distribution if it is in masked
#
#             a = []
#             for i in range(n_train_processes):
#                 # action_Invalid = True
#                 # num_loop = 0
#                 a_once = Categorical(prob).sample().cpu().numpy()[i]  # substitute
#                 # while action_Invalid:
#                 #     a_once = Categorical(prob).sample().cpu().numpy()[i] #substitute
#                 #     action_Invalid = True if masked_actions[i][a_once] == 0 else False
#                 #     num_loop += 1
#
#                     # if num_loop > 5:
#                     #     a_once = largest_prob(prob[i], masked_actions)
#                     #     break
#                 a.append(a_once)
#             #while opposite happens. Step won't change env, step_nochange changes the env\
#             s_prime_cal, r, done, masked_actions = envs.step_nochange(a)
#
#             values.append(model.critic(torch.tensor(s, device=device).float()))
#
#             log_prob = Categorical(prob).log_prob(torch.tensor(a, device=device))
#             entropy += Categorical(prob).entropy().mean()
#             log_probs.append(log_prob)
#             rewards.append(torch.FloatTensor(r).unsqueeze(1).to(device))
#             done = [[1] if i > 0 else [0] for i in done]
#             masks.append(torch.tensor(done, device=device).float())
#
#
#             a_tf = [0 for i in range(n_train_processes)]
#             s_prime, _, done, masked_actions = envs.step_after_nochange(a_tf)
#             s = s_prime
#
#
#             ##########
#             s_prime_cal = torch.tensor(s_prime_cal, device=device).float()
#
#             # loss cal
#             log_probs = torch.cat(log_probs)
#             returns = compute_returns(model.critic(s_prime_cal), rewards, masks, gamma=0.99)
#             returns = torch.cat(returns).detach()
#             values = torch.cat(values)
#             advantage = returns - values
#
#             actor_loss = -(log_probs * advantage.detach()).mean()
#             critic_loss = advantage.pow(2).mean()
#
#             loss += actor_loss + 0.5 * critic_loss - 0.001 * entropy
#
#
#         loss /= update_interval
#         loss_train += loss
#         # print('loss', loss)
#         if loss != torch.tensor(0, device = device):
#             optimizer.zero_grad()
#             loss.backward()
#             optimizer.step()
#         # graphviz.Source(make_dot(loss, params=dict(model.named_parameters()))).render('full_net')
#         # print('weight after test = > ', model.fc_actor.weight)
#         if step_idx % 100 == 0:
#             print('loss_train ===>', loss_train / 100)
#             loss_train = torch.tensor(0, device=device).float()
#         if step_idx % PRINT_INTERVAL == 0:
#             test(step_idx, model,device, num_test=10)
#             #save weights of A2C
#             if step_idx % PRINT_INTERVAL == 0:
#                 save_path = '/media/becky/GNOME-p3/monopoly_simulator/weights'
#                 save_name = save_path + '/push_buy_tf_ne_' + str(int(step_idx / PRINT_INTERVAL)) + '.pkl'
#
#                 torch.save(model, save_name)
#
#         step_idx += 1
#
#     envs.close()
