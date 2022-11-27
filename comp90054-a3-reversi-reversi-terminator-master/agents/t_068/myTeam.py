from template import Agent
import random, time
from Reversi.reversi_model import ReversiGameRule
import collections
import copy

# define the constant
TIME_LIMIT = 0.97 # less than theoretical 1 second
NUM_OF_PLAYER = 2
GAMMA = 0.9
EPSILON = 0.3  #random > 1-e

# significant squares
CORNER = [(0,0), (0,7), (7,0), (7,7)] # best
X_SQUARE = [(1,1), (1,6), (6,1), (6,6)]
C_SQUARE = [(0,1), (1,0), (0,6), (1,7), (6,0), (7,1), (7,6), (6,7)]
EDGE = [(2,0), (3,0), (4,0), (5,0),
        (2,7), (3,7), (4,7), (5,7),
        (0,2), (0,3), (0,4), (0,5),
        (7,2), (7,3), (7,4), (7,5)]
INNER_SQAURE = [(2,2), (2,3), (2,4), (2,5), 
                (3,2), (4,2), (3,5), (4,5),
                (5,2), (5,3), (5,4), (5,5)]
MIDDLE_SQAURE = [(2,1), (3,1), (4,1), (5,1), 
                (1,2), (1,3), (1,4), (1,5),
                (6,2), (6,3), (6,4), (6,5), 
                (2,6), (3,6), (4,6), (5,6)]
                
ROXANNE_TABLE = [CORNER,
                INNER_SQAURE,
                EDGE,
                MIDDLE_SQAURE,
                X_SQUARE,
                C_SQUARE]

class myAgent(Agent):
    def __init__(self,_id):
        super().__init__(_id)
        self.gameRule = ReversiGameRule(NUM_OF_PLAYER)
        self.rival_id = 1 - _id
        self.selfColor = self.gameRule.agent_colors[_id] 

    def GetSelfActions(self, state):
        return self.gameRule.getLegalActions(state,self.id)

    def GetRivalActions(self, state):
        return self.gameRule.getLegalActions(state, self.rival_id)

    def ExcuteSelfAction(self, state, action):
        nextState = self.gameRule.generateSuccessor(state,action,self.id)
        nextScore = self.gameRule.calScore(nextState,self.id)
        return (nextState, nextScore)

    def ExcuteRivalAction(self, state, action):
        nextState = self.gameRule.generateSuccessor(state, action, self.rival_id)
        nextScore = self.gameRule.calScore(nextState, self.rival_id)
        return (nextState, nextScore)

    def GameEnd(self, state):
        return (self.GetSelfActions(state) == ["Pass"] and self.GetRivalActions(state) == ["Pass"])

    def CalReward(self,state):
        return self.gameRule.calScore(state,self.id) - self.gameRule.calScore(state,1-self.id)

    # return the intersection of two lists
    def list_intersection(self, list1, list2):
        return list(set(list1).intersection(set(list2)))

    # return the difference between two lists
    def list_difference(self, list1, list2):
        return list(set(list1).difference(set(list2)))

    def CutTree(self, actions, gameState):
        # Keep the corners only if there is any
        corners = self.list_intersection(actions, CORNER)
        if len(corners) == 1:
            return corners[0]
        if len(corners) > 0:
            actions = corners

        x_squares = self.list_intersection(actions, X_SQUARE)
        c_squares = self.list_intersection(actions, C_SQUARE)

        temp_actions = copy.deepcopy(actions)
        if len(x_squares) + len(c_squares) > 1:
            for action in list(x_squares + c_squares):
                tempState = copy.deepcopy(gameState)
                tempNextState, _ = self.ExcuteSelfAction(tempState, action)
                corners_rival = self.list_intersection(list(self.GetRivalActions(tempNextState)), CORNER)
                if len(corners_rival) > 0:
                    actions.remove(action)

            if len(actions) == 0:
                actions = temp_actions

        # Check X-squares which are neighbor of self-taken corners
        # since if any corner is put on, neighboring squares would be good  
        x_neighbors = []
        temp_actions = copy.deepcopy(actions)
        if len(x_squares) > 0:
            for square in CORNER:
                x_co, y_co = square
                if gameState.board[x_co][y_co] == self.selfColor:
                    taken_corner_index = CORNER.index((x_co, y_co)) 
                    x_neighbors.append(X_SQUARE[taken_corner_index])

            # Remove non-neighbor X-squares of taken corners
            # and revert actions if none of action is left
            for x in x_squares:
                if x not in x_neighbors and x in actions:
                    actions.remove(x)
            
            if len(actions) == 0:
                actions = temp_actions

        # Check C-squares which are neighbor of self-taken corners
        # since if any corner is put on, neighboring squares would be good  
        c_neighbors = []      
        temp_actions = copy.deepcopy(actions)
        if len(c_squares) > 0:
            for square in CORNER:
                x_co, y_co = square
                if gameState.board[x_co][y_co] == self.selfColor:
                    taken_corner_index = CORNER.index((x_co, y_co)) 
                    c_neighbors.append(C_SQUARE[2*taken_corner_index])
                    c_neighbors.append(C_SQUARE[2*taken_corner_index+1])

            # Remove non-neighbor C-squares of taken corners
            # and revert actions if none of action is left
            for c in c_squares:
                if c not in c_neighbors and c in actions:
                    actions.remove(c)
            
            if len(actions) == 0:
                actions = temp_actions
        
        return list(actions)

    # Make a move by Roxanne priority
    def Move_Roxanne(self, actions):
        action = random.choice(actions)
        for move_list in ROXANNE_TABLE:
            random.shuffle(move_list)
            for move in move_list:
                if move in actions:
                    action = move
        return action

    def SelectAction(self, actions, game_state):
        # init:change to the current state
        self.gameRule.agent_colors = game_state.agent_colors
        count = 0
        startTime = time.time()

        # Cut the tree options
        actions = self.CutTree(actions, game_state)
        
        # If the tree is cut to only one corner
        if actions in CORNER:
            return actions

        solution = self.Move_Roxanne(actions)

        # record the value of state
        value_state = dict()
        # Count the number of state being chosen
        number_state = dict()
        # record the best action of state:using the string to be key
        best_action = dict()
        # the expanded actions
        expanded_actions = dict()
        root_state = 'r'

        # check if the state has fully expanded
        def availableActions(state, actions):
            if state in expanded_actions:
                expanded_action = expanded_actions[state]
                return self.list_difference(actions,expanded_action)
            else:
                return actions

        # get the next state of rival
        def rivalMove(next_state):
            rival_new_actions = self.GetRivalActions(next_state)
            rival_max_score = 0
            rival_best_state = next_state
            rival_best_actions = []
            _flag = False

            if rival_new_actions != ["Pass"]:
                for move_list in ROXANNE_TABLE:
                    random.shuffle(move_list)
                    if _flag:
                        break
                    for move in move_list:
                        if move in rival_new_actions:
                            rival_best_actions.append(move)
                            _flag = True
            else:
                rival_best_actions = ["Pass"]

            rival_best_actions = rival_new_actions

            for rival_action in rival_best_actions:
                rival_next_state, rival_next_score = self.ExcuteRivalAction(next_state,rival_action)
                if rival_next_score > rival_max_score:
                    rival_max_score = rival_next_score
                    rival_best_state = rival_next_state
                    rival_best_action = rival_action
                    
            return rival_best_state, rival_best_action


        # start MCT
        while time.time() - startTime < TIME_LIMIT:
            state = copy.deepcopy(game_state)
            new_actions = actions
            curr_state = root_state
            dequeue = collections.deque([]) #in order to back
            count += 1

            # SELECT
            while len(availableActions(curr_state, new_actions)) == 0 and not self.GameEnd(state):
                if time.time() - startTime >= TIME_LIMIT:
                    return solution
                if (random.uniform(0, 1) < (1 - EPSILON)) and (curr_state in best_action):
                    curr_action = best_action[curr_state]
                else:
                    curr_action = self.Move_Roxanne(new_actions)

                next_state, next_score = self.ExcuteSelfAction(state,curr_action)
                dequeue.append((curr_state,curr_action))

                #rival move
                rival_best_state, rival_best_action = rivalMove(next_state)

                #Iteration
                curr_state = curr_state + str(curr_action[0]) + str(curr_action[1]) \
                            + str(rival_best_action[0]) + str(rival_best_action[1])
                new_actions = self.GetSelfActions((rival_best_state))
                state = rival_best_state

            # EXPAND
            left_actions = availableActions(curr_state, new_actions)

            # fully expanded
            if len(left_actions) == 0:
                action = self.Move_Roxanne(new_actions)
            else:
                action = self.Move_Roxanne(left_actions)

            # if in the expanded list
            if curr_state in expanded_actions:
                expanded_actions[curr_state].append(action)
            else:
                expanded_actions[curr_state] = [action]

            dequeue.append((curr_state,action))
            next_state, next_score = self.ExcuteSelfAction(state, action)
            rival_best_state, rival_best_action = rivalMove(next_state)
            curr_state = curr_state + str(action[0]) + str(action[1]) \
                        + str(rival_best_action[0]) + str(rival_best_action[1])
            new_actions = self.GetSelfActions(rival_best_state)
            state = rival_best_state


            # SIMULATION
            length = 0
            while not self.GameEnd(state):
                if time.time() - startTime >= TIME_LIMIT:
                    return solution
                length += 1
                curr_action = self.Move_Roxanne(new_actions)

                next_state, next_score = self.ExcuteSelfAction(state, curr_action)
                rival_best_state, _ = rivalMove(next_state)
                new_actions = self.GetSelfActions(rival_best_state)
                state = rival_best_state
            
            reward = self.CalReward(state)


            # BACKPROPAGATE
            curr_value = reward * (GAMMA ** length)
            while len(dequeue) and time.time() - startTime < TIME_LIMIT:
                curr_state, curr_action = dequeue.pop()
                if curr_state in value_state:
                    if curr_value > value_state[curr_state]:
                        best_action[curr_state] = curr_action
                        value_state[curr_state] = curr_value
                    number_state[curr_state] += 1
                else:
                    value_state[curr_state] = curr_value
                    number_state[curr_state] = 1
                    best_action[curr_state] = curr_action
                curr_value *= GAMMA
            if root_state in best_action:
                solution = best_action[root_state]


        return solution
        