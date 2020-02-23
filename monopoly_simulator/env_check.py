from vanilla_A2C import *
from configparser import ConfigParser

env = gym.make('monopoly_simple-v1')
print('seeds =====>', env.seed(seed=0))
s = env.reset()
print('s =====>', s)
print('======================step======================')
s = env.step(0) #buy
print('======================step======================')
print('s =====>', s)
s = env.step(25) #mortgage
print('======================step======================')
print('s =====>', s)
s = env.step(53) #free-mortgage
print('======================step======================')
print('s =====>', s)