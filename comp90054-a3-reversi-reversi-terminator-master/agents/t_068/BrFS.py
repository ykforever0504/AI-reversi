from typing import final
from template import Agent
from Reversi.reversi_model import ReversiGameRule
from Reversi.reversi_utils import Cell, GRID_SIZE
import random
import collections
import time
import copy

# Significant squares
"""
Idea from https://samsoft.org.uk/reversi/strategy.htm
Strategies about significant squares:
- Corners are the most significant
    - Put on as much as possible
    - Avoid the opponent to put on
- X-square and C-square 
    - Avoid as much as possible especially X-square
    - Try let the opponent to put on
- A-square and B-square are also important to be put on
-
"""
CORNER = [(0,0), (0,7), (7,0), (7,7)] # best
X_SQUARE = [(1,1), (6,6), (1,6), (6,1)] # worst
C_SQUARE = [(0,1), (1,0), (0,6), (1,7), (6,0), (7,1), (7,6), (6,7)] # bad
A_SQUARE = [(0,2), (2,0), (0,5), (2,7), (5,0), (7,2), (7,5), (5,7)] # good
B_SQUARE = [(0,3), (0,4), (3,0), (4,0), (7,3), (7,4), (3,7), (4,7)] # good

NUM_OF_PLAYER = 2
TIME_LIMIT = 980 # in millisecond (less than theoretical 1 second)


class myAgent(Agent):
    def __init__(self, _id):
        super().__init__(_id)
        self.opponent_id = 1 - _id
        self.gameRule = ReversiGameRule(NUM_OF_PLAYER)

    def SelectAction(self, actions, game_state):
        '''
        This function reads the game state to check if the game ends
        :param actions: eligible actions
        :param game_state: game state
        :returns: final selected action
        '''
        start_time = time.perf_counter()

        # Stick with the agent index
        self.gameRule.agent_colors = game_state.agent_colors

        # Create a queue to store the state and a list to store moves
        myQueue = collections.deque([(game_state, [])])

        count = 0 
        max_score = 0

        # Prioritise checking the corners and X-squares
        corners = self.CheckSignificantSqaure(actions, "corner")
        if len(corners) == 0:
            pass
        elif len(corners) == 1:
            return corners[0]
        else:
            actions = corners

        x_sqaures = self.CheckSignificantSqaure(actions, "x-square")
        if not all(square in X_SQUARE for square in actions):
            actions = [square for square in actions if square not in x_sqaures]

        
        # Check C-squares which is neighbor of taken corners
        # since if any corner is put on, neighboring c-squares would be good     
        c_squares = self.CheckSignificantSqaure(actions, "c-square")
        temp_actions = copy.deepcopy(actions)
        c_neighbors = []

        if len(c_squares) > 0 and len(c_squares) != len(actions):

            for square in CORNER:
                x_co, y_co = square
                if game_state.board[x_co][y_co] == self.gameRule.agent_colors[self.id]:
                    taken_corner_index = CORNER.index((x_co, y_co)) 
                    c_neighbors.append(C_SQUARE[2*taken_corner_index])
                    c_neighbors.append(C_SQUARE[2*taken_corner_index+1])

            # Remove non-neighbor C-squares of taken corners
            # and revert actions if none of action is left
            for c in c_squares:
                if c not in c_neighbors:
                    actions.remove(c)
            
            if len(actions) == 0:
                actions = temp_actions


        # Initialised with a random move
        # final_action = random.choice(actions) 
        final_action = actions[0] 

        # count_empty = 0
        # for i in range(GRID_SIZE):
        #     for j in range(GRID_SIZE):
        #         if game_state.board[i][j] == Cell.EMPTY:
        #             count_empty += 1

        # if count_empty < GRID_SIZE * GRID_SIZE / 2:

        # State is not continuing and time limit is not exceeded yet
        while len(myQueue) and (time.perf_counter() - start_time)*1000 < TIME_LIMIT:
            count += 1
            state, moves = myQueue.popleft()
            next_actions = list(set(self.gameRule.getLegalActions(state, self.id)))
            flag = None

            # First, keep the corners only if there is any
            # and look for the best one by further simulation
            # and flag the corner situation
            corners = self.CheckSignificantSqaure(next_actions, "corner")
            if len(corners) == 0:
                flag = "no_corners_action"
            elif len(corners) == 1:
                pass
            else:
                flag = "corners_action"
                next_actions = corners

            if flag == "no_corners_action":
                # Second, avoid the X-sqaures if there is any
                # and look for the best one left by further simulation
                x_sqaures = self.CheckSignificantSqaure(next_actions, "x-square")
                if not all(square in X_SQUARE for square in next_actions):
                    next_actions = [square for square in next_actions if square not in x_sqaures]

                # Next, avoid the C-squares if there is any 
                # when there is no neighboring corners put on
                # and look for the best one left by further simulation
                c_squares = self.CheckSignificantSqaure(next_actions, "c-square")
                temp_next_actions = list(next_actions)

                # Check C-squares which is neighbor of taken corners
                # since if any corner is put on, neighboring c-squares would be good     
                c_neighbors = []
                for square in CORNER:
                    x_co, y_co = square
                    if state.board[x_co][y_co] == self.gameRule.agent_colors[self.id]:
                        co_index = CORNER.index((x_co, y_co)) 
                        c_neighbors.append(C_SQUARE[2*co_index])
                        c_neighbors.append(C_SQUARE[2*co_index+1])

                # Remove non-neighbor C-squares of taken corners
                # and revert actions if none of action is left
                for c in c_squares:
                    if c not in c_neighbors:
                        next_actions.remove(c)
                if all(square in c_neighbors for square in temp_next_actions) or len(next_actions) == 0:
                    next_actions = temp_next_actions

            for action in next_actions:
                # End if the time limit is exceeded
                if (time.perf_counter() - start_time)*1000 > TIME_LIMIT:
                    print("timeout")
                    break

                next_state = self.gameRule.generateSuccessor(state, action, self.id)
                next_score = self.gameRule.calScore(next_state, self.id)
                next_moves = moves + [action]

                # End when games ends
                if self.GameEnds(next_state):
                    if next_score > max_score:
                        max_score = next_score
                        final_action = next_moves[0]
                        continue

                opponent_actions = list(set(self.gameRule.getLegalActions(next_state, self.opponent_id)))

                # Try to avoid the opponent to have good moves
                corners_opponent = self.CheckSignificantSqaure(opponent_actions, "corner")
                if len(corners_opponent) > 0:
                    continue

                # Try to let the opponent to have bad moves

                # Randomise next move of opponent
                opponent_action = random.choice(opponent_actions)
                next_state = self.gameRule.generateSuccessor(next_state, \
                                            opponent_action, self.opponent_id)

                myQueue.append((next_state, next_moves))

        print("bfs round: ", count)
        print("final_action: ", final_action)
        print("time: ", time.perf_counter() - start_time)
        print("*"*30)   

        return final_action

    def GameEnds(self, state):
        '''
        This function reads the game state to check if the game ends
        when both players can no longer make moves
        :param state: game state
        :returns: true or false
        '''
        if self.gameRule.getLegalActions(state, 0) == ["Pass"] \
            and self.gameRule.getLegalActions(state, 1) == ["Pass"]:
            return True
        else: return False

    def CheckSignificantSqaure(self, actions, type):
        '''
        This function outputs the squares position
        by type of significant square specified
        :param action: actions can be made
        :param type: type of significant squares
        :returns: true or false
        '''
        squares = []
        if type == "corner":
            return list(set(actions) & set(CORNER))

        if type == "x-square":
            return list(set(actions) & set(X_SQUARE))

        if type == "a-square":
            return list(set(actions) & set(A_SQUARE))

        if type == "b-square":
            return list(set(actions) & set(B_SQUARE))

        if type == "c-square":
            return list(set(actions) & set(C_SQUARE))

        return squares
